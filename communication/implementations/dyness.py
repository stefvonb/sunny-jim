import threading

from crc16 import crc16xmodem

import communication.devices
import serial
from time import sleep, time


class DynessA48100Com(communication.devices.Battery):
    NUM_CELLS: int = 15
    SERIAL_DATA_REQUEST: bytearray
    RESPONSE_START_BYTES: bytearray
    SLIDING_BUFFER_SIZE: int

    def __init__(self, **kwargs):
        super().__init__()
        try:
            self.serial_port = kwargs['serial_port']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.bms = None

        # The following bytes are sent to the serial port to get the battery status
        self.SERIAL_DATA_REQUEST = bytearray([250, 16, 0, 0, 0, 1, 1])
        crc16_bytes = crc16xmodem(bytes(self.SERIAL_DATA_REQUEST)).to_bytes(2, 'big')
        self.SERIAL_DATA_REQUEST += crc16_bytes
        self.SERIAL_DATA_REQUEST.append(237)
        self.SERIAL_DATA_REQUEST += b'\r'

        # This appears to be how frames start for the response. If things are going wrong parsing responses, I would
        # check this first
        self.RESPONSE_START_BYTES = bytearray.fromhex("FA8000")
        self.SLIDING_BUFFER_SIZE = len(self.RESPONSE_START_BYTES)

        reading_thread = threading.Thread(target=self.__read_serial_response)
        writing_thread = threading.Thread(target=self.__serial_poll_request)

        self.threads = [reading_thread, writing_thread]
        self.thread_lock = threading.Lock()

    def try_connect(self) -> bool:
        try:
            self.bms = serial.Serial(self.serial_port, 9600)
        except serial.SerialException as serial_exception:
            self.log.error(serial_exception)
            return False
        except ValueError as value_error:
            self.log.error(value_error)
            return False

        self.bms.reset_input_buffer()
        self.bms.reset_output_buffer()

        return True

    def try_disconnect(self) -> bool:
        self.bms.close()
        return True

    def __read_serial_response(self):
        self.log.info("Started listening for state updates.")
        sliding_buffer = b'000'
        response_frame = b''

        while self.running:
            try:
                in_waiting = self.bms.inWaiting()
            except:
                # Not good practice to catch all errors, but the idea is that the polling thread will deal with
                # connection issues. So we'll just wait here until things are connected again...
                continue
            if in_waiting:
                sliding_buffer += self.bms.read()
                sliding_buffer = sliding_buffer[1:]

                if response_frame:
                    response_frame += sliding_buffer[-1:]

                if sliding_buffer == self.RESPONSE_START_BYTES:
                    response_frame = sliding_buffer[:]

                if len(response_frame) >= 88:
                    try:
                        current_state = self.__decode_state(response_frame)
                    except Exception as e:
                        self.log.error(f"Something went wrong updating state: {e}")
                        response_frame = b''
                        continue

                    with self.thread_lock:
                        # Update the logical state of the battery
                        self.time_updated = time()
                        self.voltage = current_state['voltage']
                        self.current = current_state['current']
                        self.state_of_charge = current_state["SOC"]
                        self.state_of_health = current_state["SOH"]
                        self.cell_voltages = current_state["cell_voltages"]
                        self.temperatures = current_state["temperatures"]
                        self.notify_observers()

                    response_frame = b''

        self.log.info("Stopped listening for state updates.")

    def __serial_poll_request(self):
        self.log.info("Started serial polling loop.")
        while self.running and self.connected:
            if time() - self.time_updated > 1.5:
                try:
                    self.bms.write(self.SERIAL_DATA_REQUEST)
                    sleep(1)
                except serial.SerialException:
                    self.connected = False
                    self.try_reconnect()

        self.log.info("Stopped serial polling loop.")
        self.stop()

    def __decode_state(self, buffer: bytes) -> dict:
        state = {}

        state["cell_voltages"] = []
        for i in range(self.NUM_CELLS):
            state["cell_voltages"].append((float(buffer[2 * i + 6] << 8) + float(buffer[2 * i + 1 + 6])) / 1000)

        state["temperatures"] = []
        for i in range(4):
            state["temperatures"].append(float((buffer[38] << 8) + buffer[39] - 400) / 10)

        state["voltage"] = float((buffer[46] << 8) + buffer[47]) / 100
        state["current"] = float((buffer[48] << 8) + buffer[49] - 4000) / 10

        state["SOC"] = float(buffer[50]) / 100
        state["SOH"] = float(buffer[51]) / 100

        return state

    def __del__(self):
        self.stop()

        if self.bms is None:
            return

        try:
            self.bms.close()
        except serial.SerialException:
            pass

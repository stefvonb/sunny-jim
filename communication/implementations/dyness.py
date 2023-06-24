from communication.crc16 import crc16xmodem

import communication.devices
import asyncio
import serial_asyncio
import serial
from time import time

class DynessA48100Com(communication.devices.Battery):
    NUM_CELLS: int = 15
    SERIAL_DATA_REQUEST: bytearray
    RESPONSE_START_BYTES: bytearray
    SLIDING_BUFFER_SIZE: int

    def __init__(self, device_id: str, **kwargs):
        super().__init__(device_id)
        try:
            self.serial_port = kwargs['serial_port']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.bms_reader, self.bms_writer = None, None

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
        
        # Set up some variables to track the data received
        self.sliding_buffer = b'000'
        self.response_frame = b''

    async def __get_serial(self):
        reader, writer = await serial_asyncio.open_serial_connection(url=self.serial_port, baudrate=9600)
        return reader, writer

    async def try_connect(self) -> bool:
        try:
            self.bms_reader, self.bms_writer = await self.__get_serial()
            await self.bms_writer.drain()
        except serial.SerialException as serial_exception:
            self.log.error(serial_exception)
            return False
        except ValueError as value_error:
            self.log.error(value_error)
            return False

        return True

    async def try_disconnect(self) -> bool:
        self.bms_reader.close()
        self.bms_writer.close()
        return True

    async def receive(self):
        while len(self.response_frame) < 88:
            try:
                next_bit = await self.bms_reader.read(1)
                self.sliding_buffer += next_bit
            except Exception as e:
                continue
            self.sliding_buffer = self.sliding_buffer[1:]

            if self.response_frame:
                self.response_frame += self.sliding_buffer[-1:]

            if self.sliding_buffer == self.RESPONSE_START_BYTES:
                self.response_frame = self.sliding_buffer[:]

        try:
            current_state = self.__decode_state(self.response_frame)
        except Exception as e:
            self.log.error(f"Something went wrong updating state: {e}")
            self.response_frame = b''
            return

        # Update the logical state of the battery
        self.time_updated = time()
        self.voltage = current_state['voltage']
        self.current = current_state['current']
        self.state_of_charge = current_state["SOC"]
        self.state_of_health = current_state["SOH"]
        self.cell_voltages = current_state["cell_voltages"]
        self.temperatures = current_state["temperatures"]
        self.response_frame = b''

    async def send(self):
        try:
            await self.bms_writer.drain()
            self.bms_writer.write(self.SERIAL_DATA_REQUEST)
            await asyncio.sleep(1.5)
        except serial.SerialException:
            self.connected = False
            self.try_reconnect()

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

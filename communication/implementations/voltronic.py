import threading

import serial

import communication
from communication.devices import Inverter


class KodakOGX548Inverter(Inverter):
    BAUD_RATE: int = 2400

    def __init__(self, **kwargs):
        super().__init__()
        try:
            self.serial_port = kwargs['serial_port']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.inverter = None

        # Threads and threading
        self.thread_lock = threading.Lock()

    def try_connect(self) -> bool:
        try:
            self.inverter = serial.Serial(self.serial_port, baudrate=self.BAUD_RATE)
        except serial.SerialException as serial_exception:
            self.log.error(serial_exception)
            return False
        except ValueError as value_error:
            self.log.error(value_error)
            return False

        self.inverter.reset_input_buffer()
        self.inverter.reset_output_buffer()

        return True

    def try_disconnect(self) -> bool:
        self.inverter.close()
        return True

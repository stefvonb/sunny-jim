import serial
from serial.tools.list_ports import comports
from crc16 import crc16xmodem
import logging

logger = logging.getLogger()


class SerialCommunicator:
    def __init__(self, port, baud_rate):
        self.serial = serial.Serial(port, baud_rate)

    def get_response(self, command):
        # Convert the command to binary
        command_bytes = command.encode('utf-8')
        # Calculate the required CRC bytes and append them to the command
        crc_bytes = crc16xmodem(command_bytes).to_bytes(2, 'big')
        command_bytes += crc_bytes
        # Append a carriage return to the command
        command_bytes += b"\r"

        # Write the enriched command to the serial
        write_status = self.serial.write(command_bytes)
        response_bytes = b''

        # Read the response from the serial
        while self.serial.inWaiting():
            response_bytes += self.serial.read()

        response_string = response_bytes.decode("ascii")
        return response_string

    def __del__(self):
        self.serial.close()

    @staticmethod
    def get_available_ports():
        return comports()
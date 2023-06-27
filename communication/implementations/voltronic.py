from time import time

import serial
import serial_asyncio

import communication
from communication.devices import Inverter
import asyncio
from communication.crc16 import crc16xmodem


class KodakOGX548Inverter(Inverter):
    BAUD_RATE: int = 2400
    POLL_TIME: int = 0.5

    def __init__(self, device_id: str, **kwargs):
        super().__init__(device_id)
        try:
            self.serial_port = kwargs['serial_port']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.inverter = None
        self.QPIGS = b"QPIGS" + crc16xmodem(b"QPIGS").to_bytes(2, 'big') + b'\r'

    async def __get_serial(self):
        reader, writer = await serial_asyncio.open_serial_connection(url=self.serial_port, baudrate=self.BAUD_RATE)
        return reader, writer

    async def try_connect(self) -> bool:
        try:
            self.inverter_reader, self.inverter_writer = await self.__get_serial()
            await self.inverter_writer.drain()
        except serial.SerialException as serial_exception:
            self.log.error(serial_exception)
            return False
        except ValueError as value_error:
            self.log.error(value_error)
            return False

        return True

    async def try_disconnect(self) -> bool:
        self.inverter_reader.close()
        self.inverter_writer.close()
        return True

    async def send(self) -> None:
        await asyncio.sleep(10)

    async def receive(self) -> None:
        self.inverter_writer.write(self.QPIGS)

        response = await self.inverter_reader.readuntil(b'\r')
        if len(response) == 0:
            return None

        try:
            decoded_state = self._decode_state(response)
        except ValueError:
            return None

        self.time_updated = time()
        self.grid_voltage = decoded_state['grid_ac_voltage']
        self.grid_frequency = decoded_state['grid_ac_frequency']
        self.output_voltage = decoded_state['output_ac_voltage']
        self.output_frequency = decoded_state['output_ac_frequency']
        self.load_va = decoded_state['load_va']
        self.load_power = decoded_state['load_power']
        self.load_percentage = decoded_state['load_percentage']
        self.battery_charge_current = decoded_state['battery_charge_current'] if decoded_state['battery_charge_current'] > 0 else -decoded_state['battery_discharge_current']
        self.pv_charge_current = decoded_state['pv_to_battery_charge_current']
        self.pv_input_voltage = decoded_state['pv_voltage']
        self.pv_input_power = decoded_state['pv_input_power']

        await asyncio.sleep(self.POLL_TIME)

    def _decode_state(self, response: bytes) -> dict:
        trimmed_response = response[1:]
        trimmed_response = trimmed_response[:-3]
        response_ascii = trimmed_response.decode('ascii')
        response_parts = response_ascii.split(" ")

        return {
            'grid_ac_voltage': float(response_parts[0]),
            'grid_ac_frequency': float(response_parts[1]),
            'output_ac_voltage': float(response_parts[2]),
            'output_ac_frequency': float(response_parts[3]),
            'load_va': float(response_parts[4]),
            'load_power': float(response_parts[5]),
            'load_percentage': float(response_parts[6]) / 100,
            'battery_voltage': float(response_parts[8]),
            'battery_charge_current': float(response_parts[9]),
            'battery_discharge_current': float(response_parts[15]),
            'pv_to_battery_charge_current': float(response_parts[12]),
            'pv_voltage': float(response_parts[13]),
            'pv_input_power': float(response_parts[19]),
        }
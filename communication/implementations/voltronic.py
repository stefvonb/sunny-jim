from time import time

import serial
import serial_asyncio

import communication
from communication.devices import Inverter, OutputMode, OnOffState
import asyncio
from communication.crc16 import crc16xmodem
from enum import Enum


class VoltronicModes(Enum):
    POWER_ON_MODE = 1
    STANDBY_MODE = 2
    LINE_MODE = 3
    BATTERY_MODE = 4
    FAULT_MODE = 5
    POWER_SAVING_MODE = 6


class KodakOGX548Inverter(Inverter):
    BAUD_RATE: int = 2400
    POLL_TIME: int = 0.5

    MODE_MAP = {
        "P": VoltronicModes.POWER_ON_MODE,
        "S": VoltronicModes.STANDBY_MODE,
        "L": VoltronicModes.LINE_MODE,
        "B": VoltronicModes.BATTERY_MODE,
        "F": VoltronicModes.FAULT_MODE,
        "H": VoltronicModes.POWER_SAVING_MODE
    }

    MODE_BUCKET = {
        VoltronicModes.POWER_ON_MODE: OutputMode.UNKNOWN,
        VoltronicModes.STANDBY_MODE: OutputMode.UNKNOWN,
        VoltronicModes.LINE_MODE: OutputMode.LINE,
        VoltronicModes.BATTERY_MODE: OutputMode.BATTERY,
        VoltronicModes.FAULT_MODE: OutputMode.UNKNOWN,
        VoltronicModes.POWER_SAVING_MODE: OutputMode.UNKNOWN
    }

    def __init__(self, device_id: str, **kwargs):
        super().__init__(device_id)
        try:
            self.serial_port = kwargs['serial_port']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.inverter = None
        self.QPIGS = self.generate_command("QPIGS")
        self.QMOD = self.generate_command("QMOD")
        self.QENF = self.generate_command("QENF")

    def generate_command(self, string_command: str) -> bytes:
        return string_command.encode() + crc16xmodem(string_command.encode()).to_bytes(2, 'big') + b'\r'

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

        qpigs_response = await self.inverter_reader.readuntil(b'\r')
        if len(qpigs_response) == 0:
            return None

        self.inverter_writer.write(self.QMOD)

        qmod_response = await self.inverter_reader.readuntil(b'\r')
        if len(qmod_response) == 0:
            return None

        try:
            decoded_state = self._decode_state(qpigs_response, qmod_response)
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
        self.grid_charge_current = self.battery_charge_current - self.pv_charge_current if self.battery_charge_current > 0 else 0
        self.pv_input_voltage = decoded_state['pv_voltage']
        self.pv_input_power = decoded_state['pv_input_power']
        self.output_mode = self.MODE_BUCKET[decoded_state['mode']]
        self.grid_state = OnOffState.ON if decoded_state['grid_ac_voltage'] > 0 else OnOffState.OFF

        await asyncio.sleep(self.POLL_TIME)

    def _decode_state(self, qpigs_response: bytes, qmod_response: bytes) -> dict:
        trimmed_qpigs_response = qpigs_response[1:]
        trimmed_qpigs_response = trimmed_qpigs_response[:-3]
        response_qpigs_ascii = trimmed_qpigs_response.decode('ascii')
        response_qpigs_parts = response_qpigs_ascii.split(" ")

        trimmed_qmod_response = qmod_response[1:]
        trimmed_qmod_response = trimmed_qmod_response[:-3]
        response_qmod_ascii = trimmed_qmod_response.decode('ascii')
        mode = self.MODE_MAP[response_qmod_ascii]

        return {
            'grid_ac_voltage': float(response_qpigs_parts[0]),
            'grid_ac_frequency': float(response_qpigs_parts[1]),
            'output_ac_voltage': float(response_qpigs_parts[2]),
            'output_ac_frequency': float(response_qpigs_parts[3]),
            'load_va': float(response_qpigs_parts[4]),
            'load_power': float(response_qpigs_parts[5]),
            'load_percentage': float(response_qpigs_parts[6]) / 100,
            'battery_voltage': float(response_qpigs_parts[8]),
            'battery_charge_current': float(response_qpigs_parts[9]),
            'battery_discharge_current': float(response_qpigs_parts[15]),
            'pv_to_battery_charge_current': float(response_qpigs_parts[12]),
            'pv_voltage': float(response_qpigs_parts[13]),
            'pv_input_power': float(response_qpigs_parts[19]),
            'mode': mode,
        }
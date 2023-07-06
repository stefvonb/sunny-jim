from time import time

import serial
import serial_asyncio

import communication
from communication.devices import Inverter, OutputMode, OnOffState, Charger
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

class OutputPriority(Enum):
    UTILITY_FIRST = 0
    SOLAR_FIRST = 1
    SBU_FIRST = 2

class ChargerPriority(Enum):
    UTILITY_FIRST = 0
    SOLAR_FIRST = 1
    SOLAR_AND_UTILITY = 2
    SOLAR_ONLY = 3

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

    SELECTED_MODE_MAP = {
        "0": OutputPriority.UTILITY_FIRST,
        "1": OutputPriority.SOLAR_FIRST,
        "2": OutputPriority.SBU_FIRST
    }

    SELECTED_CHARGER_MAP = {
        "0": ChargerPriority.UTILITY_FIRST,
        "1": ChargerPriority.SOLAR_FIRST,
        "2": ChargerPriority.SOLAR_AND_UTILITY,
        "3": ChargerPriority.SOLAR_ONLY
    }

    MODE_BUCKET = {
        VoltronicModes.POWER_ON_MODE: OutputMode.UNKNOWN,
        VoltronicModes.STANDBY_MODE: OutputMode.UNKNOWN,
        VoltronicModes.LINE_MODE: OutputMode.LINE,
        VoltronicModes.BATTERY_MODE: OutputMode.BATTERY,
        VoltronicModes.FAULT_MODE: OutputMode.UNKNOWN,
        VoltronicModes.POWER_SAVING_MODE: OutputMode.UNKNOWN
    }

    SELECTED_MODE_BUCKET = {
        OutputPriority.UTILITY_FIRST: OutputMode.LINE,
        OutputPriority.SOLAR_FIRST: OutputMode.BATTERY,
        OutputPriority.SBU_FIRST: OutputMode.BATTERY
    }

    CHARGER_MODE_BUCKET = {
        ChargerPriority.UTILITY_FIRST: Charger.GRID_AND_SOLAR,
        ChargerPriority.SOLAR_FIRST: Charger.GRID_AND_SOLAR,
        ChargerPriority.SOLAR_AND_UTILITY: Charger.GRID_AND_SOLAR,
        ChargerPriority.SOLAR_ONLY: Charger.SOLAR
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
        self.QPIRI = self.generate_command("QPIRI")
        self.POP00 = self.generate_command("POP00") # Sets to utility first
        self.POP02 = b'\x50\x4F\x50\x30\x32\xE2\x0B\x0D' # For some reason, the CRC doesn't work here
        self.PCP02 = self.generate_command("PCP02") # Sets charging from solar and utility
        self.PCP03 = self.generate_command("PCP03") # Sets charging from solar only

        self.desired_mode = None # It can take a while to switch modes, so we need to remember what we want to switch to
        self.persisted_mode = None # This is to remember what to switch back to after charging from utility

        self.NAK = b'(NAKss\r'
        self.ACK = b'(ACK9 \r'

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
        async with self.async_lock:
            self.inverter_writer.write(self.QPIGS)

            qpigs_response = await self.inverter_reader.readuntil(b'\r')
            if len(qpigs_response) == 0:
                return None

            self.inverter_writer.write(self.QMOD)

            qmod_response = await self.inverter_reader.readuntil(b'\r')
            if len(qmod_response) == 0:
                return None

            self.inverter_writer.write(self.QPIRI)

            qpiri_response = await self.inverter_reader.readuntil(b'\r')
            if len(qpiri_response) == 0:
                return None

            try:
                decoded_state = self._decode_state(qpigs_response, qmod_response, qpiri_response)
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
            self.selected_mode = self.SELECTED_MODE_BUCKET[decoded_state['output_priority']]
            self.selected_charger = self.CHARGER_MODE_BUCKET[decoded_state['charger_priority']] 

            await asyncio.sleep(self.POLL_TIME)

    def _decode_state(self, qpigs_response: bytes, qmod_response: bytes, qpiri_response: bytes) -> dict:
        trimmed_qpigs_response = qpigs_response[1:]
        trimmed_qpigs_response = trimmed_qpigs_response[:-3]
        response_qpigs_ascii = trimmed_qpigs_response.decode('ascii')
        response_qpigs_parts = response_qpigs_ascii.split(" ")

        trimmed_qmod_response = qmod_response[1:]
        trimmed_qmod_response = trimmed_qmod_response[:-3]
        response_qmod_ascii = trimmed_qmod_response.decode('ascii')
        mode = self.MODE_MAP[response_qmod_ascii]

        trimmed_qpiri_response = qpiri_response[1:]
        trimmed_qpiri_response = trimmed_qpiri_response[:-3]
        response_qpiri_ascii = trimmed_qpiri_response.decode('ascii')
        response_qpiri_parts = response_qpiri_ascii.split(" ")

        output_priority = self.SELECTED_MODE_MAP[response_qpiri_parts[16]]
        charger_priority = self.SELECTED_CHARGER_MAP[response_qpiri_parts[17]]

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
            'output_priority': output_priority,
            'charger_priority': charger_priority
        }


    async def switch_to_line_mode(self) -> bool:
        self.inverter_writer.write(self.POP00)

        pop00_response = await self.inverter_reader.readuntil(b'\r')
        if pop00_response == self.ACK:
            self.desired_mode = OutputMode.LINE
            return True

        return False

    async def switch_to_battery_mode(self) -> bool:
        self.inverter_writer.write(self.POP02)

        pop02_response = await self.inverter_reader.readuntil(b'\r')
        if pop02_response == self.ACK:
            self.desired_mode = OutputMode.BATTERY
            return True
        
        return False

    async def turn_on_grid_charging(self, current: int = None) -> bool:
        if current:
            actual_current = self.get_closest_charge_current(current)
            command = self.generate_command(f"MUCHGC{actual_current:03d}")
            self.inverter_writer.write(command)
            response = await self.inverter_reader.readuntil(b'\r')
            if response != self.ACK:
                self.log.error("Failed to change grid charging current. Keeping at previous value.")
            else:
                message = f"Changed grid charging current to {actual_current}A."
                if current != actual_current:
                    message += f" (requested {current}A, but closest is {actual_current}A...)"
                self.log.info(message)

        self.persisted_mode = self.desired_mode

        if not await self.switch_to_line_mode():
            return False

        self.inverter_writer.write(self.PCP02)

        pcp02_response = await self.inverter_reader.readuntil(b'\r')
        if pcp02_response == self.ACK:
            return True
        
        return False

    async def turn_off_grid_charging(self) -> bool:
        if self.persisted_mode == OutputMode.BATTERY:
            if not await self.switch_to_battery_mode():
                self.log.error("Failed to switch back to battery mode after grid charging.")
            
        self.inverter_writer.write(self.PCP03)

        pcp03_response = await self.inverter_reader.readuntil(b'\r')
        if pcp03_response == self.ACK:
            return True
        
        return False


    def get_closest_charge_current(self, input_charge_current: int):
        available_values = [2, 10, 20, 30, 40, 50]
        return min(available_values, key=lambda x:abs(x-input_charge_current))
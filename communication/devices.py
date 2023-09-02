import abc
import logging
import time
from abc import abstractmethod, ABC
from typing import List
import asyncio
from enum import Enum

from communication.observers import DeviceObserver


class DeviceType(Enum):
    UNSPECIFIED = "unspecified"
    INVERTER = "inverter"
    BATTERY = "battery"


class OnOffState(Enum):
    ON = "on"
    OFF = "off"


class OutputMode(Enum):
    LINE = "line"
    BATTERY = "battery"
    UNKNOWN = "unknown"


class Charger(Enum):
    GRID = "grid"
    SOLAR = "solar"
    GRID_AND_SOLAR = "grid+solar"
    OFF = "off"
    UNKNOWN = "unknown"


class CommandType(Enum):
    SWITCH_TO_LINE_MODE = "switch_to_line_mode"
    SWITCH_TO_BATTERY_MODE = "switch_to_battery_mode"
    TURN_ON_GRID_CHARGING = "turn_on_grid_charging"
    TURN_OFF_GRID_CHARGING = "turn_off_grid_charging"


class Device(abc.ABC):
    time_updated: float = 0

    connected: bool = False
    running: bool = False

    _observers: list[DeviceObserver]

    # Since these are very device specific, they are constants on the device classes
    # They can be overridden for different device implementations which might behave differently
    NUM_RECONNECTION_TRIALS: int = 5
    RECONNECTION_TRIAL_INTERVAL: int = 1

    device_type: DeviceType = DeviceType.UNSPECIFIED
    device_id: str

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.log = logging.getLogger(self.device_id)
        self._observers = []
        self.async_lock = asyncio.Lock()

    async def connect(self) -> None:
        self.connected = await self.try_connect()

    @abstractmethod
    async def try_connect(self) -> bool:
        pass

    async def disconnect(self) -> None:
        self.connected = not await self.try_disconnect()

    @abstractmethod
    async def try_disconnect(self) -> bool:
        pass

    async def try_reconnect(self):
        self.log.info("Attempting to reconnect device...")
        for n_trial in range(self.NUM_RECONNECTION_TRIALS):
            await self.reconnect()
            if self.connected:
                self.log.info("Successfully reconnected device.")
                return
            else:
                self.log.warning(f"Failed to reconnect device on trial {n_trial + 1}.")
                time.sleep(self.RECONNECTION_TRIAL_INTERVAL)

        self.log.error(f"Device failed to connect after {self.NUM_RECONNECTION_TRIALS} trials.")

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    @abstractmethod
    async def send(self) -> None:
        pass

    @abstractmethod
    async def receive(self) -> None:
        pass

    async def send_loop(self) -> None:
        while self.running:
            await self.send()

    async def receive_loop(self) -> None:
        while self.running:
            await self.receive()
            await self.notify_observers()

    async def run(self) -> None:
        self.running = True

        # Await both the send and receive loop tasks
        await asyncio.gather(self.send_loop(), self.receive_loop())

    def stop(self) -> None:
        self.running = False

    def get_state_dictionary(self) -> dict:
        return {"time_updated": self.time_updated}

    def get_information_dictionary(self) -> dict:
        return {"device_id": self.device_id,
                "device_type": self.device_type.value}

    async def notify_observers(self, modifier=None):
        for observer in self._observers:
            if observer != modifier:
                await observer.update(self)

    def attach_observer(self, observer: DeviceObserver):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: DeviceObserver):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    @abstractmethod
    def get_available_commands(self) -> dict[CommandType, callable]:
        pass

    async def try_run_command(self, command: CommandType, *args: tuple) -> bool:
        available_commands = self.get_available_commands()
        if command not in available_commands:
            self.log.error(f"{command.value} is not available for this device.")
            return False

        async with self.async_lock:
            return await available_commands[command](*args)


class Battery(Device, ABC):
    voltage: float = None
    current: float = None
    state_of_charge: float = None
    state_of_health: float = None
    cell_voltages: List[float] = None
    temperatures: List[float] = None

    device_type: DeviceType = DeviceType.BATTERY

    def get_state_dictionary(self):
        state_dictionary = super().get_state_dictionary()
        if any(e is None for e in [self.voltage, self.current, self.state_of_charge, self.state_of_health,
                                   self.cell_voltages, self.temperatures]):
            return None

        state_dictionary["voltage"] = self.voltage
        state_dictionary["current"] = self.current
        state_dictionary["state_of_charge"] = self.state_of_charge
        state_dictionary["state_of_health"] = self.state_of_health
        for i, cell_voltage in enumerate(self.cell_voltages):
            state_dictionary[f"voltage_cell_{i + 1}"] = cell_voltage
        for i, temperature in enumerate(self.temperatures):
            state_dictionary[f"temperature_{i + 1}"] = temperature

        return state_dictionary

    def get_available_commands(self) -> dict[CommandType, callable]:
        return {}


class Inverter(Device, ABC):
    grid_voltage: float = None
    grid_frequency: float = None
    output_voltage: float = None
    output_frequency: float = None
    load_power: float = None
    load_va: float = None
    load_percentage: float = None
    battery_charge_current: float = None
    grid_charge_current: float = None
    pv_charge_current: float = None
    pv_input_voltage: float = None
    pv_input_power: float = None
    grid_state: OnOffState = None
    output_mode: OutputMode = None
    selected_mode: OutputMode = None
    selected_charger: Charger = None

    device_type: DeviceType = DeviceType.INVERTER

    def get_state_dictionary(self):
        state_dictionary = super().get_state_dictionary()
        if any(e is None for e in [self.grid_voltage, self.grid_frequency, self.output_voltage, self.output_frequency,
                                   self.load_power, self.load_va, self.load_percentage, self.battery_charge_current,
                                   self.grid_charge_current, self.pv_charge_current, self.pv_input_voltage,
                                   self.pv_input_power, self.grid_state, self.output_mode, self.selected_mode,
                                   self.selected_charger]):
            return None

        state_dictionary["grid_voltage"] = self.grid_voltage
        state_dictionary["grid_frequency"] = self.grid_frequency
        state_dictionary["output_voltage"] = self.output_voltage
        state_dictionary["output_frequency"] = self.output_frequency
        state_dictionary["load_power"] = self.load_power
        state_dictionary["load_va"] = self.load_va
        state_dictionary["load_percentage"] = self.load_percentage
        state_dictionary["battery_charge_current"] = self.battery_charge_current
        state_dictionary["grid_charge_current"] = self.grid_charge_current
        state_dictionary["pv_charge_current"] = self.pv_charge_current
        state_dictionary["pv_input_voltage"] = self.pv_input_voltage
        state_dictionary["pv_input_power"] = self.pv_input_power
        state_dictionary["grid_state"] = self.grid_state.value
        state_dictionary["output_mode"] = self.output_mode.value
        state_dictionary["selected_mode"] = self.selected_mode.value
        state_dictionary["selected_charger"] = self.selected_charger.value

        return state_dictionary

    @abstractmethod
    async def switch_to_line_mode(self) -> bool:
        pass

    @abstractmethod
    async def switch_to_battery_mode(self) -> bool:
        pass

    @abstractmethod
    async def turn_on_grid_charging(self, current: int = None) -> bool:
        pass

    @abstractmethod
    async def turn_off_grid_charging(self) -> bool:
        pass

    def get_available_commands(self) -> dict[CommandType, callable]:
        return {CommandType.SWITCH_TO_LINE_MODE: self.switch_to_line_mode,
                CommandType.SWITCH_TO_BATTERY_MODE: self.switch_to_battery_mode,
                CommandType.TURN_ON_GRID_CHARGING: self.turn_on_grid_charging,
                CommandType.TURN_OFF_GRID_CHARGING: self.turn_off_grid_charging}


class DeviceInitialisationError(Exception):
    pass

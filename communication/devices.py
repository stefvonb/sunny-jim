import abc
import logging
import threading
import time
from abc import abstractmethod, ABC
from typing import List

from communication.observers import DeviceObserver


class Device(abc.ABC):
    time_updated: float = 0
    threads: List[threading.Thread] = None

    connected: bool = False
    running: bool = False

    _observers: List[DeviceObserver] = []

    # Since these are very device specific, they are constants on the device classes
    # They can be overridden for different device implementations which might behave differently
    NUM_RECONNECTION_TRIALS: int = 5
    RECONNECTION_TRIAL_INTERVAL: int = 1

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def connect(self) -> None:
        self.connected = self.try_connect()

    @abstractmethod
    def try_connect(self) -> bool:
        pass

    def disconnect(self) -> None:
        self.connected = not self.try_disconnect()

    @abstractmethod
    def try_disconnect(self) -> bool:
        pass

    def try_reconnect(self):
        self.log.info("Attempting to reconnect device...")
        for n_trial in range(self.NUM_RECONNECTION_TRIALS):
            self.reconnect()
            if self.connected:
                self.log.info("Successfully reconnected device.")
                return
            else:
                self.log.warning(f"Failed to reconnect device on trial {n_trial + 1}.")
                time.sleep(self.RECONNECTION_TRIAL_INTERVAL)

        self.log.error(f"Device failed to connect after {self.NUM_RECONNECTION_TRIALS} trials.")

    def reconnect(self) -> None:
        self.disconnect()
        self.connect()

    def run(self) -> None:
        self.running = True

        if self.threads is None:
            self.log.error("Monitoring thread function(s) not defined.")
            self.running = False
            return
        for thread in self.threads:
            thread.start()

    def stop(self) -> None:
        self.running = False

    def get_state_dictionary(self) -> dict:
        return {"time_updated": self.time_updated}

    def notify_observers(self, modifier=None):
        for observer in self._observers:
            if observer != modifier:
                observer.update(self)

    def attach_observer(self, observer: DeviceObserver):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: DeviceObserver):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass


class Battery(Device, ABC):
    voltage: float = None
    current: float = None
    state_of_charge: float = None
    state_of_health: float = None
    cell_voltages: List[float] = None
    temperatures: List[float] = None

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
            state_dictionary[f"voltage_cell_{i+1}"] = cell_voltage
        for i, temperature in enumerate(self.temperatures):
            state_dictionary[f"temperature_{i+1}"] = temperature

        return state_dictionary


class Inverter(Device, ABC):
    pass


class DeviceInitialisationError(Exception):
    pass

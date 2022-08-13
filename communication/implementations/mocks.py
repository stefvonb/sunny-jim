import random
import threading
import time

import communication
from communication.devices import Battery


class MockBattery(Battery):
    UPDATE_INTERVAL: int

    def __init__(self, **kwargs):
        super().__init__()

        try:
            self.voltage_value = kwargs['voltage_value']
            self.current_value = kwargs['current_value']
            self.soc_value = kwargs['soc_value']
            self.soh_value = kwargs['soh_value']
            self.cell_voltage_value = kwargs['cell_voltage_value']
            self.temperature_value = kwargs['temperature_value']
            self.num_cells = kwargs['num_cells']
        except KeyError as key_error:
            raise communication.devices.DeviceInitialisationError(f"Missing field: {key_error}")

        self.UPDATE_INTERVAL = 1

        update_thread = threading.Thread(target=self.__update_state)
        self.threads = [update_thread]
        self.thread_lock = threading.Lock()

    def try_connect(self) -> bool:
        return True

    def try_disconnect(self) -> bool:
        return True

    def __update_state(self):
        while self.running:
            time.sleep(self.UPDATE_INTERVAL)
            with self.thread_lock:
                self.time_updated = time.time()
                self.voltage = MockBattery.random_one_percent(self.voltage_value)
                self.current = MockBattery.random_one_percent(self.current_value)
                self.state_of_charge = MockBattery.random_one_percent(self.soc_value)
                self.state_of_health = self.soh_value
                self.cell_voltages = [MockBattery.random_one_percent(self.cell_voltage_value) for _ in
                                      range(self.num_cells)]
                self.temperatures = [MockBattery.random_one_percent(self.temperature_value)]
            self.notify_observers()

    @staticmethod
    def random_one_percent(number: float):
        random_number = random.random()
        one_percent_of = 0.01 * number
        plus_minus = random.choice([-1, 1])
        return float(round(number + plus_minus * (one_percent_of * random_number), 2))

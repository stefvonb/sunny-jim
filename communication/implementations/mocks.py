import random
import time
import asyncio

import communication
from communication.devices import Battery, Inverter, OutputMode, Charger, OnOffState


def random_one_percent(number: float):
    random_number = random.random()
    one_percent_of = 0.01 * number
    plus_minus = random.choice([-1, 1])
    return float(round(number + plus_minus * (one_percent_of * random_number), 2))


class MockBattery(Battery):
    UPDATE_INTERVAL: int

    def __init__(self, device_id: str, **kwargs):
        super().__init__(device_id)

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
        self.charge_direction = -1
        self.low_soc = 0.1
        self.high_soc = 0.6
        self.state_of_charge = self.soc_value

    async def try_connect(self) -> bool:
        return True

    async def try_disconnect(self) -> bool:
        return True

    async def receive(self):
        await asyncio.sleep(self.UPDATE_INTERVAL)
        self.time_updated = time.time()
        self.voltage = random_one_percent(self.voltage_value)
        self.current = random_one_percent(self.current_value)
        self.state_of_charge = self.state_of_charge + 0.01 * self.charge_direction
        self.state_of_health = self.soh_value
        self.cell_voltages = [random_one_percent(self.cell_voltage_value) for _ in
                              range(self.num_cells)]
        self.temperatures = [random_one_percent(self.temperature_value)]

        if self.state_of_charge <= self.low_soc:
            self.charge_direction = 1
        elif self.state_of_charge >= self.high_soc:
            self.charge_direction = -1

    async def send(self):
        # Do nothing
        await asyncio.sleep(self.UPDATE_INTERVAL)


class MockInverter(Inverter):
    def __init__(self, device_id: str):
        super().__init__(device_id)
        self.selected_mode = OutputMode.BATTERY
        self.selected_charger = Charger.SOLAR
        self.grid_state = OnOffState.ON

    async def switch_to_line_mode(self) -> bool:
        self.selected_mode = OutputMode.LINE
        return True

    async def switch_to_battery_mode(self) -> bool:
        self.selected_mode = OutputMode.BATTERY
        return True

    async def turn_on_grid_charging(self, current: int = None) -> bool:
        self.selected_charger = Charger.GRID
        return True

    async def turn_off_grid_charging(self) -> bool:
        self.selected_charger = Charger.SOLAR
        return True

    async def try_connect(self) -> bool:
        return True

    async def try_disconnect(self) -> bool:
        return True

    async def send(self) -> None:
        # Using this as a mechanism to change the grid state
        await asyncio.sleep(30)
        self.grid_state = OnOffState.OFF
        await asyncio.sleep(30)
        self.grid_state = OnOffState.ON

    async def receive(self) -> None:
        self.time_updated = time.time()
        self.grid_voltage = random_one_percent(230)
        self.grid_frequency = random_one_percent(50)
        self.output_voltage = random_one_percent(230)
        self.output_frequency = random_one_percent(50)
        self.load_va = random_one_percent(1000)
        self.load_power = random_one_percent(900)
        self.load_percentage = random_one_percent(0.25)
        self.battery_charge_current = random_one_percent(10)
        self.pv_charge_current = random_one_percent(3)
        self.grid_charge_current = self.battery_charge_current - self.pv_charge_current \
            if self.battery_charge_current > 0 else 0
        self.pv_input_voltage = random_one_percent(150)
        self.pv_input_power = random_one_percent(500)
        self.output_mode = self.selected_mode

        await asyncio.sleep(1)

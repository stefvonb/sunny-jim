from fastapi import FastAPI, HTTPException
from device_daemon import DeviceDaemon
from communication.devices import DeviceType, CommandType
from data_management.data_interface import DataInterface

def running_devices(daemon: DeviceDaemon):
    return daemon.running_devices

def inverter_candidate(daemon: DeviceDaemon):
    inverter_candidates = [device for device in running_devices(daemon).values() if device.get_information_dictionary()["device_type"] == DeviceType.INVERTER.value]
    if len(inverter_candidates) == 0:
        raise HTTPException(status_code=404, detail="No inverter devices found.")

    return inverter_candidates[0]

def battery_candidate(daemon: DeviceDaemon):
    battery_candidates = [device for device in running_devices(daemon).values() if device.get_information_dictionary()["device_type"] == DeviceType.BATTERY.value]
    if len(battery_candidates) == 0:
        raise HTTPException(status_code=404, detail="No battery devices found.")

    return battery_candidates[0]

def device_from_key(device_key: str, daemon: DeviceDaemon):
    if device_key not in running_devices(daemon):
        if device_key == "inverter":
            device = inverter_candidate(daemon)
        elif device_key == "battery":
            device = battery_candidate(daemon)
        else:
            raise HTTPException(status_code=404, detail=f"Device {device_key} not found.")

    else:
        device = running_devices(daemon)[device_key]

    return device

def register_device_endpoints(app: FastAPI, daemon: DeviceDaemon) -> None:
    @app.get("/devices/")
    async def get_devices():
        return_dict = {
            device_key: device.get_information_dictionary() for device_key, device in running_devices(daemon).items()
        }
        return return_dict

    @app.get("/devices/{device_key}/")
    async def get_device(device_key: str):
        device = device_from_key(device_key, daemon)

        return_dictionary = {
            "device_info": device.get_information_dictionary(),
            "device_state": device.get_state_dictionary()
        }

        return return_dictionary

    @app.get("/devices/control/available_commands/{device_key}/")
    async def get_available_commands(device_key: str):
        device = device_from_key(device_key, daemon)

        return [command.name for command in device.get_available_commands().keys()]

    @app.put("/devices/control/{device_key}/{command}/")
    async def control_device(device_key: str, command: str):
        device = device_from_key(device_key, daemon)

        command_success = await device.try_run_command(CommandType[command])
        if not command_success:
            raise HTTPException(status_code=400, detail=f"Command {command} failed for device {device_key}.")

        return {"success": True}

    @app.put("/devices/control/charge_inverter_from_grid/")
    async def charge_inverter_from_grid(charge_current: int):
        inverter = inverter_candidate(daemon)

        command_success = await inverter.try_run_command(CommandType.TURN_ON_GRID_CHARGING, charge_current)
        if not command_success:
            raise HTTPException(status_code=400, detail=f"Command CHARGE_FROM_GRID failed for device {inverter}.")

        return {"success": True}

def register_data_endpoints(app: FastAPI, data_interface: DataInterface, daemon: DeviceDaemon) -> None:
    @app.get("/data/{device_key}/past_minutes/")
    async def get_past_minutes(device_key: str, minutes: int, columns: str = None):
        device = device_from_key(device_key, daemon)

        if columns:
            columns = columns.split(",")

        result = await data_interface.get_last_n_minutes(device.device_id, minutes, columns)

        if len(result) == 0:
            raise HTTPException(status_code=404, detail=f"No data found for device {device_key}.")

        return result
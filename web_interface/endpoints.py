from fastapi import FastAPI, HTTPException
from device_daemon import DeviceDaemon
from communication.devices import DeviceType, CommandType

def register_device_endpoints(app: FastAPI, daemon: DeviceDaemon) -> None:
    def running_devices():
        return daemon.running_devices

    def inverter_candidate():
        inverter_candidates = [device for device in running_devices().values() if device.get_information_dictionary()["device_type"] == DeviceType.INVERTER.value]
        if len(inverter_candidates) == 0:
            raise HTTPException(status_code=404, detail="No inverter devices found.")

        return inverter_candidates[0]

    def battery_candidate():
        battery_candidates = [device for device in running_devices().values() if device.get_information_dictionary()["device_type"] == DeviceType.BATTERY.value]
        if len(battery_candidates) == 0:
            raise HTTPException(status_code=404, detail="No battery devices found.")

        return battery_candidates[0]

    def device_from_key(device_key: str):
        if device_key not in running_devices():
            if device_key == "inverter":
                device = inverter_candidate()
            elif device_key == "battery":
                device = battery_candidate()
            else:
                raise HTTPException(status_code=404, detail=f"Device {device_key} not found.")

        else:
            device = running_devices()[device_key]

        return device

    @app.get("/devices/")
    async def get_devices():
        return_dict = {
            device_key: device.get_information_dictionary() for device_key, device in running_devices().items()
        }
        return return_dict

    @app.get("/devices/{device_key}/")
    async def get_device(device_key: str):
        device = device_from_key(device_key)

        return_dictionary = {
            "device_info": device.get_information_dictionary(),
            "device_state": device.get_state_dictionary()
        }

        return return_dictionary

    @app.get("/devices/control/available_commands/{device_key}/")
    async def get_available_commands(device_key: str):
        device = device_from_key(device_key)

        return [command.name for command in device.get_available_commands().keys()]

    @app.put("/devices/control/{device_key}/{command}/")
    async def control_device(device_key: str, command: str):
        device = device_from_key(device_key)

        command_success = await device.try_run_command(CommandType[command])
        if not command_success:
            raise HTTPException(status_code=400, detail=f"Command {command} failed for device {device_key}.")

        return {"success": True}

    @app.put("/devices/control/charge_inverter_from_grid/")
    async def charge_inverter_from_grid(charge_current: int):
        inverter = inverter_candidate()

        command_success = await inverter.try_run_command(CommandType.TURN_ON_GRID_CHARGING, charge_current)
        if not command_success:
            raise HTTPException(status_code=400, detail=f"Command CHARGE_FROM_GRID failed for device {inverter}.")

        return {"success": True}
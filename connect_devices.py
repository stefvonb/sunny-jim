import logging
import time
from typing import Dict, Tuple
import configuration
from communication.devices import DeviceInitialisationError, Device
from communication.observers import PrintObserver
from configuration import config
import importlib

log = logging.getLogger("connect_devices")
configuration.configure_logging()


def initialise_devices() -> Dict[str, Device]:
    devices_module = importlib.import_module("communication")
    initialised_devices = {}

    for device_key, device_setup in config['devices'].items():
        if device_key in initialised_devices:
            log.error(f"Duplicate device key found in config file: {device_key}")
            continue

        if "type" not in device_setup:
            log.error(f"Missing field for device {device_key}: type")
            continue

        log.info(f"Attempting to initialise device {device_key}...")

        device_class = getattr(devices_module, device_setup["type"])
        constructor_parameters = {k: v for k, v in device_setup.items() if k != "type"}

        try:
            initialised_devices[device_key] = device_class(**constructor_parameters)
        except DeviceInitialisationError as error:
            log.error(f"Problem initialising device {device_key}: {error}")
            continue

        # We change the name of the logger to the device key, to help us debug
        initialised_devices[device_key].log.name = device_key
        log.info(f"Successfully initialised device {device_key}")

    return initialised_devices


def connect_device(device_info: Tuple[str, Device]) -> Device:
    device_key = device_info[0]
    device = device_info[1]

    log.info(f"Attempting to connect device {device_key}...")

    for trial in range(config['connections']['num_connection_tries']):
        device.connect()
        if device.connected:
            log.info(f"Successfully connected device {device_key}.")
            return device
        else:
            log.warning("Failed to connect device, trying again...")
            time.sleep(config['connections']['stall_time'])

    log.error(f"Failed to connect device {device_key}.")


def run_devices() -> Dict[str, Device]:
    initialised_devices = initialise_devices()

    connected_devices = {}
    for device_info in initialised_devices.items():
        connected_device = connect_device(device_info)
        if connected_device is not None:
            connected_devices[device_info[0]] = connected_device
            connected_device.run()

    return connected_devices


if __name__ == "__main__":
    running_devices = run_devices()

    if len(running_devices) == 0:
        log.error("No devices running!")

    else:
        for device in running_devices.values():
            device.attach_observer(PrintObserver())
        time.sleep(100)
        for device in running_devices.values():
            device.stop()

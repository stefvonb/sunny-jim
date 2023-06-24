from .devices import Device
from .observers import CsvFileLoggingObserver, PrintObserver, WebsocketServer, WebsocketObserver
import asyncio

def attach_observers(devices: dict[str, Device], config: dict):
    async_tasks = []

    for device_id, device in devices.items():
        if "csv_data_logging" in config:
            attach_csv_file_logging_observer(device, device_id, config)

        if "print_updates" in config and config["print_updates"]:
            device.attach_observer(PrintObserver())

        if "websocket_streaming" in config:
            message_queue = asyncio.Queue()
            websocket_server = WebsocketServer(config["websocket_streaming"]["host"],
                                               config["websocket_streaming"]["port"], message_queue)
            device.attach_observer(WebsocketObserver(device_id, message_queue))
            async_tasks.append(websocket_server.run_server())

    return async_tasks

def attach_csv_file_logging_observer(device: Device, device_id: str, config: dict):
    device.attach_observer(CsvFileLoggingObserver(config["csv_data_logging"]["base_filepath"], device_id,
                                                  config["csv_data_logging"]["lines_per_file"]))

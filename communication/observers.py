import abc
import csv
import datetime
import os
import asyncio
import logging

log = logging.getLogger("Observers")

class DeviceObserver(abc.ABC):
    @abc.abstractmethod
    def update(self, device):
        pass


class PrintObserver(DeviceObserver):
    def update(self, device):
        print(device.get_state_dictionary())


class CsvFileLoggingObserver(DeviceObserver):
    def __init__(self, base_filepath: str, device_id: str, lines_per_file: int):
        self.base_filepath = base_filepath
        self.device_id = device_id
        log.info(f"Creating CSV observer for device '{device_id}' with base file path '{base_filepath}'...")
        self.lines_per_file = lines_per_file

        self.current_file = None
        self.csv_writer = None
        self.current_line_count = 0

        os.makedirs(base_filepath, exist_ok=True)

    def get_filename(self) -> str:
        current_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{current_datetime}_{self.device_id}.csv"
        return os.path.join(self.base_filepath, filename)

    def open_new_file(self, file_headers):
        if self.current_file:
            self.current_file.close()

        self.current_file = open(self.get_filename(), 'w')
        self.csv_writer = csv.DictWriter(self.current_file, fieldnames=file_headers)
        self.csv_writer.writeheader()

    def update(self, device):
        device_state = device.get_state_dictionary()

        if not device_state:
            return

        if self.current_file is None or self.current_line_count >= self.lines_per_file:
            headers = device_state.keys()
            self.open_new_file(headers)
            self.current_line_count = 0

        self.csv_writer.writerow(device_state)
        self.current_line_count += 1

    def __del__(self):
        if self.current_file is not None:
            self.current_file.close()
            

class WebsocketStreamingObserver(DeviceObserver):
    def __init__(self, websocket):
        self.websocket = websocket
        log.info("Registering device to websocket server...")


    async def async_update(self, device):
        device_state = device.get_state_dictionary()

        if not device_state:
            return

        await self.websocket.send(device_state)

    def update(self, device):
        asyncio.run(self.async_update(device))

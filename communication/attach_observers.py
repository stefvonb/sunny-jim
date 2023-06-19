from .devices import Device
from .observers import CsvFileLoggingObserver

def attach_observers(devices: dict[str, Device], config: dict):
    for device_id, device in devices.items():
        if config["csv_data_logging"]:
            attach_csv_file_logging_observer(device, device_id, config)


def attach_csv_file_logging_observer(device: Device, device_id: str, config: dict):
    device.attach_observer(CsvFileLoggingObserver(config["csv_data_logging"]["base_filepath"], device_id,
                                                  config["csv_data_logging"]["lines_per_file"]))
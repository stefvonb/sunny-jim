from .devices import Device
from .observers import CsvFileLoggingObserver, PrintObserver

def attach_observers(devices: dict[str, Device], config: dict):
    for device_id, device in devices.items():
        if "csv_data_logging" in config:
            attach_csv_file_logging_observer(device, device_id, config)

        if "print_updates" in config and config["print_updates"]:
            device.attach_observer(PrintObserver())


def attach_csv_file_logging_observer(device: Device, device_id: str, config: dict):
    device.attach_observer(CsvFileLoggingObserver(config["csv_data_logging"]["base_filepath"], device_id,
                                                  config["csv_data_logging"]["lines_per_file"]))

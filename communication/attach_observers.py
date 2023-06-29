from .devices import Device
from .observers import CsvFileLoggingObserver, PrintObserver, WebsocketServer, WebsocketObserver, SQLDatabaseObserver, SQLSession
import asyncio

def attach_observers(devices: dict[str, Device], config: dict):
    async_tasks = []
    stop_functions = []

    if "print_updates" in config and config["print_updates"]:
        [device.attach_observer(PrintObserver()) for device in devices.values()]

    if "csv_data_logging" in config:
        [attach_csv_file_logging_observer(device, device_id, config) for device_id, device in devices.items()]

    if "websocket_streaming" in config:
        websocket_message_queue = asyncio.Queue()
        websocket_server = WebsocketServer(config["websocket_streaming"]["host"],
                                           config["websocket_streaming"]["port"], websocket_message_queue)
        [device.attach_observer(WebsocketObserver(device_id, websocket_message_queue)) for device_id, device in devices.items()]
        async_tasks.append(websocket_server.run_server())
        stop_functions.append(websocket_server.stop)

    if "sql_database" in config:
        sql_message_queue = asyncio.Queue()
        connection_string = f'{config["sql_database"]["sql_type"]}:///{config["sql_database"]["database_name"]}'
        sql_session = SQLSession(connection_string, sql_message_queue)
        [device.attach_observer(SQLDatabaseObserver(device_id, sql_message_queue, sql_session.metadata, sql_session.ready)) for device_id, device in devices.items()]
        async_tasks.append(sql_session.run_session())
        stop_functions.append(sql_session.stop)

    return async_tasks, stop_functions

def attach_csv_file_logging_observer(device: Device, device_id: str, config: dict):
    device.attach_observer(CsvFileLoggingObserver(config["csv_data_logging"]["base_filepath"], device_id,
                                                  config["csv_data_logging"]["lines_per_file"]))

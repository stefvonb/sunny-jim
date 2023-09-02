from .devices import Device, DeviceType
from .observers import CsvFileLoggingObserver, PrintObserver, WebsocketServer, WebsocketObserver, SQLDatabaseObserver, \
    SQLSession, GridChangeNotificationObserver, LowBatteryNotificationObserver
import asyncio
from data_management import sql_utilities


def attach_observers(devices: dict[str, Device], config: dict):
    async_tasks = []
    stop_functions = []

    if "print_updates" in config and config["print_updates"]:
        [device.attach_observer(PrintObserver()) for device in devices.values()]

    if "csv_data_logging" in config:
        [attach_csv_file_logging_observer(device, device_id, config) for device_id, device in devices.items()]

    if "websocket_streaming" in config:
        websocket_message_queue = asyncio.Queue()
        websocket_server = WebsocketServer("0.0.0.0", config["websocket_streaming"]["port"], websocket_message_queue)
        [device.attach_observer(WebsocketObserver(device_id, websocket_message_queue)) for device_id, device in
         devices.items()]
        async_tasks.append(websocket_server.run_server())
        stop_functions.append(websocket_server.stop)

    if "sql_database" in config:
        sql_message_queue = asyncio.Queue()
        connection_string = sql_utilities.get_sql_connection_string(config["sql_database"]["sql_driver"],
                                                                    config["sql_database"]["database_path"])
        sql_session = SQLSession(connection_string, sql_message_queue)
        [device.attach_observer(
            SQLDatabaseObserver(device_id, sql_message_queue, sql_session.metadata, sql_session.ready)) for
         device_id, device in devices.items()]
        async_tasks.append(sql_session.run_session())
        stop_functions.append(sql_session.stop)

    if "notifications" in config:
        webhook_endpoint = f"{config['notifications']['host']}/{config['notifications']['topic']}"
        icon_url = f"{config['web_interface']['protocol']}://{config['web_interface']['host']}:{config['web_interface']['port']}/static/favicon.png"

        if "grid_change_notifications" in config["notifications"] and config["notifications"]["grid_change_notifications"]:
            for device_id, device in devices.items():
                if device.device_type == DeviceType.INVERTER:
                    device.attach_observer(GridChangeNotificationObserver(device_id, webhook_endpoint, icon_url))

        if "low_battery_notifications" in config["notifications"] and config["notifications"]["low_battery_notifications"]:
            for device_id, device in devices.items():
                if device.device_type == DeviceType.BATTERY:
                    if "low_battery_level_percentage" not in config["notifications"]:
                        raise ValueError("Missing low battery level in config")
                    low_battery_level = config["notifications"]["low_battery_level_percentage"]
                    if "switch_action" in config["notifications"]:
                        switch_action = f"http, Switch to line mode, {config['web_interface']['protocol']}://{config['web_interface']['host']}:{config['web_interface']['port']}/{config['notifications']['switch_action']}"
                    else:
                        switch_action = None
                    device.attach_observer(LowBatteryNotificationObserver(device_id, webhook_endpoint, low_battery_level,
                                                                          switch_action, icon_url))

    return async_tasks, stop_functions


def attach_csv_file_logging_observer(device: Device, device_id: str, config: dict):
    device.attach_observer(CsvFileLoggingObserver(config["csv_data_logging"]["base_filepath"], device_id,
                                                  config["csv_data_logging"]["lines_per_file"]))

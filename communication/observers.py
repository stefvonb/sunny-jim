import abc
import csv
import datetime
import os
import asyncio
import logging
from abc import ABC

import websockets
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Table, String, Column, Integer, Float, MetaData, insert, event, text
from sqlalchemy.schema import CreateTable
from data_management import sql_utilities
import aiohttp

log = logging.getLogger("Observers")


class DeviceObserver(abc.ABC):
    @abc.abstractmethod
    async def update(self, device):
        pass


class PrintObserver(DeviceObserver):
    async def update(self, device):
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

    async def update(self, device):
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


class WebsocketServer:
    def __init__(self, host: str, port: int, shared_queue: asyncio.Queue):
        self.host = host
        self.port = port
        self.connections = set()
        self.message_queue = shared_queue
        self.running = True

    async def register_connection(self, websocket):
        self.connections.add(websocket)
        log.info(f"New connection from {websocket.remote_address}")
        try:
            await websocket.wait_closed()
        finally:
            self.connections.remove(websocket)

    async def run_server(self):
        log.info(f"Starting websocket server at ws://{self.host}:{self.port}...")
        async with websockets.serve(self.register_connection, self.host, self.port, ping_interval=None):
            while self.running:
                message = await self.message_queue.get()
                if message is None:
                    continue
                for connection in self.connections:
                    try:
                        await connection.send(message)
                    except websockets.ConnectionClosed:
                        log.info("Websocket connection terminated...")

    async def stop(self):
        for connection in list(self.connections):
            await connection.close()

        self.running = False
        self.message_queue.put_nowait(None)


class WebsocketObserver(DeviceObserver):
    def __init__(self, device_id: str, shared_queue: asyncio.Queue):
        self.device_id = device_id
        self.message_queue = shared_queue

    async def update(self, device):
        device_info = device.get_information_dictionary()
        device_state = device.get_state_dictionary()

        if not device_state:
            return

        json_message = {"device_info": device_info, "device_state": device_state}

        message = json.dumps(json_message)
        await self.message_queue.put(message)


class SQLSession:
    def __init__(self, sql_connection_string: str, shared_queue: asyncio.Queue):
        self.engine = create_async_engine(sql_connection_string)
        self.metadata = MetaData()
        self.running = True
        self.statement_queue = shared_queue
        self.ready = [False]

        # This is quite janky, but let's see if it works
        if "sqlite" in sql_connection_string:
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

    async def run_session(self):
        log.info(f"Starting SQL session with engine '{self.engine.name}'...")
        async with self.engine.begin() as connection:
            await connection.run_sync(self.metadata.create_all)
            await connection.run_sync(self.metadata.reflect, views=True)

            self.ready[0] = True

        while self.running:
            statement = await self.statement_queue.get()
            if statement is None:
                continue
            async with self.engine.begin() as connection:
                await connection.execute(statement)

    async def stop(self):
        self.running = False
        self.statement_queue.put_nowait(None)


class SQLDatabaseObserver(DeviceObserver):
    def __init__(self, device_id: str, shared_queue: asyncio.Queue, sql_metadata: MetaData, ready: list[bool]):
        self.device_id = device_id
        self.table_name = sql_utilities.get_table_name(device_id)
        self.summary_name = sql_utilities.get_summary_name(device_id)
        self.view_name = sql_utilities.get_view_name(device_id)
        self.statement_queue = shared_queue
        self.metadata = sql_metadata
        self.table_exists = False
        self.summary_exists = False
        self.view_exists = False
        self.ready = ready

    async def update(self, device):
        # TODO Need to think about if I add additional columns
        device_state = device.get_state_dictionary()

        if device_state is None:
            log.warning(f"Device {self.device_id} did not fill its state dictionary")

        # We need to wait until the SQL session has been created before we can do anything
        if not self.ready[0]:
            return

        table_names = self.metadata.tables.keys()
        if not self.table_exists:
            self.table_exists = self.table_name in table_names

            if not self.table_exists:
                log.info(f"Creating new table '{self.table_name}' in database...")
                await self.statement_queue.put(self.new_table_expression(self.table_name, device_state))

        if not self.summary_exists:
            self.summary_exists = self.summary_name in table_names

            if not self.summary_exists:
                log.info(f"Creating new summary table '{self.summary_name}' in database...")
                await self.statement_queue.put(self.new_table_expression(self.summary_name, device_state, True))

        if not self.view_exists:
            self.view_exists = self.view_name in table_names

            if not self.view_exists:
                log.info(f"Creating new view '{self.view_name}' in database...")
                await self.statement_queue.put(self.new_view_expression(device_state))

        table = self.metadata.tables[self.table_name]
        insert_statement = insert(table).values(device_state)
        await self.statement_queue.put(insert_statement)

    def new_table_expression(self, table_name, state_dictionary, add_standard_deviation_columns: bool = False):
        type_mapping = {
            str: String,
            int: Integer,
            float: Float,
        }

        table = Table(table_name, self.metadata)
        table.append_column(Column("id", Integer, primary_key=True, autoincrement=True))

        for key, value in state_dictionary.items():
            column_python_type = type(value)
            column_type = type_mapping[column_python_type]
            table.append_column(Column(key, column_type))

            if add_standard_deviation_columns and column_python_type == float and key != "time_updated":
                table.append_column(Column(f"{key}_stdev", column_type))

        create_expression = CreateTable(table)
        return create_expression

    def new_view_expression(self, state_dictionary):
        view_columns = state_dictionary.keys()
        columns_sql = ", ".join(view_columns)

        view_sql = (f"create view {self.view_name} as select {columns_sql} from {self.summary_name} "
                    f"union all select {columns_sql} from {self.table_name}")
        return text(view_sql)


class NotificationObserver(DeviceObserver, ABC):
    def __init__(self, device_id: str, webhook_endpoint: str, icon_url: str = None):
        self.device_id = device_id
        self.webhook_endpoint = webhook_endpoint
        self.icon_url = icon_url
        self.persisted_state = None

    async def try_send_notification(self, title: str, message: str, action: str = None) -> bool:
        headers = {"Title": title}
        if action:
            headers["Action"] = action
        if self.icon_url:
            headers["Icon"] = self.icon_url
        async with (aiohttp.ClientSession() as session):
            async with session.post(self.webhook_endpoint, data=message, headers=headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    log.warning(f"Failed to send notification for {self.device_id}: {response_text}")
                    return False

                return True

    def state_changed(self, new_state) -> bool:
        if self.persisted_state is None:
            self.persisted_state = new_state
            return False

        return new_state != self.persisted_state


class GridChangeNotificationObserver(NotificationObserver):
    NOTIFICATION_TITLE = "Grid Update"

    def __init__(self, device_id: str, webhook_endpoint: str, icon_url: str = None):
        super().__init__(device_id, webhook_endpoint, icon_url)

    async def update(self, device):
        device_state = device.get_state_dictionary()
        grid_state = device_state["grid_state"]

        if self.state_changed(grid_state):
            await self.try_send_notification(self.NOTIFICATION_TITLE, f"The grid is now {grid_state}")

        self.persisted_state = grid_state


class LowBatteryNotificationObserver(NotificationObserver):
    NOTIFICATION_TITLE = "Low Battery"

    def __init__(self, device_id: str, webhook_endpoint: str, low_battery_level: int, switch_action: str = None,
                 icon_url: str = None):
        super().__init__(device_id, webhook_endpoint, icon_url)
        self.low_battery_level = low_battery_level
        self.notification_sent = False
        self.switch_action = switch_action

    async def update(self, device):
        device_state = device.get_state_dictionary()
        soc = int(device_state["state_of_charge"] * 100)

        if self.state_changed(soc) and soc <= self.low_battery_level and not self.notification_sent:
            success = await self.try_send_notification(self.NOTIFICATION_TITLE, f"The battery is now at {soc}%",
                                                       self.switch_action)
            if success:
                self.notification_sent = True

        if soc > self.low_battery_level:
            self.notification_sent = False

        self.persisted_state = soc

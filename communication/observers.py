import abc
import csv
import datetime
import os
import asyncio
import logging
import websockets
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Table, String, Column, Integer, Float, MetaData, insert, event
from sqlalchemy.schema import CreateTable
from data_management import sql_utilities

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
    def __init__(self, host:str, port:int, shared_queue: asyncio.Queue):
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
        async with websockets.serve(self.register_connection, self.host, self.port):
            while self.running:
                message = await self.message_queue.get()
                if message is None:
                    continue
                for connection in self.connections:
                    await connection.send(message)

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
            await connection.run_sync(self.metadata.reflect)

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
        self.statement_queue = shared_queue
        self.metadata = sql_metadata
        self.table_exists = False
        self.ready = ready


    async def update(self, device):
        # TODO Need to think about if I add additional columns
        device_state = device.get_state_dictionary()

        # We need to wait until the SQL session has been created before we can do anything
        if not self.ready[0]:
            return

        if not self.table_exists:
            table_names = self.metadata.tables.keys()
            self.table_exists = self.table_name in table_names

            if not self.table_exists:
                log.info(f"Creating new table '{self.table_name}' in database...")
                await self.statement_queue.put(self.new_table_expression(device_state))

        table = self.metadata.tables[self.table_name]
        insert_statement = insert(table).values(device_state)
        await self.statement_queue.put(insert_statement)


    def new_table_expression(self, state_dictionary):
        type_mapping = {
            str: String,
            int: Integer,
            float: Float,
        }

        table = Table(self.table_name, self.metadata)
        table.append_column(Column("id", Integer, primary_key=True, autoincrement=True))

        for key, value in state_dictionary.items():
            column_type = type_mapping[type(value)]
            table.append_column(Column(key, column_type))
        
        create_expression = CreateTable(table)
        return create_expression
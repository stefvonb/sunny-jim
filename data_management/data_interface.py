from enum import Enum
from abc import ABC, abstractmethod
from data_management import sql_utilities
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from time import time


class DataStorageType(Enum):
    CSV = 1
    SQL = 2

# Currently this is hard-coded, solely based on what I think is most important
DATA_STORAGE_PREFERENCE = [DataStorageType.SQL, DataStorageType.CSV]


class DataInterface(ABC):
    @staticmethod
    def create_from_config(config: dict):
        for preference in DATA_STORAGE_PREFERENCE:
            if preference == DataStorageType.CSV:
                if "csv_data_logging" in config:
                    raise NotImplementedError("CSV data storage not yet implemented!")
            elif preference == DataStorageType.SQL:
                if "sql_database" in config:
                    sql_connection_string = sql_utilities.get_sql_connection_string(config["sql_database"]["sql_driver"], config["sql_database"]["database_path"])
                    return SQLDataInterface(sql_connection_string)

        raise ValueError("No valid data storage types found in config!")

    @abstractmethod
    async def get_last_n_entries(self, device_id: str, n: int, columns: list[str] = None):
        pass

    @abstractmethod
    async def get_last_n_minutes(self, device_id: str, n: int, columns: list[str] = None):
        pass

    async def get_last_n_hours(self, device_id: str, n: int, columns: list[str] = None):
        return await self.get_last_n_minutes(device_id, n * 60, columns)

    @abstractmethod
    async def get_when_grid_last_on(self):
        pass

class SQLDataInterface(DataInterface):
    def __init__(self, sql_connection_string: str):
        self.engine = create_async_engine(sql_connection_string)

    async def get_last_n_entries(self, device_id: str, n: int, columns: list[str] = None):
        async with self.engine.connect() as connection:
            table_name = sql_utilities.get_table_name(device_id)
            selection_columns = sql_utilities.get_selection_columns(columns)

            query = text(f"SELECT {selection_columns} FROM {table_name} ORDER BY time_updated DESC LIMIT {n}")
            result = await connection.execute(query)
            results_dictionary = sql_utilities.convert_cursor_result_to_dict(result)
            return results_dictionary

    async def get_last_n_minutes(self, device_id: str, n: int, columns: list[str] = None):
        async with self.engine.connect() as connection:
            table_name = sql_utilities.get_table_name(device_id)
            selection_columns = sql_utilities.get_selection_columns(columns)

            past_timestamp = time() - n * 60
            query = text(f"SELECT {selection_columns} FROM {table_name} WHERE time_updated >= {past_timestamp} ORDER BY time_updated")
            result = await connection.execute(query)
            results_dictionary = sql_utilities.convert_cursor_result_to_dict(result)
            return results_dictionary

    async def get_when_grid_last_on(self, device_id: str):
        async with self.engine.connect() as connection:
            table_name = sql_utilities.get_table_name(device_id)

            query = text(f"SELECT time_updated FROM {table_name} WHERE grid_state = 'on' ORDER BY time_updated DESC LIMIT 1")
            result = await connection.execute(query)
            results_dictionary = {'time_grid_last_on': result.first()[0]}
            return results_dictionary
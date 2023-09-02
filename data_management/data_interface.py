from enum import Enum
from abc import ABC, abstractmethod
from data_management import sql_utilities
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, MetaData
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
                    sql_connection_string = sql_utilities.get_sql_connection_string(
                        config["sql_database"]["sql_driver"], config["sql_database"]["database_path"])
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

    @abstractmethod
    async def summarise_data(self, device_id: str, cutoff_timestamp: int):
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
            query = text(
                f"SELECT {selection_columns} FROM {table_name} WHERE time_updated >= {past_timestamp} ORDER BY time_updated")
            result = await connection.execute(query)
            results_dictionary = sql_utilities.convert_cursor_result_to_dict(result)
            return results_dictionary

    async def get_when_grid_last_on(self, device_id: str):
        async with self.engine.connect() as connection:
            table_name = sql_utilities.get_table_name(device_id)

            query = text(
                f"SELECT time_updated FROM {table_name} WHERE grid_state = 'on' ORDER BY time_updated DESC LIMIT 1")
            result = await connection.execute(query)
            results_dictionary = {'time_grid_last_on': result.first()[0]}
            return results_dictionary

    async def summarise_data(self, device_id: str, cutoff_timestamp: int):
        async with self.engine.connect() as connection:
            metadata = MetaData()
            await connection.run_sync(metadata.create_all)
            await connection.run_sync(metadata.reflect)
            table_name = sql_utilities.get_table_name(device_id)

            outer_sql = "select main_group.leading_minute as time_updated"
            averaging_sql = "select CEIL(time_updated / 60) * 60 as leading_minute"
            most_recent_sql = "select ceil(time_updated/ 60) * 60 as leading_minute, row_number() over(partition by FLOOR(time_updated / 60) * 60 order by time_updated desc) as row_num"
            ordered_columns = ["time_updated"]

            for column in metadata.tables[table_name].columns:
                if column.name in ("id", "time_updated"):
                    continue

                if column.type.python_type == str:
                    outer_sql += f", outer_group.{column.name} as {column.name}"
                    ordered_columns.append(column.name)
                    most_recent_sql += f", {column.name}"

                elif column.type.python_type == float:
                    outer_sql += f", main_group.{column.name} as {column.name}, main_group.{column.name}_stdev as {column.name}_stdev"
                    ordered_columns.append(column.name)
                    ordered_columns.append(f"{column.name}_stdev")
                    averaging_sql += f", avg({column.name}) as {column.name}, stdev({column.name}) as {column.name}_stdev"

            summary_name = sql_utilities.get_summary_name(device_id)
            ordered_columns_string = ", ".join(ordered_columns)
            full_query = (f"insert into {summary_name} ({ordered_columns_string}) {outer_sql} from ({averaging_sql} from {table_name} where time_updated <= {cutoff_timestamp} "
                          f"group by FLOOR(time_updated / 60) * 60) as main_group inner join "
                          f"(select * from ({most_recent_sql} from {table_name} WHERE time_updated <= {cutoff_timestamp}) "
                          f"inner_group where inner_group.row_num = 1) outer_group on "
                          f"main_group.leading_minute = outer_group.leading_minute "
                          f"order by time_updated;")

            await connection.execute(text(full_query))

            # Drop all the summarised data from the main table
            deletion_query = f"DELETE FROM {table_name} WHERE time_updated <= {cutoff_timestamp}"
            await connection.execute(text(deletion_query))

            return {"success": True}

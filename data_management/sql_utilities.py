def get_table_name(device_id: str):
    return f"device_{device_id}"


def get_sql_connection_string(sql_driver: str, database_path: str):
    return f'{sql_driver}://{database_path}'


def get_selection_columns(columns: list[str] = None):
    if columns:
        return ", ".join(columns)
    else:
        return "*"


def convert_cursor_result_to_dict(result) -> list[dict]:
    all_results = result.fetchall()
    transposed_results = list(zip(*all_results))

    if len(all_results) == 0:
        return {}

    return_dict = {}
    for i, key in enumerate(result.keys()):
        return_dict[key] = transposed_results[i]

    return return_dict

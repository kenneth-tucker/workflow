import importlib.util
import re
import sys
from lib.utils.part_utils import PartConfig

def extract_data_names(text: str) -> list[str]:
    """
    Extract all data names of the form {name} from the given text.
    """
    return re.findall(r"\{(.*?)\}", text)

def insert_data_values(text: str, data_values: dict[str, object]) -> str:
    """
    Replace all occurrences of {name} in the text with the corresponding
    value from data_values, converted to a string.
    """
    def replace_match(match):
        name = match.group(1)
        if name in data_values:
            return str(data_values[name])
        else:
            raise KeyError(f"Data name '{name}' not found in data values")
    return re.sub(r"\{(.*?)\}", replace_match, text)

def execute_statement_with_data_values(statement: str, data_values: dict[str, object]):
    """
    Try to execute a statement with data names replaced by their values.
    The statement should be a valid Python expression after replacement.

    IMPORTANT: use this carefully, since it involves dynamic code execution.
    """
    try:
        # Replace {data_name} with data_values[data_name] in the statement string
        exec_statement = re.sub(r"\{(.*?)\}", lambda m: f"data_values['{m.group(1)}']", statement)
        # Evaluate the statement
        return eval(exec_statement, {"__builtins__": None}, {"data_values": data_values})
    except Exception as e:
        raise ValueError(f"Error evaluating statement '{statement}': {e}")

def extract_parts(
       file_path: str,
       config: dict
    ) -> dict[str, PartConfig]:
    """
    Extract all part configurations from config file data.
    Returns a dictionary mapping part names to their configurations.
    """
    part_table = config.get("part", {})
    parts = {}
    for top_level_name, top_level_part in part_table.items():
        if top_level_name == "start_here":
            continue
        parts.update(
            _extract_part_configs(
                file_path=file_path,
                raw_table=top_level_part,
                name_path=top_level_name
            )
        )
    return parts

# Private helpers

def _extract_part_configs(
    file_path: str,
    raw_table: dict,
    name_path: str
) -> dict[str, PartConfig]:
    # Helper for extract_parts that extracts nested part configurations
    # recursively and flattens the part tables into a single dictionary
    # with dot notation (e.g. part.subflow_1.subflow_2.my_step).

    # Do NOT use these reserved keywords in your part naming
    # (i.e. don't include "type_name" or "config_values" in your part name
    # or it will confuse the configuration parser).
    reserved_keys = {
        "type_name",
        "next_part",
        "start_here",
        "config_values",
        "input_names",
        "output_names"
    }

    # The next_part can be absent, a single identifier, or a name mapping.
    # Convert to a dict representation to use internally.
    next_part = raw_table.get("next_part", {})
    if isinstance(next_part, str):
        next_part = {"": next_part}

    # Each flow sub-table has a part configuration and possibly nested
    # sub-tables for nested parts. If a member of the table dictionary
    # does not have one of the reserved keys, it is treated as a nested
    # part.
    part = PartConfig(
        file_path=file_path,
        name=name_path,
        raw=raw_table,
        type_name=raw_table.get("type_name"),
        next_part=next_part,
        start_here=raw_table.get("start_here", ""),
        config_values=raw_table.get("config_values", {}),
        input_names=raw_table.get("input_names", {}),
        output_names=raw_table.get("output_names", {}),
    )
    nested_parts = {}
    for sub_key, sub_value in raw_table.items():
        if sub_key not in reserved_keys:
            nested_parts.update(
                _extract_part_configs(
                    file_path=file_path,
                    raw_table=sub_value,
                    name_path=f"{name_path}.{sub_key}"
                )
            )

    return {**nested_parts, **{name_path: part}}
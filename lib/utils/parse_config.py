import importlib.util
import re
import sys
from collections import OrderedDict
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

def extract_part_configs(
       file_path: str,
       part_table: dict,
       parent_full_name: str
    ) -> 'OrderedDict[str, PartConfig]':
    """
    Extract all part configurations from a part table.
    Returns an OrderedDict mapping part full names to their configurations.
    """
    parts = OrderedDict()
    for top_level_name, top_level_part in part_table.items():
        if top_level_name == "first_part":
            continue
        name_path = top_level_name if not parent_full_name\
            else f"{parent_full_name}.{top_level_name}"
        parts.update(
            _extract_part_configs_recursive(
                file_path=file_path,
                raw_table=top_level_part,
                name_path=name_path
            )
        )
    return parts

# Private helpers

def _extract_part_configs_recursive(
    file_path: str,
    raw_table: dict,
    name_path: str
) -> 'OrderedDict[str, PartConfig]':
    """
    Recursive helper for extract_part_configs.

    It extracts nested part configurations recursively and flattens
    the part tables into a single dictionary with dot notation.
    """

    # Do NOT use these reserved keywords in your part naming
    # (i.e. don't include "type_name" or "config_values" in your part name
    # or it will confuse the configuration parser).
    reserved_keys = {
        "type_name",
        "next_part",
        "first_part",
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
        full_name=name_path,
        raw=raw_table,
        type_name=raw_table.get("type_name"),
        next_part=next_part,
        first_part=raw_table.get("first_part", ""),
        config_values=raw_table.get("config_values", {}),
        input_names=raw_table.get("input_names", {}),
        output_names=raw_table.get("output_names", {}),
    )
    nested_parts = OrderedDict()
    for sub_key, sub_value in raw_table.items():
        if sub_key not in reserved_keys:
            nested_parts.update(
                _extract_part_configs_recursive(
                    file_path=file_path,
                    raw_table=sub_value,
                    name_path=f"{name_path}.{sub_key}"
                )
            )

    result = OrderedDict()
    result[name_path] = part
    result.update(nested_parts)
    return result
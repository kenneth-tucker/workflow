from typing import Optional

# Used to define a part type in the part_types dictionary
class PartTypeInfo:
    def __init__(
        self,
        type: type,
        description: Optional[str] = None
        # TODO add checking for required input names, output names, config values, notes, etc.
    ):
        self.type = type
        self.description = description

# Stores the parsed config data for an individual part
class PartConfig:
    def __init__(
        self,
        file_path: str,
        name: str,
        raw: dict,
        type_name: str,
        next_part: dict[str, str],
        start_here: str,
        config_values: dict[str, object],
        input_names: dict[str, str],
        output_names: dict[str, str],
    ):
        self.file_path = file_path
        self.name = name
        self.raw = raw
        self.type_name = type_name
        self.next_part = next_part
        self.start_here = start_here
        self.config_values = config_values
        self.input_names = input_names
        self.output_names = output_names

# The ExperimentManager uses this to setup your part
class PartContext:
    def __init__(
        self,
        manager,
        config,
    ):
        self.manager = manager
        self.config = config

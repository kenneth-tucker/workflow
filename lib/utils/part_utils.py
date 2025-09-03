from typing import Optional

# Used to define a part type in the part_types dictionary
class PartTypeInfo:
    def __init__(
        self,
        type: type,
        description: Optional[str] = None
        # TODO add checking for required input names, output names, config values
    ):
        self.type = type
        self.description = description

# Stores the parsed config data for an individual part
class PartConfig:
    def __init__(
        self,
        name: str,
        raw: dict,
        type_name: str,
        config_values: dict[str, object],
        input_names: dict[str, str],
        output_names: dict[str, str],
        next_part: dict[str, str] | str | None,
    ):
        self.name = name
        self.raw = raw
        self.type_name = type_name
        self.config_values = config_values
        self.input_names = input_names
        self.output_names = output_names
        self.next_part = next_part

# The ExperimentManager uses this to setup your part
class PartContext:
    def __init__(
        self,
        manager,
        config,
    ):
        self.manager = manager
        self.config = config

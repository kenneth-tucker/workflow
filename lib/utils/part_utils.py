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
        full_name: str,
        raw: dict,
        type_name: str,
        next_part: dict[str, str],
        start_here: str,
        config_values: dict[str, object],
        input_names: dict[str, str],
        output_names: dict[str, str],
    ):
        # The path of the config file this part was defined in
        self.file_path = file_path
        # The full name of the part, including any parent flow names
        self.full_name = full_name
        # The raw configuration data for this part
        self.raw = raw
        # The type of this part
        self.type_name = type_name
        # The short name(s) of the next part(s) to go to after this part
        self.next_part = next_part
        # The short name of the part to start at when entering a flow part
        self.start_here = start_here
        # The config values for this part
        self.config_values = config_values
        # The input name to experiment data name mappings for this part
        self.input_names = input_names
        # The output name to experiment data name mappings for this part
        self.output_names = output_names

# The ExperimentManager uses this to setup your part
class PartContext:
    def __init__(
        self,
        manager,
        config: PartConfig,
    ):
        self.manager = manager
        self.config = config

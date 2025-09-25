from typing import Optional

class PartTypeInfo:
    """
    Information about a part type, used in the part_types dictionary.
    """
    def __init__(
        self,
        type: type,
        description: Optional[str] = None
        # TODO add checking for required input names, output names, config values, notes, etc.
    ):
        self.type = type
        self.description = description

class PartConfig:
    """
    Stores the parsed config data for an individual part.
    """
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

class PartContext:
    """
    Context information passed to a part when it is initialized.
    """
    def __init__(
        self,
        manager,
        config: PartConfig,
    ):
        self.manager = manager
        self.config = config

class DecisionRoute:
    """
    The route for the experiment manager to take when a decision is made.

    route_name is the left hand side of the next_part mapping for the
    selected route, a command like "done" or "quit", or None/"None" if the
    researcher needs to choose.

    can_use_part_name indicates if a route name can refer to part names
    directly if no mapping is found in the current part's next_part config.
    """
    def __init__(
        self,
        route_name: str | None,
        can_use_part_name: bool = False,
    ):
        self.route_name = route_name
        self.can_use_part_name = can_use_part_name

class BeginFlowRoute:
    """
    The route for the experiment manager to take when entering a flow.

    start_here is the short name of the part to start at, a command
    like "done" or "quit", or None/"None" if the researcher needs to choose.
    It is typically the value of the "start_here" config option but
    can be something else if needed.
    """
    def __init__(
        self,
        start_here: str | None,
    ):
        self.start_here = start_here

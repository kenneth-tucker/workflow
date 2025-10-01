import os
from typing import override
from lib.utils.part_utils import BeginFlowRoute, DecisionRoute, PartConfig
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartContext

class _Part:
    """
    The base class for all parts (Steps, Decisions, and Flows).
    Do NOT inherit from this class directly, instead inherit from Step, Decision, or Flow.
    """
    def __init__(self, context: PartContext):
        # Do not access _context in your class, use the helper methods in this
        # class instead.
        self._context = context

    def get_output_file_path(self, relative_path: str = "") -> str:
        """
        Get the file path you should use for this run of the experiment.
        """
        if relative_path:
            normalized_path = os.path.normpath(relative_path)
            return os.path.join(self._context.manager.out_dir_for_run, normalized_path)
        return self._context.manager.out_dir_for_run

    def get_config_file_path(self) -> str:
        """
        Get the config file path that defined this part.
        """
        return self._context.config.file_path

    def get_full_name(self) -> str:
        """
        Get the full part name assigned to this part instance.
        """
        return self._context.config.full_name

    def get_config(
        self,
        config_name: str,
        allow: list[type] | None = None,
        optional: bool = False
    ) -> object:
        """
        Read a configuration value, optionally checking if its type
        is in the 'allow' list of types.
        
        Raises a ConfigError if the config is not found or if the type
        does not match to alert the researcher that they made a mistake
        in the config file. You can make any config value optional with
        the 'optional' flag, in which case the returned value is None
        if the config isn't found.

        Important Note: you can (and should) call get_config() from
        your class constructor BUT make sure to do so after calling
        the superclass constructor, super().__init__(context), otherwise
        it will not work as expected.

        Example (required config, no type checking):
        value = self.get_config('my_config')

        Example (required config with type checking):
        value = self.get_config('my_int_or_list_config', allow=[int, list])

        Example (optional config, no type checking):
        value = self.get_config('my_optional_config', optional=True)

        Example (optional config with type checking):
        value = self.get_config('my_optional_str_config', allow=[str], optional=True)
        """
        if config_name not in self._context.config.config_values:
            if optional:
                return None
            # Check for typos in config if here
            raise ConfigError(
                f"Config '{config_name}' for {self._context.config.full_name} must be assigned a value"
            )
        value = self._context.config.config_values.get(config_name)
        # Note: isinstance() cannot handle nested types like list[int]
        if allow is not None and not any(isinstance(value, t) for t in allow):
            # Config has unexpected type
            raise ConfigError(
                f"Config '{config_name}' for {self._context.config.full_name} has the "
                f"wrong type, {type(value).__name__}, list of allowed types: "
                f"{allow}"
            )
        return value

    def get_input(
        self,
        argument_name: str,
        allow: list[type] | None = None,
        optional: bool = False,
        can_use_global: bool = False
    ) -> object:
        """
        Read an input argument, optionally checking if its type
        is in the 'allow' list of types.
        
        Raises a ConfigError if the argument is not assigned or a
        ValueError if the type does not match. You can make the
        argument optional with the 'optional' flag, in which case
        the returned value is None. The 'can_use_global' flag
        determines if a global variable with the given name
        should be used in case the input name mapping is missing.
        This option is convenient but can lead to unexpected behavior
        and brittle experiments if not used carefully. If the global
        name is also not found, None is returned.
        
        Example (required input, no type checking):
        value = self.get_input('my_arg')
        
        Example (required input with type checking):
        value = self.get_input('my_int_or_list_arg', allow=[int, list])
        
        Example (optional input, no type checking):
        value = self.get_input('my_optional_arg', optional=True)
        
        Example (optional input with type checking):
        value = self.get_input('my_optional_int_arg', allow=[int], optional=True)
        
        Example (input with global name fallback if no name mapping exists):
        value = self.get_input('my_int_arg_or_global', allow=[int], can_use_global=True)
        """
        global_name = self._context.config.input_names.get(argument_name)
        if global_name is None:
            if can_use_global:
                # Try the given name in the experiment data
                global_name = argument_name
            else:
                if optional:
                    return None
                # Check for typos in config input_names list if here
                raise ConfigError(
                    f"Input name '{argument_name}' for {self._context.config.full_name} "
                    "must be mapped to the name of some experiment data"
                )
        value = self._context.manager._get_data(global_name)
        # Note: isinstance() cannot handle nested types like list[int]
        if allow is not None and not any(isinstance(value, t) for t in allow):
            # Input has unexpected type
            raise ValueError(
                f"Experiment data '{global_name}' for the input "
                f"'{argument_name}' of {self._context.config.full_name} has the wrong "
                f"type, {type(value).__name__}, list of allowed types: {allow}"
            )
        return value
    
    def copy_experiment_data(self) -> dict:
        """
        Get a copy of the entire experiment data dictionary.
        """
        return self._context.manager._copy_experiment_data()
    
    def save_data_to_trace_entry(self, part_data: dict) -> None:
        """
        Store a data dictionary into the current trace entry as
        'part_data'. This can be used to record any extra data
        that is specific to this run of your part. Make sure it
        is JSON-serializable. Overwrites any previously saved
        'part_data' if called multiple times during the same part run.
        """
        self._context.manager._save_data_to_trace_entry(part_data)

    def load_data_from_retrace_entry(self) -> dict | None:
        """
        When retracing an old run of an experiment, retrieve any
        'part_data' dictionary that was saved for this part
        in the trace entry. Returns None if no data was saved or
        if we are not retracing.
        """
        return self._context.manager._load_data_from_retrace_entry()

    def insert_custom_trace_entry(self, event_type: str, event_data: dict | None = None) -> None:
        """
        Insert a custom trace entry into the experiment trace
        at the current position. The event_type is a string
        that identifies the type of the custom entry and
        event_data is a dictionary of any JSON-serializable data
        you want to include in the entry. This can be used to
        record any extra information you want in the trace or
        to signal tools that are monitoring the experiment using
        the trace.
        """
        self._context.manager._insert_custom_trace_entry(event_type, event_data)

# Base classes for Steps, Decisions, and Flows.
# Inherit from these and pass in the context
# to the constructor. You MUST implement some
# methods in your subclass (see below).
#
# Example:
# class MyStep(Step):
#     def __init__(self, context):
#         super().__init__(context)
#         ...
#
#     @override
#     def run_step(self) -> None:
#         ...

class Step(_Part):
    """
    A step to run in the experiment. Can modify the experiment data.
    """
    def __init__(self, context: PartContext):
        super().__init__(context)

    def run_step(self) -> None:
        """
        You MUST implement this in your subclass. ExperimentManager
        calls this to run your step's procedure. It might be run
        multiple times during the experiment so be sure to reset
        any state between calls.
        """
        raise NotImplementedError("Must implement the run_step method in your subclass")

    # Helper functions you can call in your step

    def set_output(
        self,
        argument_name: str,
        value: object,
        optional: bool = False,
        can_use_global: bool = False
    ) -> None:
        """
        Write an output argument with the given value.
        
        Raises a ConfigError if the argument is not assigned. You can make
        the argument optional with the 'optional' flag, in which
        case no experiment data is actually changed. This is useful
        if you want to output anything 'extra', that the researcher
        might or might not care about, such as more verbose data. The
        'can_use_global' flag determines if a global variable with the
        given name should be used in case the output name mapping is
        missing. This option is convenient but can lead to unexpected
        behavior and brittle experiments if not used carefully.

        IMPORTANT NOTE: Only Step types should modify the experiment data.

        Example:
        x = 42
        ...
        self.set_output('my_arg', x)

        Example (output with global name fallback if no name mapping exists):
        self.set_output(
            'my_tricky_arg_or_global',
            'possibly corrupted something else',
            can_use_global=True
        )
        """
        global_name = self._context.config.output_names.get(argument_name)
        if global_name is None:
            if can_use_global:
                # Try the given name in the experiment data
                global_name = argument_name
            else:
                if optional:
                    # Do nothing for unmapped optional outputs
                    return
                # Check for typos in config outputs list if here
                raise ConfigError(
                        f"Output name '{argument_name}' for {self._context.config.full_name} "
                        "must be mapped to the name of some experiment data"
                    )
        self._context.manager._set_data(global_name, value)

class Decision(_Part):
    """
    A decision point in the experiment. Should NOT modify the experiment data.
    """
    def __init__(self, context: PartContext):
        super().__init__(context)

    def decide_route(self) -> DecisionRoute:
        """
        You MUST implement this in your subclass. ExperimentManager
        calls this to decide which route to take in the experiment.
        """
        raise NotImplementedError("Must implement the decide_route method in your subclass")

class Flow(_Part):
    """
    A flow to setup and contain related parts. Should NOT modify the experiment
    data except through its parts.
    """
    def __init__(self, context: PartContext):
        super().__init__(context)

    def begin_flow(self) -> BeginFlowRoute:
        """
        You MUST implement this in your subclass. ExperimentManager
        calls this when it enters your flow. You need to setup your flow's
        parts and tell the manager which of your parts to run first.
        """
        raise NotImplementedError("Must implement the begin_flow method in your subclass")

    def end_flow(self) -> None:
        """
        You MUST implement this in your subclass. ExperimentManager
        calls this when it exits your flow. You need to perform any
        necessary cleanup here.
        """
        raise NotImplementedError("Must implement the end_flow method in your subclass")
    
    # Helper functions you can call to manage your flow
    # Note: a part's full name includes all parent flows, while
    # a part's short name is just the part's own name.
    # e.g. "a.b.c" is the full name for part "c" in the flow "a.b".
    # We use short names for these helpers since a flow should
    # only know about and be managing its own parts.

    def get_first_part(self) -> str | None:
        """
        Get the short name of the part to start with when this flow is entered,
        or None if not configured.
        """
        return self._context.config.first_part

    def list_part_names(self) -> list[str]:
        """
        List the short names for all parts in the current flow.
        Note: does not include parts in nested flows.
        """
        return self._context.manager._get_flow_parts_short_names(self.get_full_name())

    def get_part(self, part_short_name: str) -> _Part | None:
        """
        Access a part object from the current flow, returns None
        if the part does not exist.
        """
        return self._context.manager._get_part(f"{self.get_full_name()}.{part_short_name}")

    def add_part(self, part_config: PartConfig) -> None:
        """
        Construct a new part with the given config data then add
        it into the current flow. If a part already exists in the flow
        with the same name then that part is replaced with the new one.

        Raises a ConfigError if the config is found to be invalid.
        Check the part_config.full_name to ensure it is in this flow.
        """
        if not part_config.full_name.startswith(f"{self.get_full_name()}."):
            raise ConfigError(
                f"Cannot add part '{part_config.full_name}' to flow '{self.get_full_name()}', "
                "a part's full name must start with its flow's full name"
            )
        self._context.manager._add_part(part_config)

    def remove_part(self, part_short_name: str) -> None:
        """
        Remove a part from the current flow, does nothing if the part does not exist.
        """
        self._context.manager._remove_part(f"{self.get_full_name()}.{part_short_name}")

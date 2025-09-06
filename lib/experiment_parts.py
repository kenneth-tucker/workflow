from typing import override
from lib.utils.part_utils import PartConfig, PartTypeInfo
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartContext

# Contains the common functionality for all parts.
# Inherit from Step, Decision, or Flow below instead of this but
# you can call these methods using self (e.g. self.get_input()).
class _Part:
    def __init__(self, context: PartContext):
        # Do not access _context in your class, use helper methods
        # in this class instead.
        self._context = context

    # Get the config file path that defined this part.
    def get_config_file_path(self) -> str:
        return self._context.config.file_path

    # Get the full part name assigned to this part instance.
    def get_full_name(self) -> str:
        return self._context.config.full_name

    # Read a configuration value, optionally checking if its type
    # is in the 'allow' list of types. Raises a ConfigError if
    # the config is not found or if the type does not match to alert
    # the researcher that they made a mistake in the config file. You
    # can make any config value optional with the 'optional' flag, in
    # which case the returned value is None if the config isn't found.
    #
    # Important Note: you can (and should) call get_config() from
    # your class constructor BUT make sure to do so after calling
    # the superclass constructor, super().__init__(context), otherwise
    # it will not work as expected.
    #
    # Example (required config, no type checking):
    # value = self.get_config('my_config')
    #
    # Example (required config with type checking):
    # value = self.get_config('my_int_or_list_config', allow=[int, list])
    #
    # Example (optional config, no type checking):
    # value = self.get_config('my_optional_config', optional=True)
    #
    # Example (optional config with type checking):
    # value = self.get_config('my_optional_str_config', allow=[str], optional=True)
    def get_config(
        self,
        config_name: str,
        allow: list[type] | None = None,
        optional: bool = False
    ) -> object:
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

    # Read an input argument, optionally checking if its type
    # is in the 'allow' list of types. Raises a ConfigError if
    # the argument is not assigned or a ValueError if the type does not match.
    # You can make the argument optional with the 'optional' flag, in
    # which case the returned value is None. The 'can_use_global'
    # flag determines if a global variable with the given name
    # should be used in case the input name mapping is missing.
    # This option is convenient but can lead to unexpected behavior
    # and brittle experiments if not used carefully. If the global
    # name is also not found, None is returned.
    #
    # Example (required input, no type checking):
    # value = self.get_input('my_arg')
    #
    # Example (required input with type checking):
    # value = self.get_input('my_int_or_list_arg', allow=[int, list])
    #
    # Example (optional input, no type checking):
    # value = self.get_input('my_optional_arg', optional=True)
    #
    # Example (optional input with type checking):
    # value = self.get_input('my_optional_int_arg', allow=[int], optional=True)
    #
    # Example (input with global name fallback if no name mapping exists):
    # value = self.get_input('my_int_arg_or_global', allow=[int], can_use_global=True)
    def get_input(
        self,
        argument_name: str,
        allow: list[type] | None = None,
        optional: bool = False,
        can_use_global: bool = False
    ) -> object:
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
    
    # Write an output argument with the given value. Raises a
    # ConfigError if the argument is not assigned. You can make
    # the argument optional with the 'optional' flag, in which
    # case no experiment data is actually changed. This is useful
    # if you want to output anything 'extra', that the researcher
    # might or might not care about, such as more verbose data. The
    # 'can_use_global' flag determines if a global variable with the
    # given name should be used in case the output name mapping is
    # missing. This option is convenient but can lead to unexpected
    # behavior and brittle experiments if not used carefully.
    #
    # IMPORTANT NOTE: Only Step types should modify the experiment data.
    #
    # Example:
    # x = 42
    # ...
    # self.set_output('my_arg', x)
    #
    # Example (output with global name fallback if no name mapping exists):
    # self.set_output(
    #     'my_tricky_arg_or_global',
    #     'possibly corrupted something else',
    #     can_use_global=True
    # )
    def set_output(
        self,
        argument_name: str,
        value: object,
        optional: bool = False,
        can_use_global: bool = False
    ) -> None:
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

# A step to run in the experiment. Can modify the experiment data.
class Step(_Part):
    def __init__(self, context: PartContext):
        super().__init__(context)

    # NOTE: YOU must implement this in your class definition.
    # ExperimentManager calls this to run your step's procedure.
    # It might be run multiple times during the experiment so
    # be sure to reset any state between calls.
    def run_step(self) -> None:
        raise NotImplementedError("Must implement the run_step method in your subclass")

# A decision point in the experiment. A Decision subclass
# should NOT modify anything, it should just decide what
# part of the experiment we want to do next.
class Decision(_Part):
    def __init__(self, context: PartContext):
        super().__init__(context)

    # NOTE: YOU must implement this in your class definition.
    # ExperimentManager calls this to decide which route to take.
    # You need to return the selected route name (not the part name),
    # "done" to leave the current flow (ends the experiment if
    # it is in the outermost flow), "quit" to end the entire experiment,
    # or None if you could not decide and need the researcher to
    # manually decide what's next.
    def decide_route(self) -> str | None:
        raise NotImplementedError("Must implement the decide_route method in your subclass")
    
    @override
    def set_output(self, argument_name, value, optional = False, can_use_global = False):
        # You should NOT be setting outputs in a decision type,
        # the ExperimentManager assumes only step types modify
        # the experiment data.
        raise TypeError("Cannot set an output in a decision")

# A flow sets up and contains related parts. A Flow subclass
# should NOT modify anything other than the parts it contains.
class Flow(_Part):
    def __init__(self, context: PartContext):
        super().__init__(context)

    # NOTE: YOU must implement this in your class definition.
    # ExperimentManager calls this when it enters your flow.
    # You need to setup your flow's parts then return the (short)
    # name of the first part of your flow for the ExperimentManager
    # to run, or "done" to leave the flow right away or "quit"
    # to end the entire experiment or None to have the researcher
    # decide what to do first in the flow.
    def begin_flow(self) -> str | None:
        raise NotImplementedError("Must implement the begin_flow method in your subclass")

    # NOTE: YOU must implement this in your class definition.
    # ExperimentManager calls this when it exits your flow.
    # You need to perform any necessary cleanup here.
    def end_flow(self) -> None:
        raise NotImplementedError("Must implement the end_flow method in your subclass")

    @override
    def set_output(self, argument_name, value, optional = False, can_use_global = False):
        # You should NOT be setting outputs in a flow type,
        # the ExperimentManager assumes only step types modify
        # the experiment data.
        raise TypeError("Cannot set an output in a flow")
    
    # Helper functions you can call to manage your flow
    # Note: a part's full name includes all parent flows, while
    # a part's short name is just the part's own name.
    # e.g. "a.b.c" is the full name for part "c" in the flow "a.b".
    # We use short names for these helpers since a flow should
    # only know about and be managing its own parts.

    def get_start_here(self) -> str | None:
        # Get the short name of the part to start with
        # when this flow is entered, or None if not configured.
        return self._context.config.start_here

    def list_part_names(self) -> list[str]:
        # List the short names for all parts in the current flow.
        # Note: does not include parts in nested flows.
        return self._context.manager._get_flow_parts_short_names(self.get_full_name())

    def get_part(self, part_short_name: str) -> _Part | None:
        # Access a part object from the current flow, returns None
        # if the part does not exist.
        return self._context.manager._get_part(f"{self.get_full_name()}.{part_short_name}")

    def add_part(self, part_config: PartConfig) -> None:
        # Construct a new part with the given config data then add
        # it into the current flow. If a part already exists in the flow
        # with the same name then that part is replaced with the new one.
        # Raises a ConfigError if the config is found to be invalid.
        # Check the part_config.full_name to ensure it is in this flow.
        if not part_config.full_name.startswith(f"{self.get_full_name()}."):
            raise ConfigError(
                f"Cannot add part '{part_config.full_name}' to flow '{self.get_full_name()}', "
                "a part's full name must start with its flow's full name"
            )
        self._context.manager._add_part(part_config)

    def remove_part(self, part_short_name: str) -> None:
        # Remove a part from the current flow, does nothing if the part does not exist.
        self._context.manager._remove_part(f"{self.get_full_name()}.{part_short_name}")

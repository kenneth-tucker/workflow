from typing import override
from lib.experiment_parts import Step
from lib.utils.exceptions import ConfigError
from lib.utils.parse_config import extract_data_names, insert_data_values

class TerminalStep(Step):
    """
    A step part that shows a prompt in the terminal and optionally
    gets input from the researcher.
    The prompt can include experiment data names as {name}.
    If the "enter" config is given, the input is converted to that type.
    """
    def __init__(self, context):
        super().__init__(context)
        self.prompt: str = self.get_config("prompt", allow=[str])
        # The type of input the researcher is expected to provide,
        # only show a prompt if not provided
        self.input_type_name: str | None = self.get_config("enter", allow=[str], optional=True)
        # The name of the experiment data to store the input value,
        # should be provided if "enter" is provided
        self.store_name: str | None = self.get_config("to", allow=[str], optional=True)
        # How to handle retracing, "auto" if the input should be automatically
        # filled in when retracing to this step or "manual" if the researcher should be
        # prompted again. Default is "auto".
        self.retrace_behavior: str | None = self.get_config("retrace", allow=[str], optional=True)
        if self.input_type_name is not None:
            self.input_type_converter: type = {
                "str": str,
                "int": int,
                "float": float,
            }.get(self.input_type_name)
            if not self.input_type_converter:
                raise ConfigError(
                    f"Unsupported input type '{self.input_type_name}' in part '{self.get_full_name()}'"
                )
            if not self.store_name:
                raise ConfigError(
                    f"Missing 'to' configuration in part '{self.get_full_name()}'"
                )
            if self.retrace_behavior not in (None, "auto", "manual"):
                raise ConfigError(
                    f"Invalid retrace behavior '{self.retrace_behavior}' in part '{self.get_full_name()}': "
                    "must be 'auto' or 'manual'"
                )
        else:
            if self.store_name:
                raise ConfigError(
                    f"Cannot use 'to' without 'enter' in part '{self.get_full_name()}'"
                )
            if self.retrace_behavior:
                raise ConfigError(
                    f"Cannot use 'retrace' without 'enter' in part '{self.get_full_name()}'"
                )

    @override
    def run_step(self) -> None:
        # Insert data values into the prompt
        data_names = extract_data_names(self.prompt)
        data_values = {name: self.get_input(name, can_use_global=True) for name in data_names}
        text = insert_data_values(self.prompt, data_values)

        if self.store_name is None:
            # Just print the prompt without getting input
            print(text)
            return
        else:
            # Handle getting input from the researcher or retracing
            if self.retrace_behavior in (None, "auto"):
                # Use the old input, if retracing and behavior is "auto" (default if not set)
                retrace_data = self.load_data_from_retrace_entry()
                if retrace_data is not None:
                    old_input_text = retrace_data.get("researcher_input")
                else:
                    old_input_text = None
            else:
                # In "manual" mode, always prompt the researcher for input
                old_input_text = None

            if old_input_text is not None:
                # Use the old input
                print(f"{text} {old_input_text} (from trace)")
                researcher_input = old_input_text
                converted_input = self.input_type_converter(old_input_text)
            else:
                # Signal in the trace that we are waiting for researcher input
                self.insert_custom_trace_entry(
                    event_type="waiting_for_researcher",
                    event_data={"prompt": text}
                )
                # Get researcher input until it can be converted to the desired type
                converted_input = None
                while converted_input is None:
                    researcher_input = input(text)
                    try:
                        converted_input = self.input_type_converter(researcher_input)
                    except Exception as e:
                        print(f"Could not convert '{researcher_input}' to {self.input_type_name}")
                        print("Please try again.")

            # Store the results
            self.save_data_to_trace_entry({"researcher_input": researcher_input})
            self.set_output(self.store_name, converted_input, can_use_global=True)

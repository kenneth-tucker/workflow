from typing import override
from lib.experiment_parts import Step
from lib.utils.exceptions import ConfigError
from lib.utils.parse_config import extract_data_names, insert_data_values

# Show a prompt and get input
class TerminalStep(Step):
    def __init__(self, context):
        super().__init__(context)
        self.prompt: str = self.get_config("prompt", allow=[str])
        # The type of input the researcher is expected to provide,
        # only show a prompt if not provided
        self.input_type_name: str | None = self.get_config("enter", allow=[str], optional=True)
        # The name of the experiment data to store the input value,
        # should be provided if "enter" is provided
        self.store_name: str | None = self.get_config("to", allow=[str], optional=True)
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
        else:
            if self.store_name:
                raise ConfigError(
                    f"Cannot use 'to' without 'enter' in part '{self.get_full_name()}'"
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
            # Get researcher input and convert it
            converted_input = None
            while converted_input is None:
                researcher_input = input(text)
                try:
                    converted_input = self.input_type_converter(researcher_input)
                except Exception as e:
                    print(f"Could not convert '{researcher_input}' to {self.input_type_name}")
                    print("Please try again.")
            self.set_output(self.store_name, converted_input, can_use_global=True)

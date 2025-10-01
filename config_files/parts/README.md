# Parts Library
A collection of parts that can be loaded into experiments
as flows to help you with common tasks.

## How to Load
In your experiment config file include a table like this
to load in parts during experiment configuration:

[part.some_task]
type_name = "flow.load"
next_part = "part_to_run_after_leaving_the_flow"
[part.some_task.config_values]
path = "path/to/some/task/config_file.toml"

Relative paths are relative to the directory containing
your experiment config file.

Alternatively, you can load in parts dynamically, while
the experiment is running. In this example, the researcher
types in the config file path for the parts they want to
load in:

[part.load_prompt]
type_name = "step.terminal"
next_part = "my_choice"
[part.load_prompt.config_values]
prompt = """
Enter the config file path
> """
enter = "str"
to = "my_path"

[part.my_choice]
type_name = "flow.load"
next_part = "part_to_run_after_leaving_the_flow"
[part.my_choice.input_names]
path = "my_path"

## Flows List
TODO - describe each flow

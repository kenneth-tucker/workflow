# Flows Library
A collection of flows that can be imported into experiments
to help you with common tasks.

## How to Import
In your experiment config file include a table like this:

[part.my_helper]
type_name = "flow.load"
next_part = "part_to_run_after_leaving_the_flow"
[part.my_helper.config_values]
path = "path/to/helper/helper_config_file.toml"

## Flows List
TODO - describe each flow

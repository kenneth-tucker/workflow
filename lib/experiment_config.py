import os
import tomllib
from workflow.lib.utils.exceptions import ConfigError
from workflow.lib.utils.part_utils import PartConfig, PartTypeInfo
from workflow.lib.utils.import_module import import_module_from_path

# The configuration class for the workflow manager,
# initialized from a config TOML file.
class ExperimentConfig:
    # Initialize the experiment config from a TOML file
    def __init__(self, file_path):
        self.file_path = file_path
        self._load_config()
        self._parse_config()
        self._load_part_types()
        self._build_output_dirs()
        self._validate_config()

    # Private helper methods

    def _load_config(self):
        print(f"Loading experiment configuration from '{self.file_path}'...")
        with open(self.file_path, "rb") as f:
            data = tomllib.load(f)
        self.raw_input = data

    def _parse_config(self):
        print("Parsing experiment configuration...")

        # Get the top-level experiment information
        self.experiment_table = self.raw_input.get("experiment")
        if not self.experiment_table:
            raise ConfigError("Missing experiment table in config")
        self.experiment_name = self.experiment_table.get("name")
        self.out_dir_root = self.experiment_table.get("out_dir")
        self.part_types_py = self.experiment_table.get("part_types_py")
        self.initial_part_name = self.experiment_table.get("start")

        # Get the (optional) initial values table
        self.initial_values = self.raw_input.get("initial_values", {})

        # Get the config file information for each of the parts, by
        # recursively parsing the nested tables in the flow table
        self.flow_table = self.raw_input.get("flow", {})
        self.parts = {}
        for top_level_name, top_level_part in self.flow_table.items():
            self.parts.update(
                self._extract_part_configs(
                    top_level_part, path=top_level_name
                )
            )

    def _build_output_dirs(self):
        # Build the output directory structure for this experiment
        # and this particular run
        print("Setting up output directories...")
        self.out_dir_for_experiment = self.out_dir_root + "/" + self.experiment_name + "/"
        os.makedirs(self.out_dir_for_experiment, exist_ok=True)
        existing_runs = [
            d for d in os.listdir(self.out_dir_for_experiment)
            if os.path.isdir(os.path.join(self.out_dir_for_experiment, d)) and d.startswith("run_")
        ]
        # The run number is one larger than the largest existing run number
        self.run_number = max(
            (int(d.split("_")[1]) for d in existing_runs), default=0
        ) + 1
        self.out_dir_for_run = self.out_dir_for_experiment + f"run_{self.run_number}/"
        os.makedirs(self.out_dir_for_run, exist_ok=False)

    def _extract_part_configs(
        self,
        raw_table: dict,
        path: str
    ) -> dict[str, PartConfig]:
        # Helper for _parse_config that extracts nested part configurations
        # recursively and flattens the flow tables into a single dictionary
        # with dot notation (e.g. flow.subflow_1.subflow_2.my_step).

        # Do NOT use these reserved keywords in your part naming
        # (i.e. don't include "type_name" or "config_values" in your part name
        # or it will confuse the configuration parser).
        reserved_keys = {
            "type_name",
            "config_values",
            "input_names",
            "output_names",
            "next_part"
        }

        # Each flow sub-table has a part configuration and possibly nested
        # sub-tables for nested parts. If a member of the table dictionary
        # does not have one of the reserved keys, it is treated as a nested
        # part.
        part = PartConfig(
            name=path,
            raw=raw_table,
            type_name=raw_table.get("type_name"),
            config_values=raw_table.get("config_values", {}),
            input_names=raw_table.get("input_names", {}),
            output_names=raw_table.get("output_names", {}),
            next_part=raw_table.get("next_part", None),
        )
        nested_parts = {}
        for sub_key, sub_value in raw_table.items():
            if sub_key not in reserved_keys:
                nested_parts.update(self._extract_part_configs(sub_value, path=f"{path}.{sub_key}"))

        return {**nested_parts, **{path: part}}

    def _load_part_types(self):
        # Dynamically load the part types from the specified
        # Python file or from the default part type file
        script_path = os.path.abspath(__file__)
        part_types_py = self.part_types_py or os.path.join(script_path, "../part_types/part_types.py")
        print(f"Loading part types from '{part_types_py}'...")
        module = import_module_from_path("workflow.part_types.part_types", part_types_py)
        self.part_types: dict[str, PartTypeInfo] = module.part_types

    def _validate_config(self):
        # Perform checks on various aspects of the
        # experiment configuration, to prevent misconfigurations
        # and tricky bugs during experiment execution
        print("Validating experiment configuration...")
        if not self.experiment_name:
            raise ConfigError("Experiment name is required")
        if not self.out_dir:
            raise ConfigError("Experiment output directory is required")
        if not self.part_types:
            raise ConfigError("Part types must be defined")
        for part_name, part_config in self.parts.items():
            if part_config.type_name not in self.part_types:
                raise ConfigError(f"Unknown part type '{part_config.type_name}' for part '{part_name}'")

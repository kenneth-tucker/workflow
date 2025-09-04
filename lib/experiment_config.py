import os
import tomllib
from lib.utils.parse_config import extract_parts
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartConfig, PartTypeInfo
from lib.utils.import_module import import_module_from_path

# The configuration class for the workflow manager,
# initialized from an experiment's config TOML file.
class ExperimentConfig:
    # Initialize the experiment config from a TOML file
    def __init__(self, file_path: str):
        self.file_path = os.path.normpath(file_path)
        self._load_config()
        self._parse_config()
        self._load_part_types()
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
        if not self.experiment_name:
            raise ConfigError("Missing experiment name in config")
        self.out_dir = self.experiment_table.get("out_dir")
        if not self.out_dir:
            raise ConfigError("Missing experiment output directory in config")
        self.part_types_py = self.experiment_table.get("part_types_py", None)
        self.initial_values = self.experiment_table.get("initial_values", {})

        # Get the config file information for each of the parts
        self.part_table = self.raw_input.get("part")
        if not self.part_table:
            raise ConfigError("Missing part table in config")
        self.initial_part_name = self.part_table.get("start_here", None)
        self.part_configs = extract_parts(self.file_path, self.raw_input)
        if not self.part_configs:
            raise ConfigError("No parts found in config")

    def _load_part_types(self):
        # Dynamically load the part types from the specified
        # Python file or from the default part type file
        script_dir_path = os.path.normpath(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.part_types_py = os.path.normpath(
            self.part_types_py or os.path.join(
                script_dir_path, "../part_types/part_types.py"
            )
        )
        print(f"Loading part types from '{self.part_types_py}'...")
        module = import_module_from_path(
            "workflow.part_types.part_types", self.part_types_py
        )
        self.part_types: dict[str, PartTypeInfo] = module.part_types

    def _validate_config(self):
        # Perform checks on various aspects of the
        # experiment configuration, to prevent misconfigurations
        # and tricky bugs during experiment execution
        for part_name, part_config in self.part_configs.items():
            if part_config.type_name not in self.part_types:
                raise ConfigError(f"Unknown part type '{part_config.type_name}' for part '{part_name}'")

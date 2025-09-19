import os
import tomllib
from lib.utils.parse_config import extract_part_configs
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartConfig, PartTypeInfo
from lib.utils.import_module import import_module_from_path

class ExperimentConfig:
    """
    The configuration class for the workflow manager,
    initialized from an experiment's config TOML file.
    """
    def __init__(self, file_path: str):
        """
        Initialize the experiment config from a TOML file.
        """
        self.file_path = os.path.normpath(file_path)
        self._load_config()
        self._parse_config()
        self._load_part_types()
        self._validate_config()

    # Private helper methods

    def _load_config(self):
        print(f"Loading experiment configuration from '{self.file_path}'...", flush=True)
        with open(self.file_path, "rb") as f:
            data = tomllib.load(f)
        self.raw_input = data

    def _parse_config(self):
        print("Parsing experiment configuration...", flush=True)

        # Get the top-level experiment information
        self.experiment_table = self.raw_input.get("experiment")
        if not self.experiment_table:
            raise ConfigError("Missing experiment table in config")
        self.experiment_name = self.experiment_table.get("name")
        if not self.experiment_name:
            raise ConfigError("Missing experiment name in config")
        out_dir_raw = self.experiment_table.get("out_dir")
        if not out_dir_raw:
            raise ConfigError("Missing experiment output directory in config")
        # If the output directory path is a relative path, then
        # it is relative to the directory of this config file
        if not os.path.isabs(out_dir_raw):
            self.out_dir = os.path.normpath(
                os.path.join(os.path.dirname(self.file_path), out_dir_raw)
            )
        else:
            self.out_dir = os.path.normpath(out_dir_raw)
        self.part_types_py = self.experiment_table.get("part_types_py", None)
        self.initial_values = self.experiment_table.get("initial_values", {})

        # Get the config file information for each of the parts
        self.part_table = self.raw_input.get("part")
        if not self.part_table:
            raise ConfigError("Missing part table in config")
        self.initial_part_name = self.part_table.get("start_here", None)
        self.part_configs = extract_part_configs(self.file_path, self.part_table, "")
        if not self.part_configs:
            raise ConfigError("No parts found in config")

    def _load_part_types(self):
        """
        Load the part types from the specified Python file.
        """
        script_dir_path = os.path.normpath(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.part_types_py = os.path.normpath(
            self.part_types_py or os.path.join(
                script_dir_path, "../part_types/part_types.py"
            )
        )
        print(f"Loading part types from '{self.part_types_py}'...", flush=True)
        module = import_module_from_path(
            "workflow.part_types.part_types", self.part_types_py
        )
        self.part_types: dict[str, PartTypeInfo] = module.part_types

    def _validate_config(self):
        """
        Validate the experiment configuration.
        """
        print("Validating experiment configuration...", flush=True)
        for part_full_name, part_config in self.part_configs.items():
            if part_config.type_name not in self.part_types:
                raise ConfigError(f"Unknown part type '{part_config.type_name}' for part '{part_full_name}'")
        # TODO do more thorough validation (including inputs/outputs being right for type)
        # TODO check each nested part has a flow parent
        # TODO check all next_part references are short names, contain no dots, and refer
        # to valid part names
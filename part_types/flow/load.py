import os
import tomllib
from typing import override
from lib.experiment_parts import Flow
from lib.utils.exceptions import ConfigError
from lib.utils.parse_config import extract_part_configs

class LoadFlow(Flow):
    """
    A flow part that loads parts from a TOML config file.
    The path to the config file can be given as a config value
    (loaded one time when the flow is constructed), or from
    the path given as an input variable to the flow (loaded
    each time the flow begins).
    """
    def __init__(self, context):
        super().__init__(context)
        self.initial_part_name = None
        path: str | None = self.get_config(
            "path", allow=[str], optional=True
        )
        if path:
            self._load_parts_from_file(path)

    @override
    def begin_flow(self) -> str | None:
        path: str | None = self.get_input(
            "path", allow=[str], optional=True
        )
        if path:
            self._load_parts_from_file(path)
        # If a path input is specified then try to load that
        return self.initial_part_name

    @override
    def end_flow(self) -> None:
        return

    # Private helpers

    def _load_parts_from_file(self, path: str):
        """
        Load parts from a TOML config file at the given path.

        If the path is relative, it is relative to the config file that
        defined this LoadFlow part. Any old parts are removed first.
        """
        try:
            old_part_names = self.list_part_names()
            for part_name in old_part_names:
                self.remove_part(part_name)
            if not os.path.isabs(path):
                absolute_path = os.path.normpath(
                    os.path.join(os.path.dirname(self.get_config_file_path()), path)
                )
            else:
                absolute_path = os.path.normpath(path)
            with open(absolute_path, "rb") as f:
                raw_input = tomllib.load(f)
            part_table = raw_input.get("part")
            if not part_table:
                raise ConfigError(
                    f"No part table found in '{absolute_path}'"
                )
            self.initial_part_name = part_table.get("start_here", None)
            part_configs = extract_part_configs(
                absolute_path,
                part_table,
                self.get_full_name()
            )
            if not part_configs:
                raise ConfigError(f"No parts found in '{absolute_path}'")
            for part_name, part_config in part_configs.items():
                self.add_part(part_config)
            # TODO validate the loaded parts more thoroughly
        except Exception as e:
            raise ConfigError(f"Failed to load parts from '{path}' for {self.get_full_name()}: {e}")

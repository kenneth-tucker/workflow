"""
Shared fixtures for the test suite.
"""
from copy import deepcopy

import pytest

from lib.utils.part_utils import PartConfig, PartContext


class FakeManager:
    """
    A minimal stand-in for ExperimentManager.

    Implements the private API surface that _Part/Step/Decision/Flow call,
    backed by plain dicts/lists so tests can seed inputs and assert on
    outputs easily, without needing a real ExperimentManager/trace file.
    """
    def __init__(self, data: dict | None = None, old_trace_part_data: dict | None = None):
        # Experiment data, read/written via get_input/set_output
        self.data: dict = data or {}
        # part_data recorded by the *previous* retrace entry for the part
        # under test, returned from load_data_from_retrace_entry()
        self.old_trace_part_data: dict | None = old_trace_part_data
        # part_data most recently passed to save_data_to_trace_entry()
        self.saved_trace_part_data: dict | None = None
        # (event_type, event_data) pairs passed to insert_custom_trace_entry()
        self.custom_trace_entries: list[tuple[str, dict | None]] = []
        # full_name -> PartConfig, for Flow.add_part/remove_part/get_part/list_part_names
        self.parts: dict = {}
        # Stand-in for ExperimentManager.out_dir_for_run, used by get_output_file_path()
        self.out_dir_for_run: str = "<test_out_dir>"

    def _get_data(self, global_name: str):
        return self.data.get(global_name)

    def _set_data(self, global_name: str, value: object) -> None:
        self.data[global_name] = value

    def _copy_experiment_data(self) -> dict:
        return deepcopy(self.data)

    def _save_data_to_trace_entry(self, part_data: dict) -> None:
        self.saved_trace_part_data = part_data

    def _load_data_from_retrace_entry(self) -> dict | None:
        return self.old_trace_part_data

    def _insert_custom_trace_entry(self, event_type: str, event_data: dict | None) -> None:
        self.custom_trace_entries.append((event_type, event_data))

    def _add_part(self, part_config: PartConfig) -> None:
        self.parts[part_config.full_name] = part_config

    def _remove_part(self, part_full_name: str) -> None:
        self.parts.pop(part_full_name, None)

    def _get_part(self, part_full_name: str):
        return self.parts.get(part_full_name)

    def _get_flow_parts_short_names(self, flow_full_name: str) -> list[str]:
        prefix = f"{flow_full_name}."
        return [
            name[len(prefix):] for name in self.parts
            if name.startswith(prefix) and "." not in name[len(prefix):]
        ]


@pytest.fixture
def fake_manager() -> FakeManager:
    return FakeManager()


@pytest.fixture
def make_part_context(fake_manager: FakeManager):
    """
    Factory fixture for building a PartContext against the fake_manager.

    Returns a function so each test can customize the config for the
    part it is constructing, e.g.:

        context = make_part_context(config_values={"statements": [...]})
    """
    def _make(
        file_path: str = "<test>",
        type_name: str = "test.part",
        full_name: str = "test_part",
        config_values: dict | None = None,
        input_names: dict | None = None,
        output_names: dict | None = None,
        next_part: dict | None = None,
        first_part: str | None = None,
    ) -> PartContext:
        config = PartConfig(
            file_path=file_path,
            full_name=full_name,
            raw={},
            type_name=type_name,
            next_part=next_part or {},
            first_part=first_part,
            config_values=config_values or {},
            input_names=input_names or {},
            output_names=output_names or {},
        )
        return PartContext(manager=fake_manager, config=config)
    return _make


@pytest.fixture
def write_toml(tmp_path):
    """
    Factory fixture that writes TOML text to a temp file (via pytest's
    built-in tmp_path fixture) and returns its Path. Using a real file
    on disk (rather than mocking open()) means these tests exercise the
    same code path ExperimentConfig uses in production.
    """
    def _write(content: str, filename: str = "config.toml"):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path
    return _write

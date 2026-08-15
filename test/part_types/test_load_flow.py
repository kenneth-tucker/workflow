"""
Tests for part_types/flow/load.py (LoadFlow)
"""
import pytest

from lib.utils.exceptions import ConfigError
from part_types.flow.load import LoadFlow


def make_load_flow(
    make_part_context,
    file_path: str = "<test>",
    config_values=None,
    input_names=None,
):
    context = make_part_context(
        file_path=file_path,
        config_values=config_values or {},
        input_names=input_names or {},
    )
    return LoadFlow(context)


class TestLoadFlowConstruction:
    def test_loads_parts_immediately_when_path_config_given(self, make_part_context, fake_manager, write_toml):
        part_file_path = write_toml(
            "[part]\n"
            "[part.part1]\n"
            "type_name = \"step.expression\"\n"
            "[part.part1.config_values]\n"
            "statements = [\"x = 1\"]\n",
            filename="test_parts.toml"
        )
        flow = make_load_flow(make_part_context, config_values={"path": str(part_file_path)})
        assert "part1" in flow.list_part_names()
        route = flow.begin_flow()
        assert route.first_part is None  # no first_part specified in the part file

    def test_relative_path_is_resolved_against_the_defining_config_files_directory(
        self, make_part_context, fake_manager, write_toml, tmp_path
    ):
        write_toml(
            "[part]\n"
            "[part.part1]\n"
            "type_name = \"step.expression\"\n"
            "[part.part1.config_values]\n"
            "statements = [\"x = 1\"]\n",
            filename="relative_parts.toml"
        )
        defining_file_path = str(tmp_path / "main_config.toml")
        flow = make_load_flow(
            make_part_context,
            file_path=defining_file_path,
            config_values={"path": "relative_parts.toml"},
        )
        assert "part1" in flow.list_part_names()

    def test_does_not_load_anything_when_path_config_absent(self, make_part_context, fake_manager):
        flow = make_load_flow(make_part_context, config_values={})
        assert flow.list_part_names() == []


class TestLoadFlowBeginFlow:
    def test_begin_flow_loads_parts_from_input_path(self, make_part_context, fake_manager, write_toml):
        part_file_path = write_toml(
            "[part]\n"
            "first_part = \"part1\"\n"
            "[part.part1]\n"
            "type_name = \"step.expression\"\n"
            "[part.part1.config_values]\n"
            "statements = [\"x = 1\"]\n",
            filename="test_parts.toml"
        )
        fake_manager.data["part_path"] = str(part_file_path)
        flow = make_load_flow(make_part_context, input_names={"path": "part_path"})
        assert flow.list_part_names() == []
        route = flow.begin_flow()
        assert "part1" in flow.list_part_names()
        assert route.first_part == "part1"

    def test_reloading_removes_previously_loaded_parts_first(self, make_part_context, fake_manager, write_toml):
        part_file_path1 = write_toml(
            "[part]\n"
            "[part.part1]\n"
            "type_name = \"step.expression\"\n"
            "[part.part1.config_values]\n"
            "statements = [\"x = 1\"]\n",
            filename="test_parts1.toml"
        )
        part_file_path2 = write_toml(
            "[part]\n"
            "[part.part2]\n"
            "type_name = \"step.expression\"\n"
            "[part.part2.config_values]\n"
            "statements = [\"y = 2\"]\n",
            filename="test_parts2.toml"
        )
        fake_manager.data["part_path"] = str(part_file_path1)
        flow = make_load_flow(make_part_context, input_names={"path": "part_path"})
        assert "part2" not in flow.list_part_names()
        route1 = flow.begin_flow()
        assert "part1" in flow.list_part_names()
        assert "part2" not in flow.list_part_names()
        fake_manager.data["part_path"] = str(part_file_path2)
        route2 = flow.begin_flow()
        assert "part1" not in flow.list_part_names()
        assert "part2" in flow.list_part_names()


class TestLoadFlowErrors:
    def test_missing_part_table_raises_config_error(self, make_part_context, fake_manager, write_toml):
        part_file_path = write_toml(
            "[experiment]\n"
            "name = \"my_experiment\"\n"
            "out_dir = \"results\"\n",
            filename="test_parts.toml"
        )
        flow = make_load_flow(make_part_context, input_names={"path": "part_path"})
        fake_manager.data["part_path"] = str(part_file_path)
        with pytest.raises(ConfigError, match="No part table found"):
            flow.begin_flow()

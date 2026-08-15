"""
Tests for lib/utils/part_utils.py (PartTypeInfo, PartConfig, PartContext,
DecisionRoute, BeginFlowRoute).
"""
from lib.utils.part_utils import (
    BeginFlowRoute,
    DecisionRoute,
    PartConfig,
    PartContext,
    PartTypeInfo,
)


class TestPartTypeInfo:
    def test_stores_type_and_description(self):
        info = PartTypeInfo(type=str, description="A description")
        assert info.type is str
        assert info.description == "A description"

    def test_description_defaults_to_none(self):
        info = PartTypeInfo(type=str)
        assert info.description is None


class TestPartConfig:
    def test_stores_all_constructor_arguments_as_attributes(self):
        config = PartConfig(
            file_path="config.toml",
            full_name="flow1.step1",
            raw={"type_name": "step.terminal"},
            type_name="step.terminal",
            next_part={"": "step2"},
            first_part="step1",
            config_values={"prompt": "Hi"},
            input_names={"x": "global_x"},
            output_names={"y": "global_y"},
        )

        assert config.file_path == "config.toml"
        assert config.full_name == "flow1.step1"
        assert config.raw == {"type_name": "step.terminal"}
        assert config.type_name == "step.terminal"
        assert config.next_part == {"": "step2"}
        assert config.first_part == "step1"
        assert config.config_values == {"prompt": "Hi"}
        assert config.input_names == {"x": "global_x"}
        assert config.output_names == {"y": "global_y"}


class TestPartContext:
    def test_stores_manager_and_config(self):
        manager = object()
        config = PartConfig(
            file_path="config.toml",
            full_name="step1",
            raw={},
            type_name="step.terminal",
            next_part={},
            first_part=None,
            config_values={},
            input_names={},
            output_names={},
        )

        context = PartContext(manager=manager, config=config)

        assert context.manager is manager
        assert context.config is config


class TestDecisionRoute:
    def test_can_use_part_name_defaults_to_false(self):
        route = DecisionRoute(route_name="route_a")
        assert route.can_use_part_name is False

    def test_stores_route_name(self):
        route = DecisionRoute(route_name="route_a", can_use_part_name=True)
        assert route.route_name == "route_a"
        assert route.can_use_part_name is True


class TestBeginFlowRoute:
    def test_stores_first_part(self):
        route = BeginFlowRoute(first_part="step1")
        assert route.first_part == "step1"

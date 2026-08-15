"""
Tests for lib/experiment_parts.py (the _Part base class and the Step /
Decision / Flow base classes).
"""
import os

import pytest

from lib.experiment_parts import Decision, Flow, Step
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartConfig


class TestGetConfig:
    def test_returns_value_when_present(self, make_part_context):
        step = Step(make_part_context(config_values={"x": 5}))

        assert step.get_config("x") == 5

    def test_raises_config_error_when_missing_and_required(self, make_part_context):
        step = Step(make_part_context(config_values={}))

        with pytest.raises(ConfigError):
            step.get_config("missing")

    def test_returns_none_when_missing_and_optional(self, make_part_context):
        step = Step(make_part_context(config_values={}))

        assert step.get_config("missing", optional=True) is None

    def test_raises_config_error_when_type_not_in_allow_list(self, make_part_context):
        step = Step(make_part_context(config_values={"x": "a string"}))

        with pytest.raises(ConfigError):
            step.get_config("x", allow=[int])

    def test_accepts_value_matching_any_type_in_allow_list(self, make_part_context):
        step = Step(make_part_context(config_values={"x": 5}))

        assert step.get_config("x", allow=[int, str]) == 5


class TestGetInput:
    def test_raises_config_error_when_unmapped_and_required(self, make_part_context):
        step = Step(make_part_context(input_names={}))

        with pytest.raises(ConfigError):
            step.get_input("x")

    def test_returns_none_when_unmapped_and_optional(self, make_part_context):
        step = Step(make_part_context(input_names={}))

        assert step.get_input("x", optional=True) is None

    def test_can_use_global_falls_back_to_argument_name(self, make_part_context, fake_manager):
        fake_manager.data["x"] = 10
        step = Step(make_part_context(input_names={}))

        assert step.get_input("x", can_use_global=True) == 10

    def test_can_use_global_returns_none_when_global_also_missing(self, make_part_context, fake_manager):
        step = Step(make_part_context(input_names={}))

        assert step.get_input("x", can_use_global=True) is None

    def test_raises_value_error_when_mapped_value_has_wrong_type(self, make_part_context, fake_manager):
        # Note: unlike get_config's type mismatch (ConfigError), get_input
        # raises ValueError for a type mismatch.
        fake_manager.data["x"] = "not an int"
        step = Step(make_part_context(input_names={"arg": "x"}))

        with pytest.raises(ValueError):
            step.get_input("arg", allow=[int])


class TestSetOutput:
    def test_raises_config_error_when_unmapped_and_required(self, make_part_context):
        step = Step(make_part_context(output_names={}))

        with pytest.raises(ConfigError):
            step.set_output("y", 5)

    def test_does_nothing_when_unmapped_and_optional(self, make_part_context, fake_manager):
        step = Step(make_part_context(output_names={}))

        step.set_output("y", 5, optional=True)

        assert fake_manager.data == {}

    def test_stores_value_under_mapped_output_name(self, make_part_context, fake_manager):
        step = Step(make_part_context(output_names={"y": "global_y"}))

        step.set_output("y", 42)

        assert fake_manager._get_data("global_y") == 42

    def test_can_use_global_falls_back_to_argument_name(self, make_part_context, fake_manager):
        step = Step(make_part_context(output_names={}))

        step.set_output("y", 42, can_use_global=True)

        assert fake_manager._get_data("y") == 42


class TestPartHelperMethods:
    def test_copy_experiment_data_returns_independent_copy(self, make_part_context, fake_manager):
        fake_manager.data = {"a": {"b": 1}}
        step = Step(make_part_context())

        copy = step.copy_experiment_data()
        copy["a"]["b"] = 999

        assert fake_manager.data["a"]["b"] == 1

    def test_save_and_load_data_from_retrace_entry_round_trip(self, make_part_context, fake_manager):
        step = Step(make_part_context())

        step.save_data_to_trace_entry({"k": 1})
        assert fake_manager.saved_trace_part_data == {"k": 1}

        fake_manager.old_trace_part_data = {"k": 2}
        assert step.load_data_from_retrace_entry() == {"k": 2}

    def test_insert_custom_trace_entry_forwards_to_manager(self, make_part_context, fake_manager):
        step = Step(make_part_context())

        step.insert_custom_trace_entry("evt", {"a": 1})

        assert fake_manager.custom_trace_entries == [("evt", {"a": 1})]

    def test_get_full_name_returns_configured_full_name(self, make_part_context):
        step = Step(make_part_context(full_name="flow.step1"))

        assert step.get_full_name() == "flow.step1"

    def test_get_output_file_path_with_and_without_relative_path(self, make_part_context, fake_manager):
        step = Step(make_part_context())

        assert step.get_output_file_path() == fake_manager.out_dir_for_run
        assert step.get_output_file_path("sub/file.txt") == os.path.join(
            fake_manager.out_dir_for_run, os.path.normpath("sub/file.txt")
        )


class TestAbstractMethodsRaiseNotImplementedError:
    def test_step_run_step_raises_not_implemented_error(self, make_part_context):
        step = Step(make_part_context())

        with pytest.raises(NotImplementedError):
            step.run_step()

    def test_decision_decide_route_raises_not_implemented_error(self, make_part_context):
        decision = Decision(make_part_context())

        with pytest.raises(NotImplementedError):
            decision.decide_route()

    def test_flow_begin_flow_raises_not_implemented_error(self, make_part_context):
        flow = Flow(make_part_context())

        with pytest.raises(NotImplementedError):
            flow.begin_flow()

    def test_flow_end_flow_raises_not_implemented_error(self, make_part_context):
        flow = Flow(make_part_context())

        with pytest.raises(NotImplementedError):
            flow.end_flow()


def make_part_config(full_name: str) -> PartConfig:
    return PartConfig(
        file_path="<test>",
        full_name=full_name,
        raw={},
        type_name="step.terminal",
        next_part={},
        first_part=None,
        config_values={},
        input_names={},
        output_names={},
    )


class TestFlowPartManagementHelpers:
    def test_add_part_rejects_full_name_outside_flow(self, make_part_context, fake_manager):
        # part_config.full_name must start with "<flow full name>."
        flow = Flow(make_part_context(full_name="my_flow"))
        part_config = make_part_config("other_flow.part1")

        with pytest.raises(ConfigError):
            flow.add_part(part_config)

    def test_add_part_delegates_to_manager(self, make_part_context, fake_manager):
        flow = Flow(make_part_context(full_name="my_flow"))
        part_config = make_part_config("my_flow.part1")

        flow.add_part(part_config)

        assert fake_manager.parts["my_flow.part1"] is part_config

    def test_remove_part_delegates_to_manager(self, make_part_context, fake_manager):
        flow = Flow(make_part_context(full_name="my_flow"))
        fake_manager.parts["my_flow.part1"] = make_part_config("my_flow.part1")

        flow.remove_part("part1")

        assert "my_flow.part1" not in fake_manager.parts

    def test_list_part_names_delegates_to_manager(self, make_part_context, fake_manager):
        flow = Flow(make_part_context(full_name="my_flow"))
        fake_manager.parts["my_flow.a"] = make_part_config("my_flow.a")
        fake_manager.parts["my_flow.b"] = make_part_config("my_flow.b")

        assert sorted(flow.list_part_names()) == ["a", "b"]

    def test_get_part_delegates_to_manager_with_full_name(self, make_part_context, fake_manager):
        flow = Flow(make_part_context(full_name="my_flow"))
        part_config = make_part_config("my_flow.part1")
        fake_manager.parts["my_flow.part1"] = part_config

        assert flow.get_part("part1") is part_config

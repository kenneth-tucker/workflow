"""
Integration tests for lib/experiment_manager.py (ExperimentManager) - runs
a full experiment path across real ExperimentConfig + ExperimentTrace +
part-type objects (no fakes).
"""
import os

import pytest

from lib.experiment_config import ExperimentConfig
from lib.experiment_manager import ExperimentManager, ExperimentMode
from lib.experiment_trace import (
    ErrorEntry,
    ExperimentBeginEntry,
    ExperimentEndEntry,
    ExperimentTrace,
    FlowBeginEntry,
    FlowEndEntry,
    PartAddEntry,
)


def make_manager(write_toml, config_toml: str, filename: str = "config.toml") -> ExperimentManager:
    """Write `config_toml` to a file and build an ExperimentManager for it."""
    config_path = write_toml(config_toml, filename=filename)
    config = ExperimentConfig(str(config_path))
    return ExperimentManager(config)


def refuse_to_be_called(*args, **kwargs):
    """A stand-in for input() that fails the test if it is ever called."""
    raise AssertionError("input() should not have been called")


LINEAR_CONFIG = """
[experiment]
name = "linear_experiment"
out_dir = "results"

[experiment.initial_values]
a = 2
b = 3

[part]
first_part = "compute"

[part.compute]
type_name = "step.expression"
next_part = "quit"

[part.compute.config_values]
statements = ["total = {a} + {b}"]
"""


def decision_config(x_value: int) -> str:
    return f"""
[experiment]
name = "decision_experiment"
out_dir = "results"

[experiment.initial_values]
x = {x_value}

[part]
first_part = "check"

[part.check]
type_name = "decision.conditional"

[part.check.config_values]
statements = ["route_high if {{x}} > 10", "else route_low"]

[part.check.next_part]
route_high = "high"
route_low = "low"

[part.high]
type_name = "step.expression"
next_part = "quit"

[part.high.config_values]
statements = ["result = 'high'"]

[part.low]
type_name = "step.expression"
next_part = "quit"

[part.low.config_values]
statements = ["result = 'low'"]
"""


class TestNormalRun:
    def test_runs_a_simple_linear_flow_to_completion(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)
        manager.run(ExperimentMode.NORMAL)
        assert manager.experiment_data["total"] == 5

    def test_decision_step_branches_to_the_correct_next_part(self, write_toml):
        manager = make_manager(write_toml, decision_config(x_value=15))
        manager.run(ExperimentMode.NORMAL)
        assert manager.experiment_data["result"] == "high"
        trace_path = os.path.join(manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=trace_path)
        part_names = [piece.part_name for piece in reloaded.get_part_path()]
        assert "high" in part_names
        assert "low" not in part_names

    def test_trace_file_records_experiment_begin_and_end_entries(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)
        manager.run(ExperimentMode.NORMAL)
        trace_path = os.path.join(manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=trace_path)
        begin_entries = [entry for entry in reloaded.trace if isinstance(entry, ExperimentBeginEntry)]
        end_entries = [entry for entry in reloaded.trace if isinstance(entry, ExperimentEndEntry)]
        assert len(begin_entries) == 1
        assert begin_entries[0].experiment_name == "linear_experiment"
        assert len(end_entries) == 1
        assert reloaded.trace.index(begin_entries[0]) < reloaded.trace.index(end_entries[0])

    def test_run_number_increments_across_successive_runs(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)

        manager.run(ExperimentMode.NORMAL)
        assert manager.run_number == 1
        first_run_dir = manager.out_dir_for_run

        manager.run(ExperimentMode.NORMAL)
        assert manager.run_number == 2
        second_run_dir = manager.out_dir_for_run

        assert first_run_dir != second_run_dir
        assert os.path.isdir(first_run_dir)
        assert os.path.isdir(second_run_dir)


class TestErrorHandling:
    def test_error_in_a_step_records_error_entry_and_stops_before_committing_data(
        self, write_toml, monkeypatch
    ):
        # Experiment data changes made by a part should only be committed
        # after that part completes successfully (see _run_part's use of
        # self.new_experiment_data vs self.experiment_data).
        config_toml = """
[experiment]
name = "error_experiment"
out_dir = "results"

[experiment.initial_values]
a = 1

[part]
first_part = "boom"

[part.boom]
type_name = "step.expression"
next_part = "after"

[part.boom.config_values]
statements = ["bad = 1 / 0"]

[part.after]
type_name = "step.expression"
next_part = "quit"

[part.after.config_values]
statements = ["after_ran = 1"]
"""
        manager = make_manager(write_toml, config_toml)
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "quit")

        manager.run(ExperimentMode.NORMAL)

        assert "bad" not in manager.experiment_data
        assert "after_ran" not in manager.experiment_data

        trace_path = os.path.join(manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=trace_path)
        error_entries = [entry for entry in reloaded.trace if isinstance(entry, ErrorEntry)]
        assert len(error_entries) == 1
        assert error_entries[0].part_name == "boom"


class TestRerunAndContinueModes:
    def test_rerun_mode_retraces_the_same_path_as_the_old_trace(self, write_toml, monkeypatch):
        config_path = write_toml(LINEAR_CONFIG)
        config = ExperimentConfig(str(config_path))

        first_manager = ExperimentManager(config)
        first_manager.run(ExperimentMode.NORMAL)
        old_trace_path = os.path.join(first_manager.out_dir_for_run, "trace.json")
        old_trace = ExperimentTrace(input_file_path=old_trace_path)

        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        second_manager = ExperimentManager(config)
        second_manager.run(ExperimentMode.RERUN, old_trace=old_trace)

        assert second_manager.experiment_data["total"] == 5
        new_trace_path = os.path.join(second_manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=new_trace_path)
        old_part_names = [piece.part_name for piece in old_trace.get_part_path()]
        new_part_names = [piece.part_name for piece in reloaded.get_part_path()]
        assert new_part_names == old_part_names

    def test_rerun_mode_raises_on_path_deviation_from_old_trace(self, write_toml):
        old_config_path = write_toml(decision_config(x_value=15), filename="old_config.toml")
        old_manager = ExperimentManager(ExperimentConfig(str(old_config_path)))
        old_manager.run(ExperimentMode.NORMAL)
        old_trace_path = os.path.join(old_manager.out_dir_for_run, "trace.json")
        old_trace = ExperimentTrace(input_file_path=old_trace_path)

        new_config_path = write_toml(decision_config(x_value=5), filename="new_config.toml")
        new_manager = ExperimentManager(ExperimentConfig(str(new_config_path)))

        with pytest.raises(RuntimeError, match="Path deviation"):
            new_manager.run(ExperimentMode.RERUN, old_trace=old_trace)

    def test_continue_mode_resumes_after_the_end_of_the_old_trace(self, write_toml, monkeypatch):
        config_toml = """
[experiment]
name = "continue_experiment"
out_dir = "results"

[part]
first_part = "stepA"

[part.stepA]
type_name = "step.expression"

[part.stepA.config_values]
statements = ["first_ran = 1"]

[part.stepB]
type_name = "step.expression"
next_part = "quit"

[part.stepB.config_values]
statements = ["second_ran = 1"]
"""
        config_path = write_toml(config_toml)
        config = ExperimentConfig(str(config_path))

        first_manager = ExperimentManager(config)
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "quit")
        first_manager.run(ExperimentMode.NORMAL)
        assert "second_ran" not in first_manager.experiment_data
        old_trace_path = os.path.join(first_manager.out_dir_for_run, "trace.json")
        old_trace = ExperimentTrace(input_file_path=old_trace_path)

        second_manager = ExperimentManager(config)
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "stepB")
        second_manager.run(ExperimentMode.CONTINUE, old_trace=old_trace)

        assert second_manager.experiment_data["first_ran"] == 1
        assert second_manager.experiment_data["second_ran"] == 1


class TestModeValidation:
    def test_normal_mode_with_old_trace_raises_value_error(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)

        with pytest.raises(ValueError):
            manager.run(ExperimentMode.NORMAL, old_trace=ExperimentTrace())

    def test_rerun_mode_without_old_trace_raises_value_error(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)

        with pytest.raises(ValueError):
            manager.run(ExperimentMode.RERUN, old_trace=None)


class TestOutputDirectory:
    def test_run_directory_contains_config_copy_and_trace_file(self, write_toml):
        manager = make_manager(write_toml, LINEAR_CONFIG)

        manager.run(ExperimentMode.NORMAL)

        assert os.path.isfile(os.path.join(manager.out_dir_for_run, "config.toml"))
        assert os.path.isfile(os.path.join(manager.out_dir_for_run, "trace.json"))

    def test_on_output_dir_built_callback_receives_run_directory(self, write_toml):
        config_path = write_toml(LINEAR_CONFIG)
        config = ExperimentConfig(str(config_path))
        received_dirs = []
        manager = ExperimentManager(config, on_output_dir_built=received_dirs.append)

        manager.run(ExperimentMode.NORMAL)

        assert received_dirs == [manager.out_dir_for_run]


class TestResearcherDecisions:
    RESEARCHER_DECISION_CONFIG = """
[experiment]
name = "researcher_decision_experiment"
out_dir = "results"

[part]
first_part = "only_step"

[part.only_step]
type_name = "step.expression"

[part.only_step.config_values]
statements = ["ran = 1"]

[part.next_step]
type_name = "step.expression"
next_part = "quit"

[part.next_step.config_values]
statements = ["next_ran = 1"]
"""

    def test_prompts_researcher_when_next_part_is_unresolved(self, write_toml, monkeypatch):
        manager = make_manager(write_toml, self.RESEARCHER_DECISION_CONFIG)
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "next_step")

        manager.run(ExperimentMode.NORMAL)

        assert manager.experiment_data["ran"] == 1
        assert manager.experiment_data["next_ran"] == 1

    def test_retries_after_an_invalid_researcher_response(self, write_toml, monkeypatch, capsys):
        manager = make_manager(write_toml, self.RESEARCHER_DECISION_CONFIG)
        responses = iter(["bogus_name", "next_step"])
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(responses))

        manager.run(ExperimentMode.NORMAL)

        assert manager.experiment_data["next_ran"] == 1
        assert "bogus_name" in capsys.readouterr().out


class TestNestedFlows:
    def test_nested_flow_records_flow_begin_and_end_entries(self, write_toml):
        config_toml = """
[experiment]
name = "nested_flow_experiment"
out_dir = "results"

[part]
first_part = "outer"

[part.outer]
type_name = "flow.standard"
first_part = "inner_step"
next_part = "quit"

[part.outer.inner_step]
type_name = "step.expression"
next_part = "done"

[part.outer.inner_step.config_values]
statements = ["inner_ran = 1"]
"""
        manager = make_manager(write_toml, config_toml)

        manager.run(ExperimentMode.NORMAL)

        assert manager.experiment_data["inner_ran"] == 1
        trace_path = os.path.join(manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=trace_path)
        assert any(isinstance(entry, FlowBeginEntry) for entry in reloaded.trace)
        assert any(isinstance(entry, FlowEndEntry) for entry in reloaded.trace)


class TestDynamicParts:
    def test_flow_load_records_part_add_entry_for_loaded_parts(self, write_toml):
        write_toml(
            """
[part]
first_part = "loaded_step"

[part.loaded_step]
type_name = "step.expression"
next_part = "done"

[part.loaded_step.config_values]
statements = ["loaded_ran = 1"]
""",
            filename="loaded_parts.toml",
        )
        config_toml = """
[experiment]
name = "dynamic_parts_experiment"
out_dir = "results"

[part]
first_part = "loader"

[part.loader]
type_name = "flow.load"
next_part = "quit"

[part.loader.config_values]
path = "loaded_parts.toml"
"""
        manager = make_manager(write_toml, config_toml)

        manager.run(ExperimentMode.NORMAL)

        assert manager.experiment_data["loaded_ran"] == 1
        trace_path = os.path.join(manager.out_dir_for_run, "trace.json")
        reloaded = ExperimentTrace(input_file_path=trace_path)
        part_add_entries = [entry for entry in reloaded.trace if isinstance(entry, PartAddEntry)]
        assert any(entry.full_name == "loader.loaded_step" for entry in part_add_entries)


class TestRetraceDataFlow:
    def test_rerun_reuses_researcher_input_recorded_in_the_old_trace(self, write_toml, monkeypatch):
        config_toml = """
[experiment]
name = "retrace_experiment"
out_dir = "results"

[part]
first_part = "ask"

[part.ask]
type_name = "step.terminal"
next_part = "quit"

[part.ask.config_values]
prompt = "Enter a number: "
enter = "int"
to = "answer"
"""
        config_path = write_toml(config_toml)
        config = ExperimentConfig(str(config_path))

        first_manager = ExperimentManager(config)
        monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "42")
        first_manager.run(ExperimentMode.NORMAL)
        assert first_manager.experiment_data["answer"] == 42
        old_trace_path = os.path.join(first_manager.out_dir_for_run, "trace.json")
        old_trace = ExperimentTrace(input_file_path=old_trace_path)

        second_manager = ExperimentManager(config)
        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        second_manager.run(ExperimentMode.RERUN, old_trace=old_trace)

        assert second_manager.experiment_data["answer"] == 42

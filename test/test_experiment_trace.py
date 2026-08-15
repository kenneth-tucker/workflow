"""
Tests for lib/experiment_trace.py (ExperimentTrace and its TraceEntry
subclasses) - reads/writes the JSON trace file and reconstructs the path
taken through an experiment.
"""
from datetime import datetime, timedelta

import pytest

from lib.experiment_trace import (
    AtPartEntry,
    CustomEntry,
    ExperimentBeginEntry,
    ExperimentEndEntry,
    ExperimentTrace,
    PartAddEntry,
    StepEntry,
)

BASE_TIME = datetime(2024, 1, 1, 0, 0, 0)


def at_time(seconds: int) -> datetime:
    return BASE_TIME + timedelta(seconds=seconds)


class TestExperimentTraceBasics:
    def test_new_trace_with_no_input_file_starts_empty(self, tmp_path):
        trace = ExperimentTrace()

        assert trace.trace == []

    def test_record_appends_entry_to_in_memory_trace(self, tmp_path):
        trace = ExperimentTrace(output_file_path=str(tmp_path / "trace.json"))
        entry = AtPartEntry(at_time(0), "step1")

        trace.record(entry)

        assert trace.trace == [entry]

    def test_record_streams_entry_as_json_to_output_file(self, tmp_path):
        output_path = tmp_path / "trace.json"

        with ExperimentTrace(output_file_path=str(output_path)) as trace:
            trace.record(AtPartEntry(at_time(0), "step1"))

        content = output_path.read_text(encoding="utf-8")
        assert '"event": "at_part"' in content
        assert '"part_name": "step1"' in content

    def test_part_add_entry_rejects_invalid_part_category(self):
        with pytest.raises(ValueError):
            PartAddEntry(at_time(0), "step1", "config.toml", {}, "invalid_category")


class TestExperimentTraceRoundTrip:
    def test_written_trace_can_be_reloaded_from_file(self, tmp_path):
        output_path = tmp_path / "trace.json"

        with ExperimentTrace(output_file_path=str(output_path)) as trace:
            trace.record(ExperimentBeginEntry(at_time(0), "my_experiment", 1, {"x": 1}))
            trace.record(AtPartEntry(at_time(1), "step1"))
            trace.record(ExperimentEndEntry(at_time(2), "my_experiment", 1))

        reloaded = ExperimentTrace(input_file_path=str(output_path))

        assert len(reloaded.trace) == 3
        begin_entry, at_part_entry, end_entry = reloaded.trace
        assert begin_entry.event == "experiment_begin"
        assert begin_entry.experiment_name == "my_experiment"
        assert begin_entry.run_number == 1
        assert begin_entry.experiment_data == {"x": 1}
        assert at_part_entry.event == "at_part"
        assert at_part_entry.part_name == "step1"
        assert end_entry.event == "experiment_end"
        assert end_entry.run_number == 1


class TestGetPartPath:
    def test_returns_part_names_in_order_visited(self, tmp_path):
        trace = ExperimentTrace(output_file_path=str(tmp_path / "trace.json"))
        trace.record(AtPartEntry(at_time(0), "step1"))
        trace.record(StepEntry(at_time(1), "step1", {}, None))
        trace.record(AtPartEntry(at_time(2), "step2"))
        trace.record(StepEntry(at_time(3), "step2", {}, None))

        part_path = trace.get_part_path()

        assert [piece.part_name for piece in part_path] == ["step1", "step2"]

    def test_attaches_part_data_from_the_entry_after_at_part(self, tmp_path):
        trace = ExperimentTrace(output_file_path=str(tmp_path / "trace.json"))
        trace.record(AtPartEntry(at_time(0), "step1"))
        trace.record(StepEntry(at_time(1), "step1", {"x": 1}, {"foo": "bar"}))

        part_path = trace.get_part_path()

        assert part_path[0].part_data == {"foo": "bar"}

    def test_skips_over_custom_entries_to_find_part_data(self, tmp_path):
        # An AtPartEntry followed by a CustomEntry then a StepEntry should
        # still attach the StepEntry's part_data to that path piece.
        trace = ExperimentTrace(output_file_path=str(tmp_path / "trace.json"))
        trace.record(AtPartEntry(at_time(0), "step1"))
        trace.record(CustomEntry(at_time(1), "some_event", {"a": 1}))
        trace.record(StepEntry(at_time(2), "step1", {}, {"foo": "bar"}))

        part_path = trace.get_part_path()

        assert part_path[0].part_data == {"foo": "bar"}

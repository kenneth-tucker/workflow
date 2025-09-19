from copy import deepcopy
import os
from typing import Optional
import json
from datetime import datetime

# The latest trace file version
# IMPORTANT NOTE: if you change the format you must increment
# this version number and add handling for converting old formats
TRACE_FILE_VERSION = 1

class PartPathPiece:
    """
    A piece of a path through the experiment, consisting of the
    part name and optional part data that may be associated with it.
    """
    def __init__(self, part_name: str | None, part_data: dict | None):
        self.part_name = part_name
        self.part_data = part_data

# Types of trace entries

class TraceEntry:
    """
    Base class for all trace entries.
    """
    def __init__(
        self,
        timestamp: datetime,
        event: str
    ):
        self.timestamp = timestamp
        self.event = event

class ExperimentBeginEntry(TraceEntry):
    """
    Trace entry for the start of an experiment run.
    """
    def __init__(
        self,
        timestamp: datetime,
        experiment_name: str,
        run_number: int,
        experiment_data: dict[str, any]
    ):
        super().__init__(timestamp, "experiment_begin")
        self.experiment_name = experiment_name
        self.run_number = run_number
        self.experiment_data = experiment_data

class ExperimentEndEntry(TraceEntry):
    """
    Trace entry for the end of an experiment run.
    """
    def __init__(
        self,
        timestamp: datetime,
        experiment_name: str,
        run_number: int
    ):
        super().__init__(timestamp, "experiment_end")
        self.experiment_name = experiment_name
        self.run_number = run_number

class AtPartEntry(TraceEntry):
    """
    Trace entry for going to a new part.
    """
    def __init__(
        self,
        timestamp: datetime,
        part_name: str
    ):
        super().__init__(timestamp, "at_part")
        self.part_name = part_name

class ErrorEntry(TraceEntry):
    """
    Trace entry for error encountered while running a part.
    """
    def __init__(
        self,
        timestamp: datetime,
        part_name: str,
        error_message: str
    ):
        super().__init__(timestamp, "error")
        self.part_name = part_name
        self.error_message = error_message

class ResearcherDecisionEntry(TraceEntry):
    """
    Trace entry for a researcher's decision on what to do next.
    """
    def __init__(
        self,
        timestamp: datetime,
        next_part: str | None
    ):
        super().__init__(timestamp, "researcher_decision")
        self.next_part = next_part

class StepEntry(TraceEntry):
    """
    Trace entry for completing a step part in the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        step_name: str,
        data_before: dict,
        data_after: dict,
        part_data: dict | None
    ):
        super().__init__(timestamp, "step")
        self.step_name = step_name
        self.data_before = data_before
        self.data_after = data_after
        self.part_data = part_data

class DecisionEntry(TraceEntry):
    """
    Trace entry for completing a decision part in the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        decision_name: str,
        next_part: str | None,
        part_data: dict | None
    ):
        super().__init__(timestamp, "decision")
        self.decision_name = decision_name
        self.next_part = next_part
        self.part_data = part_data

class FlowBeginEntry(TraceEntry):
    """
    Trace entry for beginning a flow in the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        flow_name: str,
        first_part: str | None,
        part_data: dict | None
    ):
        super().__init__(timestamp, "flow_begin")
        self.flow_name = flow_name
        self.first_part = first_part
        self.part_data = part_data

class FlowEndEntry(TraceEntry):
    """
    Trace entry for ending a flow in the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        flow_name: str,
        part_data: dict | None
    ):
        super().__init__(timestamp, "flow_end")
        self.flow_name = flow_name
        self.part_data = part_data

class PartAddEntry(TraceEntry):
    """
    Trace entry for adding a part to the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        full_name: str,
        file_path: str,
        raw_config: dict,
        part_category: str,
    ):
        allowed_categories = {"step", "decision", "flow"}
        if part_category not in allowed_categories:
            raise ValueError(f"part_category must be one of {allowed_categories}, got '{part_category}'")
        super().__init__(timestamp, "part_add")
        self.full_name = full_name
        self.file_path = file_path
        self.raw_config = raw_config
        self.part_category = part_category

class PartRemoveEntry(TraceEntry):
    """
    Trace entry for removing a part from the experiment.
    """
    def __init__(
        self,
        timestamp: datetime,
        full_name: str,
    ):
        super().__init__(timestamp, "part_remove")
        self.full_name = full_name

class CustomEntry(TraceEntry):
    """
    Trace entry for custom events that part
    implementations may want to log.
    """
    def __init__(
        self,
        timestamp: datetime,
        event_type: str,
        event_data: dict | None
    ):
        super().__init__(timestamp, "custom")
        self.event_type = event_type
        self.event_data = event_data

class ExperimentTrace:
    """
    Class for tracing the execution of an experiment.
    It reads and writes JSON files.
    """
    def __init__(
        self,
        input_file_path: Optional[str] = None,
        output_file_path: Optional[str] = None,
    ):
        """
        Initialize the trace, loading from input file if provided,
        and preparing to write to output file if provided.
        """
        self.input_file_path = os.path.normpath(input_file_path) if input_file_path else None
        self.output_file_path = os.path.normpath(output_file_path) if output_file_path else None
        if self.input_file_path:
            # Load an old trace
            self._load_input_trace()
            self._parse_input_trace()
            self._validate_input_trace()
            self.trace = deepcopy(self.parsed_input)
        else:
            # Start a new trace
            self.trace = []
        if self.output_file_path:
            self._open_output_trace()
            self._initialize_output_trace()

    def record(self, entry: TraceEntry):
        """
        Record a new trace entry, streaming it to the output file if provided.
        """
        self.trace.append(entry)
        if self.output_trace_file:
            # Serialize the entry as a dict
            entry_dict = entry.__dict__.copy()
            entry_dict["timestamp"] = entry.timestamp.isoformat()
            json.dump(entry_dict, self.output_trace_file)
            self.output_trace_file.write(',\n')
            self.output_trace_file.flush()

    def get_part_path(self) -> list[PartPathPiece]:
        """
        Get the full list of part names in the path taken through the experiment,
        including any 'part_data' associated with that part of the path.
        """
        part_path = []
        for i, entry in enumerate(self.trace):
            if isinstance(entry, AtPartEntry):
                # The entry after the AtPartEntry may have part_data, assuming
                # it is a StepEntry, DecisionEntry, FlowBeginEntry, or FlowEndEntry
                # and not something like ErrorEntry or ResearcherDecisionEntry.
                # We do need to skip over any CustomEntry entries that the part
                # implementation may have logged.
                j = i + 1
                while True:
                    part_entry = self.trace[j] if j < len(self.trace) else None
                    if not isinstance(part_entry, CustomEntry):
                        break
                    j += 1
                if isinstance(part_entry, (StepEntry, DecisionEntry, FlowBeginEntry, FlowEndEntry)):
                    part_data = part_entry.part_data
                else:
                    part_data = None
                part_path.append(PartPathPiece(entry.part_name, part_data))
        return part_path

    # Private helper methods

    def _load_input_trace(self):
        data = {}
        if self.input_file_path:
            with open(self.input_file_path, 'r') as f:
                data = json.load(f)
        self.raw_input = data

    def _parse_input_trace(self):
        # Note: update this method if the trace file format changes
        version = self.raw_input.get("version")
        raw_trace = self.raw_input.get("trace", [])
        # Deserialize the raw trace entries
        self.parsed_input = []
        for entry in raw_trace:
            if not entry:
                # Skip empty entries (e.g. the last one)
                continue
            timestamp = datetime.fromisoformat(entry["timestamp"])
            match entry.get("event"):
                case "experiment_begin":
                    self.parsed_input.append(ExperimentBeginEntry(
                        timestamp=timestamp,
                        experiment_name=entry["experiment_name"],
                        run_number=entry["run_number"],
                        experiment_data=entry["experiment_data"]
                    ))
                case "experiment_end":
                    self.parsed_input.append(ExperimentEndEntry(
                        timestamp=timestamp,
                        experiment_name=entry["experiment_name"],
                        run_number=entry["run_number"]
                    ))
                case "at_part":
                    self.parsed_input.append(AtPartEntry(
                        timestamp=timestamp,
                        part_name=entry["part_name"]
                    ))
                case "error":
                    self.parsed_input.append(ErrorEntry(
                        timestamp=timestamp,
                        part_name=entry["part_name"],
                        error_message=entry["error_message"]
                    ))
                case "researcher_decision":
                    self.parsed_input.append(ResearcherDecisionEntry(
                        timestamp=timestamp,
                        next_part=entry["next_part"]
                    ))
                case "step":
                    self.parsed_input.append(StepEntry(
                        timestamp=timestamp,
                        step_name=entry["step_name"],
                        data_before=entry["data_before"],
                        data_after=entry["data_after"],
                        part_data=entry.get("part_data")
                    ))
                case "decision":
                    self.parsed_input.append(DecisionEntry(
                        timestamp=timestamp,
                        decision_name=entry["decision_name"],
                        next_part=entry["next_part"],
                        part_data=entry.get("part_data")
                    ))
                case "flow_begin":
                    self.parsed_input.append(FlowBeginEntry(
                        timestamp=timestamp,
                        flow_name=entry["flow_name"],
                        first_part=entry["first_part"],
                        part_data=entry.get("part_data")
                    ))
                case "flow_end":
                    self.parsed_input.append(FlowEndEntry(
                        timestamp=timestamp,
                        flow_name=entry["flow_name"],
                        part_data=entry.get("part_data")
                    ))
                case "part_add":
                    self.parsed_input.append(PartAddEntry(
                        timestamp=timestamp,
                        full_name=entry["full_name"],
                        file_path=entry["file_path"],
                        raw_config=entry["raw_config"],
                        part_category=entry["part_category"]
                    ))
                case "part_remove":
                    self.parsed_input.append(PartRemoveEntry(
                        timestamp=timestamp,
                        full_name=entry["full_name"]
                    ))
                case "custom":
                    self.parsed_input.append(CustomEntry(
                        timestamp=timestamp,
                        event_type=entry["event_type"],
                        event_data=entry["event_data"]
                    ))
                case _:
                    raise ValueError(f"Unknown trace entry type: {entry.get('event')}")
        self.parsed_input.sort(key=lambda e: e.timestamp)

    def _validate_input_trace(self):
        if not self.parsed_input:
            return
        # TODO: Implement any checking logic to catch issues early

    def _open_output_trace(self):
        if self.output_file_path:
            self.output_trace_file = open(self.output_file_path, 'w')
        else:
            self.output_trace_file = None

    def _close_output_trace(self):
        if self.output_trace_file:
            self.output_trace_file.close()
            self.output_trace_file = None

    def _initialize_output_trace(self):
        if self.output_trace_file:
            self.output_trace_file.write('{"version": %d, "trace": [\n' % TRACE_FILE_VERSION)
            self.output_trace_file.flush()

    def _finalize_output_trace(self):
        if self.output_trace_file:
            self.output_trace_file.write('{}]}\n')
            self.output_trace_file.flush()

    def __enter__(self):
        # Support usage as a context manager
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure the output trace file is ended and closed properly
        self._finalize_output_trace()
        self._close_output_trace()

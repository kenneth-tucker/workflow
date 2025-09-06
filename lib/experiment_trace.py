from copy import deepcopy
import os
from typing import Optional
import json
from datetime import datetime

# The latest trace file version
# IMPORTANT NOTE: if you change the format you must increment
# this version number and add handling for converting old formats
TRACE_FILE_VERSION = 1

# Types of trace entries

# Base class for all trace entries
class TraceEntry:
    def __init__(
        self,
        timestamp: datetime,
        event: str
    ):
        self.timestamp = timestamp
        self.event = event

# Trace entry for the start of an experiment run
class ExperimentBeginEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        experiment_name: str,
        run_number: int
    ):
        super().__init__(timestamp, "experiment_begin")
        self.experiment_name = experiment_name
        self.run_number = run_number

# Trace entry for the end of an experiment run
class ExperimentEndEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        experiment_name: str,
        run_number: int
    ):
        super().__init__(timestamp, "experiment_end")
        self.experiment_name = experiment_name
        self.run_number = run_number

# Trace entry for error encountered while running a part
class ErrorEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        part_name: str,
        error_message: str
    ):
        super().__init__(timestamp, "error")
        self.part_name = part_name
        self.error_message = error_message

# Trace entry for a researcher's decision on what to do next
class ResearcherDecisionEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        next_part: str | None
    ):
        super().__init__(timestamp, "researcher_decision")
        self.next_part = next_part

# Trace entry for completing a step part in the experiment
class StepEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        step_name: str,
        data_before: dict,
        data_after: dict
    ):
        super().__init__(timestamp, "step")
        self.step_name = step_name
        self.data_before = data_before
        self.data_after = data_after

# Trace entry for a decision part's (usually automated)
# decision on what to do next
class DecisionEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        decision_name: str,
        next_part: str | None,
    ):
        super().__init__(timestamp, "decision")
        self.decision_name = decision_name
        self.next_part = next_part

# Trace beginning a flow
class FlowBeginEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        flow_name: str,
        first_part: str | None,
    ):
        super().__init__(timestamp, "flow_begin")
        self.flow_name = flow_name
        self.first_part = first_part

# Trace end of flow
class FlowEndEntry(TraceEntry):
    def __init__(
        self,
        timestamp: datetime,
        flow_name: str,
    ):
        super().__init__(timestamp, "flow_end")
        self.flow_name = flow_name

# The class for tracing the execution of an experiment.
# It reads and writes JSON files.
class ExperimentTrace:
    # Starts with data from the input file, if provided.
    # Outputs data to the output file, if provided.
    def __init__(
        self,
        input_file_path: Optional[str] = None,
        output_file_path: Optional[str] = None,
    ):
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

    # Records a new trace entry, streaming it to the output file if provided.
    def record(self, entry: TraceEntry):
        self.trace.append(entry)
        if self.output_trace_file:
            if len(self.trace) > 1:
                # Add a comma before the next entry
                self.output_trace_file.write(',\n')
            # Serialize the entry as a dict
            entry_dict = entry.__dict__.copy()
            entry_dict["timestamp"] = entry.timestamp.isoformat()
            json.dump(entry_dict, self.output_trace_file)
            self.output_trace_file.flush()

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
            timestamp = datetime.fromisoformat(entry["timestamp"])
            match entry.get("event"):
                case "experiment_begin":
                    self.parsed_input.append(ExperimentBeginEntry(
                        timestamp=timestamp,
                        experiment_name=entry["experiment_name"],
                        run_number=entry["run_number"]
                    ))
                case "experiment_end":
                    self.parsed_input.append(ExperimentEndEntry(
                        timestamp=timestamp,
                        experiment_name=entry["experiment_name"],
                        run_number=entry["run_number"]
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
                        data_after=entry["data_after"]
                    ))
                case "decision":
                    self.parsed_input.append(DecisionEntry(
                        timestamp=timestamp,
                        decision_name=entry["decision_name"],
                        next_part=entry["next_part"]
                    ))
                case "flow_begin":
                    self.parsed_input.append(FlowBeginEntry(
                        timestamp=timestamp,
                        flow_name=entry["flow_name"],
                        first_part=entry["first_part"]
                    ))
                case "flow_end":
                    self.parsed_input.append(FlowEndEntry(
                        timestamp=timestamp,
                        flow_name=entry["flow_name"]
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
            self.output_trace_file.write(']}')
            self.output_trace_file.flush()

    def __enter__(self):
        # Support usage as a context manager
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure the output trace file is ended and closed properly
        self._finalize_output_trace()
        self._close_output_trace()

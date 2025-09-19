from datetime import datetime
from enum import Enum

# Special commands that can be used in the experiment.
# Note: needs to match the COMMAND_NAMES in lib
COMMAND_NAMES = {
    # Leave the current flow
    "done",
    # Quit the experiment
    "quit"
}

class ExperimentState(Enum):
    NOT_STARTED = "not started"
    RUNNING = "running"
    WAITING_FOR_RESEARCHER = "waiting for researcher"
    COMPLETED = "completed"

class PartModel:
    """
    Model to represent a single part in the experiment.
    """
    def __init__(
        self,
        full_name: str,
        file_path: str,
        raw_config: dict,
        part_category: str,
    ):
        self.full_name = full_name
        self.file_path = file_path
        self.raw_config = raw_config
        self.part_category = part_category

class ErrorModel:
    """
    Model to represent an error that occurred during the experiment.
    """
    def __init__(self, part_name: str, error_message: str, timestamp: datetime):
        self.part_name = part_name
        self.error_message = error_message
        self.timestamp = timestamp

class ExperimentModel:
    """
    Model to represent the state of an experiment based on trace entries.
    """
    def __init__(self):
        self.experiment_name: str | None = None
        self.run_number: int | None = None
        self.experiment_data: dict[str, any] = {}
        self.experiment_parts: dict[str, PartModel] = {}
        self.experiment_state = ExperimentState.NOT_STARTED
        self.part_path: list[str] = []
        self.flow_stack: list[str] = []
        self.error_stack: list[str] = []
    
    def on_trace_entry(self, trace_entry: dict):
        # Update the experiment model based on the trace entry
        timestamp = datetime.fromisoformat(trace_entry["timestamp"])
        match trace_entry.get("event"):
            case "experiment_begin":
                self.experiment_name = trace_entry["experiment_name"]
                self.run_number = trace_entry["run_number"]
                self.experiment_data = trace_entry.get("experiment_data", {})
                self.experiment_state = ExperimentState.RUNNING
            case "experiment_end":
                self.experiment_state = ExperimentState.COMPLETED
            case "at_part":
                self.part_path.append(trace_entry["part_name"])
                # The researcher needs to decide what to do next if
                # part_name is not a valid part or command
                if trace_entry["part_name"] in self.experiment_parts or \
                   trace_entry["part_name"] in COMMAND_NAMES:
                    self.experiment_state = ExperimentState.RUNNING
                else:
                    self.experiment_state = ExperimentState.WAITING_FOR_RESEARCHER
            case "error":
                self.error_stack.append(
                    ErrorModel(
                        part_name=trace_entry["part_name"],
                        error_message=trace_entry["error_message"],
                        timestamp=timestamp,
                    )
                )
            case "researcher_decision":
                # Nothing to do, will see result of researcher decision in at_part
                pass
            case "step":
                self.experiment_data = trace_entry.get("data_after", self.experiment_data)
            case "decision":
                # Nothing to do, will see result of decision in at_part
                pass
            case "flow_begin":
                self.flow_stack.append(trace_entry["flow_name"])
            case "flow_end":
                self.part_path.append(self.flow_stack.pop() if self.flow_stack else "")
            case "part_add":
                # If a child part is added before its parent (like in the case of
                # the load flow), also add a placeholder for the parent first
                parent_full_name = trace_entry["full_name"].rsplit(".", 1)[0]
                if self.experiment_parts.get(parent_full_name) is None:
                    parent_part = PartModel(
                        full_name=parent_full_name,
                        file_path="",
                        raw_config={},
                        part_category="flow",  # Assume parent is a flow
                    )
                    self.experiment_parts[parent_part.full_name] = parent_part
                part = PartModel(
                    full_name=trace_entry["full_name"],
                    file_path=trace_entry["file_path"],
                    raw_config=trace_entry["raw_config"],
                    part_category=trace_entry["part_category"],
                )
                self.experiment_parts[part.full_name] = part
            case "part_remove":
                self.experiment_parts.pop(trace_entry["full_name"], None)
            case "custom":
                # Handle custom trace entries if needed
                if trace_entry["event_type"] == "waiting_for_researcher":
                    self.experiment_state = ExperimentState.WAITING_FOR_RESEARCHER
            case _:
                raise ValueError(f"Unknown trace entry type: {trace_entry.get('event')}")
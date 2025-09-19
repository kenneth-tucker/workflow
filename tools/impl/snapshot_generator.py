

from copy import deepcopy
from datetime import datetime
from tools.impl.snapshot import Snapshot
from tools.impl.experiment_model import COMMAND_NAMES, ExperimentModel
from tools.impl.flowchart import FlowChart
from tools.impl.trace_monitor import TraceObserver

class SnapshotConsumer:
    """
    Base class for objects that want to observe snapshots.
    """
    def on_new_snapshot(self, snapshot: Snapshot):
        raise NotImplementedError("Must be implemented by subclass")

class SnapshotGenerator(TraceObserver):
    """
    Tracks the state of an experiment and generates snapshots for visualizing each change.
    """
    def __init__(self):
        self.snapshots = []
        self.cur_model = ExperimentModel()
        self.observers = {}

    def add_observer(self, id: str, observer: SnapshotConsumer):
        self.observers[id] = observer

    def remove_observer(self, id: str):
        self.observers.pop(id, None)
    
    def on_trace_entry(self, trace_entry: dict):
        """
        Update the experiment model and generate a new snapshot based on the trace entry.
        """
        # Update the experiment model
        self.cur_model.on_trace_entry(trace_entry)
        
        # Parse the timestamp
        timestamp = datetime.fromisoformat(trace_entry["timestamp"])

        # Generate the flowchart
        self.flowchart = FlowChart(self.cur_model)

        # Make the event more descriptive
        match trace_entry.get("event"):
            case "experiment_begin":
                event_info = f"Experiment started"
            case "experiment_end":
                event_info = f"Experiment completed"
            case "at_part":
                if trace_entry["part_name"] in self.cur_model.experiment_parts:
                    part = self.cur_model.experiment_parts[trace_entry["part_name"]]
                    event_info = f"At {part.part_category} '{part.full_name}' (of type '{part.type_name}')"
                elif trace_entry["part_name"] in COMMAND_NAMES:
                    event_info = f"Command '{trace_entry['part_name']}' issued"
                else:
                    event_info = f"Waiting for the researcher to decide what to do next"
            case "error":
                event_info = f"Error occurred at '{trace_entry['part_name']}' with message: '{trace_entry['error_message']}'"
            case "researcher_decision":
                event_info = f"Researcher decision made, going to '{trace_entry['next_part']}'"
            case "step":
                event_info = f"Step '{trace_entry['step_name']}' completed"
            case "decision":
                if "next_part" in trace_entry:
                    event_info = f"Decision '{trace_entry['decision_name']}' made, going to '{trace_entry['next_part']}'"
                else:
                    event_info = f"Decision '{trace_entry['decision_name']}' has been delegated to the researcher"
            case "flow_begin":
                if "first_part" in trace_entry:
                    event_info = f"Flow '{trace_entry['flow_name']}' started at '{trace_entry['first_part']}'"
                else:
                    event_info = f"Flow '{trace_entry['flow_name']}' started in manual mode"
            case "flow_end":
                event_info = f"Flow '{trace_entry['flow_name']}' completed"
            case "part_add":
                part = self.cur_model.experiment_parts[trace_entry["full_name"]]
                event_info = f"Added a part named '{part.full_name}' (of type '{part.type_name}')"
            case "part_remove":
                event_info = f"Removed a part named '{trace_entry["full_name"]}'"
            case "custom":
                # Add descriptions for custom events here
                match trace_entry.get("event_type"):
                    case "waiting_for_researcher_input":
                        event_info = "Waiting for researcher input"
                        prompt = trace_entry.get("event_data", {}).get("prompt")
                        if prompt:
                            event_info += f" (prompt: '{prompt}')"
                    case _:
                        # Generic custom event description
                        event_info = f"Event '{trace_entry['event_type']}' occurred"
                        if "event_data" in trace_entry:
                            event_info += f" with data: {trace_entry['event_data']}"
            case _:
                event_info = trace_entry.get("event", "")
        
        # Create the snapshot
        snapshot = Snapshot(
            timestamp=timestamp,
            event_info=event_info,
            experiment_model=deepcopy(self.cur_model),
            flowchart=self.flowchart
        )

        # Store the snapshot and notify observers
        self.snapshots.append(snapshot)
        for observer in self.observers.values():
            observer.on_new_snapshot(snapshot)

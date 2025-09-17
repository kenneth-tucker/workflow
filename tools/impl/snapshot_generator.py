

from copy import deepcopy
from datetime import datetime
from tools.impl.snapshot import Snapshot
from tools.impl.experiment_model import ExperimentModel
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
        # Generate a new snapshot based on the trace entry's effect on the model
        timestamp = datetime.fromisoformat(trace_entry["timestamp"])
        self.flowchart = FlowChart(self.cur_model)
        snapshot = Snapshot(
            timestamp=timestamp,
            event=trace_entry.get("event", ""),
            experiment_model=deepcopy(self.cur_model),
            flowchart=self.flowchart
        )
        self.snapshots.append(snapshot)
        for observer in self.observers.values():
            observer.on_new_snapshot(snapshot)

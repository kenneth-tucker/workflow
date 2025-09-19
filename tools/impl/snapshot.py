
from datetime import datetime
from tools.impl.experiment_model import ExperimentModel
from tools.impl.flowchart import FlowChart

class Snapshot:
    """
    Represents a snapshot of the experiment at a specific point in time.
    """
    def __init__(
        self,
        timestamp: datetime,
        event_info: str,
        experiment_model: ExperimentModel,
        flowchart: FlowChart
    ):
        self.timestamp = timestamp
        self.event_info = event_info
        self.experiment_model = experiment_model
        self.flowchart = flowchart

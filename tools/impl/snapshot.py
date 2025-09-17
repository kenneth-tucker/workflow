
from datetime import datetime
from tools.impl.experiment_model import ExperimentModel
from tools.impl.flowchart import FlowChart

# Contains all of the content for a snapshot of the experiment at a given time
class Snapshot:
    def __init__(
        self,
        timestamp: datetime,
        event: str,
        experiment_model: ExperimentModel,
        flowchart: FlowChart
    ):
        self.timestamp = timestamp
        self.event = event
        self.experiment_model = experiment_model
        self.flowchart = flowchart

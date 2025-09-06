from typing import override
from lib.experiment_parts import Flow

# Start a flow in manual mode
class ManualFlow(Flow):
    def __init__(self, context):
        super().__init__(context)

    @override
    def begin_flow(self) -> str | None:
        # Researcher specifies the first part to run
        return None

    @override
    def end_flow(self) -> None:
        return
from typing import override
from lib.experiment_parts import Flow

class ManualFlow(Flow):
    """
    A flow part that starts in manual mode, where the researcher
    specifies the first part to run.
    """
    def __init__(self, context):
        super().__init__(context)

    @override
    def begin_flow(self) -> str | None:
        # Researcher specifies the first part to run
        return None

    @override
    def end_flow(self) -> None:
        return
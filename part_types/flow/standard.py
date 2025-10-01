from typing import override
from lib.experiment_parts import Flow
from lib.utils.part_utils import BeginFlowRoute

class StandardFlow(Flow):
    """
    A flow part that starts in standard mode, using the configured
    first_part part name as the first part to run.
    """
    def __init__(self, context):
        super().__init__(context)

    @override
    def begin_flow(self) -> BeginFlowRoute:
        # Use the configured first_part part name, if provided
        return BeginFlowRoute(self.get_first_part())

    @override
    def end_flow(self) -> None:
        return

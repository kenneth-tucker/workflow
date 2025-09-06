from typing import override
from lib.experiment_parts import Flow

# Start a flow in standard mode, using the start_here config value
class StandardFlow(Flow):
    def __init__(self, context):
        super().__init__(context)

    @override
    def begin_flow(self) -> str | None:
        # Use the configured start_here part name, if provided
        return self.get_start_here()

    @override
    def end_flow(self) -> None:
        return
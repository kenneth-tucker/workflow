from lib.utils.part_utils import PartTypeInfo
from part_types.decision.conditional import ConditionalDecision
from part_types.flow.load import LoadFlow
from part_types.flow.manual import ManualFlow
from part_types.flow.standard import StandardFlow
from part_types.step.dump import DumpStep
from part_types.step.terminal import TerminalStep

# All of the types of parts for experiments go here
# Note: use snake case for part type names and
# try to use a consistent naming scheme
# Note: if you change a name here be sure to update
# all of the config files too
part_types = {
    # Decision types
    "decision.conditional": PartTypeInfo(
        type=ConditionalDecision,
        description="Decide a route using conditional statements"
    ),

    # Flow types
    "flow.load": PartTypeInfo(
        type=LoadFlow,
        description="Run parts from another config file"
    ),
    "flow.manual": PartTypeInfo(
        type=ManualFlow,
        description="Let the researcher choose the first part to run"
    ),
    "flow.standard": PartTypeInfo(
        type=StandardFlow,
        description="Run parts in a sequence"
    ),

    # Step types
    "step.dump": PartTypeInfo(
        type=DumpStep,
        description="Show the experiment data"
    ),
    "step.terminal": PartTypeInfo(
        type=TerminalStep,
        description="Show a prompt and get input"
    )
}
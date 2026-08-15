from lib.utils.part_utils import PartTypeInfo
from part_types.decision.conditional import ConditionalDecision
from part_types.flow.load import LoadFlow
from part_types.flow.standard import StandardFlow
from part_types.step.dump import DumpStep
from part_types.step.expression import ExpressionStep
from part_types.step.terminal import TerminalStep

# Make a copy of this file in your own project and add your own types.
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
    "flow.standard": PartTypeInfo(
        type=StandardFlow,
        description="Run parts in a sequence"
    ),

    # Step types
    "step.dump": PartTypeInfo(
        type=DumpStep,
        description="Show the experiment data"
    ),
    "step.expression": PartTypeInfo(
        type=ExpressionStep,
        description="Calculate expressions and store results"
    ),
    "step.terminal": PartTypeInfo(
        type=TerminalStep,
        description="Show a prompt and get input"
    )
}
import copy
from datetime import datetime
import enum
from typing import Optional
from workflow.lib.utils.part_utils import PartContext
from workflow.lib.experiment_config import ExperimentConfig
from workflow.lib.experiment_parts import _Part, Step, Decision, Flow
from workflow.lib.experiment_trace import ExperimentTrace, \
    ExperimentBeginEntry, ExperimentEndEntry, ErrorEntry, \
    ResearcherDecisionEntry, StepEntry, DecisionEntry, \
    FlowBeginEntry, FlowEndEntry

# How to run the ExperimentManager
class ExperimentMode(enum.Enum):
    # Start a new experiment
    NORMAL = "normal"
    # Try to re-run an old experiment based on its trace,
    # including the ending of the experiment
    RERUN = "rerun"
    # Same as rerun, except the experiment can
    # be continued from the last part before it ended
    CONTINUE = "continue"

# This class manages the execution of an experiment
class ExperimentManager:
    # Initialize the experiment manager
    def __init__(
        self,
        config: ExperimentConfig,
        mode: ExperimentMode,
        old_trace: Optional[ExperimentTrace] = None,
    ):
        self.config = config
        self.mode = mode
        self.old_trace = old_trace

    # Run the experiment
    def run(self) -> None:
        # Always reset the experiment before starting
        self._reset()

        # Start of experiment
        print(f"Experiment '{self.config.experiment_name}' started")
        self.experiment_trace.record(
            ExperimentBeginEntry(
                datetime.datetime.now(),
                self.config.experiment_name
            )
        )
        
        # Main loop for running the experiment
        current_part_name = self.config.initial_part_name
        next_part_name = None
        while current_part_name != "quit":
            if current_part_name == "done":
                # Leaving the current flow
                if self.flow_stack.size() > 0:
                    # TODO handle leaving flow and assign next_part_name
                    pass
                else:
                    # When the top-level flow is done, end the experiment
                    next_part_name = "quit"
            elif current_part_name is None or current_part_name not in self.experiment_parts:
                # The researcher needs to tell us what to do next
                self._print_flow_info()
                if current_part_name is None:
                    print("\nNo part specified to run next\n")
                else:
                    print(f"\nUnknown part: '{current_part_name}'\n")
                next_part_name = self._get_next_from_researcher()
                self.experiment_trace.record(
                    ResearcherDecisionEntry(
                        datetime.datetime.now(),
                        next_part_name
                    )
                )
            else:
                try:
                    # Make a deepcopy of the experiment data so the original is
                    # preserved if the current part encounters an error when it runs.
                    self.new_experiment_data = copy.deepcopy(self.experiment_data)

                    # Handle the current part
                    current_part = self.experiment_parts[current_part_name]
                    if isinstance(current_part, Step):
                        current_part.run_step()
                        next_part_name = current_part._context.config.next_part
                        self.experiment_trace.record(
                            StepEntry(
                                datetime.datetime.now(),
                                current_part_name,
                                self.experiment_data,
                                self.new_experiment_data
                            )
                        )
                    elif isinstance(current_part, Decision):
                        route_name = current_part.decide_route()
                        next_part_name = current_part._context.config.next_part.get(route_name)
                        self.experiment_trace.record(
                            DecisionEntry(
                                datetime.datetime.now(),
                                current_part_name,
                                next_part_name
                            )
                        )
                    elif isinstance(current_part, Flow):
                        next_part_name = current_part.begin_flow(self._get_flow_parts())
                        self.flow_stack.append(current_part_name)
                        self.experiment_trace.record(
                            FlowBeginEntry(
                                datetime.datetime.now(),
                                current_part_name,
                                next_part_name
                            )
                        )
                    else:
                        # Your class needs to inherit from Step, Decision, or Flow
                        raise TypeError(f"Unknown part type: {type(current_part)}")

                    # TODO handle mode where we are re-running an old trace and deal
                    # with overriding decisions and ensuring consistent re-run
                    
                    # Update the experiment data to the new data after a successful run
                    self.experiment_data = copy.deepcopy(self.new_experiment_data)
                except Exception as e:
                    print(f"Error occurred while running part '{current_part_name}': {e}")
                    self.experiment_trace.record(
                        ErrorEntry(
                            datetime.datetime.now(),
                            current_part_name,
                            str(e)
                        )
                    )
                    # Ask the researcher what to do next
                    next_part_name = None
            # Go to the next part
            current_part_name = next_part_name
        
        # End of experiment
        print(f"Experiment '{self.config.experiment_name}' completed")
        self.experiment_trace.record(
            ExperimentEndEntry(
                datetime.datetime.now(),
                self.config.experiment_name
            )
        )
        return

    # Private helper methods, only the library code should use these

    def _reset(self) -> None:
        # (Re)initialize the experiment state
        self.experiment_data = copy.deepcopy(self.config.initial_values)
        self.new_experiment_data = copy.deepcopy(self.config.initial_values)
        self.experiment_parts = self._construct_parts()
        self.experiment_trace = ExperimentTrace(self.config.out_dir_for_run + "trace.json")
        # TODO make a copy of the config to the output file so it can be reused
        self.flow_stack = []

    def _get_data(self, global_name: str) -> object | None:
        # Get the global experiment data, returns None if not found
        return self.new_experiment_data.get(global_name)

    def _set_data(self, global_name: str, value: object) -> None:
        # Set the global experiment data to the given value
        self.new_experiment_data[global_name] = value

    def _construct_parts(self) -> dict[str, _Part]:
        # Construct instances of each part of the experiment as
        # specified in the configuration and part_types dictionary
        parts = {}
        for part_name, part_config in self.config.parts.items():
            part_type = self.config.part_types.get(part_config.type_name)
            part_context = PartContext(self, part_config)
            # Call the class constructor for the part type
            parts[part_name] = part_type.type(part_context)
        return parts

    def _get_flow_path(self) -> str:
        # Get the current flow path
        return ".".join(self.flow_stack)
    
    def _get_flow_parts(self) -> list[str]:
        # Get the names of parts that are in the current flow
        flow_path = self._get_flow_path()
        flow_parts = []
        for part_name in self.experiment_parts.keys():
            if not flow_path:
                # If we are at the top level, show all top-level parts
                if '.' not in part_name:
                    flow_parts.append(part_name)
            elif part_name.startswith(flow_path):
                # If we are in a sub-flow, show all parts of the sub-flow
                flow_parts.append(part_name)
        return flow_parts

    def _print_flow_info(self) -> None:
        # Show the researcher where they are and what parts are available
        flow_path = self._get_flow_path()
        if not flow_path:
            print(f"You are in the top-level flow for experiment '{self.config.experiment_name}', which has these parts:")
        else:
            print(f"You are in the '{flow_path}' flow, which has these parts:")
        flow_parts = self._get_flow_parts()
        for part_name in flow_parts:
            print(f" - {part_name} : {type(self.experiment_parts[part_name]).__name__}")

    def _get_next_from_researcher(self) -> str:
        # Prompt the researcher for what to do next.
        # Returns the fully qualified name of the 
        # part to run next or a special command.
        print(
            "Enter one of the following:\n"
            " - the name of the next part to run\n"
            " - 'done' to leave the current flow\n"
            " - 'quit' to end the entire experiment\n\n"
        )
        val = ""
        while val == "":
            val = input("> ").strip()
        if val == "done" or val == "quit":
            return val
        flow_path = self._get_flow_path()
        if flow_path:
            return flow_path + "." + val
        return val

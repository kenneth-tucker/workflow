import copy
from datetime import datetime
import enum
import os
import shutil
from typing import Optional
from lib.utils.part_utils import PartContext
from lib.experiment_config import ExperimentConfig
from lib.experiment_parts import _Part, Step, Decision, Flow
from lib.experiment_trace import ExperimentTrace, \
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

# Special commands that are not treated as names of parts
COMMAND_NAMES = {
    # Leave the current flow
    "done",
    # Quit the experiment
    "quit"
}

# This class manages the execution of an experiment
class ExperimentManager:
    # Configure the manager for running a particular type of experiment
    def __init__(
        self,
        config: ExperimentConfig
    ):
        self.config = config

    # Run the experiment one time, part by part
    # Note: can be called multiple times to re-run the experiment
    def run(
        self,
        mode: ExperimentMode,
        old_trace: Optional[ExperimentTrace] = None
    ) -> None:
        # TODO handle mode where we are re-running an old trace and deal
        self.mode = mode
        self.old_trace = old_trace
        self._begin_experiment_run()        
        current_part_name = self.config.initial_part_name
        next_part_name = None
        while current_part_name != "quit":
            if current_part_name == "done":
                next_part_name = self._end_flow(current_part_name)
            elif current_part_name is None or current_part_name not in self.experiment_parts:
                next_part_name = self._get_researcher_decision(current_part_name)
            else:
                next_part_name = self._run_part(current_part_name)
            current_part_name = next_part_name
        self._end_experiment_run()

    # Private helper methods, only the library code should use these

    def _begin_experiment_run(self) -> None:
        # (Re)initialize the experiment state
        self.flow_stack = []
        self.experiment_data = copy.deepcopy(self.config.initial_values)
        self.new_experiment_data = copy.deepcopy(self.config.initial_values)
        self.experiment_parts = self._construct_parts()
        self._build_output_dirs()
        self.experiment_trace = ExperimentTrace(self.out_dir_for_run + "trace.json")
        print(f"Experiment '{self.config.experiment_name}' started")
        self.experiment_trace.record(
            ExperimentBeginEntry(
                datetime.datetime.now(),
                self.config.experiment_name
            )
        )

    def _end_experiment_run(self) -> None:
        print(f"Experiment '{self.config.experiment_name}' completed")
        self.experiment_trace.record(
            ExperimentEndEntry(
                datetime.datetime.now(),
                self.config.experiment_name
            )
        )

    def _run_part(self, current_part_name: str) -> str | None:
        # Try to run the current part, returns the name of the next part, None, or a command
        next_part_name = None
        try:
            # Make a deepcopy of the experiment data so the original is
            # preserved if the current part encounters an error when it runs.
            self.new_experiment_data = copy.deepcopy(self.experiment_data)

            # Handle the current part
            current_part = self.experiment_parts[current_part_name]
            if isinstance(current_part, Step):
                current_part.run_step()
                next_part_name = current_part._context.config.next_part.get("")
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
                if route_name is not None and route_name not in COMMAND_NAMES:
                    next_part_name = current_part._context.config.next_part.get(route_name)
                else:
                    next_part_name = route_name
                self.experiment_trace.record(
                    DecisionEntry(
                        datetime.datetime.now(),
                        current_part_name,
                        next_part_name
                    )
                )
            elif isinstance(current_part, Flow):
                relative_part_name = current_part.begin_flow()
                if relative_part_name is not None and relative_part_name not in COMMAND_NAMES:
                    # Enter the flow at the given start
                    next_part_name = current_part_name + "." + relative_part_name
                else:
                    # Enter the flow but get the researcher's decision what to do inside
                    # (if relative_part_name is None) or run the command inside
                    next_part_name = relative_part_name
                # Keep track of what level we're in
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
            
            # Update the experiment data to the new data after a successful run
            self.experiment_data = copy.deepcopy(self.new_experiment_data)
        except Exception as e:
            print(f"Error while running part '{current_part_name}': {e}")
            self.experiment_trace.record(
                ErrorEntry(
                    datetime.datetime.now(),
                    current_part_name,
                    str(e)
                )
            )
            # Ask the researcher what to do next
            next_part_name = None
        return next_part_name

    def _end_flow(self, current_part_name: str) -> str | None:
        # End the current flow, returns the name of the next part, None, or a command
        next_part_name = None
        if self.flow_stack.size() > 0:
            # End the current flow and return to the parent flow
            flow_part_name = self.flow_stack.pop()
            flow_part = self.experiment_parts[flow_part_name]
            try:
                flow_part.end_flow()
                next_part_name = flow_part._context.config.next_part.get("")
                self.experiment_trace.record(
                    FlowEndEntry(
                        datetime.datetime.now(),
                        flow_part_name
                    )
                )
            except Exception as e:
                print(f"Error ending flow '{flow_part_name}': {e}")
                self.experiment_trace.record(
                    ErrorEntry(
                        datetime.datetime.now(),
                        current_part_name,
                        str(e)
                    )
                )
                # Ask the researcher what to do next
                next_part_name = None
        else:
            # When the top-level flow is done, end the experiment
            next_part_name = "quit"
        return next_part_name

    def _get_researcher_decision(self, current_part_name: str) -> str:
        # The researcher needs to tell us what to do next
        self._print_flow_info()
        if current_part_name is None:
            print("\nNo part specified\n")
        else:
            print(f"\nUnknown part: '{current_part_name}'\n")
        next_part_name = self._get_next_from_researcher()
        self.experiment_trace.record(
            ResearcherDecisionEntry(
                datetime.datetime.now(),
                next_part_name
            )
        )

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
        for part_name, part_config in self.config.part_configs.items():
            part_type = self.config.part_types.get(part_config.type_name)
            part_context = PartContext(self, part_config)
            # Call the class constructor for the part type
            parts[part_name] = part_type.type(part_context)
        return parts

    def _build_output_dirs(self):
        # Build the output directory structure for this run
        # Note: this method figures out the run number by looking at
        # the existing runs in the output directory
        print("Setting up output directories...")
        out_dir_for_experiment = self.config.out_dir_root + "/" + self.config.experiment_name + "/"
        os.makedirs(out_dir_for_experiment, exist_ok=True)
        existing_runs = [
            d for d in os.listdir(out_dir_for_experiment)
            if os.path.isdir(os.path.join(out_dir_for_experiment, d)) and d.startswith("run_")
        ]
        # The run number is one larger than the largest existing run number
        self.run_number = max(
            (int(d.split("_")[1]) for d in existing_runs), default=0
        ) + 1
        self.out_dir_for_run = self.out_dir_for_experiment + f"run_{self.run_number}/"
        print(f"Directory for experiment '{self.experiment_name}' run {self.run_number} created: {self.out_dir_for_run}")
        os.makedirs(self.out_dir_for_run, exist_ok=False)
        # Copy the config file to the new directory
        shutil.copy(self.file_path, self.out_dir_for_run + "config.toml")

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
            print(f"You are in the top-level flow of experiment '{self.config.experiment_name}', which has these parts:")
        else:
            print(f"You are in the '{flow_path}' flow, which has these parts:")
        flow_parts = self._get_flow_parts()
        for part_name in flow_parts:
            print(f" - {part_name} : {self.experiment_parts[part_name]._context.config.type_name}")

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
        if val in COMMAND_NAMES:
            return val
        flow_path = self._get_flow_path()
        if flow_path:
            return flow_path + "." + val
        return val

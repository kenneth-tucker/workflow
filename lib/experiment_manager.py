from copy import deepcopy
from datetime import datetime
import enum
import os
import shutil
from typing import Optional
from lib.utils.exceptions import ConfigError
from lib.utils.part_utils import PartConfig, PartContext, PartTypeInfo
from lib.experiment_config import ExperimentConfig
from lib.experiment_parts import _Part, Step, Decision, Flow
from lib.experiment_trace import AtPartEntry, ExperimentTrace, \
    ExperimentBeginEntry, ExperimentEndEntry, ErrorEntry, PartAddEntry, PartRemoveEntry, \
    ResearcherDecisionEntry, StepEntry, DecisionEntry, \
    FlowBeginEntry, FlowEndEntry

class ExperimentMode(enum.Enum):
    """
    The various modes in which an experiment can be run.
    """
    # Start a new experiment
    NORMAL = "normal"
    # Try to re-run an old experiment based on its trace,
    # including the ending of the experiment
    RERUN = "rerun"
    # Same as rerun, except the experiment can
    # be continued from the last part before it ended
    CONTINUE = "continue"

# Special commands that can be used in the experiment.
COMMAND_NAMES = {
    # Leave the current flow
    "done",
    # Quit the experiment
    "quit"
}

class ExperimentManager:
    """
    Manages the running of an experiment
    """
    def __init__(
        self,
        config: ExperimentConfig
    ):
        self.config = config

    def run(
        self,
        mode: ExperimentMode,
        old_trace: Optional[ExperimentTrace] = None
    ) -> None:
        """
        Run the experiment one time, part by part.
        """

        # Setup for retracing an old run's path, part by part, if needed
        if mode in {ExperimentMode.RERUN, ExperimentMode.CONTINUE}:
            if old_trace is None:
                raise ValueError("old_trace must be provided when mode is RERUN or CONTINUE")
            old_part_path = old_trace.get_part_path()
            if mode == ExperimentMode.CONTINUE:
                # Replace quit with None so we can continue
                if len(old_part_path) > 0 and old_part_path[-1] == "quit":
                    old_part_path[-1] = None
                else:
                    old_part_path.append(None)
        else:
            old_part_path = []
        
        # Setup the new experiment run
        self._begin_experiment_run()

        # Ensure the new trace will be closed correctly
        with self.experiment_trace:

            # Run the experiment, part by part
            path_index = 0
            current_part_full_name = self.config.initial_part_name
            while current_part_full_name != "quit":

                # If we are (still) retracing an old run, check we are on the same path
                if path_index < len(old_part_path) and \
                    old_part_path[path_index] != current_part_full_name:
                    raise ValueError(
                        f"Path deviation at index {path_index} while retracing old run: "
                        f"expected '{old_part_path[path_index]}', got '{current_part_full_name}'"
                    )

                # Always record the part (or command) we are at
                self.experiment_trace.record(
                    AtPartEntry(
                        datetime.now(),
                        current_part_full_name
                    )
                )

                # Handle the current part or command
                if current_part_full_name == "done":
                    next_part_short_name = self._end_flow()
                elif current_part_full_name is None or \
                    current_part_full_name not in self.experiment_parts:
                    if path_index < len(old_part_path):
                        # If retracing, use the past researcher's decision from the old run
                        next_part_short_name = old_part_path[path_index + 1]
                    else:
                        # Ask the current researcher what to do next
                        next_part_short_name = self._get_researcher_decision(current_part_full_name)
                else:
                    next_part_short_name = self._run_part(current_part_full_name)

                # Move to the next part or command
                path_index += 1
                current_part_full_name = self._convert_to_full_name(next_part_short_name)

            # Tear down the experiment run
            self.experiment_trace.record(
                AtPartEntry(
                    datetime.now(),
                    "quit"
                )
            )
            for flow_full_name in reversed(self.flow_stack):
                self._end_flow()
            self._end_experiment_run()

    # Private helper methods, only the library code should use these

    def _begin_experiment_run(self) -> None:
        """
        (Re)initialize the experiment state for a new run.
        """
        self.flow_stack: list[str] = []
        self.experiment_data = deepcopy(self.config.initial_values)
        self.new_experiment_data = deepcopy(self.config.initial_values)
        self._build_output_dirs()
        self._construct_parts()
        print(f"Experiment '{self.config.experiment_name}' run {self.run_number} started")
        self.experiment_trace.record(
            ExperimentBeginEntry(
                datetime.now(),
                self.config.experiment_name,
                self.run_number
            )
        )

    def _end_experiment_run(self) -> None:
        print(f"Experiment '{self.config.experiment_name}' run {self.run_number} completed")
        self.experiment_trace.record(
            ExperimentEndEntry(
                datetime.now(),
                self.config.experiment_name,
                self.run_number
            )
        )

    def _run_part(self, current_part_full_name: str) -> str | None:
        """
        Run the current part of the experiment.

        Returns the name of the next part to run, or a special command.
        """
        next_part_short_name = None
        try:
            # Make a copy of the experiment data so the original is
            # preserved if the current part encounters an error when it runs.
            self.new_experiment_data = deepcopy(self.experiment_data)

            # Handle the current part
            current_part = self.experiment_parts[current_part_full_name]
            if isinstance(current_part, Step):
                current_part.run_step()
                next_part_short_name = current_part._context.config.next_part.get("")
                self.experiment_trace.record(
                    StepEntry(
                        datetime.now(),
                        current_part_full_name,
                        self.experiment_data,
                        self.new_experiment_data
                    )
                )
            elif isinstance(current_part, Decision):
                route_name = current_part.decide_route()
                if route_name is None or route_name in COMMAND_NAMES:
                    next_part_short_name = route_name
                else:
                    next_part_short_name = current_part._context.config.next_part.get(route_name)
                self.experiment_trace.record(
                    DecisionEntry(
                        datetime.now(),
                        current_part_full_name,
                        next_part_short_name
                    )
                )
            elif isinstance(current_part, Flow):
                next_part_short_name = current_part.begin_flow()
                # Keep track of what level we're in
                self.flow_stack.append(current_part_full_name)
                self.experiment_trace.record(
                    FlowBeginEntry(
                        datetime.now(),
                        current_part_full_name,
                        next_part_short_name
                    )
                )
            else:
                # Your class needs to inherit from Step, Decision, or Flow
                raise TypeError(f"Unknown part type: {type(current_part)}")
            
            # Update the experiment data to the new data after a successful run
            self.experiment_data = deepcopy(self.new_experiment_data)
        except Exception as e:
            print(f"Error while running part '{current_part_full_name}': {e}")
            self.experiment_trace.record(
                ErrorEntry(
                    datetime.now(),
                    current_part_full_name,
                    str(e)
                )
            )
            # Ask the researcher what to do next
            next_part_short_name = None
        return next_part_short_name

    def _end_flow(self) -> str | None:
        """
        End the current flow and return to the parent flow.

        Returns the name of the next part to run, or a special command.
        """
        next_part_short_name = None
        if len(self.flow_stack) > 0:
            # End the current flow and return to the parent flow
            flow_part_full_name = self.flow_stack.pop()
            flow_part = self.experiment_parts[flow_part_full_name]
            try:
                flow_part.end_flow()
                next_part_short_name = flow_part._context.config.next_part.get("")
                self.experiment_trace.record(
                    FlowEndEntry(
                        datetime.now(),
                        flow_part_full_name
                    )
                )
            except Exception as e:
                print(f"Error ending flow '{flow_part_full_name}': {e}")
                self.experiment_trace.record(
                    ErrorEntry(
                        datetime.now(),
                        flow_part_full_name,
                        str(e)
                    )
                )
                # Ask the researcher what to do next
                next_part_short_name = None
        else:
            # When the top-level flow is done, end the experiment
            next_part_short_name = "quit"
        return next_part_short_name

    def _get_researcher_decision(self, current_part_full_name: str) -> str:
        """
        Get the researcher's decision on what to do next.

        Returns the name of the next part to run, or a special command.
        """
        self._print_flow_info()
        if current_part_full_name is None:
            print("\nNo part specified\n")
        else:
            print(f"\nUnknown part: '{current_part_full_name}'\n")
        next_part_short_name = self._get_next_from_researcher()
        self.experiment_trace.record(
            ResearcherDecisionEntry(
                datetime.now(),
                next_part_short_name
            )
        )
        return next_part_short_name

    def _get_data(self, global_name: str) -> object | None:
        """
        Get the global experiment data, returns None if not found
        """
        return self.new_experiment_data.get(global_name)

    def _set_data(self, global_name: str, value: object) -> None:
        """
        Set the global experiment data to the given value
        """
        self.new_experiment_data[global_name] = value

    def _copy_experiment_data(self) -> dict:
        """
        Get a copy of the current experiment data.
        """
        return deepcopy(self.new_experiment_data)

    def _add_part(self, part_config: PartConfig) -> None:
        """
        Add a new part to the experiment.

        If a part with the same name already exists, it is replaced.
        """
        try:
            part_type = self.config.part_types.get(part_config.type_name)
            part_context = PartContext(self, part_config)
            self.experiment_parts[part_config.full_name] = part_type.type(part_context)
            self.experiment_trace.record(
                PartAddEntry(
                    datetime.now(),
                    part_config.full_name,
                    part_config.file_path,
                    part_config.raw,
                    "step" if issubclass(part_type.type, Step) else
                    "decision" if issubclass(part_type.type, Decision) else
                    "flow" if issubclass(part_type.type, Flow) else
                    "unknown"
                )
            )
        except Exception as e:
            raise ConfigError(f"Failed to add part '{part_config.full_name}': {e}")

    def _remove_part(self, part_full_name: str) -> None:
        """
        Remove the part with the given name from the experiment.
        """
        self.experiment_parts.pop(part_full_name, None)
        self.experiment_trace.record(
            PartRemoveEntry(
                datetime.now(),
                part_full_name
            )
        )

    def _get_part(self, part_full_name: str) -> _Part | None:
        """
        Get the part with the given name, returns None if not found
        """
        return self.experiment_parts.get(part_full_name)

    def _construct_parts(self) -> None:
        """
        Construct instances of each part of the experiment as
        specified in the configuration and part_types dictionary
        """
        self.experiment_parts: dict[str, _Part] = {}
        for _, part_config in self.config.part_configs.items():
            self._add_part(part_config)

    def _build_output_dirs(self) -> None:
        """
        Build the output directory structure for this run.

        Note: this method figures out the run number by looking at
        the existing runs in the output directory.
        """
        print("Setting up output directories...")
        out_dir_for_experiment = os.path.join(self.config.out_dir, self.config.experiment_name)
        os.makedirs(out_dir_for_experiment, exist_ok=True)
        existing_runs = [
            d for d in os.listdir(out_dir_for_experiment)
            if os.path.isdir(os.path.join(out_dir_for_experiment, d)) and d.startswith("run_")
        ]
        # The run number is one larger than the largest existing run number
        self.run_number = max(
            (int(d.split("_")[1]) for d in existing_runs), default=0
        ) + 1
        self.out_dir_for_run = os.path.join(out_dir_for_experiment, f"run_{self.run_number}")
        print(f"Creating directory for experiment '{self.config.experiment_name}' run {self.run_number}: {self.out_dir_for_run}")
        os.makedirs(self.out_dir_for_run, exist_ok=False)
        # Copy the config file to the new directory
        shutil.copy(self.config.file_path, os.path.join(self.out_dir_for_run, "config.toml"))
        # Create the experiment trace file
        self.experiment_trace_file_path = os.path.join(self.out_dir_for_run, "trace.json")
        print(f"Creating experiment trace file: {self.experiment_trace_file_path}")
        self.experiment_trace = ExperimentTrace(output_file_path=self.experiment_trace_file_path)

    def _convert_to_full_name(self, short_name: str | None) -> str | None:
        """
        Convert a short part name to a full part name based on the current flow.
        """
        full_name = None
        flow_full_name = self._get_current_flow_full_name()
        if short_name is None or \
            short_name in COMMAND_NAMES or \
            not flow_full_name:
            full_name = short_name
        else:
            full_name = flow_full_name + "." + short_name
        return full_name

    def _get_current_flow_full_name(self) -> str:
        """
        Get the full name of the current flow we are in.
        """
        return self.flow_stack[-1] if len(self.flow_stack) > 0 else ""
    
    def _get_flow_parts_short_names(self, flow_full_name: str) -> list[str]:
        """
        Get the short names of the parts that are in the flow with the given name.
        """
        flow_parts_short_names = []
        for part_full_name in self.experiment_parts.keys():
            if not flow_full_name:
                # If we are at the top level, show all top-level parts
                if '.' not in part_full_name:
                    flow_parts_short_names.append(part_full_name)
            elif part_full_name.startswith(flow_full_name + "."):
                # If we are in a sub-flow, get all children of the sub-flow,
                # but not grandchildren or deeper
                short_name = part_full_name[len(flow_full_name) + 1:]
                if '.' not in short_name:
                    flow_parts_short_names.append(short_name)
        return flow_parts_short_names

    def _print_flow_info(self) -> None:
        """
        Show the researcher where they are and what parts are available.
        """
        flow_full_name = self._get_current_flow_full_name()
        if not flow_full_name:
            print(f"You are in the top-level flow of experiment '{self.config.experiment_name}', which has these parts:")
        else:
            print(f"You are in the '{flow_full_name}' flow, which has these parts:")
        short_names = self._get_flow_parts_short_names(flow_full_name)
        for short_name in short_names:
            full_name = self._convert_to_full_name(short_name)
            print(f" - {short_name} : {self.experiment_parts[full_name]._context.config.type_name}")

    def _get_next_from_researcher(self) -> str:
        """
        Prompt the researcher for what to do next.
        """
        print(
            "Enter one of the following:\n"
            " - the name of the next part to run\n"
            " - 'done' to leave the current flow\n"
            " - 'quit' to end the entire experiment\n\n"
        )
        val = ""
        while val == "":
            val = input("> ").strip()
        return val

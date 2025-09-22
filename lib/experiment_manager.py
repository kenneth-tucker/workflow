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
from lib.experiment_trace import ExperimentTrace, PartPathPiece, \
    AtPartEntry, ExperimentBeginEntry, ExperimentEndEntry, ErrorEntry, \
    PartAddEntry, PartRemoveEntry, ResearcherDecisionEntry, StepEntry, \
    DecisionEntry, FlowBeginEntry, FlowEndEntry, CustomEntry

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
        config: ExperimentConfig,
        on_output_dir_built: Optional[callable] = None
    ):
        self.config = config
        # A callback function that is called after the output directory is built
        self.on_output_dir_built = on_output_dir_built

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
        else:
            if old_trace is not None:
                raise ValueError("old_trace must be None when mode is NORMAL")
            old_part_path = []
        
        # Setup the new experiment run
        self._begin_experiment_run()

        # Ensure the new trace will be closed correctly
        with self.new_trace:

            # Run the experiment, part by part
            path_index = 0
            current_part_full_name = self.config.initial_part_name
            while True:
                # If we are (still) retracing an old run, check we are on the same path
                if path_index < len(old_part_path) and \
                    old_part_path[path_index].part_name != current_part_full_name:
                    raise RuntimeError(
                        f"Path deviation at path index {path_index} while retracing old run: "
                        f"expected '{old_part_path[path_index].part_name}', got '{current_part_full_name}'"
                    )
                
                # Get any part_data associated with this part in the old trace
                self.old_trace_part_data = \
                    old_part_path[path_index].part_data if path_index < len(old_part_path) else None
                
                # Clear any part_data from the previous part
                self.new_trace_part_data = None

                # Always record the part (or command) we are at
                self.new_trace.record(
                    AtPartEntry(
                        datetime.now(),
                        current_part_full_name
                    )
                )

                # Handle the current part or command
                if current_part_full_name == "quit":
                    if path_index < len(old_part_path) - 1:
                        # If retracing, use the past researcher's decision from the old run
                        next_part_short_name = self._convert_to_short_name(
                            old_part_path[path_index + 1].part_name
                        )
                    elif mode == ExperimentMode.CONTINUE and \
                        path_index == len(old_part_path) - 1:
                        # If continuing, ask the current researcher what to do next
                        next_part_short_name = self._get_researcher_decision(current_part_full_name)
                    else:
                        # Quit the experiment
                        break
                    self.new_trace.record(
                        ResearcherDecisionEntry(
                            datetime.now(),
                            next_part_short_name
                        )
                    )
                elif current_part_full_name == "done":
                    next_part_short_name = self._end_flow()
                elif current_part_full_name is None or \
                    current_part_full_name not in self.experiment_parts:
                    if path_index < len(old_part_path) - 1:
                        # If retracing, use the past researcher's decision from the old run
                        next_part_short_name = self._convert_to_short_name(
                            old_part_path[path_index + 1].part_name
                        )
                    else:
                        # Ask the current researcher what to do next
                        next_part_short_name = self._get_researcher_decision(current_part_full_name)
                    self.new_trace.record(
                        ResearcherDecisionEntry(
                            datetime.now(),
                            next_part_short_name
                        )
                    )
                else:
                    next_part_short_name = self._run_part(current_part_full_name)

                # Move to the next part or command
                path_index += 1
                current_part_full_name = self._convert_to_full_name(next_part_short_name)

            # Tear down the experiment run
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
        print(f"Experiment '{self.config.experiment_name}' run {self.run_number} started", flush=True)
        self.new_trace.record(
            ExperimentBeginEntry(
                datetime.now(),
                self.config.experiment_name,
                self.run_number,
                self.experiment_data
            )
        )

    def _end_experiment_run(self) -> None:
        print(f"Experiment '{self.config.experiment_name}' run {self.run_number} completed", flush=True)
        self.new_trace.record(
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
                self.new_trace.record(
                    StepEntry(
                        datetime.now(),
                        current_part_full_name,
                        self.experiment_data,
                        self.new_experiment_data,
                        self.new_trace_part_data
                    )
                )
            elif isinstance(current_part, Decision):
                route_name = current_part.decide_route()
                if route_name is None or route_name in COMMAND_NAMES:
                    next_part_short_name = route_name
                else:
                    next_part_short_name = current_part._context.config.next_part.get(route_name)
                self.new_trace.record(
                    DecisionEntry(
                        datetime.now(),
                        current_part_full_name,
                        next_part_short_name,
                        self.new_trace_part_data
                    )
                )
            elif isinstance(current_part, Flow):
                next_part_short_name = current_part.begin_flow()
                # Keep track of what level we're in
                self.flow_stack.append(current_part_full_name)
                self.new_trace.record(
                    FlowBeginEntry(
                        datetime.now(),
                        current_part_full_name,
                        next_part_short_name,
                        self.new_trace_part_data
                    )
                )
            else:
                # Your class needs to inherit from Step, Decision, or Flow
                raise TypeError(f"Unknown part type: {type(current_part)}")
            
            # Update the experiment data to the new data after a successful run
            self.experiment_data = deepcopy(self.new_experiment_data)
        except Exception as e:
            print(f"Error while running part '{current_part_full_name}': {e}", flush=True)
            self.new_trace.record(
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
                self.new_trace.record(
                    FlowEndEntry(
                        datetime.now(),
                        flow_part_full_name,
                        self.new_trace_part_data
                    )
                )
            except Exception as e:
                print(f"Error ending flow '{flow_part_full_name}': {e}", flush=True)
                self.new_trace.record(
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
            print("\nYour decision was requested")
        elif current_part_full_name == "quit":
            print("\nThe experiment can be continued")
        else:
            print(f"\nUnknown part '{current_part_full_name}' encountered")
        print("What would you like to do next?")
        next_part_short_name = self._get_next_from_researcher()
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
    
    def _save_data_to_trace_entry(self, part_data: dict) -> None:
        """
        Store a data dictionary into the current trace entry as
        'part_data'.
        """
        self.new_trace_part_data = part_data

    def _load_data_from_retrace_entry(self) -> dict | None:
        """
        When retracing an old run of an experiment, retrieve any
        'part_data' dictionary stored in the old trace entry.
        """
        return self.old_trace_part_data

    def _insert_custom_trace_entry(self, event_type: str, event_data: dict | None) -> None:
        """
        Insert a custom trace entry into the experiment trace.
        """
        self.new_trace.record(
            CustomEntry(
                datetime.now(),
                event_type,
                event_data
            )
        )

    def _add_part(self, part_config: PartConfig) -> None:
        """
        Add a new part to the experiment.

        If a part with the same name already exists, it is replaced.
        """
        try:
            part_type = self.config.part_types.get(part_config.type_name)
            part_context = PartContext(self, part_config)
            self.experiment_parts[part_config.full_name] = part_type.type(part_context)
            self.new_trace.record(
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
        self.new_trace.record(
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
        print("Setting up output directories...", flush=True)
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
        print(f"Creating directory for experiment '{self.config.experiment_name}' run {self.run_number}: {self.out_dir_for_run}", flush=True)
        os.makedirs(self.out_dir_for_run, exist_ok=False)
        # Copy the config file to the new directory
        shutil.copy(self.config.file_path, os.path.join(self.out_dir_for_run, "config.toml"))
        # Create the experiment trace file
        self.new_trace_file_path = os.path.join(self.out_dir_for_run, "trace.json")
        print(f"Creating experiment trace file: {self.new_trace_file_path}", flush=True)
        self.new_trace = ExperimentTrace(output_file_path=self.new_trace_file_path)
        # Call the callback function, if provided
        if self.on_output_dir_built is not None:
            self.on_output_dir_built(self.out_dir_for_run)

    def _convert_to_short_name(self, full_name: str | None) -> str | None:
        """
        Extract the short part name from a full part name.
        """
        if full_name is None or full_name in COMMAND_NAMES:
            return full_name
        return full_name.split(".")[-1]

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
            print(f"You are in the top-level flow of experiment '{self.config.experiment_name}', which has these parts:", flush=True)
        else:
            print(f"You are in the '{flow_full_name}' flow, which has these parts:", flush=True)
        short_names = self._get_flow_parts_short_names(flow_full_name)
        for short_name in short_names:
            full_name = self._convert_to_full_name(short_name)
            print(f" - {short_name} : {self.experiment_parts[full_name]._context.config.type_name}", flush=True)

    def _get_next_from_researcher(self) -> str:
        """
        Prompt the researcher for what to do next.
        """
        print(
            "Enter one of the following:\n"
            " - the name of the next part to run\n"
            " - 'done' to leave the current flow\n"
            " - 'quit' to end the entire experiment\n"
        )
        val = ""
        while val == "":
            val = input("> ").strip()
            if val not in self._get_flow_parts_short_names(self._get_current_flow_full_name()) and \
                val not in COMMAND_NAMES:
                print(f"Invalid input: '{val}'")
                val = ""
        return val

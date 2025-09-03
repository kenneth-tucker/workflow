# The main file to run the Workflow manager
#
# Example Commands:
#
# Start a new run of an experiment
# workflow.py <config_file>
#
# Try to rerun an experiment based on a trace file, including the ending of the experiment
# workflow.py <config_file> --rerun <old_trace_file>
#
# Same as rerun, except the experiment can be continued from the last part before it ended
# workflow.py <config_file> --continue <old_trace_file>

import argparse
import os
import sys

# Allow running this script directly from any directory without installing the package
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from workflow.lib.experiment_config import ExperimentConfig
from workflow.lib.experiment_manager import ExperimentManager, ExperimentMode
from workflow.lib.experiment_trace import ExperimentTrace

def main():
    # Get the arguments
    parser = argparse.ArgumentParser(description="Run an experiment")
    parser.add_argument("config_file", type=str, help="Path to the configuration file (required)")
    parser.add_argument("--rerun", dest="rerun_file", type=str, default=None, help="Path to an old trace file to rerun (optional)")
    parser.add_argument("--continue", dest="continue_file", type=str, default=None, help="Path to an old trace file to continue (optional)")
    args = parser.parse_args()
    config_file = args.config_file
    if args.rerun_file and args.continue_file:
        raise ValueError("Cannot use both --rerun and --continue options at the same time")
    elif args.rerun_file:
        mode = ExperimentMode.RERUN
        old_trace_file = args.rerun_file
    elif args.continue_file:
        mode = ExperimentMode.CONTINUE
        old_trace_file = args.continue_file
    else:
        mode = ExperimentMode.NORMAL
        old_trace_file = None
    # Setup the config from the provided config file
    config = ExperimentConfig(config_file)
    # Read in the old trace file, if provided
    old_trace = ExperimentTrace(input_file_path=old_trace_file) if old_trace_file else None
    # Setup the experiment
    manager = ExperimentManager(config, mode, old_trace=old_trace)
    # Run the experiment, returns on completion
    manager.run()

if __name__ == "__main__":
    main()

# The main file to run the Workflow manager
#
# Example Commands:
#
# Start a new run of an experiment
# workflow.py <config_file>

# Start an experiment and open a web page to view the experiment
# Note: see tools/view_experiment.py for setup instructions
# workflow.py <config_file> --view
#
# Try to rerun an experiment based on a trace file, including the ending of the experiment
# workflow.py <config_file> --rerun <old_trace_file>
#
# Same as rerun, except the experiment can be continued from the last part before it ended
# workflow.py <config_file> --continue <old_trace_file>

import argparse
import os
import sys
import subprocess

# Allow running this script directly from any directory without installing the package
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.experiment_config import ExperimentConfig
from lib.experiment_manager import ExperimentManager, ExperimentMode
from lib.experiment_trace import ExperimentTrace

def open_experiment_in_browser(run_dir: str):
    """
    Open the experiment in a web browser.

    We use a separate process to run the the view_experiment module,
    so that it does not interfere with the main experiment process,
    including clogging its stdout/stderr.
    """
    subprocess.Popen([sys.executable, "-m", "tools.view_experiment", run_dir],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    # Get the arguments
    parser = argparse.ArgumentParser(description="Run an experiment")
    parser.add_argument("config_file", type=str, help="Path to the configuration file (required)")
    parser.add_argument("--view", action="store_true", help="Open a web page to view the experiment (optional)")
    parser.add_argument("--rerun", dest="rerun_file", type=str, default=None, help="Path to an old trace file to rerun (optional)")
    parser.add_argument("--continue", dest="continue_file", type=str, default=None, help="Path to an old trace file to continue (optional)")
    args = parser.parse_args()
    config_file = args.config_file
    if args.view:
        on_output_dir_built = open_experiment_in_browser
    else:
        on_output_dir_built = None
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
    manager = ExperimentManager(config, on_output_dir_built=on_output_dir_built)
    # Run the experiment one time, returns on completion
    manager.run(mode, old_trace)

if __name__ == "__main__":
    main()

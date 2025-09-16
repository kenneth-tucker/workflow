# Show an ongoing experiment in a web browser
#
# Example Command:
# view_experiment.py <run_dir>

import argparse
import os
from impl.trace_monitor import TraceMonitor
from impl.trace_printer import TracePrinter

def main():
    # Get the arguments
    parser = argparse.ArgumentParser(description="Show an ongoing experiment in a web browser")
    parser.add_argument("run_dir", type=str, help="Path to the run directory (required)")
    args = parser.parse_args()
    run_dir = os.path.normpath(args.run_dir)
    trace_file_path = os.path.join(run_dir, "trace.json")
    # Monitor changes in the trace file and update the viewers
    monitor = TraceMonitor(trace_file_path)
    monitor.add_observer("printer", TracePrinter())
    monitor.monitor()

if __name__ == "__main__":
    main()

# Show an ongoing experiment in a web browser
#
# Example Command:
# view_experiment.py <run_dir>
#
# Setup Instructions:
#
# 1. Install the graphviz Python package using pip:
# pip install graphviz
#
# 2. Install Graphviz rendering software, which is
# required for generating visualizations:
# https://graphviz.org/download/
#
# 3. Install Flask for the web server:
# pip install flask

import argparse
import os
import sys
from time import sleep
import webbrowser
import threading

# Allow running this script directly from any directory without installing the package
if __package__ is None or __package__ == "":
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from tools.impl.trace_monitor import TraceMonitor
from tools.impl.trace_printer import TracePrinter
from tools.impl.snapshot_generator import SnapshotGenerator
from tools.impl.web_server import web_data, app

DEFAULT_SERVER_NAME = "127.0.0.1"
DEFAULT_PORT_NUMBER = 50000

def view_experiment(run_dir: str):
    run_dir = os.path.normpath(run_dir)
    trace_file_path = os.path.join(run_dir, "trace.json")
    # Whenever there is a new trace, print it to the console for debugging
    trace_printer = TracePrinter()
    # Whenever there is a new trace, generate a new snapshot of the experiment
    # (which includes a flowchart visualization)
    snapshot_generator = SnapshotGenerator()
    # Make the web data reflect new snapshots as they arrive
    snapshot_generator.add_observer("web_data", web_data)
    # Setup the web server to show the experiment
    # Note: you may need to adjust the host and port as needed
    # (e.g. if the port is already in use)
    # Note: we run the server in a separate thread so that
    # it does not block the trace monitoring
    server_thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": DEFAULT_SERVER_NAME,
            "port": DEFAULT_PORT_NUMBER,
            "debug": True,
            "use_reloader": False
        },
        daemon=True
    )
    server_thread.start()
    # Give the server a moment to start up
    sleep(1)
    # Open the web page in the default browser
    webbrowser.open(f"http://{DEFAULT_SERVER_NAME}:{DEFAULT_PORT_NUMBER}")
    # Update the web view whenever there is a new snapshot
    # React to changes in the trace file
    trace_monitor = TraceMonitor(trace_file_path)
    # Uncomment to see trace events printed to the console
    #trace_monitor.add_observer("trace_printer", trace_printer)
    trace_monitor.add_observer("snapshot_generator", snapshot_generator)
    # Returns when the end of the trace file is reached
    trace_monitor.monitor()
    # Show the web page for a bit longer, in case the user
    # did not get a chance to see the final state
    sleep(5)

def main():
    parser = argparse.ArgumentParser(description="Show an ongoing experiment in a web browser")
    parser.add_argument("run_dir", type=str, help="Path to the run directory (required)")
    args = parser.parse_args()
    view_experiment(args.run_dir)

if __name__ == "__main__":
    main()

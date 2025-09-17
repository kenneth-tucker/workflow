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
from time import sleep
import webbrowser
from impl.trace_monitor import TraceMonitor
from impl.trace_printer import TracePrinter
from impl.snapshot_generator import SnapshotGenerator
from impl.web_server import PORT_NUMBER, SERVER_NAME, web_data, app
import threading

def main():
    # Get the arguments
    parser = argparse.ArgumentParser(description="Show an ongoing experiment in a web browser")
    parser.add_argument("run_dir", type=str, help="Path to the run directory (required)")
    args = parser.parse_args()
    run_dir = os.path.normpath(args.run_dir)
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
            "host": SERVER_NAME,
            "port": PORT_NUMBER,
            "debug": True,
            "use_reloader": False
        },
        daemon=True
    )
    server_thread.start()
    sleep(1)  # Give the server a moment to start
    # Open the web page in the default browser
    webbrowser.open(f"http://{SERVER_NAME}:{PORT_NUMBER}")
    # Update the web view whenever there is a new snapshot
    # React to changes in the trace file
    trace_monitor = TraceMonitor(trace_file_path)
    # Uncomment to see trace events printed to the console
    #trace_monitor.add_observer("trace_printer", trace_printer)
    trace_monitor.add_observer("snapshot_generator", snapshot_generator)
    # Returns when the end of the trace file is reached
    trace_monitor.monitor()

if __name__ == "__main__":
    main()

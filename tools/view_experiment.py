# Show an ongoing or completed experiment in a web browser
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
import socket

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
MAX_PORT_NUMBER = 50100  # Try up to this port

def find_open_port(host, start_port, max_port):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No open port found in range {start_port}-{max_port-1}")

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
    # Find an open port for the web server
    port_number = find_open_port(DEFAULT_SERVER_NAME, DEFAULT_PORT_NUMBER, MAX_PORT_NUMBER)

    # Setup the web server to show the experiment
    # Note: we run the server in a separate thread so that
    # it does not block the trace monitoring
    server_thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": DEFAULT_SERVER_NAME,
            "port": port_number,
            "debug": False,
            "use_reloader": False
        },
        daemon=True
    )
    server_thread.start()
    # Give the server a moment to start up
    sleep(1)
    # Open the web page in the default browser
    webbrowser.open(f"http://{DEFAULT_SERVER_NAME}:{port_number}")

    # Update the web view whenever there is a new snapshot
    # React to changes in the trace file
    trace_monitor = TraceMonitor(trace_file_path)
    # Uncomment to see trace events printed to the console
    #trace_monitor.add_observer("trace_printer", trace_printer)
    trace_monitor.add_observer("snapshot_generator", snapshot_generator)
    # Returns when the end of the trace file is reached
    trace_monitor.monitor()
    print("Experiment monitoring completed")

    # Keep the server alive until the user is done
    input("Press <ENTER> to exit...")

def main():
    parser = argparse.ArgumentParser(description="Show an ongoing experiment in a web browser")
    parser.add_argument("run_dir", type=str, help="Path to the run directory (required)")
    args = parser.parse_args()
    view_experiment(args.run_dir)

if __name__ == "__main__":
    main()

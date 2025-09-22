"""
Implements a web page for viewing an ongoing experiment.
"""

from datetime import datetime
import atexit
import os
import psutil
import threading
from flask import Flask, render_template, jsonify
from tools.impl.flowchart import FlowChart
from tools.impl.snapshot import Snapshot
from tools.impl.snapshot_generator import SnapshotConsumer

class WebData(SnapshotConsumer):
    """
    Maintains the viewable content for the web page, as new snapshots arrive.
    """
    def __init__(self):
        self.experiment_json = {
            "state": "",
            "name": "",
            "run": "",
            "snapshots": [],
        }
        # Track which flowchart PNGs are in use by this web server instance
        # and maintain a .inuse file with the list of PNGs
        self._inuse_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webserver_inuse")
        if not os.path.exists(self._inuse_dir):
            os.makedirs(self._inuse_dir)
        self._pid = os.getpid()
        self._inuse_file = os.path.join(self._inuse_dir, f"webserver_{self._pid}.inuse")
        self._inuse_pngs = set()
        atexit.register(self._cleanup_inuse_file)
        # Clear any old in-use PNGs from previous runs
        self.clear_flowchart_pngs()
        # Ensure thread-safe access to experiment_json
        self._lock = threading.Lock()

    def _write_inuse_file(self):
        with open(self._inuse_file, "w") as f:
            for png in self._inuse_pngs:
                f.write(f"{png}\n")

    def _cleanup_inuse_file(self):
        try:
            if os.path.exists(self._inuse_file):
                os.remove(self._inuse_file)
        except Exception:
            pass

    def clear_flowchart_pngs(self):
        """
        Remove any old flowchart PNG files from the static/flowcharts directory
        that are not in use by any running web server.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(base_dir, "static", "flowcharts")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Clean up stale .inuse files (whose PID is not running)
        for fname in os.listdir(self._inuse_dir):
            if fname.startswith("webserver_") and fname.endswith(".inuse"):
                pid_str = fname[len("webserver_"):-len(".inuse")]
                try:
                    pid = int(pid_str)
                    if not psutil.pid_exists(pid):
                        os.remove(os.path.join(self._inuse_dir, fname))
                except Exception:
                    pass

        # Gather all in-use PNGs from all .inuse files
        inuse_pngs = set()
        for fname in os.listdir(self._inuse_dir):
            if fname.endswith(".inuse"):
                try:
                    with open(os.path.join(self._inuse_dir, fname), "r") as f:
                        for line in f:
                            inuse_pngs.add(line.strip())
                except Exception:
                    pass

        # Remove PNGs not in use
        for filename in os.listdir(dir_path):
            if filename.endswith(".png"):
                if filename not in inuse_pngs:
                    file_path = os.path.join(dir_path, filename)
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

    def save_flowchart_png(self, flowchart: FlowChart) -> str:
        """
        Save the flowchart as a PNG file in the static/flowcharts directory,
        and return the URL path to access it. Track the PNG as in use by this server.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = f"{timestamp_str}.png"
        file_path = os.path.join(base_dir, "static", "flowcharts", filename)
        flowchart.save_as_png(file_path)
        self._inuse_pngs.add(filename)
        self._write_inuse_file()
        return f"/static/flowcharts/{filename}"

    def on_new_snapshot(self, snapshot: Snapshot):
        flowchart_url = self.save_flowchart_png(snapshot.flowchart)
        with self._lock:
            snapshot_index = len(self.experiment_json["snapshots"])
            snapshot_json = {
                "timestamp": snapshot.timestamp.isoformat(),
                "event_info": snapshot.event_info,
                "label": f"{snapshot_index + 1}",
                "flowchart": flowchart_url,
                "data": snapshot.experiment_model.experiment_data
            }
            self.experiment_json["snapshots"].append(snapshot_json)
            self.experiment_json["state"] = snapshot.experiment_model.experiment_state.value or ""
            if not self.experiment_json["name"]:
                self.experiment_json["name"] = snapshot.experiment_model.experiment_name or ""
            if not self.experiment_json["run"]:
                self.experiment_json["run"] = str(snapshot.experiment_model.run_number or "")

# Create a global instance to hold the web data
web_data = WebData()

# Create the Flask app
app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    """
     Serve the main index page.
    """
    return render_template("index.html")

@app.route("/experiment_data")
def experiment_data():
    """
    Serve the current experiment data as JSON, when requested by the client.
    """
    with web_data._lock:
        return jsonify(web_data.experiment_json)

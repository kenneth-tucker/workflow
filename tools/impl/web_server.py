"""
Implements a web page for viewing an ongoing experiment.
"""

from datetime import datetime
import os
import threading
from flask import Flask, render_template, jsonify, url_for
from tools.impl.flowchart import FlowChart
from tools.impl.snapshot import Snapshot
from tools.impl.snapshot_generator import SnapshotConsumer

class WebData(SnapshotConsumer):
    """
    Maintains the viewable content for the web page, as new snapshots arrive.
    """
    def __init__(self):
        self.experiment_json = {
            "name": "",
            "run": "",
            "snapshots": [],
        }
        self.clear_flowchart_pngs()
        # Ensure thread-safe access to experiment_json
        self._lock = threading.Lock()

    def clear_flowchart_pngs(self):
        """
        Remove any old flowchart PNG files from the static/flowcharts directory.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(base_dir, "static", "flowcharts")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for filename in os.listdir(dir_path):
            if filename.endswith(".png"):
                file_path = os.path.join(dir_path, filename)
                os.remove(file_path)

    def save_flowchart_png(self, flowchart: FlowChart) -> str:
        """
        Save the flowchart as a PNG file in the static/flowcharts directory,
        and return the URL path to access it.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "static", "flowcharts", f"{timestamp_str}")
        flowchart.save_as_png(file_path)
        return f"/static/flowcharts/{timestamp_str}.png"

    def on_new_snapshot(self, snapshot: Snapshot):
        flowchart_url = self.save_flowchart_png(snapshot.flowchart)
        with self._lock:
            snapshot_index = len(self.experiment_json["snapshots"])
            snapshot_json = {
                "timestamp": snapshot.timestamp.isoformat(),
                "event": snapshot.event,
                "label": f"{snapshot_index}",
                "flowchart": flowchart_url,
                "data": snapshot.experiment_model.experiment_data
            }
            self.experiment_json["snapshots"].append(snapshot_json)
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

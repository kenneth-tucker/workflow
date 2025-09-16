import json
import time

# The latest trace file version this tool supports
SUPPORTED_TRACE_FILE_VERSION = 1

class TraceObserver:
    """
    Base class for objects that want to observe trace file entries.
    """
    def on_trace_entry(self, trace_entry: dict):
        raise NotImplementedError("on_trace_entry() must be implemented in subclasses")

class TraceMonitor:
    """
    Monitor a trace file and notify any registered observers of new entries.
    """
    def __init__(self, trace_file_path: str):
        self.trace_file_path = trace_file_path
        self.observers = {}

    def add_observer(self, id: str, observer: TraceObserver):
        self.observers[id] = observer

    def remove_observer(self, id: str):
        self.observers.pop(id, None)

    def monitor(self):
        # Stream in the trace file data, line by line, and update any observers
        self.trace_entries = []
        with open(self.trace_file_path, "r") as f:
            footer_reached = False
            while not footer_reached:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                line_index = f.tell()
                stripped_line = line.rstrip(", \n\r\t")
                if line.startswith('{"version":'):
                    # JSON header (e.g. '{"version": 1, "trace": [')
                    version_str = line.split('"version":', 1)[1].split(",", 1)[0].strip()
                    version = int(version_str)
                    if not version:
                        raise ValueError(f"Missing version number in trace file header")
                    if version > SUPPORTED_TRACE_FILE_VERSION:
                        raise ValueError(f"Trace file version {version} is not supported (max supported is {SUPPORTED_TRACE_FILE_VERSION})")
                elif stripped_line == "":
                    # Skip separators
                    pass
                else:
                    # JSON entry line (e.g. '{"timestamp": "...", "event": "...", ...},')
                    # Note: may include the closing ']}'
                    if line.endswith("]}"):
                        footer_reached = True
                        stripped_line = stripped_line[:-2]  # Remove the ']}'
                    try:
                        entry = json.loads(stripped_line)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Error parsing JSON in trace file: {e}")
                    self.trace_entries.append(entry)
                    for observer in self.observers.values():
                        observer.on_trace_entry(entry)

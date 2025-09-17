

import pprint
from impl.trace_monitor import TraceObserver

class TracePrinter(TraceObserver):
    """
    Observer that prints trace entries to the console in a human-readable format.
    """
    def on_trace_entry(self, trace_entry: dict):
        pprint.pprint(trace_entry)
        print()

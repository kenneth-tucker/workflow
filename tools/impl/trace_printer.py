

from impl.trace_monitor import TraceObserver

class TracePrinter(TraceObserver):
    """
    Observer that prints trace entries to the console.
    """
    def on_trace_entry(self, trace_entry: dict):
        print(f"Trace Entry: {trace_entry}\n")

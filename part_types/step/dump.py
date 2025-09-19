from lib.experiment_parts import Step

class DumpStep(Step):
    """"
    A step part that prints all current experiment data to the console,
    in alphabetical order by data name.
    """
    def __init__(self, context):
        super().__init__(context)

    def run_step(self) -> None:
        print("Experiment Data:", flush=True)
        experiment_data = self.copy_experiment_data()
        if not experiment_data:
            print("  (no data)", flush=True)
            return
        for name, value in sorted(experiment_data.items()):
            print(f"  {name}: {value}", flush=True)

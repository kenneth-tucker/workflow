from lib.experiment_parts import Step

class DumpStep(Step):
    """"
    A step part that prints all current experiment data to the console.
    """
    def __init__(self, context):
        super().__init__(context)

    def run_step(self) -> None:
        print("Experiment Data:")
        experiment_data = self.copy_experiment_data()
        if not experiment_data:
            print("  (no data)")
            return
        for name, value in experiment_data.items():
            print(f"  {name}: {value}")

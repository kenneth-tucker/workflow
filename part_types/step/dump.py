from lib.experiment_parts import Step

class DumpStep(Step):
    """"
    A step part that prints all current experiment data to the console,
    in alphabetical order by data name. Hidden data (names starting with _)
    are grouped at the end under a "Hidden" section.
    """
    def __init__(self, context):
        super().__init__(context)

    def run_step(self) -> None:
        print("Experiment Data:", flush=True)
        experiment_data = self.copy_experiment_data()
        if not experiment_data:
            print("  (no data)", flush=True)
            return

        def is_hidden_key(key):
            return any(k.startswith('_') for k in key.split('.'))

        def flatten_data(obj, prefix=''):
            result = {}
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    result.update(flatten_data(v, full_key))
                else:
                    result[full_key] = v
            return result

        flat_data = flatten_data(experiment_data)
        visible = sorted([k for k in flat_data if not is_hidden_key(k)])
        hidden = sorted([k for k in flat_data if is_hidden_key(k)])

        for name in visible:
            print(f"  {name}: {flat_data[name]}", flush=True)
        if hidden:
            print(f"  Hidden ({len(hidden)} Item{'s' if len(hidden) != 1 else ''}):", flush=True)
            for name in hidden:
                print(f"    {name}: {flat_data[name]}", flush=True)

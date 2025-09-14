
from lib.experiment_parts import Step
from lib.utils.exceptions import ConfigError
from lib.utils.parse_config import execute_statement_with_data_values

# Calculate expressions and store results
class ExpressionStep(Step):
    def __init__(self, context):
        super().__init__(context)
        self.statements: list[str] = \
            self.get_config("statements", allow=[list])
        # Check each statement is a string
        for statement in self.statements:
            if not isinstance(statement, str):
                raise ConfigError(
                    f"Invalid statement '{statement}' in part '{self.get_full_name()}': "
                    "must be a string"
                )

    def run_step(self) -> None:
        for statement in self.statements:
            parts = statement.split("=")
            if len(parts) != 2:
                raise ConfigError(
                    f"Invalid statement '{statement}' in part '{self.get_full_name()}': "
                    "must be of the form '<data_name> = <expression>'"
                )
            data_name = parts[0].strip()
            expression = parts[1].strip()
            try:
                # Evaluate the expression using the experiment data as variables
                result = execute_statement_with_data_values(
                    expression,
                    self.copy_experiment_data()
                )
                # Store the result in the experiment data
                self.set_output(data_name, result, can_use_global=True)
            except Exception as e:
                raise ConfigError(
                    f"Could not evaluate expression '{expression}' in part "
                    f"'{self.get_full_name()}': {e}"
                )

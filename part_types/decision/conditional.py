from typing import override
from lib.experiment_parts import Decision
from lib.utils.exceptions import ConfigError
from lib.utils.parse_config import execute_statement_with_data_values, extract_data_names
from lib.utils.part_utils import DecisionRoute

class ConditionalDecision(Decision):
    """
    A decision part that decides which route to take based on conditional statements.
    The statements are evaluated in order, and the first one that evaluates to true is taken.
    Statements are of the form:
        <route_name> if <condition>
        ...
        else <route_name>
    where <condition> is a boolean expression containing experiment data names as {name}.
    """
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

    @override
    def decide_route(self) -> DecisionRoute:
        for i, statement in enumerate(self.statements):
            parsed_statement = self._parse_statement(statement)
            if not parsed_statement:
                raise ConfigError(
                    f"Invalid statement '{statement}' in part '{self.get_full_name()}'"
                )
            if parsed_statement["type"] == "if":
                # Retrieve the value of each data name in the condition
                data_values = {}
                for data_name in parsed_statement["data_names"]:
                    data_values[data_name] = self.get_input(data_name, can_use_global=True)
                # Try to have the Python interpreter evaluate the condition
                if self._evaluate_condition(parsed_statement["condition"], data_values):
                    # The condition is true so use this statement's route
                    return DecisionRoute(parsed_statement["route_name"], can_use_part_name=True)
            elif parsed_statement["type"] == "else":
                if i != len(self.statements) - 1:
                    raise ConfigError(
                        f"Else statement must be last in part '{self.get_full_name()}'"
                    )
                return DecisionRoute(parsed_statement["route_name"], can_use_part_name=True)
        # No route could be determined from the given statements
        return DecisionRoute(None)

    def _parse_statement(self, statement: str) -> dict:
        parts = statement.split(" if ")
        parsed_statement = {}
        if len(parts) == 2:
            # <route_name> if <condition>
            parsed_statement = {
                "type": "if",
                "route_name": parts[0].strip(),
                "condition": parts[1].strip()
            }
            # Extract all {name} items and list them as data_names
            parsed_statement["data_names"] = \
                extract_data_names(parsed_statement["condition"])
        elif statement.startswith("else "):
            parsed_statement = {
                "type": "else",
                "route_name": statement[5:].strip(),
            }
        return parsed_statement

    def _evaluate_condition(self, condition: str, data_values: dict) -> bool:
        try:
            return bool(execute_statement_with_data_values(condition, data_values))
        except Exception as e:
            raise ValueError(
                f"Error evaluating condition '{condition}' in part '{self.get_full_name()}': {e}"
            )

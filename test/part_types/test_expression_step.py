"""
Tests for part_types/step/expression.py.
"""
import pytest

from lib.utils.exceptions import ConfigError
from part_types.step.expression import ExpressionStep


def make_expression_step(
    make_part_context,
    fake_manager,
    statements,
    data=None,
    input_names=None,
    output_names=None,
):
    fake_manager.data.update(data or {})
    context = make_part_context(
        config_values={"statements": statements},
        input_names=input_names or {},
        output_names=output_names or {},
    )
    return ExpressionStep(context)


class TestExpressionStepConstruction:
    def test_rejects_non_list_statements_config(self, make_part_context, fake_manager):
        context = make_part_context(config_values={"statements": "not a list"})

        with pytest.raises(ConfigError):
            ExpressionStep(context)

    def test_rejects_non_string_statement(self, make_part_context, fake_manager):
        with pytest.raises(ConfigError):
            make_expression_step(make_part_context, fake_manager, statements=[123])


class TestExpressionStepRun:
    def test_computes_and_stores_result_from_global_data(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["total = {a} + {b}"],
            data={"a": 2, "b": 3},
        )

        step.run_step()

        assert fake_manager._get_data("total") == 5

    def test_supports_multiple_statements_in_order(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["result = 1 + 1", "result_two = {result} * 2"],
        )

        step.run_step()

        assert fake_manager._get_data("result") == 2
        assert fake_manager._get_data("result_two") == 4

    def test_raises_config_error_on_malformed_statement(self, make_part_context, fake_manager):
        step = make_expression_step(make_part_context, fake_manager, statements=["not_an_assignment"])

        with pytest.raises(ConfigError, match="must be of the form"):
            step.run_step()

    def test_raises_config_error_when_referenced_data_name_is_missing(
        self, make_part_context, fake_manager
    ):
        step = make_expression_step(make_part_context, fake_manager, statements=["total = {missing} + 1"])

        with pytest.raises(ConfigError):
            step.run_step()

    def test_tolerates_extra_whitespace_around_statement_parts(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["  total   =   {a} + 1  "],
            data={"a": 4},
        )

        step.run_step()

        assert fake_manager._get_data("total") == 5

    def test_uses_input_names_mapping_over_can_use_global_fallback(self, make_part_context, fake_manager):
        # "a" is mapped to a differently-named global; the un-mapped global "a"
        # is left unset to prove the mapping (not the fallback) is what's used.
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["total = {a} + 1"],
            data={"mapped_a": 4},
            input_names={"a": "mapped_a"},
        )

        step.run_step()

        assert fake_manager._get_data("total") == 5

    def test_uses_output_names_mapping_to_store_result(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["total = 1 + 1"],
            output_names={"total": "mapped_total"},
        )

        step.run_step()

        assert fake_manager._get_data("mapped_total") == 2
        assert fake_manager._get_data("total") is None

    def test_equality_operator_in_expression(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["flag = {a} == {b}"],
            data={"a": 1, "b": 1},
        )
        step.run_step()
        assert fake_manager._get_data("flag") is True

    def test_run_step_does_not_leak_state_between_runs(self, make_part_context, fake_manager):
        step = make_expression_step(
            make_part_context,
            fake_manager,
            statements=["total = {a} + 1"],
            data={"a": 1},
        )

        step.run_step()
        assert fake_manager._get_data("total") == 2

        fake_manager.data["a"] = 10
        step.run_step()
        assert fake_manager._get_data("total") == 11

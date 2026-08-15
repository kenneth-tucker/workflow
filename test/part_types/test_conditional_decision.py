"""
Tests for part_types/decision/conditional.py (ConditionalDecision).
"""
import pytest

from lib.utils.exceptions import ConfigError
from part_types.decision.conditional import ConditionalDecision


def make_conditional_decision(
    make_part_context,
    fake_manager,
    statements,
    data=None,
):
    if fake_manager is not None:
        fake_manager.data.update(data or {})
    context = make_part_context(config_values={"statements": statements})
    return ConditionalDecision(context)


class TestConditionalDecisionConstruction:
    def test_rejects_non_list_statements_config(self, make_part_context):
        with pytest.raises(ConfigError):
            make_conditional_decision(make_part_context, None, "not a list")

    def test_rejects_non_string_statement(self, make_part_context):
        with pytest.raises(ConfigError):
            make_conditional_decision(make_part_context, None, [123])


class TestConditionalDecisionRoute:
    def test_first_true_condition_wins(self, make_part_context, fake_manager):
        decision = make_conditional_decision(
            make_part_context,
            fake_manager,
            statements=[
                "route_a if {x} > 10",
                "route_b if {y} < 5",
                "route_c if {z} == 0",
            ],
            data={"x": 15, "y": 3, "z": 0},
        )

        route = decision.decide_route()

        assert route.route_name == "route_a"
        assert route.can_use_part_name is True

    def test_returns_none_route_when_no_condition_matches_and_no_else(self, make_part_context, fake_manager):
        decision = make_conditional_decision(
            make_part_context,
            fake_manager,
            statements=[
                "route_a if {x} > 10",
                "route_b if {y} < 5",
            ],
            data={"x": 4, "y": 11},
        )

        route = decision.decide_route()

        assert route.route_name is None

    def test_else_statement_used_as_fallback(self, make_part_context, fake_manager):
        decision = make_conditional_decision(
            make_part_context,
            fake_manager,
            statements=[
                "route_a if {x} > 10",
                "route_b if {y} < 5",
                "else route_c",
            ],
            data={"x": 4, "y": 11},
        )

        route = decision.decide_route()

        assert route.route_name == "route_c"
        assert route.can_use_part_name is True

    def test_else_not_last_raises_config_error(self, make_part_context, fake_manager):
        decision = make_conditional_decision(
            make_part_context,
            fake_manager,
            statements=[
                "route_a if {x} > 10",
                "else route_b",
                "route_c if {y} < 5",
            ],
            data={"x": 4, "y": 11},
        )
        with pytest.raises(ConfigError):
            decision.decide_route()

    def test_malformed_statement_raises_config_error(self, make_part_context, fake_manager):
        decision = make_conditional_decision(
            make_part_context,
            fake_manager,
            statements=[
                "route_a if {x} > 10",
                "malformed statement",
                "route_c if {y} < 5",
            ],
            data={"x": 4, "y": 11},
        )
        with pytest.raises(ConfigError):
            decision.decide_route()

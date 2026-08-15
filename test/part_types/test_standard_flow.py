"""
Tests for part_types/flow/standard.py (StandardFlow).
"""
from part_types.flow.standard import StandardFlow


def make_standard_flow(make_part_context, first_part: str | None = None):
    context = make_part_context(first_part=first_part)
    return StandardFlow(context)


class TestStandardFlow:
    def test_begin_flow_returns_configured_first_part(self, make_part_context):
        flow = make_standard_flow(make_part_context, first_part="step1")
        route = flow.begin_flow()
        assert route.first_part == "step1"

    def test_begin_flow_returns_none_when_first_part_not_configured(self, make_part_context):
        flow = make_standard_flow(make_part_context, first_part=None)
        route = flow.begin_flow()
        assert route.first_part is None

    def test_end_flow_does_nothing(self, make_part_context):
        flow = make_standard_flow(make_part_context, first_part=None)
        result = flow.end_flow()
        assert result is None

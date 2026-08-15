"""
Tests for part_types/step/terminal.py.
"""
import pytest

from lib.utils.exceptions import ConfigError
from part_types.step.terminal import TerminalStep


def make_terminal_step(make_part_context, config_values, data=None, fake_manager=None):
    if fake_manager is not None and data:
        fake_manager.data.update(data)
    context = make_part_context(config_values=config_values)
    return TerminalStep(context)


def refuse_to_be_called(*args, **kwargs):
    raise AssertionError("input() should not have been called")


class TestTerminalStepConstruction:
    def test_prompt_only_is_valid(self, make_part_context):
        step = make_terminal_step(make_part_context, {"prompt": "Hello!"})

        assert step.input_type_name is None
        assert step.store_name is None

    def test_valid_enter_and_to_configuration(self, make_part_context):
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        assert step.input_type_name == "int"
        assert step.store_name == "answer"

    def test_unsupported_enter_type_raises_config_error(self, make_part_context):
        with pytest.raises(ConfigError, match="Unsupported input type"):
            make_terminal_step(
                make_part_context,
                {"prompt": "p", "enter": "bool", "to": "answer"},
            )

    def test_to_without_enter_raises_config_error(self, make_part_context):
        with pytest.raises(ConfigError, match="Cannot use 'to' without 'enter'"):
            make_terminal_step(make_part_context, {"prompt": "p", "to": "answer"})

    def test_retrace_without_enter_raises_config_error(self, make_part_context):
        with pytest.raises(ConfigError, match="Cannot use 'retrace' without 'enter'"):
            make_terminal_step(make_part_context, {"prompt": "p", "retrace": "auto"})

    def test_enter_without_to_raises_config_error(self, make_part_context):
        with pytest.raises(ConfigError, match="Missing 'to' configuration"):
            make_terminal_step(make_part_context, {"prompt": "p", "enter": "str"})

    def test_invalid_retrace_value_raises_config_error(self, make_part_context):
        with pytest.raises(ConfigError, match="must be 'auto' or 'manual'"):
            make_terminal_step(
                make_part_context,
                {"prompt": "p", "enter": "str", "to": "answer", "retrace": "sometimes"},
            )


class TestTerminalStepRunWithoutInput:
    def test_prints_prompt_and_never_calls_input(self, make_part_context, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        step = make_terminal_step(make_part_context, {"prompt": "Just a message"})

        step.run_step()

        assert "Just a message" in capsys.readouterr().out

    def test_substitutes_data_names_into_prompt(self, make_part_context, fake_manager, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Hello {name}!"},
            data={"name": "Bob"},
            fake_manager=fake_manager,
        )

        step.run_step()

        assert "Hello Bob!" in capsys.readouterr().out


class TestTerminalStepRunWithInput:
    def test_converts_and_stores_researcher_input(self, make_part_context, fake_manager, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "42")
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 42
        assert fake_manager.saved_trace_part_data == {"researcher_input": "42"}

    def test_retries_until_input_converts_successfully(self, make_part_context, fake_manager, monkeypatch, capsys):
        responses = iter(["not a number", "5"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 5
        assert "Could not convert 'not a number' to int" in capsys.readouterr().out

    def test_records_waiting_for_input_custom_trace_entry(self, make_part_context, fake_manager, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "1")
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        step.run_step()

        assert fake_manager.custom_trace_entries == [
            ("waiting_for_researcher_input", {"prompt": "Enter a number: "})
        ]


class TestTerminalStepRetraceBehavior:
    def test_auto_retrace_reuses_old_input_without_calling_input(self, make_part_context, fake_manager, monkeypatch):
        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        fake_manager.old_trace_part_data = {"researcher_input": "7"}
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 7

    def test_default_retrace_behavior_is_auto(self, make_part_context, fake_manager, monkeypatch):
        # No "retrace" config given at all should behave the same as "auto".
        monkeypatch.setattr("builtins.input", refuse_to_be_called)
        fake_manager.old_trace_part_data = {"researcher_input": "7"}
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer", "retrace": "auto"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 7

    def test_manual_retrace_still_prompts_for_input(self, make_part_context, fake_manager, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "3")
        fake_manager.old_trace_part_data = {"researcher_input": "7"}
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer", "retrace": "manual"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 3

    def test_no_old_trace_data_falls_back_to_prompting(self, make_part_context, fake_manager, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda prompt="": "9")
        fake_manager.old_trace_part_data = None
        step = make_terminal_step(
            make_part_context,
            {"prompt": "Enter a number: ", "enter": "int", "to": "answer"},
        )

        step.run_step()

        assert fake_manager._get_data("answer") == 9

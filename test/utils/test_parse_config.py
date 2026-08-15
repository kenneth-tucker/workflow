"""
Unit tests for lib/utils/parse_config.py.
"""
import pytest

from lib.utils.parse_config import (
    execute_statement_with_data_values,
    extract_data_names,
    extract_part_configs,
    insert_data_values,
)


class TestExtractDataNames:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("no placeholders here", []),
            ("hello {name}", ["name"]),
            ("{first_name} and {last_name}", ["first_name", "last_name"]),
            ("{a} appears {a} twice", ["a", "a"]),
            ("", []),
        ],
    )
    def test_extracts_all_names(self, text, expected):
        assert extract_data_names(text) == expected


class TestInsertDataValues:
    def test_replaces_known_names_with_string_values(self):
        result = insert_data_values(
            "Hello {name}, you are {age}",
            {"name": "Bob", "age": 42},
        )

        assert result == "Hello Bob, you are 42"

    def test_raises_key_error_for_unknown_name(self):
        with pytest.raises(KeyError):
            insert_data_values("Hello {name}", {})


class TestExecuteStatementWithDataValues:
    @pytest.mark.parametrize(
        "statement, data_values, expected",
        [
            ("{a} + {b}", {"a": 1, "b": 2}, 3),
            ("{a} == {b}", {"a": 2, "b": 2}, True),
            ("{a} > {b}", {"a": 1, "b": 2}, False),
            ("[{a}, {b}]", {"a": 1, "b": 2}, [1, 2]),
        ],
    )
    def test_evaluates_expression_with_substituted_values(self, statement, data_values, expected):
        assert execute_statement_with_data_values(statement, data_values) == expected

    def test_wraps_missing_data_name_in_value_error(self):
        with pytest.raises(ValueError, match="Error evaluating statement"):
            execute_statement_with_data_values("{missing}", {})

    def test_blocks_direct_reference_to_builtin_names(self):
        # {"__builtins__": None} in the eval() globals stops the builtins
        # module from being implicitly injected, so a bare reference to a
        # builtin name like __import__ fails to resolve.
        with pytest.raises(ValueError):
            execute_statement_with_data_values("__import__('os').system('echo hi')", {})

    def test_blocks_dunder_attribute_based_sandbox_escape(self):
        # Regression test for the dunder-name rejection: this is the classic
        # eval-sandbox escape route that {"__builtins__": None} alone does NOT
        # stop, since it walks from a tuple literal to object's loaded
        # subclasses without ever referencing a builtin name. It IS blocked
        # now because it contains "__class__"/"__bases__"/"__subclasses__",
        # all of which are rejected for containing "__".
        with pytest.raises(ValueError):
            execute_statement_with_data_values(
                "().__class__.__bases__[0].__subclasses__()", {}
            )


class TestExtractPartConfigs:
    def test_extracts_a_single_flat_part(self):
        part_table = {
            "first_part": "greeting",
            "greeting": {
                "type_name": "step.terminal",
                "next_part": "menu",
                "config_values": {"prompt": "Hi"},
            },
        }

        parts = extract_part_configs("config.toml", part_table, "")

        assert list(parts.keys()) == ["greeting"]
        greeting = parts["greeting"]
        assert greeting.type_name == "step.terminal"
        assert greeting.next_part == {"": "menu"}
        assert greeting.config_values == {"prompt": "Hi"}

    def test_flattens_nested_parts_using_dot_notation(self):
        part_table = {
            "my_flow": {
                "type_name": "flow.standard",
                "first_part": "inner_step",
                "inner_step": {
                    "type_name": "step.terminal",
                },
            },
        }

        parts = extract_part_configs("config.toml", part_table, "")

        assert list(parts.keys()) == ["my_flow", "my_flow.inner_step"]
        assert parts["my_flow.inner_step"].full_name == "my_flow.inner_step"

    def test_string_next_part_is_normalized_to_default_route_dict(self):
        part_table = {"a": {"type_name": "step.terminal", "next_part": "b"}}

        parts = extract_part_configs("config.toml", part_table, "")

        assert parts["a"].next_part == {"": "b"}

    def test_missing_next_part_defaults_to_empty_dict(self):
        part_table = {"a": {"type_name": "step.terminal"}}

        parts = extract_part_configs("config.toml", part_table, "")

        assert parts["a"].next_part == {}

    def test_ignores_top_level_first_part_key(self):
        part_table = {"first_part": "a", "a": {"type_name": "step.terminal"}}

        parts = extract_part_configs("config.toml", part_table, "")

        assert list(parts.keys()) == ["a"]

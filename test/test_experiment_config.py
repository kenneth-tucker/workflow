"""
Tests for lib/experiment_config.py.
"""
import os
import textwrap

import pytest

from lib.experiment_config import ExperimentConfig
from lib.utils.exceptions import ConfigError

MINIMAL_VALID_CONFIG = textwrap.dedent("""\
    [experiment]
    name = "my_experiment"
    out_dir = "results"

    [part]
    first_part = "greeting"

    [part.greeting]
    type_name = "step.terminal"
    [part.greeting.config_values]
    prompt = "Hello!"
    enter = "str"
    to = "name"
    """)


class TestExperimentConfigLoading:
    def test_loads_minimal_valid_config(self, write_toml):
        config_path = write_toml(MINIMAL_VALID_CONFIG)

        config = ExperimentConfig(str(config_path))

        assert config.experiment_name == "my_experiment"
        assert config.initial_part_name == "greeting"
        assert "greeting" in config.part_configs
        assert config.part_configs["greeting"].type_name == "step.terminal"

    def test_relative_out_dir_is_resolved_against_config_file_directory(self, write_toml, tmp_path):
        config_path = write_toml(MINIMAL_VALID_CONFIG)

        config = ExperimentConfig(str(config_path))

        expected = os.path.normpath(os.path.join(str(tmp_path), "results"))
        assert config.out_dir == expected

    def test_absolute_out_dir_is_kept_as_is(self, write_toml, tmp_path):
        abs_out_dir = tmp_path / "abs_results"
        content = MINIMAL_VALID_CONFIG.replace(
            'out_dir = "results"',
            f'out_dir = "{abs_out_dir.as_posix()}"',
        )
        config_path = write_toml(content)

        config = ExperimentConfig(str(config_path))

        assert config.out_dir == os.path.normpath(str(abs_out_dir))


class TestExperimentConfigValidation:
    @pytest.mark.parametrize(
        "broken_config, expected_message",
        [
            (
                textwrap.dedent("""\
                    [part]
                    first_part = "a"
                    """),
                "Missing experiment table",
            ),
            (
                textwrap.dedent("""\
                    [experiment]
                    out_dir = "results"

                    [part]
                    first_part = "a"
                    """),
                "Missing experiment name",
            ),
            (
                textwrap.dedent("""\
                    [experiment]
                    name = "x"

                    [part]
                    first_part = "a"
                    """),
                "Missing experiment output directory",
            ),
            (
                textwrap.dedent("""\
                    [experiment]
                    name = "x"
                    out_dir = "results"
                    """),
                "Missing part table",
            ),
        ],
        ids=["no experiment table", "no name", "no out_dir", "no part table"],
    )
    def test_raises_config_error_for_missing_required_fields(
        self, write_toml, broken_config, expected_message
    ):
        config_path = write_toml(broken_config)

        with pytest.raises(ConfigError, match=expected_message):
            ExperimentConfig(str(config_path))

    def test_raises_config_error_for_unknown_part_type(self, write_toml):
        content = textwrap.dedent("""\
            [experiment]
            name = "my_experiment"
            out_dir = "results"

            [part]
            first_part = "greeting"

            [part.greeting]
            type_name = "not_a_real_type"
            """)
        config_path = write_toml(content)

        with pytest.raises(ConfigError, match="Unknown part type"):
            ExperimentConfig(str(config_path))

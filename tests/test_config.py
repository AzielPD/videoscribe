"""Tests for the settings precedence: defaults < config.json < .env < CLI.

A user who overrides one value in .env expects everything else to keep working.
Getting the order wrong is the kind of bug that shows up as "it ignored my
setting" long after the run has finished.
"""

from __future__ import annotations

import json

import pytest

from videoscribe.config import DEFAULTS, load_config


@pytest.fixture
def paths(tmp_path):
    """An isolated config.json and .env that do not exist yet."""
    return tmp_path / "config.json", tmp_path / ".env"


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


class TestPrecedence:
    def test_defaults_apply_when_nothing_is_configured(self, paths):
        config_path, env_path = paths
        config = load_config(config_path, env_path)
        assert config.model == DEFAULTS["transcription.model"]

    def test_config_json_beats_defaults(self, paths):
        config_path, env_path = paths
        write_json(config_path, {"transcription": {"model": "medium"}})
        assert load_config(config_path, env_path).model == "medium"

    def test_env_beats_config_json(self, paths):
        config_path, env_path = paths
        write_json(config_path, {"transcription": {"model": "medium"}})
        env_path.write_text("VIDEOSCRIBE_MODEL=large-v3\n", encoding="utf-8")
        assert load_config(config_path, env_path).model == "large-v3"

    def test_cli_beats_everything(self, paths):
        config_path, env_path = paths
        write_json(config_path, {"transcription": {"model": "medium"}})
        env_path.write_text("VIDEOSCRIBE_MODEL=large-v3\n", encoding="utf-8")
        config = load_config(config_path, env_path,
                             {"transcription.model": "tiny"})
        assert config.model == "tiny"

    def test_none_overrides_are_ignored(self, paths):
        """argparse hands us None for every flag the user did not type."""
        config_path, env_path = paths
        write_json(config_path, {"transcription": {"model": "medium"}})
        config = load_config(config_path, env_path,
                             {"transcription.model": None})
        assert config.model == "medium"

    def test_one_override_does_not_disturb_the_others(self, paths):
        config_path, env_path = paths
        env_path.write_text("VIDEOSCRIBE_MODEL=tiny\n", encoding="utf-8")
        config = load_config(config_path, env_path)
        assert config.model == "tiny"
        assert config.language == DEFAULTS["transcription.language"]


class TestEnvParsing:
    def test_comments_and_blank_lines_are_skipped(self, paths):
        config_path, env_path = paths
        env_path.write_text(
            "# a comment\n\nVIDEOSCRIBE_MODEL=base\n", encoding="utf-8")
        assert load_config(config_path, env_path).model == "base"

    def test_quoted_values_are_unwrapped(self, paths):
        config_path, env_path = paths
        env_path.write_text('VIDEOSCRIBE_MODEL="base"\n', encoding="utf-8")
        assert load_config(config_path, env_path).model == "base"

    def test_an_empty_value_falls_back_instead_of_blanking(self, paths):
        """`VIDEOSCRIBE_MODEL=` in a shipped .env must not break the run."""
        config_path, env_path = paths
        env_path.write_text("VIDEOSCRIBE_MODEL=\n", encoding="utf-8")
        assert load_config(config_path, env_path).model


class TestBadInput:
    def test_invalid_json_stops_with_an_explanation(self, paths):
        config_path, env_path = paths
        config_path.write_text("{not json", encoding="utf-8")
        with pytest.raises(SystemExit, match="config.json"):
            load_config(config_path, env_path)

    def test_a_byte_order_mark_is_tolerated(self, paths):
        """Notepad on Windows writes one, and it is not the user's fault."""
        config_path, env_path = paths
        config_path.write_text(
            '﻿{"transcription": {"model": "medium"}}', encoding="utf-8")
        assert load_config(config_path, env_path).model == "medium"


class TestNarrationSettings:
    def test_frame_interval_and_window_are_configurable(self, paths):
        config_path, env_path = paths
        write_json(config_path, {"narration": {"frame_interval_seconds": 20,
                                               "window_seconds": 60}})
        config = load_config(config_path, env_path)
        assert config.frame_interval == 20
        assert config.window_seconds == 60

    def test_numbers_arriving_as_text_from_env_are_still_numbers(self, paths):
        config_path, env_path = paths
        env_path.write_text("VIDEOSCRIBE_FRAME_INTERVAL=25\n", encoding="utf-8")
        assert load_config(config_path, env_path).frame_interval == 25

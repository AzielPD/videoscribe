"""Tests for offering the description only when it can actually be produced.

The transcript is the product; the description is the extra. Presenting the
extra as available and then failing -- possibly after half an hour of
transcription -- is worse than not offering it, so the check happens up front.
"""

from __future__ import annotations

import pytest

from videoscribe import vision
from videoscribe.vision import is_configured


@pytest.fixture
def no_backends(monkeypatch):
    """A machine with no API key, no claude command and no Ollama."""
    for variable in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                     "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(vision.ClaudeCliBackend, "is_available",
                        classmethod(lambda cls: False))
    monkeypatch.setattr(vision.OllamaBackend, "is_available",
                        classmethod(lambda cls: False))


@pytest.fixture
def only_gemini(no_backends, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


class TestIsConfigured:
    def test_false_when_nothing_is_set_up(self, no_backends):
        assert is_configured() is False

    def test_true_with_an_api_key(self, only_gemini):
        assert is_configured() is True

    def test_true_with_the_claude_command(self, no_backends, monkeypatch):
        monkeypatch.setattr(vision.ClaudeCliBackend, "is_available",
                            classmethod(lambda cls: True))
        assert is_configured() is True

    def test_true_with_ollama(self, no_backends, monkeypatch):
        monkeypatch.setattr(vision.OllamaBackend, "is_available",
                            classmethod(lambda cls: True))
        assert is_configured() is True

    def test_a_machine_too_small_for_ollama_does_not_count_as_configured(
            self, no_backends, monkeypatch):
        """Ollama answering is not the same as being able to run the model."""
        from dataclasses import dataclass

        @dataclass
        class TinyMachine:
            ram_gb: float = 4.0
            gpu_name: str = ""
            gpu_vram_gb: float = 0.0

            @property
            def has_gpu(self) -> bool:
                return False

        monkeypatch.setattr(vision.OllamaBackend, "is_available",
                            classmethod(lambda cls: True))
        assert is_configured(TinyMachine()) is False


class TestAutoSelectionMatchesTheOffer:
    """What the menu promises and what the run picks must agree."""

    def test_auto_fails_when_is_configured_says_no(self, no_backends):
        assert is_configured() is False
        with pytest.raises(vision.VisionUnavailable):
            vision.select_backend("auto")

    def test_auto_succeeds_when_is_configured_says_yes(self, only_gemini):
        assert is_configured() is True
        assert vision.select_backend("auto").name == "gemini"

    def test_the_refusal_explains_how_to_fix_it(self, no_backends):
        with pytest.raises(vision.VisionUnavailable) as caught:
            vision.select_backend("auto")
        message = str(caught.value)
        assert "GEMINI_API_KEY" in message or "claude" in message
        assert "transcript" in message.lower()

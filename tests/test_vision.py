"""Tests for back-end selection and for the limits of the local model.

The Ollama sizing rules here were written against measurements, not guesses:
a request carrying twelve frames of a 1280x720 video reached about 10800
tokens and was refused outright by a server defaulting to 4096.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from videoscribe.vision import (
    BACKENDS,
    DEFAULT_MODELS,
    OllamaBackend,
    VisionUnavailable,
    WindowPlan,
    available_backends,
    select_backend,
)


@dataclass
class FakeMachine:
    """Enough of a MachineProfile for the decisions under test."""

    ram_gb: float = 16.0
    gpu_name: str = ""
    gpu_vram_gb: float = 0.0

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpu_name) and self.gpu_vram_gb > 0


CPU_MACHINE = FakeMachine()
GPU_MACHINE = FakeMachine(gpu_name="RTX 4070", gpu_vram_gb=12.0)
SMALL_MACHINE = FakeMachine(ram_gb=6.0)


class TestContextSize:
    """The 4096-token default is what made every window fail with HTTP 400."""

    def test_twelve_frames_needs_more_than_the_ollama_default(self):
        size = OllamaBackend.context_size(12, "prompt", 1600)
        assert size > 4096

    def test_a_single_frame_still_gets_a_workable_floor(self):
        assert OllamaBackend.context_size(1, "x", 100) == OllamaBackend.MIN_CONTEXT

    def test_grows_with_the_number_of_frames(self):
        one = OllamaBackend.context_size(1, "prompt", 1600)
        many = OllamaBackend.context_size(8, "prompt", 1600)
        assert many > one

    def test_leaves_room_for_the_answer(self):
        """The reply shares the window with the question."""
        size = OllamaBackend.context_size(4, "", 1600)
        assert size >= 4 * OllamaBackend.TOKENS_PER_FRAME + 1600

    def test_is_capped_so_a_cpu_is_not_asked_for_the_impossible(self):
        assert OllamaBackend.context_size(500, "p", 1600) == OllamaBackend.MAX_CONTEXT

    def test_counts_a_long_prompt_too(self):
        short = OllamaBackend.context_size(2, "x", 100)
        long = OllamaBackend.context_size(2, "x" * 30000, 100)
        assert long > short


class TestPlanWindows:
    """Windows are shortened to fit; the frame interval is never touched."""

    def test_default_window_is_shortened_on_a_cpu(self):
        plan = OllamaBackend.plan_windows(10, 120, CPU_MACHINE)
        assert plan.changed
        assert plan.window_seconds < 120
        assert plan.frame_interval == 10, "coverage must not be reduced"

    def test_resulting_window_holds_at_most_the_frame_limit(self):
        plan = OllamaBackend.plan_windows(10, 120, CPU_MACHINE)
        frames = plan.window_seconds // plan.frame_interval
        assert frames <= OllamaBackend.MAX_FRAMES_PER_REQUEST_CPU

    def test_a_window_that_already_fits_is_left_alone(self):
        plan = OllamaBackend.plan_windows(20, 60, CPU_MACHINE)
        assert not plan.changed
        assert (plan.frame_interval, plan.window_seconds) == (20, 60)

    def test_a_graphics_card_keeps_the_ordinary_default(self):
        plan = OllamaBackend.plan_windows(10, 120, GPU_MACHINE)
        assert not plan.changed
        assert plan.window_seconds == 120

    def test_the_change_is_explained_rather_than_silent(self):
        plan = OllamaBackend.plan_windows(10, 120, CPU_MACHINE)
        assert plan.note.strip()
        assert "120" in plan.note

    def test_hosted_back_ends_change_nothing(self):
        for name, backend in BACKENDS.items():
            if name in {"ollama", "none"}:
                continue
            plan = backend.plan_windows(10, 120, CPU_MACHINE)
            assert not plan.changed, f"{name} should accept the requested window"
            assert plan.window_seconds == 120

    def test_never_returns_a_window_shorter_than_one_frame(self):
        plan = OllamaBackend.plan_windows(30, 30, CPU_MACHINE)
        assert plan.window_seconds >= plan.frame_interval


class TestVerdict:
    def test_a_graphics_card_is_recommended(self):
        level, note = OllamaBackend.verdict(GPU_MACHINE)
        assert level == "recommended"
        assert "RTX 4070" in note

    def test_a_cpu_only_machine_is_offered_but_marked_slow(self):
        level, note = OllamaBackend.verdict(CPU_MACHINE)
        assert level == "slow"
        assert note.strip(), "the cost has to be stated, not implied"

    def test_too_little_memory_is_unusable(self):
        level, _ = OllamaBackend.verdict(SMALL_MACHINE)
        assert level == "unusable"

    def test_quotes_the_model_the_pipeline_would_actually_run(self):
        """Not the largest that fits: the user would plan around a wrong number."""
        _, note = OllamaBackend.verdict(CPU_MACHINE)
        assert OllamaBackend.DEFAULT_MODEL in note
        assert DEFAULT_MODELS["ollama"][0] == OllamaBackend.DEFAULT_MODEL

    def test_privacy_option_is_never_hidden_on_a_capable_machine(self):
        """Slow is a caveat, not a refusal -- it is the only private back end."""
        level, _ = OllamaBackend.verdict(CPU_MACHINE)
        assert level != "unusable"


class TestSecondsPerFrame:
    def test_a_graphics_card_is_quoted_as_faster(self):
        cpu = OllamaBackend.seconds_per_frame("qwen2.5vl:3b", CPU_MACHINE)
        gpu = OllamaBackend.seconds_per_frame("qwen2.5vl:3b", GPU_MACHINE)
        assert gpu < cpu

    def test_matches_the_measurement_it_was_taken_from(self):
        """9 frames took about 12 minutes on 16 cores with no card."""
        per_frame = OllamaBackend.seconds_per_frame("qwen2.5vl:3b", CPU_MACHINE)
        assert 60 <= per_frame <= 100

    def test_an_unknown_model_falls_back_instead_of_raising(self):
        assert OllamaBackend.seconds_per_frame("no-such-model", CPU_MACHINE) > 0


class TestSelectBackend:
    def test_an_unknown_name_lists_the_real_ones(self):
        """A typo must fail loudly, naming the valid choices."""
        with pytest.raises(VisionUnavailable) as caught:
            select_backend("gpt5-vision")
        assert "ollama" in str(caught.value)

    def test_none_is_always_selectable(self):
        assert select_backend("none").name == "none"

    def test_disabled_back_end_refuses_to_generate(self):
        with pytest.raises(VisionUnavailable):
            select_backend("none").generate("p", [], "m")

    def test_every_back_end_has_default_models(self):
        for name in BACKENDS:
            if name == "none":
                continue
            assert name in DEFAULT_MODELS, f"{name} has no default model"


class TestAvailableBackends:
    def test_reports_a_row_for_every_back_end(self):
        names = {row[0] for row in available_backends()}
        assert names == set(BACKENDS) - {"none"}

    def test_a_machine_too_small_marks_the_local_model_unavailable(self):
        rows = {name: (ready, note) for name, ready, note in
                available_backends(SMALL_MACHINE)}
        ready, _ = rows["ollama"]
        assert ready is False

    def test_works_without_a_machine_profile(self):
        assert available_backends() is not None


class TestWindowPlan:
    def test_a_plan_without_a_note_counts_as_unchanged(self):
        assert not WindowPlan(10, 120).changed

    def test_a_plan_with_a_note_counts_as_changed(self):
        assert WindowPlan(10, 40, "shortened").changed

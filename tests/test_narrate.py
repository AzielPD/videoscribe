"""Tests for windowing and for the prompt sent to the image model.

Rule 2 lives here as much as in the pipeline: a window built with an offset has
to carry times on the *source video's* clock, because that is the clock the
reader will type into a player.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from videoscribe.narrate import Window, build_windows, strip_preamble


def frames(count: int) -> list[Path]:
    return [Path(f"frame_{n:05d}.jpg") for n in range(1, count + 1)]


def speech(start: float, end: float, text: str = "hola", speaker: int = 1) -> dict:
    return {"start": start, "end": end, "text": text, "speaker": speaker}


class TestBuildWindows:
    def test_covers_the_whole_span(self):
        windows = build_windows(frames(12), [], 120, 10, 60)
        assert windows[0].start == 0
        assert windows[-1].end == 120

    def test_every_frame_lands_in_exactly_one_window(self):
        windows = build_windows(frames(12), [], 120, 10, 60)
        placed = [path for window in windows for _, path in window.frames]
        assert sorted(placed) == sorted(frames(12))

    def test_frame_times_follow_the_interval(self):
        windows = build_windows(frames(3), [], 30, 10, 60)
        assert [second for second, _ in windows[0].frames] == [0, 10, 20]

    def test_a_short_tail_still_gets_a_window(self):
        windows = build_windows(frames(7), [], 65, 10, 60)
        assert len(windows) == 2
        assert windows[1].end == 65

    def test_dialogue_overlapping_a_boundary_appears_in_both(self):
        """Cutting a sentence in half would hide it from one of the two."""
        windows = build_windows(frames(2), [speech(55, 65)], 120, 10, 60)
        assert windows[0].dialogue and windows[1].dialogue

    def test_empty_input_still_produces_one_window(self):
        assert len(build_windows([], [], 0, 10, 60)) == 1


class TestOffsetOntoSourceClock:
    """Rule 2: --start shifts the audio, never the timecodes we print."""

    def test_frames_are_timed_from_the_offset(self):
        windows = build_windows(frames(3), [], 30, 10, 60, offset=720)
        assert [second for second, _ in windows[0].frames] == [720, 730, 740]

    def test_window_bounds_are_on_the_source_clock(self):
        windows = build_windows(frames(6), [], 60, 10, 60, offset=720)
        assert windows[0].start == 720
        assert windows[0].end == 780

    def test_allowed_timecodes_are_source_video_times(self):
        windows = build_windows(frames(2), [speech(725, 730)], 20, 10, 60, offset=720)
        allowed = windows[0].allowed_timecodes()
        assert "00:12:00" in allowed       # the first frame, at 720 s
        assert "00:12:05" in allowed       # the speech, at 725 s
        assert "00:00:00" not in allowed   # the extracted-audio clock


class TestAllowedTimecodes:
    def test_includes_frames_and_speech(self):
        window = Window(0, 0, 60,
                        frames=[(0.0, Path("a.jpg")), (10.0, Path("b.jpg"))],
                        dialogue=[speech(5, 8)])
        assert window.allowed_timecodes() == {"00:00:00", "00:00:10", "00:00:05"}

    def test_truncates_like_every_other_timecode(self):
        window = Window(0, 0, 60, frames=[(40.7, Path("a.jpg"))])
        assert window.allowed_timecodes() == {"00:00:40"}

    def test_an_empty_window_allows_nothing(self):
        assert Window(0, 0, 60).allowed_timecodes() == set()


class TestIsEmpty:
    def test_no_frames_and_no_speech_is_empty(self):
        assert Window(0, 0, 60).is_empty

    def test_speech_alone_is_not_empty(self):
        assert not Window(0, 0, 60, dialogue=[speech(1, 2)]).is_empty

    def test_frames_alone_are_not_empty(self):
        assert not Window(0, 0, 60, frames=[(0.0, Path("a.jpg"))]).is_empty


class TestBuildPrompt:
    def test_asks_for_the_requested_language(self):
        window = Window(0, 0, 60, frames=[(0.0, Path("a.jpg"))])
        assert "Spanish" in window.build_prompt("Persona", "Spanish")

    def test_labels_every_frame_with_its_time(self):
        window = Window(0, 720, 780, frames=[(720.0, Path("a.jpg"))])
        assert "[00:12:00]" in window.build_prompt("Persona", "Spanish")

    def test_says_so_when_there_are_no_frames(self):
        prompt = Window(0, 0, 60, dialogue=[speech(1, 2)]).build_prompt("P", "Spanish")
        assert "no frames" in prompt

    def test_says_so_when_nobody_speaks(self):
        prompt = Window(0, 0, 60, frames=[(0.0, Path("a.jpg"))]).build_prompt("P", "Spanish")
        assert "no speech" in prompt

    def test_carries_the_speaker_label(self):
        window = Window(0, 0, 60, dialogue=[speech(1, 2, "buenos dias", speaker=2)])
        assert "Persona2" in window.build_prompt("Persona", "Spanish")


class TestStripPreamble:
    def test_drops_a_leading_courtesy_line(self):
        assert strip_preamble("Here is the paragraph:\n\nShe speaks.") == "She speaks."

    def test_keeps_a_paragraph_that_starts_straight_away(self):
        text = "She hands over the receipt and points at the date."
        assert strip_preamble(text) == text

    def test_a_single_line_is_never_emptied(self):
        assert strip_preamble("She speaks.") == "She speaks."

    def test_drops_the_model_complaining_about_its_own_input(self):
        """This reached a finished account: English chatter atop a Spanish document.

        The synthesis step sends no images, and the Claude CLI back end used to
        append "Read these image files:" with an empty list anyway, so the model
        opened by saying no images had arrived.
        """
        leaked = (
            "I don't see any image files attached to this message — only the "
            "text section describing the 00:12:00 segment.\n"
            "\n"
            "That said, the section above is complete. Here is the account:\n"
            "\n"
            "---\n"
            "\n"
            "En este segmento se ve a una mujer de chaqueta rosa."
        )
        assert strip_preamble(leaked) == "En este segmento se ve a una mujer de chaqueta rosa."

    @pytest.mark.parametrize("opener", [
        "I cannot see the frames.",
        "Unfortunately the images did not load.",
        "It seems the frames are missing.",
        "Sorry, I could not read them.",
        "Note that the audio is unclear.",
    ])
    def test_drops_other_shapes_of_self_commentary(self, opener):
        assert strip_preamble(f"{opener}\n\nShe speaks.") == "She speaks."

    def test_drops_a_horizontal_rule_left_behind(self):
        assert strip_preamble("---\n\nShe speaks.") == "She speaks."

    def test_does_not_eat_a_sentence_that_merely_starts_with_one_of_the_words(self):
        """Only the last line is protected, so this must not be treated as chatter."""
        text = "Sure enough, the door opens.\nShe walks through it."
        assert strip_preamble(text) == "She walks through it."
        assert strip_preamble("Sure enough, the door opens.") == "Sure enough, the door opens."

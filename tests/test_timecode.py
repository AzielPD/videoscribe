"""Tests for the timecode rules, which are the ones that must never break.

A lawyer quotes a sentence and points at the second it was said. If a timecode
is off by one second it may name the next sentence, and if it was invented it
names nothing at all. Both failures are silent in the output, so they are
pinned down here instead.
"""

from __future__ import annotations

import pytest

from videoscribe.timecode import (
    format_srt_timecode,
    format_timecode,
    parse_timecode,
    strip_invented_timecodes,
)


class TestFormatTimecode:
    """Rule 1: truncate, never round."""

    @pytest.mark.parametrize("seconds, expected", [
        (0, "00:00:00"),
        (40.7, "00:00:40"),      # the case that shipped broken once
        (40.999, "00:00:40"),
        (59.9, "00:00:59"),
        (60, "00:01:00"),
        (3599.9, "00:59:59"),
        (3600, "01:00:00"),
    ])
    def test_truncates_downwards(self, seconds, expected):
        assert format_timecode(seconds) == expected

    def test_fifty_minutes_is_not_an_hour(self):
        """The original PowerShell bug: [int](3030/3600) rounded to 1 hour.

        3030 seconds is 50 minutes 30 seconds. Any implementation that rounds
        the hour component reports 01:00:30 and shifts every dialogue line.
        """
        assert format_timecode(3030) == "00:50:30"

    def test_negative_is_clamped_not_wrapped(self):
        assert format_timecode(-5) == "00:00:00"

    def test_never_rounds_up_across_any_boundary(self):
        """Property: the labelled second is never ahead of the real one."""
        for tenth in range(0, 7200):
            seconds = tenth / 10.0
            hours, minutes, secs = (int(p) for p in format_timecode(seconds).split(":"))
            assert hours * 3600 + minutes * 60 + secs <= seconds


class TestFormatSrtTimecode:
    def test_keeps_milliseconds(self):
        assert format_srt_timecode(40.7) == "00:00:40,700"

    def test_rounding_to_a_full_second_carries_over(self):
        """.9996 rounds to 1000 ms, which is not a legal SubRip value."""
        assert format_srt_timecode(40.9996) == "00:00:41,000"

    def test_zero(self):
        assert format_srt_timecode(0) == "00:00:00,000"


class TestParseTimecode:
    @pytest.mark.parametrize("text, expected", [
        ("00:12:00", 720.0),
        ("12:00", 720.0),
        ("90", 90.0),
        ("01:00:00", 3600.0),
        ("00:00:40.5", 40.5),
        ("", 0.0),
    ])
    def test_accepted_forms(self, text, expected):
        assert parse_timecode(text) == expected

    def test_round_trip_with_format(self):
        assert format_timecode(parse_timecode("00:50:30")) == "00:50:30"

    def test_rejects_nonsense_with_a_usable_message(self):
        with pytest.raises(ValueError, match="HH:MM:SS"):
            parse_timecode("half past two")


class TestStripInventedTimecodes:
    """Rule 3: a wrong timecode is worse than no timecode."""

    def test_keeps_allowed_stamps(self):
        text = "[00:12:00] She hands over the receipt."
        cleaned, removed = strip_invented_timecodes(text, {"00:12:00"})
        assert cleaned == text
        assert removed == 0

    def test_removes_invented_stamps(self):
        text = "[00:12:00] She speaks. [00:12:07] He answers."
        cleaned, removed = strip_invented_timecodes(text, {"00:12:00"})
        assert "00:12:07" not in cleaned
        assert "00:12:00" in cleaned
        assert removed == 1

    def test_removes_the_bracket_and_its_leading_space(self):
        cleaned, _ = strip_invented_timecodes("She speaks [00:99:99] loudly.", set())
        assert cleaned == "She speaks loudly."

    def test_counts_distinct_stamps_not_occurrences(self):
        text = "[00:01:01] a [00:01:01] b [00:02:02] c"
        _, removed = strip_invented_timecodes(text, set())
        assert removed == 2

    def test_empty_allowed_set_strips_everything(self):
        cleaned, removed = strip_invented_timecodes("[00:00:01] x [00:00:02] y", set())
        assert "[" not in cleaned
        assert removed == 2

    def test_leaves_text_without_timecodes_alone(self):
        """The local 3B model writes no timecodes at all; that must not crash."""
        text = "Se observa a una persona con uniforme."
        cleaned, removed = strip_invented_timecodes(text, {"00:12:00"})
        assert cleaned == text
        assert removed == 0

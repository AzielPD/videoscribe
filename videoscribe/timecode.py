"""Turning seconds into timecodes, and back.

Every timecode written by this toolkit points at a real moment in the source
video. A reader must be able to type it into a player and land on the sentence
being quoted, so the conversion has to *truncate* rather than round: at second
40.7 the correct label is 00:00:40, not 00:00:41, because 00:00:41 might
already be the next sentence.
"""

from __future__ import annotations

import math
import re

TIMECODE_PATTERN = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]")


def format_timecode(seconds: float) -> str:
    """Seconds to ``HH:MM:SS``, always truncating downwards."""
    total = int(math.floor(max(0.0, seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_srt_timecode(seconds: float) -> str:
    """Seconds to the ``HH:MM:SS,mmm`` form SubRip subtitles require."""
    clamped = max(0.0, seconds)
    milliseconds = int(round((clamped - math.floor(clamped)) * 1000))
    if milliseconds == 1000:  # rounding can push .9996 over the edge
        clamped, milliseconds = math.floor(clamped) + 1, 0
    total = int(math.floor(clamped))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def parse_timecode(text: str) -> float:
    """``HH:MM:SS``, ``MM:SS`` or a bare number of seconds to a float."""
    if not text:
        return 0.0
    parts = text.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError as exc:
        raise ValueError(f"'{text}' is not a valid time. Use HH:MM:SS, MM:SS or seconds.") from exc


def format_duration(seconds: float) -> str:
    """Human phrasing for an estimate, e.g. ``about 25 minutes``.

    Translated, because this appears in the model chooser where the whole point
    is that a non-technical reader can compare the options at a glance.
    """
    from .i18n import t  # imported here to keep this module dependency-free

    if seconds < 90:
        return t("duration.under_two_minutes")
    minutes = seconds / 60.0
    if minutes < 60:
        return t("duration.minutes", value=int(round(minutes)))
    hours = minutes / 60.0
    if hours < 2:
        return t("duration.hours", value=f"{hours:.1f}")
    return t("duration.hours", value=int(round(hours)))


def strip_invented_timecodes(text: str, allowed: set[str]) -> tuple[str, int]:
    """Delete ``[HH:MM:SS]`` markers that do not appear in ``allowed``.

    Language models estimate timecodes when asked to cite them, and an invented
    one sends a reader to the wrong minute of a long recording -- worse than no
    citation at all. Every marker is therefore checked against the exact set of
    frame times and transcript times that were supplied for that window, and
    anything else is removed.

    Returns the cleaned text and how many distinct markers were dropped.
    """
    invented = {
        match.group(1)
        for match in TIMECODE_PATTERN.finditer(text)
        if match.group(1) not in allowed
    }
    cleaned = text
    for stamp in invented:
        cleaned = re.sub(r"\s*\[" + re.escape(stamp) + r"\]", "", cleaned)
    return cleaned.strip(), len(invented)

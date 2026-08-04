"""Writing the result files.

Output files are numbered so that someone opening the folder for the first time
can tell what to read in what order:

===================================  ===========================================
File                                 Contents
===================================  ===========================================
``01_audio.mp3``                     the sound track on its own
``02_transcript.txt``                who said what, with timecodes
``03_subtitles.srt``                 the same, as subtitles for a video player
``04_narrative.txt``                 the written account of the video
``05_narrative_by_section.md``       the same, split into short sections
``data/transcript.json``             machine-readable, used to re-run steps
``data/manifest.json``               what was produced, with what settings
===================================  ===========================================

Text files are written as UTF-8 with a byte-order mark, because Windows Notepad
and Excel misread accented characters without one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .timecode import format_srt_timecode, format_timecode
from .transcribe import Transcript, merge_consecutive

ENCODING_WITH_BOM = "utf-8-sig"

DISCLAIMER = (
    "This file was produced automatically by speech recognition and, where a\n"
    "          visual description is included, by an image model. Both make mistakes.\n"
    "          Check every figure, name and job title against the recording before\n"
    "          relying on it. Each timecode points at the moment in the video where\n"
    "          the statement can be verified."
)


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=ENCODING_WITH_BOM)
    return path


def _header(title: str, rows: list[tuple[str, str]]) -> str:
    """A fixed-width header block shared by the text outputs."""
    line = "=" * 70
    width = max(len(label) for label, _ in rows)
    body = "\n".join(f"{label.ljust(width)} : {value}" for label, value in rows)
    return f"{line}\n{title}\n{line}\n{body}\n{line}\n\n"


def write_transcript_txt(
    path: Path,
    transcript: Transcript,
    source_name: str,
    speaker_label: str,
    speaker_count: int,
    span: tuple[float, float] | None = None,
) -> Path:
    """The readable transcript, one block per speaker turn.

    ``span`` records which stretch of the source video this covers. Timecodes
    below always refer to the source video, never to the extracted stretch, so
    they can be typed straight into a player.
    """
    rows = [("Source file", source_name)]
    if span and span[0] > 0:
        rows.append(("Covers", f"{format_timecode(span[0])} to {format_timecode(span[1])} "
                               "of the source video"))
    rows.append(("Duration", format_timecode(transcript.duration)))

    header = _header(
        "TRANSCRIPT WITH SPEAKER IDENTIFICATION",
        rows + [
            ("Language", f"{transcript.language} (confidence {transcript.language_probability:.2f})"),
            ("Model", transcript.model),
            ("Speakers found", str(speaker_count)),
            ("Generated", datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")),
            ("Please note", DISCLAIMER),
        ],
    )

    blocks = []
    for turn in merge_consecutive(transcript.segments):
        speaker = f"{speaker_label}{turn.get('speaker', 1)}"
        blocks.append(f"[{format_timecode(turn['start'])}] {speaker}:\n    {turn['text']}\n")

    return _write_text(path, header + "\n".join(blocks))


def write_subtitles_srt(path: Path, transcript: Transcript, speaker_label: str) -> Path:
    """SubRip subtitles, each line prefixed with the speaker."""
    entries = []
    for number, segment in enumerate(transcript.segments, start=1):
        speaker = f"{speaker_label}{segment.get('speaker', 1)}"
        entries.append(
            f"{number}\n"
            f"{format_srt_timecode(segment['start'])} --> {format_srt_timecode(segment['end'])}\n"
            f"{speaker}: {segment['text']}\n"
        )
    return _write_text(path, "\n".join(entries))


def write_transcript_json(path: Path, transcript: Transcript, extra: dict | None = None) -> Path:
    """Machine-readable transcript. Re-running later steps depends on this file."""
    payload = {
        "duration": transcript.duration,
        "language": transcript.language,
        "language_probability": transcript.language_probability,
        "model": transcript.model,
        "segments": transcript.segments,
    }
    payload.update(extra or {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def write_narrative_txt(
    path: Path,
    account: str,
    source_name: str,
    frame_count: int,
    frame_interval: int,
    segment_count: int,
    backend_name: str,
    span: tuple[float, float],
) -> Path:
    """The continuous written account of the video."""
    header = _header(
        "WRITTEN ACCOUNT OF THE VIDEO (sound and image)",
        [
            ("Source file", source_name),
            ("Covers", f"{format_timecode(span[0])} to {format_timecode(span[1])}"),
            ("Based on", f"{frame_count} frames (one every {frame_interval}s) "
                         f"and {segment_count} speech segments"),
            ("Described by", backend_name),
            ("Generated", datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")),
            ("Please note", DISCLAIMER),
        ],
    )
    return _write_text(path, header + account.strip() + "\n")


def write_narrative_markdown(path: Path, source_name: str, sections: list[tuple[float, str]]) -> Path:
    """The account split into sections, one per window, each with its timecode."""
    lines = [
        f"# Written account by section - {source_name}",
        "",
        "Each section covers one stretch of the recording. The heading is the time "
        "at which the stretch begins.",
        "",
    ]
    for start, paragraph in sections:
        lines += [f"## {format_timecode(start)}", "", paragraph.strip(), ""]
    return _write_text(path, "\n".join(lines))


def write_manifest(path: Path, data: dict) -> Path:
    """Record what was produced and with which settings, for reproducibility."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_readme(path: Path, files: list[tuple[str, str]]) -> Path:
    """A plain-language guide dropped into each result folder."""
    lines = [
        "WHAT IS IN THIS FOLDER",
        "=" * 70,
        "",
    ]
    width = max((len(name) for name, _ in files), default=20)
    for name, description in files:
        lines.append(f"  {name.ljust(width)}  {description}")
    lines += [
        "",
        "-" * 70,
        "IMPORTANT",
        "",
        "These files were produced automatically. Speech recognition mishears",
        "words, especially names and numbers, and the visual description can",
        "misread small print. Before relying on any statement, open the video at",
        "the timecode shown in square brackets and confirm it yourself.",
        "",
        "The 'work' folder holds temporary files and can be deleted.",
        "The 'data' folder is needed if you want to re-run a step later.",
        "",
    ]
    return _write_text(path, "\n".join(lines))

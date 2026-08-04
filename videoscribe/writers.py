"""Writing the result files.

Output files are numbered so that someone opening the folder for the first time
can tell what to read in what order:

===================================  ===========================================
File                                 Contents
===================================  ===========================================
``00_READ_ME_FIRST.txt``             a plain-language guide to the folder
``01_audio.mp3``                     the sound track on its own
``02_transcript.txt``                who said what, with timecodes
``03_subtitles.srt``                 the same, as subtitles for a video player
``04_narrative.txt``                 the written account of the video
``05_narrative_by_section.md``       the same, split into short sections
``data/transcript.json``             machine-readable, used to re-run steps
``data/manifest.json``               what was produced, with what settings
===================================  ===========================================

Everything a reader sees here is translated. These documents get handed to
other people -- a colleague, a client, a court -- so a Spanish run must not
produce Spanish speech under an English heading.

Text files are written as UTF-8 with a byte-order mark, because Windows Notepad
and Excel misread accented characters without one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .i18n import t
from .timecode import format_srt_timecode, format_timecode
from .transcribe import Transcript, merge_consecutive

ENCODING_WITH_BOM = "utf-8-sig"
RULE = "=" * 70


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=ENCODING_WITH_BOM)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _wrap(text: str, width: int, indent: str) -> str:
    """Wrap a long value so the header block stays inside a terminal width."""
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return f"\n{indent}".join(lines)


def _header(title: str, rows: list[tuple[str, str]]) -> str:
    """A fixed-width header block shared by the text outputs."""
    width = max(len(label) for label, _ in rows)
    indent = " " * (width + 3)
    body = "\n".join(
        f"{label.ljust(width)} : {_wrap(value, 68 - width, indent)}"
        for label, value in rows
    )
    return f"{RULE}\n{title}\n{RULE}\n{body}\n{RULE}\n\n"


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
    rows = [(t("file.source"), source_name)]
    if span and span[0] > 0:
        rows.append((
            t("file.covers"),
            t("file.covers_value",
              start=format_timecode(span[0]), end=format_timecode(span[1])),
        ))
    rows += [
        (t("file.duration"), format_timecode(transcript.duration)),
        (t("file.language"), t("file.language_value", code=transcript.language,
                               confidence=f"{transcript.language_probability:.2f}")),
        (t("file.model"), transcript.model),
        (t("file.speakers_found"), str(speaker_count)),
        (t("file.generated"), _now()),
        (t("file.please_note"), t("file.disclaimer")),
    ]

    blocks = []
    for turn in merge_consecutive(transcript.segments):
        speaker = f"{speaker_label}{turn.get('speaker', 1)}"
        blocks.append(f"[{format_timecode(turn['start'])}] {speaker}:\n    {turn['text']}\n")

    return _write_text(path, _header(t("file.transcript_title"), rows) + "\n".join(blocks))


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
    rows = [
        (t("file.source"), source_name),
        (t("file.covers"), t("file.covers_value",
                             start=format_timecode(span[0]), end=format_timecode(span[1]))),
        (t("file.based_on"), t("file.based_on_value", frames=frame_count,
                               interval=frame_interval, segments=segment_count)),
        (t("file.described_by"), backend_name),
        (t("file.generated"), _now()),
        (t("file.please_note"), t("file.disclaimer")),
    ]
    return _write_text(path, _header(t("file.narrative_title"), rows) + account.strip() + "\n")


def write_narrative_markdown(path: Path, source_name: str, sections: list[tuple[float, str]]) -> Path:
    """The account split into sections, one per window, each with its timecode."""
    lines = [
        f"# {t('file.sections_title', name=source_name)}",
        "",
        t("file.sections_intro"),
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


def write_readme(path: Path, include_narrative: bool) -> Path:
    """A plain-language guide dropped into each result folder."""
    files = [
        ("01_audio.mp3", t("readme.file_audio")),
        ("02_transcript.txt", t("readme.file_transcript")),
        ("03_subtitles.srt", t("readme.file_subtitles")),
    ]
    if include_narrative:
        files += [
            ("04_narrative.txt", t("readme.file_narrative")),
            ("05_narrative_by_section.md", t("readme.file_sections")),
        ]
    files += [
        ("data/", t("readme.file_data")),
        ("work/", t("readme.file_work")),
    ]

    width = max(len(name) for name, _ in files)
    lines = [t("readme.title"), RULE, ""]
    lines += [f"  {name.ljust(width)}  {description}" for name, description in files]
    lines += [
        "",
        "-" * 70,
        t("readme.important"),
        "",
        _wrap(t("readme.warning"), 68, ""),
        "",
        t("readme.work_folder"),
        t("readme.data_folder"),
        "",
    ]
    return _write_text(path, "\n".join(lines))

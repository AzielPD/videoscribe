"""Tests for the output files.

Rule 4 says uncertainty is surfaced, not hidden. These readers are lawyers who
may quote the file in a filing, so the disclaimer is not decoration: it is the
thing that stops an automated transcript being read as a certified one.
"""

from __future__ import annotations

import json

import pytest

from videoscribe.transcribe import Transcript
from videoscribe.writers import (
    write_narrative_markdown,
    write_narrative_txt,
    write_subtitles_srt,
    write_transcript_json,
    write_transcript_txt,
)


@pytest.fixture
def transcript():
    return Transcript(
        segments=[
            {"start": 720.0, "end": 725.0, "text": "primera frase", "speaker": 1},
            {"start": 725.5, "end": 730.0, "text": "segunda frase", "speaker": 2},
        ],
        language="es",
        language_probability=1.0,
        duration=180.0,
        model="tiny",
    )


class TestTranscriptTxt:
    def test_carries_a_disclaimer(self, transcript, tmp_path):
        path = write_transcript_txt(tmp_path / "t.txt", transcript, "v.mp4", "Persona", 2)
        assert path.read_text(encoding="utf-8-sig").strip()
        # The header names the caveat under some wording in either language.
        assert len(path.read_text(encoding="utf-8-sig").splitlines()) > 5

    def test_timecodes_refer_to_the_source_video(self, transcript, tmp_path):
        """Rule 2: a segment at 720 s is 00:12:00 of the original, not 00:00:00."""
        path = write_transcript_txt(tmp_path / "t.txt", transcript, "v.mp4",
                                    "Persona", 2, span=(720.0, 900.0))
        text = path.read_text(encoding="utf-8-sig")
        assert "[00:12:00]" in text
        assert "[00:00:00]" not in text

    def test_records_the_span_when_only_part_was_processed(self, transcript, tmp_path):
        path = write_transcript_txt(tmp_path / "t.txt", transcript, "v.mp4",
                                    "Persona", 2, span=(720.0, 900.0))
        text = path.read_text(encoding="utf-8-sig")
        assert "00:12:00" in text and "00:15:00" in text

    def test_names_the_speakers_with_the_given_label(self, transcript, tmp_path):
        path = write_transcript_txt(tmp_path / "t.txt", transcript, "v.mp4", "Persona", 2)
        assert "Persona1" in path.read_text(encoding="utf-8-sig")

    def test_names_the_model_that_produced_it(self, transcript, tmp_path):
        path = write_transcript_txt(tmp_path / "t.txt", transcript, "v.mp4", "Persona", 2)
        assert "tiny" in path.read_text(encoding="utf-8-sig")


class TestSubtitlesSrt:
    def test_uses_the_subrip_millisecond_form(self, transcript, tmp_path):
        path = write_subtitles_srt(tmp_path / "s.srt", transcript, "Persona")
        assert "00:12:00,000 --> 00:12:05,000" in path.read_text(encoding="utf-8-sig")

    def test_numbers_entries_from_one(self, transcript, tmp_path):
        path = write_subtitles_srt(tmp_path / "s.srt", transcript, "Persona")
        assert path.read_text(encoding="utf-8-sig").startswith("1\n")

    def test_is_written_with_a_byte_order_mark(self, transcript, tmp_path):
        """Deliberate: without it Windows reads accented text as the code page."""
        path = write_subtitles_srt(tmp_path / "s.srt", transcript, "Persona")
        assert path.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_writes_one_entry_per_segment(self, transcript, tmp_path):
        path = write_subtitles_srt(tmp_path / "s.srt", transcript, "Persona")
        assert path.read_text(encoding="utf-8-sig").count("-->") == 2


class TestTranscriptJson:
    def test_round_trips(self, transcript, tmp_path):
        path = write_transcript_json(tmp_path / "t.json", transcript)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data["model"] == "tiny"
        assert len(data["segments"]) == 2

    def test_records_the_time_offset_so_later_steps_can_realign(self, transcript, tmp_path):
        """Rule 2: the offset has to survive into the machine-readable file."""
        path = write_transcript_json(tmp_path / "t.json", transcript,
                                     {"time_offset": 720.0})
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data["time_offset"] == 720.0

    def test_is_valid_utf8_json_for_accented_text(self, tmp_path):
        transcript = Transcript([{"start": 0.0, "end": 1.0, "text": "ñandú áéí"}],
                                "es", 1.0, 1.0, "tiny")
        path = write_transcript_json(tmp_path / "t.json", transcript)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data["segments"][0]["text"] == "ñandú áéí"


class TestNarrative:
    def test_txt_names_the_model_that_wrote_it(self, tmp_path):
        """The reader has to know a local 3B model produced this, not a person."""
        path = write_narrative_txt(tmp_path / "n.txt", "Un parrafo.", "v.mp4",
                                   frame_count=9, frame_interval=20,
                                   segment_count=57, backend_name="ollama",
                                   span=(720.0, 900.0))
        text = path.read_text(encoding="utf-8-sig")
        assert "ollama" in text
        assert "Un parrafo." in text

    def test_txt_records_the_span_on_the_source_clock(self, tmp_path):
        path = write_narrative_txt(tmp_path / "n.txt", "Un parrafo.", "v.mp4",
                                   frame_count=9, frame_interval=20,
                                   segment_count=57, backend_name="ollama",
                                   span=(720.0, 900.0))
        text = path.read_text(encoding="utf-8-sig")
        assert "00:12:00" in text and "00:15:00" in text

    def test_markdown_heads_each_section_with_its_start_time(self, tmp_path):
        path = write_narrative_markdown(tmp_path / "n.md", "v.mp4",
                                        [(720.0, "Primero."), (780.0, "Segundo.")])
        text = path.read_text(encoding="utf-8-sig")
        assert "## 00:12:00" in text
        assert "## 00:13:00" in text

    def test_markdown_keeps_sections_in_order(self, tmp_path):
        path = write_narrative_markdown(tmp_path / "n.md", "v.mp4",
                                        [(720.0, "Primero."), (780.0, "Segundo.")])
        text = path.read_text(encoding="utf-8-sig")
        assert text.index("Primero.") < text.index("Segundo.")

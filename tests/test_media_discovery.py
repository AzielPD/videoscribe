"""Tests for what the inbox picks up.

The pipeline works from the extracted audio track, so a recording that arrives
as an MP3 needs nothing special. This already worked through ``--file``, which
never looked at the extension; the inbox was the only thing that did not know.
"""

from __future__ import annotations

import pytest

from videoscribe.pipeline import (
    AUDIO_EXTENSIONS,
    MEDIA_EXTENSIONS,
    VIDEO_EXTENSIONS,
    find_videos,
    output_folder_for,
)


def drop(folder, *names):
    """Create empty files in ``folder`` and return it."""
    for name in names:
        (folder / name).write_bytes(b"")
    return folder


class TestFindVideos:
    def test_finds_video_files(self, tmp_path):
        drop(tmp_path, "a.mp4", "b.mkv", "c.mov")
        assert len(find_videos(tmp_path)) == 3

    def test_finds_audio_files(self, tmp_path):
        """The capability that existed but was unreachable from the inbox."""
        drop(tmp_path, "hearing.mp3", "call.wav", "voice.m4a")
        assert len(find_videos(tmp_path)) == 3

    def test_finds_both_together(self, tmp_path):
        drop(tmp_path, "a.mp4", "b.mp3")
        assert [p.name for p in find_videos(tmp_path)] == ["a.mp4", "b.mp3"]

    def test_ignores_unrelated_files(self, tmp_path):
        drop(tmp_path, "notes.txt", "sheet.xlsx", ".gitkeep", "README.md")
        assert find_videos(tmp_path) == []

    def test_is_case_insensitive(self, tmp_path):
        """Phones and cameras write .MP4 and .MOV in capitals."""
        drop(tmp_path, "A.MP4", "B.MP3")
        assert len(find_videos(tmp_path)) == 2

    def test_sorted_by_name(self, tmp_path):
        drop(tmp_path, "c.mp4", "a.mp4", "b.mp4")
        assert [p.name for p in find_videos(tmp_path)] == ["a.mp4", "b.mp4", "c.mp4"]

    def test_a_missing_folder_is_not_an_error(self, tmp_path):
        assert find_videos(tmp_path / "nope") == []

    def test_does_not_descend_into_subfolders(self, tmp_path):
        """Only what the user dropped in, not an archive they happen to keep there."""
        (tmp_path / "old").mkdir()
        drop(tmp_path / "old", "archived.mp4")
        drop(tmp_path, "current.mp4")
        assert [p.name for p in find_videos(tmp_path)] == ["current.mp4"]


class TestExtensionSets:
    def test_media_is_video_plus_audio(self):
        assert MEDIA_EXTENSIONS == VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

    def test_video_and_audio_do_not_overlap(self):
        assert not (VIDEO_EXTENSIONS & AUDIO_EXTENSIONS)

    @pytest.mark.parametrize("extension", [".mp3", ".wav", ".m4a", ".flac", ".ogg"])
    def test_the_common_audio_formats_are_covered(self, extension):
        assert extension in MEDIA_EXTENSIONS

    @pytest.mark.parametrize("extension", [".mp4", ".mkv", ".mov", ".avi", ".webm"])
    def test_the_common_video_formats_are_covered(self, extension):
        assert extension in MEDIA_EXTENSIONS

    def test_every_extension_starts_with_a_dot(self):
        """Path.suffix always includes it, so a bare 'mp3' would never match."""
        assert all(e.startswith(".") for e in MEDIA_EXTENSIONS)

    def test_every_extension_is_lowercase(self):
        """find_videos lowercases the suffix before looking it up."""
        assert all(e == e.lower() for e in MEDIA_EXTENSIONS)


class TestOutputFolder:
    def test_an_audio_file_gets_a_folder_like_any_other(self, tmp_path):
        assert output_folder_for(tmp_path / "hearing.mp3", tmp_path).name == "hearing"

    def test_the_extension_is_dropped(self, tmp_path):
        assert output_folder_for(tmp_path / "a.mp4", tmp_path).name == "a"

"""Tests for the defences, so that removing one fails the build.

A security check that nothing exercises is a comment. These cover the two ways
this toolkit takes input from outside itself: an address from the environment,
and an archive downloaded from the internet.
"""

from __future__ import annotations

import io
import tarfile
import zipfile

import pytest

from videoscribe.install import (
    _download,
    _members_staying_inside,
    _zip_names_staying_inside,
)
from videoscribe.vision import _check_http_url


class TestCheckHttpUrl:
    """OLLAMA_HOST comes from the environment; urllib opens whatever it says."""

    @pytest.mark.parametrize("url", [
        "http://localhost:11434/api/generate",
        "https://api.example.com/v1",
        "HTTP://LOCALHOST:11434/x",
    ])
    def test_accepts_http_and_https(self, url):
        assert _check_http_url(url) == url

    @pytest.mark.parametrize("url", [
        "file:///c:/windows/win.ini",
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "//example.com/x",
        "",
    ])
    def test_rejects_everything_else(self, url):
        with pytest.raises(RuntimeError, match="http"):
            _check_http_url(url)

    def test_names_the_variable_to_look_at(self, url="file:///etc/passwd"):
        """A refusal the user cannot act on is only half a defence."""
        with pytest.raises(RuntimeError, match="OLLAMA_HOST"):
            _check_http_url(url)


class TestDownloadRequiresHttps:
    def test_refuses_plain_http(self, tmp_path):
        with pytest.raises(ValueError, match="HTTPS"):
            _download("http://example.com/ffmpeg.zip", tmp_path / "out.zip")

    def test_refuses_a_local_file(self, tmp_path):
        with pytest.raises(ValueError, match="HTTPS"):
            _download("file:///etc/passwd", tmp_path / "out.zip")


def make_tar(tmp_path, names, link=None):
    """A tar carrying entries with the given names, plus an optional symlink."""
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, "w") as bundle:
        for name in names:
            data = b"x"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
        if link:
            name, target = link
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            bundle.addfile(info)
    return archive


class TestTarPathTraversal:
    """The fallback for old Pythons used to extract unfiltered."""

    def test_a_harmless_archive_passes(self, tmp_path):
        archive = make_tar(tmp_path, ["ffmpeg/bin/ffmpeg"])
        destination = tmp_path / "out"
        destination.mkdir()
        with tarfile.open(archive) as bundle:
            assert len(list(_members_staying_inside(bundle, destination))) == 1

    def test_a_parent_directory_escape_is_refused(self, tmp_path):
        archive = make_tar(tmp_path, ["../../escaped.txt"])
        destination = tmp_path / "out"
        destination.mkdir()
        with tarfile.open(archive) as bundle, pytest.raises(ValueError, match="escapes"):
            list(_members_staying_inside(bundle, destination))

    def test_a_symlink_pointing_outside_is_refused(self, tmp_path):
        archive = make_tar(tmp_path, [], link=("link", "../../../../etc/passwd"))
        destination = tmp_path / "out"
        destination.mkdir()
        with tarfile.open(archive) as bundle, pytest.raises(ValueError, match="outside"):
            list(_members_staying_inside(bundle, destination))

    def test_a_symlink_staying_inside_is_allowed(self, tmp_path):
        archive = make_tar(tmp_path, ["real"], link=("link", "real"))
        destination = tmp_path / "out"
        destination.mkdir()
        with tarfile.open(archive) as bundle:
            assert len(list(_members_staying_inside(bundle, destination))) == 2


class TestZipPathTraversal:
    def test_a_harmless_archive_passes(self, tmp_path):
        archive = tmp_path / "ok.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("ffmpeg/bin/ffmpeg.exe", "x")
        destination = tmp_path / "out"
        destination.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            assert _zip_names_staying_inside(bundle, destination) == [
                "ffmpeg/bin/ffmpeg.exe"
            ]

    def test_a_parent_directory_escape_is_refused(self, tmp_path):
        archive = tmp_path / "evil.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../../escaped.exe", "x")
        destination = tmp_path / "out"
        destination.mkdir()
        with zipfile.ZipFile(archive) as bundle, pytest.raises(ValueError, match="escapes"):
            _zip_names_staying_inside(bundle, destination)


class TestNoSecretsInOutput:
    """An API key must never reach a file the user might email to someone."""

    def test_api_key_backends_read_from_the_environment_only(self):
        """Keys are never a config.json field, so they cannot be committed."""
        from videoscribe.config import DEFAULTS

        for key in DEFAULTS:
            assert "api_key" not in key.lower()
            assert "secret" not in key.lower()
            assert "token" not in key.lower()

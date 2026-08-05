"""Locating and checking the external programs VideoScribe depends on.

Three things must be present for a full run:

* **ffmpeg**       -- extracts audio and video frames. Always required.
* **faster-whisper** -- speech recognition. Always required.
* **claude**       -- the Claude Code command line tool. Only required for the
  optional visual narration step.

Nothing here installs anything; that is the job of ``init.ps1`` / ``init.sh``.
These helpers only report what is present so the program can fail early with a
message a non-technical user can act on.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Folders where ffmpeg commonly lands on Windows when it is not on PATH.
WINDOWS_FFMPEG_HINTS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\*\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\*\bin\ffmpeg.exe"),
]

# ...and on macOS / Linux.
UNIX_FFMPEG_HINTS = [
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "/snap/bin/ffmpeg",
]


class ToolMissing(RuntimeError):
    """Raised when a required external program cannot be found."""


def find_ffmpeg(override: str = "") -> str:
    """Return the full path to ffmpeg.

    Looks at, in order: an explicit override from config, the PATH, and then a
    short list of well-known install folders. Raises :class:`ToolMissing` with
    installation instructions when nothing turns up.
    """
    if override:
        if Path(override).is_file():
            return str(Path(override))
        raise ToolMissing(
            f"paths.ffmpeg points to '{override}', but there is no file there.\n"
            "Fix it in config.json or .env, or leave it empty to search automatically."
        )

    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path

    hints = WINDOWS_FFMPEG_HINTS if os.name == "nt" else UNIX_FFMPEG_HINTS
    for pattern in hints:
        # glob.glob, not Path.glob: these patterns are absolute and carry a
        # wildcard in the middle ("C:/ffmpeg/*/bin/ffmpeg.exe"), which Path.glob
        # cannot express without first guessing a base directory.
        for candidate in sorted(glob.glob(pattern)):  # noqa: PTH207 - see above
            if Path(candidate).is_file():
                return candidate

    raise ToolMissing(
        "ffmpeg was not found.\n"
        "  Windows : run init.cmd, or install it with  winget install Gyan.FFmpeg\n"
        "  macOS   : run ./init.sh, or install it with  brew install ffmpeg\n"
        "  Linux   : run ./init.sh, or install it with  sudo apt install ffmpeg"
    )


def find_ffprobe(ffmpeg_path: str) -> str:
    """Return the ffprobe that sits next to a given ffmpeg binary."""
    sibling = Path(ffmpeg_path).with_name("ffprobe" + (".exe" if os.name == "nt" else ""))
    if sibling.is_file():
        return str(sibling)
    on_path = shutil.which("ffprobe")
    if on_path:
        return on_path
    raise ToolMissing(f"ffprobe was not found next to {ffmpeg_path} nor on PATH.")


def find_claude() -> str:
    """Return the path to the Claude Code CLI, used for visual narration."""
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    raise ToolMissing(
        "The 'claude' command was not found, so the visual narration step cannot run.\n"
        "Install it from https://claude.com/claude-code and sign in once, or turn the\n"
        "step off by setting narration.enabled to false in config.json."
    )


def has_faster_whisper() -> bool:
    """True when the speech recognition package is importable."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class ToolStatus:
    """Result of a single check, ready to print."""

    name: str
    ok: bool
    detail: str
    required: bool = True

    def line(self) -> str:
        mark = "OK     " if self.ok else ("MISSING" if self.required else "not set")
        return f"  [{mark}] {self.name:<16} {self.detail}"


def check_all(ffmpeg_override: str = "") -> list[ToolStatus]:
    """Run every environment check and return the results in display order."""
    results: list[ToolStatus] = []

    import sys

    version = ".".join(str(n) for n in sys.version_info[:3])
    results.append(ToolStatus("python", sys.version_info >= (3, 10),
                              f"{version} at {sys.executable}"))

    try:
        path = find_ffmpeg(ffmpeg_override)
        detail = path
        try:
            out = subprocess.run(
                [path, "-version"], capture_output=True, text=True, timeout=20, check=False
            )
            first = out.stdout.splitlines()[0] if out.stdout else ""
            if first:
                detail = f"{first.split(' Copyright')[0]}  ({path})"
        except (OSError, subprocess.SubprocessError):
            pass
        results.append(ToolStatus("ffmpeg", True, detail))
    except ToolMissing as exc:
        results.append(ToolStatus("ffmpeg", False, str(exc).splitlines()[0]))

    ok = has_faster_whisper()
    if ok:
        import faster_whisper

        detail = f"version {getattr(faster_whisper, '__version__', 'unknown')}"
    else:
        detail = "not installed -- run:  pip install -r requirements.txt"
    results.append(ToolStatus("faster-whisper", ok, detail))

    try:
        import numpy

        results.append(ToolStatus("numpy", True, f"version {numpy.__version__}"))
    except ImportError:
        results.append(ToolStatus("numpy", False,
                                  "not installed -- run:  pip install -r requirements.txt"))

    try:
        results.append(ToolStatus("claude CLI", True, find_claude(), required=False))
    except ToolMissing:
        results.append(
            ToolStatus(
                "claude CLI",
                False,
                "not found -- only needed for the visual narration step",
                required=False,
            )
        )

    return results

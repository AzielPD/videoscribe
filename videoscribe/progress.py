"""Console progress reporting: numbered steps and a progress bar.

No third-party dependency. The bar redraws in place with a carriage return and
falls back to plain line-by-line output when the output is redirected to a file
or the terminal cannot handle it.

Typical output::

    ============================================================
     VideoScribe  --  VID_20240115_101500.mp4
    ============================================================

    [1/4] Reading the video file
          50 minutes 30 seconds, audio present, 1080x1920

    [2/4] Extracting audio
          [##############################] 100%  done in 0:15
          -> 01_audio.mp3 (46.2 MB)

    [3/4] Converting speech to text
          [############------------------]  41%  20:43 / 50:30  ETA 12:04
"""

from __future__ import annotations

import shutil
import sys
import time
from typing import TextIO

from .timecode import format_timecode

BAR_WIDTH = 30
FILLED, EMPTY = "#", "-"


def _supports_redraw(stream: TextIO) -> bool:
    """True when we can safely redraw a line in place."""
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


class Reporter:
    """Prints the numbered steps of a run and owns the progress bars."""

    def __init__(self, total_steps: int, stream: TextIO | None = None, quiet: bool = False):
        self.total_steps = total_steps
        self.stream = stream or sys.stdout
        self.quiet = quiet
        self.current_step = 0
        self._redraw = _supports_redraw(self.stream)

    # --- Framing ----------------------------------------------------------
    def banner(self, title: str, subtitle: str = "") -> None:
        if self.quiet:
            return
        width = min(shutil.get_terminal_size((70, 20)).columns, 70)
        self._write("\n" + "=" * width + "\n")
        self._write(f" {title}\n")
        if subtitle:
            self._write(f" {subtitle}\n")
        self._write("=" * width + "\n")

    def step(self, description: str) -> None:
        """Announce the next numbered step."""
        self.current_step += 1
        if self.quiet:
            return
        self._write(f"\n[{self.current_step}/{self.total_steps}] {description}\n")

    def detail(self, message: str) -> None:
        """An indented note underneath the current step."""
        if self.quiet:
            return
        for line in str(message).splitlines():
            self._write(f"      {line}\n")

    def warn(self, message: str) -> None:
        """A note the user should actually read; shown even in quiet mode."""
        for line in str(message).splitlines():
            self._write(f"      ! {line}\n")

    def done(self, message: str) -> None:
        if self.quiet:
            return
        self._write(f"      -> {message}\n")

    # --- Progress bars ----------------------------------------------------
    def bar(self, total: float, unit: str = "plain") -> ProgressBar:
        """Create a bar bound to this reporter.

        ``unit`` selects how the numbers are rendered: ``"time"`` shows
        timecodes (00:12:30 / 00:50:30), anything else shows counts (7 / 26).
        """
        return ProgressBar(self, total, unit)

    def _write(self, text: str) -> None:
        self.stream.write(text)
        self.stream.flush()


class ProgressBar:
    """A single in-place progress bar. Use as a context manager."""

    def __init__(self, reporter: Reporter, total: float, unit: str = "plain"):
        self.reporter = reporter
        self.total = max(float(total), 1e-9)
        self.unit = unit
        self.started = time.monotonic()
        self.value = 0.0
        self._last_render = 0.0
        self._finished = False

    def __enter__(self) -> ProgressBar:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def update(self, value: float, note: str = "") -> None:
        """Set absolute progress and redraw, at most a few times per second."""
        self.value = min(max(value, 0.0), self.total)
        now = time.monotonic()
        if now - self._last_render < 0.15 and self.value < self.total:
            return
        self._last_render = now
        self._render(note)

    def advance(self, amount: float = 1.0, note: str = "") -> None:
        self.update(self.value + amount, note)

    def close(self, note: str = "") -> None:
        """Finish the bar, leaving the completed line on screen."""
        if self._finished:
            return
        self._finished = True
        self.value = self.total
        elapsed = time.monotonic() - self.started
        self._render(note or f"done in {int(elapsed // 60)}:{int(elapsed % 60):02d}", final=True)

    # --- Rendering --------------------------------------------------------
    def _render(self, note: str = "", final: bool = False) -> None:
        if self.reporter.quiet:
            return
        fraction = self.value / self.total
        filled = int(round(BAR_WIDTH * fraction))
        bar = FILLED * filled + EMPTY * (BAR_WIDTH - filled)

        if self.unit == "time":
            counts = f"{format_timecode(self.value)} / {format_timecode(self.total)}"
        else:
            counts = f"{int(self.value)} / {int(self.total)}"

        suffix = note
        if not final and not note and fraction > 0.02:
            elapsed = time.monotonic() - self.started
            remaining = elapsed / fraction - elapsed
            suffix = f"ETA {int(remaining // 60)}:{int(remaining % 60):02d}"

        line = f"      [{bar}] {fraction * 100:3.0f}%  {counts}"
        if suffix:
            line += f"  {suffix}"

        if self.reporter._redraw:
            # Pad to clear whatever the previous, possibly longer, line left.
            self.reporter._write("\r" + line.ljust(78) + ("\n" if final else ""))
        elif final:
            self.reporter._write(line + "\n")

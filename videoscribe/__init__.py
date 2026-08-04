"""VideoScribe -- turn a video into a written, checkable document.

Two things come out of a video file:

* a **transcript**, with each speaker labelled and every turn timecoded, and
* optionally a **written account** of what happens on screen, produced by an
  image model reading video frames alongside the transcript.

Everything except the visual account runs locally with no account or API key.

Quick start
-----------
::

    python videoscribe.py            # interactive menu
    python videoscribe.py run        # process everything in inbox/
    python videoscribe.py doctor     # check the installation

Design notes worth knowing before changing anything:

* Timecodes are always truncated, never rounded, so they point at the moment a
  statement can be verified. See :mod:`videoscribe.timecode`.
* Timecodes cited by the image model are checked against the real frame and
  transcript times, and removed when invented.
* Speaker separation uses hand-written acoustic features rather than a neural
  embedding, to keep installation to a single ``pip install``. It is the
  weakest part of the toolkit and says so in its own output.
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["__version__", "main"]


def main(argv: list[str] | None = None) -> int:
    """Entry point used by ``videoscribe.py`` and by ``python -m videoscribe``."""
    from .cli import main as cli_main

    return cli_main(argv)

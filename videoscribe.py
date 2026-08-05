#!/usr/bin/env python3
"""VideoScribe entry point.

Run this file to start the program:

    python videoscribe.py            open the interactive menu
    python videoscribe.py run        process every video in the inbox folder
    python videoscribe.py doctor     check that everything is installed

The real code lives in the ``videoscribe`` package next to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from any working directory, e.g. by double-clicking run.cmd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# noqa: UP036 - deliberately checks a version below the supported floor. This
# file parses on 3.8, so the guard is what turns a baffling crash into a
# sentence telling the user to upgrade.
if sys.version_info < (3, 9):  # noqa: UP036 - pragma: no cover
    sys.exit(
        "VideoScribe needs Python 3.9 or newer.\n"
        f"This is Python {'.'.join(str(n) for n in sys.version_info[:3])}.\n"
        "Install a newer version from https://www.python.org/downloads/"
    )

from videoscribe import main  # noqa: E402  (import must follow the path fix)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped by the user.")
        # `from None`: Ctrl-C is the user's decision, not an error to report.
        raise SystemExit(130) from None

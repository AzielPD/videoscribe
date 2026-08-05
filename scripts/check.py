#!/usr/bin/env python3
"""Run every check over the codebase: tests, code quality, security.

    python scripts/check.py            run everything, then a summary
    python scripts/check.py tests      only the unit tests
    python scripts/check.py quality    only the linter
    python scripts/check.py security   only the security scans

Each check is run even when an earlier one fails, because a linting complaint
should not hide a failing test. The exit code is non-zero if any of them failed,
which is what a CI job wants.

Needs the development tools:  pip install -r requirements-dev.txt
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# This file lives in scripts/, so the repository is one level up. Every check
# below is run from there, because ruff, pytest and bandit all resolve their
# configuration from pyproject.toml in the working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
RULE = "=" * 70

# name -> (group, argv, what a failure means)
CHECKS: dict[str, tuple[str, list[str], str]] = {
    "unit tests": (
        "tests",
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        "Behaviour changed. Read the failure before changing the test.",
    ),
    "code quality": (
        "quality",
        [sys.executable, "-m", "ruff", "check", "."],
        "Style or a likely bug. Most are fixable with: ruff check . --fix",
    ),
    "security (code)": (
        "security",
        [sys.executable, "-m", "bandit", "-r", "videoscribe/", "videoscribe.py",
         "-c", "pyproject.toml", "-q"],
        "A risky pattern. If it is deliberate, say why in a '# nosec' comment.",
    ),
    "security (dependencies)": (
        "security",
        [sys.executable, "-m", "pip_audit", "-r", "requirements.txt",
         "--progress-spinner", "off"],
        "A dependency has a known vulnerability. Upgrade it.",
    ),
}


def run(name: str, argv: list[str]) -> bool:
    """Run one check, showing its output as it goes."""
    print(f"\n{RULE}\n {name}\n{RULE}")
    try:
        return subprocess.run(argv, cwd=REPO_ROOT, check=False).returncode == 0
    except FileNotFoundError:
        print(f"  Could not run {argv[0]}. Try: pip install -r requirements-dev.txt")
        return False


def main(argv: list[str]) -> int:
    wanted = argv[1] if len(argv) > 1 else "all"
    if wanted not in {"all", "tests", "quality", "security"}:
        print(__doc__)
        return 2

    if not shutil.which(sys.executable):
        print("Could not find the Python interpreter that is running this.")
        return 2

    selected = {
        name: spec for name, spec in CHECKS.items()
        if wanted in ("all", spec[0])
    }

    results = {name: run(name, argv_) for name, (_, argv_, _) in selected.items()}

    print(f"\n{RULE}\n SUMMARY\n{RULE}")
    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        if not passed:
            print(f"         {CHECKS[name][2]}")

    failed = [name for name, passed in results.items() if not passed]
    print()
    if failed:
        print(f"  {len(failed)} of {len(results)} checks failed.")
        return 1
    print(f"  All {len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env bash
# ============================================================================
#  Start VideoScribe on macOS or Linux.
#
#  Run:  ./run.sh
#
#  With no arguments this opens the menu. Anything you pass is handed straight
#  to the program, so ./run.sh run --describe works too.
#
#  If it complains that something is missing, run ./init.sh first.
# ============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Prefer the private environment created by init.sh.
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo
    echo "  Python was not found on this computer."
    echo "  Run ./init.sh first to install it."
    echo
    exit 1
fi

exec "$PYTHON" videoscribe.py "$@"

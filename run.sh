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
    # Offer to fix it rather than just reporting it: someone who has never
    # used a terminal has no way to act on "run ./init.sh first".
    echo
    echo "  Python was not found on this computer."
    echo "  VideoScribe needs it, and the setup script can install it for you."
    echo
    if [ -t 0 ]; then
        printf '  Run the setup now? (y/n) [y]: '
        read -r answer || answer=""
        case "${answer:-y}" in
            [YySs]*)
                echo
                exec "$REPO_ROOT/init.sh"
                ;;
        esac
    fi
    echo
    echo "  When you are ready, run:  ./init.sh"
    echo
    exit 1
fi

exec "$PYTHON" videoscribe.py "$@"

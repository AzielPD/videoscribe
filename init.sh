#!/usr/bin/env bash
# ============================================================================
#  VideoScribe setup for macOS and Linux.
#
#  Checks for each requirement and installs only what is missing:
#
#    1. Python 3.10 or newer
#    2. ffmpeg
#    3. Python packages (into a virtual environment)
#    4. Folders (inbox, output)
#    5. Personal settings file (.env)
#
#  Usage:
#      ./init.sh                 normal setup
#      ./init.sh --dry-run       show what would happen, change nothing
#      ./init.sh --no-venv       install packages system-wide instead
# ============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

DRY_RUN=0
USE_VENV=1
STEP=0
TOTAL_STEPS=5

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --no-venv) USE_VENV=0 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# --- Output helpers ---------------------------------------------------------
if [ -t 1 ]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m';  C_DIM=$'\033[2m';    C_OFF=$'\033[0m'
else
    C_CYAN=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_DIM=''; C_OFF=''
fi

step()   { STEP=$((STEP + 1)); printf '\n%s[%d/%d] %s%s\n' "$C_CYAN" "$STEP" "$TOTAL_STEPS" "$1" "$C_OFF"; }
ok()     { printf '      %s[ok]   %s%s\n' "$C_GREEN" "$1" "$C_OFF"; }
info()   { printf '      %s%s%s\n' "$C_DIM" "$1" "$C_OFF"; }
warn()   { printf '      %s[!]    %s%s\n' "$C_YELLOW" "$1" "$C_OFF"; }
fail()   { printf '      %s[fail] %s%s\n' "$C_RED" "$1" "$C_OFF"; }
banner() { printf '\n%s\n %s\n%s\n' "======================================================================" "$1" "======================================================================"; }

run() {
    # Execute a command unless this is a dry run.
    if [ "$DRY_RUN" -eq 1 ]; then
        info "would run: $*"
        return 0
    fi
    "$@"
}

have() { command -v "$1" >/dev/null 2>&1; }

# Detect the package manager once, so the install steps stay readable.
detect_installer() {
    if [ "$(uname -s)" = "Darwin" ]; then
        have brew && echo "brew" || echo "none"
    elif have apt-get; then echo "apt"
    elif have dnf;     then echo "dnf"
    elif have pacman;  then echo "pacman"
    elif have zypper;  then echo "zypper"
    else echo "none"
    fi
}
INSTALLER="$(detect_installer)"

install_package() {
    # install_package <package name> <friendly name>
    local package="$1" friendly="$2"
    case "$INSTALLER" in
        brew)   run brew install "$package" ;;
        apt)    run sudo apt-get update -qq && run sudo apt-get install -y "$package" ;;
        dnf)    run sudo dnf install -y "$package" ;;
        pacman) run sudo pacman -S --noconfirm "$package" ;;
        zypper) run sudo zypper install -y "$package" ;;
        none)
            fail "$friendly is missing and no package manager was found."
            if [ "$(uname -s)" = "Darwin" ]; then
                info "Install Homebrew first: https://brew.sh"
            fi
            return 1
            ;;
    esac
}

banner "VIDEOSCRIBE SETUP"
echo " This installs the programs needed to turn a video into a document."
echo " It only installs what is missing."
[ "$DRY_RUN" -eq 1 ] && warn "Dry run: nothing will actually be installed."

# --- 0. Language ------------------------------------------------------------
# Asked first, and only when the terminal is interactive, so an automated run
# is never left waiting for an answer that will not come.
UI_LANGUAGE=""
if [ "$DRY_RUN" -eq 0 ] && [ -t 0 ]; then
    printf '\n%s\n SELECT LANGUAGE  /  SELECCIONA IDIOMA\n%s\n\n' \
        "======================================================================" \
        "======================================================================"
    echo "  1) English"
    echo "  2) Espanol (Spanish)"
    echo
    printf '  Pick a number / Elige un numero [1]: '
    read -r language_choice || language_choice=""
    case "$language_choice" in
        2) UI_LANGUAGE="es" ;;
        *) UI_LANGUAGE="en" ;;
    esac
fi

# --- 1. Python --------------------------------------------------------------
step "Checking Python"

PYTHON=""
for candidate in python3 python; do
    if have "$candidate"; then
        version="$("$candidate" -c 'import sys; print(".".join(str(n) for n in sys.version_info[:3]))' 2>/dev/null || echo "")"
        if [ -n "$version" ] && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            ok "Python $version found at $(command -v "$candidate")"
            break
        elif [ -n "$version" ]; then
            warn "Python $version is older than the required 3.10"
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    warn "Python 3.10 or newer is not installed."
    if [ "$INSTALLER" = "brew" ]; then
        install_package python "Python" && PYTHON=python3
    else
        install_package python3 "Python" && PYTHON=python3
    fi
    if [ -z "$PYTHON" ] || ! have "$PYTHON"; then
        fail "Could not install Python. Get it from https://www.python.org/downloads/"
        exit 1
    fi
    ok "Python installed."
fi

# --- 2. ffmpeg --------------------------------------------------------------
step "Checking ffmpeg"

if have ffmpeg; then
    ok "ffmpeg found at $(command -v ffmpeg)"
else
    warn "ffmpeg is not installed."
    if install_package ffmpeg "ffmpeg"; then
        ok "ffmpeg installed."
    else
        fail "Nothing will work without ffmpeg."
        exit 1
    fi
fi

# --- 3. Python packages -----------------------------------------------------
step "Installing Python packages"

if [ ! -f requirements.txt ]; then
    fail "requirements.txt is missing from $REPO_ROOT"
    exit 1
fi

if [ "$USE_VENV" -eq 1 ]; then
    # A virtual environment keeps these packages away from the system Python,
    # which several Linux distributions now refuse to modify (PEP 668).
    if [ ! -d .venv ]; then
        info "Creating a private Python environment in .venv"
        run "$PYTHON" -m venv .venv
    else
        info "Reusing the existing .venv"
    fi
    VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
    [ "$DRY_RUN" -eq 1 ] && VENV_PYTHON="$PYTHON"
else
    VENV_PYTHON="$PYTHON"
    info "Installing system-wide, as requested with --no-venv"
fi

info "This downloads a few hundred megabytes the first time."
run "$VENV_PYTHON" -m pip install --quiet --disable-pip-version-check --upgrade pip
run "$VENV_PYTHON" -m pip install --disable-pip-version-check -r requirements.txt
ok "Packages installed."

# --- 4. Folders -------------------------------------------------------------
step "Creating folders"

for folder in inbox output; do
    if [ -d "$folder" ]; then
        info "$folder already exists"
    else
        run mkdir -p "$folder"
        ok "$folder created"
    fi
done

# --- 5. Personal settings ---------------------------------------------------
step "Setting up your personal settings file"

if [ -f .env ]; then
    info ".env already exists; leaving it untouched"
elif [ -f .env.example ]; then
    run cp .env.example .env
    ok ".env created from the example"
fi

# Record the language chosen at the start, together with the speech and
# written-output languages it implies, so the first real run starts correctly.
if [ -n "$UI_LANGUAGE" ] && [ -f .env ]; then
    if [ "$UI_LANGUAGE" = "es" ]; then
        speech="es"; written="Spanish"
    else
        speech="en"; written="English"
    fi
    # sed -i takes an argument on BSD sed (macOS) and none on GNU sed (Linux).
    if sed --version >/dev/null 2>&1; then
        SED_INPLACE=(-i)
    else
        SED_INPLACE=(-i '')
    fi
    sed "${SED_INPLACE[@]}" \
        -e "s|^VIDEOSCRIBE_UI_LANGUAGE=.*|VIDEOSCRIBE_UI_LANGUAGE=$UI_LANGUAGE|" \
        -e "s|^VIDEOSCRIBE_LANGUAGE=.*|VIDEOSCRIBE_LANGUAGE=$speech|" \
        -e "s|^VIDEOSCRIBE_NARRATION_LANGUAGE=.*|VIDEOSCRIBE_NARRATION_LANGUAGE=$written|" \
        .env
    ok "Language set to $UI_LANGUAGE (speech $speech, written accounts $written)"
fi

run chmod +x run.sh 2>/dev/null || true

# --- Report -----------------------------------------------------------------
if [ "$DRY_RUN" -eq 0 ]; then
    banner "CHECKING YOUR COMPUTER"
    "$VENV_PYTHON" videoscribe.py doctor || true
fi

banner "SETUP FINISHED"
cat <<EOF

  Next steps:

    1. Copy your video files into the 'inbox' folder
    2. Run:  ./run.sh

  Results appear in the 'output' folder, one subfolder per video.

EOF

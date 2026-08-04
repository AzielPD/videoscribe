#!/usr/bin/env bash
# ============================================================================
#  Check that VideoScribe starts correctly on Linux.
#
#  These tests cover everything a user meets *before* any video is processed:
#  the menu, machine detection, tool discovery, and the messages shown when
#  something is missing. They do not transcribe anything, so they finish in
#  seconds and need no model download.
#
#  Usage:
#      bash tests/run_container_tests.sh
#
#  Requires podman (or docker; set ENGINE=docker).
# ============================================================================

set -uo pipefail

ENGINE="${ENGINE:-podman}"
IMAGE="${IMAGE:-videoscribe-test}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PASSED=0
FAILED=0

if [ -t 1 ]; then
    C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
    C_GREEN=''; C_RED=''; C_DIM=''; C_OFF=''
fi

# check <name> <stdin> <expected exit code> <pattern that must appear> [command...]
check() {
    local name="$1" stdin="$2" want_code="$3" want_text="$4"
    shift 4

    local output code
    output="$(printf '%s' "$stdin" | "$ENGINE" run --rm -i "$IMAGE" "$@" 2>&1)"
    code=$?

    local problem=""
    if [ "$want_code" != "any" ] && [ "$code" -ne "$want_code" ]; then
        problem="exit code was $code, expected $want_code"
    elif [ -n "$want_text" ] && ! grep -qi -- "$want_text" <<<"$output"; then
        problem="output did not contain: $want_text"
    fi

    if [ -z "$problem" ]; then
        printf '%s  PASS%s  %s\n' "$C_GREEN" "$C_OFF" "$name"
        PASSED=$((PASSED + 1))
    else
        printf '%s  FAIL%s  %s\n' "$C_RED" "$C_OFF" "$name"
        printf '%s        %s%s\n' "$C_DIM" "$problem" "$C_OFF"
        sed 's/^/        | /' <<<"$output" | tail -20
        FAILED=$((FAILED + 1))
    fi
}

echo
echo "======================================================================"
echo " Building the test image"
echo "======================================================================"
if ! "$ENGINE" build -t "$IMAGE" -f "$REPO_ROOT/tests/Containerfile" "$REPO_ROOT"; then
    echo "Build failed." >&2
    exit 1
fi

echo
echo "======================================================================"
echo " Startup and environment"
echo "======================================================================"

check "python starts and the package imports" \
    "" 0 "1.0.0" \
    python -c "import videoscribe; print(videoscribe.__version__)"

check "every module compiles" \
    "" 0 "" \
    python -m compileall -q videoscribe videoscribe.py

check "ffmpeg is found on Linux" \
    "" 0 "/usr/bin/ffmpeg" \
    python -c "from videoscribe.tools import find_ffmpeg; print(find_ffmpeg())"

check "doctor reports the missing package instead of crashing" \
    "" 1 "faster-whisper" \
    python videoscribe.py doctor

check "doctor detects the Linux machine" \
    "" 1 "Linux" \
    python videoscribe.py doctor

check "models command lists the model table" \
    "" 0 "large-v3" \
    python videoscribe.py models

echo
echo "======================================================================"
echo " Shell scripts"
echo "======================================================================"

# Note the $'\r' quoting: ANSI-C quoting, which produces a real carriage
# return. $"\r" would be locale translation and searches for a literal
# backslash-r, which as a basic regex matches the letter r in every file.
check "run.sh has no carriage returns" \
    "" 0 "clean" \
    bash -c $'grep -q \'\r\' run.sh && echo "HAS CRLF" || echo clean'

check "init.sh has no carriage returns" \
    "" 0 "clean" \
    bash -c $'grep -q \'\r\' init.sh && echo "HAS CRLF" || echo clean'

check "run.cmd does have carriage returns, as cmd.exe needs" \
    "" 0 "crlf ok" \
    bash -c $'grep -q \'\r\' run.cmd && echo "crlf ok" || echo "MISSING CRLF"'

check "run.sh is valid bash" \
    "" 0 "" \
    bash -n run.sh

check "init.sh is valid bash" \
    "" 0 "" \
    bash -n init.sh

check "init.sh --dry-run changes nothing" \
    "" 0 "would run\|already exists\|SETUP FINISHED" \
    bash init.sh --dry-run

check "init.sh --help prints usage" \
    "" 0 "VideoScribe setup" \
    bash init.sh --help

echo
echo "======================================================================"
echo " The main menu"
echo "======================================================================"

check "menu draws and quits cleanly on the quit option" \
    "5
" 0 "WHAT WOULD YOU LIKE TO DO" \
    python videoscribe.py

check "menu lists every option" \
    "5
" 0 "Transcript + description" \
    python videoscribe.py

check "menu shows where videos go" \
    "5
" 0 "/app/inbox" \
    python videoscribe.py

check "menu reports an empty inbox" \
    "5
" 0 "No videos found" \
    python videoscribe.py

check "option 3 reports the machine" \
    "3
" 0 "CPU cores" \
    python videoscribe.py

check "option 3 recommends a model" \
    "3
" 0 "Recommended model" \
    python videoscribe.py

check "option 3 lists the image back ends" \
    "3
" 0 "gemini" \
    python videoscribe.py

check "option 3 prints the settings in use" \
    "3
" 0 "transcription.model" \
    python videoscribe.py

check "option 1 with an empty inbox stops with a message" \
    "1
" 1 "nothing to process" \
    python videoscribe.py

check "invalid input is rejected, then accepted" \
    "9
5
" 0 "Please answer one of" \
    python videoscribe.py

check "end of input is handled without a traceback" \
    "" 0 "Cancelled" \
    python videoscribe.py

echo
echo "======================================================================"
echo " Language"
echo "======================================================================"

check "menu draws in Spanish when asked" \
    "5
" 0 "QUE QUIERES HACER" \
    env VIDEOSCRIBE_UI_LANGUAGE=es python videoscribe.py

check "menu draws in English when asked" \
    "5
" 0 "WHAT WOULD YOU LIKE TO DO" \
    env VIDEOSCRIBE_UI_LANGUAGE=en python videoscribe.py

check "the language option appears in the menu" \
    "5
" 0 "Idioma" \
    env VIDEOSCRIBE_UI_LANGUAGE=es python videoscribe.py

check "the picker is reachable and bilingual" \
    "4
2
5
" 0 "SELECCIONA IDIOMA  /  SELECT LANGUAGE" \
    env VIDEOSCRIBE_UI_LANGUAGE=es python videoscribe.py

check "switching to English redraws the menu in English" \
    "4
1
5
" 0 "WHAT WOULD YOU LIKE TO DO" \
    env VIDEOSCRIBE_UI_LANGUAGE=es python videoscribe.py

check "--ui-language works on the models command" \
    "" 0 "MODELOS DE TRANSCRIPCION" \
    python videoscribe.py models --ui-language es

check "--ui-language works on the doctor command" \
    "" 1 "ESTA COMPUTADORA" \
    python videoscribe.py doctor --ui-language es

check "durations are translated too" \
    "" 0 "unos\|unas" \
    python videoscribe.py models --ui-language es

check "an unknown language falls back to English" \
    "5
" 0 "WHAT WOULD YOU LIKE TO DO" \
    env VIDEOSCRIBE_UI_LANGUAGE=de python videoscribe.py

check "every message has both translations" \
    "" 0 "complete" \
    python -c "
from videoscribe.i18n import MESSAGES, LANGUAGE_NAMES
missing = [k for k, v in MESSAGES.items() for lang in LANGUAGE_NAMES if lang not in v]
print('INCOMPLETE: ' + ', '.join(missing) if missing else 'complete')
"

check "init.sh accepts a language without prompting" \
    "" 0 "SETUP FINISHED" \
    bash init.sh --dry-run

echo
echo "======================================================================"
echo " Menu with a video present"
echo "======================================================================"

# A tiny generated clip, so the menu has something to list without shipping a
# real recording in the repository.
MAKE_CLIP='ffmpeg -loglevel error -f lavfi -i testsrc=duration=2:size=320x240:rate=5 \
           -f lavfi -i sine=frequency=440:duration=2 -shortest \
           -c:v libx264 -c:a aac inbox/VID_20250101_120000.mp4'

check "menu lists a video that is waiting" \
    "5
" 0 "VID_20250101_120000.mp4" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

check "model table appears and the run can be declined" \
    "1
3
n
" 0 "CHOOSE HOW ACCURATE" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

check "model table shows download sizes" \
    "1
3
n
" 0 "480 MB" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

check "declining at the confirmation starts nothing" \
    "1
3
n
" 0 "Start now" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

# Option 2 needs a video before it gets as far as checking for an image model,
# so this only makes sense once the inbox has something in it.
check "option 2 explains that no image model is configured" \
    "2
n
" 1 "image-capable model" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

check "option 2 offers to continue with the transcript only" \
    "2
n
" 1 "Continue with the transcript only" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

check "option 2 falls back to a transcript when the user accepts" \
    "2
y
3
n
" 0 "CHOOSE HOW ACCURATE" \
    bash -c "$MAKE_CLIP && python videoscribe.py"

echo
echo "======================================================================"
printf ' %sPassed: %d%s   %sFailed: %d%s\n' "$C_GREEN" "$PASSED" "$C_OFF" \
    "$([ "$FAILED" -gt 0 ] && echo "$C_RED" || echo "$C_DIM")" "$FAILED" "$C_OFF"
echo "======================================================================"
echo

[ "$FAILED" -eq 0 ]

# Notes for AI coding assistants

Read this before changing anything. It records decisions that look arbitrary but
are not, and mistakes that have already been made once in this codebase.

## What this project is

A toolkit that turns a video into a transcript and, optionally, a written account of
what happens on screen. The primary readers are **lawyers**, who need to quote a
statement and point at the second it was made.

That audience drives every design decision below. When in doubt, choose the option
that makes the output easier to verify, even when it makes the output less
impressive.

## Layout

The root holds only what a *user* touches. Anything a user never double-clicks
belongs in a folder.

```
init.cmd / init.sh        install everything; Windows / Unix. Double-clicked
run.cmd / run.sh          start the program. Double-clicked
videoscribe.py            entry point; run this
config.json               shared defaults, meant to be edited by hand
VERSION                   must match videoscribe.__version__ and CHANGELOG.md;
                          tests/test_version.py fails if they drift
CHANGELOG.md              what changed between releases
.github/workflows/        CI: the same checks, on Linux, Windows and macOS,
                          plus Python 3.9 to prove the floor the README claims
videoscribe/
  config.py               settings: defaults < config.json < .env < CLI
  tools.py                finds ffmpeg, checks the environment
  system.py               profiles the machine, recommends a model
  network.py              which servers are reachable, and what each is for
  progress.py             numbered steps and progress bars
  timecode.py             seconds <-> HH:MM:SS, and timecode validation
  audio.py                ffmpeg: extract audio and frames
  features.py             MFCC and pitch, in NumPy
  diarize.py              clustering segments into speakers
  transcribe.py           faster-whisper
  parallel.py             splitting a recording across workers
  install.py              fetching ffmpeg when it is missing
  vision.py               pluggable image-model back ends
  narrate.py              prompts and windowing for the visual account
  writers.py              output files
  pipeline.py             the 8 steps, in order
  cli.py / menu.py        the two front ends
scripts/
  init.ps1                the real Windows installer; init.cmd hands over to it
  check.py                runs tests, ruff, bandit and pip-audit
tests/                    pytest suite, plus the container tests
powershell/               PowerShell wrappers over the same engine
docs/                     accuracy, configuration, and design assessments
inbox/                    users drop video or audio recordings here
output/<recording name>/  results, one folder per recording
```

Some root files cannot move, and it is worth knowing why before trying:
`pyproject.toml` (ruff, pytest and bandit resolve config from the working
directory), `.containerignore` and `.dockerignore` (the build context is the
repository root), `LICENSE` and `README.md` (GitHub only detects them at root),
and `.env.example` (users copy it to `.env` beside it).

## Rules that must not be broken

### 1. Timecodes truncate, never round

`format_timecode` in `timecode.py` uses `math.floor`. At second 40.7 the correct
label is `00:00:40`, because `00:00:41` may already be the next sentence.

This has already gone wrong once. The original PowerShell version used `[int]`,
which in PowerShell **rounds** — so `[int](3030/3600)` produced `1` hour for a
50-minute video, and every dialogue timecode was shifted. It was misdiagnosed as
the model hallucinating times before the real cause was found. If you port this
logic to another language, check the rounding behaviour of its integer cast first.

### 2. Every timecode refers to the source video

When `--start` is used, the extracted audio begins at zero but the transcript times
are shifted back onto the source video's clock immediately after transcription
(`pipeline.py`). `diarize()` takes an `audio_offset` so it can still index into the
extracted samples. The JSON records `time_offset`.

A user must be able to type any timecode we print into a player of the original file
and land on the right moment. Anything else makes the output unverifiable.

### 3. Invented timecodes are deleted, not kept

`strip_invented_timecodes` checks every `[HH:MM:SS]` the image model writes against
the exact set of frame times and transcript times supplied for that window. Anything
else is removed. Do not soften this into a warning: a wrong timecode is worse than
no timecode.

### 4. Uncertainty is surfaced, not hidden

- `DiarizationResult.quality_note()` warns when the clustering found no real
  structure. Keep it.
- The prompts in `narrate.py` require "apparently" / "it seems" for inference, and
  require unreadable text to be reported as unreadable.
- Every output file carries a disclaimer in its header.

Do not remove any of these to make the output read better.

## Things that will bite you

**ffmpeg `-ss` and `-t` go before `-i`.** After `-i` they apply only to the *first*
output file, which silently produces a trimmed MP3 next to a full-length WAV. This
bug shipped once. See `_time_args` in `audio.py`.

**PowerShell `$ErrorActionPreference = 'Stop'` plus a native command.** Any line the
program writes to stderr becomes a terminating error, even a harmless warning. The
wrappers relax the preference around the call and judge by exit code. Do not
"simplify" that back.

**PowerShell script files need a UTF-8 BOM** in Windows PowerShell 5.1, or non-ASCII
characters are read as the system code page. The scripts here are ASCII-only as
well, as a second line of defence.

**Python's `int()` truncates; PowerShell's `[int]` rounds.** See rule 1.

**Ollama gives a model 4096 tokens of context unless you ask for more.** One frame
of a 1280x720 video costs about 900 tokens, so the default 120-second window (12
frames) arrives at roughly 10,800 and the whole request is refused with HTTP 400 --
instantly, which looks like a broken install rather than a size limit. Worse, the
per-window exception lands in `result.warnings`, and those are never printed when
the run then dies on `error.no_sections`; you have to call `OllamaBackend.generate`
directly to see the cause. `OllamaBackend.context_size` now sizes the window from
the images actually sent.

**Raising the context is not enough on a CPU.** Twelve frames at 16k context blew
past `REQUEST_TIMEOUT` (600 s) on 16 cores. Back ends therefore get a say in how the
recording is cut up, through `VisionBackend.plan_windows`; Ollama shortens the window
so a request holds at most four frames, and keeps the frame interval untouched so
coverage does not silently drop. The adjustment is printed, never silent.

**Measured, not assumed:** `qwen2.5vl:3b` costs about 80 seconds a frame on a CPU,
reads large embroidered lettering but not the fine line under it, and writes *no*
timecodes at all despite the prompt asking for them. That last one is why the local
model is not the default on a machine without a graphics card. If you change the
model or the prompt, re-measure before changing these numbers.

## Testing changes

Run everything before you claim anything works:

```bash
pip install -r requirements-dev.txt     # once
python scripts/check.py                 # tests, ruff, bandit, pip-audit
```

The unit tests in `tests/test_*.py` encode the rules above. If one fails, read the
failure before changing the test: `test_fifty_minutes_is_not_an_hour` exists because
that bug shipped, and `test_timecodes_refer_to_the_source_video` exists because rule
2 is invisible in the output when it breaks.

`tests/run_container_tests.sh` is separate and needs podman; it covers startup and
the menu on Linux.

Then verify by hand with a short sample, which takes about a minute:

```bash
python videoscribe.py run --file inbox/<something>.mp4 \
    --start 00:12:00 --duration 00:02:00 --model tiny --describe \
    --output output_test
```

Then check that the timecodes in `02_transcript.txt` and `04_narrative.txt` refer to
the same moments, and that both match the source video.

`python videoscribe.py doctor` should exit 0 on a working install.

## Style

- Comments explain *why*, not *what*. If a line needs a comment saying what it does,
  rename something instead.
- Docstrings on every module and public function, written for someone who has not
  read the rest of the file.
- Plain English in anything a user sees. No jargon in error messages: say what went
  wrong and what to do about it.
- Everything user-facing is in English. The *default output language* is Spanish
  (`config.json`), which is a setting, not a hard-coded string.

## Deliberate non-goals

- **No neural speaker embeddings by default.** They are better, and they would mean
  a model download plus, for pyannote, a Hugging Face account and licence
  acceptance. Installation staying at one `pip install` is worth the accuracy cost.
  Adding an optional ONNX embedding back end would be a genuine improvement; making
  it mandatory would not.
- **No GUI.** The menu covers non-technical users adequately.
- **No cloud transcription.** The point is that the transcript never leaves the
  machine.

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

```
videoscribe.py            entry point; run this
videoscribe/
  config.py               settings: defaults < config.json < .env < CLI
  tools.py                finds ffmpeg, checks the environment
  system.py               profiles the machine, recommends a model
  progress.py             numbered steps and progress bars
  timecode.py             seconds <-> HH:MM:SS, and timecode validation
  audio.py                ffmpeg: extract audio and frames
  features.py             MFCC and pitch, in NumPy
  diarize.py              clustering segments into speakers
  transcribe.py           faster-whisper
  vision.py               pluggable image-model back ends
  narrate.py              prompts and windowing for the visual account
  writers.py              output files
  pipeline.py             the 8 steps, in order
  cli.py / menu.py        the two front ends
powershell/               PowerShell wrappers over the same engine
inbox/                    users drop videos here
output/<video name>/      results, one folder per video
```

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

## Testing changes

There is no test suite yet. Verify by hand with a short sample, which takes about a
minute:

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

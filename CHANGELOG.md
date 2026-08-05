# Changelog

Notable changes, newest first. Dates are the day the version was tagged.

The version here, the `VERSION` file and `videoscribe.__version__` must always
agree; a test in `tests/test_version.py` fails if they drift apart.

## 1.0.0 — 2026-08-05

First public release.

### What it does

- Turns a video **or an audio recording** into a transcript that labels each
  voice and stamps every turn with a timestamp on the source recording's clock.
- Writes SRT subtitles and a machine-readable JSON alongside it.
- Optionally writes a chronological account of what the camera shows, combining
  frames with the audio, through Claude, Gemini, OpenAI or a local model.
- Runs fully offline for the transcript, after the speech model downloads once.
- Speaks English and Spanish throughout, in the interface and the output files.
- Installs itself on Windows, macOS and Linux, fetching ffmpeg when it is
  missing — including a portable copy that needs no administrator rights.

### Choices worth knowing about

- **Timecodes truncate, never round.** At second 40.7 the label is `00:00:40`,
  because `00:00:41` may already be the next sentence.
- **Every timecode refers to the source video**, including when only part of it
  was processed with `--start`.
- **Invented timecodes are deleted, not flagged.** Anything the image model
  writes is checked against the exact frame and transcript times for that
  window. A wrong timecode is worse than no timecode.
- **Uncertainty is surfaced.** The speaker separation reports its own quality
  score and warns when the voices did not separate cleanly; that warning cannot
  be switched off. Every output file carries a disclaimer.
- **Speaker separation uses acoustic features, not neural voice fingerprints.**
  It is genuinely weaker. It is also why installation is one `pip install` with
  no account and no licence to accept.
- **The description is only offered when a model can actually produce it.**
  Without one, the menu marks it unavailable and the run produces the transcript
  and subtitles as usual.

### Measured, not assumed

- One hour of video, transcribed with `small`: about 59 minutes on a 4-core
  laptop, 22 minutes on 16 cores, 5 minutes on a graphics card.
- Splitting a recording across workers: 2:44 in one part, 1:41 in two, 1:37 in
  four, on 8 minutes of audio with 16 cores.
- The local vision model `qwen2.5vl:3b` costs about 80 seconds per frame on a
  CPU — roughly eight times the length of the recording at the default sampling
  rate — reads large embroidered lettering but not the fine line under it, and
  writes no timecodes at all. This is why it is not the default without a
  graphics card.

### Known limitations

- Speaker separation struggles when several similar voices talk in a noisy
  room. Pass `--speakers N` when you know the number.
- The visual description needs an outside provider unless the machine has a
  graphics card.
- There is no graphical interface. The text menu covers the same ground.

# Configuration

Every setting can be changed in three places. Each one overrides the one before it:

```
built-in defaults  <  config.json  <  .env  <  command line
     (code)            (shared)      (yours)     (this run)
```

- **`config.json`** — shared defaults. Edit this to change behaviour for everyone
  using this copy of the tool. It is committed to version control.
- **`.env`** — your own machine. Copy `.env.example` to `.env` and edit. It is *not*
  committed, so this is where API keys and machine-specific paths belong.
- **Command line** — wins over everything, for a single run.

---

## Transcription

| config.json | .env | Command line | Default |
|---|---|---|---|
| `transcription.model` | `VIDEOSCRIBE_MODEL` | `--model` | `small` |
| `transcription.language` | `VIDEOSCRIBE_LANGUAGE` | `--language` | `es` |
| `transcription.compute_type` | `VIDEOSCRIBE_COMPUTE_TYPE` | — | `int8` |
| `transcription.beam_size` | — | — | `5` |
| `transcription.cpu_threads` | `VIDEOSCRIBE_CPU_THREADS` | — | `0` |

**`model`** — `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`. Bigger is
more accurate and slower. Run `python videoscribe.py models` for timings measured on
your computer.

**`language`** — a two-letter code (`es`, `en`, `pt`, `fr`) or `auto`. **Setting this
wrong is the most common cause of a poor first result.** The shipped default is
Spanish; change it if that is not your language. `auto` works but costs a little
accuracy on short recordings.

**`compute_type`** — `int8` is right for CPU. On a graphics card, `float16` is faster
and slightly more accurate.

**`cpu_threads`** — `0` means use every core, up to 16. Lower it if you want to keep
the machine responsive while it runs.

---

## Speakers

| config.json | .env | Command line | Default |
|---|---|---|---|
| `speakers.count` | `VIDEOSCRIBE_SPEAKERS` | `--speakers` | `0` |
| `speakers.max_count` | `VIDEOSCRIBE_MAX_SPEAKERS` | `--max-speakers` | `6` |
| `speakers.label` | `VIDEOSCRIBE_SPEAKER_LABEL` | — | `Person` |

**`count`** — how many people speak. `0` asks the tool to work it out, which is
unreliable in noisy recordings. If you know the number, give it: the result is
noticeably better. Combine with `--resume` to re-label without re-transcribing.

**`label`** — the word before the number. `Person` gives `Person1`, `Person2`. Use
`Speaker` for English output, `Persona` for Spanish.

See [`ACCURACY.md`](ACCURACY.md) for what to expect from this step.

---

## Visual description

| config.json | .env | Command line | Default |
|---|---|---|---|
| `narration.enabled` | `VIDEOSCRIBE_NARRATION` | `--describe` | `true` |
| `narration.frame_interval_seconds` | `VIDEOSCRIBE_FRAME_INTERVAL` | `--frame-interval` | `10` |
| `narration.window_seconds` | `VIDEOSCRIBE_WINDOW_SECONDS` | `--window` | `120` |
| `narration.max_frame_edge` | — | — | `1568` |
| `narration.vision_model` | `VIDEOSCRIBE_VISION_MODEL` | — | *(automatic)* |
| `narration.synthesis_model` | `VIDEOSCRIBE_SYNTHESIS_MODEL` | — | *(automatic)* |
| `narration.output_language` | `VIDEOSCRIBE_NARRATION_LANGUAGE` | — | `Spanish` |
| — | — | `--vision-backend` | `auto` |

**`frame_interval_seconds`** — one frame every N seconds. This is the main cost
control. At 10 seconds, a 50-minute video produces about 300 frames and roughly
600,000 input tokens. At 20 seconds, half that. Lower it below 10 only when brief
actions matter, such as a document changing hands.

**`window_seconds`** — how much video is described per request. Larger windows give
the model more context and cost fewer requests, but each request is bigger. 120 is a
good balance.

**`max_frame_edge`** — frames are scaled to fit inside this square. 1568 px is the
point beyond which the models downscale anyway, so larger values waste disk and
upload time without adding readable detail.

**`output_language`** — spelled out in English: `Spanish`, `English`, `Portuguese`.
This controls the language the account is *written in*, independently of the spoken
language.

---

## Which image model describes the video

Set `--vision-backend` or leave it as `auto`, which tries these in order and uses
the first one that is configured:

| Back end | What it needs |
|---|---|
| `claude-cli` | The `claude` command installed and signed in. No API key. |
| `anthropic` | `ANTHROPIC_API_KEY` in `.env` |
| `openai` | `OPENAI_API_KEY` in `.env` |
| `gemini` | `GEMINI_API_KEY` in `.env` |

Check what is available with `python videoscribe.py doctor`.

Naming a back end explicitly instead of `auto` makes the tool fail loudly if it is
not configured, rather than quietly using something else.

### Adding another provider

Write a class in `videoscribe/vision.py` with an `is_available()` classmethod and a
`generate(prompt, images, model)` method, then add it to the `BACKENDS` dictionary.
Roughly 30 lines.

---

## Folders

| config.json | .env | Command line | Default |
|---|---|---|---|
| `paths.inbox` | `VIDEOSCRIBE_INBOX` | — | `inbox` |
| `paths.output` | `VIDEOSCRIBE_OUTPUT` | `--output` | `output` |
| `paths.ffmpeg` | `VIDEOSCRIBE_FFMPEG` | — | *(searched)* |

Relative paths are relative to the repository folder. Absolute paths work too, which
is useful for pointing the output at a case folder or a network drive.

**`ffmpeg`** — leave empty and it is found automatically: the PATH first, then the
usual install locations. Set it only if ffmpeg lives somewhere unusual.

---

## Housekeeping

| config.json | .env | Command line | Default |
|---|---|---|---|
| `cleanup.keep_wav` | `VIDEOSCRIBE_KEEP_WAV` | `--keep-work` | `false` |
| `cleanup.keep_frames` | `VIDEOSCRIBE_KEEP_FRAMES` | `--keep-work` | `false` |

The temporary WAV is about 2 MB per minute of video; frames are about 200 KB each.
Both are deleted after a successful run. Keep them while experimenting, because
`--resume` can then reuse them.

---

## Audio

| config.json | .env | Default |
|---|---|---|
| `audio.mp3_bitrate` | `VIDEOSCRIBE_MP3_BITRATE` | `128k` |
| `audio.sample_rate` | — | `16000` |

**`sample_rate`** should not be changed. The speech model expects 16 kHz, and the
acoustic features used for speaker separation assume it throughout.

---

## Worked examples

**A quick sample before committing to a long run**

```bash
python videoscribe.py run --start 00:12:00 --duration 00:03:00 --model tiny
```

**English recording, two speakers, best available accuracy**

```bash
python videoscribe.py run --language en --speakers 2 --model large-v3
```

**Re-label the speakers without re-transcribing**

```bash
python videoscribe.py run --speakers 3 --resume
```

**Visual description at half the usual cost**

```bash
python videoscribe.py run --describe --frame-interval 20
```

**Carry on after an interrupted run**

```bash
python videoscribe.py run --describe --resume
```

Sections already written are kept; only the missing ones are requested again.

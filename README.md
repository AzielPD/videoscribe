# VideoScribe

**English** · [Español](README.es.md)

**Turn a video into a written, timestamped record you can read, search and check.**

You have a video. You need it in writing. VideoScribe takes a video file and gives
you back a transcript, with a timecode on every line and a label for each speaker.
It can also write an account of what the camera shows: what people are wearing,
what is written on a badge or a sign, what document changes hands, and when. Every
statement carries a timecode, so you can open the video at that second and confirm
it yourself.

It runs on your own computer. The transcript step needs no internet and no account
of any kind.

> **This is a drafting aid, not a certified transcript.** Speech recognition
> mishears words, especially names and numbers. Read the output and check it
> against the recording before you rely on it for anything that matters.

---

## What it does

- Pulls the sound out of the video as an **MP3** you can play anywhere.
- Writes a **transcript** that labels each voice `Person1`, `Person2`, `Person3`,
  and stamps every turn with a timecode in the form `[HH:MM:SS]`.
- Produces **SRT subtitles** that load in any video player.
- Optionally writes a **chronological account of the video**. An AI reads frames
  from the video and combines what it sees with what was said, so readable text on
  uniforms, signs and papers ends up in the written record.
- Puts everything in one folder per video, with a plain-language note explaining
  what each file is.
- **Tells you when the speaker separation looks unreliable**, instead of quietly
  guessing.
- Runs on Windows, macOS and Linux. Installer scripts are included.

## What it is not

It is not a certified transcript and it is not a substitute for a court reporter.
The speaker separation can split one voice into two in a noisy recording. Check
the output against the video before filing it, quoting it, or relying on it in any
formal proceeding.

---

## Getting started

### 1. Install

| Your computer | What to do |
|---|---|
| **Windows** | Double-click **`init.cmd`** |
| **macOS / Linux** | Open a terminal in this folder and run **`./init.sh`** |

The installer checks what you already have and installs only what is missing:
Python, ffmpeg, and a few Python packages. It takes a few minutes the first time
and prints what it is doing at every step.

### 2. Put your videos in the `inbox` folder

Copy or drag them in. Supported formats: mp4, mkv, avi, mov, wmv, flv, webm, m4v,
mpg, mpeg, ts, 3gp.

### 3. Run it

| Your computer | What to do |
|---|---|
| **Windows** | Double-click **`run.cmd`** |
| **macOS / Linux** | Run **`./run.sh`** |

A menu appears:

```
 WHAT WOULD YOU LIKE TO DO?
======================================================================
  1) Transcript only            audio to text, with who said what
  2) Transcript + description   also describe what is seen on screen
  3) Check my computer          what is installed, which model fits
  4) Quit
```

Pick `1` or `2`. The program then shows you what your computer can handle, lets
you choose how accurate you want the transcript to be, tells you how long it will
take, and asks before starting.

### 4. Collect your results

Everything lands in `output/<name of your video>/`:

| File | What it is |
|---|---|
| `00_READ_ME_FIRST.txt` | A plain-language guide to this folder |
| `01_audio.mp3` | The sound of the video on its own |
| `02_transcript.txt` | Who said what, with the time of each turn |
| `03_subtitles.srt` | The same text as subtitles; open it with the video |
| `04_narrative.txt` | The written account of the video *(option 2 only)* |
| `05_narrative_by_section.md` | The same account, split into short sections |
| `data/` | Machine-readable files; keep these to re-run a step later |
| `work/` | Temporary files; safe to delete |

---

## What the output looks like

The examples below are invented, not real case material.

**`02_transcript.txt`**

```
[00:03:48] Person1:
    En el recibo me aparecen dos mil pesos de recargo y en la ventanilla
    me dijeron otra cifra; quiero que me expliquen de dónde sale.

[00:04:05] Person2:
    El recargo se calcula por trimestre vencido, señora. Le imprimo el
    desglose y si está mal, aquí mismo se lo corregimos.
```

**`04_narrative.txt`** — this is the part that makes it more than a transcript:

> Frente a la ventanilla aparece sentada una persona con playera blanca bajo un
> chaleco verde olivo. El bordado se alcanza a leer parcialmente como
> "...ano de Tal", "...ección De Parques" y "H. AYUNTAMIENTO DE VILLA EJEMPLO
> 2018-2021" `[00:04:20]`. En `[00:06:05]` se ve un papel con anotaciones
> manuscritas que aparentemente muestran cifras como "$1,780", coincidiendo con la
> conversación sobre montos.

Note what it is doing: quoting the text it can read, saying "parcialmente" and
"aparentemente" where it is unsure, and attaching a timecode to each observation so
you can check it.

---

## Choosing how accurate the transcript should be

Bigger models make fewer mistakes and take longer. Run this to see timings measured
for *your* computer:

```
python videoscribe.py models
```

Rough guide for **one hour of video on a 16-core laptop with no graphics card**:

| Model | Time | Download | When to use it |
|---|---|---|---|
| `tiny` | ~6 min | 75 MB | A quick look to see if the audio is usable |
| `base` | ~10 min | 145 MB | Still rough |
| `small` | ~22 min | 480 MB | **Default.** Good balance |
| `medium` | ~58 min | 1.5 GB | Clearly better with names and figures |
| `large-v3` | ~3 hours | 3.1 GB | Best available; painful without a graphics card |

A graphics card makes this several times faster. VideoScribe detects one
automatically and recommends a larger model when your machine can handle it.

**On a multi-core CPU the recording is split and transcribed in parallel.** Whisper's
own threading stops helping past about four cores, so the rest would sit idle. The
cuts land in silences, never mid-word, and a recording with no usable silence is
transcribed in one piece instead. Measured on 8 minutes of audio, 16 cores:
2:44 in one part, 1:41 in two, 1:37 in four. It happens automatically; set
`transcription.workers` to 1 to turn it off.

---

## If the speakers come out wrong

This is the weakest part of the tool, and it will tell you when it is unsure:

```
! The voices did not separate cleanly (best score 1.22, where 1.00 means no
  structure at all). Treat the speaker labels as a rough guide.
```

The fix is quick. If you know how many people are speaking, say so:

```
python videoscribe.py run --speakers 2 --resume
```

`--resume` reuses the transcript that was already produced, so this takes seconds
rather than repeating the whole run.

**Why it is limited:** speakers are separated using acoustic features (voice timbre
and pitch) with clustering, written in NumPy. This is why installation is a single
`pip install` with no account and no licence to accept. It is genuinely weaker than
a trained neural speaker model, and it struggles when several similar voices talk
in a noisy room. See [`docs/ACCURACY.md`](docs/ACCURACY.md) for the detail.

---

## Describing what is on screen

The transcript needs nothing but your own computer. The **visual description** needs
an image-capable model. You have five options, and any one of them works:

| Option | What you need | Cost |
|---|---|---|
| **Claude Code CLI** | Install it from [claude.com/claude-code](https://claude.com/claude-code) and sign in once | Included in a Claude subscription |
| **Anthropic API** | `ANTHROPIC_API_KEY` in your `.env` | Pay per use |
| **OpenAI API** | `OPENAI_API_KEY` in your `.env` | Pay per use |
| **Google Gemini** | `GEMINI_API_KEY` in your `.env` | Free tier available |
| **A model on your own computer** | [Ollama](https://ollama.com) installed | Free, and nothing leaves the machine |

If none is set up, the menu offers all four and can paste an API key into `.env` for
you, or download the local model. You never have to edit a file by hand.

**About the local option.** It is the only one that sends nothing over the internet,
which may decide the matter for confidential footage. Be aware of the trade: a 3-billion
parameter model reads a large sign reliably but is markedly worse at the small
embroidered text on a uniform, and on a CPU it takes roughly 25 seconds per frame
against a second or two for a cloud model. The menu tells you the estimate for your
video before you commit.

VideoScribe finds whichever you have and uses it. Check with
`python videoscribe.py doctor`.

> **Privacy note.** The transcript never leaves your computer. The visual
> description does send video frames to whichever provider you choose. If the
> footage must not leave your machine, use option 1 with a transcript only, or
> leave the description switched off.

### Cost and detail

One frame every 10 seconds is the default. For a 50-minute video that is about 300
frames, roughly 600,000 tokens of input. To halve it:

```
python videoscribe.py run --describe --frame-interval 20
```

---

## Settings

Three places, each overriding the one before it:

1. **`config.json`** — the shared defaults. Edit this to change them for everyone
   using this copy.
2. **`.env`** — your own machine. Copy `.env.example` to `.env` and edit. Never
   committed to version control, so this is where API keys belong.
3. **Command line** — wins over both. `--model medium`, `--speakers 2`, and so on.

> **Language.** The default is Spanish (`es`), because that is what this tool was
> built and tested against. Change `transcription.language` in `config.json` to
> `en`, `pt`, `fr`, or `auto` to detect it. Getting this wrong is the most common
> cause of a bad first result.

---

## Command line

The menu covers the common cases. For everything else:

```bash
python videoscribe.py                       # the menu
python videoscribe.py run                   # everything in inbox/
python videoscribe.py run --describe        # also describe the picture
python videoscribe.py run --file talk.mp4 --model medium
python videoscribe.py run --speakers 2 --resume
python videoscribe.py run --start 00:12:00 --duration 00:03:00   # a sample
python videoscribe.py doctor                # what is installed, what fits
python videoscribe.py models                # models timed for this computer
```

Taking a three-minute sample first, with `--start` and `--duration`, is the
cheapest way to check that the language and audio quality are good enough before
committing to a long run.

### PowerShell

Windows users who prefer PowerShell have native wrappers with tab completion:

```powershell
.\powershell\Transcribe.ps1 -Model medium -Speakers 2
.\powershell\Narrate.ps1 -Resume
Get-ChildItem C:\cases\*.mp4 | .\powershell\Transcribe.ps1
```

These call the same engine, so both front ends always agree.

---

## Who this is for

Anyone who needs a video in writing, and needs to be able to point at the moment a
statement was made:

- **Lawyers** — depositions, hearings, recorded confrontations, body-cam footage
- **Journalists and investigators** — interviews, press conferences, source material
- **Insurance and HR investigators** — recorded statements and incident footage
- **Researchers** — qualitative interviews and field recordings
- **Accessibility work** — subtitles, and descriptions of what happens on screen

---

## Frequently asked questions

### How do I transcribe a video to text for free?

Run the installer for your system, drop your video into `inbox/`, and run it. The
transcript, MP3 and subtitles land in `output/<video name>/`. The tool is free and
open source, and transcription costs nothing to run because it happens on your own
computer.

### Can I transcribe a video without uploading it to the cloud?

Yes, for the transcript. Speech recognition runs locally on your CPU or GPU. After
the model downloads once, it needs no internet and no account. The exception is the
optional visual description, which does send frames to whichever image model you
configure.

### How do I get a transcript that shows who is speaking?

VideoScribe does this automatically, labelling voices `Person1`, `Person2` and so
on in the order they first speak. If you already know how many people are in the
recording, tell it: `--speakers 3` is noticeably more reliable than the automatic
estimate.

### How accurate is automatic speaker identification?

Limited, and honest about it. It can split one person's voice into two in a noisy
recording, and it warns you in the output when the voices did not separate cleanly.
See [`docs/ACCURACY.md`](docs/ACCURACY.md).

### Can AI describe what happens in a video, not just what is said?

Yes, as an optional step. An image model reads frames and combines what it sees —
clothing, badges, signs, documents, readable text — with the transcript. Every claim
carries a timecode so you can check it.

### How long does it take to transcribe a one-hour video?

In a measured run, 50 minutes of video took about 21 minutes on a 16-core CPU with
no graphics card, using the `small` model. Run `python videoscribe.py models` for an
estimate on your own machine.

### Do I need a graphics card?

No. The defaults are tuned for a CPU-only machine. A graphics card makes it faster
and lets you use a larger model comfortably.

### Is an AI-generated transcript admissible in court?

Treat this as a drafting aid. VideoScribe is not a certified transcript and makes no
claim about admissibility. A human must verify the output against the recording
before it is used in any formal proceeding. The timecode on every line exists
precisely so that checking is quick.

---

## How it works

```
video file
    |
    +-- ffmpeg ------------> MP3 (for you) + 16 kHz WAV (for the models)
    |
    +-- faster-whisper ----> text segments with times
    |
    +-- MFCC + pitch ------> features per segment
    |     + clustering       -> Person1, Person2, ...
    |
    +-- ffmpeg ------------> one frame every N seconds        (optional)
    |
    +-- image model -------> a paragraph per two minutes      (optional)
    |
    +-- image model -------> one continuous account           (optional)
```

Two design decisions worth knowing about:

**Timecodes are truncated, never rounded.** At second 40.7 the label is `00:00:40`,
not `00:00:41`, because 41 might already be the next sentence. Every timecode points
at the source video, even when only a stretch of it was processed.

**Invented timecodes are removed.** Language models estimate times when asked to cite
them. Every `[HH:MM:SS]` the image model writes is checked against the real frame and
transcript times for that stretch, and deleted if it does not match. A wrong timecode
is worse than none: it sends a reader to the wrong minute.

---

## Requirements

- Python 3.9 or newer
- ffmpeg -- and if it is missing, the program offers to install it, including a
  portable copy that needs no administrator rights
- About 2 GB of disk space for the default model
- For the visual description only: one of the four image model options above

The installers handle all of this.

## Documentation

- [`docs/ACCURACY.md`](docs/ACCURACY.md) — what to trust, what to check, and why
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — every setting explained
- [`tests/README.md`](tests/README.md) — how the container tests work
- [`CLAUDE.md`](CLAUDE.md) — notes for AI coding assistants working on this repo

## Tests

Startup and menu behaviour are checked on Linux inside a container, so the
result does not depend on the machine running them:

```bash
bash tests/run_container_tests.sh      # needs podman, or ENGINE=docker
```

31 checks covering imports, tool discovery, the shell scripts, line endings, and
every path through the menu. They do not transcribe anything, so they finish in
seconds.

## Licence

MIT. See [`LICENSE`](LICENSE).

# VideoScribe — offline video and audio transcription with timestamps and speaker labels

**English** · [Español](README.es.md)

**Turn a video or an audio recording into a searchable, timestamped transcript —
who said what, at what second — entirely on your own computer. No account, no
upload, no cloud.**

You have a recording. You need it in writing. VideoScribe takes a video or audio
file and gives you back a transcript, with a timestamp on every line and a label
for each speaker. It can also write an account of what the camera shows: what
people are wearing, what is written on a badge or a sign, what document changes
hands, and when. Every statement carries a timestamp, so you can open the
recording at that second and confirm it yourself.

Speech recognition runs **fully offline** on your own CPU or graphics card, using
OpenAI's Whisper through [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
After the model downloads once, the transcript step needs no internet and no
account of any kind.

> **This is a drafting aid, not a certified transcript.** Speech recognition
> mishears words, especially names and numbers. Read the output and check it
> against the recording before you rely on it for anything that matters.

---

## What it does

- Accepts **video or audio**: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm` and the rest,
  plus `.mp3`, `.wav`, `.m4a`, `.flac` and other audio formats. A Zoom, Teams or
  Meet recording works as it comes.
- Pulls the sound out as an **MP3** you can play anywhere.
- Writes a **transcript** that labels each voice `Person1`, `Person2`, `Person3`,
  and stamps every turn with a timestamp (timecode) in the form `[HH:MM:SS]`.
- Produces **SRT subtitles** that load in any video player.
- Runs **fully offline** after the first model download — no internet, no account,
  nothing uploaded.
- Optionally writes a **chronological account of the video**. An AI reads frames
  from the video and combines what it sees with what was said, so readable text on
  uniforms, signs and papers ends up in the written record.
- Puts everything in one folder per recording, with a plain-language note
  explaining what each file is.
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

### 2. Put your recordings in the `inbox` folder

Copy or drag them in.

- **Video:** mp4, mkv, avi, mov, wmv, flv, webm, m4v, mpg, mpeg, ts, 3gp
- **Audio:** mp3, wav, m4a, aac, ogg, opus, flac, wma, aiff

Audio files work exactly like video, minus the description of what is on screen.

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
  4) Language                   currently: English
  5) Quit
```

If no image model is set up, option 2 is shown as *not available* and picking it
explains what is missing. The transcript never depends on one.

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

**Why it is limited:** speaker diarization here uses acoustic features (voice
timbre and pitch) with clustering, written in NumPy. This is why installation is a
single `pip install` with no account and no licence to accept. It is genuinely
weaker than a trained neural speaker model, and it struggles when several similar
voices talk in a noisy room. See [`docs/ACCURACY.md`](docs/ACCURACY.md) for the
detail.

---

## Describing what is on screen

The transcript needs nothing but your own computer. The **visual description** needs
an image-capable model. Any one of these works, and you only need one.

### What each option needs

| Option | How to connect it | Cost |
|---|---|---|
| **Google Gemini** | Sign in at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) with your ordinary Google account, click *Create API key*, paste it in | Has a free tier |
| **Claude Code CLI** | Install from [claude.com/claude-code](https://claude.com/claude-code), run `claude` once and sign in | Included in a Claude subscription |
| **Anthropic API** | Create a key at [console.anthropic.com](https://console.anthropic.com/settings/keys) | Pay per use, needs credit on the account |
| **OpenAI API** | Create a key at [platform.openai.com](https://platform.openai.com/api-keys) | Pay per use, needs credit on the account |
| **A model on your own computer** | Install [Ollama](https://ollama.com); VideoScribe offers to download the model | Free, and nothing leaves the machine |

**You do not have to edit any file.** Run `python videoscribe.py`, choose the
description option, and the menu asks which provider you have, takes the key, and
writes it to `.env` for you. The key is typed hidden, and `.env` is never committed.

If you would rather do it by hand, one line in `.env` is enough:

```
GEMINI_API_KEY=...
```

Check what was found with `python videoscribe.py doctor`.

### If you have none of them

**Start with Gemini.** It has a free tier, the key takes about a minute to get, and
it needs nothing but the Google account you already have. A Claude subscription is
not required to use this tool — the Claude Code option is there for people who
happen to have one already.

### Can I sign in with a Google account instead of pasting a key?

In practice that is what the Gemini option already is: you sign in with your Google
account at AI Studio and click a button. What comes back is called an API key rather
than a login, but nothing else about the flow is different, and there is no billing
setup for the free tier.

Full OAuth is not worth building here. Google's OAuth path for models is Vertex AI,
which needs a Google Cloud project, a billing account and the `gcloud` tool — strictly
more work than pasting a key. And for a program that runs on your own machine, OAuth
means shipping a client secret inside a public repository and running a small web
server to catch the redirect: more that can break, for the same requirement of having
an account.

**Hugging Face** is not supported today. It would also be a token pasted into `.env`
rather than a sign-in, so it would not avoid the step you are trying to avoid. It is
a reasonable option to add if you want a free provider that is not Google — ask.

### About the local option

It is the only one that sends nothing over the internet, which may decide the matter
for confidential footage. Be aware of what it costs, measured on a 16-core machine
with no graphics card:

- **Speed.** About 80 seconds per frame, which at the default of one frame every
  10 seconds is roughly **8 times the length of the recording**. A one-hour video
  takes most of a day. A graphics card is roughly ten times faster.
- **Small print.** It read the embroidered town name on a uniform correctly, but
  paraphrased the line above it and did not attempt the wearer's name underneath.
- **Timecodes.** In testing it wrote **none at all**, although the prompt asks for
  them. Since the whole point of the account is being able to check a claim against
  the video, this is the reason it is not offered as the default on a machine without
  a graphics card.

The menu and `doctor` both tell you which of these applies to your computer before
you commit to anything.

> **Privacy note.** The transcript never leaves your computer, whichever option you
> pick. The visual description does send video frames to whichever provider you
> choose. If the footage must not leave your machine, use the local model, or ask
> for a transcript only and leave the description switched off.

### Cost and detail

One frame every 10 seconds is the default. For a 50-minute video that is about 300
frames, roughly 600,000 tokens of input. To halve it:

```
python videoscribe.py run --describe --frame-interval 20
```

With the local model you do not need to tune anything: it works out how many frames
its own context window and your processor can handle, shortens the sections to match,
and says on screen that it did so.

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

### Who it works well for, and its known limitations

Most tools only tell you the first half. Here is both, so you can decide before
you spend an hour transcribing.

**Served well.** A small or medium practice, on ordinary office hardware, working
in Spanish or English, that needs a quotable transcript of a hearing, a
deposition or a meeting — and for whom it matters that the recording never
leaves the computer. That is the central case and it is covered solidly.

**Served partly.** Anyone who needs the written description of what is on
screen. Unless the machine has a graphics card, that part depends on an outside
provider. The transcript never does.

**Served badly, and worth saying plainly:**

- **Anyone who needs to know *with certainty* who spoke.** Speaker separation
  here clusters voices by MFCC and pitch, not by neural voice fingerprints. That
  is a deliberate trade so installation stays one `pip install` with no account
  and no licence to accept. The program reports a separation score with every
  run and warns you when it falls below 1.25, where 1.00 means the audio had no
  natural break at all and the speaker labels are close to arbitrary. With
  several similar voices in a noisy room, treat the labels as a rough guide and
  check them. The tool is honest about this; it is still the weakest thing it
  does. See [`docs/ACCURACY.md`](docs/ACCURACY.md).
- **Anyone who will never open a terminal.** Today that means double-clicking
  `run.cmd` and typing a number while reading a fixed-width table. It works, and
  people who have never used a command line do manage it, but it is the roughest
  edge on the whole product.

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

### Can I transcribe an audio file, not just a video?

Yes. Drop an `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.opus`, `.aac`, `.wma` or
`.aiff` into `inbox/` exactly as you would a video, or point at one directly with
`--file`. Everything works the same — transcript, speaker labels, timestamps,
subtitles. The only part that does not apply is the visual description, because
there is no picture; the program says so and carries on.

### Can I use this to transcribe a hearing or a deposition?

It is what the tool was built for. The whole point is that you can quote a
sentence and point at the exact second it was said, so anyone can check it by
typing that timestamp into a player. Read
[Who it works well for, and its known limitations](#who-it-works-well-for-and-its-known-limitations)
first: speaker separation is the weakest part, and in a room with several similar
voices you should tell it how many people there are with `--speakers`.

### Does it work with different accents?

Yes. The speech model was trained on many regional varieties and does not favour
one. What does change the result is the model size: `small` mishears proper names
and figures noticeably more than `medium`. If the recording contains names,
addresses or amounts that matter, use the largest model your computer can hold and
check those parts against the recording.

### Can I transcribe a Zoom, Teams or Google Meet recording?

Yes, as it comes. Those apps save `.mp4` video or `.m4a` audio, and both are
picked up without conversion. This is the usual route for remote depositions,
recorded interviews and HR meetings.

### Does it work offline, with no internet connection?

Yes, for the transcript, which is the main use. The speech model downloads once —
between 75 MB and 3.1 GB depending on which one you pick — and after that
everything runs on your own machine with no connection and no account. Only the
optional description of what is on screen needs the internet.

### Can I transcribe several recordings at once?

Yes. Put them all in `inbox/` and run once; each gets its own folder under
`output/`. On a machine with several cores, one recording is also split across
workers internally, which is why a 16-core machine is much faster than a 4-core one.

### How do I get the transcript into Word?

Open `02_transcript.txt` in Word directly — it is plain UTF-8 text and Word reads
it without any conversion. Use *File → Save As* if you want a `.docx`. The
subtitles file `03_subtitles.srt` is also plain text and opens the same way.

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

### The minimum, and what it gives you

| You need | And you get |
|---|---|
| Python 3.9 or newer | |
| ffmpeg — if it is missing, the program offers to install it, including a portable copy needing no administrator rights | **A transcript** with who said what and a timecode on every line |
| About 2 GB of disk for the default model | **Subtitles** as an `.srt` file |
| | A machine-readable `.json` of the same |

**That is the whole list.** No account, no API key, no card, and no internet
connection after the first run downloads the model. This is what most people
need, and it is the part that never sends your recording anywhere.

### To also describe what is on screen

This one part needs a model that can look at images, because nothing on your
computer can read a video frame on its own. Any **one** of these:

- **A Google Gemini API key** — free tier, needs only the Google account you
  already have. The quickest start if you have none of the others.
- **The `claude` command**, from [claude.com/claude-code](https://claude.com/claude-code),
  signed in once. Uses a Claude subscription you already pay for. (The back end
  runs the `claude` command, so it must be on your PATH — installing the
  command line tool is what puts it there.)
- **An Anthropic or OpenAI API key**, if you already have one. Both are pay per
  use and need credit on the account.
- **Ollama and a graphics card**, if the footage must not leave the machine at
  all. Read [About the local option](#about-the-local-option) first: without a
  graphics card it takes around eight times the length of the recording and
  writes no timecodes.

[How to connect each one](#what-each-option-needs) is a table further up.

### If you set none of them up

Nothing breaks and nothing is hidden. The menu shows the description option
marked *not available*, and picking it explains what is missing and offers to
set one up. Runs produce the transcript and subtitles as normal, and
`python videoscribe.py run --describe` says the description was skipped and
carries on rather than failing.

The installers handle everything in the minimum list.

## Documentation

- [`docs/ACCURACY.md`](docs/ACCURACY.md) — what to trust, what to check, and why
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — every setting explained
- [`tests/README.md`](tests/README.md) — how the container tests work
- [`CLAUDE.md`](CLAUDE.md) — notes for AI coding assistants working on this repo

## Tests and checks

Everything runs from one command:

```bash
pip install -r requirements-dev.txt
python scripts/check.py
```

That runs four things, and reports all four even if an earlier one fails:

| Check | What it covers |
|---|---|
| **unit tests** | 128 tests over the rules that must not break: timecodes truncate rather than round, every time refers to the source video, invented timecodes are stripped, settings precedence, and the limits of the local model |
| **code quality** | `ruff` — unused names, import order, likely bugs, style |
| **security (code)** | `bandit` — archive extraction, URL schemes, subprocess use |
| **security (dependencies)** | `pip-audit` — known vulnerabilities in what we install |

Run one group on its own with `python scripts/check.py tests`, `quality` or
`security`.

Startup and menu behaviour are additionally checked on Linux inside a container,
so the result does not depend on the machine running them:

```bash
bash tests/run_container_tests.sh      # needs podman, or ENGINE=docker
```

31 checks covering imports, tool discovery, the shell scripts, line endings, and
every path through the menu. Neither suite transcribes anything, so both finish
in seconds.

## Licence

MIT. See [`LICENSE`](LICENSE).

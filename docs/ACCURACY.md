# What to trust, and what to check

**English** · [Español](ACCURACY.es.md)

This page exists because the honest answer to "how accurate is it?" is "it depends,
and here is exactly where it fails". If you are going to quote this output in front
of a judge, a client or an editor, read this first.

## The short version

| Part of the output | Trust it? | What to do |
|---|---|---|
| **Timecodes** | Yes | They are computed arithmetically, not guessed |
| **Words spoken** | Mostly | Check names, figures and technical terms |
| **Who said it** | **Least reliable part** | Verify by ear before quoting |
| **What is visible** | Mostly | Check anything small: badges, print, figures |
| **Interpretation** | Marked as such | Read "apparently" as "the tool is guessing" |

---

## Timecodes

These are the one thing you can rely on, and the whole design is arranged around
keeping them that way.

- They are **truncated, never rounded**. Second 40.7 is labelled `00:00:40`, because
  `00:00:41` might already be the next sentence.
- They always refer to the **source video**, even when you processed only a stretch
  of it with `--start`. Type one into a player and you land on the right moment.
- Timecodes in the visual account are **checked against the real frame and transcript
  times** for that stretch. Any the model invented are deleted before you see them.

That last point matters. Language models estimate times when asked to cite them. In
testing, one run cited `[00:02:33]` for a line that was actually at `[00:01:38]`. The
validation now catches this; when it fires, you see a note saying how many were
removed.

---

## The words

Speech recognition quality depends on the model you chose, the audio, and the
language setting.

**What it gets wrong, reliably:**

- **Proper names.** Almost always. A person's name heard once will usually be wrong.
- **Figures.** "1780" and "17" are easy to confuse; so are "el 12" and "el 13".
- **Overlapping speech.** When two people talk at once, one of them is usually lost.
- **Legal and technical vocabulary** not common in ordinary speech.
- **Repetition artefacts.** The model occasionally emits the same sentence twice at a
  silence boundary. If you see a line duplicated, check the audio before assuming the
  speaker repeated themselves.

**What helps:**

- Set the language explicitly rather than using `auto`. It is the single most common
  cause of a bad result.
- Use a bigger model. `medium` is noticeably better than `small` on names and
  figures, at about 2.6 times the time.
- Take a three-minute sample first (`--start` / `--duration`) to check the audio is
  usable before committing to a long run.

---

## Who said what

**This is the weakest part of the tool. Treat the speaker labels as a first draft.**

### How it works

Each speech segment is described by its acoustic features — the timbre of the voice
(MFCCs) and its pitch — and segments are then grouped by similarity. There is no
trained model of what a speaker sounds like; it is a statistical grouping of sounds.

### Why it is built this way

The alternative, a neural speaker embedding such as pyannote, is clearly better. It
also requires a separate model download, a Hugging Face account, and accepting a
licence before the tool will run at all. Keeping installation to one `pip install`,
with no account anywhere, was judged worth the accuracy cost for this audience.

This is a trade-off, not a claim that the current approach is good.

### When it fails

It works when voices are clearly different — a man and a woman in a quiet room. It
fails when:

- Several people have similar voices
- The recording is noisy, outdoors, or in a room with echo
- People are at different distances from the microphone
- Someone's voice changes register between calm and raised speech

The most common failure is **splitting one person into two labels**. In a real
50-minute recording tested during development, `Person1` and `Person3` turned out to
be the same person for long stretches.

### How you know

The tool tells you:

```
! The voices did not separate cleanly (best score 1.22, where 1.00 means no
  structure at all). Treat the speaker labels as a rough guide, and consider
  re-running with an explicit speaker count.
```

The score is the ratio between merge distances in the clustering. Near 1.00 means
the data had no natural break, so whichever number of speakers was chosen is close
to arbitrary. Above about 1.5 the split is meaningful.

### How to fix it

Tell it how many people are speaking:

```bash
python videoscribe.py run --speakers 3 --resume
```

`--resume` reuses the existing transcript, so this takes seconds. Try the number you
know to be correct; if you are unsure, try two or three values and read which one
produces sensible turn-taking.

---

## The visual account

### What it does well

In testing, it correctly read (the examples here are invented, not real case
material):

- `DIRECCIÓN DE PARQUES` lettering on a vehicle
- A licence plate
- A handwritten sign reading `Renta De Cancha $40`
- Embroidery on a uniform, quoted as partially legible: `"...ano de Tal"`,
  `"...ección De Parques"`
- A discrepancy nobody asked it to look for: the uniform said `2018-2021` while a
  wall sign said `2022-2025`

### What to check

- **Small print.** Badge names, document figures, anything at the edge of legibility.
  The model reports these as partial (`"...ana de Tal"`) when it is unsure, which is
  the behaviour you want, but the fragment it does report may still be wrong.
- **Anything it attributes to a specific person.** The model sees frames, not a
  continuous video, and cannot always tell who is speaking. Where the audio makes an
  accusation, the account should say it cannot link the words to anyone visible —
  and in testing it did — but check this every time.
- **Sampling gaps.** One frame every 10 seconds is the default. Anything that happens
  between two frames is invisible. If a document changes hands in three seconds, it
  may not appear at all. Lower `--frame-interval` for footage where brief actions
  matter.

### What "apparently" means

The prompts require the model to mark inference with "apparently" or "it seems".
When you see those words, read them as: *the tool is guessing, verify this*.

---

## A practical checklist before you rely on this

1. Open `02_transcript.txt` and skim for `Person` labels that alternate implausibly
   mid-sentence. That is the split-voice failure.
2. Search the transcript for every figure that matters and listen to that timecode.
3. Search for every proper name and listen. Assume it is wrong until you have heard
   it.
4. In `04_narrative.txt`, check every quoted piece of readable text against the
   video at its timecode.
5. Check anything marked "apparently", "it seems" or "parcialmente".
6. If the run printed a speaker-separation warning, do not quote speaker attribution
   without listening.

None of this takes long, because every line has a timecode. That is the point.

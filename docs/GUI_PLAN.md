# A desktop window for VideoScribe, built with CustomTkinter

This document works out what it would take to put a graphical front end on
VideoScribe, using CustomTkinter and the light lavender theme from
[CTkThemesPack](https://github.com/a13xe/CTkThemesPack).

It is a plan, not a decision. Nothing here has been built. The last section
lists the questions only the user can answer.

> **Note.** `CLAUDE.md` currently lists "No GUI" as a deliberate non-goal, on
> the grounds that the text menu covers non-technical users adequately. This
> document is a proposal to revisit that, not permission to ignore it. If the
> plan is accepted, that line in `CLAUDE.md` has to change with it.

---

## The short version

| Question | Answer |
|---|---|
| Is CustomTkinter the right tool? | Yes, with one large caveat below |
| Does it break "one `pip install`, no accounts"? | Not if the GUI is optional. It would if it were mandatory |
| How much of the existing code changes? | Very little. About 10 lines outside the new GUI package |
| Biggest risk | `tkinter` is not present on the machine as often as people assume |
| Effort | Roughly two weeks for one person, in four phases |
| Should it become a double-clickable `.exe`? | No, not yet. Extend the existing `run.cmd` instead |

**The caveat.** CustomTkinter needs `tkinter`, and `tkinter` is not a Python
package. `pip` cannot install it. It is a compiled module plus a Tcl/Tk runtime
that has to be present already. It usually is. It is not always.

We checked the Python on this machine:

```
C:\python\python.exe   3.14.3
>>> import tkinter
ModuleNotFoundError: No module named 'tkinter'
```

There is no `Lib\tkinter`, no `DLLs\_tkinter.pyd` and no `tcl\` folder in that
installation. This is a normal Windows Python from python.org with the optional
"tcl/tk and IDLE" component left unticked during setup. So the common claim that
"tkinter ships with Python on Windows" is not reliable, and the machine this
project is being developed on is itself a counter-example. Any plan that assumes
`tkinter` is there will fail on first launch, which is the worst possible moment.

---

## 1. Toolkit choice

### What CustomTkinter gives us

CustomTkinter draws modern-looking widgets on top of `tkinter`. Version 6.0.0
was released in June 2026. It is licensed CC0 / MIT, which sits fine next to this
repository's MIT licence. It depends only on `darkdetect` and `packaging`.

The things that matter here:

- **It is small.** About a megabyte, against the several hundred that
  `faster-whisper` already pulls in through `ctranslate2` and `onnxruntime`.
  Nobody will notice it in the download.
- **No account, no licence to accept, no model to fetch.** This is the property
  `CLAUDE.md` protects when it refuses to make `pyannote` a default. CustomTkinter
  does not threaten it.
- **It looks current.** That matters more than it sounds. The audience is lawyers
  deciding whether to trust an automated transcript. A window that looks like it
  was built in 1998 undermines that before they read a word of output.
- **The requested theme is a JSON file and applying it is one line.**

### What it costs

**1. The `tkinter` dependency is real and it is not a pip problem.**

| Platform | Situation |
|---|---|
| Windows | Bundled with the python.org installer, but as an **optional component** that can be, and on this machine was, left out |
| macOS | Present in python.org builds (Tk 8.6). The Apple system Python ships an old Tk 8.5 with known bugs |
| Debian / Ubuntu | **Missing by default.** Needs `python3-tk` |
| Fedora / RHEL | **Missing by default.** Needs `python3-tkinter` |
| Arch | **Missing by default.** Needs `tk` |

The failure mode on Linux is nasty: `pip install customtkinter` **succeeds**, and
then the program fails at import. The user did everything right and got an error
anyway.

**2. Accessibility is poor.** CustomTkinter paints its widgets onto a `tkinter`
Canvas. They are not native controls, so a screen reader sees almost nothing.
The README lists "Accessibility work" as one of the audiences for this tool.
Handing that audience a front end their screen reader cannot read would be an
uncomfortable irony. The console front end is, as it happens, far better in this
respect, which is one more reason to keep it.

**3. The release history is bursty.** Version 5.2.2 was January 2024. Version
6.0.0 was June 2026. Two and a half quiet years, then a major version. It is
healthy now. It has not always been.

**4. A major version bump raises a question we could not answer.** The lavender
theme in CTkThemesPack was written for the 5.x theme format. We could not find
release notes for 6.0.0 to confirm the theme JSON schema is unchanged. This needs
ten minutes of hands-on checking before anything else is built. See Phase 0.

### Alternatives weighed

**Plain `tkinter` / `ttk`.** Adds no dependency at all and has better screen
reader support, because `ttk` widgets are native on Windows and macOS. But it
does not solve the actual problem: the risk is `tkinter` being absent, and plain
`tkinter` has that risk in full. It also cannot produce the requested lavender
look without a great deal of manual styling. It gives up the appearance and keeps
the risk, so it is strictly worse here.

**PySide6 / Qt.** The strongest alternative. Genuinely native widgets, proper
accessibility, a real threading model built in (`QThread` and signals, instead of
hand-rolled queues), excellent high-DPI handling, and by far the best story if a
frozen executable is ever wanted. The costs are a roughly 120 MB wheel and the
LGPL, which is fine for this use but is one more thing to explain. The size
argument is weaker than it first appears given what `faster-whisper` already
downloads. **If accessibility or a double-clickable installer become priorities,
Qt is the better long-term answer.** For the job as described today, it is more
machinery than the problem needs.

**A local web page.** Serve a small page from the standard library's
`http.server` and open the browser. Zero new dependencies, works anywhere Python
works, no `tkinter` at all, perfect accessibility, and lavender is trivial in
CSS. It preserves "one `pip install`" completely. The cost is that it is a
server: a port to pick, a firewall prompt on some machines, and a user experience
that reads as "a website" rather than "a program", which some of this audience
will find more confusing rather than less. Worth naming honestly, because it is
the only option that adds nothing to the install at all.

**Verdict.** CustomTkinter, on two conditions:

1. **It is an optional extra, never a hard requirement.** `requirements.txt` stays
   exactly as it is. Add a separate `requirements-gui.txt`. Anyone who does not
   want the GUI keeps today's install unchanged, and the "one `pip install`, no
   accounts" property survives intact for them.
2. **`tkinter` is checked before anything else**, in the installers and again at
   `--gui` startup, with a message that says what to run to fix it.

---

## 2. The lavender theme

### What was verified

We fetched the repository and the theme file directly.

| Item | Finding |
|---|---|
| File name | `themes/lavender.json` |
| Repository | `https://github.com/a13xe/CTkThemesPack`, default branch `main` |
| Licence | **The Unlicense** (public domain). Confirmed via the GitHub API: `spdx_id: "Unlicense"` |
| Light and dark | One file contains both. Every colour is a two-element array `[light, dark]` |
| How it is applied | `customtkinter.set_default_color_theme("path/to/lavender.json")` |

The accent colours are `#B19CD9` for light mode and `#9370DB` for dark, with
`#7A5DC7` as the dark-mode hover. Backgrounds are Tk's named greys: `gray92`
for the window in light mode, `gray86` for frames.

**The theme must be vendored into the repository, not fetched at run time.** The
Unlicence permits this, and it removes a network dependency from application
startup. Copy it to `videoscribe/gui/themes/lavender.json` and record where it
came from in a comment.

### Two defects that have to be fixed

The theme is designed dark-first. In light mode two of its colour pairs fail
badly. These are measured WCAG contrast ratios, computed from the exact values in
the file:

| Element | Colours | Ratio | Needs | Verdict |
|---|---|---|---|---|
| Button label | `#DCE4EE` on `#B19CD9` | **1.90:1** | 4.5:1 | Fails badly |
| Progress bar fill | `#B19CD9` on `#939BA2` | **1.16:1** | 3:1 | Nearly invisible |
| Body text | `gray10` on `gray92` | 14.60:1 | 4.5:1 | Fine |
| Entry text | `gray10` on `#F9F9FA` | 16.54:1 | 4.5:1 | Fine |

The progress bar one matters most. The main screen of this application is a
progress display that a user watches for twenty minutes or more. In light mode
the theme's default renders it as pale lavender on mid grey, which is very nearly
no contrast at all.

Proposed overrides, staying within the theme's own palette:

| Element | Change | New ratio |
|---|---|---|
| `CTkButton.text_color` light | `#DCE4EE` → `gray10` | 7.15:1 |
| `CTkProgressBar.progress_color` light | `#B19CD9` → `#7A5DC7` | 3.60:1 |
| `CTkProgressBar.fg_color` light | `#939BA2` → `gray86` | (as above) |

The theme also defines no warning colour, and we need one. `#92400E` on the
`gray86` frame background gives 5.12:1 and reads as a warning without shouting.
Whatever is chosen, **the warning must never be signalled by colour alone** — it
needs an icon and the word, because some readers are colour-blind and some will
print the screen.

Because these overrides exist, the sensible arrangement is to vendor the file and
edit it, keeping a short note at the top of the GUI theme module recording what
was changed and why.

### Light mode has to be forced

The colour arrays are `[light, dark]` and CustomTkinter picks between them
according to the current appearance mode, which by default follows the operating
system through `darkdetect`. A user with Windows set to dark mode would get the
dark lavender, not the light lavender that was asked for. So the GUI must call
`set_appearance_mode("Light")` explicitly at startup rather than relying on the
default.

Whether it should *stay* forced, or offer a dark mode too, is a question for the
user. See the end of this document.

---

## 3. Architecture

### The pipeline is already in good shape for this

This is the most encouraging finding in the whole exercise. `pipeline.py`
communicates with the outside world through exactly seven things on `Reporter`:

```
reporter.total_steps      set once
reporter.banner(...)      framing
reporter.step(...)        announce a numbered step
reporter.detail(...)      a note under the current step
reporter.warn(...)        something the user must read
reporter.done(...)        a result line
reporter.bar(total, unit) a progress bar, used as a context manager
```

It never writes to a stream itself. It never calls `print`. It never asks the
user anything. **Every question in the current program is asked before
`process_video` is called, and none during it.** That means a GUI does not have
to plumb mid-run prompts back to the UI thread, which is normally the hardest
part of this kind of work.

So the job is not to restructure the pipeline. It is to write a second
implementation of a small interface that already exists in all but name.

### The Reporter split

`progress.py` today has one concrete `Reporter` that writes to a `TextIO`, and a
`ProgressBar` that reaches into `reporter._write` and `reporter._redraw`. Those
two private members are the only console-specific things in the file.

Proposed shape:

```
progress.py
    class Reporter(ABC)          the seven-item interface above
    class ProgressHandle(ABC)    update / advance / close / context manager
    class ConsoleReporter(Reporter)   today's class, renamed, behaviour unchanged
    class ConsoleBar(ProgressHandle)  today's ProgressBar, renamed
    class QueueReporter(Reporter)     new: puts messages on a queue.Queue
    class QueueBar(ProgressHandle)    new
    class Cancelled(BaseException)    new, see below
```

`QueueReporter` **must not import `customtkinter` or `tkinter`.** It only knows
about `queue.Queue`. Every method turns its arguments into a small plain record
and puts it on the queue. That keeps it testable without a display, and it makes
the threading rule below mechanically enforceable.

### Threading

`tkinter` is not thread-safe, and the way it fails is unpleasant: not a clean
exception, but rare non-deterministic crashes and hangs that will not reproduce
under a debugger. So one rule, without exceptions:

> **No code on the worker thread may touch a widget.** All communication is one
> `queue.Queue` in one direction.

The arrangement:

- One worker thread runs the whole batch, calling `process_video` per video in
  sequence. Do not add a thread per video. `faster-whisper` already parallelises
  internally through `plan_worker_count`, and stacking another layer on top would
  fight it for cores.
- The worker gets a `QueueReporter`. Nothing else.
- The UI thread drains the queue on a timer, `root.after(100, drain)`, and
  updates widgets from what it finds.
- Because `QueueReporter` cannot import `tkinter`, the rule can be checked by a
  test rather than by review discipline.

Two other things belong on the worker thread, which is easy to overlook:

- **`total_audio_seconds()` runs `ffprobe` on every video.** On a large inbox that
  is seconds of blocking work, and the model chooser cannot be drawn until it
  finishes. It must not run on the UI thread.
- **`profile_machine()`** shells out to `nvidia-smi` with a 15-second timeout when
  a driver is present. Same treatment.

### Cancellation

There is no Ctrl-C in a GUI, so cancellation has to be cooperative.

- Add `Cancelled` to `progress.py` and a `check_cancelled()` method on the
  interface. On `ConsoleReporter` it does nothing. On `QueueReporter` it raises
  `Cancelled` when a flag set by the UI thread is up.
- Call it at the top of `Reporter.step()`, which already runs five to eight times
  per video, and inside the per-window narration loop, which is the longest
  stretch of repeated work.
- **`Cancelled` must derive from `BaseException`, not `Exception`.** `pipeline.py`
  line 331 catches bare `Exception` inside the narration loop, deliberately, so
  that one bad window does not kill the run. That handler would silently swallow
  a cancellation and carry on. This is a specific, predictable bug and it is worth
  writing the plan down so it is avoided rather than debugged. The same applies to
  the `except Exception` in `menu.py` around `process_video`.

**Stop means "stop at the next checkpoint", and the button must say so.** Whisper
is a C extension; a transcription segment already in flight cannot be interrupted.
The honest interface is a Stop button that changes to "Stopping…" and explains
that the current step will finish first.

The good news is that the recovery story already exists and is well tested:
`--resume` reuses whatever was completed. So Stop leaves usable partial work, and
a later run picks it up. The GUI should say that in as many words when a run is
stopped, rather than implying the work was lost.

### What changes, and by how much

| File | Change | Size |
|---|---|---|
| `videoscribe/progress.py` | Split into interface plus console and queue implementations. Console behaviour unchanged | ~120 lines added |
| `videoscribe/pipeline.py` | One line for the default reporter, a few `check_cancelled()` calls, and re-raise `Cancelled` past the two broad `except Exception` handlers | ~6 lines |
| `videoscribe/cli.py` | One line for the renamed console class, plus a `--gui` branch | ~8 lines |
| `videoscribe/menu.py` | One line for the renamed console class. Otherwise untouched | 1 line |
| `videoscribe/i18n.py` | New `gui.*` message keys. Additive only | ~40 entries |
| `videoscribe/vision.py` | Only if we want a real progress bar for the Ollama pull, see below | ~30 lines |
| `videoscribe/gui/` | New package | The bulk of the work |
| `requirements-gui.txt` | New file. `requirements.txt` is **not** touched | 2 lines |
| `init.sh`, `init.ps1`, `init.cmd` | Check for `tkinter`, offer to install it | ~30 lines each |
| `tests/` | Container needs `python3-tk`; add a headless import test | small |

**Files that do not change at all:** `system.py`, `install.py`, `audio.py`,
`diarize.py`, `features.py`, `transcribe.py`, `narrate.py`, `writers.py`,
`timecode.py`, `tools.py`, `parallel.py`, `config.py`.

`install.py` deserves a specific note, because it was singled out for review. It
needs **no changes at all**: `install_portable(on_message, on_progress)` and
`install_with_package_manager(on_message)` already take callbacks, so the GUI
passes its own and gets the download progress for free. That is good design
paying off.

### Three subprocess traps

These are the parts most likely to be missed, because they work perfectly in a
console and silently break in a window.

1. **`install_with_package_manager` runs `subprocess.run(command)` with inherited
   stdio.** Under a GUI with no console attached, `sudo apt-get` prompts for a
   password that the user cannot see and the program waits forever. The fix is
   either to prefer the portable route on Linux and macOS, or to run the package
   manager in a visible terminal window. The portable route is better anyway for
   this audience: it needs no administrator rights, which a lawyer on a managed
   work laptop usually does not have.
2. **`setup_local_vision` runs `subprocess.run(["ollama", "pull", model])` with
   inherited stdio.** That is a 3.2 GB download whose progress would be completely
   invisible. Ollama's HTTP API has a `/api/pull` endpoint that streams JSON
   progress, and `vision.py` already has the machinery to talk to it. This is the
   one small addition to `vision.py` mentioned in the table above.
3. **`pythonw.exe` on Windows has no stdout.** Launching the GUI with it to avoid
   a console window flash means every stray `print` in the codebase — and
   `menu.py` is full of them — is writing to a closed handle. Safer to launch with
   `python.exe` from the existing `.cmd` and accept the console window, or to
   redirect the streams explicitly at startup.

---

## 4. Screens

Every screen in the current text menu, and what replaces it.

| # | Console screen | Where it lives | GUI equivalent |
|---|---|---|---|
| 1 | First-run language picker | `choose_language(first_run=True)` | Modal dialog before the main window. Bilingual in itself |
| 2 | Main menu | `run_menu` loop | The main window: inbox list, output path, four actions |
| 3 | ffmpeg missing, install offer | `offer_to_install_ffmpeg` | Modal, blocking. Options with sizes, sources and admin markers, then a download bar |
| 4 | Machine report | `show_machine` | A panel: cores, memory, disk, graphics card, recommended model and the reason |
| 5 | Environment check | `show_environment` | Two tables: required programs, image models. Plus the settings dump |
| 6 | "How should the video be described?" | `setup_vision` | Modal with the four options, each with its own cost and privacy note |
| 7 | API key prompt | `ask_for_api_key` | Modal. Provider list with links, then a **masked** field |
| 8 | Ollama local setup | `setup_local_vision` | Modal: model, download size, the slowness estimate, then a real pull progress bar |
| 9 | Model chooser | `choose_model` | A table with per-video times, download sizes and markers |
| 10 | Run confirmation | `_start_run` | A summary panel: how many videos, which model, rough time, then Start |
| 11 | Per-step progress | `Reporter` | The main progress panel: 5 or 8 numbered steps, details, bars |
| 12 | Completion and warnings | `reporter.banner` plus the warning loop | Results panel: files produced, warnings, a button to open the folder |
| 13 | Language change | menu option 4 | Same dialog as 1, reachable from a settings button |
| 14 | Per-video failure | `app.could_not_process` | An error row against that video. The batch continues, as it does today |

**One screen not yet in the menu.** There is uncommitted work in the tree adding
a `videoscribe network` command, which reports which servers this computer can
actually reach and which are blocked. It is currently a CLI command only, with no
menu entry, so it is not in the table above. If it lands, it belongs in the GUI
next to the environment check at row 5 — arguably more so than in the console,
since "the download is stuck" is exactly the kind of problem a non-technical user
cannot diagnose. Worth confirming its status before Phase 3, which is where the
downloads live.

### The details that are easy to forget

**The API key must never be echoed.** The console uses `getpass`. The GUI
equivalent is an entry with `show="*"`. Beyond that: do not add a "reveal" toggle
by default, do not log the value anywhere, do not leave it in a widget after the
dialog closes, and write it only to `.env`. The console currently reassures the
user with "Saved in .env. It stays on this computer and is never committed." That
sentence must survive into the GUI. It is the reason a cautious user is willing to
paste the key at all.

**The model table must keep showing what will not work.** For a model too large
for the machine, `choose_model` prints a row with dashes and "too big for this
computer". A GUI's instinct is to hide those rows. It should not. Show them,
disabled, with the reason. Hiding them removes information the user is entitled
to, and it invites the question "why does this list have five entries on my
colleague's machine and three on mine?"

**Times are measured for the actual video, not for a nominal hour.** The comment
in `_start_run` is emphatic about this: quoting "about 19 minutes" for a
twenty-second clip destroys trust in every other number on screen. A GUI that
lets the user tick and untick individual videos must **recompute** the estimate
whenever the selection changes. That is a real behavioural difference from the
console, which measures the whole inbox once.

**The ffmpeg install flow reloads the configuration.** Lines 516 to 519 of
`menu.py` reload `Config` after a portable install, because the new path was
written to `.env`, while carefully preserving the chosen UI language across the
reload. The GUI has to do the same thing, and it is exactly the sort of four-line
subtlety that gets lost in a rewrite.

**The first-run language dialog has no "not a terminal" escape.** The console
skips it when stdin is piped, so automated runs are not left waiting. A GUI has
no equivalent situation. It should simply always ask on first run.

**Changing the language must redraw everything.** Because `t()` resolves at call
time and the console redraws the whole menu on every loop, the console gets this
for free. A GUI does not. The simplest and least bug-prone approach is to destroy
and rebuild the main frame on a language change, rather than trying to keep every
label bound to a variable.

---

## 5. Design rules the GUI must not break

`CLAUDE.md` rule 4 is the one at risk here. Graphical interfaces hide things by
design: tabs, collapsible panels, notifications that fade after four seconds. The
whole rule says uncertainty is surfaced rather than hidden. Concretely:

**The speaker-separation warning.** `DiarizationResult.quality_note()` fires when
the best separation score is below 1.25, and `pipeline.py` sends it to
`reporter.warn()` and appends it to `result.warnings`. In the console it is
impossible to miss: it is printed inline, marked with `!`, and shown even in quiet
mode. In the GUI it must be:

- A **persistent block in the results panel**, not a toast and not a notification.
  It cannot be auto-dismissed and it cannot be behind a tab.
- Marked with an icon **and** the word, never colour alone.
- Carrying the score, exactly as the console does. "Best score 1.22, where 1.00
  means no structure at all" is the sentence that lets a reader judge for
  themselves. Reducing it to "speaker labels may be unreliable" throws away the
  part that makes it checkable.
- Fully visible without truncation. The console wraps at 66 characters through
  `wrap()`. GUI labels need `wraplength` set and a window that can grow. **A
  truncated warning is a hidden warning.**

There is also an opportunity here that the console cannot take. The warning ends
with "consider re-running with an explicit speaker count". In a GUI that can be an
actual button — "Re-run with 2 speakers" — wired to `--speakers 2 --resume`,
which takes seconds rather than repeating the whole run. That turns a warning the
user has to act on into one they can act on in a click. That is a genuine
improvement over the console, not just parity.

**The disclaimer.** `file.disclaimer` goes into the header of every output file
and `readme.warning` into `00_READ_ME_FIRST.txt`. Both must stay exactly as they
are; they are written by `writers.py`, which does not change. On top of that, the
completion screen must show the disclaimer **visible without scrolling**. Not
behind a "?" icon, not in an About box, not in a tooltip. The user who is about to
email a transcript to a colleague is the person who needs to read it.

**Invented timecodes.** `detail.invented_removed` reports per window how many
fabricated timecodes were deleted. The GUI should total these and show the number
in the completion summary. Disclosing "4 invented timecodes were removed" builds
trust rather than damaging it, and quietly dropping the count would be against
the spirit of rule 3.

**Timecodes themselves.** Rules 1 and 2 are back-end concerns and the GUI cannot
break them — with one exception worth stating plainly, given the history recorded
in `CLAUDE.md` about PowerShell's rounding `[int]`:

> **The GUI must never compute or reformat a timecode.** It displays strings
> produced by `timecode.py` and nothing else.

It would be very easy for someone writing a progress label to reach for
`f"{m:02d}:{s:02d}"` with a `round()` in it and reintroduce, in the display layer,
the exact bug that took real effort to diagnose the first time.

**Translation.** Every visible string goes through `t()`, as `menu.py` does now.
New keys under a `gui.` prefix. No hardcoded English, including on buttons,
window titles, tooltips and error dialogs.

**Plain language.** The style rule says no jargon in error messages: say what went
wrong and what to do about it. That applies to dialogs too. "Tcl/Tk runtime not
found" is not acceptable; "The graphical interface needs an extra part of Python
that is not installed. Run `sudo apt install python3-tk` and start again" is.

---

## 6. Packaging

**The command line keeps working, unchanged, in every option below.** `menu.py`
is untouched, `cli.py` gains one branch, and the PowerShell wrappers call the same
engine as before.

### Option A: a flag. `python videoscribe.py --gui`

Cost: near zero. This should exist regardless of what else is decided. But on its
own it does not reach the audience, because the whole premise is that these users
will never open a terminal to type it.

### Option B: extend the existing double-click path. Recommended.

The README already tells users to double-click `run.cmd` on Windows or run
`./run.sh` elsewhere. That path exists and people already follow it. The cheapest
real win is to use it:

- `run.cmd` and `run.sh` open the GUI when it is available, and fall back to the
  text menu when it is not.
- Add a `run-gui.command` for macOS, which needs that extension to be
  double-clickable from Finder, and a `.desktop` file for Linux.
- Have `init.cmd` create a Start Menu or desktop shortcut. That gets a
  double-clickable icon with a proper name, which is most of what "feels like a
  real program" actually means to this audience, without freezing anything.

Cost: small, and no new tooling in the build.

### Option C: a frozen executable. Not recommended yet.

Worth being specific about why, because it sounds more attractive than it is.

- `faster-whisper` pulls in `ctranslate2`, `onnxruntime` and `tokenizers`, all
  with native binaries and data files. PyInstaller hidden-import and
  binary-collection problems are close to certain, and they are tedious.
- The result would be roughly 400 MB and **still not self-contained**: the Whisper
  model is not bundled, so the first run still downloads 480 MB into
  `~/.cache/huggingface`, and ffmpeg is still a separate program.
- An unsigned executable downloaded from the internet gets a SmartScreen warning
  on Windows, and on a managed corporate laptop it may be blocked outright by
  policy. For a user who cannot install software, that is **worse** than the
  current position, not better. Code signing removes the warning and costs money
  every year.

So freezing removes the Python installation step and nothing else, at
considerable cost and some risk of making things worse for exactly the users it
targets. Revisit it only if the Python install is measured to be the real
blocker. It probably is not; `init.cmd` already installs Python.

---

## 7. Effort and phases

Ordered so that something usable exists as early as possible, and so that the
part touching shared code lands on its own where it can be reviewed properly.

### Phase 0 — Check the assumptions. Half a day.

Before any code. Three things:

1. Install CustomTkinter 6.0.0 and confirm `lavender.json` still loads. If the
   6.0.0 theme schema changed, correct the vendored copy now rather than
   discovering it in Phase 2.
2. Confirm `tkinter` on each machine that matters, starting with the one this is
   developed on, where it is currently absent.
3. Apply the contrast fixes from section 2 and look at them on a real screen.

**Deliverable:** a vendored, corrected `lavender.json` and a go/no-go on the
toolkit.

### Phase 1 — The Reporter split. One to one and a half days.

Interface, `ConsoleReporter`, `QueueReporter`, `Cancelled`. Plus a small console
harness that runs `process_video` on a worker thread through the queue and prints
the result, proving the plumbing with no GUI and no new dependency.

**Deliverable:** no visible change, no new dependency, existing container tests
still green. This phase is worth landing even if the GUI is later abandoned,
because it makes the pipeline embeddable in anything.

### Phase 2 — A minimum usable window. Three to four days.

One window: the inbox list, a transcript-only button, the machine report, the
model chooser, the progress panel, the results panel with warnings, and Stop.
Light lavender applied. Language handling working.

**Deliverable, and the point of the whole exercise: a non-technical user can
produce a transcript without opening a terminal.**

### Phase 3 — The setup paths. Two to three days.

The screens that only appear when something is missing, which is to say the ones
that matter most for a first-time user: the ffmpeg install offer with its download
progress, the four-way vision setup, the masked API key dialog, and the Ollama
pull with real progress via `/api/pull`.

**Deliverable:** "transcript plus description" works end to end from a clean
machine.

### Phase 4 — Packaging, polish and tests. Two days.

Double-click launchers, the `tkinter` checks in `init.sh`, `init.ps1` and
`init.cmd`, high-DPI and resizing, container test updates, and documentation.

**Total: roughly 8 to 11 working days for one person**, so about two weeks with
review and the inevitable interruptions.

---

## 8. What is most likely to go wrong

Ranked by probability times damage.

1. **`tkinter` is missing on a user's machine.** Already observed here. It happens
   at first launch, which is the worst moment, and to a user with no way to
   diagnose it. Mitigated by checking in the installers and again at startup, with
   a message that names the exact command to run.
2. **Something touches a widget from the worker thread.** The symptom is a rare
   crash or freeze that will not reproduce on demand, and it will be blamed on
   Whisper or on ffmpeg for a week before anyone suspects the UI. Mitigated by the
   single-queue rule and by keeping `tkinter` unimportable from `QueueReporter`,
   which a test can enforce.
3. **Cancellation is swallowed by the broad `except Exception` in the narration
   loop.** Specific, predictable, and avoided by making `Cancelled` derive from
   `BaseException`.
4. **A subprocess prompts where nobody can see it** — `sudo`, winget's UAC dialog,
   or `ollama pull` writing to a stdout that does not exist. Looks like a hang.
5. **The lavender theme does not load on CustomTkinter 6.0.0.** Unverified. Cheap
   to check, which is why it is Phase 0.
6. **The light theme's contrast defects ship.** Measured and fixable, but only if
   someone remembers. They are invisible to a developer on a good monitor and
   painful for the user who has neither.
7. **The first paint blocks on `ffprobe`** over a large inbox, and the window
   appears frozen before it has drawn anything.
8. **The text menu quietly rots** once everyone tests only the GUI. The existing
   container tests cover every path through `menu.py`; they need to keep running,
   and the menu needs to stay the supported front end it is today.

---

## Open questions for the user

These are decisions we could not make on your behalf.

1. **Does the GUI become a supported front end, or an experiment?** This changes
   the answer to almost everything else, and it means editing the "No GUI" line in
   `CLAUDE.md` either way. If it is supported, it needs its own tests and it has
   to work in both languages from day one.

2. **Optional extra, or required?** The plan assumes optional: `requirements.txt`
   untouched, a separate `requirements-gui.txt`, and today's install unchanged for
   anyone who does not want a window. Making it required would be simpler to
   explain and would break the property `CLAUDE.md` protects. We recommend
   optional but it is your call.

3. **Which machines actually have to work?** The `tkinter` risk is entirely
   different if the answer is "Windows laptops we control" versus "whatever a
   client happens to own". If Linux is in scope, `init.sh` has to install
   `python3-tk` and that means `sudo`, which some users do not have.

4. **Light only, or light by default with a dark option?** The request was the
   light lavender theme. The file contains both, so offering dark costs almost
   nothing — but it doubles what has to be checked for contrast, and we have
   already found two defects in one mode.

5. **Is accessibility a requirement?** If a screen reader has to work, CustomTkinter
   is the wrong choice and the recommendation changes to Qt. Worth answering
   explicitly before Phase 2, because it is expensive to change afterwards. The
   README does list accessibility work as one of the audiences.

6. **Should the GUI be able to start a run on a folder other than `inbox/`?** The
   console model is "drop files in `inbox/`". A window invites drag-and-drop and a
   file picker, which is friendlier but diverges from the documented workflow and
   from what the PowerShell wrappers do.

7. **How much of `doctor` belongs in the GUI?** Everything, a summary, or a
   "Copy diagnostics" button that puts the full text on the clipboard for a
   support email? The last option is cheap and probably the most useful of the
   three.

8. **Does the frozen-executable question need revisiting now or later?** Our
   recommendation is later, and only if the Python installation step is measured
   to be the actual barrier rather than the assumed one.

> A separate document, `docs/GUI_PLAN_FLET.md`, covers a Flet-based alternative.
> This plan does not evaluate or compare against it; the two are meant to be read
> side by side.

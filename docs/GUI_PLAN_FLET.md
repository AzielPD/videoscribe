# A graphical interface built with Flet

This is an assessment, not a decision. It works out what a Flet front end for
VideoScribe would look like, what it would cost, and where it would probably go
wrong. No code has been written.

`CLAUDE.md` currently lists "No GUI" as a deliberate non-goal, on the grounds that
the menu covers non-technical users adequately. That judgement is what is being
revisited. A lawyer who has never opened a terminal can be walked through
double-clicking `run.cmd`, but the menu still asks them to read a fixed-width
table and type a number. A window with buttons is a lower bar.

---

## The short version

**Recommendation.** Flet is a reasonable choice, but only if the app is shipped
the way VideoScribe is already shipped: installed by `init.cmd` / `init.sh` and
launched by `run.cmd` / `run.sh`, with `pip install flet` added to
`requirements.txt`. Do not try to produce a signed, self-contained installer with
`flet build` — that is where the cost and the risk are, and it buys less than it
looks like it does.

**Main reservation.** Flet's headline feature is that the same code runs on
desktop, web and mobile. For this program that is close to worthless. VideoScribe
reads local video files and runs local models; mobile is impossible and web is a
different product. So Flet is being chosen purely for how the desktop window
looks, and for that it charges a ~40 MB Flutter engine that is downloaded from
GitHub on first run. On a locked-down work laptop — the exact machine our users
have — that download is the single most likely thing to fail.

**Second reservation.** Flet is between major versions. 0.86.5 is current;
1.0 has not shipped. The API was rewritten between 0.28 and 0.80 and every
tutorial, blog post and Stack Overflow answer written before December 2025 is now
wrong. Anyone working on this must check the version on every example they copy.

---

## What was verified, and when

Everything below was checked against flet.dev, the GitHub repository and PyPI on
**4 August 2026**.

| Fact | Value | Source |
|---|---|---|
| Current version | **0.86.5**, released 1 August 2026 | PyPI |
| Licence | **Apache-2.0** | PyPI, GitHub |
| Python required | **3.10 or newer** | PyPI metadata |
| `flet` wheel size | 622 KB | PyPI |
| Runtime dependencies | `httpx`, `oauthlib`, `repath`, `msgpack` | PyPI metadata |
| Desktop client (Windows) | `flet-windows.zip`, **40.1 MB** compressed | GitHub release v0.86.5 |
| Desktop client (macOS) | `flet-macos.tar.gz`, **52.6 MB** compressed | GitHub release v0.86.5 |
| Desktop client (Linux) | ~16 MB compressed per distro variant | GitHub release v0.86.5 |
| Where the client lands | `~/.flet/client/`, downloaded on first run | Flet 0.83.0 release notes |
| Mirror override | `FLET_CLIENT_URL` environment variable | Flet 0.83.0 release notes |

**Marked unverified.** I could not measure the *unpacked* size of the desktop
client, only the compressed download. A Flutter desktop runner typically expands
to somewhere between 1.5x and 2.5x its archive, so budget roughly 60–100 MB on
disk for Windows and 80–130 MB for macOS. Treat those as estimates, not measured
figures.

### The API revision is real and recent

The brief asked me to establish this rather than assume it. It happened.

- **0.28.3** is the last release of the old API.
- **1.0 alpha** introduced a ground-up rewrite.
- **1.0 beta shipped as 0.80.0 on 24 December 2025.** The project's own wording is
  that the API is "99% stable and will not change before the 1.0 final release".
- **0.86.0 (14 July 2026)** is described by the project as "the last one before
  1.0". 0.90 is planned as the 1.0 release candidate.

The changes that matter for anything written here:

| Old | Current |
|---|---|
| `ft.app(target=main)` | `ft.run(main)` |
| `page.open(dialog)` | `page.show_dialog(dialog)` / `page.pop_dialog()` |
| `FilePicker` as a control with `on_result` | a **service** in `page.services`, async methods only |
| `page.client_storage` | `page.shared_preferences` |
| `Page.on_resized` | `Page.on_resize` |
| `ft.alignment.center` | `ft.Alignment.CENTER` |
| `Button(text="...")` | `Button(content="...")` |
| charts in core | separate `flet-charts` package |

And the one that shapes the whole architecture:

> Flet 1.0 uses a **single-threaded async UI model**, like JavaScript or Flutter.
> A blocking call such as `time.sleep()` freezes the interface.

That is not a footnote. VideoScribe's pipeline blocks for minutes at a time. See
[Architecture](#architecture) below.

### Python 3.10 is a floor

The README promises Python 3.9 or newer. Flet requires 3.10. Adding a Flet GUI
either raises VideoScribe's minimum to 3.10, or makes the GUI an optional extra
that 3.9 users cannot install. This needs an explicit decision; it is in the open
questions at the end.

---

## 1. Is Flet the right tool for this particular job?

### The cross-platform claim, examined honestly

Flet's distinguishing property is one codebase running as a desktop window, a web
page or a mobile app. Each of those deserves a straight answer.

**Desktop: yes, and this is the only one that matters.** A native window on
Windows, macOS and Linux from one Python file, with a modern look and no per-
platform code. That is the entire value proposition here.

**Mobile: no. Not partly, not eventually.** VideoScribe runs faster-whisper on
top of ctranslate2, holds a 480 MB to 3.1 GB model in memory, and shells out to
ffmpeg. None of that exists on a phone in a usable form. The frame is a red
herring: the model is not "port the UI to mobile", it is "there is no version of
this program that runs on a phone". Do not let the mobile capability influence
any design decision.

**Web: interesting, but it is a different product.** `flet run --web` serves the
same app in a browser while the Python keeps running on the host machine. There
is a genuine scenario there — one well-specified office machine does the
transcribing, and several lawyers reach it from their own browsers. But getting
there needs work Flet does not do for you:

- Videos are multi-gigabyte. Today they are picked up from a local `inbox/`
  folder. Over the web they would have to be uploaded, with all the progress,
  resumption and disk-quota handling that implies.
- The pipeline is CPU-bound and saturates the machine. Two simultaneous users
  means a job queue, which does not exist.
- There is no authentication. Deposition footage on an unauthenticated internal
  web page is worse than no web page.
- The privacy promise in the README is "it runs on your own computer". A shared
  server is still local to the firm, but it is not the same claim, and the
  wording would have to change.

So: web mode is a plausible *later* product, not a free bonus. Build the desktop
app. If someone asks for the shared-machine version afterwards, Flet will have
saved a real amount of work — but do not count that saving today.

### What it costs

**Download and disk.** `pip install flet` fetches under a megabyte. Then, the
first time the app runs, Flet downloads the Flutter desktop client from GitHub
Releases — 40 MB on Windows, 53 MB on macOS, 16 MB on Linux — and caches it in
`~/.flet/client/`. Compare with CustomTkinter, which is about 900 KB of Python
and data files on top of the tkinter that already ships with CPython.

Against VideoScribe's existing footprint this is less dramatic than it sounds.
`pip install -r requirements.txt` already pulls ctranslate2, onnxruntime,
tokenizers and numpy — several hundred megabytes — and the default `small` model
is another 480 MB. Adding 40 MB to that is a rounding error. **The problem is not
the size. It is where it comes from and when.**

**Is it still a pure `pip install`?** Almost. `pip install flet[desktop]`
installs cleanly with no compiler and no system packages. But the install is not
finished until the app has run once and fetched its client. That is a
second network round trip, at a different moment, from a different host
(`github.com`), that `pip` does not know about and `init.cmd` currently would not
either. If it fails, the user sees a Flet error, not a VideoScribe one.

**The locked-down work laptop.** This is the case that decides it, because it is
our users' actual machine.

| Obstacle | Does it bite? |
|---|---|
| No administrator rights | No. Flet installs into the user's Python environment and caches under the home directory. |
| Corporate proxy | Possibly. The client download is a plain HTTPS fetch; a proxy needing authentication will break it with a message about GitHub, not about VideoScribe. |
| `github.com` blocked | **Yes, fatally** — unless `FLET_CLIENT_URL` is pointed at an internal mirror. That is a documented escape hatch and it works, but somebody has to host the mirror. |
| Antivirus / SmartScreen | Likely at least once. The cached client is an unsigned `.exe` that appeared in the user's profile without an installer. That is close to the textbook description of what endpoint protection is looking for. |
| No internet at all | Fatal, unless the `~/.flet/client/` folder is pre-seeded by hand. |

Mitigation, and it should be built in from day one: **`init.cmd` / `init.sh` must
warm the client cache during installation**, while the user is already watching a
progress display and has already agreed to downloads. Do it by launching a
throwaway Flet window and closing it immediately, or by fetching and unpacking
the archive directly. Either way, the failure then happens during install, where
VideoScribe already has good error messages, instead of on first use.

`python videoscribe.py doctor` should also learn to report whether the Flet
client is cached, in the same style as its existing ffmpeg checks.

---

## Architecture

### The problem in one sentence

`process_video()` blocks for minutes to hours, and Flet's UI runs on a single
async event loop where a blocking call freezes the window.

### The shape of the solution

```
  UI event loop (Flet)                     worker thread
  --------------------                     -------------
  button click
      |
      +-- page.run_thread(run_all) ------> process_video(video, config,
      |                                                  options, reporter)
      |                                        |
      |                                        +-- reporter.step(...)
      |                                        +-- bar.update(...)
      |                                        +-- reporter.warn(...)
      |                                             |
      |                                             v
      |                                       queue.Queue  (thread-safe)
      |                                             |
      +-- page.run_task(drain_queue) <--------------+
              every ~100 ms:
                  read everything queued
                  mutate controls
                  page.update()
```

Three rules make it safe:

1. **Nothing on the worker thread ever touches a control.** It only puts plain
   messages on a `queue.Queue`. `queue.Queue` is thread-safe; Flet controls are
   not, and updating them from a foreign thread is exactly the class of bug that
   produces intermittent, unreproducible freezes.
2. **One coroutine owns all UI mutation.** Started with `page.run_task()`, it
   loops on `await asyncio.sleep(0.1)`, drains the queue, applies every message,
   and calls `page.update()` once. One update per tick, not one per message.
3. **Progress messages coalesce.** A bar sends absolute values, so when three
   updates for the same bar arrive in one tick only the last is applied.

`page.run_thread()` and `page.run_task()` are both documented on the current
`Page` reference, so this uses supported API rather than raw `threading.Thread`.

The existing `ProgressBar` already throttles redraws to about seven per second
(`progress.py`, the 0.15-second check in `update()`). At that rate a 100 ms drain
tick is comfortably fast enough, and the queue never grows.

**Note on the transcription workers.** `transcribe_in_parallel()` uses
`ThreadPoolExecutor`, not `multiprocessing` (`transcribe.py`, around line 209).
That is fortunate: multiprocessing inside a Flet app has been a recurring source
of trouble, and threads inside a thread are unremarkable. Do not "improve" this
into a process pool without testing it under Flet first.

### Abstracting `Reporter`

`Reporter` in `progress.py` is already the right shape. Every call site uses only
`banner`, `step`, `detail`, `warn`, `done` and `bar`, and `bar` returns something
with `update`, `advance` and `close` that works as a context manager. Nothing
else about it is public.

The smallest honest change:

- Turn `Reporter` into the base class or `typing.Protocol` defining exactly those
  six methods, plus a `ProgressBar` protocol with `update`, `advance`, `close`
  and the context-manager pair.
- Rename the current implementation to `ConsoleReporter`. Its behaviour does not
  change at all.
- Add `QueueReporter`, which turns every call into a message on the queue.
- `pipeline.py` line 99 does `reporter = reporter or Reporter(total_steps)`.
  That becomes `ConsoleReporter(total_steps)`. It is the only line in the
  pipeline that needs touching.

Keep the console version as the default, so `python videoscribe.py run` behaves
byte for byte as it does today. That also keeps the container tests honest: they
test the console path, and the console path stays real rather than becoming a
compatibility shim.

Do not let the GUI import anything from `menu.py`. `menu.py` calls `input()`,
`getpass`, `print()` and `sys.exit()`; none of that survives contact with a
window. The GUI is a third front end alongside `cli.py` and `menu.py`, sharing
`pipeline.py`, `config.py`, `system.py`, `install.py`, `vision.py` and `i18n.py`.

### Cancellation

The pipeline has no cancellation today, and this is the part most likely to be
done badly. A Stop button that does nothing for four minutes is worse than no
Stop button.

**Mechanism: cooperative, checked at the points that already exist.**

Add a `Cancelled(RuntimeError)` exception and a `cancelled` flag on the reporter.
Raise `Cancelled` from inside `Reporter.step()` and `ProgressBar.update()`. Those
two methods are called from every loop that runs for any length of time —
ffmpeg's progress reader, the transcription progress callback, the per-window
narration loop — so a cancel takes effect within a second or so without adding a
single new check to the numerical code.

Three concrete changes this forces, all of which will otherwise silently break
it:

1. **`pipeline.py`, the narration loop (around line 331)** catches
   `except Exception` so that one bad window cannot kill a run. `Cancelled` is an
   Exception and would be swallowed, leaving the run to grind through every
   remaining window. Add `except Cancelled: raise` immediately above it.
2. **`menu.py`, the per-video loop (around line 614)** has the same problem for
   the console front end. The GUI's own loop must not repeat the mistake.
3. **`audio.py`, `_run_ffmpeg()` (around line 85)** starts ffmpeg with `Popen`
   and calls `on_progress` inside the read loop, with no `try`/`finally`. If the
   callback raises, the Python side unwinds and ffmpeg keeps running. Wrap the
   loop in `try`/`finally` and call `process.terminate()`.

**What the button should say.** Not "Cancel" — "Stop after this step". Then the
label changes to "Stopping…" and the app waits. This is more honest than a
progress dialog that pretends to be instantaneous, and it matches how the rest of
VideoScribe talks to the user.

**What survives a stop.** Everything already written stays on disk, and
`--resume` already knows how to pick it up. Say so on screen when a run is
stopped: "the work so far is saved in `output/<name>/`; starting again will reuse
it." That turns cancellation from a loss into a pause, which is a genuinely
better product than the console has.

### Closing the window mid-run

Treat window close during a run as a cancel that needs confirming. Flet's
`page.window` exposes the native window; intercept the close, show a dialog with
`page.show_dialog()`, and only exit once the worker has stopped. Killing the
process outright is survivable — `--resume` exists — but leaves half-written
files and a bad impression.

---

## Screens

Every screen in `menu.py`, and what replaces it. Nothing is dropped.

| Console screen | `menu.py` | Flet equivalent |
|---|---|---|
| First-run language picker | `choose_language(first_run=True)` | Modal dialog on first launch, two large buttons |
| Main menu | `run_menu()` | Home screen: file list, two action cards, settings icon |
| ffmpeg missing + install offer | `offer_to_install_ffmpeg()` | Blocking dialog with radio options, then a progress dialog |
| "What can my computer do" | `show_machine()` + `show_environment()` | Settings tab, "This computer" panel |
| Model chooser | `choose_model()` | Table of selectable rows with time, size and purpose |
| How to describe the video | `setup_vision()` | Radio cards, one per back end |
| API key prompt | `ask_for_api_key()` | Provider picker, then a masked field |
| Ollama model pull | `setup_local_vision()` | Progress dialog with streamed output |
| Confirm before starting | `_start_run()` | Summary panel with an explicit start button |
| Per-step progress | `Reporter` / `ProgressBar` | Step list with one determinate bar per step |
| Finished | end of `_start_run()` | Results panel, warnings first, then files |

Notes on the ones that are easy to forget or easy to get wrong.

**First-run language.** `resolve_startup_language()` already returns whether the
language was explicit. The GUI reads the same flag and shows the same choice. Two
details survive from the console version and must not be lost: choosing Spanish
also sets `transcription.language` and `narration.output_language` via
`LANGUAGE_DEFAULTS`, and the user is told that it did. Being silently switched
into Spanish transcription is confusing; being told is not.

Note that `menu.py` skips the picker when stdin is not a terminal. The GUI has no
equivalent condition, so it always shows the picker on first run. That is the
right behaviour, but it means the GUI cannot be driven headlessly for tests
without a flag.

**Model chooser.** This is the screen that most rewards a GUI. The console prints
a fixed-width table and asks for a number. The GUI can show one selectable row
per model with columns for time, download size and purpose, using the same data:
`estimate_runtime()`, `MODEL_DOWNLOAD_MB` and the `MODEL_PURPOSE` keys. Keep every
piece of information the console shows:

- Models that would not fit in memory (`can_run()` is False) stay **visible but
  disabled**, with the reason shown. Hiding them makes the machine look worse
  than it is and invites the question "where did `large-v3` go?".
- The badges — recommended, current, already downloaded — become chips on the row.
- The "this is a 1.5 GB download that happens once" confirmation stays a separate
  step. Do not fold it into row selection. The user is agreeing to a download and
  should have to say so.
- The header saying the times are measured for *this* job, not a hypothetical
  hour, must survive. `menu.py` is careful about this and the reason is written
  down in a comment there: quoting "about 19 minutes" for a twenty-second clip
  destroys trust in every other number on screen.

**ffmpeg install offer.** `install_options()` already returns labelled options
with detail text and a `needs_admin` flag. Render them as radio rows; put
"needs administrator rights" as a visible warning on the row, not in a tooltip.
`install_portable()` takes a `report` callback for text and a `progress` callback
for bytes — both map directly onto a label and a determinate progress bar, and
the console's tty-versus-pipe branching disappears entirely. Show the source host
and the size before starting, as the console does; a user on a metered connection
is entitled to know.

**How the video should be described.** Four options, and a GUI can carry more of
the explanation than a console can without becoming a wall of text. One card
each, with the detail text from `vision.option_*_detail`:

- **Local model (Ollama).** Card should carry the privacy statement plainly — it
  is the only option that sends nothing over the internet — alongside the honest
  cost, which `setup_local_vision()` already computes: roughly 25 seconds per
  frame on a CPU, and the estimated total in minutes for *this* video.
- **API key.** Leads to the key screen below.
- **Claude Code CLI.** Detected, not configured here.
- **Skip.** Not styled as a failure. Transcript-only is a legitimate and
  commonly correct choice, and for confidential footage it is the *right* choice.

The privacy note from the README belongs on this screen, not buried in settings:
the transcript never leaves the computer, the description does.

**API key.** The one screen with a hard rule: `TextField(password=True,
can_reveal_password=True)`. Verified in the current control reference. The reveal
toggle is deliberate — someone pasting a 100-character key needs to be able to
check it — but it defaults to hidden.

Everything else from `ask_for_api_key()` carries over: the provider list with
where to get a key and what it costs, and the two statements the console makes
about what happens next. The key goes into `.env`, and `.env` is not committed to
version control. Both facts should be visible on the screen, not in a help page.
Reuse `save_setting()` unchanged, and keep the `os.environ[variable] = key` line
so the run can start without a restart.

**Progress.** The console prints `[3/8] Converting speech to text` and redraws one
bar. The GUI shows all steps at once as a list: completed steps ticked with their
`done()` line, the current step with its bar, later steps greyed. This is
strictly better than the console — the user can see that eight things will happen
and where they are in that sequence — and it costs nothing extra, because
`Reporter.step()` already carries the number and the total.

Keep the ETA. `ProgressBar._render()` computes it and people watch it.

**Finished.** Warnings first, then the file list, then the folder path with a
button that opens it in Explorer or Finder. The order matters and is argued in
the next section.

### Where Flet gives you something the console cannot

**Drag and drop of video files onto the window — real, but not free.** This
needed verifying and the answer is more awkward than it first looks.

- Flet's built-in `Draggable` / `DragTarget` are for dragging controls *within*
  the app. They do not accept files from Explorer or Finder.
- The long-standing request for OS file drop (issue #112) was closed as completed
  in March 2025, but I could find **no documented `on_file_drop` event in Flet
  core** as of 0.86.5. I am marking the core support as **unverified** rather
  than assuming the closed issue means it landed.
- The working route is the community extension **`flet-dropzone`** (0.4.0,
  released 1 August 2026, Apache-2.0), which wraps the Flutter `desktop_drop`
  package and supports Windows, macOS and Linux.
- **The catch:** third-party Flet extensions are Flutter packages. They are only
  resolved by `flet build`, not by `flet run` against the stock prebuilt client.
  Using `flet-dropzone` means building a custom client, which means the Flutter
  SDK, and on Windows Visual Studio with the "Desktop development with C++"
  workload and Developer Mode enabled for symlinks. That is a large addition to
  the build story for one convenience feature.

**So do not promise drag and drop in the first version.** Ship a "Choose
videos…" button using the built-in `FilePicker` service, which needs nothing
extra. Revisit drag and drop only if the project decides to do custom builds
anyway.

Genuinely free wins that the console cannot match:

- **A file picker that starts in the right folder.** Today the user has to find
  `inbox/` in Explorer. `FilePicker` is a service in `page.services` with async
  methods (`await picker.pick_files(allow_multiple=True)`).
- **Open the results folder.** One button, removing the "where did it go?"
  question entirely.
- **Warnings that stay on screen.** A console warning scrolls away during a
  three-hour run. A pinned banner does not. See below.
- **Per-video progress across a batch**, rather than eight numbered steps
  repeating with no sense of the whole.
- **Selective re-runs.** `--speakers 2 --resume` is the documented fix when
  speaker separation goes wrong, and today it requires typing a command. In a
  GUI it is a number field and a button on the results screen: "the speakers came
  out wrong — I know there were [2] people". That turns the tool's weakest
  feature into something a non-technical user can actually correct.

---

## Design rules the GUI must not break

`CLAUDE.md` rule 4 is *uncertainty is surfaced, not hidden*. Rules 1 to 3 concern
timecodes and are untouched by a front end — the GUI must not format times
itself, and must call `format_timecode()` for anything it displays. Rule 4 is the
one a GUI can quietly destroy, because graphical interfaces are built out of
components designed to make warnings tidy and dismissible.

**The speaker-separation warning.** `DiarizationResult.quality_note()` returns a
string when the best separation score is under 1.25. It reaches
`reporter.warn()` and `result.warnings`. In the GUI:

- It renders as an **amber banner pinned above the run log**, not as a line
  inside a scrolling list. Once shown it does not scroll away for the rest of
  the run.
- It appears again on the finished screen, **above the file list**, under the
  "Please note" heading (`app.please_note`, which already exists).
- **Never a snackbar or a toast.** Flet has both. They disappear after a few
  seconds. A warning that says "treat the speaker labels as a rough guide" must
  not be capable of being missed by someone who looked away.
- The banner is **not dismissible**. There is no close button, no "don't show
  this again", and no setting that suppresses it.
- Next to the warning, put the fix as a button, because the console cannot: the
  "I know there were N people" re-run described above.

**The colour of a warning must not be the accent colour.** This sounds like
pedantry and is not. In a lavender interface, purple is the colour of buttons and
selected rows. If the warning is also purple it reads as decoration. Warnings get
amber; errors get red; neither is anywhere else in the palette. Concrete values
are in the next section.

**The disclaimer.** The README opens with it, and `writers.py` puts
`file.disclaimer` in the header of the output files. The GUI must reach the user
too, and the standard graphical answer — an About box — is not good enough,
because nobody opens it. Three places, all of them unavoidable:

1. **A permanent single-line strip along the bottom of the window**, in muted
   text: this is a drafting aid, not a certified transcript. Always visible, on
   every screen, from the moment the app opens.
2. **In the confirmation panel before a run starts**, as body text next to the
   start button — not a link, not a checkbox, not collapsed behind "more
   information".
3. **On the finished screen**, above the file list, in the same block as any
   warnings.

Use the existing `file.disclaimer` string from `i18n.py` in all three places, so
that what the screen says and what the output file says are the same sentence in
the same language. Do not write a new, shorter, friendlier version for the UI.

**Everything on screen goes through `t()`.** `menu.py`'s docstring already states
this rule and it applies unchanged. New GUI screens mean new keys in
`i18n.MESSAGES` with both `en` and `es` entries. A missing translation shows the
key, which is deliberately ugly and easy to spot. Two practical consequences:

- Button labels must survive Spanish, which runs roughly 20% longer than English.
  Do not size buttons to fit "Start"; size them to fit "Comenzar ahora" without
  the text wrapping oddly.
- Changing language must redraw the whole window immediately, the way the console
  redraws its menu. The `t()` calls are evaluated at render time, so this means
  rebuilding the control tree after `set_language()` — not caching strings at
  startup.

**Plain English in error messages.** `CLAUDE.md` requires saying what went wrong
and what to do about it. The GUI adds two new failure sources with no console
equivalent, and both need real messages rather than a stack trace in a dialog:
the Flet client failing to download, and a video file that cannot be read after
being chosen through the picker.

---

## The light lavender palette

Flet's theming is Flutter's Material 3 theming, exposed through Python. It works
differently from a tkinter theme pack: instead of styling widgets, you define a
set of **semantic colour roles** — primary, surface, error and about forty more —
and every control derives its appearance from them. Getting the roles right means
every control looks correct without being styled individually.

Verified API:

- `page.theme` and `page.dark_theme` take a `ft.Theme`.
- `page.theme_mode` takes `ft.ThemeMode.LIGHT`, `DARK` or `SYSTEM` (the default).
- `ft.Theme(color_scheme_seed=...)` generates a whole palette from one colour.
- `ft.Theme(color_scheme=ft.ColorScheme(...))` sets roles explicitly.
- Colours accept hex strings such as `"#6750A4"` as well as `ft.Colors` constants.
- `Container` and similar controls take their own `theme` and `theme_mode`, so a
  region can be given a different scheme without affecting the rest of the page.

### Two ways to get lavender

**The one-line version.** Material's own baseline seed is already a lavender:

```python
page.theme = ft.Theme(color_scheme_seed="#6750A4")
page.theme_mode = ft.ThemeMode.LIGHT
```

This produces a coherent, accessible scheme. Its weakness for our purposes is
that the generator normalises chroma, so the surfaces come out very close to
white with only a hint of violet. It reads as "a Material app", not as "a light
lavender app".

**The deliberate version.** Set the roles explicitly. These values are a
Material 3 tonal palette at roughly hue 265°, with the surfaces pushed a little
further towards lavender than the generator would choose.

```python
LAVENDER_LIGHT = ft.ColorScheme(
    primary="#5E4B8B",                    # buttons, selected rows, focus rings
    on_primary="#FFFFFF",
    primary_container="#E7DEFA",          # quiet fills, selected list rows
    on_primary_container="#1F1147",
    secondary="#625B71",                  # muted controls
    on_secondary="#FFFFFF",
    secondary_container="#E8DEF8",
    on_secondary_container="#1D192B",
    tertiary="#6B5A7E",
    on_tertiary="#FFFFFF",
    surface="#FBF8FF",                    # the window background
    on_surface="#1C1B1F",                 # all body text
    surface_container_lowest="#FFFFFF",
    surface_container_low="#F6F1FC",
    surface_container="#F1EBF9",          # cards
    surface_container_high="#EBE4F5",     # raised cards, dialogs
    surface_container_highest="#E5DDF0",
    on_surface_variant="#4A4458",         # secondary text, the disclaimer strip
    outline="#7A7289",                    # borders
    outline_variant="#CBC3DA",            # dividers
    error="#B3261E",
    on_error="#FFFFFF",
    error_container="#F9DEDC",
    on_error_container="#410E0B",
    inverse_surface="#322F35",
    inverse_primary="#CFBCFF",
)

page.theme = ft.Theme(color_scheme=LAVENDER_LIGHT)
```

Contrast, checked rather than assumed:

| Pair | Ratio | Verdict |
|---|---|---|
| `on_surface` `#1C1B1F` on `surface` `#FBF8FF` | ~16:1 | Comfortably AAA |
| `on_primary` `#FFFFFF` on `primary` `#5E4B8B` | ~7.4:1 | AAA for normal text |
| `on_surface_variant` `#4A4458` on `surface` `#FBF8FF` | ~9:1 | AAA; safe for the disclaimer strip |
| `on_error` `#FFFFFF` on `error` `#B3261E` | ~5.9:1 | AA |

Lawyers reading long transcripts on a laptop in a hotel room is a real use case.
Do not trade contrast for prettiness.

### Warning colours, outside the scheme

Material 3 has no "warning" role. Define the amber explicitly and use it in
exactly one place — the uncertainty banner:

```python
WARNING_BG     = "#FFF3D6"   # banner background
WARNING_TEXT   = "#8A5A00"   # banner text, ~5.4:1 on the background
WARNING_BORDER = "#E0A82E"   # 1px border, so it reads as a warning without shouting
```

Amber is chosen because it is far from lavender in hue, so it cannot be mistaken
for an accent, and far from the error red, so an unreliable speaker split does not
look like a crash. Nothing else in the interface uses amber.

### Dark theme

Provide one and let `ThemeMode.SYSTEM` choose. A user whose operating system is
dark and whose transcription tool is glaring white will assume the tool is broken.

```python
LAVENDER_DARK = ft.ColorScheme(
    primary="#CFBCFF",
    on_primary="#37275C",
    primary_container="#4E3D78",
    on_primary_container="#EADDFF",
    surface="#141218",
    on_surface="#E6E0E9",
    surface_container="#211F26",
    surface_container_high="#2B2930",
    on_surface_variant="#CAC4D0",
    outline="#948F9E",
    outline_variant="#49454F",
    error="#F2B8B5",
    on_error="#601410",
    error_container="#8C1D18",
    on_error_container="#F9DEDC",
)
```

The warning colours invert too: background `#3E2E00`, text `#FFD98A`, border
`#8A6A1E`.

### Typography

Flet uses Flutter's bundled Roboto by default. It is fine, it costs nothing, and
it is already there. If a more document-like face is wanted later, `page.fonts`
registers custom fonts and `Theme.text_theme` applies them — but bundling font
files adds weight to a build for a cosmetic gain, so leave it alone until
somebody actually complains.

One typographic rule does matter: **timecodes and file names must be monospaced.**
`[00:04:05]` is a thing to be compared against a video player, and proportional
digits make columns of timecodes hard to scan.

---

## Packaging

### Recommendation: do not package

Keep doing exactly what VideoScribe does now.

- Add `flet[desktop]>=0.86` to `requirements.txt`.
- `init.cmd` / `init.sh` install it along with everything else, and additionally
  warm the `~/.flet/client/` cache so the first launch is not the first download.
- `run.cmd` / `run.sh` launch the GUI. Add a `--menu` or `--console` flag that
  falls back to today's text menu, and keep every existing command-line entry
  point untouched.

The reason is proportion. Users already run a multi-minute installer that fetches
Python, ffmpeg and several hundred megabytes of Python packages. That installer
works, it explains itself as it goes, and it needs no administrator rights. A
self-contained app bundle would replace a working thing with a harder thing to
gain very little.

### If you package anyway

**`flet build` — the modern route.** Produces a native executable with a Python
runtime embedded, using the Flutter SDK. Flet bundles CPython 3.12, 3.13 or 3.14
(3.14.6 by default).

| Platform | Build host | Prerequisites |
|---|---|---|
| Windows | Windows only | Visual Studio 2022 or 2026 with "Desktop development with C++"; Developer Mode enabled for symlinks |
| macOS | macOS | Xcode command line tools |
| Linux | Linux | the usual GTK build dependencies |

The Flutter SDK downloads itself to `$HOME/flutter/<version>` on first build if
it is not on the PATH. There is no cross-compilation: Windows builds need a
Windows machine, macOS builds need a Mac. For a three-platform release that means
three build machines or three CI runners.

**`flet pack` — the older route.** Wraps PyInstaller. Still documented, still
works, and it has a `--codesign-identity` option for macOS. It produces a larger,
slower-starting artefact than `flet build`. Its one advantage is that PyInstaller
is well understood and its behaviour with awkward native wheels is a known
quantity.

**The risk nobody should discover late.** `flet build` packages the app's
dependencies through `serious_python`. VideoScribe depends on ctranslate2,
onnxruntime, tokenizers and numpy — all native wheels, and ctranslate2 in
particular is large and CPU-feature sensitive. Flet's documentation on binary
packages is mostly about iOS and Android; the desktop case uses ordinary PyPI
wheels for the host architecture and *should* work, but **I could not verify that
this specific stack builds**, and there is a documented gotcha about binaries
compiled for AVX2 failing on older CPUs. If packaging is attempted at all, prove
`flet build windows` produces a working executable **before** any UI work starts.
It is a half-day experiment that could save a fortnight.

**Artefact size, estimated not measured.** The Flutter runner and Flet client are
roughly 60–100 MB unpacked. The Python runtime and site-packages, dominated by
ctranslate2 and onnxruntime, are several hundred megabytes more. Expect something
in the range of 400 MB to 700 MB before the transcription model — which is not
bundled and still downloads on first use. There is no version of this that fits
on a memory stick as a tidy little app.

**Code signing.** Unavoidable if you distribute a binary.

- **Windows.** Unsigned executables trigger SmartScreen. An OV certificate
  reduces it; an EV certificate largely removes it. Either way it is an annual
  cost and an identity-verification process.
- **macOS.** Unsigned apps are refused by Gatekeeper. You need an Apple Developer
  account, a Developer ID certificate, and notarisation. `flet pack` supports
  `--codesign-identity`; notarisation is a separate step.
- **Linux.** Not applicable in practice.

This is the strongest argument for not packaging. Shipping a source tree that
runs `python videoscribe.py` sidesteps all of it — and, unlike a signed binary,
it lets a security-conscious firm read what the program does before running it,
which for this audience is a feature.

### The command line must keep working

Non-negotiable, and it costs nothing if the architecture above is followed: the
GUI is a front end over `pipeline.py`, exactly as `cli.py` and `menu.py` are.
`videoscribe.py run --speakers 2 --resume` must behave identically whether or not
Flet is installed. The PowerShell wrappers call the same engine and are unaffected.

Add an import guard so that a missing or broken Flet gives a plain message —
"the graphical interface needs Flet; run `pip install flet[desktop]`, or use
`python videoscribe.py` for the text menu" — rather than a traceback.

---

## Effort and risk

### Phases

Ordered so that something usable exists as early as possible, and so that the
riskiest questions are answered before much is built on top of them.

**Phase 0 — Spike (1–2 days).** Prove the two things that could sink the project.
A window that runs `process_video()` on a real file in a worker thread, with a
progress bar driven by a queue-backed reporter, and a Stop button that actually
stops. No styling, no other screens. If threading, cancellation or the client
download turns out to be a problem, it surfaces here for the price of two days.

**Phase 1 — Usable transcript-only app (1 week).** Home screen, file picker,
model chooser, confirmation, progress, results. Lavender theme applied. Full
`t()` coverage for both languages. Warnings and disclaimer wired in as specified
above. At the end of this phase the tool is genuinely usable by someone who never
opens a terminal — for option 1, which is the more common case.

**Phase 2 — Setup screens (3–4 days).** First-run language picker, ffmpeg install
offer with its download progress, the "how should the video be described" screen,
the API key screen, the Ollama pull. These are the screens that only appear on
some machines, which makes them easy to leave half-finished and hard to test.
Budget deliberately.

**Phase 3 — Description pipeline in the GUI (2–3 days).** Steps 6 to 8, the
per-window progress, the removed-invented-timecodes count, per-window failures
that do not kill the run.

**Phase 4 — Polish (3–5 days).** Batch progress across several videos, the
"I know there were N people" re-run, opening the results folder, window close
handling, dark theme, the empty-inbox state, keyboard navigation.

**Phase 5 — Install and distribute (2 days, or much more).** Warming the client
cache in the installers, `doctor` reporting Flet's state, the fallback flag, the
import guard. Two days if the recommendation above is followed. If a signed
installer is wanted instead, this is a separate project with its own budget and
an annual certificate bill.

Rough total for phases 0 to 4: **three to four weeks** for one developer
comfortable with Python but new to Flet. Add a week if that developer must also
learn Material 3's role vocabulary well enough to use it deliberately rather than
by trial and error.

### What is most likely to go wrong

In descending order of expected pain.

1. **The Flet client download, on the exact machines this is for.** Managed
   laptops, proxies, blocked GitHub, endpoint protection quarantining an unsigned
   executable in the user's profile. This is the top risk and it is not a coding
   problem — it is a deployment problem, which means it will be discovered by a
   user, not by a developer. Mitigate by warming the cache during install,
   documenting `FLET_CLIENT_URL`, and testing on a genuinely locked-down machine
   early. Not on the developer's machine with the corporate VPN off.

2. **Documentation and examples that predate the rewrite.** The API changed
   between 0.28 and 0.80 and most material on the internet is older than that.
   Every copied example must be version-checked. Expect to lose real time to
   examples that look right and do not run.

3. **Cancellation done half-way.** The three code changes listed above are easy
   to miss, and each one produces a Stop button that appears to work and then
   does not. A run that ignores Stop for twenty minutes will be reported as a
   hang.

4. **Warnings quietly softened.** Not a bug — a drift. Somebody makes the banner
   dismissible because it looks untidy, or moves it below the file list because
   the layout is cleaner. This breaks `CLAUDE.md` rule 4 and nothing will fail a
   test. Write the rule into the GUI module's docstring, the way `menu.py`
   documents its own rules, so the next person reads it before deciding.

5. **Building against 1.0.** 1.0 has not shipped. The project says the API is
   stable, and 0.86 is called the last release before 1.0, so the risk is modest
   — but it is not zero, and it is a promise rather than a release. Pin an exact
   version in `requirements.txt` and upgrade deliberately.

6. **`flet build` and native wheels.** Only a risk if packaging is attempted.
   See above; prove it early or not at all.

7. **Long-running UI stability.** A three-hour `large-v3` run means three hours
   of a window updating several times a second. Test one. Do not assume.

---

## A fair comparison with CustomTkinter

Assessed from research on CustomTkinter as a technology, not against any
particular proposal.

CustomTkinter 6.0.0 was released on 24 June 2026, is MIT licensed, and is
actively maintained. It draws modern-looking widgets on top of the tkinter that
ships with CPython.

| | Flet | CustomTkinter |
|---|---|---|
| Extra download | ~900 KB of Python, plus a 40–53 MB engine fetched from GitHub on first run | ~900 KB; tkinter is already in CPython |
| Pure `pip install` | Yes, plus a second fetch at first launch | Yes, and nothing else |
| Works offline after install | Only once the client is cached | Yes, immediately |
| Look | Flutter-rendered Material 3; identical on all three platforms | Modernised tkinter; good, but recognisably tkinter up close |
| Theming | Semantic Material 3 roles; set the palette once, everything follows | Per-widget colour options and JSON theme files; more manual |
| Layout | Flutter's flex model; responsive resizing comes free | Tk `grid`/`pack`; workable, more fiddly for resizable windows |
| Threading | Single-threaded async loop; needs the queue discipline described above | Also single-threaded; needs `after()` scheduling — the same discipline, different syntax |
| Packaging | `flet build` (Flutter SDK, VS C++ on Windows) or `flet pack` (PyInstaller) | PyInstaller, but `--onefile` does not work; needs `--onedir` and manual `--add-data` for its `.json` and `.otf` files |
| Python floor | 3.10 | Works on 3.9, matching VideoScribe today |
| Maturity | Rewritten API, 1.0 not yet shipped | Stable API, long-established, large body of correct examples |
| Web / mobile | Possible | No |
| Risk of surprise on a locked-down laptop | The engine download | Low; nothing new is fetched |

**Where each one wins.** Flet gives a better-looking, more consistent result with
less layout work, and a theming model that makes a coherent lavender palette a
twenty-line declaration instead of a per-widget chore. CustomTkinter adds
essentially nothing to the install, needs no second download, keeps Python 3.9
working, and has a stable API with a decade of tkinter knowledge behind it.

**The honest summary.** If this were a general desktop application, Flet would be
the easy recommendation. It is not. It is a tool for lawyers on managed corporate
laptops, where "it downloaded something from GitHub and antivirus ate it" is a
support call nobody can resolve remotely. CustomTkinter's decisive advantage is
that it adds no new failure mode to installation. Flet's decisive advantage is
that it looks markedly better and is much less work to lay out well.

That is a genuine trade-off and it is a judgement about the users, not about the
technology. If the deployment environment is known to be permissive — a small
firm, personal laptops, ordinary internet — take Flet. If it is not known, or if
it is known to be locked down, CustomTkinter is the safer answer and the
difference in appearance is not worth the support burden.

---

## Open questions for the user

1. **Python 3.9.** Flet needs 3.10. Do we raise VideoScribe's minimum to 3.10,
   make the GUI an optional extra that 3.9 users cannot install, or rule Flet out
   on this ground alone?

2. **How locked down are the target machines, really?** Everything in the risk
   section hangs on this. Can they reach `github.com`? Is there an authenticating
   proxy? What does endpoint protection do to an unsigned executable that appears
   in the user's profile? One test on one real machine would settle more than any
   further research.

3. **Installed source tree, or signed installer?** I recommend the former, which
   makes packaging nearly free. A signed installer is a separate project with an
   annual certificate cost and per-platform build machines. Which is wanted?

4. **Does the GUI replace the text menu, or sit beside it?** I have assumed
   beside it: `run.cmd` opens the window, `--menu` opens today's text menu, and
   the container tests keep testing the console path. Confirm — if the menu is to
   be retired, the test suite needs replacing rather than extending.

5. **Is the shared-office-machine web mode actually wanted?** It is the only
   version of Flet's cross-platform story with any value here, and it changes the
   privacy wording in the README. If nobody wants it, we can stop weighing it.

6. **How much lavender?** The palette above puts a light lavender cast on the
   window background and every card. The Material seed alternative is nearly
   white with a violet hint. The first is more distinctive; the second is more
   conventional for a document tool used in professional settings. Which reads
   better to you?

7. **Drag and drop.** It requires a custom Flutter build. Confirmed as
   deliberately out of scope for a first version — but if it is considered
   essential, that decision has to be taken up front, because it changes the
   whole build story rather than adding a feature to it.

8. **What happens to a run when the window is closed?** I have proposed
   confirming and stopping cleanly. The alternative — keep running in the
   background with a tray icon — is more useful for three-hour jobs and
   noticeably more work. Worth it?

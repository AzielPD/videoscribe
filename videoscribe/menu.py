"""The interactive menu, for people who would rather not type commands.

Running ``python videoscribe.py`` with no arguments lands here. Everything it
offers is also available as a command-line flag, so the menu is a convenience
and never the only way to do something.

The menu is deliberately chatty: it says what it found, what it is about to do
and roughly how long that will take, and it asks before doing anything slow or
expensive.

Every visible string goes through :func:`videoscribe.i18n.t`, so the whole
interface follows whichever language the user picked.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import Config, load_config, save_setting
from .i18n import (
    LANGUAGE_DEFAULTS,
    LANGUAGE_NAMES,
    detect_system_language,
    get_language,
    language_name,
    set_language,
    t,
)
from .pipeline import RunOptions, find_videos, process_video
from .progress import Reporter
from .system import (
    MODEL_DOWNLOAD_MB,
    can_run,
    estimate_runtime,
    model_is_downloaded,
    profile_machine,
    recommend_model,
)
from .timecode import format_duration, format_timecode
from .tools import ToolMissing, check_all, find_ffmpeg
from .vision import available_backends, is_configured

RULE = "=" * 70
THIN = "-" * 70

# Offered in the menu, cheapest first.
SELECTABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Accepted as "yes" in either language, plus the usual English forms.
YES_WORDS = {"y", "yes", "s", "si"}
NO_WORDS = {"n", "no"}


def ask(prompt: str, valid: set[str], default: str = "") -> str:
    """Read one answer, repeating until it is one of ``valid``."""
    hint = f" [{default}]" if default else ""
    while True:
        try:
            answer = input(f"{prompt}{hint}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n" + t("prompt.cancelled"))
            sys.exit(0)
        if not answer and default:
            return default
        if answer in valid:
            return answer
        print("  " + t("prompt.answer_one_of", options=", ".join(sorted(valid))))


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question, accepting both English and Spanish answers.

    The suggested answer is shown in the reader's own language, so a Spanish
    prompt reads "(s/n) [s]" rather than the confusing "(s/n) [y]".
    """
    accepted = YES_WORDS | NO_WORDS
    fallback = t("prompt.yes_letter") if default else t("prompt.no_letter")
    answer = ask(f"{prompt} {t('prompt.yes_no')}", accepted, fallback)
    return answer in YES_WORDS


def wrap(text: str, width: int = 66) -> list[str]:
    """Small word wrapper, so long explanations stay inside the console."""
    words, lines, current = str(text).split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def print_wrapped(text: str, indent: str = "    ") -> None:
    for line in wrap(text):
        print(f"{indent}{line}")


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------
def resolve_startup_language(config: Config) -> tuple[str, bool]:
    """Work out which language to start in.

    Returns ``(code, was_explicit)``. ``was_explicit`` is False when nothing was
    configured and the language came from the operating system, which is the
    signal that the user should be offered the picker on this first run.
    """
    configured = (config.ui_language or "").strip().lower()
    if configured in LANGUAGE_NAMES:
        return set_language(configured), True
    return set_language(detect_system_language()), False


def choose_language(config: Config, first_run: bool = False) -> str:
    """Show the language picker and remember the choice in ``.env``."""
    print(f"\n{RULE}")
    print(f" {t('language.header')}")
    print(RULE)
    print()

    codes = list(LANGUAGE_NAMES)
    for index, code in enumerate(codes, start=1):
        marker = "  <" if code == get_language() else ""
        print(f"  {index}) {LANGUAGE_NAMES[code]}{marker}")

    options = {str(index): code for index, code in enumerate(codes, start=1)}
    default = next((key for key, code in options.items() if code == get_language()), "1")

    print()
    print_wrapped(t("language.explain"), indent="  ")
    print()
    chosen = options[ask("  " + t("prompt.pick_number"), set(options), default)]
    set_language(chosen)

    # Persist the choice, and align the spoken and written languages with it
    # unless the user has already set those deliberately in config.json.
    save_setting("VIDEOSCRIBE_UI_LANGUAGE", chosen)
    config.values["ui.language"] = chosen

    defaults = LANGUAGE_DEFAULTS.get(chosen, {})
    if first_run and defaults:
        for key, value in defaults.items():
            config.values[key] = value
        save_setting("VIDEOSCRIBE_LANGUAGE", defaults["transcription.language"])
        save_setting("VIDEOSCRIBE_NARRATION_LANGUAGE", defaults["narration.output_language"])
        print()
        print("  " + t("language.saved", language=language_name()))
        print("  " + t("language.also_sets",
                       code=defaults["transcription.language"],
                       written=defaults["narration.output_language"]))
    else:
        print()
        print("  " + t("language.saved", language=language_name()))

    print("  " + t("language.change_later"))
    return chosen


def total_audio_seconds(videos: list[Path], config: Config) -> float:
    """Combined length of the videos waiting, read with ffprobe.

    Falls back to a nominal hour per unreadable file so a single odd video
    cannot stop the menu from offering a choice.
    """
    from .audio import probe

    try:
        ffmpeg = find_ffmpeg(config.ffmpeg_override)
    except ToolMissing:
        return 3600.0 * len(videos)

    total = 0.0
    for video in videos:
        try:
            total += probe(ffmpeg, video).duration
        except (RuntimeError, OSError):
            total += 3600.0
    return total or 3600.0


# ---------------------------------------------------------------------------
# Installing a missing program
# ---------------------------------------------------------------------------
def offer_to_install_ffmpeg() -> bool:
    """Ask whether to fetch ffmpeg, and do it. True when it is now available.

    Nothing is downloaded or installed without an explicit answer here. The
    size and the source are shown first, because a user on a metered or managed
    connection deserves to know what they are agreeing to.
    """
    from .install import install_options, install_portable, install_with_package_manager

    options = install_options()
    if not options:
        print()
        print_wrapped(t("install.no_options"), indent="  ")
        return False

    print(f"\n{RULE}\n {t('install.offer_header')}\n{RULE}")
    print_wrapped(t("install.explain"), indent="  ")
    print()

    choices: dict[str, str] = {}
    for index, option in enumerate(options, start=1):
        admin = f" {t('install.needs_admin')}" if option.needs_admin else ""
        print(f"  {index}) {option.label}{admin}")
        print(f"     {option.detail}")
        choices[str(index)] = option.kind

    quit_key = str(len(options) + 1)
    print(f"  {quit_key}) {t('install.option_none')}")
    print()

    answer = ask("  " + t("prompt.pick_number"), set(choices) | {quit_key}, "1")
    if answer == quit_key:
        return False

    print("\n  " + t("install.working"))

    def report(message: str) -> None:
        print(f"    {message}")

    # Redrawing in place only works on a real terminal. When the output is
    # piped or redirected, a carriage return does not erase anything and the
    # log fills with hundreds of near-identical lines, so report sparsely.
    redraws = sys.stdout.isatty()
    milestones = {"last": -1}

    def progress(done: int, total: int) -> None:
        if not total:
            return
        megabytes = done // (1024 * 1024), total // (1024 * 1024)
        if redraws:
            print("\r    " + t("install.downloading", done=megabytes[0], total=megabytes[1]),
                  end="", flush=True)
            return
        quarter = (done * 4) // total
        if quarter != milestones["last"]:
            milestones["last"] = quarter
            print("    " + t("install.downloading", done=megabytes[0], total=megabytes[1]),
                  flush=True)

    if choices[answer] == "package-manager":
        path = install_with_package_manager(report)
    else:
        path = install_portable(report, progress)
        print()

    if path:
        print("\n  " + t("install.success"))
        return True
    print("\n  " + t("install.failed"))
    return False


# ---------------------------------------------------------------------------
# Setting up a model that can read the picture
# ---------------------------------------------------------------------------
# Where to get a key, and which environment variable holds it.
API_PROVIDERS = [
    ("Google Gemini", "GEMINI_API_KEY", "https://aistudio.google.com/apikey",
     "free tier available / tiene capa gratuita"),
    ("Anthropic", "ANTHROPIC_API_KEY", "https://console.anthropic.com/settings/keys",
     "pay per use / se paga por uso"),
    ("OpenAI", "OPENAI_API_KEY", "https://platform.openai.com/api-keys",
     "pay per use / se paga por uso"),
]


def ask_for_api_key() -> bool:
    """Prompt for an API key and store it in ``.env``. True when one was saved.

    Typed rather than echoed, and written only to ``.env``, which is ignored by
    version control. The user is told both of those things.
    """
    import getpass

    print(f"\n  {t('vision.choose_provider')}\n")
    for index, (label, _, url, note) in enumerate(API_PROVIDERS, start=1):
        print(f"  {index}) {label:<16} {note}")
        print(f"     {t('vision.key_where', url=url)}")
    print()

    options = {str(i): entry for i, entry in enumerate(API_PROVIDERS, start=1)}
    _, variable, _, _ = options[ask("  " + t("prompt.pick_number"), set(options), "1")]

    print()
    try:
        key = getpass.getpass(f"  {t('vision.paste_key')}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n" + t("prompt.cancelled"))
        return False

    if not key:
        print("  " + t("vision.key_empty"))
        return False

    save_setting(variable, key)
    # Make it visible to this process too, so the run can start immediately
    # instead of asking the user to restart.
    os.environ[variable] = key
    print("\n  " + t("vision.key_saved"))
    return True


def setup_local_vision(machine, audio_seconds: float) -> bool:
    """Offer to run a vision model locally through Ollama."""
    from .vision import OllamaBackend

    if not shutil.which("ollama") and not OllamaBackend.is_available():
        print()
        print_wrapped(t("vision.ollama_missing"), indent="  ")
        return False

    model = OllamaBackend.recommend_model(machine.ram_gb)
    spec = OllamaBackend.MODELS[model]

    level, verdict = OllamaBackend.verdict(machine, model)
    if level == "unusable":
        print()
        print_wrapped(verdict, indent="  ")
        return False

    print()
    print("  " + t("vision.ollama_model", model=model, size=spec["gb"]))

    # One frame every ten seconds is the default sampling rate. The per-frame
    # cost is asked of the back end rather than read from the table, so that a
    # graphics card is reflected instead of quoting everyone the CPU figure.
    frames = max(1, int(audio_seconds // 10))
    minutes = int(frames * OllamaBackend.seconds_per_frame(model, machine) / 60)
    print_wrapped(t("vision.ollama_slow", minutes=minutes), indent="  ")

    if model not in OllamaBackend.installed_models():
        print()
        if not ask_yes_no("  " + t("vision.ollama_pull"), True):
            return False
        print("\n  " + t("install.working"))
        result = subprocess.run(["ollama", "pull", model], check=False)
        if result.returncode != 0:
            print("\n  " + t("install.failed"))
            return False

    if not OllamaBackend.is_available():
        print()
        print_wrapped(OllamaBackend.why_unavailable(), indent="  ")
        return False

    save_setting("VIDEOSCRIBE_VISION_MODEL", model)
    save_setting("VIDEOSCRIBE_SYNTHESIS_MODEL", model)
    print("\n  " + t("vision.ollama_ready"))
    return True


def explain_vision_missing(config: Config) -> str:
    """Say why the description is not available, and offer a way forward.

    Returns what the caller should do next:

    ``"describe"``   a model was set up; run with the description after all
    ``"transcript"`` run anyway, transcript and subtitles only
    ``"back"``       return to the menu

    Someone who picked the description wants their recording processed. Sending
    them back to the menu to pick option 1 instead is a step that teaches them
    nothing, so the transcript is offered here.
    """
    print(f"\n{RULE}\n {t('vision.not_set_up_header')}\n{RULE}")
    print_wrapped(t("vision.not_set_up_explain"), indent="  ")
    print()
    print_wrapped(t("vision.not_set_up_options"), indent="  ")
    print()
    print("  " + t("vision.not_set_up_docs"))
    print()

    if ask_yes_no("  " + t("vision.set_up_now"), False):
        machine = profile_machine(config.output_dir)
        if setup_vision(machine, audio_seconds=0.0):
            return "describe"

    print()
    if ask_yes_no("  " + t("run.continue_transcript_only"), True):
        return "transcript"
    return "back"


def setup_vision(machine, audio_seconds: float) -> bool:
    """Offer every way of getting a model that can read the picture.

    Returns True when one is ready, so the caller can go ahead with the
    description instead of falling back to a transcript.
    """
    from .vision import ClaudeCliBackend, OllamaBackend

    level, verdict = OllamaBackend.verdict(machine)

    print(f"\n{RULE}\n {t('vision.header')}\n{RULE}")
    print_wrapped(t("vision.explain"), indent="  ")
    print()
    print(f"  1) {t('vision.option_local')}")
    print_wrapped(t("vision.option_local_detail"), indent="     ")
    # What the local option costs *here*, rather than in general. On a machine
    # without a graphics card this is the difference between a sensible choice
    # and one that runs overnight, so it decides the default below too.
    print_wrapped(verdict, indent="     ")
    print(f"  2) {t('vision.option_key')}")
    print_wrapped(t("vision.option_key_detail"), indent="     ")
    print(f"  3) {t('vision.option_claude')}")
    print_wrapped(t("vision.option_claude_detail"), indent="     ")
    print(f"  4) {t('vision.option_skip')}")
    print()

    # Pre-select the local model only where it is actually the better choice.
    if level == "recommended":
        default = "1"
    elif ClaudeCliBackend.is_available():
        default = "3"
    else:
        default = "2"

    answer = ask("  " + t("prompt.pick_number"), {"1", "2", "3", "4"}, default)
    if answer == "4":
        return False
    if answer == "1":
        return setup_local_vision(machine, audio_seconds)
    if answer == "2":
        return ask_for_api_key()

    print("\n    " + t("run.no_vision_claude"))
    return False


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def show_machine(config: Config):
    """Print what this computer is, and which model suits it."""
    machine = profile_machine(config.output_dir)
    recommended, reason = recommend_model(machine)

    print(f"\n{RULE}\n {t('machine.header')}\n{RULE}")
    for line in machine.summary():
        print(f"  {line}")

    print()
    print("  " + t("machine.recommended", model=recommended))
    print_wrapped(reason)
    return machine, recommended


def show_environment(config: Config) -> None:
    """The 'is everything installed' screen."""
    print(f"\n{RULE}\n {t('check.programs_header')}\n{RULE}")
    for status in check_all(config.ffmpeg_override):
        print(status.line())

    print(f"\n{RULE}\n {t('check.vision_header')}\n{RULE}")
    any_ready = False
    for name, ready, explanation in available_backends():
        mark = "OK     " if ready else "not set"
        print(f"  [{mark}] {name:<16} {explanation}")
        any_ready = any_ready or ready
    if not any_ready:
        print()
        print_wrapped(t("check.no_vision"), indent="  ")


# What each model is good for, so the choice does not require knowing what a
# transcription model is. Mirrors the table in the README.
MODEL_PURPOSE = {
    "tiny": "model.when_tiny",
    "base": "model.when_base",
    "small": "model.when_small",
    "medium": "model.when_medium",
    "large-v3": "model.when_large",
}


def choose_model(config: Config, machine, recommended: str, audio_seconds: float) -> str:
    """Let the user pick a transcription model, with times and sizes shown.

    ``audio_seconds`` is the real length of the videos waiting, so the times
    quoted are for this job rather than for a hypothetical hour.
    """
    print(f"\n{RULE}\n {t('model.header')}\n{RULE}")
    print("  " + t("model.explain"))
    print("  " + t("model.measured_for", duration=format_timecode(audio_seconds)))
    print()
    print(f"  {'':3} {t('model.col_model'):<10} {t('model.col_time'):<22} "
          f"{t('model.col_download'):<10} {t('model.col_when')}")
    print(f"  {THIN}")

    options: dict[str, str] = {}
    for index, name in enumerate(SELECTABLE_MODELS, start=1):
        purpose = t(MODEL_PURPOSE.get(name, ""))
        if not can_run(name, machine):
            print(f"  {index:>2}) {name:<10} {'-':<22} {'-':<10} {t('model.too_big')}")
            continue
        runtime = format_duration(estimate_runtime(name, audio_seconds, machine))
        size = f"{MODEL_DOWNLOAD_MB.get(name, 0)} MB"
        print(f"  {index:>2}) {name:<10} {runtime:<22} {size:<10} {purpose}")

        marks = []
        if name == recommended:
            marks.append(t("model.recommended"))
        if name == config.model:
            marks.append(t("model.current"))
        if model_is_downloaded(name):
            marks.append(t("model.downloaded"))
        if marks:
            print(f"      {'':<10} {'':<22} {'':<10} <- {', '.join(marks)}")
        options[str(index)] = name

    if not options:
        return config.model

    default_key = next(
        (key for key, name in options.items() if name == config.model), next(iter(options))
    )
    print()
    chosen = options[ask("  " + t("prompt.pick_number"), set(options), default_key)]

    if not model_is_downloaded(chosen):
        print()
        print("  " + t("model.not_here_yet", model=chosen, size=MODEL_DOWNLOAD_MB.get(chosen, 0)))
        print("  " + t("model.downloads_once"))
        if not ask_yes_no("  " + t("model.download_confirm"), True):
            return config.model
    return chosen


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_menu(argv: list[str] | None = None) -> int:
    """Show the menu and act on the choice. Returns a process exit code."""
    config = load_config()
    _, language_was_explicit = resolve_startup_language(config)

    # On a first run nothing has been chosen yet, so ask before anything else.
    # After that the picker is only reached through the menu.
    #
    # Skipped when the input is piped rather than typed: an automated run would
    # otherwise have its first line swallowed by a question it cannot see.
    if not language_was_explicit and sys.stdin.isatty():
        choose_language(config, first_run=True)

    while True:
        print(f"\n{RULE}")
        print(f" {t('app.tagline')}")
        print(RULE)

        try:
            find_ffmpeg(config.ffmpeg_override)
        except ToolMissing as exc:
            print(f"\n  {t('check.missing_tool')}\n")
            for line in str(exc).splitlines():
                print(f"    {line}")
            # Telling someone to go and install something is a dead end if they
            # have never used a terminal. Offer to do it instead.
            if not offer_to_install_ffmpeg():
                print("\n  " + t("check.run_installer"))
                return 2
            # A portable install records its path in .env, so the settings have
            # to be read again before the new location is visible.
            chosen_language = config.values["ui.language"]
            config = load_config()
            config.values["ui.language"] = chosen_language
            continue  # redraw the menu, now that ffmpeg is available

        inbox = config.inbox_dir
        inbox.mkdir(parents=True, exist_ok=True)
        videos = find_videos(inbox)

        print()
        print("  " + t("app.videos_folder", path=inbox))
        print("  " + t("app.results_folder", path=config.output_dir))

        if videos:
            print()
            print("  " + t("app.videos_waiting", count=len(videos)))
            for video in videos:
                print(f"    - {video.name}  ({video.stat().st_size / (1024 ** 3):.2f} GB)")
        else:
            print()
            print("  " + t("app.no_videos"))
            print("  " + t("app.copy_videos_into", path=inbox))

        # The description is only offered when something can actually produce
        # it. Presenting it like any other choice and failing half an hour
        # later, after the transcript has already run, is the worse outcome.
        vision_ready = is_configured()

        print(f"\n{RULE}\n {t('menu.header')}\n{RULE}")
        print("  1) " + t("menu.option_transcript"))
        print("  2) " + t("menu.option_describe"))
        if not vision_ready:
            print("     " + t("menu.describe_unavailable"))
        print("  3) " + t("menu.option_check"))
        print("  4) " + t("menu.option_language", language=language_name()))
        print("  5) " + t("menu.option_quit"))
        choice = ask("\n  " + t("prompt.pick_number"), {"1", "2", "3", "4", "5"}, "1")

        if choice == "5":
            return 0

        if choice == "4":
            choose_language(config)
            continue  # redraw the menu in the new language

        if choice == "3":
            show_machine(config)
            show_environment(config)
            print(f"\n{RULE}\n {t('check.settings_header')}\n{RULE}")
            print(config.describe())
            print("\n  " + t("check.change_settings") + "\n")
            continue

        describe = choice == "2"
        if describe and not vision_ready:
            # Explain rather than refuse silently, and leave the door open: the
            # setup offered here is the only way a non-technical user gets a key
            # into .env without opening a text editor.
            decision = explain_vision_missing(config)
            if decision == "back":
                continue
            describe = decision == "describe"

        if not videos:
            print("\n  " + t("app.nothing_to_process", path=inbox))
            return 1

        return _start_run(config, videos, describe=describe)


def _start_run(config: Config, videos: list[Path], describe: bool) -> int:
    """Confirm the plan with the user, then process every video."""
    machine, recommended = show_machine(config)

    if describe:
        ready = [name for name, ok, _ in available_backends() if ok]
        if ready:
            print("\n  " + t("vision.found", backend=ready[0]))
        else:
            describe = setup_vision(machine, total_audio_seconds(videos, config))
            if not describe and not ask_yes_no(
                "\n  " + t("run.continue_transcript_only"), True
            ):
                return 1

    # Measure the videos rather than guessing. Quoting "about 19 minutes" for a
    # twenty-second clip destroys any trust in the other numbers on screen.
    total_seconds = total_audio_seconds(videos, config)
    model = choose_model(config, machine, recommended, total_seconds)
    config.values["transcription.model"] = model

    total = estimate_runtime(model, total_seconds, machine)
    print(f"\n{RULE}")
    print("  " + t("run.about_to", count=len(videos), model=model))
    print("  " + t("run.rough_time", time=format_duration(total))
          + (t("run.plus_description") if describe else "."))
    print("  " + t("run.leave_running"))
    print(RULE)
    if not ask_yes_no("\n  " + t("prompt.start_now"), True):
        return 0

    options = RunOptions(describe_video=describe)
    failures = 0
    for position, video in enumerate(videos, start=1):
        reporter = Reporter(total_steps=8 if describe else 5)
        reporter.banner(t("app.video_n_of_m", position=position, total=len(videos)), video.name)
        try:
            result = process_video(video, config, options, reporter, machine)
            reporter.banner(t("app.finished"), str(result.output_dir))
            for path in result.files:
                print(f"    {path.name}")
            if result.warnings:
                print("\n  " + t("app.please_note"))
                for warning in result.warnings:
                    print_wrapped(warning)
        except Exception as exc:  # noqa: BLE001 - report and carry on to the next file
            failures += 1
            print("\n  " + t("app.could_not_process", name=video.name))
            print_wrapped(str(exc), indent="     ")

    print(f"\n{RULE}")
    print("  " + t("app.done", path=config.output_dir))
    if failures:
        print("  " + t("app.failed_count", count=failures))
    print(RULE + "\n")
    return 1 if failures else 0

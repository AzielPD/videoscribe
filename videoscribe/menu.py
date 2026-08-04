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
from .timecode import format_duration
from .tools import ToolMissing, check_all, find_ffmpeg
from .vision import available_backends

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
    """Ask a yes/no question, accepting both English and Spanish answers."""
    accepted = YES_WORDS | NO_WORDS
    fallback = "y" if default else "n"
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


def choose_model(config: Config, machine, recommended: str, audio_seconds: float) -> str:
    """Let the user pick a transcription model, with times and sizes shown."""
    print(f"\n{RULE}\n {t('model.header')}\n{RULE}")
    print("  " + t("model.explain"))
    print()
    print(f"  {'':3} {t('model.col_model'):<10} {t('model.col_time'):<24} "
          f"{t('model.col_download'):<11} {t('model.col_status')}")
    print(f"  {THIN}")

    options: dict[str, str] = {}
    for index, name in enumerate(SELECTABLE_MODELS, start=1):
        if not can_run(name, machine):
            print(f"  {index:>2}) {name:<10} {'-':<24} {'-':<11} {t('model.too_big')}")
            continue
        runtime = format_duration(estimate_runtime(name, audio_seconds, machine))
        size = f"{MODEL_DOWNLOAD_MB.get(name, 0)} MB"
        marks = []
        if name == recommended:
            marks.append(t("model.recommended"))
        if name == config.model:
            marks.append(t("model.current"))
        if model_is_downloaded(name):
            marks.append(t("model.downloaded"))
        print(f"  {index:>2}) {name:<10} {runtime:<24} {size:<11} {', '.join(marks)}")
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
            print("\n  " + t("check.run_installer"))
            return 2

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

        print(f"\n{RULE}\n {t('menu.header')}\n{RULE}")
        print("  1) " + t("menu.option_transcript"))
        print("  2) " + t("menu.option_describe"))
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

        if not videos:
            print("\n  " + t("app.nothing_to_process", path=inbox))
            return 1

        return _start_run(config, videos, describe=(choice == "2"))


def _start_run(config: Config, videos: list[Path], describe: bool) -> int:
    """Confirm the plan with the user, then process every video."""
    machine, recommended = show_machine(config)

    if describe:
        ready = [name for name, ok, _ in available_backends() if ok]
        if not ready:
            print(f"\n{RULE}")
            print_wrapped(t("run.no_vision_options"), indent="  ")
            print("    " + t("run.no_vision_claude"))
            print("    " + t("run.no_vision_key"))
            print(RULE)
            if not ask_yes_no("\n  " + t("run.continue_transcript_only"), True):
                return 1
            describe = False
        else:
            print("\n  " + t("run.vision_will_use", backend=ready[0]))

    # A representative length purely so the model table shows sensible times;
    # the real duration is measured per video once the run starts.
    approximate_seconds = 3000.0
    model = choose_model(config, machine, recommended, approximate_seconds)
    config.values["transcription.model"] = model

    total = sum(estimate_runtime(model, approximate_seconds, machine) for _ in videos)
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

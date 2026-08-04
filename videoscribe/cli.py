"""Command-line interface.

Commands
--------
``(no arguments)``  open the interactive menu
``run``             process videos from the inbox, or one named file
``doctor``          report what is installed and what this computer can run
``models``          list transcription models with times for this computer

Examples
--------
::

    python videoscribe.py                          # menu
    python videoscribe.py run                      # everything in inbox/
    python videoscribe.py run --describe           # also describe the picture
    python videoscribe.py run --file movie.mp4 --model medium
    python videoscribe.py run --speakers 2 --resume
    python videoscribe.py doctor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .i18n import detect_system_language, set_language, t
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
from .tools import ToolMissing, check_all
from .vision import available_backends

RULE = "=" * 70


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videoscribe",
        description="Turn a video into a transcript and, optionally, a written "
                    "account of what happens on screen.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with no arguments for an interactive menu.",
    )
    # --ui-language is shared by every subcommand through a parent parser.
    # Declaring it on both the main parser and a subparser would let the
    # subparser's default (None) overwrite a value given before the command.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--ui-language", choices=["en", "es"],
                        help="language of the messages on screen: en or es")

    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", parents=[common],
                                help="process one or more videos")
    run.add_argument("--file", type=Path,
                     help="a single video; default is every video in the inbox folder")
    run.add_argument("--describe", action="store_true",
                     help="also describe what is visible on screen (needs an image model)")
    run.add_argument("--model",
                     help="transcription model: tiny, base, small, medium, large-v3")
    run.add_argument("--language",
                     help="two-letter language code such as es or en, or 'auto'")
    run.add_argument("--speakers", type=int,
                     help="how many people speak; 0 asks the program to work it out")
    run.add_argument("--max-speakers", type=int,
                     help="upper limit when the speaker count is worked out automatically")
    run.add_argument("--start", help="skip to this point, as HH:MM:SS")
    run.add_argument("--duration", help="process only this much, as HH:MM:SS")
    run.add_argument("--frame-interval", type=int,
                     help="seconds between video frames for the description (default 10)")
    run.add_argument("--window", type=int, dest="window_seconds",
                     help="seconds of video described per request (default 120)")
    run.add_argument("--vision-backend", default="auto",
                     help="auto, claude-cli, anthropic, openai, gemini")
    run.add_argument("--resume", action="store_true",
                     help="reuse whatever was already produced and only redo what is missing")
    run.add_argument("--keep-work", action="store_true",
                     help="keep the temporary audio and frames")
    run.add_argument("--output", type=Path, help="results folder (default: output/)")
    run.add_argument("--quiet", action="store_true", help="print less")

    subparsers.add_parser("doctor", parents=[common],
                          help="check the installation and this computer")
    subparsers.add_parser("models", parents=[common],
                          help="list transcription models and their cost here")

    return parser


def _overrides_from(args: argparse.Namespace) -> dict:
    """Map command-line arguments onto dotted configuration keys."""
    mapping = {
        "transcription.model": getattr(args, "model", None),
        "transcription.language": getattr(args, "language", None),
        "speakers.count": getattr(args, "speakers", None),
        "speakers.max_count": getattr(args, "max_speakers", None),
        "narration.frame_interval_seconds": getattr(args, "frame_interval", None),
        "narration.window_seconds": getattr(args, "window_seconds", None),
    }
    if getattr(args, "output", None):
        mapping["paths.output"] = str(args.output)
    if getattr(args, "keep_work", False):
        mapping["cleanup.keep_wav"] = True
        mapping["cleanup.keep_frames"] = True
    return {key: value for key, value in mapping.items() if value is not None}


def apply_language(config, requested: str | None = None) -> None:
    """Pick the interface language: command line, then config, then the OS."""
    set_language(requested or config.ui_language or detect_system_language())


def command_doctor(requested: str | None = None) -> int:
    config = load_config()
    apply_language(config, requested)
    machine = profile_machine(config.output_dir)
    recommended, reason = recommend_model(machine)

    print(f"\n{RULE}\n {t('doctor.computer')}\n{RULE}")
    for line in machine.summary():
        print(f"  {line}")

    print(f"\n{RULE}\n {t('check.programs_header')}\n{RULE}")
    problems = 0
    for status in check_all(config.ffmpeg_override):
        print(status.line())
        if status.required and not status.ok:
            problems += 1

    print(f"\n{RULE}\n {t('doctor.vision_header')}\n{RULE}")
    for name, ready, explanation in available_backends():
        print(f"  [{'OK     ' if ready else 'not set'}] {name:<16} {explanation}")

    print(f"\n{RULE}\n {t('doctor.recommendation')}\n{RULE}")
    print("  " + t("doctor.model_line", model=recommended))
    print(f"  {reason}")

    print(f"\n{RULE}\n {t('doctor.folders')}\n{RULE}")
    print("  " + t("doctor.videos_in", path=config.inbox_dir))
    print("  " + t("doctor.results_in", path=config.output_dir))

    print(f"\n{RULE}\n {t('doctor.settings')}\n{RULE}")
    print(config.describe())
    print()

    if problems:
        print("  " + t("doctor.missing_count", count=problems) + "\n")
    return 1 if problems else 0


def command_models(requested: str | None = None) -> int:
    config = load_config()
    apply_language(config, requested)
    machine = profile_machine(config.output_dir)
    recommended, _ = recommend_model(machine)
    one_hour = 3600.0

    print(f"\n{RULE}\n {t('models.header')}\n{RULE}")
    print("  " + t("models.for_one_hour") + "\n")
    print(f"  {t('model.col_model'):<10} {t('model.col_time'):<24} "
          f"{t('model.col_download'):<11} {t('model.col_status')}")
    print(f"  {'-' * 66}")
    for name in ["tiny", "base", "small", "medium", "large-v3"]:
        if not can_run(name, machine):
            print(f"  {name:<10} {'-':<24} {'-':<11} {t('models.needs_memory')}")
            continue
        runtime = format_duration(estimate_runtime(name, one_hour, machine))
        size = f"{MODEL_DOWNLOAD_MB.get(name, 0)} MB"
        marks = []
        if name == recommended:
            marks.append(t("models.recommended_here"))
        if name == config.model:
            marks.append(t("model.current"))
        if model_is_downloaded(name):
            marks.append(t("model.downloaded"))
        print(f"  {name:<10} {runtime:<24} {size:<11} {', '.join(marks)}")
    print("\n  " + t("models.change_with"))
    print("  " + t("models.or_permanently") + "\n")
    return 0


def command_run(args: argparse.Namespace) -> int:
    config = load_config(overrides=_overrides_from(args))
    apply_language(config, getattr(args, "ui_language", None))
    machine = profile_machine(config.output_dir)

    if args.file:
        if not args.file.is_file():
            print(f"No such file: {args.file}")
            return 2
        videos = [args.file]
    else:
        videos = find_videos(config.inbox_dir)
        if not videos:
            print(f"\n  No videos found in {config.inbox_dir}")
            print("  Copy your video files there, or pass --file <path>\n")
            return 1

    options = RunOptions(
        describe_video=args.describe,
        start=args.start,
        duration=args.duration,
        resume=args.resume,
        vision_backend=args.vision_backend,
        quiet=args.quiet,
    )

    failures = 0
    for position, video in enumerate(videos, start=1):
        reporter = Reporter(total_steps=8 if args.describe else 5, quiet=args.quiet)
        reporter.banner(t("app.video_n_of_m", position=position, total=len(videos)),
                        video.name)
        try:
            result = process_video(video, config, options, reporter, machine)
            reporter.banner(t("app.finished"), str(result.output_dir))
            for path in result.files:
                print(f"    {path.name}")
            for warning in result.warnings:
                print(f"    ! {warning}")
        except (ToolMissing, RuntimeError, ValueError) as exc:
            failures += 1
            print(f"\n  !! {video.name}: {exc}\n")
        except KeyboardInterrupt:
            print("\n  Stopped. Re-run with --resume to carry on where this left off.\n")
            return 130

    print("\n  " + t("app.results_in", path=config.output_dir) + "\n")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    # No arguments at all means the user probably double-clicked something.
    if not argv:
        from .menu import run_menu

        return run_menu()

    args = build_parser().parse_args(argv)
    requested = getattr(args, "ui_language", None)
    if args.command == "doctor":
        return command_doctor(requested)
    if args.command == "models":
        return command_models(requested)
    if args.command == "run":
        return command_run(args)

    build_parser().print_help()
    return 0

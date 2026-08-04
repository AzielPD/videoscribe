"""End-to-end processing of one video.

The run is a sequence of visible, numbered steps:

1. Inspect the video file
2. Extract the audio
3. Convert speech to text
4. Tell the speakers apart
5. Write the transcript files
6. (optional) Extract video frames
7. (optional) Describe each stretch of video
8. (optional) Write the final account

Steps 6 to 8 only happen when a visual description was requested *and* an
image-capable model is configured. Everything before that works offline with no
account of any kind.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import writers
from .audio import extract_audio, extract_frames, probe, read_wav_mono
from .config import Config
from .diarize import diarize
from .i18n import t
from .narrate import build_windows, narrate_window, synthesise
from .progress import Reporter
from .system import MachineProfile, estimate_runtime, profile_machine
from .timecode import format_duration, format_timecode, parse_timecode
from .tools import find_ffmpeg
from .transcribe import Transcript, summarise, transcribe
from .vision import DEFAULT_MODELS, VisionUnavailable, select_backend

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".ts", ".3gp",
}


@dataclass
class RunOptions:
    """Everything that can change between two runs of the same video."""

    describe_video: bool = False
    start: str | None = None
    duration: str | None = None
    resume: bool = False
    vision_backend: str = "auto"
    quiet: bool = False


@dataclass
class RunResult:
    """What a completed run produced."""

    video: Path
    output_dir: Path
    files: list[Path] = field(default_factory=list)
    speaker_count: int = 0
    warnings: list[str] = field(default_factory=list)


def find_videos(folder: Path) -> list[Path]:
    """Every video file directly inside ``folder``, sorted by name."""
    if not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def output_folder_for(video: Path, output_root: Path) -> Path:
    """Result folder for one video: ``output/<video file name without extension>``.

    Recordings from phones are usually already named ``VID_20250723_130058``,
    which makes a good folder name. Anything else keeps its own stem, so the
    link back to the original file is never lost.
    """
    return output_root / video.stem


def process_video(
    video: Path,
    config: Config,
    options: RunOptions,
    reporter: Reporter | None = None,
    machine: MachineProfile | None = None,
) -> RunResult:
    """Run the whole pipeline over one video file."""
    wants_description = options.describe_video and config.narration_enabled
    total_steps = 8 if wants_description else 5
    reporter = reporter or Reporter(total_steps)
    reporter.total_steps = total_steps
    machine = machine or profile_machine(video.parent)

    output_dir = output_folder_for(video, config.output_dir)
    work_dir = output_dir / "work"
    data_dir = output_dir / "data"
    for folder in (output_dir, work_dir, data_dir):
        folder.mkdir(parents=True, exist_ok=True)

    result = RunResult(video=video, output_dir=output_dir)
    ffmpeg = find_ffmpeg(config.ffmpeg_override)

    # --- 1. Inspect ------------------------------------------------------
    reporter.step(t("step.reading"))
    info = probe(ffmpeg, video)
    size_gb = video.stat().st_size / (1024 ** 3)
    reporter.detail(f"{video.name}  ({size_gb:.2f} GB)")
    reporter.detail(
        t("detail.length", duration=format_timecode(info.duration))
        + (t("detail.picture", width=info.width, height=info.height) if info.width else "")
    )
    if not info.has_audio:
        raise RuntimeError(t("error.no_audio", name=video.name))

    span_start = parse_timecode(options.start) if options.start else 0.0
    span_length = parse_timecode(options.duration) if options.duration else info.duration - span_start
    if span_length <= 0:
        raise RuntimeError(t("error.span_outside"))

    estimate = estimate_runtime(config.model, span_length, machine)
    reporter.detail(t("detail.estimate", model=config.model,
                      time=format_duration(estimate)))

    # --- 2. Audio ---------------------------------------------------------
    reporter.step(t("step.extracting_audio"))
    mp3_path = output_dir / "01_audio.mp3"
    wav_path = work_dir / "audio_16k.wav"
    needs_extraction = not (options.resume and mp3_path.is_file() and wav_path.is_file())

    if needs_extraction:
        with reporter.bar(span_length, unit="time") as bar:
            extract_audio(
                ffmpeg, video, mp3_path, wav_path,
                bitrate=config.mp3_bitrate, sample_rate=config.sample_rate,
                start=options.start, duration=options.duration,
                total_seconds=span_length, on_progress=bar.update,
            )
            bar.close(t("bar.extracted"))
    else:
        reporter.detail(t("detail.already_extracted"))
    reporter.done(f"01_audio.mp3 ({mp3_path.stat().st_size / (1024 ** 2):.1f} MB)")
    result.files.append(mp3_path)

    # --- 3. Speech to text ------------------------------------------------
    reporter.step(t("step.transcribing"))
    transcript_json = data_dir / "transcript.json"

    if options.resume and transcript_json.is_file():
        import json

        stored = json.loads(transcript_json.read_text(encoding="utf-8"))
        transcript = Transcript(
            segments=stored["segments"],
            language=stored["language"],
            language_probability=stored["language_probability"],
            duration=stored["duration"],
            model=stored.get("model", config.model),
        )
        reporter.detail(t("detail.reusing_transcript", count=len(transcript.segments)))
        # Stored segment times are already relative to the source video.
    else:
        reporter.detail(t("detail.model_threads", model=config.model,
                          language=config.language, threads=config.cpu_threads))
        reporter.detail(t("detail.first_download"))
        with reporter.bar(span_length, unit="time") as bar:
            transcript = transcribe(
                wav_path,
                model_size=config.model,
                language=config.language,
                compute_type=config.compute_type,
                beam_size=config.beam_size,
                cpu_threads=config.cpu_threads,
                on_progress=lambda done, total: bar.update(done),
            )
            bar.close(t("bar.transcribed"))
        reporter.detail(summarise(transcript))

        # The recogniser saw only the extracted stretch, so its times start at
        # zero. Shift them onto the source video's clock straight away: every
        # timecode this program writes must point at a moment in the original
        # file, otherwise a reader cannot verify it.
        if span_start:
            for segment in transcript.segments:
                segment["start"] += span_start
                segment["end"] += span_start

    if not transcript.segments:
        raise RuntimeError(t("error.no_speech"))

    # --- 4. Speakers ------------------------------------------------------
    reporter.step(t("step.speakers"))
    audio = read_wav_mono(wav_path, expected_rate=config.sample_rate)
    with reporter.bar(1) as bar:
        diarization = diarize(
            audio, transcript.segments,
            speaker_count=config.speaker_count,
            max_speakers=config.max_speakers,
            audio_offset=span_start,
        )
        bar.close(t("bar.grouped"))

    result.speaker_count = diarization.speaker_count
    reporter.detail(t("detail.speakers_found", count=diarization.speaker_count))
    for number in sorted(diarization.speaking_time):
        reporter.detail("  " + t("detail.speech_time",
                                 speaker=f"{config.speaker_label}{number}",
                                 duration=format_timecode(diarization.speaking_time[number])))

    note = diarization.quality_note()
    if note:
        reporter.warn(note)
        result.warnings.append(note)

    # --- 5. Transcript files ----------------------------------------------
    reporter.step(t("step.writing_transcript"))
    result.files.append(
        writers.write_transcript_txt(
            output_dir / "02_transcript.txt", transcript, video.name,
            config.speaker_label, diarization.speaker_count,
            span=(span_start, span_start + span_length),
        )
    )
    result.files.append(
        writers.write_subtitles_srt(output_dir / "03_subtitles.srt", transcript, config.speaker_label)
    )
    writers.write_transcript_json(
        transcript_json, transcript,
        extra={
            "speaker_count": diarization.speaker_count,
            "source": video.name,
            # Segment times are on the source video's clock; this says where the
            # extracted audio begins, which a resume needs in order to index it.
            "time_offset": span_start,
            "covers_seconds": span_length,
        },
    )
    reporter.done("02_transcript.txt, 03_subtitles.srt")

    if not wants_description:
        _finish(reporter, config, result, work_dir, video, transcript, options, None)
        return result

    # --- 6 to 8. Visual description ---------------------------------------
    try:
        backend = select_backend(options.vision_backend)
    except VisionUnavailable as exc:
        reporter.warn(str(exc))
        result.warnings.append(t("warn.vision_skipped"))
        _finish(reporter, config, result, work_dir, video, transcript, options, None)
        return result

    vision_model, synthesis_model = DEFAULT_MODELS.get(backend.name, ("", ""))
    if config.vision_model:
        vision_model = config.vision_model
    if config.synthesis_model:
        synthesis_model = config.synthesis_model

    reporter.step(t("step.extracting_frames"))
    frames_dir = work_dir / "frames"
    existing = sorted(frames_dir.glob("frame_*.jpg")) if frames_dir.is_dir() else []
    if options.resume and existing:
        frames = existing
        reporter.detail(t("detail.reusing_frames", count=len(frames)))
    else:
        with reporter.bar(span_length, unit="time") as bar:
            frames = extract_frames(
                ffmpeg, video, frames_dir,
                interval_seconds=config.frame_interval,
                max_edge=config.max_frame_edge,
                start=options.start, duration=options.duration,
                total_seconds=span_length, on_progress=bar.update,
            )
            bar.close(t("bar.extracted"))
    reporter.detail(t("detail.frames_every", count=len(frames),
                      interval=config.frame_interval))

    reporter.step(t("step.describing", backend=backend.name))
    windows = [
        window
        for window in build_windows(
            frames, transcript.segments, span_length,
            config.frame_interval, config.window_seconds, offset=span_start,
        )
        if not window.is_empty
    ]

    parts_dir = work_dir / "sections"
    parts_dir.mkdir(parents=True, exist_ok=True)
    paragraphs: list[tuple] = []
    failures = 0

    with reporter.bar(len(windows)) as bar:
        for position, window in enumerate(windows, start=1):
            part_file = parts_dir / f"section_{window.index:04d}.txt"
            if options.resume and part_file.is_file() and part_file.stat().st_size > 0:
                paragraphs.append((window, part_file.read_text(encoding="utf-8")))
                bar.update(position, f"{format_timecode(window.start)} {t('bar.reused')}")
                continue
            try:
                paragraph, removed = narrate_window(
                    backend, window, vision_model, config.speaker_label, config.narration_language
                )
                part_file.write_text(paragraph, encoding="utf-8")
                paragraphs.append((window, paragraph))
                suffix = f"{format_timecode(window.start)}"
                if removed:
                    suffix += "  " + t("detail.invented_removed", count=removed)
                bar.update(position, suffix)
            except Exception as exc:  # noqa: BLE001 - one bad window must not kill the run
                failures += 1
                bar.update(position, f"{format_timecode(window.start)} FAILED")
                result.warnings.append(f"Section at {format_timecode(window.start)}: {exc}")
        bar.close(t("detail.sections_described",
                    done=len(paragraphs), total=len(windows)))

    if failures:
        reporter.warn(t("detail.sections_failed", count=failures))
    if not paragraphs:
        raise RuntimeError(t("error.no_sections"))

    reporter.step(t("step.writing_account"))
    result.files.append(
        writers.write_narrative_markdown(
            output_dir / "05_narrative_by_section.md",
            video.name,
            [(window.start, text) for window, text in paragraphs],
        )
    )
    with reporter.bar(1) as bar:
        account = synthesise(backend, paragraphs, synthesis_model, config.narration_language)
        bar.close(t("bar.written"))

    result.files.append(
        writers.write_narrative_txt(
            output_dir / "04_narrative.txt", account, video.name,
            frame_count=len(frames), frame_interval=config.frame_interval,
            segment_count=len(transcript.segments), backend_name=backend.name,
            span=(span_start, span_start + span_length),
        )
    )
    reporter.done("04_narrative.txt, 05_narrative_by_section.md")

    _finish(reporter, config, result, work_dir, video, transcript, options, backend.name)
    return result


def _finish(
    reporter: Reporter,
    config: Config,
    result: RunResult,
    work_dir: Path,
    video: Path,
    transcript: Transcript,
    options: RunOptions,
    backend_name: str | None,
) -> None:
    """Write the folder guide and manifest, then tidy up temporary files."""
    entries = [
        ("01_audio.mp3", "The sound of the video on its own."),
        ("02_transcript.txt", "Who said what, with the time of each turn."),
        ("03_subtitles.srt", "The same text as subtitles; open it with the video."),
    ]
    if backend_name:
        entries += [
            ("04_narrative.txt", "A written account of what happens in the video."),
            ("05_narrative_by_section.md", "The same account, split into short sections."),
        ]
    entries += [
        ("data/", "Machine-readable files. Keep these to re-run a step later."),
        ("work/", "Temporary files. Safe to delete."),
    ]
    writers.write_readme(result.output_dir / "00_READ_ME_FIRST.txt", entries)

    writers.write_manifest(
        result.output_dir / "data" / "manifest.json",
        {
            "source_file": video.name,
            "source_size_bytes": video.stat().st_size,
            "duration_seconds": transcript.duration,
            "language": transcript.language,
            "transcription_model": transcript.model,
            "speakers_found": result.speaker_count,
            "visual_description": backend_name,
            "settings": config.values,
            "warnings": result.warnings,
        },
    )

    if not config.keep_wav:
        wav = work_dir / "audio_16k.wav"
        if wav.is_file():
            wav.unlink()
    if not config.keep_frames and backend_name:
        frames_dir = work_dir / "frames"
        if frames_dir.is_dir():
            shutil.rmtree(frames_dir, ignore_errors=True)

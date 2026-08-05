"""Speech to text with faster-whisper.

Model sizes, measured on a 16-core CPU with no GPU, for 50 minutes of audio:

===========  ==================  ==========================================
Model        Time                Notes
===========  ==================  ==========================================
``tiny``     about 5 minutes     draft quality; useful only for a quick look
``base``     about 10 minutes    still rough
``small``    about 20 minutes    good default
``medium``   about 50 minutes    clearly better on names and figures
``large-v3`` 2 to 3 hours        best available, painful without a GPU
===========  ==================  ==========================================

The first run of any size downloads the model (roughly 75 MB for ``small``,
1.5 GB for ``large-v3``) and caches it under the user's home folder.
"""

from __future__ import annotations

import os
import threading
import warnings
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .i18n import t
from .timecode import format_timecode


@dataclass
class Transcript:
    """Everything the recogniser produced for one recording."""

    segments: list[dict]  # {"start": float, "end": float, "text": str}
    language: str
    language_probability: float
    duration: float
    model: str


def transcribe(
    wav_path: Path,
    model_size: str = "small",
    language: str = "es",
    compute_type: str = "int8",
    beam_size: int = 5,
    cpu_threads: int = 4,
    on_progress: Callable[[float, float], None] | None = None,
) -> Transcript:
    """Run speech recognition over a 16 kHz mono WAV.

    Parameters
    ----------
    language:
        Two-letter code such as ``es`` or ``en``. Pass ``"auto"`` to let the
        model detect it, which costs a little accuracy on short recordings.
    on_progress:
        Called as ``(seconds_done, total_seconds)`` roughly every 30 seconds of
        audio, so a caller can print a progress line.
    """
    # These warnings are about how Hugging Face caches model files. They are
    # harmless, they scroll the progress display away, and there is nothing a
    # user of this tool can usefully do about them.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.*")

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SystemExit(
            "faster-whisper is not installed.\n"
            "Run:  pip install -r requirements.txt"
        ) from exc

    model = WhisperModel(
        model_size, device="cpu", compute_type=compute_type, cpu_threads=cpu_threads
    )

    options: dict = {
        "beam_size": beam_size,
        # Voice activity detection trims silence, which both speeds things up
        # and stops the model from hallucinating text over quiet stretches.
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500},
        # Without this the model can fall into repetition loops, echoing a
        # sentence it already produced.
        "condition_on_previous_text": False,
    }
    if language and language.lower() != "auto":
        options["language"] = language

    iterator, info = model.transcribe(str(wav_path), **options)

    segments: list[dict] = []
    last_reported = -30.0
    for item in iterator:
        text = item.text.strip()
        if text:
            segments.append({"start": item.start, "end": item.end, "text": text})
        if on_progress and item.end - last_reported >= 30:
            last_reported = item.end
            on_progress(item.end, info.duration)

    return Transcript(
        segments=segments,
        language=info.language,
        language_probability=float(info.language_probability),
        duration=float(info.duration),
        model=model_size,
    )


def transcribe_in_parallel(
    wav_path: Path,
    ffmpeg: str,
    workers: int,
    work_dir: Path,
    model_size: str = "small",
    language: str = "es",
    compute_type: str = "int8",
    beam_size: int = 5,
    cpu_threads: int = 4,
    sample_rate: int = 16000,
    on_progress: Callable[[float, float], None] | None = None,
    on_plan: Callable[[str], None] | None = None,
) -> Transcript:
    """Transcribe several parts of a recording at once.

    The recording is cut at silences into ``workers`` pieces, and one shared
    model transcribes them concurrently. Falls back to :func:`transcribe` when
    the recording is too short to split, or when no silence sits near a useful
    boundary -- cutting a word in half would corrupt both sides of the cut.

    Segment times come back on the original recording's clock, so the caller
    cannot tell the difference apart from the wall time.
    """
    from concurrent.futures import ThreadPoolExecutor

    from .parallel import choose_split_points, describe_plan, find_silences, split_wav

    if workers < 2:
        return transcribe(wav_path, model_size, language, compute_type,
                          beam_size, cpu_threads, on_progress)

    with wave.open(str(wav_path), "rb") as handle:
        total_seconds = handle.getnframes() / float(handle.getframerate())

    points = choose_split_points(total_seconds, workers, find_silences(ffmpeg, wav_path))
    if not points:
        # No clean place to cut. One piece is slower but never mangles a word.
        return transcribe(wav_path, model_size, language, compute_type,
                          beam_size, cpu_threads, on_progress)

    chunks = split_wav(wav_path, points, work_dir / "chunks", sample_rate)
    if on_plan:
        on_plan(describe_plan(workers, chunks))

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.*")

    from faster_whisper import WhisperModel

    # num_workers lets concurrent transcribe() calls share one loaded model.
    # Loading it once per chunk instead would multiply memory by `workers`.
    model = WhisperModel(
        model_size, device="cpu", compute_type=compute_type,
        cpu_threads=cpu_threads, num_workers=workers,
    )

    options: dict = {
        "beam_size": beam_size,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500},
        "condition_on_previous_text": False,
    }
    if language and language.lower() != "auto":
        options["language"] = language

    # Progress is the sum of what every worker has finished so far, which keeps
    # the bar monotonic even though the chunks finish out of order.
    finished = {chunk.index: 0.0 for chunk in chunks}
    lock = threading.Lock()

    def run(chunk):
        iterator, info = model.transcribe(str(chunk.path), **options)
        found = []
        for item in iterator:
            text = item.text.strip()
            if text:
                found.append({
                    "start": item.start + chunk.start,
                    "end": item.end + chunk.start,
                    "text": text,
                })
            if on_progress:
                with lock:
                    finished[chunk.index] = item.end
                    on_progress(sum(finished.values()), total_seconds)
        with lock:
            finished[chunk.index] = chunk.duration
            if on_progress:
                on_progress(sum(finished.values()), total_seconds)
        return found, info

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, chunks))

    segments = sorted(
        (segment for found, _ in results for segment in found),
        key=lambda item: item["start"],
    )
    first_info = results[0][1]

    for chunk in chunks:
        chunk.path.unlink(missing_ok=True)

    return Transcript(
        segments=segments,
        language=first_info.language,
        language_probability=float(first_info.language_probability),
        duration=total_seconds,
        model=model_size,
    )


def merge_consecutive(segments: list[dict], max_gap: float = 2.0) -> list[dict]:
    """Join neighbouring segments from the same speaker into one paragraph.

    Whisper emits a segment every few seconds; without this a transcript reads
    as a stutter of one-line turns rather than as speech.
    """
    merged: list[dict] = []
    for segment in segments:
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous.get("speaker") == segment.get("speaker")
            and segment["start"] - previous["end"] < max_gap
        ):
            previous["text"] += " " + segment["text"]
            previous["end"] = segment["end"]
        else:
            merged.append(dict(segment))
    return merged


def format_speaker(label: str, number: int) -> str:
    """Build the display name for a speaker, e.g. ``Person1``."""
    return f"{label}{number}"


def summarise(transcript: Transcript) -> str:
    """One-line description used in logs."""
    return t(
        "detail.transcript_summary",
        count=len(transcript.segments),
        language=transcript.language,
        confidence=f"{transcript.language_probability:.2f}",
        duration=format_timecode(transcript.duration),
    )

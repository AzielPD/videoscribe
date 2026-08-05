"""Audio and frame extraction with ffmpeg.

Two artefacts come out of a source video:

* an **MP3**, which is the deliverable a person listens to, and
* a **16 kHz mono WAV**, which is what the speech model and the speaker
  separation code read.

Both are produced in a *single* pass so a multi-gigabyte file is read from disk
only once.
"""

from __future__ import annotations

import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .tools import find_ffprobe


@dataclass
class MediaInfo:
    """The handful of facts we need about a source file."""

    duration: float  # seconds
    has_audio: bool
    width: int = 0
    height: int = 0


def probe(ffmpeg: str, video: Path) -> MediaInfo:
    """Read duration and stream layout using ffprobe."""
    ffprobe = find_ffprobe(ffmpeg)
    result = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=codec_type,width,height",
            "-of", "default=noprint_wrappers=1",
            str(video),
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {video.name}:\n{result.stderr.strip()}")

    duration, has_audio, width, height = 0.0, False, 0, 0
    for line in result.stdout.splitlines():
        key, _, value = line.partition("=")
        if key == "duration" and value not in ("", "N/A"):
            duration = float(value)
        elif key == "codec_type" and value == "audio":
            has_audio = True
        elif key == "width" and value.isdigit() and not width:
            width = int(value)
        elif key == "height" and value.isdigit() and not height:
            height = int(value)

    if duration <= 0:
        raise RuntimeError(f"{video.name} reports no duration; is it a valid video file?")
    return MediaInfo(duration=duration, has_audio=has_audio, width=width, height=height)


def _run_ffmpeg(args: list[str], total_seconds: float = 0.0, on_progress=None) -> None:
    """Run ffmpeg, optionally driving a progress callback.

    ``-progress pipe:1`` makes ffmpeg emit ``key=value`` lines on stdout, which
    is far easier to parse than the human-readable ``-stats`` output -- and it
    keeps the terminal clean so our own progress bar is the only thing drawing.
    """
    if on_progress is None or total_seconds <= 0:
        result = subprocess.run(
            args + ["-loglevel", "error", "-nostats"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed (exit code {result.returncode}):\n"
                               f"{result.stderr.strip()[:500]}")
        return

    process = subprocess.Popen(
        args + ["-loglevel", "error", "-nostats", "-progress", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    # stdout=PIPE guarantees this, but `python -O` strips asserts, so the
    # promise is stated as a comment rather than enforced at a cost.
    for line in process.stdout:  # noqa: S101 - see above
        key, _, value = line.strip().partition("=")
        if key == "out_time_ms" and value.isdigit():
            on_progress(min(int(value) / 1_000_000.0, total_seconds))
        elif key == "progress" and value == "end":
            on_progress(total_seconds)

    process.wait()
    if process.returncode != 0:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(
            f"ffmpeg failed (exit code {process.returncode}):\n{stderr.strip()[:500]}"
        )


def _time_args(start: str | None, duration: str | None) -> list[str]:
    """Build the -ss/-t pair.

    Both go *before* -i on purpose. Placed after -i they would only apply to the
    first output file, which silently produces a trimmed MP3 next to a
    full-length WAV.
    """
    args: list[str] = []
    if start:
        args += ["-ss", start]
    if duration:
        args += ["-t", duration]
    return args


def extract_audio(
    ffmpeg: str,
    video: Path,
    mp3_path: Path,
    wav_path: Path | None,
    bitrate: str = "128k",
    sample_rate: int = 16000,
    start: str | None = None,
    duration: str | None = None,
    total_seconds: float = 0.0,
    on_progress=None,
) -> None:
    """Write an MP3 and (optionally) a 16 kHz mono WAV in one ffmpeg pass."""
    mp3_path.parent.mkdir(parents=True, exist_ok=True)

    args = [ffmpeg, "-hide_banner", "-y"]
    args += _time_args(start, duration)
    args += ["-i", str(video)]
    args += ["-vn", "-map", "0:a:0", "-c:a", "libmp3lame",
             "-b:a", bitrate, "-ac", "1", str(mp3_path)]
    if wav_path is not None:
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        args += [
            "-vn", "-map", "0:a:0", "-c:a", "pcm_s16le",
            "-ar", str(sample_rate), "-ac", "1", str(wav_path),
        ]

    _run_ffmpeg(args, total_seconds, on_progress)


def extract_frames(
    ffmpeg: str,
    video: Path,
    frames_dir: Path,
    interval_seconds: int,
    max_edge: int = 1568,
    start: str | None = None,
    duration: str | None = None,
    total_seconds: float = 0.0,
    on_progress=None,
) -> list[Path]:
    """Save one JPEG every ``interval_seconds`` and return them in time order.

    Frames are scaled to fit inside a ``max_edge`` square. 1568 px is the point
    beyond which the vision model downscales anyway, so anything larger costs
    disk and upload time without adding readable detail.
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("frame_*.jpg"):
        stale.unlink()

    scale = f"scale={max_edge}:{max_edge}:force_original_aspect_ratio=decrease"
    args = [ffmpeg, "-hide_banner", "-y"]
    args += _time_args(start, duration)
    args += [
        "-i", str(video),
        "-vf", f"fps=1/{interval_seconds},{scale}",
        "-q:v", "3",
        str(frames_dir / "frame_%05d.jpg"),
    ]

    _run_ffmpeg(args, total_seconds, on_progress)
    return sorted(frames_dir.glob("frame_*.jpg"))


def read_wav_mono(path: Path, expected_rate: int = 16000) -> np.ndarray:
    """Load a 16-bit mono WAV as float32 samples in the range [-1, 1]."""
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1:
            raise ValueError(f"{path.name} must be mono.")
        if handle.getsampwidth() != 2:
            raise ValueError(f"{path.name} must be 16-bit PCM.")
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())

    if rate != expected_rate:
        raise ValueError(f"{path.name} must be {expected_rate} Hz, found {rate} Hz.")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

"""Splitting a long recording across several workers.

Speech recognition on a CPU does not get proportionally faster as you give it
more threads: past roughly four, the extra cores spend most of their time
waiting. Running several *concurrent* transcriptions with fewer threads each
recovers a good part of that loss.

Two things make this safe rather than merely fast:

**One model, many workers.** faster-whisper accepts ``num_workers``, which lets
several ``transcribe`` calls run in parallel against a single loaded model. That
matters because a second copy of ``medium`` is another five gigabytes; on a
16 GB laptop, naive process-level parallelism runs out of memory long before it
runs out of cores.

**Cuts land in silence.** Splitting a recording at an arbitrary second cuts a
word in half and both halves come back wrong. Split points are therefore moved
to the nearest silence that ffmpeg can find, and only kept if one exists nearby.
When no usable silence is found the recording is transcribed in one piece --
slower, but never wrong.
"""

from __future__ import annotations

import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from .system import MODEL_RAM_GB, MachineProfile

# Below this length the setup cost outweighs anything parallelism can win back.
MIN_SECONDS_TO_SPLIT = 240.0

# Each worker wants roughly this many threads before extra ones stop helping.
THREADS_PER_WORKER = 4

# More than this and the coordination cost, and the memory, stop being worth it.
MAX_WORKERS = 4

# How far from an ideal split point we will look for a silence to cut in.
SEARCH_WINDOW_SECONDS = 20.0

# What counts as silence: quieter than this, for at least this long.
SILENCE_THRESHOLD_DB = -30
SILENCE_MIN_SECONDS = 0.4


@dataclass
class Chunk:
    """One piece of the recording, and where it sits in the original."""

    index: int
    start: float
    end: float
    path: Path

    @property
    def duration(self) -> float:
        return self.end - self.start


def plan_worker_count(
    machine: MachineProfile, model: str, audio_seconds: float, configured: int = 0
) -> int:
    """Decide how many transcriptions to run at once.

    ``configured`` overrides the calculation when greater than zero; 1 disables
    splitting entirely. The automatic answer is the smallest of what the cores
    allow, what memory allows, and :data:`MAX_WORKERS`.
    """
    if configured and configured > 0:
        return max(1, configured)

    # A GPU is already saturated by one stream; splitting only adds overhead.
    if machine.has_gpu:
        return 1

    if audio_seconds < MIN_SECONDS_TO_SPLIT:
        return 1

    by_cores = max(1, machine.cores // THREADS_PER_WORKER)

    # Leave 2 GB for the operating system, then see how many copies of the
    # working set fit. The model itself is shared, but each concurrent decode
    # holds its own activations, roughly a third of the model again.
    per_worker_gb = max(0.5, MODEL_RAM_GB.get(model, 2.0) * 0.35)
    usable_gb = max(0.0, machine.ram_gb - 2.0 - MODEL_RAM_GB.get(model, 2.0))
    by_memory = max(1, int(usable_gb // per_worker_gb)) if machine.ram_gb else 1

    return max(1, min(by_cores, by_memory, MAX_WORKERS))


def threads_per_worker(machine: MachineProfile, workers: int) -> int:
    """Split the available cores between the workers, at least one each."""
    return max(1, min(16, machine.cores) // max(1, workers))


def find_silences(ffmpeg: str, audio_path: Path) -> list[tuple[float, float]]:
    """Return ``(start, end)`` for every silence ffmpeg can find.

    ffmpeg reports these on stderr as it scans; there is no machine-readable
    output format for the filter, so the log lines are parsed.
    """
    result = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-nostats", "-i", str(audio_path),
            "-af", f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:d={SILENCE_MIN_SECONDS}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True, check=False,
    )

    silences: list[tuple[float, float]] = []
    pending_start: float | None = None
    for line in result.stderr.splitlines():
        start = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if start:
            pending_start = float(start.group(1))
            continue
        end = re.search(r"silence_end:\s*(-?[\d.]+)", line)
        if end and pending_start is not None:
            silences.append((pending_start, float(end.group(1))))
            pending_start = None
    return silences


def choose_split_points(
    total_seconds: float, workers: int, silences: list[tuple[float, float]]
) -> list[float]:
    """Pick ``workers - 1`` cut points, each in the middle of a silence.

    Returns an empty list when no suitable silence exists near an ideal
    boundary, which the caller reads as "do not split this recording".
    """
    if workers < 2:
        return []

    points: list[float] = []
    for index in range(1, workers):
        ideal = total_seconds * index / workers
        candidates = [
            (abs((start + end) / 2 - ideal), (start + end) / 2)
            for start, end in silences
            if abs((start + end) / 2 - ideal) <= SEARCH_WINDOW_SECONDS
        ]
        if not candidates:
            return []
        points.append(min(candidates)[1])

    # Guard against two boundaries collapsing onto the same silence.
    points = sorted({round(point, 3) for point in points})
    if len(points) != workers - 1:
        return []
    # strict=False on purpose: pairing a list with itself offset by one is
    # meant to stop at the shorter, which is how consecutive pairs are walked.
    if any(later - earlier < 1.0
           for earlier, later in zip(points, points[1:], strict=False)):
        return []
    return points


def split_wav(source: Path, points: list[float], work_dir: Path, sample_rate: int) -> list[Chunk]:
    """Write one WAV per chunk and return them in order.

    Reads and writes with the standard library ``wave`` module rather than
    shelling out again: the audio is already on disk in the exact format we
    need, so copying frame ranges is both faster and lossless.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    for stale in work_dir.glob("chunk_*.wav"):
        stale.unlink()

    with wave.open(str(source), "rb") as reader:
        channels = reader.getnchannels()
        width = reader.getsampwidth()
        rate = reader.getframerate()
        frames = reader.getnframes()
        raw = reader.readframes(frames)

    total_seconds = frames / float(rate)
    boundaries = [0.0] + list(points) + [total_seconds]
    bytes_per_frame = channels * width

    chunks: list[Chunk] = []
    # Same pairwise walk as above: n boundaries describe n-1 chunks.
    for index, (start, end) in enumerate(
            zip(boundaries, boundaries[1:], strict=False)):
        first = int(start * rate) * bytes_per_frame
        last = int(end * rate) * bytes_per_frame
        path = work_dir / f"chunk_{index:02d}.wav"
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(width)
            writer.setframerate(rate)
            writer.writeframes(raw[first:last])
        chunks.append(Chunk(index=index, start=start, end=end, path=path))

    return chunks


def describe_plan(workers: int, chunks: list[Chunk]) -> str:
    """One line explaining the split, for the progress display."""
    if workers < 2 or not chunks:
        return ""
    pieces = " + ".join(f"{chunk.duration / 60:.0f}min" for chunk in chunks)
    return f"{workers} parts in parallel ({pieces})"

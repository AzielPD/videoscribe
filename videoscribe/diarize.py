"""Grouping speech segments by speaker.

The approach is deliberately simple and dependency-free:

1. Describe every segment with the acoustic features from :mod:`.features`.
2. Normalise those features across the whole recording, so a quiet speaker and
   a loud one are compared on voice colour rather than volume.
3. Merge segments bottom-up (agglomerative clustering, average linkage, cosine
   distance) until the desired number of speakers remains.
4. Renumber the groups by who speaks first, so ``Person1`` is always the first
   voice heard.

Accuracy caveat: this separates voices that differ clearly. Similar voices in a
noisy room will be split or merged incorrectly. When the result looks wrong,
re-run with an explicit speaker count -- that is far more reliable than the
automatic estimate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .i18n import t
from .features import SAMPLE_RATE, segment_features

# Segments shorter than this are too noisy to define a cluster; they are still
# labelled, but only after the clusters have been fixed by the longer ones.
MIN_SECONDS_FOR_FITTING = 1.2

# How strongly pitch counts relative to a single normalised MFCC dimension.
PITCH_WEIGHT = 2.5

# If everything merges below this cosine distance, treat the recording as one
# speaker rather than inventing a split.
SINGLE_SPEAKER_THRESHOLD = 0.10


@dataclass
class DiarizationResult:
    """What the caller gets back, alongside the mutated segment list."""

    speaker_count: int
    separation_scores: dict[int, float]
    speaking_time: dict[int, float]

    def quality_note(self) -> str:
        """A plain-language warning when the split looks unconvincing.

        Scores are ratios of merge distances: values near 1.0 mean the data had
        no natural break, so whichever number of speakers was chosen is close to
        arbitrary.
        """
        if not self.separation_scores:
            return ""
        best = max(self.separation_scores.values())
        if best < 1.25:
            return t("warn.speakers_unclear", score=f"{best:.2f}")
        return ""


def average_linkage(vectors: np.ndarray) -> list[tuple[int, int, float]]:
    """Cluster rows bottom-up, returning the merge history.

    Each entry is ``(kept_index, absorbed_index, distance)``. Distances between
    merged groups are updated with the Lance-Williams rule for average linkage,
    which keeps the whole thing to a couple of vectorised operations per merge.
    """
    count = len(vectors)
    unit = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)
    distances = (1.0 - unit @ unit.T).astype(np.float64)
    np.fill_diagonal(distances, np.inf)

    sizes = np.ones(count)
    history: list[tuple[int, int, float]] = []

    for _ in range(count - 1):
        flat = int(np.argmin(distances))
        keep, absorb = divmod(flat, count)
        history.append((keep, absorb, float(distances[keep, absorb])))

        merged = (sizes[keep] * distances[keep, :] + sizes[absorb] * distances[absorb, :]) / (
            sizes[keep] + sizes[absorb]
        )
        distances[keep, :] = merged
        distances[:, keep] = merged
        distances[keep, keep] = np.inf
        sizes[keep] += sizes[absorb]

        # Retire the absorbed row/column so argmin never selects it again.
        distances[absorb, :] = np.inf
        distances[:, absorb] = np.inf

    return history


def labels_for(history: list[tuple[int, int, float]], count: int, clusters: int) -> np.ndarray:
    """Replay the first ``count - clusters`` merges to get cluster ids."""
    parent = list(range(count))

    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]  # path compression
            node = parent[node]
        return node

    for keep, absorb, _ in history[: count - clusters]:
        parent[root(absorb)] = root(keep)

    renumber: dict[int, int] = {}
    labels = np.zeros(count, dtype=int)
    for node in range(count):
        group = root(node)
        renumber.setdefault(group, len(renumber))
        labels[node] = renumber[group]
    return labels


def choose_cluster_count(
    history: list[tuple[int, int, float]], count: int, max_speakers: int
) -> tuple[int, dict[int, float]]:
    """Estimate how many speakers there are from the merge distances.

    ``distance_at(k)`` is how far apart the two groups were when the recording
    went from k+1 clusters down to k. A large jump between k and k-1 means k is
    a natural stopping point, so we score each k by that ratio.
    """

    def distance_at(clusters: int) -> float:
        return history[count - clusters - 1][2] if 0 < clusters < count else float("inf")

    if count < 2 or distance_at(1) < SINGLE_SPEAKER_THRESHOLD:
        return 1, {}

    scores = {
        k: distance_at(k - 1) / max(distance_at(k), 1e-6)
        for k in range(2, min(max_speakers, count) + 1)
    }
    return max(scores, key=scores.get), scores


def diarize(
    audio: np.ndarray,
    segments: list[dict],
    speaker_count: int = 0,
    max_speakers: int = 6,
    audio_offset: float = 0.0,
) -> DiarizationResult:
    """Assign a 1-based speaker number to every segment, in place.

    Parameters
    ----------
    audio:
        The extracted audio as mono float samples at 16 kHz.
    segments:
        Dicts with ``start``/``end`` in seconds; a ``speaker`` key is added.
    speaker_count:
        Force this many speakers. 0 asks for automatic detection.
    audio_offset:
        Where ``audio`` begins in the source video. Segment times are always
        stored relative to the source video, so when only a stretch was
        extracted this offset converts them into positions inside ``audio``.
    """
    if not segments:
        return DiarizationResult(0, {}, {})

    vectors, pitches, usable = [], [], []
    for index, segment in enumerate(segments):
        begin = max(0, int((segment["start"] - audio_offset) * SAMPLE_RATE))
        finish = min(len(audio), int((segment["end"] - audio_offset) * SAMPLE_RATE))
        if finish <= begin:
            continue
        vector, pitch = segment_features(audio[begin:finish])
        if vector is None:
            continue
        vectors.append(vector)
        pitches.append(pitch)
        usable.append(index)

    if len(usable) < 2:
        for segment in segments:
            segment["speaker"] = 1
        total = sum(s["end"] - s["start"] for s in segments)
        return DiarizationResult(1, {}, {1: total})

    # Normalise each feature dimension across the recording (cepstral mean and
    # variance normalisation). This removes the fixed colouring of the room and
    # the microphone, leaving differences between voices.
    matrix = np.vstack(vectors).astype(np.float64)
    matrix = (matrix - matrix.mean(axis=0)) / np.maximum(matrix.std(axis=0), 1e-6)

    pitch_array = np.array(pitches, dtype=np.float64)
    if np.isfinite(pitch_array).sum() >= 2:
        pitch_array = np.where(np.isfinite(pitch_array), pitch_array, np.nanmean(pitch_array))
        pitch_array = (pitch_array - pitch_array.mean()) / max(pitch_array.std(), 1e-6)
    else:
        pitch_array = np.zeros(len(matrix))
    matrix = np.hstack([matrix, (PITCH_WEIGHT * pitch_array)[:, None]])

    durations = np.array([segments[i]["end"] - segments[i]["start"] for i in usable])
    long_enough = np.where(durations >= MIN_SECONDS_FOR_FITTING)[0]
    if len(long_enough) < 2:
        long_enough = np.arange(len(matrix))

    history = average_linkage(matrix[long_enough])
    fitted_count = len(long_enough)

    if speaker_count and speaker_count > 0:
        clusters = min(speaker_count, fitted_count)
        _, scores = choose_cluster_count(history, fitted_count, max_speakers)
    else:
        clusters, scores = choose_cluster_count(history, fitted_count, max_speakers)
    fitted_labels = labels_for(history, fitted_count, clusters)

    # Long segments define the cluster centres; short ones join the nearest.
    centroids = np.vstack(
        [matrix[long_enough][fitted_labels == c].mean(axis=0) for c in range(clusters)]
    )
    centroids /= np.maximum(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-9)
    unit = matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-9)
    assignment = np.argmax(unit @ centroids.T, axis=1)
    assignment[long_enough] = fitted_labels

    # Renumber so Person1 is whoever speaks first.
    order: dict[int, int] = {}
    for cluster in assignment:
        if cluster not in order:
            order[cluster] = len(order) + 1

    for position, index in enumerate(usable):
        segments[index]["speaker"] = order[assignment[position]]
    for segment in segments:
        segment.setdefault("speaker", 1)

    speaking_time: dict[int, float] = {}
    for segment in segments:
        speaking_time[segment["speaker"]] = (
            speaking_time.get(segment["speaker"], 0.0) + segment["end"] - segment["start"]
        )

    return DiarizationResult(clusters, scores, speaking_time)

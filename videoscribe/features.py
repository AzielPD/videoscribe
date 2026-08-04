"""Acoustic features used to tell speakers apart, implemented in NumPy only.

Speaker separation ("diarisation") normally relies on a neural speaker
embedding model. Those need an extra download and, in the case of pyannote, a
Hugging Face account plus licence acceptance. To keep this toolkit runnable
straight after ``pip install -r requirements.txt``, the speaker features here
are computed from scratch:

* **MFCCs** capture the timbre of a voice -- roughly, its vocal tract shape.
* **Pitch (F0)** captures how low or high the voice is, which separates most
  male/female pairs on its own.

The combination is markedly weaker than a trained embedding. It works well on
clean recordings with distinct voices and struggles in noisy rooms with similar
voices. See ``docs/ACCURACY.md`` for what that means in practice.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000

# --- Mel filter bank ------------------------------------------------------
N_FILTERS = 40
N_FFT = 512
FMIN_HZ = 20.0
FMAX_HZ = 7600.0

# --- Frame geometry -------------------------------------------------------
MFCC_FRAME_SECONDS = 0.025
MFCC_HOP_SECONDS = 0.010
PITCH_FRAME_SECONDS = 0.040
PITCH_HOP_SECONDS = 0.020

# --- Pitch search range (human speech) ------------------------------------
F0_MIN_HZ = 70
F0_MAX_HZ = 350
VOICED_THRESHOLD = 0.35  # normalised autocorrelation peak above which a frame counts as voiced


def _hz_to_mel(hz: float | np.ndarray) -> float | np.ndarray:
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def _mel_to_hz(mel: float | np.ndarray) -> float | np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _build_mel_filters() -> np.ndarray:
    """Triangular mel-spaced filters, shape (N_FILTERS, N_FFT // 2 + 1)."""
    mel_points = np.linspace(_hz_to_mel(FMIN_HZ), _hz_to_mel(FMAX_HZ), N_FILTERS + 2)
    hz_points = _mel_to_hz(mel_points)
    bins = np.floor((N_FFT + 1) * hz_points / SAMPLE_RATE).astype(int)

    filters = np.zeros((N_FILTERS, N_FFT // 2 + 1), dtype=np.float32)
    for i in range(N_FILTERS):
        left, centre, right = bins[i], bins[i + 1], bins[i + 2]
        centre = max(centre, left + 1)
        right = min(max(right, centre + 1), N_FFT // 2)
        if left >= centre or centre >= right:
            continue
        filters[i, left:centre] = (np.arange(left, centre) - left) / (centre - left)
        filters[i, centre:right] = (right - np.arange(centre, right)) / (right - centre)
    return filters


def _build_dct(n_out: int, n_in: int) -> np.ndarray:
    """Orthonormal DCT-II matrix, the step that turns log-mel into cepstral."""
    n = np.arange(n_in)
    k = np.arange(n_out)[:, None]
    return (np.cos(np.pi * k * (2 * n + 1) / (2 * n_in)) * np.sqrt(2.0 / n_in)).astype(np.float32)


MEL_FILTERS = _build_mel_filters()
DCT_MATRIX = _build_dct(14, N_FILTERS)


def _frame_signal(signal: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    """Slice a 1-D signal into overlapping frames, shape (n_frames, frame_length)."""
    if len(signal) < frame_length:
        signal = np.pad(signal, (0, frame_length - len(signal)))
    n_frames = 1 + (len(signal) - frame_length) // hop_length
    indices = np.arange(frame_length)[None, :] + hop_length * np.arange(n_frames)[:, None]
    return signal[indices]


def mfcc(signal: np.ndarray) -> np.ndarray:
    """Return MFCCs of shape (n_frames, 13), dropping the energy coefficient c0.

    c0 tracks loudness rather than voice identity, so keeping it would make the
    clustering sensitive to how close each person sat to the microphone.
    """
    emphasised = np.append(signal[0:1], signal[1:] - 0.97 * signal[:-1])
    frames = _frame_signal(
        emphasised,
        int(MFCC_FRAME_SECONDS * SAMPLE_RATE),
        int(MFCC_HOP_SECONDS * SAMPLE_RATE),
    )
    frames = frames * np.hamming(frames.shape[1]).astype(np.float32)
    power = np.abs(np.fft.rfft(frames, N_FFT)) ** 2
    log_mel = np.log(np.maximum(power @ MEL_FILTERS.T, 1e-10))
    return (log_mel @ DCT_MATRIX.T)[:, 1:]


def median_log_pitch(signal: np.ndarray) -> float:
    """Median log-F0 over voiced frames, or NaN when the segment has no clear voicing.

    Pitch is estimated by autocorrelation: the lag of the strongest peak inside
    the human speech range gives the period, and its height relative to frame
    energy says whether the frame is voiced at all.
    """
    frame_length = int(PITCH_FRAME_SECONDS * SAMPLE_RATE)
    hop_length = int(PITCH_HOP_SECONDS * SAMPLE_RATE)
    if len(signal) < frame_length:
        return float("nan")

    frames = _frame_signal(signal, frame_length, hop_length)
    frames = frames - frames.mean(axis=1, keepdims=True)
    frames = frames * np.hanning(frame_length).astype(np.float32)

    n_fft = 1 << int(np.ceil(np.log2(2 * frame_length)))
    spectrum = np.fft.rfft(frames, n_fft)
    autocorr = np.fft.irfft(spectrum * np.conj(spectrum), n_fft)[:, :frame_length].real

    energy = autocorr[:, 0]
    lag_min, lag_max = int(SAMPLE_RATE / F0_MAX_HZ), int(SAMPLE_RATE / F0_MIN_HZ)
    window = autocorr[:, lag_min:lag_max + 1]
    best_lag = np.argmax(window, axis=1)
    peak = window[np.arange(len(window)), best_lag]

    normalised = np.where(energy > 1e-8, peak / np.maximum(energy, 1e-8), 0.0)
    voiced = normalised > VOICED_THRESHOLD
    if voiced.sum() < 3:
        return float("nan")
    return float(np.log(np.median(SAMPLE_RATE / (best_lag[voiced] + lag_min))))


def segment_features(signal: np.ndarray) -> tuple[np.ndarray | None, float]:
    """Summarise one speech segment as (timbre vector, log pitch).

    The timbre vector concatenates the mean and standard deviation of each MFCC
    coefficient, giving 26 numbers that describe both the average voice colour
    and how much it moves during the segment.
    """
    coefficients = mfcc(signal)
    if len(coefficients) < 3:
        return None, float("nan")
    vector = np.concatenate([coefficients.mean(axis=0), coefficients.std(axis=0)])
    return vector, median_log_pitch(signal)

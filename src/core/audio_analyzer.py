"""Audio analysis using librosa: spectrogram, chromagram, MFCC, tonnetz, tempogram, segmentation."""

import os
import warnings
import numpy as np
from pathlib import Path

warnings.filterwarnings('ignore', category=UserWarning)


def load_audio(path: str, sr: int = 22050) -> tuple:
    """Load an audio file. Returns (y, sr)."""
    import librosa
    y, sr = librosa.load(path, sr=sr, mono=True)
    return y, sr


def compute_spectrogram(y, sr, hop_length: int = 1024) -> np.ndarray:
    """Compute spectrogram (dB-scaled STFT magnitude)."""
    import librosa
    D = librosa.stft(y, hop_length=hop_length)
    return librosa.amplitude_to_db(np.abs(D), ref=np.max)


def compute_chromagram(y, sr, hop_length: int = 512) -> np.ndarray:
    """Compute CQT chromagram."""
    import librosa
    return librosa.feature.chroma_cqt(y=y, sr=sr, n_chroma=12, bins_per_octave=12)


def compute_mfcc(y, sr, hop_length: int = 256) -> np.ndarray:
    """Compute MFCC features (scaled)."""
    import librosa
    import sklearn.preprocessing
    mfccs = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length)
    return sklearn.preprocessing.scale(mfccs, axis=1)


def compute_tonnetz(y, sr) -> np.ndarray:
    """Compute tonal centroids (tonnetz)."""
    import librosa
    return librosa.feature.tonnetz(y=y, sr=sr)


def compute_tempogram(y, sr, hop_length: int = 1024) -> np.ndarray:
    """Compute tempogram."""
    import librosa
    return librosa.feature.tempogram(y=y, sr=sr, hop_length=hop_length)


def segment_structure(feature: np.ndarray, n_segments: int = 8, axis: int = 1) -> np.ndarray:
    """Agglomerative structural segmentation. Returns boundary frame indices."""
    import librosa.segment
    return librosa.segment.agglomerative(feature, n_segments, axis=axis)


def frames_to_time(bounds, sr: int, hop_length: int = 512):
    """Convert frame indices to time in seconds."""
    import librosa
    return librosa.frames_to_time(bounds, sr=sr, hop_length=hop_length)

"""Wrappers around the two neural networks: Demucs (stems) and Beat This!
(beats and downbeats). Models are loaded once and reused for every track."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

log = logging.getLogger("stemprep")


def pick_device(requested: str = "auto") -> str:
    import torch

    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class StemSeparator:
    """Demucs htdemucs: drums, bass, other, vocals."""

    def __init__(self, model: str = "htdemucs", device: str = "auto", shifts: int = 1,
                 jobs: int = 0):
        from demucs.api import Separator

        self.device = pick_device(device)
        log.info("Loading Demucs model %s on %s", model, self.device)
        self._sep = Separator(model=model, device=self.device, shifts=shifts,
                              progress=True, jobs=jobs)
        self.samplerate = self._sep.samplerate

    def separate(self, audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        import torch

        wav = torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32))
        _, stems = self._sep.separate_tensor(wav, sr)
        out = {}
        for name, t in stems.items():
            arr = t.detach().cpu().numpy().astype(np.float32)
            if self.samplerate != sr:
                arr = _resample(arr, self.samplerate, sr)
            out[name] = arr
        return out


class BeatTracker:
    """Beat This! (CPJKU, 2024) — beats and downbeats in seconds."""

    def __init__(self, device: str = "auto", checkpoint: str = "final0"):
        from beat_this.inference import Audio2Beats

        self.device = pick_device(device)
        if self.device == "mps":
            self.device = "cpu"  # not all ops are supported on MPS
        log.info("Loading Beat This! (%s) on %s", checkpoint, self.device)
        self._model = Audio2Beats(checkpoint_path=checkpoint, device=self.device, dbn=False)

    def track(self, audio: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
        mono = np.asarray(audio, dtype=np.float64)
        if mono.ndim == 2:
            mono = mono.mean(axis=0)
        beats, downbeats = self._model(mono, sr)
        return np.asarray(beats, dtype=float), np.asarray(downbeats, dtype=float)


def _resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    try:
        import soxr

        return np.stack([soxr.resample(ch, sr_from, sr_to) for ch in x]).astype(np.float32)
    except ImportError:  # pragma: no cover - soxr comes with beat_this
        n = int(round(x.shape[1] * sr_to / sr_from))
        idx = np.linspace(0, x.shape[1] - 1, n)
        return np.stack([np.interp(idx, np.arange(x.shape[1]), ch) for ch in x]).astype(np.float32)


def load_models(stems: bool, device: str, model: str) -> Tuple[Optional[StemSeparator], BeatTracker]:
    sep = StemSeparator(model=model, device=device) if stems else None
    return sep, BeatTracker(device=device)

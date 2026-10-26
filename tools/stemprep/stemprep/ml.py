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

        self.name = model
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


class UmxSeparator:
    """Open-Unmix (umxl / umxhq): spectrogram model, much faster than Demucs
    on a CPU but with more bleed between stems. Used for the "fast" stems."""

    def __init__(self, model: str = "umxl", device: str = "auto"):
        from openunmix import utils

        self.name = model
        self.device = pick_device(device)
        if self.device == "mps":
            self.device = "cpu"
        log.info("Loading Open-Unmix model %s on %s", model, self.device)
        self._sep = utils.load_separator(model, targets=["drums", "bass", "other", "vocals"],
                                         device=self.device)
        self._sep.freeze()
        self.samplerate = int(self._sep.sample_rate)

    def separate(self, audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        import torch
        from openunmix import predict

        wav = torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32))
        with torch.no_grad():
            stems = predict.separate(wav, rate=sr, separator=self._sep, device=self.device)
        out = {}
        for name, t in stems.items():
            arr = t[0].detach().cpu().numpy().astype(np.float32)
            if self.samplerate != sr:
                arr = _resample(arr, self.samplerate, sr)
            out[name] = arr
        return out


class SpleeterSeparator:
    """Deezer's Spleeter 4-stem U-Nets as ONNX (community conversion,
    huggingface.co/Best-Practice/spleeter-4stems-onnx, Apache-2.0 / MIT
    weights). Much faster than Demucs on a CPU, rougher quality: used for
    the "fast" stems.

    The models estimate magnitudes up to ~11 kHz (1024 of 2049 bins); the
    soft masks are extended over the upper band with each frame's mean, so
    the four stems still add up exactly to the mix.
    """

    REPO = "Best-Practice/spleeter-4stems-onnx"
    N_FFT, HOP, FRAMES, BINS = 4096, 1024, 512, 1024
    SR = 44100
    STEMS = ("vocals", "drums", "bass", "other")

    def __init__(self, precision: str = "fp32", threads: int = 0, gpu: bool = True):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        self.name = "spleeter4" + ("-fp16" if precision == "fp16" else "")
        self.samplerate = self.SR
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        providers = ["CPUExecutionProvider"]
        # DirectML (onnxruntime-directml): any DirectX 12 GPU, including
        # Intel integrated graphics
        if gpu and "DmlExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "DmlExecutionProvider")
            opts.enable_mem_pattern = False  # required by DirectML
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.device = "gpu" if providers[0] != "CPUExecutionProvider" else "cpu"
        suffix = ".fp16.onnx" if precision == "fp16" else ".onnx"
        log.info("Loading Spleeter 4-stem (%s) on %s", precision, providers[0])
        self._sessions = {
            s: ort.InferenceSession(hf_hub_download(self.REPO, s + suffix), opts,
                                    providers=providers)
            for s in self.STEMS}

    def separate(self, audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        # STFT, masks and overlap-add in torch: float32 and multi-threaded
        # (numpy took as long as the networks themselves)
        import torch
        import torch.nn.functional as tnf

        x = np.ascontiguousarray(audio, dtype=np.float32)
        if x.ndim == 1:
            x = np.stack([x, x])
        if sr != self.SR:
            x = _resample(x, sr, self.SR)
        n = x.shape[1]
        N, H, T, F = self.N_FFT, self.HOP, self.FRAMES, self.BINS
        pad = N - H
        n_frames = int(np.ceil((pad + n) / H))
        length = (n_frames - 1) * H + N
        padded = torch.zeros(2, length)
        padded[:, pad:pad + n] = torch.from_numpy(x)
        win = torch.hann_window(N, periodic=True)
        out = torch.zeros(len(self.STEMS), 2, length)

        def overlap_add(frames: "torch.Tensor") -> "torch.Tensor":
            """(C, count, N) frames, hop H -> (C, (count-1)*H + N)"""
            c, count, _ = frames.shape
            return tnf.fold(frames.transpose(1, 2), output_size=(1, (count - 1) * H + N),
                            kernel_size=(1, N), stride=(1, H)).reshape(c, -1)

        with torch.no_grad():
            for f0 in range(0, n_frames, T):
                count = min(T, n_frames - f0)
                frames = padded[:, f0 * H:f0 * H + (count - 1) * H + N].unfold(-1, N, H)
                spec = torch.fft.rfft(frames * win)  # (2, count, 2049)
                mag = torch.zeros(2, 1, T, F)
                mag[:, 0, :count] = spec[..., :F].abs()
                feed = {"x": mag.numpy()}
                est = [torch.from_numpy(sess.run(["y"], feed)[0][:, 0, :count])
                       for sess in self._sessions.values()]
                power = [e * e for e in est]
                total = sum(power) + 1e-10
                for i, p in enumerate(power):
                    mask = (p + 1e-10 / len(power)) / total
                    full = torch.cat([mask, mask.mean(-1, keepdim=True)
                                      .expand(-1, -1, spec.shape[-1] - F)], -1)
                    y = torch.fft.irfft(spec * full, n=N) * win
                    out[i, :, f0 * H:f0 * H + (count - 1) * H + N] += overlap_add(y)
            # Normalize by the summed squared window (constant except at the edges)
            wsum = overlap_add((win * win).expand(1, n_frames, N)).clamp_min(1e-8)
            out = (out / wsum)[:, :, pad:pad + n].numpy()
        stems = {}
        for i, s in enumerate(self.STEMS):
            y = np.ascontiguousarray(out[i])
            stems[s] = _resample(y, self.SR, sr) if sr != self.SR else y
        return stems


def make_separator(model: str, device: str = "auto"):
    """Demucs (htdemucs...), Open-Unmix (umx*) or Spleeter (spleeter4)."""
    if model.startswith("umx"):
        return UmxSeparator(model, device)
    if model.startswith("spleeter4"):
        return SpleeterSeparator("fp16" if model.endswith("fp16") else "fp32")
    return StemSeparator(model=model, device=device)


class BeatTracker:
    """Beat This! (CPJKU, 2024) — beats and downbeats in seconds."""

    # Can be run on excerpts (see beats_from_excerpts)
    supports_excerpts = True

    def __init__(self, device: str = "auto", checkpoint: str = "final0"):
        from beat_this.inference import Audio2Beats

        self.checkpoint = checkpoint
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


def beats_from_excerpts(tracker, mono: np.ndarray, sr: int, duration: float,
                        excerpts: int = 3, seconds: float = 20.0,
                        max_jitter: float = 0.03) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Beats and downbeats of a whole track from a few short excerpts.

    Dance music is made on a grid at one tempo, so a constant-tempo grid
    fitted to the beats of a few excerpts describes the whole track; the bar
    phase comes from a vote of the excerpts' downbeats. Several times faster
    than tracking the whole track. Returns None if the excerpts don't fit one
    tempo (live drummer, tempo changes): track the whole file then.
    """
    mono = np.asarray(mono, dtype=np.float64).reshape(-1)
    n = int(seconds * sr)
    if duration < excerpts * seconds * 2:
        return None
    # Spread over the track, avoiding the very start and end
    starts = np.linspace(0.12, 0.88, excerpts) * (len(mono) - n)
    beats, downbeats = [], []
    for s in starts.astype(int):
        b, d = tracker(mono[s:s + n], sr)
        beats.append(np.asarray(b) + s / sr)
        downbeats.append(np.asarray(d) + s / sr)
    if any(len(b) < 8 for b in beats):
        return None
    # Number the beats across excerpts that are a minute or more apart: a
    # tempo off by 0.5% would already miscount by a beat or two. So fit the
    # first excerpt, place the next one with that grid, refit, and so on.
    def numbered(b, t0, period):
        return np.round((b - t0) / period)

    def counted(b):
        """Beat numbers counted gap by gap: a missed beat (a gap of two
        periods) doesn't shift the rest, and period errors don't add up."""
        gaps = np.diff(b)
        return np.concatenate([[0.0], np.cumsum(np.round(gaps / np.median(gaps)))])

    first = beats[0]
    idx = counted(first)
    period, t0 = np.polyfit(idx, first, 1)
    all_idx, all_beats = idx, first
    for b in beats[1:]:
        # The excerpt's first beat is placed on the grid so far; the rest
        # are counted from it
        start = numbered(b[:1], t0, period)[0]
        all_idx = np.concatenate([all_idx, start + counted(b)])
        all_beats = np.concatenate([all_beats, b])
        period, t0 = np.polyfit(all_idx, all_beats, 1)
    slope, intercept = period, t0
    if np.std(all_beats - (slope * all_idx + intercept)) > max_jitter:
        return None
    first = intercept - np.floor(intercept / slope) * slope  # earliest beat >= 0
    grid = np.arange(first, duration, slope)
    grid_idx = np.round((grid - intercept) / slope).astype(int)
    votes = np.zeros(4)
    for d in np.concatenate(downbeats):
        votes[int(np.round((d - intercept) / slope)) % 4] += 1
    phase = int(np.argmax(votes))
    return grid, grid[(grid_idx % 4) == phase]


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

"""Speed/quality benchmark for the analysis and stem models (developer tool).

  python -m stemprep.bench file1.mp3 file2.mp3 ... [--excerpt 60] [--out results.json]

For each file:
- decode time at 44.1 kHz stereo vs. 22.05 kHz mono
- beat tracking with each Beat This! checkpoint: time, and downbeat/beat
  agreement (F-measure, +-70 ms) with the full model "final0"
- stem separation on an excerpt with each candidate: time per minute of
  audio, and SDR of each stem against htdemucs (overlap 0.25, today's
  setting) on the same excerpt. That SDR is a proxy (htdemucs isn't the
  truth), so listen too: --save-excerpts writes the stems as WAVs.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from .audio import SAMPLE_RATE, decode, write_wav

log = logging.getLogger("stemprep")

STEMS = ("drums", "bass", "other", "vocals")
TOLERANCE = 0.07


def f_measure(est, ref, tol: float = TOLERANCE) -> float:
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    if len(est) == 0 or len(ref) == 0:
        return 0.0
    matched = 0
    used = np.zeros(len(ref), dtype=bool)
    for t in est:
        i = int(np.argmin(np.abs(ref - t)))
        if not used[i] and abs(ref[i] - t) <= tol:
            used[i] = True
            matched += 1
    p, r = matched / len(est), matched / len(ref)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def sdr(est: np.ndarray, ref: np.ndarray) -> float:
    n = min(est.shape[-1], ref.shape[-1])
    est, ref = est[..., :n], ref[..., :n]
    noise = np.sum((ref - est) ** 2)
    return float(10 * np.log10(max(np.sum(ref ** 2), 1e-12) / max(noise, 1e-12)))


def timed(fn, *args, **kwargs):
    t = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, time.perf_counter() - t


# --- stem candidates --------------------------------------------------------


def demucs_separator(overlap: float):
    from demucs.api import Separator

    sep = Separator(model="htdemucs", device="cpu", overlap=overlap, progress=False)

    def run(audio: np.ndarray):
        import torch

        _, stems = sep.separate_tensor(torch.from_numpy(audio), SAMPLE_RATE)
        return {k: v.numpy() for k, v in stems.items()}
    return run


def umx_separator(model: str):
    from openunmix import predict, utils

    # Load once; predict.separate() would reload the weights on every call
    sep = utils.load_separator(model, targets=list(STEMS), device="cpu")
    sep.freeze()

    def run(audio: np.ndarray):
        import torch

        with torch.no_grad():
            out = predict.separate(torch.from_numpy(audio), rate=SAMPLE_RATE, separator=sep,
                                   device="cpu")
        return {k: v[0].numpy() for k, v in out.items()}
    return run


def spleeter_separator(precision: str):
    from .ml import SpleeterSeparator

    sep = SpleeterSeparator(precision)
    return lambda audio: sep.separate(audio, SAMPLE_RATE)


CANDIDATES = {
    "htdemucs-0.25": lambda: demucs_separator(0.25),  # reference (today's setting)
    "htdemucs-0.1": lambda: demucs_separator(0.1),
    "umxl": lambda: umx_separator("umxl"),
    "umxhq": lambda: umx_separator("umxhq"),
    "spleeter4": lambda: spleeter_separator("fp32"),
    "spleeter4-fp16": lambda: spleeter_separator("fp16"),
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stemprep-bench")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--excerpt", type=float, default=60.0, help="seconds of audio for stem tests")
    p.add_argument("--checkpoints", default="final0,small0")
    p.add_argument("--stems", default=",".join(CANDIDATES), help="stem candidates to run")
    p.add_argument("--threads", type=int, default=0, help="torch threads (0 = default)")
    p.add_argument("--save-excerpts", type=Path, default=None)
    p.add_argument("--reference-dir", type=Path, default=None,
                   help="use htdemucs-0.25 stems saved by an earlier --save-excerpts run "
                        "as the reference instead of separating again")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    import torch
    from beat_this.inference import Audio2Beats

    if args.threads:
        torch.set_num_threads(args.threads)
    log.info("torch threads: %d", torch.get_num_threads())

    checkpoints = [c for c in args.checkpoints.split(",") if c]
    trackers = {}
    for c in checkpoints:
        try:
            trackers[c] = Audio2Beats(checkpoint_path=c, device="cpu", dbn=False)
        except Exception as e:  # unknown checkpoint name, no download...
            log.warning("Beat This! %s not available: %s", c, e)
    separators = {}
    for name in [s for s in args.stems.split(",") if s]:
        try:
            separators[name] = CANDIDATES[name]()
        except Exception as e:
            log.warning("Stem candidate %s not available: %s", name, e)

    results = []
    for path in args.files:
        log.info("== %s", path.name)
        r = {"file": path.name}
        stereo, r["decode_44k_stereo_s"] = timed(decode, path)
        mono22, r["decode_22k_mono_s"] = timed(decode, path, 22050, 1)
        duration = stereo.shape[1] / SAMPLE_RATE
        r["duration_s"] = duration

        # Beats: final0 as today (44.1 kHz stereo in), others on 22.05 kHz mono
        ref_beats = ref_down = None
        for name, tracker in trackers.items():
            if name == "final0":
                (beats, down), t = timed(tracker, stereo.mean(axis=0).astype(np.float64), SAMPLE_RATE)
            else:
                (beats, down), t = timed(tracker, mono22[0].astype(np.float64), 22050)
            r[f"beats_{name}_s"] = t
            if name == "final0":
                ref_beats, ref_down = beats, down
            elif ref_beats is not None:
                r[f"beats_{name}_beatF"] = f_measure(beats, ref_beats)
                r[f"beats_{name}_downbeatF"] = f_measure(down, ref_down)
        if "final0" in trackers and ref_beats is not None:
            from .ml import beats_from_excerpts

            fitted, t = timed(beats_from_excerpts, trackers["final0"], mono22[0], 22050,
                              duration)
            r["beats_excerpts_s"] = t
            if fitted is None:
                r["beats_excerpts_fallback"] = 1.0
            else:
                r["beats_excerpts_beatF"] = f_measure(fitted[0], ref_beats)
                r["beats_excerpts_downbeatF"] = f_measure(fitted[1], ref_down)

        # Stems on an excerpt from the middle (where the music is busy)
        n = int(args.excerpt * SAMPLE_RATE)
        start = max(0, (stereo.shape[1] - n) // 2)
        excerpt = np.ascontiguousarray(stereo[:, start:start + n])
        minutes = excerpt.shape[1] / SAMPLE_RATE / 60
        reference = None
        saved = args.reference_dir / path.stem / "htdemucs-0.25" if args.reference_dir else None
        if saved and saved.is_dir():
            from .audio import read_wav

            reference = {s: read_wav(saved / f"{s}.wav") for s in STEMS}
        for name, run in separators.items():
            stems, t = timed(run, excerpt)
            r[f"stems_{name}_s_per_min"] = t / minutes
            if name == "htdemucs-0.25":
                reference = stems
            elif reference is not None:
                for s in STEMS:
                    r[f"stems_{name}_sdr_{s}"] = sdr(stems[s], reference[s])
            if args.save_excerpts:
                d = args.save_excerpts / path.stem / name
                d.mkdir(parents=True, exist_ok=True)
                for s in STEMS:
                    write_wav(d / f"{s}.wav", stems[s])
                if not (d.parent / "mix.wav").exists():
                    write_wav(d.parent / "mix.wav", excerpt)
        log.info(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}))
        results.append(r)

    if args.out:
        args.out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    summarize(results)
    return 0


def summarize(results) -> None:
    keys = sorted({k for r in results for k in r if isinstance(r[k], float) and k != "duration_s"})
    print(f"\n{'measure':40} {'mean':>8} {'min':>8} {'max':>8}")
    for k in keys:
        v = np.array([r[k] for r in results if k in r])
        print(f"{k:40} {v.mean():8.2f} {v.min():8.2f} {v.max():8.2f}")
    mean_dur = np.mean([r["duration_s"] for r in results]) / 60
    print(f"\n(average track length {mean_dur:.1f} min; *_s_per_min x length = time per track)")


if __name__ == "__main__":
    raise SystemExit(main())

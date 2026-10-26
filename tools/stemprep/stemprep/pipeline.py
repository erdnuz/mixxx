"""One track in, stem file + structure sidecar out."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from . import __version__
from .audio import SAMPLE_RATE, decode
from .structure import (
    SECTION_COLORS,
    FrameFeatures,
    Structure,
    analyze_structure,
    frame_features,
    suggest_cues,
)

log = logging.getLogger("stemprep")

SIDECAR_SUFFIX = ".structure.json"
# Set by Mixxx in the sidecar once it added the suggested hot cues
CUES_APPLIED_KEY = "mixxx_cues_applied"
# Set by Mixxx: the hot cues it added (slot, frame, label)
AUTO_CUES_KEY = "mixxx_auto_cues"


def sidecar_path(audio_path: Path) -> Path:
    """'Song.stem.mp4' -> 'Song.stem.mp4.structure.json' (what Mixxx looks for)."""
    return audio_path.with_name(audio_path.name + SIDECAR_SUFFIX)


def features_path(target: Path) -> Path:
    """Cached analysis features, so tracks can be re-analyzed without
    running the neural networks again: '<folder>/.stemprep/<file>.features.npz'."""
    return target.parent / ".stemprep" / (target.name + ".features.npz")


def stem_output_path(source: Path, out_dir: Path) -> Path:
    stem = source.name
    for ext in (".stem.mp4", ".stem.m4a"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    else:
        stem = source.stem
    stem = re.sub(r'[<>:"/\\|?*]', "_", stem)
    return out_dir / f"{stem}.stem.mp4"


@dataclass
class Options:
    make_stems: bool = True
    force: bool = False
    bitrate: str = "256k"
    # Written to the sidecar: "fast" stems may later be replaced by "hq" ones
    stems_quality: str = "hq"


# Beats and the section features only need mono at this rate (Beat This!
# converts to it anyway), which is much cheaper to decode than 44.1k stereo.
ANALYSIS_SR = 22050

# Keys that belong to the stem file (or to Mixxx), not to one analysis: they
# are carried over when the analysis is redone.
STEMS_KEYS = ("stems", "stems_quality", "stems_offset_ms", "stems_sample_rate", "source_size")


def structure_to_json(s: Structure, duration: float, analyzed: Path, tier: str = "stems",
                      models: Optional[dict] = None) -> dict:
    return {
        "format": "mixxx-structure",
        "version": 1,
        "generator": f"stemprep {__version__}",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        # "mix": sections from the full mix only (fast, rougher);
        # "stems": from the separated stems (Mixxx only adds hot cues then)
        "tier": tier,
        "models": models or {},
        "analyzed_file": analyzed.name,
        "duration": round(duration, 4),
        "bpm": round(s.bpm, 3),
        "beats_per_bar": s.beats_per_bar,
        "phrase_bars": s.phrase_bars,
        "beats": [round(b, 4) for b in s.beats],
        "downbeats": [round(b, 4) for b in s.bar_starts],
        "phrases": [round(s.bar_starts[i], 4) for i in s.phrases if i < len(s.bar_starts)],
        "sections": [
            {
                "start": round(sec.start, 4),
                "end": round(sec.end, 4),
                "bars": sec.bars,
                "label": sec.label,
                "color": SECTION_COLORS.get(sec.label.split(" ")[0], "#FFFFFF"),
                "energy": round(sec.energy, 3),
            }
            for sec in s.sections
        ],
        "cues": suggest_cues(s),
        "bar_energy": [round(e, 3) for e in s.bar_energy],
    }


def read_sidecar(audio_path: Path) -> dict:
    try:
        return json.loads(sidecar_path(audio_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_sidecar(audio_path: Path, data: dict) -> Path:
    path = sidecar_path(audio_path)
    old = read_sidecar(audio_path)
    data = dict(data)
    # Keep Mixxx's note that it already added the hot cues, so re-analyzing
    # doesn't bring back cues the user deleted.
    if old.get(CUES_APPLIED_KEY):
        data[CUES_APPLIED_KEY] = old[CUES_APPLIED_KEY]
    # ...and which cues it added, so it can replace them while untouched
    if AUTO_CUES_KEY in old:
        data[AUTO_CUES_KEY] = old[AUTO_CUES_KEY]
    for key in STEMS_KEYS:
        if key in old and key not in data:
            data[key] = old[key]
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


def measure_offset_ms(source: Path, stem_file: Path, seconds: float = 30.0) -> float:
    """How much later (ms) the stem file's mix plays than the source, as
    decoded by ffmpeg. AAC encoder priming should be compensated by the MP4
    edit list; Mixxx refuses stem files that are off by more than 5 ms."""
    a = decode(source, ANALYSIS_SR, 1, max_seconds=seconds)[0]
    b = decode(stem_file, ANALYSIS_SR, 1, max_seconds=seconds)[0]
    n = min(len(a), len(b))
    if n < ANALYSIS_SR:
        return 0.0
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    size = 1 << int(np.ceil(np.log2(2 * n)))
    corr = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    max_lag = int(0.2 * ANALYSIS_SR)  # +-200 ms
    lags = np.concatenate([np.arange(0, max_lag + 1), np.arange(-max_lag, 0)])
    window = np.concatenate([corr[:max_lag + 1], corr[-max_lag:]])
    return round(float(lags[int(np.argmax(window))]) / ANALYSIS_SR * 1000.0, 2)


def save_features(target: Path, source: Path, beats, downbeats, duration: float,
                  frames: FrameFeatures) -> None:
    path = features_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {f"p_{k}": v.astype(np.float32) for k, v in frames.power.items()}
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez_compressed(
        tmp,
        beats=np.asarray(beats, dtype=np.float64),
        downbeats=np.asarray(downbeats, dtype=np.float64),
        duration=np.float64(duration),
        has_stems=np.bool_(frames.has_stems),
        flux=frames.flux.astype(np.float32),
        source=np.str_(str(source)),
        **arrays,
    )
    tmp.replace(path)


def load_features(target: Path):
    """(beats, downbeats, duration, frames, source) or None."""
    path = features_path(target)
    if not path.exists():
        return None
    with np.load(path) as z:
        power = {k[2:]: z[k] for k in z.files if k.startswith("p_")}
        frames = FrameFeatures(power, z["flux"], bool(z["has_stems"]))
        return z["beats"], z["downbeats"], float(z["duration"]), frames, Path(str(z["source"]))


def _is_stem_file(path: Path) -> bool:
    return path.name.lower().endswith((".stem.mp4", ".stem.m4a"))


def _target_for(source: Path, out_dir: Path, opts: Options) -> Path:
    return source if (_is_stem_file(source) or not opts.make_stems) \
        else stem_output_path(source, out_dir)


def is_analyzed(source: Path) -> bool:
    return sidecar_path(Path(source)).exists()


def stems_path(source: Path, out_dir: Path, quality: str = "hq") -> Path:
    """Fast (rough) stems live in a "fast" subfolder until the high quality
    ones replace them; a different name because Mixxx may have the fast
    file open when the high quality one is written."""
    return stem_output_path(source, out_dir / "fast" if quality == "fast" else out_dir)


def has_stems(source: Path, out_dir: Path, quality: str = "hq") -> bool:
    """quality "fast": any stems will do."""
    hq = stems_path(Path(source), out_dir)
    if hq.exists() and sidecar_path(hq).exists():
        return True
    fast = stems_path(Path(source), out_dir, "fast")
    return quality == "fast" and fast.exists() and sidecar_path(fast).exists()


def source_sample_rate(path: Path) -> int:
    """The file's own sample rate. Stem files are written at it, because Mixxx
    stores beats and cues in frames of the track's sample rate."""
    try:
        import mutagen

        info = mutagen.File(str(path))
        if info is not None and getattr(info.info, "sample_rate", 0):
            return int(info.info.sample_rate)
    except Exception as e:  # unreadable tags: fall back
        log.debug("No sample rate for %s: %s", path, e)
    return SAMPLE_RATE


def is_done(source: Path, out_dir: Path, opts: Options) -> bool:
    source = Path(source)
    if opts.make_stems and not _is_stem_file(source):
        return has_stems(source, out_dir, opts.stems_quality)
    return is_analyzed(source)


def _summary(data: dict) -> str:
    return ", ".join(f"{s['label']}@{_mmss(s['start'])}" for s in data["sections"])


# Track beats on a few excerpts and fit one tempo grid (ml.beats_from_excerpts)
# instead of the whole track: several times faster; tracks that don't keep
# one tempo fall back to whole-track tracking.
EXCERPT_BEATS = True


def _track_beats(beat_tracker, mono: np.ndarray, duration: float):
    """(beats, downbeats, model name)"""
    name = getattr(beat_tracker, "checkpoint", "")
    if EXCERPT_BEATS and getattr(beat_tracker, "supports_excerpts", False):
        from .ml import beats_from_excerpts

        fitted = beats_from_excerpts(beat_tracker.track, mono[0], ANALYSIS_SR, duration)
        if fitted is not None:
            return fitted[0], fitted[1], name + "-excerpts"
        log.info("Tempo isn't steady; tracking beats over the whole track")
    beats, downbeats = beat_tracker.track(mono, ANALYSIS_SR)
    return beats, downbeats, name


def analyze_track(source: Path, beat_tracker, opts: Options) -> Optional[Path]:
    """Fast tier: beats + sections from the mix, sidecar next to the source.
    Returns the source, or None if it was analyzed already."""
    source = Path(source)
    if not opts.force and is_analyzed(source):
        # Never replace an analysis from stems (or an older one without a
        # tier, made with stems) by a rougher one from the mix.
        tier = read_sidecar(source).get("tier")
        if tier != "mix" or load_features(source) is not None:
            return None
    t0 = time.time()
    mono = decode(source, ANALYSIS_SR, 1)
    duration = mono.shape[1] / ANALYSIS_SR
    beats, downbeats, beats_model = _track_beats(beat_tracker, mono, duration)
    if len(beats) < 8:
        log.warning("Too few beats found in %s; skipping structure", source.name)
    frames = frame_features(ANALYSIS_SR, mix=mono)
    structure = analyze_structure(beats, downbeats, duration, frames=frames)
    is_stem = _is_stem_file(source)
    data = structure_to_json(structure, duration, source, tier="stems" if is_stem else "mix",
                             models={"beats": beats_model})
    write_sidecar(source, data)
    save_features(source, source, beats, downbeats, duration, frames)
    log.info("Analyzed in %.1fs: %.1f BPM | %s", time.time() - t0, structure.bpm, _summary(data))
    return source


def make_stems(source: Path, out_dir: Path, separator, beat_tracker,
               opts: Options) -> Optional[Path]:
    """Slow tier: stem file + sections from the stems. Upgrades the
    source's sidecar to "tier": "stems" and points it at the stem file.
    Returns the stem file, or None if it exists already."""
    source = Path(source)
    quality = opts.stems_quality
    target = stems_path(source, out_dir, quality)
    if not opts.force and has_stems(source, out_dir, quality):
        return None
    cached = load_features(source)
    if cached is None:  # beats come from the fast tier
        analyze_track(source, beat_tracker, Options(force=True))
        cached = load_features(source)
    beats, downbeats = cached[0], cached[1]

    t0 = time.time()
    sr = source_sample_rate(source)
    audio = decode(source, sr)
    duration = audio.shape[1] / sr
    log.info("Separating stems with %s (%s quality)...", getattr(separator, "name", "?"), quality)
    stems = separator.separate(audio, sr)
    from .stemfile import write_stem_file

    log.info("Writing %s", target.name)
    write_stem_file(target, audio, stems, source_for_tags=source, bitrate=opts.bitrate,
                    sample_rate=sr)
    frames = frame_features(sr, stems=stems)
    save_features(target, source, beats, downbeats, duration, frames)
    structure = analyze_structure(beats, downbeats, duration, frames=frames)
    data = structure_to_json(structure, duration, source, tier="stems", models={
        "beats": getattr(beat_tracker, "checkpoint", ""),
        "stems": getattr(separator, "name", "")})
    data.update(_stems_keys(source, target, quality))
    write_sidecar(target, data)
    write_sidecar(source, data)
    if quality != "fast":
        _remove_stems(stems_path(source, out_dir, "fast"))
    log.info("Stems in %.0fs | %s", time.time() - t0, _summary(data))
    return target


def _remove_stems(stem_file: Path) -> None:
    """Best effort: Mixxx may still have the file open; then it stays."""
    for p in (stem_file, sidecar_path(stem_file), features_path(stem_file)):
        try:
            p.unlink(missing_ok=True)
        except OSError as e:
            log.info("Could not remove %s yet: %s", p.name, e)


def _stems_keys(source: Path, target: Path, quality: str) -> dict:
    return {
        "stems": str(target),
        "stems_quality": quality,
        "stems_offset_ms": measure_offset_ms(source, target),
        "stems_sample_rate": source_sample_rate(target),
        "source_size": source.stat().st_size,
    }


def reanalyze(target: Path) -> bool:
    """Redo bars/phrases/sections from cached features (fast; after the
    detection was improved). False if the file has no cached features."""
    cached = load_features(target)
    if cached is None:
        return False
    beats, downbeats, duration, frames, source = cached
    if not frames.has_stems and read_sidecar(target).get("tier") == "stems":
        return True  # the stem file's features are better; done via the stem file
    structure = analyze_structure(beats, downbeats, duration, frames=frames)
    data = structure_to_json(structure, duration, source,
                             tier="stems" if frames.has_stems else "mix",
                             models=read_sidecar(target).get("models"))
    is_fast = target.parent.name == "fast"
    hq_exists = is_fast and stems_path(source, target.parent.parent).exists()
    if source != target and source.exists() and not hq_exists:
        old = read_sidecar(source)
        if (old.get("stems") != str(target) or "stems_offset_ms" not in old
                or "stems_sample_rate" not in old):
            # Stem file made before sidecars pointed at it
            data.update(_stems_keys(source, target, "fast" if is_fast else "hq"))
        write_sidecar(source, data)
    write_sidecar(target, data)
    log.info("%s: %s", target.name, _summary(data))
    return True


def process_track(source: Path, out_dir: Path, separator, beat_tracker,
                  opts: Options) -> Optional[Path]:
    """Both tiers. Returns the file to load in Mixxx (stem file, or the
    source in analysis-only mode), or None if everything was done already."""
    source = Path(source)
    analyzed = analyze_track(source, beat_tracker, opts)
    if not opts.make_stems or _is_stem_file(source):
        return analyzed
    return make_stems(source, out_dir, separator, beat_tracker, opts)


def _mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def find_audio_files(path: Path):
    from .audio import AUDIO_EXTENSIONS

    path = Path(path)
    if path.is_file():
        return [path]
    files = []
    for p in sorted(path.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS and not p.name.endswith(".part.mp4"):
            files.append(p)
    return files

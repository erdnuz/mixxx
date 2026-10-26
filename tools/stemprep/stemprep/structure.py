"""Bar, phrase and section detection.

Works on beats/downbeats from the beat tracker plus the separated stems.
Only numpy is needed here so this module can be tested without the ML stack.

The idea:
1. Build a clean list of bars from the detected downbeats (filling gaps).
2. Measure each bar: kick, drums, bass, music and vocal loudness, brightness.
3. Find the phrase grid: dance music changes on 8-bar boundaries, so pick the
   8-bar offset where the music changes the most (the big jump into a drop
   usually decides it).
4. Classify 4-bar blocks by energy (kick + bass in = high, kick out = low)
   and turn runs of blocks into labelled sections: Intro, Build, Drop,
   Breakdown, Groove, Outro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

ANALYSIS_SR = 11025  # features are computed on a downsampled mono signal

SECTION_COLORS = {
    "Intro": "#3F8EFC",
    "Groove": "#9AA0A6",
    "Build": "#F5B700",
    "Drop": "#FF3B30",
    "Breakdown": "#8E5CFF",
    "Outro": "#3F8EFC",
    "Verse": "#9AA0A6",
    "Hook": "#FF6F3C",
}

@dataclass
class Section:
    start_bar: int
    end_bar: int  # exclusive
    label: str
    energy: float
    start: float = 0.0
    end: float = 0.0

    @property
    def bars(self) -> int:
        return self.end_bar - self.start_bar


@dataclass
class Structure:
    bpm: float
    beats_per_bar: int
    beats: List[float]
    bar_starts: List[float]
    phrase_bars: int
    phrase_origin_bar: int
    phrases: List[int]  # bar indices where a phrase starts
    sections: List[Section] = field(default_factory=list)
    bar_energy: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Bars
# ---------------------------------------------------------------------------


def estimate_bpm(beats: Sequence[float]) -> float:
    beats = np.asarray(beats, dtype=float)
    if len(beats) < 4:
        return 0.0
    ibi = np.diff(beats)
    med = np.median(ibi)
    # Robust: ignore intervals far from the median (missed / double beats)
    good = ibi[(ibi > 0.7 * med) & (ibi < 1.3 * med)]
    if len(good) == 0:
        good = ibi
    # Fit a straight line to the beat times using only consistent beats for
    # a more precise tempo than the median interval.
    idx = np.concatenate([[0], np.cumsum(np.round(ibi / med))]).astype(float)
    slope = np.polyfit(idx, beats, 1)[0]
    if 0.7 * med < slope < 1.3 * med:
        return 60.0 / slope
    return 60.0 / float(np.median(good))


def beats_per_bar_from(beats: Sequence[float], downbeats: Sequence[float]) -> int:
    beats = np.asarray(beats)
    downbeats = np.asarray(downbeats)
    if len(downbeats) < 2:
        return 4
    counts = []
    for a, b in zip(downbeats[:-1], downbeats[1:]):
        n = int(np.sum((beats >= a - 1e-3) & (beats < b - 1e-3)))
        if 2 <= n <= 7:
            counts.append(n)
    if not counts:
        return 4
    values, freq = np.unique(counts, return_counts=True)
    return int(values[np.argmax(freq)])


def build_bars(
    beats: Sequence[float],
    downbeats: Sequence[float],
    duration: float,
    beats_per_bar: int,
) -> List[float]:
    """Return a gap-free list of bar start times covering the whole track.

    The bar phase comes from the detected downbeats (majority vote over the
    beat index modulo beats_per_bar), so a few missed or extra downbeats
    don't shift every bar after them.
    """
    beats = np.asarray(beats, dtype=float)
    downbeats = np.asarray(downbeats, dtype=float)
    if len(beats) < beats_per_bar * 2:
        return list(downbeats)

    # Which beat index (mod beats_per_bar) do the downbeats fall on?
    votes = np.zeros(beats_per_bar)
    for db in downbeats:
        i = int(np.argmin(np.abs(beats - db)))
        if abs(beats[i] - db) < 0.07:
            votes[i % beats_per_bar] += 1
    phase = int(np.argmax(votes)) if votes.sum() > 0 else 0

    # Bar starts on detected beats; extend outside the beat range with the
    # local tempo so intros/outros without detected beats still get bars.
    bar_starts = list(beats[phase::beats_per_bar])
    bar_len = beats_per_bar * 60.0 / max(estimate_bpm(beats), 1.0)
    t = bar_starts[0] - bar_len
    while t > -0.5 * bar_len and t > -1.0:
        bar_starts.insert(0, t)
        t -= bar_len
    t = bar_starts[-1] + bar_len
    while t < duration - 0.25 * bar_len:
        bar_starts.append(t)
        t += bar_len
    return [float(b) for b in bar_starts if b >= -0.05]


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


def _to_mono_ds(x: np.ndarray, sr: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        # accept (channels, n) or (n, channels)
        x = x.mean(axis=0) if x.shape[0] <= 2 else x.mean(axis=1)
    if sr == ANALYSIS_SR:
        return x
    # cheap but adequate decimation for loudness features
    factor = sr / ANALYSIS_SR
    n = int(len(x) / factor)
    idx = (np.arange(n) * factor).astype(np.int64)
    # simple boxcar anti-alias filter before picking samples
    k = max(1, int(round(factor)))
    if k > 1:
        kernel = np.ones(k, dtype=np.float32) / k
        x = np.convolve(x, kernel, mode="same")
    return x[idx]


BAND_FFT, BAND_HOP = 2048, 512
FLUX_FFT, FLUX_HOP = 1024, 256


def _frame_times(n_frames: int, n_fft: int, hop: int) -> np.ndarray:
    return (np.arange(n_frames) * hop + n_fft / 2) / ANALYSIS_SR


def _band_power_frames(x: np.ndarray, bands: Dict[str, tuple]) -> Dict[str, np.ndarray]:
    """Power per STFT frame (BAND_HOP) in each frequency band."""
    n_fft = BAND_FFT
    hop = BAND_HOP
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    n_frames = 1 + (len(x) - n_fft) // hop
    window = np.hanning(n_fft).astype(np.float32)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / ANALYSIS_SR)
    masks = {k: (freqs >= lo) & (freqs < hi) for k, (lo, hi) in bands.items()}
    per_frame = {k: np.zeros(n_frames, dtype=np.float32) for k in bands}
    chunk = 512
    for s in range(0, n_frames, chunk):
        e = min(n_frames, s + chunk)
        idx = (np.arange(s, e)[:, None] * hop) + np.arange(n_fft)[None, :]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1)) ** 2
        for k, m in masks.items():
            per_frame[k][s:e] = spec[:, m].sum(axis=1)
    return per_frame


def _bar_index(frame_times, bar_starts):
    bar_starts = np.asarray(bar_starts)
    edges = np.append(bar_starts, bar_starts[-1] + np.median(np.diff(bar_starts)))
    bar_idx = np.searchsorted(edges, frame_times, side="right") - 1
    valid = (bar_idx >= 0) & (bar_idx < len(bar_starts))
    return bar_idx, valid


def _aggregate_percentiles(per_frame, frame_times, bar_starts):
    bar_idx, valid = _bar_index(frame_times, bar_starts)
    out = {}
    n = len(bar_starts)
    for k, v in per_frame.items():
        p90 = np.full(n, 1e-10)
        p25 = np.full(n, 1e-10)
        order = np.argsort(bar_idx[valid], kind="stable")
        bi = bar_idx[valid][order]
        vals = v[valid][order]
        bounds = np.searchsorted(bi, np.arange(n + 1))
        for b in range(n):
            seg = vals[bounds[b]:bounds[b + 1]]
            if len(seg):
                p90[b] = np.percentile(seg, 90)
                p25[b] = np.percentile(seg, 25)
        out[k + "_p90"] = p90
        out[k + "_p25"] = p25
    return out


def _aggregate(per_frame, frame_times, bar_starts):
    bar_starts = np.asarray(bar_starts)
    edges = np.append(bar_starts, bar_starts[-1] + np.median(np.diff(bar_starts)))
    out = {}
    bar_idx = np.searchsorted(edges, frame_times, side="right") - 1
    valid = (bar_idx >= 0) & (bar_idx < len(bar_starts))
    for k, v in per_frame.items():
        sums = np.bincount(bar_idx[valid], weights=v[valid], minlength=len(bar_starts))
        cnt = np.bincount(bar_idx[valid], minlength=len(bar_starts))
        out[k] = sums / np.maximum(cnt, 1)
    return out


def _spectral_flux_frames(x: np.ndarray) -> np.ndarray:
    """Onset strength (how busy the drums are) per frame (FLUX_HOP)."""
    n_fft, hop = FLUX_FFT, FLUX_HOP
    if len(x) < n_fft:
        return np.zeros(0, dtype=np.float32)
    n_frames = 1 + (len(x) - n_fft) // hop
    window = np.hanning(n_fft).astype(np.float32)
    flux = np.zeros(n_frames, dtype=np.float32)
    prev = None
    chunk = 1024
    for s in range(0, n_frames, chunk):
        e = min(n_frames, s + chunk)
        idx = (np.arange(s, e)[:, None] * hop) + np.arange(n_fft)[None, :]
        mag = np.log1p(np.abs(np.fft.rfft(x[idx] * window, axis=1)))
        if prev is not None:
            mag_all = np.vstack([prev[None, :], mag])
        else:
            mag_all = np.vstack([mag[:1], mag])
        d = np.maximum(0.0, np.diff(mag_all, axis=0)).sum(axis=1)
        flux[s:e] = d
        prev = mag[-1]
    return flux


def _db(p: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(p, 1e-10))


@dataclass
class FrameFeatures:
    """Band power per BAND_HOP frame and drum onset strength per FLUX_HOP
    frame. This is the expensive part of the analysis and doesn't depend on
    the bar grid, so it can be cached and re-analyzed after tuning."""

    power: Dict[str, np.ndarray]
    flux: np.ndarray
    has_stems: bool


def frame_features(
    sr: int,
    stems: Optional[Dict[str, np.ndarray]] = None,
    mix: Optional[np.ndarray] = None,
) -> FrameFeatures:
    if stems:
        drums = _to_mono_ds(stems["drums"], sr)
        power = _band_power_frames(drums, {
            "kick": (35.0, 120.0), "drums": (35.0, 5000.0), "hats": (5000.0, 5500.0)})
        power.update(_band_power_frames(_to_mono_ds(stems["bass"], sr),
                                        {"bass": (30.0, 300.0)}))
        power.update(_band_power_frames(_to_mono_ds(stems["other"], sr),
                                        {"music": (100.0, 5000.0), "bright": (2500.0, 5500.0)}))
        power.update(_band_power_frames(_to_mono_ds(stems["vocals"], sr),
                                        {"vocals": (150.0, 5000.0)}))
        return FrameFeatures(power, _spectral_flux_frames(drums), True)
    if mix is None:
        raise ValueError("need stems or mix")
    m = _to_mono_ds(mix, sr)
    power = _band_power_frames(m, {
        "music": (250.0, 4000.0), "hats": (5000.0, 5500.0), "vocals": (300.0, 3400.0),
        "low": (35.0, 200.0)})
    return FrameFeatures(power, _spectral_flux_frames(m), False)


def bars_from_frames(frames: FrameFeatures, bar_starts: Sequence[float]) -> Dict[str, np.ndarray]:
    """Per-bar loudness features in dB relative to the track's loud parts."""
    n_band = len(next(iter(frames.power.values())))
    band_times = _frame_times(n_band, BAND_FFT, BAND_HOP)
    flux_times = _frame_times(len(frames.flux), FLUX_FFT, FLUX_HOP)
    if len(frames.flux):
        busy = _aggregate({"f": frames.flux}, flux_times, bar_starts)["f"]
    else:
        busy = np.zeros(len(bar_starts))
    if frames.has_stems:
        p = _aggregate(frames.power, band_times, bar_starts)
        feats = {k: _db(p[k]) for k in ("kick", "drums", "hats", "bass", "music", "vocals")}
        feats["bright"] = _db(p["bright"]) - _db(p["music"])
    else:
        p = _aggregate({k: frames.power[k] for k in ("music", "hats", "vocals")},
                       band_times, bar_starts)
        # Without stems, tell kick from bass by how the low end behaves inside
        # the bar: a kick is loud peaks with gaps, a bassline fills the gaps.
        low = _aggregate_percentiles({"low": frames.power["low"]}, band_times, bar_starts)
        p["kick"] = low["low_p90"]
        p["bass"] = low["low_p25"]
        feats = {k: _db(v) for k, v in p.items()}
        feats["drums"] = np.maximum(feats["kick"], feats["hats"])
        feats["bright"] = feats["hats"] - feats["music"]
    feats["busy"] = busy

    # Make levels relative: 0 dB = this track's loud level for that part.
    for k in ("kick", "drums", "hats", "bass", "music", "vocals"):
        ref = np.percentile(feats[k], 90)
        feats[k] = np.clip(feats[k] - ref, -40.0, 6.0)
    feats["busy"] = feats["busy"] / max(np.percentile(feats["busy"], 90), 1e-6)
    return feats


def bar_features(
    bar_starts: Sequence[float],
    sr: int,
    stems: Optional[Dict[str, np.ndarray]] = None,
    mix: Optional[np.ndarray] = None,
) -> Dict[str, np.ndarray]:
    return bars_from_frames(frame_features(sr, stems=stems, mix=mix), bar_starts)


# ---------------------------------------------------------------------------
# Phrases and sections
# ---------------------------------------------------------------------------


def _norm01(x: np.ndarray, lo_pct=5, hi_pct=95) -> np.ndarray:
    lo, hi = np.percentile(x, lo_pct), np.percentile(x, hi_pct)
    if hi - lo < 1e-6:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def energy_curve(feats: Dict[str, np.ndarray]) -> np.ndarray:
    kick = _norm01(feats["kick"])
    bass = _norm01(feats["bass"])
    drums = _norm01(feats["drums"])
    music = _norm01(feats["music"])
    vocals = _norm01(feats["vocals"])
    return 0.32 * kick + 0.28 * bass + 0.15 * drums + 0.15 * music + 0.10 * vocals


def novelty(feats: Dict[str, np.ndarray], width: int = 4) -> np.ndarray:
    """How much the music changes at the start of each bar."""
    keys = ("kick", "bass", "drums", "music", "vocals", "hats")
    m = np.stack([feats[k] for k in keys], axis=1)  # bars x d (dB)
    m = m / 10.0  # 10 dB change == 1 unit
    n = len(m)
    nov = np.zeros(n)
    for b in range(1, n):
        lo = max(0, b - width)
        hi = min(n, b + width)
        before = m[lo:b].mean(axis=0)
        after = m[b:hi].mean(axis=0)
        nov[b] = float(np.linalg.norm(after - before))
    return nov


def phrase_origin(nov: np.ndarray, phrase_bars: int = 8) -> int:
    """Pick the bar offset of the phrase grid from where the music changes."""
    if len(nov) < phrase_bars * 2:
        return 0
    scores = np.zeros(phrase_bars)
    for o in range(phrase_bars):
        scores[o] = nov[o::phrase_bars].sum()
    # Strongest single change (usually the first drop) gets an extra vote:
    biggest = int(np.argmax(nov))
    scores[biggest % phrase_bars] += nov[biggest]
    return int(np.argmax(scores))


def _differs(a: dict, b: dict) -> bool:
    """True if two neighbouring blocks sound clearly different."""
    if a is b:
        return True
    return (abs(a["energy"] - b["energy"]) > 0.08 or abs(a["kick"] - b["kick"]) > 0.4
            or abs(a["bass"] - b["bass"]) > 0.4)


def _otsu(values: np.ndarray) -> float:
    """Threshold splitting values into a low and a high group (1-D Otsu)."""
    v = np.sort(np.asarray(values, dtype=float))
    if len(v) < 2 or v[-1] - v[0] < 1e-6:
        return float(v[0]) if len(v) else 0.0
    best_t, best_score = v[0], -1.0
    for i in range(1, len(v)):
        if v[i] - v[i - 1] < 1e-9:
            continue
        lo, hi = v[:i], v[i:]
        score = len(lo) * len(hi) * (hi.mean() - lo.mean()) ** 2
        if score > best_score:
            best_score, best_t = score, (v[i - 1] + v[i]) / 2.0
    return float(best_t)


def _classify_blocks(feats, energy, block_starts, n_bars):
    """Return per-block (level, energy, rising, has_kick, has_bass)."""
    kick_on_bar = feats["kick"] > -12.0
    bass_on_bar = feats["bass"] > -12.0
    out = []
    for i, s in enumerate(block_starts):
        e = block_starts[i + 1] if i + 1 < len(block_starts) else n_bars
        sl = slice(s, e)
        en = float(np.mean(energy[sl]))
        kick = float(np.mean(kick_on_bar[sl]))
        bass = float(np.mean(bass_on_bar[sl]))
        # "Rising": brightness/busyness/energy going up through the block, or
        # drums getting busier (snare rolls) — typical of a build-up.
        seg_len = e - s
        rising = False
        if seg_len >= 2:
            x = np.arange(seg_len)
            def slope(v):
                return float(np.polyfit(x, v[sl], 1)[0]) if seg_len > 1 else 0.0
            rising = (slope(feats["bright"]) > 0.4 or slope(feats["busy"]) > 0.06
                      or slope(energy) > 0.03)
        out.append(dict(start=s, end=e, energy=en, kick=kick, bass=bass, rising=rising))
    return out


def detect_sections(
    bar_starts: Sequence[float],
    feats: Dict[str, np.ndarray],
    phrase_bars: int = 8,
    block_bars: int = 4,
):
    n_bars = len(bar_starts)
    energy = energy_curve(feats)
    nov = novelty(feats)
    origin = phrase_origin(nov, phrase_bars)

    # 4-bar blocks aligned to the phrase grid (first block may be shorter)
    first = origin % block_bars
    block_starts = ([0] if first > 0 else []) + list(range(first, n_bars, block_bars))
    blocks = _classify_blocks(feats, energy, block_starts, n_bars)
    if not blocks:
        return origin, [], energy

    ens = np.array([b["energy"] for b in blocks])
    hi_thr = max(_otsu(ens), 0.45)
    dynamic = np.percentile(ens, 90) - np.percentile(ens, 10)

    for b in blocks:
        if b["kick"] >= 0.5 and b["bass"] >= 0.5 and b["energy"] >= hi_thr - 1e-6:
            b["level"] = "high"
        elif b["kick"] < 0.25 or b["energy"] < hi_thr * 0.55:
            b["level"] = "low"
        else:
            b["level"] = "mid"

    labels = [None] * len(blocks)
    if dynamic < 0.2:
        # Not much contrast (hip hop, pop, some house): label by relative
        # energy instead of drops/breakdowns.
        med = np.median(ens)
        for i, b in enumerate(blocks):
            labels[i] = "Hook" if b["energy"] > med + 0.05 else "Verse"
    else:
        high = [b["level"] == "high" for b in blocks]
        first_high = high.index(True) if any(high) else None
        last_high = len(high) - 1 - high[::-1].index(True) if any(high) else None
        for i, b in enumerate(blocks):
            if b["level"] == "high":
                labels[i] = "Drop"
            elif first_high is not None and i < first_high:
                labels[i] = "Intro"
            elif last_high is not None and i > last_high:
                labels[i] = "Outro"
            elif b["level"] == "low":
                labels[i] = "Breakdown"
            else:
                labels[i] = "Groove"
        # Build-ups: the non-drop block(s) right before each drop that rise
        # in energy, or that have drums without bass (classic build).
        for i in range(1, len(blocks)):
            if labels[i] == "Drop" and labels[i - 1] != "Drop":
                j = i - 1
                steps = 0
                while j >= 0 and labels[j] != "Drop" and steps < 2:
                    b = blocks[j]
                    classic = b["kick"] >= 0.25 and b["bass"] < 0.5
                    # The block right before the drop may be a build because it
                    # rises or has drums without bass; further back only if it
                    # clearly rises (otherwise it's still the intro/breakdown).
                    if b["rising"] or (steps == 0 and classic and b["level"] != "low"
                                       and _differs(b, blocks[max(j - 1, 0)])):
                        labels[j] = "Build"
                        j -= 1
                        steps += 1
                    else:
                        break
        # A track with no intro before the first drop starts at the drop.
        if not any(lbl == "Intro" for lbl in labels) and labels[0] not in ("Drop", "Build"):
            labels[0] = "Intro"

    # Merge consecutive blocks with the same label into sections.
    sections: List[Section] = []
    for b, lbl in zip(blocks, labels):
        if sections and sections[-1].label == lbl:
            s = sections[-1]
            total = s.bars + (b["end"] - b["start"])
            s.energy = (s.energy * s.bars + b["energy"] * (b["end"] - b["start"])) / total
            s.end_bar = b["end"]
        else:
            sections.append(Section(b["start"], b["end"], lbl, b["energy"]))

    # Absorb lonely 4-bar sections sandwiched between the same label
    # (a single quiet block inside a drop is usually a fill, not a breakdown),
    # but keep short builds — they are real.
    changed = True
    while changed:
        changed = False
        for i in range(1, len(sections) - 1):
            s = sections[i]
            if (s.bars <= block_bars and s.label != "Build"
                    and sections[i - 1].label == sections[i + 1].label):
                prev, nxt = sections[i - 1], sections[i + 1]
                prev.end_bar = nxt.end_bar
                prev.energy = max(prev.energy, nxt.energy)
                del sections[i:i + 2]
                changed = True
                break

    # Number repeated drops: Drop, Drop 2, ...
    drop_count = 0
    for s in sections:
        if s.label == "Drop":
            drop_count += 1
            if drop_count > 1:
                s.label = f"Drop {drop_count}"

    return origin, sections, energy


def analyze_structure(
    beats: Sequence[float],
    downbeats: Sequence[float],
    duration: float,
    sr: int = 0,
    stems: Optional[Dict[str, np.ndarray]] = None,
    mix: Optional[np.ndarray] = None,
    phrase_bars: int = 8,
    frames: Optional[FrameFeatures] = None,
) -> Structure:
    """Pass either the audio (stems or mix, at sample rate sr) or
    precomputed frame features."""
    beats = [float(b) for b in beats]
    bpb = beats_per_bar_from(beats, downbeats)
    bar_starts = build_bars(beats, downbeats, duration, bpb)
    bpm = estimate_bpm(beats)
    if len(bar_starts) < 8:
        return Structure(bpm, bpb, beats, bar_starts, phrase_bars, 0,
                         list(range(0, len(bar_starts), phrase_bars)))
    if frames is None:
        frames = frame_features(sr, stems=stems, mix=mix)
    feats = bars_from_frames(frames, bar_starts)
    origin, sections, energy = detect_sections(bar_starts, feats, phrase_bars)

    edges = list(bar_starts) + [duration]
    for s in sections:
        s.start = float(edges[s.start_bar])
        s.end = float(edges[min(s.end_bar, len(edges) - 1)])

    phrases = sorted(set(range(origin % phrase_bars, len(bar_starts), phrase_bars))
                     | {s.start_bar for s in sections})
    return Structure(
        bpm=bpm,
        beats_per_bar=bpb,
        beats=beats,
        bar_starts=bar_starts,
        phrase_bars=phrase_bars,
        phrase_origin_bar=origin % phrase_bars,
        phrases=phrases,
        sections=sections,
        bar_energy=[float(e) for e in energy],
    )


# Which sections get hot cues when there are more than max_cues: drops
# first, then grooves, breakdowns and builds (the user's priority), then the
# intro/outro if slots are left. Mixxx fills the pads in this order, so drops
# are always on the first pads. Hook/Verse are the drop/groove of
# low-contrast music.
CUE_PRIORITY = {"Drop": 0, "Hook": 0, "Groove": 1, "Verse": 1, "Breakdown": 2,
                "Build": 3, "Intro": 4, "Outro": 4}


def suggest_cues(structure: Structure, max_cues: int = 8) -> List[dict]:
    """Hot cue suggestions at the start of the sections, most important
    first (CUE_PRIORITY; in track order within the same kind)."""
    ranked = []
    seen: Dict[str, int] = {}
    for s in structure.sections:
        base = s.label.split(" ")[0]
        if base not in CUE_PRIORITY:
            continue
        if base == "Intro" and s.start_bar != 0:
            continue  # only an intro that starts the track
        # Repeated kinds are numbered like drops ("BREAKDOWN 2"), so every
        # pad has its own name (Mixxx also tells its cues apart by label)
        seen[base] = seen.get(base, 0) + 1
        label = s.label if s.label != base or seen[base] == 1 else f"{base} {seen[base]}"
        ranked.append((CUE_PRIORITY[base], s.start, {
            "position": round(s.start, 4),
            "bar": s.start_bar,
            "label": label.upper(),
            "color": SECTION_COLORS.get(base, "#FFFFFF"),
        }))
    ranked.sort(key=lambda r: (r[0], r[1]))
    return [cue for _, _, cue in ranked[:max_cues]]

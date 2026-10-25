"""Synthetic EDM track: checks bars, phrase grid and section labels.

Run:  python -m pytest tests  (or just python tests/test_structure.py)
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from stemprep.structure import analyze_structure, suggest_cues  # noqa: E402

SR = 22050
BPM = 128.0
BEAT = 60.0 / BPM
OFFSET = 0.37  # silence before the first downbeat

# (label, bars, kick, bass, music, hats, riser, vocals)
LAYOUT = [
    ("Intro", 16, 1, 0, 0.3, 1, 0, 0),
    ("Build", 8, 0, 0, 0.6, 0, 1, 0),
    ("Drop", 16, 1, 1, 1.0, 1, 0, 1),
    ("Breakdown", 16, 0, 0, 0.5, 0, 0, 1),
    ("Build", 8, 0.3, 0, 0.7, 0, 1, 0),
    ("Drop 2", 16, 1, 1, 1.0, 1, 0, 1),
    ("Outro", 16, 1, 0, 0.2, 1, 0, 0),
]


def synth(rng):
    total_bars = sum(b for _, b, *_ in LAYOUT)
    n = int((OFFSET + total_bars * 4 * BEAT + 2.0) * SR)
    t = np.arange(n) / SR
    stems = {k: np.zeros(n, dtype=np.float32) for k in ("drums", "bass", "other", "vocals")}
    bar = 0
    for label, bars, kick, bass, music, hats, riser, vox in LAYOUT:
        for b in range(bars):
            for beat in range(4):
                start = OFFSET + ((bar + b) * 4 + beat) * BEAT
                i0 = int(start * SR)
                seg = np.arange(int(BEAT * SR))
                i1 = min(n, i0 + len(seg))
                seg = seg[: i1 - i0]
                tt = seg / SR
                if kick:
                    env = np.exp(-tt * 18)
                    f = 50 + 80 * np.exp(-tt * 30)
                    stems["drums"][i0:i1] += kick * 0.9 * env * np.sin(2 * np.pi * np.cumsum(f) / SR)
                if hats:
                    h0 = i0 + int(BEAT / 2 * SR)
                    h1 = min(n, h0 + int(0.05 * SR))
                    stems["drums"][h0:h1] += 0.15 * rng.standard_normal(h1 - h0) * np.exp(
                        -np.arange(h1 - h0) / SR * 60)
                if riser:
                    # snare roll getting denser and a noise sweep getting louder
                    prog = (b * 4 + beat) / (bars * 4)
                    hits = 1 if prog < 0.5 else (2 if prog < 0.75 else 4)
                    for h in range(hits):
                        s0 = i0 + int(h * BEAT / hits * SR)
                        s1 = min(n, s0 + int(0.06 * SR))
                        stems["drums"][s0:s1] += 0.3 * rng.standard_normal(s1 - s0)
                    stems["other"][i0:i1] += 0.2 * prog * rng.standard_normal(i1 - i0)
                if bass:
                    stems["bass"][i0:i1] += 0.6 * np.sin(2 * np.pi * 55 * tt) * (tt > 0.1 * BEAT)
                if music:
                    stems["other"][i0:i1] += music * 0.25 * (
                        np.sin(2 * np.pi * 440 * tt) + np.sin(2 * np.pi * 554 * tt))
                if vox:
                    stems["vocals"][i0:i1] += 0.2 * np.sin(2 * np.pi * 330 * tt) * np.sin(
                        2 * np.pi * 5 * tt) ** 2
        bar += bars
    return stems, total_bars, n / SR


def ground_truth_sections():
    out, bar = [], 0
    for label, bars, *_ in LAYOUT:
        out.append((label, bar, bar + bars))
        bar += bars
    return out


def test_synthetic_edm():
    rng = np.random.default_rng(1)
    stems, total_bars, duration = synth(rng)
    beats = OFFSET + np.arange(total_bars * 4) * BEAT
    beats = beats + rng.normal(0, 0.008, len(beats))  # tracker jitter
    downbeats = list(beats[::4])
    # tracker misses a few downbeats and adds one wrong one
    for i in (5, 6, 40, 41, 42):
        downbeats[i] = None
    downbeats = [d for d in downbeats if d is not None] + [beats[2 + 4 * 30]]
    downbeats.sort()

    s = analyze_structure(beats, downbeats, duration, SR, stems=stems)
    assert abs(s.bpm - BPM) < 0.2, s.bpm
    assert s.beats_per_bar == 4
    # bars line up with the true downbeats
    true_bars = OFFSET + np.arange(total_bars) * 4 * BEAT
    k = int(np.argmin(np.abs(np.asarray(s.bar_starts) - true_bars[0])))
    assert abs(s.bar_starts[k] - true_bars[0]) < 0.03
    assert s.phrase_origin_bar % 8 == k % 8

    got = [(sec.label, sec.start_bar - k, sec.end_bar - k) for sec in s.sections]
    print("\nDetected sections:")
    for g in got:
        print("  ", g)
    print("Cues:", [(c["label"], c["bar"] - k) for c in suggest_cues(s)])
    truth = ground_truth_sections()
    # Every true section start (other than 0) must be a detected boundary,
    # and the labels must match.
    detected_starts = {start: label for label, start, _ in got}
    for label, start, _ in truth:
        assert start in detected_starts, (label, start, got)
        assert detected_starts[start] == label, (label, start, detected_starts[start])


if __name__ == "__main__":
    test_synthetic_edm()
    print("ok")

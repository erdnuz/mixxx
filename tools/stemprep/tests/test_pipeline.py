"""End-to-end pipeline with stand-in models (no torch needed)."""
import json, os, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import test_structure as T
from stemprep.audio import write_wav
from stemprep.pipeline import (Options, analyze_track, load_features, make_stems,
                               process_track, reanalyze, sidecar_path)
from stemprep.stemfile import read_stem_manifest

class FakeSeparator:
    def __init__(self, stems): self.stems = stems
    def separate(self, audio, sr):
        n = audio.shape[1]
        out = {}
        for k, v in self.stems.items():
            v = np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v).astype(np.float32)
            out[k] = np.stack([v, v])
        return out

class FakeBeats:
    checkpoint = "fake"
    def __init__(self, beats): self.beats = beats; self.calls = 0
    def track(self, audio, sr): self.calls += 1; return self.beats, self.beats[::4]

def test_pipeline():
    T.LAYOUT = T.LAYOUT[:4]
    rng = np.random.default_rng(0)
    stems, nb, dur = T.synth(rng)
    mix = sum(stems.values())
    beats = T.OFFSET + np.arange(nb * 4) * T.BEAT
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        src = d / "Artist - Song.wav"
        up = np.interp(np.linspace(0, len(mix) - 1, int(len(mix) * 44100 / T.SR)), np.arange(len(mix)), mix)
        write_wav(src, np.stack([up, up]) * 0.5)
        tracker = FakeBeats(beats)

        # Fast tier: sidecar next to the source, from the mix
        assert analyze_track(src, tracker, Options()) == src
        mix = json.loads(sidecar_path(src).read_text())
        assert mix["tier"] == "mix" and "stems" not in mix
        assert load_features(src) is not None

        # Stems tier: beats are reused, not tracked again
        out = process_track(src, d / "Stems", FakeSeparator(stems), tracker, Options())
        assert tracker.calls == 1
        assert out.name == "Artist - Song.stem.mp4" and out.exists()
        assert read_stem_manifest(out)["version"] == 1
        data = json.loads(sidecar_path(out).read_text())
        source_data = json.loads(sidecar_path(src).read_text())
        assert source_data["tier"] == "stems" and source_data["stems"] == str(out)
        assert source_data["source_size"] == src.stat().st_size
        # the stem file plays in sync with the source (AAC priming handled)
        print("offset ms:", source_data["stems_offset_ms"])
        assert abs(source_data["stems_offset_ms"]) <= 5
        labels = [s["label"] for s in data["sections"]]
        print(labels, data["bpm"], [c["label"] for c in data["cues"]])
        # a quiet part after the last drop at the end of the track is the outro
        assert labels == ["Intro", "Build", "Drop", "Outro"]
        assert abs(data["bpm"] - 128) < 0.2
        # second run skips
        assert process_track(src, d / "Stems", None, None, Options()) is None

        # Re-analysis keeps the stem link and Mixxx's cue note; the source's own
        # (mix) features don't override the stems analysis
        source_data["mixxx_cues_applied"] = True
        sidecar_path(src).write_text(json.dumps(source_data))
        assert reanalyze(src) and reanalyze(out)
        again = json.loads(sidecar_path(src).read_text())
        assert again["tier"] == "stems" and again["stems"] == str(out)
        assert again["mixxx_cues_applied"] is True
        assert again["stems_sample_rate"] == 44100

        # Fast stems first, then high quality ones replace them
        src2 = d / "Artist - Fast.wav"
        src2.write_bytes(src.read_bytes())
        fast = make_stems(src2, d / "Stems", FakeSeparator(stems), tracker,
                          Options(stems_quality="fast"))
        assert fast.parent.name == "fast" and fast.exists()
        assert json.loads(sidecar_path(src2).read_text())["stems_quality"] == "fast"
        hq = make_stems(src2, d / "Stems", FakeSeparator(stems), tracker, Options())
        assert hq.parent == d / "Stems" and not fast.exists()
        linked = json.loads(sidecar_path(src2).read_text())
        assert linked["stems"] == str(hq) and linked["stems_quality"] == "hq"

if __name__ == "__main__":
    test_pipeline(); print("ok")

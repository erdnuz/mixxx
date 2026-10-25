"""End-to-end pipeline with stand-in models (no torch needed)."""
import json, os, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import test_structure as T
from stemprep.audio import write_wav
from stemprep.pipeline import Options, process_track, sidecar_path
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
    def __init__(self, beats): self.beats = beats
    def track(self, audio, sr): return self.beats, self.beats[::4]

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
        out = process_track(src, d / "Stems", FakeSeparator(stems), FakeBeats(beats), Options())
        assert out.name == "Artist - Song.stem.mp4" and out.exists()
        assert read_stem_manifest(out)["version"] == 1
        data = json.loads(sidecar_path(out).read_text())
        assert sidecar_path(src).exists()
        labels = [s["label"] for s in data["sections"]]
        print(labels, data["bpm"], [c["label"] for c in data["cues"]])
        # a quiet part after the last drop at the end of the track is the outro
        assert labels == ["Intro", "Build", "Drop", "Outro"]
        assert abs(data["bpm"] - 128) < 0.2
        # second run skips
        assert process_track(src, d / "Stems", None, None, Options()) is None

if __name__ == "__main__":
    test_pipeline(); print("ok")

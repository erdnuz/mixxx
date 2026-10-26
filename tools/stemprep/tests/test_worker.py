"""The worker's steps for a queued track, with stand-in models."""
import json, os, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import test_structure as T
from test_pipeline import FakeBeats, FakeSeparator
from stemprep.audio import write_wav
from stemprep import worker
from stemprep.pipeline import sidecar_path


def test_worker_steps():
    T.LAYOUT = T.LAYOUT[:4]
    rng = np.random.default_rng(0)
    stems, nb, _ = T.synth(rng)
    mix = sum(stems.values())
    beats = T.OFFSET + np.arange(nb * 4) * T.BEAT
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        track = d / "Downloads" / "130 fweak" / "Artist - Song.wav"
        track.parent.mkdir(parents=True)
        up = np.interp(np.linspace(0, len(mix) - 1, int(len(mix) * 44100 / T.SR)),
                       np.arange(len(mix)), mix)
        write_wav(track, np.stack([up, up]) * 0.5)

        queue = d / "queue"
        queue.mkdir()
        (queue / "b.json").write_text(json.dumps({"path": str(track), "priority": 0}))
        (queue / "a.json").write_text(json.dumps({"path": str(d / "missing.mp3"), "priority": 5}))
        (queue / "bad.json").write_text("not json")
        reqs = worker.read_queue(queue)
        assert [r.file.name for r in reqs] == ["b.json", "a.json"]  # by priority
        assert not (queue / "bad.json").exists()

        w = worker.Worker(d)
        w._beats = FakeBeats(beats)
        w._separators = {worker.FAST_MODEL: FakeSeparator(stems)}

        req = reqs[0]
        assert w.step(req) is True       # 1. analysis from the mix
        assert json.loads(sidecar_path(track).read_text())["tier"] == "mix"
        assert w.step(req) is False      # 2. fast stems, finished (Demucs is `stemprep hq`)
        data = json.loads(sidecar_path(track).read_text())
        assert data["stems_quality"] == "fast" and "/fast/" in data["stems"].replace("\\", "/")
        assert w.step(reqs[1]) is False  # missing track: dropped


if __name__ == "__main__":
    test_worker_steps()
    print("ok")

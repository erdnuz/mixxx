import json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from stemprep.stemfile import write_stem_file, read_stem_manifest, STEM_ORDER
from stemprep.audio import decode, find_ffmpeg

def test_stem_file_roundtrip():
    sr = 44100
    t = np.arange(sr * 3) / sr
    stems = {s: np.stack([np.sin(2*np.pi*f*t), np.sin(2*np.pi*f*t)]).astype(np.float32) * 0.2
             for s, f in zip(STEM_ORDER, (60, 110, 440, 880))}
    mix = sum(stems.values())
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        src = d / "src.m4a"
        subprocess.run([find_ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=3",
                        "-metadata", "title=Test Song", "-metadata", "artist=Someone",
                        "-c:a", "aac", str(src)], check=True)
        out = write_stem_file(d / "Someone - Test Song.stem.mp4", mix, stems, source_for_tags=src)
        man = read_stem_manifest(out)
        assert man["version"] == 1 and [s["name"] for s in man["stems"]] == ["Drums", "Bass", "Melody", "Vocals"]
        probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                                           "-show_streams", "-show_format", str(out)],
                                          capture_output=True, check=True).stdout)
        audio = [s for s in probe["streams"] if s["codec_type"] == "audio"]
        assert len(audio) == 5 and all(s["channels"] == 2 for s in audio)
        assert probe["format"]["tags"]["title"] == "Test Song"
        # stem 2 (bass, 110 Hz) decodes back to roughly the right content
        bass = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-map", "0:a:2", "-f", "f32le",
                               "-ac", "1", "-ar", "44100", "-"], capture_output=True, check=True).stdout
        b = np.frombuffer(bass, dtype=np.float32)
        spec = np.abs(np.fft.rfft(b[sr//2: sr//2 + sr]))
        assert abs(np.argmax(spec) - 110) <= 2
        print("streams:", len(audio), "manifest ok, size", out.stat().st_size)

if __name__ == "__main__":
    test_stem_file_roundtrip(); print("ok")

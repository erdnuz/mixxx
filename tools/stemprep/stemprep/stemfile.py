"""Write Native Instruments style .stem.mp4 files that Mixxx 2.6+ can play.

Layout: audio stream 0 is the full mix, streams 1-4 are the stems
(drums, bass, melody, vocals). A JSON manifest lives in the MP4 atom
moov/udta/stem, which is how Mixxx (and Traktor) recognise a stem file.
"""

from __future__ import annotations

import json
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .audio import SAMPLE_RATE, find_ffmpeg, write_wav

STEM_ORDER = ("drums", "bass", "other", "vocals")
STEM_NAMES = {"drums": "Drums", "bass": "Bass", "other": "Melody", "vocals": "Vocals"}
STEM_COLORS = {"drums": "#009E73", "bass": "#D55E00", "other": "#CC79A7", "vocals": "#56B4E9"}


def manifest() -> dict:
    return {
        "stems": [{"name": STEM_NAMES[s], "color": STEM_COLORS[s]} for s in STEM_ORDER],
        "mastering_dsp": {
            "compressor": {"enabled": False, "input_gain": 0.5, "output_gain": 0.5,
                           "threshold": 0, "dry_wet": 50, "attack": 0.003,
                           "release": 0.3, "ratio": 10, "hp_cutoff": 300},
            "limiter": {"enabled": False, "release": 0.05, "threshold": 0,
                        "ceiling": -0.35},
        },
        "version": 1,
    }


def write_stem_file(
    out_path: Path,
    mix: np.ndarray,
    stems: Dict[str, np.ndarray],
    source_for_tags: Optional[Path] = None,
    bitrate: str = "256k",
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    """Encode mix + 4 stems to AAC in one MP4 and add the stem manifest."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out_path.with_name(out_path.name + ".part.mp4")
    with tempfile.TemporaryDirectory(prefix="stemprep_") as tmp:
        tmp = Path(tmp)
        inputs = [tmp / "mix.wav"] + [tmp / f"{s}.wav" for s in STEM_ORDER]
        n = mix.shape[1]
        write_wav(inputs[0], _fit(mix, n), sample_rate)
        for s, p in zip(STEM_ORDER, inputs[1:]):
            write_wav(p, _fit(stems[s], n), sample_rate)

        cmd = [find_ffmpeg(), "-v", "error", "-nostdin", "-y"]
        for p in inputs:
            cmd += ["-i", str(p)]
        has_source = source_for_tags is not None and Path(source_for_tags).exists()
        if has_source:
            cmd += ["-i", str(source_for_tags)]
        for i in range(len(inputs)):
            cmd += ["-map", f"{i}:a:0"]
        if has_source:
            src = len(inputs)
            # Copy title/artist/album/etc. and the cover picture if there is one
            cmd += ["-map_metadata", str(src), "-map", f"{src}:v:0?",
                    "-c:v", "copy", "-disposition:v:0", "attached_pic"]
        cmd += ["-c:a", "aac", "-b:a", bitrate, "-ar", str(sample_rate)]
        for i, name in enumerate(["Mix"] + [STEM_NAMES[s] for s in STEM_ORDER]):
            cmd += [f"-metadata:s:a:{i}", f"handler_name={name}"]
        cmd += ["-f", "mp4", str(tmp_out)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed writing stem file:\n" +
                               proc.stderr.decode(errors="replace"))
    add_stem_manifest(tmp_out, manifest())
    tmp_out.replace(out_path)
    return out_path


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = np.stack([x, x])
    if x.shape[1] > n:
        return x[:, :n]
    if x.shape[1] < n:
        return np.pad(x, ((0, 0), (0, n - x.shape[1])))
    return x


# ---------------------------------------------------------------------------
# Minimal MP4 box editing
# ---------------------------------------------------------------------------


def _read_boxes(data: bytes, start: int, end: int):
    """Yield (type, box_start, header_size, box_end) for boxes in [start, end)."""
    pos = start
    while pos + 8 <= end:
        size, typ = struct.unpack(">I4s", data[pos:pos + 8])
        header = 8
        if size == 1:
            size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            raise ValueError(f"corrupt MP4 box {typ!r} at {pos}")
        yield typ.decode("latin-1"), pos, header, pos + size
        pos += size


def _box(typ: str, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), typ.encode("latin-1")) + payload


def add_stem_manifest(path: Path, manifest_obj: dict) -> None:
    """Insert (or replace) moov/udta/stem. The moov box must come after mdat
    (ffmpeg's default without +faststart) so no sample offsets move."""
    data = Path(path).read_bytes()
    top = list(_read_boxes(data, 0, len(data)))
    moov = [b for b in top if b[0] == "moov"]
    if not moov:
        raise ValueError("no moov box")
    _, m_start, m_hdr, m_end = moov[0]
    mdat_after = any(b[0] == "mdat" and b[1] > m_start for b in top)
    if mdat_after:
        raise ValueError("moov before mdat (faststart) is not supported")

    payload = json.dumps(manifest_obj, separators=(",", ":")).encode("utf-8")
    stem_box = _box("stem", payload)

    children = list(_read_boxes(data, m_start + m_hdr, m_end))
    new_moov_payload = b""
    found_udta = False
    for typ, b_start, b_hdr, b_end in children:
        if typ == "udta":
            found_udta = True
            udta_children = b""
            for ctyp, c_start, _, c_end in _read_boxes(data, b_start + b_hdr, b_end):
                if ctyp != "stem":
                    udta_children += data[c_start:c_end]
            new_moov_payload += _box("udta", udta_children + stem_box)
        else:
            new_moov_payload += data[b_start:b_end]
    if not found_udta:
        new_moov_payload += _box("udta", stem_box)
    if m_hdr != 8:
        raise ValueError("64-bit moov size not supported")
    new_moov = _box("moov", new_moov_payload)
    Path(path).write_bytes(data[:m_start] + new_moov + data[m_end:])


def read_stem_manifest(path: Path) -> Optional[dict]:
    """Read moov/udta/stem the same way Mixxx does (used by the tests)."""
    data = Path(path).read_bytes()
    for typ, s, h, e in _read_boxes(data, 0, len(data)):
        if typ != "moov":
            continue
        for t2, s2, h2, e2 in _read_boxes(data, s + h, e):
            if t2 != "udta":
                continue
            for t3, s3, h3, e3 in _read_boxes(data, s2 + h2, e2):
                if t3 == "stem":
                    return json.loads(data[s3 + h3:e3].rstrip(b"\0"))
    return None

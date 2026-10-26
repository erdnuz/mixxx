"""Decoding and encoding audio with the ffmpeg command line tool."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np

SAMPLE_RATE = 44100

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".aiff", ".aif", ".ogg",
                    ".opus", ".wma", ".alac", ".mp4"}


def find_ffmpeg() -> str:
    """ffmpeg on PATH, or the copy spotDL downloads into ~/.spotdl."""
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    found = shutil.which("ffmpeg")
    if found:
        return found
    spotdl_copy = Path.home() / ".spotdl" / exe
    if spotdl_copy.exists():
        return str(spotdl_copy)
    raise RuntimeError(
        "ffmpeg not found. Install it (winget install Gyan.FFmpeg) or run "
        "'spotdl --download-ffmpeg'.")


def find_ffprobe() -> Optional[str]:
    ffmpeg = Path(find_ffmpeg())
    probe = ffmpeg.with_name(ffmpeg.name.replace("ffmpeg", "ffprobe"))
    if probe.exists():
        return str(probe)
    return shutil.which("ffprobe")


def decode(path: Path, sample_rate: int = SAMPLE_RATE, channels: int = 2,
           max_seconds: Optional[float] = None) -> np.ndarray:
    """Decode any audio file to float32, shape (channels, n). Analysis that
    only needs mono at a low rate (beats, sections) is much cheaper with
    channels=1, sample_rate=22050."""
    cmd = [find_ffmpeg(), "-v", "error", "-nostdin", "-i", str(path),
           "-map", "0:a:0", "-f", "f32le", "-acodec", "pcm_f32le",
           "-ac", str(channels), "-ar", str(sample_rate)]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg could not decode {path}: {proc.stderr.decode(errors='replace')}")
    data = np.frombuffer(proc.stdout, dtype=np.float32)
    return data.reshape(-1, channels).T.copy()


def probe_tags(path: Path) -> dict:
    probe = find_ffprobe()
    if not probe:
        return {}
    proc = subprocess.run([probe, "-v", "error", "-print_format", "json", "-show_format",
                           str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout).get("format", {}).get("tags", {})
    except json.JSONDecodeError:
        return {}


def read_wav(path: Path) -> np.ndarray:
    """Read a 32-bit float WAV as written by write_wav(): shape (channels, n)."""
    import struct

    data = Path(path).read_bytes()
    channels = struct.unpack("<H", data[22:24])[0]
    return np.frombuffer(data[44:], dtype=np.float32).reshape(-1, channels).T.copy()


def write_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write (2, n) float audio as 32-bit float WAV (no extra dependencies)."""
    import struct

    audio = np.asarray(audio, dtype=np.float32)
    interleaved = audio.T.reshape(-1).tobytes()
    channels = audio.shape[0]
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(interleaved)))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 3, channels, sample_rate,
                            sample_rate * channels * 4, channels * 4, 32))
        f.write(b"data")
        f.write(struct.pack("<I", len(interleaved)))
        f.write(interleaved)

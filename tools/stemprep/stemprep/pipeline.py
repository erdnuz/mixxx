"""One track in, stem file + structure sidecar out."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import __version__
from .audio import SAMPLE_RATE, decode
from .structure import SECTION_COLORS, Structure, analyze_structure, suggest_cues

log = logging.getLogger("stemprep")

SIDECAR_SUFFIX = ".structure.json"


def sidecar_path(audio_path: Path) -> Path:
    """'Song.stem.mp4' -> 'Song.stem.mp4.structure.json' (what Mixxx looks for)."""
    return audio_path.with_name(audio_path.name + SIDECAR_SUFFIX)


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
    sidecar_for_source: bool = True


def structure_to_json(s: Structure, duration: float, analyzed: Path) -> dict:
    return {
        "format": "mixxx-structure",
        "version": 1,
        "generator": f"stemprep {__version__}",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
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


def write_sidecar(audio_path: Path, data: dict) -> Path:
    path = sidecar_path(audio_path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


def process_track(source: Path, out_dir: Path, separator, beat_tracker,
                  opts: Options) -> Optional[Path]:
    """Returns the file to load in Mixxx (stem file, or the source in
    analysis-only mode), or None if skipped."""
    source = Path(source)
    is_stem_source = source.name.lower().endswith((".stem.mp4", ".stem.m4a"))
    target = source if (is_stem_source or not opts.make_stems) else stem_output_path(source, out_dir)

    if not opts.force and target.exists() and sidecar_path(target).exists():
        log.info("Already done: %s", target.name)
        return None

    t0 = time.time()
    log.info("Decoding %s", source.name)
    audio = decode(source, SAMPLE_RATE)
    duration = audio.shape[1] / SAMPLE_RATE

    stems = None
    if opts.make_stems and not is_stem_source:
        log.info("Separating stems (this is the slow part)...")
        stems = separator.separate(audio, SAMPLE_RATE)

    log.info("Tracking beats and downbeats...")
    beats, downbeats = beat_tracker.track(audio, SAMPLE_RATE)
    if len(beats) < 8:
        log.warning("Too few beats found in %s; skipping structure", source.name)

    log.info("Finding bars, phrases and sections...")
    structure = analyze_structure(beats, downbeats, duration, SAMPLE_RATE,
                                  stems=stems, mix=None if stems else audio)
    data = structure_to_json(structure, duration, source)

    if stems is not None:
        from .stemfile import write_stem_file

        log.info("Writing %s", target.name)
        write_stem_file(target, audio, stems, source_for_tags=source, bitrate=opts.bitrate)
    write_sidecar(target, data)
    if opts.sidecar_for_source and target != source:
        write_sidecar(source, data)

    summary = ", ".join(f"{s['label']}@{_mmss(s['start'])}" for s in data["sections"])
    log.info("Done in %.0fs: %.1f BPM | %s", time.time() - t0, structure.bpm, summary)
    return target


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

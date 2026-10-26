"""How well do the detected sections match what the DJ marked? (developer tool)

  python -m stemprep.evaluate [--db PATH] [--crate "stemprep checked"]

Ground truth comes from Mixxx itself: the custom build adds hot cues labelled
INTRO, BUILD, DROP, BREAKDOWN, OUTRO... at detected sections. Fix the wrong
ones in Mixxx (move, delete, add a cue and give it one of those labels), then
put the track into the crate "stemprep checked". This script reads those
cues (read-only) and compares them with the current analysis files, so a
change to structure.py can be scored right after `stemprep reanalyze`.

Scores per label (DROP, BREAKDOWN, BUILD): a marked cue is found if the
analysis has a section with that label starting within one bar of it.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

from .pipeline import read_sidecar

LABELS = ("DROP", "BREAKDOWN", "BUILD", "INTRO", "OUTRO")
HOTCUE = 1  # mixxx::CueType::HotCue


def default_db() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "Mixxx-Custom" / "mixxxdb.sqlite"


def base_label(label: str) -> str:
    """'Drop 2' / 'DROP 2' -> 'DROP'"""
    word = (label or "").strip().split(" ")[0].upper()
    return "BREAKDOWN" if word.startswith("BREAK") else word


def marked_cues(db: Path, crate: str):
    """{track location: [(seconds, LABEL)]} for tracks in the crate."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        """SELECT tl.location, l.samplerate, c.position, c.label
           FROM crates cr
           JOIN crate_tracks ct ON ct.crate_id = cr.id
           JOIN library l ON l.id = ct.track_id
           JOIN track_locations tl ON tl.id = l.location
           JOIN cues c ON c.track_id = l.id
           WHERE cr.name = ? AND c.type = ? AND c.position >= 0""",
        (crate, HOTCUE)).fetchall()
    con.close()
    result = defaultdict(list)
    for location, samplerate, position, label in rows:
        if samplerate and base_label(label) in LABELS:
            result[location].append((position / 2.0 / samplerate, base_label(label)))
    return result


def score(cues_by_track, verbose: bool = False) -> dict:
    found = defaultdict(int)
    total = defaultdict(int)
    extra = defaultdict(int)
    for location, cues in sorted(cues_by_track.items()):
        data = read_sidecar(Path(location))
        if not data:
            print(f"no analysis: {location}")
            continue
        bar = 4 * 60.0 / max(data.get("bpm") or 120.0, 1.0)
        sections = [(s["start"], base_label(s["label"])) for s in data.get("sections", [])]
        for t, label in cues:
            total[label] += 1
            hit = any(lbl == label and abs(start - t) <= bar for start, lbl in sections)
            found[label] += hit
            if verbose and not hit:
                print(f"  missed {label} at {t:6.1f}s  {Path(location).name}")
        for start, lbl in sections:
            if lbl in ("DROP", "BREAKDOWN") and not any(
                    l == lbl and abs(start - t) <= bar for t, l in cues):
                extra[lbl] += 1
                if verbose:
                    print(f"  extra  {lbl} at {start:6.1f}s  {Path(location).name}")
    report = {}
    for label in LABELS:
        if total[label]:
            report[label] = {"found": found[label], "of": total[label],
                             "recall": round(found[label] / total[label], 3),
                             "extra": extra[label]}
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stemprep-evaluate")
    p.add_argument("--db", type=Path, default=default_db())
    p.add_argument("--crate", default="stemprep checked")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    if not args.db.exists():
        print(f"Mixxx database not found: {args.db}")
        return 1
    cues = marked_cues(args.db, args.crate)
    if not cues:
        print(f'No tracks with section hot cues in the crate "{args.crate}".')
        return 1
    print(f"{len(cues)} checked track(s)")
    print(json.dumps(score(cues, args.verbose), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

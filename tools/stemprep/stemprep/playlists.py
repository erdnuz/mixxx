"""Spotify playlists that stemprep keeps in sync.

State lives in <root>/playlists.json:

  {"version": 1, "playlists": [
     {"url": ..., "id": "playlist:37i9...", "name": "130 fweak", "folder": "130 fweak",
      "added": "2026-10-25T21:00:00", "last_sync": ...,
      "tracks": [{"id": <spotify track id>, "title": ..., "artists": ...,
                  "file": "130 fweak/Artist - Title.mp3", "removed": null}]}]}

A sync reads the playlist listing, downloads only tracks we don't have yet,
and marks tracks that disappeared from the playlist as removed (their files
are kept). The caller then makes stems for the new tracks and writes an
M3U playlist (in Spotify order) that Mixxx can import.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .download import SpotifyDownloader, safe_folder_name, spotify_id

log = logging.getLogger("stemprep")

STATE_FILE = "playlists.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class PlaylistStore:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / STATE_FILE
        self.data = {"version": 1, "playlists": []}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def playlists(self) -> List[dict]:
        return self.data["playlists"]

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def find(self, key: str) -> Optional[dict]:
        """By link, Spotify id, name or folder (case-insensitive)."""
        sid = spotify_id(key)
        for p in self.playlists:
            if sid and p["id"] == sid:
                return p
            if key.lower() in (p["name"].lower(), p["folder"].lower()):
                return p
        return None

    def add(self, url: str, folder: Optional[str] = None) -> dict:
        sid = spotify_id(url)
        if not sid:
            raise ValueError(f"Not a Spotify link: {url}")
        existing = self.find(url)
        if existing:
            if folder:
                existing["folder"] = folder
            return existing
        entry = {"url": url.split("?")[0], "id": sid, "name": "", "folder": folder or "",
                 "added": _now(), "last_sync": None, "tracks": []}
        self.playlists.append(entry)
        return entry

    def remove(self, key: str) -> Optional[dict]:
        p = self.find(key)
        if p:
            self.playlists.remove(p)
        return p


@dataclass
class SyncResult:
    playlist: dict
    files: List[Path] = field(default_factory=list)  # current tracks, Spotify order
    new: List[Path] = field(default_factory=list)
    removed: List[dict] = field(default_factory=list)
    failed: int = 0


def sync_playlist(entry: dict, downloader: SpotifyDownloader, download_dir: Path) -> SyncResult:
    name, songs = downloader.fetch(entry["url"])
    entry["name"] = name
    if not entry["folder"]:
        entry["folder"] = safe_folder_name(name)
    folder = download_dir / entry["folder"]
    known = {t["id"]: t for t in entry["tracks"]}
    result = SyncResult(entry)

    # Tracks we have a file for already skip the download step entirely.
    to_download = []
    for song in songs:
        t = known.get(song.song_id)
        if t and t.get("file") and (download_dir / t["file"]).exists():
            continue
        to_download.append(song)
    got = downloader.download(to_download, folder) if to_download else {}

    first_sync = entry["last_sync"] is None
    current = []
    for song in songs:
        t = known.get(song.song_id)
        is_new = t is None and not first_sync
        if t is None:
            t = {"id": song.song_id, "title": song.name, "artists": ", ".join(song.artists),
                 "file": None, "removed": None, "added": _now()}
            known[song.song_id] = t
        t["removed"] = None
        if song.song_id in got:
            path = got[song.song_id]
            if is_new:
                result.new.append(path)
            t["file"] = path.relative_to(download_dir).as_posix()
        if t.get("file") and (download_dir / t["file"]).exists():
            result.files.append(download_dir / t["file"])
        else:
            result.failed += 1
        current.append(t)

    ids = {s.song_id for s in songs}
    gone = [t for t in entry["tracks"] if t["id"] not in ids]
    for t in gone:
        if not t.get("removed"):
            t["removed"] = _now()
            result.removed.append(t)
    # Current tracks in Spotify order, then the removed ones (kept for history)
    entry["tracks"] = current + gone
    entry["last_sync"] = _now()
    return result


def write_m3u(path: Path, files: List[Path]) -> None:
    """Extended M3U with paths relative to the playlist file."""
    lines = ["#EXTM3U"]
    for f in files:
        try:
            rel = f.relative_to(path.parent).as_posix()
        except ValueError:
            rel = str(f)
        title = f.name[:-len(".stem.mp4")] if f.name.lower().endswith(".stem.mp4") else f.stem
        lines.append(f"#EXTINF:-1,{title}")
        lines.append(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

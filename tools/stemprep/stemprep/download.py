"""Download Spotify playlists/albums/tracks with spotDL.

spotDL reads the track list from Spotify and fetches the matching audio from
YouTube Music, so quality is what YouTube serves (typically ~128-256 kbps AAC
or Opus). We keep the original codec (no re-encode) so nothing more is lost.

Your own spotDL settings in ~/.spotdl/config.json (Spotify client id/secret,
YouTube cookie file, audio providers...) are used; only the output location,
format and overwrite mode are set here.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("stemprep")

SPOTIFY_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]+/)?(playlist|album|track|artist)/([A-Za-z0-9]+)")

FILE_TEMPLATE = "{artists} - {title}.{output-ext}"


def is_spotify_url(s: str) -> bool:
    return bool(SPOTIFY_RE.match(s))


def spotify_id(url: str) -> Optional[str]:
    """'https://open.spotify.com/playlist/37i9...?si=..' -> 'playlist:37i9...'"""
    m = SPOTIFY_RE.match(url)
    return f"{m.group(1)}:{m.group(2)}" if m else None


def safe_folder_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")
    return name or "Spotify"


def _norm(s: str) -> str:
    """Loose file name comparison: case, punctuation and spacing ignored."""
    return re.sub(r"[\W_]+", "", s.lower())


class SpotifyDownloader:
    """One spotDL client for any number of playlists (spotDL only allows
    one Spotify client per process)."""

    def __init__(self, download_dir: Path, threads: int = 4):
        try:
            from spotdl import Spotdl
            from spotdl.utils.config import SPOTIFY_OPTIONS, get_config
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("spotDL is not installed (pip install spotdl)") from e

        try:
            user_cfg = get_config()
        except Exception:  # no config file yet
            user_cfg = {}

        self.download_dir = download_dir
        download_dir.mkdir(parents=True, exist_ok=True)
        spotify = {k: user_cfg.get(k, v) for k, v in SPOTIFY_OPTIONS.items()}
        settings = dict(user_cfg)
        settings.update({
            "output": str(download_dir / FILE_TEMPLATE),
            "format": "m4a",
            # keep the source as-is when it's already AAC, otherwise convert at
            # the source's own bitrate
            "bitrate": "auto",
            "overwrite": "skip",
            "threads": threads,
            "print_errors": True,
            "save_errors": str(download_dir / "spotdl-errors.txt"),
            "simple_tui": True,
            # we look for existing files ourselves (any format, see find_existing)
            "scan_for_songs": False,
            # Lyrics are scraped from three websites per track by default and
            # are no use in a DJ stem file.
            "lyrics_providers": [],
            "generate_lrc": False,
        })
        self._client = Spotdl(
            client_id=spotify["client_id"],
            client_secret=spotify["client_secret"],
            user_auth=spotify.get("user_auth", False),
            cache_path=spotify.get("cache_path"),
            no_cache=spotify.get("no_cache", False),
            headless=spotify.get("headless", False),
            use_official_api=spotify.get("use_official_api", False),
            downloader_settings=settings,
        )

    def fetch(self, url: str) -> Tuple[str, list]:
        """(list name, songs in playlist order).

        Only the playlist listing is read (Spotdl.search() would also look up
        track, album and artist of every song, ~3 requests per track, which
        is slow and runs into Spotify's rate limit). The full metadata is
        fetched in download() for the songs that are actually downloaded."""
        from spotdl.utils.search import get_simple_songs

        log.info("Looking up %s on Spotify...", url)
        songs = get_simple_songs([url])
        name = next((s.list_name for s in songs if s.list_name), None)
        if not name and songs:
            name = songs[0].album_name if "/album/" in url else songs[0].name
        return name or "Spotify", songs

    def _complete(self, songs: list) -> list:
        """Full Spotify metadata (album, genres, cover...) for the tags."""
        from concurrent.futures import ThreadPoolExecutor

        from spotdl.utils.search import reinit_song

        def one(song):
            try:
                return reinit_song(song)
            except Exception as e:  # keep the listing data; still downloadable
                log.debug("No full metadata for %s: %s", song.display_name, e)
                return song

        with ThreadPoolExecutor(max_workers=self._client.downloader.settings["threads"]) as ex:
            return list(ex.map(one, songs))  # keeps the order

    @staticmethod
    def expected_name(song) -> str:
        """File name (without extension) spotDL gives this song."""
        from spotdl.utils.formatter import create_file_name

        return create_file_name(song, FILE_TEMPLATE, "m4a").stem

    def find_existing(self, song, folder: Path) -> Optional[Path]:
        """A file for this song already in the folder, in any audio format
        (e.g. mp3s downloaded earlier with different spotDL settings)."""
        from .audio import AUDIO_EXTENSIONS

        if not folder.is_dir():
            return None
        want = _norm(self.expected_name(song))
        for p in folder.iterdir():
            if (p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
                    and not p.name.lower().endswith(".stem.mp4")
                    and _norm(p.stem) == want):
                return p
        return None

    def download(self, songs: list, folder: Path) -> Dict[str, Path]:
        """Download the songs into folder; {song_id: file} for those that
        worked. Songs that are already there aren't downloaded again."""
        folder.mkdir(parents=True, exist_ok=True)
        files: Dict[str, Path] = {}
        missing = []
        for song in songs:
            existing = self.find_existing(song, folder)
            if existing:
                files[song.song_id] = existing
            else:
                missing.append(song)
        if missing:
            log.info("Downloading %d new track(s) into %s", len(missing), folder)
            self._client.downloader.settings["output"] = str(folder / FILE_TEMPLATE)
            for song, path in self._client.download_songs(self._complete(missing)):
                if path is not None and Path(path).exists():
                    files[song.song_id] = Path(path)
            failed = len(missing) - sum(1 for s in missing if s.song_id in files)
            if failed:
                log.warning("%d track(s) could not be downloaded (see %s)", failed,
                            self.download_dir / "spotdl-errors.txt")
        return files


def download(url: str, download_dir: Path, threads: int = 4) -> List[Path]:
    """Download (or find already-downloaded) tracks; return their paths in
    playlist order."""
    downloader = SpotifyDownloader(download_dir, threads)
    name, songs = downloader.fetch(url)
    log.info("%d tracks in %s", len(songs), name)
    files = downloader.download(songs, download_dir / safe_folder_name(name))
    return [files[s.song_id] for s in songs if s.song_id in files]

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
from typing import List

log = logging.getLogger("stemprep")

SPOTIFY_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]+/)?(playlist|album|track|artist)/")


def is_spotify_url(s: str) -> bool:
    return bool(SPOTIFY_RE.match(s))


def download(url: str, download_dir: Path, threads: int = 4) -> List[Path]:
    """Download (or find already-downloaded) tracks; return their paths in
    playlist order."""
    try:
        from spotdl import Spotdl
        from spotdl.utils.config import SPOTIFY_OPTIONS, get_config
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("spotDL is not installed (pip install spotdl)") from e

    try:
        user_cfg = get_config()
    except Exception:  # no config file yet
        user_cfg = {}

    spotify = {k: user_cfg.get(k, v) for k, v in SPOTIFY_OPTIONS.items()}
    download_dir.mkdir(parents=True, exist_ok=True)
    settings = dict(user_cfg)
    settings.update({
        "output": str(download_dir / "{list-name}" / "{artists} - {title}.{output-ext}"),
        "format": "m4a",
        # keep the source as-is when it's already AAC, otherwise convert at the
        # source's own bitrate
        "bitrate": "auto",
        "overwrite": "skip",
        "threads": threads,
        "print_errors": True,
        "save_errors": str(download_dir / "spotdl-errors.txt"),
        "simple_tui": True,
    })

    client = Spotdl(
        client_id=spotify["client_id"],
        client_secret=spotify["client_secret"],
        user_auth=spotify.get("user_auth", False),
        cache_path=spotify.get("cache_path"),
        no_cache=spotify.get("no_cache", False),
        headless=spotify.get("headless", False),
        downloader_settings=settings,
    )
    log.info("Looking up %s on Spotify...", url)
    songs = client.search([url])
    log.info("%d tracks; downloading the ones you don't have yet", len(songs))
    results = client.download_songs(songs)
    paths = [Path(p) for _, p in results if p is not None and Path(p).exists()]
    failed = len(songs) - len(paths)
    if failed:
        log.warning("%d track(s) could not be downloaded (see %s)", failed,
                    download_dir / "spotdl-errors.txt")
    return paths

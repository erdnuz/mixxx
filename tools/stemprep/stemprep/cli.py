"""stemprep: Spotify playlist -> stems + bars/phrases -> Mixxx.

Examples
  stemprep https://open.spotify.com/playlist/...      download, split, analyze
  stemprep "D:\\Music\\House"                           split + analyze a folder
  stemprep song.mp3 --no-stems                         only bars/phrases sidecar
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from . import __version__

log = logging.getLogger("stemprep")


def default_root() -> Path:
    return Path(os.environ.get("STEMPREP_ROOT", Path.home() / "Music" / "stemprep"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="stemprep",
        description="Download Spotify playlists, split them into stems and find "
                    "bars, phrases and drops for Mixxx.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples", 1)[1] if __doc__ else None,
    )
    p.add_argument("inputs", nargs="+",
                   help="Spotify playlist/album/track links, audio files or folders")
    p.add_argument("--root", type=Path, default=default_root(),
                   help="Base folder (default: ~/Music/stemprep). Downloads go to "
                        "<root>/Downloads, stem files to <root>/Stems")
    p.add_argument("--out", type=Path, default=None,
                   help="Where to write stem files (default: <root>/Stems/<playlist>)")
    p.add_argument("--no-stems", action="store_true",
                   help="Skip stem separation; only analyze bars/phrases")
    p.add_argument("--download-only", action="store_true",
                   help="Only download from Spotify")
    p.add_argument("--force", action="store_true", help="Redo tracks that are already done")
    p.add_argument("--device", default="auto", help="auto, cpu or cuda")
    p.add_argument("--model", default="htdemucs",
                   help="Demucs model: htdemucs (default), htdemucs_ft (better, 4x slower)")
    p.add_argument("--bitrate", default="256k", help="AAC bitrate per stem (default 256k)")
    p.add_argument("--threads", type=int, default=4, help="Parallel spotDL downloads")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=f"stemprep {__version__}")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    from .download import download, is_spotify_url
    from .pipeline import Options, find_audio_files, process_track

    jobs = []  # (source file, stem output folder)
    for item in args.inputs:
        if is_spotify_url(item):
            files = download(item, args.root / "Downloads", threads=args.threads)
            for f in files:
                out = args.out or (args.root / "Stems" / f.parent.name)
                jobs.append((f, out))
        else:
            path = Path(item).expanduser()
            if not path.exists():
                log.error("Not found: %s", path)
                continue
            for f in find_audio_files(path):
                base = path if path.is_dir() else path.parent
                out = args.out or (args.root / "Stems" / base.name)
                jobs.append((f, out))

    if args.download_only or not jobs:
        if not jobs:
            log.warning("Nothing to process.")
        return 0

    from .ml import load_models

    separator, beat_tracker = load_models(not args.no_stems, args.device, args.model)
    opts = Options(make_stems=not args.no_stems, force=args.force, bitrate=args.bitrate)

    done, failed = [], []
    t0 = time.time()
    for i, (src, out_dir) in enumerate(jobs, 1):
        log.info("[%d/%d] %s", i, len(jobs), src.name)
        try:
            result = process_track(src, out_dir, separator, beat_tracker, opts)
            if result:
                done.append(result)
        except KeyboardInterrupt:
            log.warning("Stopped. Finished tracks are kept; run again to continue.")
            break
        except Exception as e:  # keep going with the rest of the playlist
            log.exception("Failed on %s: %s", src.name, e)
            failed.append(src)

    log.info("Finished %d track(s) in %.1f min%s.", len(done), (time.time() - t0) / 60,
             f", {len(failed)} failed" if failed else "")
    if done:
        folders = sorted({str(d.parent) for d in done})
        log.info("Add this folder to your Mixxx library (Preferences > Library):\n  %s",
                 "\n  ".join(folders))
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())

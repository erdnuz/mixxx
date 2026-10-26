"""stemprep: Spotify playlist -> stems + bars/phrases -> Mixxx.

Examples
  stemprep add https://open.spotify.com/playlist/...   track a playlist and sync it
  stemprep add <link> --folder "130 fweak"             ... into a folder you already have
  stemprep sync                                        new tracks of all tracked playlists
  stemprep list                                        tracked playlists
  stemprep remove "130 fweak"                          stop tracking (files are kept)
  stemprep https://open.spotify.com/playlist/...       one-off download, split, analyze
  stemprep "D:\\Music\\House"                           split + analyze a folder
  stemprep song.mp3 --no-stems                         only bars/phrases sidecar
  stemprep reanalyze                                   redo bars/phrases/sections of all
                                                       stem files (fast, no stems redone)
  stemprep hq                                          high quality (Demucs) stems for all
                                                       tracks that don't have them yet;
                                                       minutes per track: run overnight

Stems are "fast" (Spleeter, ~30 s per track) unless --quality hq is given.
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

COMMANDS = ("add", "sync", "list", "remove", "reanalyze", "hq", "worker")


def default_root() -> Path:
    return Path(os.environ.get("STEMPREP_ROOT", Path.home() / "Music" / "stemprep"))


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--root", type=Path, default=default_root(),
                   help="Base folder (default: ~/Music/stemprep). Downloads go to "
                        "<root>/Downloads, stem files to <root>/Stems")
    p.add_argument("-v", "--verbose", action="store_true")


def _processing(p: argparse.ArgumentParser) -> None:
    p.add_argument("--no-stems", action="store_true",
                   help="Skip stem separation; only analyze bars/phrases")
    p.add_argument("--force", action="store_true", help="Redo tracks that are already done")
    p.add_argument("--device", default="auto", help="auto, cpu or cuda")
    p.add_argument("--quality", choices=("fast", "hq"), default="fast",
                   help="fast: Spleeter stems, ~30 s per track (default); hq: Demucs, several "
                        "minutes per track (or run `stemprep hq` overnight later)")
    p.add_argument("--model", default="htdemucs",
                   help="Demucs model for hq: htdemucs (default), htdemucs_ft (better, 4x slower)")
    p.add_argument("--bitrate", default=None,
                   help="AAC bitrate per stem (default 128k fast, 256k hq)")
    p.add_argument("--threads", type=int, default=4, help="Parallel spotDL downloads")


def build_parser(command: str | None) -> argparse.ArgumentParser:
    fmt = argparse.RawDescriptionHelpFormatter
    epilog = __doc__.split("Examples", 1)[1] if __doc__ else None
    if command is None:
        p = argparse.ArgumentParser(
            prog="stemprep", formatter_class=fmt, epilog=epilog,
            description="Download Spotify playlists, split them into stems and find "
                        "bars, phrases and drops for Mixxx. Commands: " + ", ".join(COMMANDS))
        p.add_argument("inputs", nargs="+",
                       help="Spotify playlist/album/track links, audio files or folders")
        p.add_argument("--out", type=Path, default=None,
                       help="Where to write stem files (default: <root>/Stems/<playlist>)")
        p.add_argument("--download-only", action="store_true", help="Only download from Spotify")
        p.add_argument("--version", action="version", version=f"stemprep {__version__}")
        _processing(p)
    else:
        p = argparse.ArgumentParser(prog=f"stemprep {command}", formatter_class=fmt)
        if command == "add":
            p.add_argument("urls", nargs="+", help="Spotify playlist or album links")
            p.add_argument("--folder", help="Folder name under Downloads (default: the "
                                            "playlist name). Use it to adopt a folder you "
                                            "already have.")
            p.add_argument("--no-sync", action="store_true", help="Only remember the playlist")
        elif command == "sync":
            p.add_argument("playlists", nargs="*",
                           help="Names or links to sync (default: all tracked playlists)")
            p.add_argument("--download-only", action="store_true",
                           help="Only download; make stems later")
        elif command == "remove":
            p.add_argument("playlists", nargs="+", help="Names or links")
        elif command == "reanalyze":
            p.add_argument("paths", nargs="*", type=Path,
                           help="Stem files or folders (default: <root>/Stems)")
        elif command == "hq":
            p.description = ("High quality (Demucs) stems for every track that doesn't have "
                             "them yet. Several minutes per track: run it overnight. Stop "
                             "any time; it continues where it stopped.")
            p.add_argument("paths", nargs="*", type=Path,
                           help="Folders or files (default: <root>/Downloads)")
            p.add_argument("--device", default="auto", help="auto, cpu or cuda")
            p.add_argument("--model", default="htdemucs",
                           help="htdemucs (default), htdemucs_ft (better, 4x slower)")
            p.add_argument("--bitrate", default=None, help="AAC bitrate per stem (default 256k)")
        elif command == "worker":
            p.description = "Background worker for tracks Mixxx asks for (started by Mixxx)."
            p.add_argument("--device", default="auto", help="auto, cpu or cuda")
        if command in ("add", "sync"):
            _processing(p)
    _common(p)
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv and argv[0] in COMMANDS else None
    args = build_parser(command).parse_args(argv[1:] if command else argv)

    if command == "worker":
        from . import worker

        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                            format="%(asctime)s  %(message)s", datefmt="%H:%M:%S",
                            stream=sys.stderr or open(os.devnull, "w"))
        return worker.main(args.root, args.device)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    if command in ("add", "sync"):
        return cmd_sync(args, command)
    if command == "list":
        return cmd_list(args)
    if command == "remove":
        return cmd_remove(args)
    if command == "reanalyze":
        return cmd_reanalyze(args)
    if command == "hq":
        return cmd_hq(args)
    return cmd_process(args)


def cmd_process(args) -> int:
    from .download import download, is_spotify_url
    from .pipeline import find_audio_files

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
            base = path if path.is_dir() else path.parent
            for f in find_audio_files(path):
                # Folder of playlist folders: keep one stem folder per playlist
                out = args.out or (args.root / "Stems" / f.parent.name
                                   if f.parent != base else args.root / "Stems" / base.name)
                jobs.append((f, out))

    if args.download_only or not jobs:
        if not jobs:
            log.warning("Nothing to process.")
        return 0
    done, failed = run_jobs(jobs, args)
    return 1 if failed and not done else 0


def cmd_hq(args) -> int:
    from .pipeline import find_audio_files
    from .worker import lower_priority

    lower_priority()  # the PC stays usable while it runs
    jobs = []
    for path in args.paths or [args.root / "Downloads"]:
        if not path.exists():
            log.error("Not found: %s", path)
            continue
        for f in find_audio_files(path):
            if not f.name.lower().endswith(".stem.mp4"):
                jobs.append((f, args.root / "Stems" / f.parent.name))
    args.quality, args.no_stems, args.force = "hq", False, False
    done, failed = run_jobs(jobs, args)
    return 1 if failed and not done else 0


def run_jobs(jobs, args):
    """Two passes: first bars/phrases/sections for every track from the mix
    (seconds per track, so new tracks are usable quickly), then stems for
    those that need them (args.quality: Spleeter or Demucs). Models are only
    loaded if there is work. Returns (done, failed)."""
    from .pipeline import Options, analyze_track, has_stems, is_done, make_stems

    from .worker import FAST_BITRATE

    bitrate = args.bitrate or (FAST_BITRATE if args.quality == "fast" else "256k")
    opts = Options(make_stems=not args.no_stems, force=args.force, bitrate=bitrate,
                   stems_quality=args.quality)
    todo = [(src, out) for src, out in jobs if opts.force or not is_done(src, out, opts)]
    if len(todo) < len(jobs):
        log.info("%d track(s) already done", len(jobs) - len(todo))
    if not todo:
        return [], []

    from .ml import BeatTracker, make_separator
    from .worker import FAST_MODEL

    beat_tracker = BeatTracker(device=args.device)
    stem_jobs = [(src, out) for src, out in todo
                 if opts.make_stems and not src.name.lower().endswith(".stem.mp4")
                 and (opts.force or not has_stems(src, out, opts.stems_quality))]
    done, failed = [], []

    def attempt(label, fn, src):
        try:
            return fn()
        except KeyboardInterrupt:
            raise
        except Exception as e:  # keep going with the rest of the playlist
            log.exception("%s failed on %s: %s", label, src.name, e)
            failed.append(src)
            return None

    t0 = time.time()
    try:
        for i, (src, _) in enumerate(todo, 1):
            log.info("[analyze %d/%d] %s", i, len(todo), src.name)
            if attempt("Analysis", lambda: analyze_track(src, beat_tracker, opts), src) \
                    and not stem_jobs:
                done.append(src)
        if stem_jobs:
            separator = make_separator(
                FAST_MODEL if opts.stems_quality == "fast" else args.model, args.device)
            for i, (src, out_dir) in enumerate(stem_jobs, 1):
                log.info("[stems %d/%d] %s", i, len(stem_jobs), src.name)
                result = attempt("Stems", lambda: make_stems(src, out_dir, separator,
                                                             beat_tracker, opts), src)
                if result:
                    done.append(result)
    except KeyboardInterrupt:
        log.warning("Stopped. Finished tracks are kept; run again to continue.")

    log.info("Finished %d track(s) in %.1f min%s.", len(done), (time.time() - t0) / 60,
             f", {len(failed)} failed" if failed else "")
    return done, failed


def cmd_sync(args, command) -> int:
    from .download import SpotifyDownloader
    from .playlists import PlaylistStore, sync_playlist, write_m3u

    store = PlaylistStore(args.root)
    if command == "add":
        entries = [store.add(url, args.folder) for url in args.urls]
        store.save()
        for e in entries:
            log.info("Tracking %s", e["url"])
        if args.no_sync:
            return 0
        args.download_only = False
    else:
        if args.playlists:
            entries = []
            for key in args.playlists:
                e = store.find(key)
                if e is None:
                    log.error("Not tracked: %s (see 'stemprep list')", key)
                    return 1
                entries.append(e)
        else:
            entries = list(store.playlists)
        if not entries:
            log.warning("No playlists tracked yet. Add one: stemprep add <Spotify link>")
            return 0

    downloads = args.root / "Downloads"
    downloader = SpotifyDownloader(downloads, threads=args.threads)
    results = []
    for e in entries:
        try:
            r = sync_playlist(e, downloader, downloads)
        except Exception as ex:  # one broken playlist shouldn't stop the others
            log.exception("Could not sync %s: %s", e.get("name") or e["url"], ex)
            continue
        store.save()
        results.append(r)
        log.info("%s: %d tracks, %d new, %d removed%s", e["name"], len(r.files), len(r.new),
                 len(r.removed), f", {r.failed} not downloaded" if r.failed else "")
        for t in r.removed:
            log.info("  removed on Spotify (file kept): %s - %s", t["artists"], t["title"])

    if not args.download_only:
        jobs = [(f, args.root / "Stems" / r.playlist["folder"]) for r in results for f in r.files]
        run_jobs(jobs, args)

    # A Mixxx-importable playlist per Spotify playlist, in Spotify order. It
    # lists the downloaded tracks (those are in the library); Mixxx plays them
    # with their stems by itself.
    for r in results:
        if r.files:
            m3u = downloads / r.playlist["folder"] / (r.playlist["folder"] + ".m3u8")
            write_m3u(m3u, r.files)
            log.info("Playlist for Mixxx: %s", m3u)
    return 0


def cmd_list(args) -> int:
    from .playlists import PlaylistStore

    store = PlaylistStore(args.root)
    if not store.playlists:
        print("No playlists tracked yet. Add one: stemprep add <Spotify link>")
        return 0
    for p in store.playlists:
        active = [t for t in p["tracks"] if not t.get("removed")]
        removed = len(p["tracks"]) - len(active)
        print(f"{p['name'] or '(not synced yet)'}  [{p['folder'] or '-'}]")
        print(f"    {p['url']}")
        print(f"    {len(active)} tracks" + (f", {removed} removed" if removed else "")
              + f", last sync {p['last_sync'] or 'never'}")
    return 0


def cmd_remove(args) -> int:
    from .playlists import PlaylistStore

    store = PlaylistStore(args.root)
    status = 0
    for key in args.playlists:
        p = store.remove(key)
        if p:
            log.info("No longer tracking %s (files kept in %s)", p["name"], p["folder"])
        else:
            log.error("Not tracked: %s", key)
            status = 1
    store.save()
    return status


def cmd_reanalyze(args) -> int:
    from .pipeline import reanalyze

    paths = args.paths or [args.root / "Downloads", args.root / "Stems"]
    targets = []
    for p in paths:
        if p.is_dir():
            # Every file with cached features: sources (analysis from the
            # mix) and stem files (analysis from stems)
            suffix = ".features.npz"
            targets += sorted(f.parent.parent / f.name[:-len(suffix)]
                              for f in p.rglob("*" + suffix) if f.parent.name == ".stemprep")
        elif p.exists():
            targets.append(p)
    # Sources first: a stem file's analysis then overrides the mix one
    targets.sort(key=lambda t: t.name.lower().endswith(".stem.mp4"))
    n = sum(1 for t in targets if t.exists() and reanalyze(t))
    log.info("Re-analyzed %d file(s).", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())

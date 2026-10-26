"""Background worker for tracks Mixxx asks for (`stemprep worker`).

Mixxx writes one small JSON file per track into <data dir>/queue when a track
is loaded into a deck (src/mixer/stemprepqueue.cpp) and starts this worker if
<data dir>/worker.lock hasn't been refreshed for a minute.

Per track, in steps, highest priority first (a newly loaded track can get
ahead of others between steps):
1. bars/phrases/sections from the mix (seconds), so the waveform shows them
2. fast stems (Spleeter, ~30 s), so mute/solo work shortly after loading

High quality Demucs stems take minutes per track and are made separately,
e.g. overnight, with `stemprep hq`; Mixxx then uses them instead.

Mixxx swaps new stems into a deck by itself (PhraseControl). The worker runs
at below-normal priority and exits after a while without work.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("stemprep")

LOCK_REFRESH_S = 10
IDLE_EXIT_S = 15 * 60
FAST_MODEL = "spleeter4"
# Fast stems are temporary (replaced by `stemprep hq`); AAC at 128k encodes
# ~1.5x faster than 256k
FAST_BITRATE = "128k"
MAX_ATTEMPTS = 2


def data_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "stemprep"
    return Path.home() / ".local" / "share" / "stemprep"


@dataclass
class Request:
    file: Path  # the queue file
    path: Path  # the track
    priority: int
    requested: str
    attempts: int


def read_queue(queue: Path) -> List[Request]:
    requests = []
    for f in queue.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            requests.append(Request(f, Path(d["path"]), int(d.get("priority", 5)),
                                    str(d.get("requested", "")), int(d.get("attempts", 0))))
        except (OSError, ValueError, KeyError) as e:
            log.warning("Ignoring bad request %s: %s", f.name, e)
            f.unlink(missing_ok=True)
    return sorted(requests, key=lambda r: (r.priority, r.requested))


def lower_priority() -> None:
    try:
        if os.name == "nt":
            import ctypes

            below_normal = 0x00004000
            kernel32 = ctypes.windll.kernel32
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), below_normal)
        else:
            os.nice(10)
    except Exception as e:  # not fatal
        log.debug("Could not lower priority: %s", e)


class Lock:
    """<data dir>/worker.lock, refreshed every few seconds while running, so
    Mixxx (and a second worker) can see this one is alive."""

    def __init__(self, path: Path):
        self.path = path
        self._stop = threading.Event()

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and time.time() - self.path.stat().st_mtime < 3 * LOCK_REFRESH_S:
            return False
        self.path.write_text(str(os.getpid()), encoding="utf-8")
        threading.Thread(target=self._refresh, daemon=True).start()
        return True

    def _refresh(self) -> None:
        while not self._stop.wait(LOCK_REFRESH_S):
            try:
                os.utime(self.path)
            except OSError:
                pass

    def release(self) -> None:
        self._stop.set()
        self.path.unlink(missing_ok=True)


class Worker:
    def __init__(self, root: Path, device: str = "auto"):
        self.root = root
        self.device = device
        self._beats = None
        self._separators = {}

    def beats(self):
        if self._beats is None:
            from .ml import BeatTracker

            self._beats = BeatTracker(device=self.device)
        return self._beats

    def separator(self, model: str):
        if model not in self._separators:
            from .ml import make_separator

            self._separators[model] = make_separator(model, self.device)
        return self._separators[model]

    def stems_dir(self, track: Path) -> Path:
        return self.root / "Stems" / track.parent.name

    def step(self, req: Request) -> Optional[bool]:
        """One step for this track. True: more to do later, False: finished,
        None: nothing possible right now."""
        from .pipeline import Options, analyze_track, has_stems, is_analyzed, make_stems

        track = req.path
        if not track.exists():
            log.info("Gone: %s", track)
            return False
        out = self.stems_dir(track)
        if not is_analyzed(track):
            log.info("Analyzing %s", track.name)
            analyze_track(track, self.beats(), Options())
            return True
        if not has_stems(track, out, "fast"):
            log.info("Fast stems for %s", track.name)
            make_stems(track, out, self.separator(FAST_MODEL), self.beats(),
                       Options(stems_quality="fast", bitrate=FAST_BITRATE))
        return False

    def run(self) -> int:
        queue = data_dir() / "queue"
        queue.mkdir(parents=True, exist_ok=True)
        idle_since = time.time()
        while True:
            pending = read_queue(queue)
            progressed = False
            for req in pending:
                try:
                    result = self.step(req)
                except Exception as e:
                    log.exception("Failed on %s: %s", req.path.name, e)
                    result = self._retry_later(req)
                if result is None:
                    continue  # try the next track
                if result is False:
                    req.file.unlink(missing_ok=True)
                progressed = True
                break  # re-read the queue: a new deck load may come first
            if progressed:
                idle_since = time.time()
                continue
            if time.time() - idle_since > IDLE_EXIT_S:
                log.info("Nothing to do; exiting.")
                return 0
            time.sleep(5)

    def _retry_later(self, req: Request) -> bool:
        if req.attempts + 1 >= MAX_ATTEMPTS:
            failed = req.file.parent.parent / "failed"
            failed.mkdir(exist_ok=True)
            req.file.replace(failed / req.file.name)
            return True  # handled (moved away)
        data = json.loads(req.file.read_text(encoding="utf-8"))
        data["attempts"] = req.attempts + 1
        data["priority"] = req.priority + 10  # others first
        req.file.write_text(json.dumps(data), encoding="utf-8")
        return True


def main(root: Path, device: str = "auto") -> int:
    # Started by Mixxx through pythonw.exe (no console window): there is no
    # stdout/stderr, and progress bars or log output would fail.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    lock = Lock(data_dir() / "worker.lock")
    if not lock.acquire():
        log.info("A worker is already running.")
        return 0
    # Log to a file: Mixxx starts the worker without a console
    handler = logging.FileHandler(data_dir() / "worker.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S"))
    logging.getLogger().addHandler(handler)
    lower_priority()
    log.info("Worker started (pid %d)", os.getpid())
    try:
        return Worker(root, device).run()
    except KeyboardInterrupt:
        return 0
    finally:
        lock.release()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    sys.exit(main(Path.home() / "Music" / "stemprep"))

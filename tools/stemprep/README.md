# stemprep

Spotify playlist → stems → bars, phrases and drops → ready to mix in the
custom Mixxx build.

```
stemprep https://open.spotify.com/playlist/...   # download, split, analyze
stemprep "D:\Music\House"                         # split + analyze a folder
stemprep song.mp3 --no-stems                      # only bars/phrases
```

For every track it writes:

- `Stems/<playlist>/<Artist - Title>.stem.mp4`: a Native Instruments style
  stem file (mix + Drums, Bass, Melody, Vocals) that Mixxx 2.6+ and Traktor
  can play.
- `<file>.structure.json` next to it (and next to the source file): beats,
  real downbeats, 8-bar phrases and sections (Intro, Build, Drop, Breakdown,
  Outro…) with suggested hot cues. The custom Mixxx build reads this file.

## How it works

1. **spotDL** reads the playlist from Spotify and fetches the matching audio
   from YouTube Music (kept as-is, no extra re-encode). Your
   `~/.spotdl/config.json` settings are used.
2. **Demucs** (`htdemucs`) separates drums, bass, other and vocals.
3. **Beat This!** finds beats and downbeats.
4. `structure.py` measures each bar (kick, bass, drums, melody, vocals,
   brightness, busyness), finds the 8-bar phrase grid from where the music
   changes most, and labels 4-bar blocks by energy: kick + bass in = drop,
   kick out = breakdown, rising energy / snare rolls before a drop = build.

On a CPU (no NVIDIA GPU) separation takes roughly 1–3 minutes per track.
Tracks that are already done are skipped, so you can stop and re-run.

## Install (Windows)

Double-click `windows/Install Stemprep.bat`. It creates its own Python
environment in `%LOCALAPPDATA%\stemprep`, installs PyTorch (CUDA if an NVIDIA
GPU is present), Demucs, Beat This! and spotDL, downloads the models and puts
a **Stemprep** shortcut on the Desktop. Paste a Spotify link into it, or drag
files/folders onto it.

## Tests

```
python tests/test_structure.py   # numpy only
python tests/test_stemfile.py    # needs ffmpeg
python tests/test_pipeline.py    # needs ffmpeg
```

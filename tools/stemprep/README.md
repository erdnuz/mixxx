# stemprep

Spotify playlist → stems → bars, phrases and drops → ready to mix in the
custom Mixxx build.

```
stemprep add https://open.spotify.com/playlist/...  # track a playlist and sync it
stemprep add <link> --folder "130 fweak"            # ... into a folder you already have
stemprep sync                                       # new tracks of all tracked playlists
stemprep list                                       # tracked playlists
stemprep remove "130 fweak"                         # stop tracking (files are kept)

stemprep https://open.spotify.com/playlist/...      # one-off: download, split, analyze
stemprep "D:\Music\House"                            # split + analyze a folder
stemprep song.mp3 --no-stems                        # only bars/phrases
stemprep reanalyze                                  # redo bars/phrases/sections (fast)
stemprep hq                                         # Demucs stems for everything (overnight)
```

## With the custom Mixxx build

Add `Music/stemprep/Downloads` to the Mixxx library, **not** `Stems` (Mixxx
would import the stem files as separate tracks). When you load a track,
Mixxx asks stemprep (`stemprep worker`, started in the background) for:

1. bars, phrases and sections from the track itself: on the waveform after
   ~8 s;
2. fast stems (Spleeter): ~1 minute; Mixxx switches the deck to them when
   it's stopped, keeping position, tempo and pitch.

High quality stems (Demucs, ~6 minutes per track on a laptop CPU) are made
only when you run `stemprep hq` (Desktop menu, option 7), e.g. overnight.
Mixxx uses them the next time the track is loaded.

For every track it writes:

- `Stems/<playlist>/<Artist - Title>.stem.mp4`: a Native Instruments style
  stem file (mix + Drums, Bass, Melody, Vocals) that Mixxx 2.6+ and Traktor
  can play.
- `<file>.structure.json` next to it (and next to the source file): beats,
  real downbeats, 8-bar phrases and sections (Intro, Build, Drop, Breakdown,
  Outro…) with suggested hot cues. The custom Mixxx build reads this file.
- `Stems/<playlist>/.stemprep/<file>.features.npz`: the measured loudness
  features, so `stemprep reanalyze` can redo the phrase/section detection
  after an update in seconds, without running the neural networks again.
  Mixxx's note that it already added the hot cues is kept.

## Tracked playlists

`stemprep add` remembers playlists in `<root>/playlists.json` (default root:
`~/Music/stemprep`). `stemprep sync` then:

1. reads the playlist from Spotify (just the track list: tracks you already
   have cost no further Spotify requests),
2. downloads only the new tracks into `Downloads/<folder>`. A file that is
   already there in any format counts (e.g. mp3s from an earlier spotDL run),
3. makes stems and analysis for them,
4. writes `Downloads/<folder>/<folder>.m3u8` in Spotify order. In Mixxx:
   Playlists → right-click → Import Playlist.

Tracks removed from the Spotify playlist are listed but their files are
kept. The Desktop shortcut has a menu for all of this.

## How it works

1. **spotDL** reads the playlist from Spotify and fetches the matching audio
   from YouTube Music (kept as-is, no extra re-encode). Your
   `~/.spotdl/config.json` settings are used, except that lyrics aren't
   fetched (they aren't needed in a DJ stem file and cost three website
   lookups per track).
2. **Demucs** (`htdemucs`) separates drums, bass, other and vocals.
3. **Beat This!** finds beats and downbeats.
4. `structure.py` measures each bar (kick, bass, drums, melody, vocals,
   brightness, busyness), finds the 8-bar phrase grid from where the music
   changes most, and labels 4-bar blocks by energy: kick + bass in = drop,
   kick out = breakdown, rising energy / snare rolls before a drop = build.
5. The five streams are AAC-encoded in parallel and put into one MP4.

Measured on an i5-8350U laptop on battery, per 3.8-minute track: sections
~8 s, Spleeter stems ~61 s, Demucs stems ~6.2 min. Tracks that are already
done are skipped, so you can stop and re-run.

## Install (Windows)

Double-click `windows/Install Stemprep.bat`. It creates its own Python
environment in `%LOCALAPPDATA%\stemprep`, installs PyTorch (CUDA if an NVIDIA
GPU is present), Demucs, Beat This! and spotDL, downloads the models and puts
a **Stemprep** shortcut on the Desktop.

## Tests

```
python tests/test_structure.py   # numpy only
python tests/test_playlists.py   # no network needed
python tests/test_evaluate.py    # numpy only
python tests/test_stemfile.py    # needs ffmpeg
python tests/test_pipeline.py    # needs ffmpeg
python tests/test_worker.py      # needs ffmpeg
```

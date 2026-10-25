# Custom Mixxx for erdnuz — handoff notes

This fork (`erdnuz/mixxx`, branch **`custom-dj`**, based on upstream **2.6** beta)
adds stems + bar/phrase/section awareness for a Pioneer **DDJ-SB2** on
**Windows** (Intel UHD 620, no NVIDIA GPU). The user's stock Mixxx 2.5.6 stays
installed; this build runs side by side from a portable zip.

## How builds work (no local compiler needed)

- `.github/workflows/custom-build.yml` runs on every push to `custom-*`:
  - **Linux compile + tests** (fast feedback; runs `TrackStructure*`, beat
    tests, all MIDI mapping validation tests, and the stemprep structure test)
  - **Windows x64 portable zip** → artifact `Mixxx-Custom-win64` with
    `Mixxx Custom.bat` (uses `--settings-path %LOCALAPPDATA%\Mixxx-Custom`)
- Upstream `develop.yml` was made manual-only so pushes don't run the full
  matrix. Don't push to a branch named like `2.6` (triggers `release.yml`).
- Check runs: `gh run list -R erdnuz/mixxx`, logs: `gh run view <id> --log-failed`.
- Upstream remote: `git remote add upstream https://github.com/mixxxdj/mixxx`.

## What's implemented

### tools/stemprep (Python, runs on the user's PC)
Spotify link / folder → spotDL download (m4a, no re-encode) → Demucs
`htdemucs` stems → NI-style `.stem.mp4` (stream 0 = mix, 1–4 = drums, bass,
melody, vocals; manifest in `moov/udta/stem`) → Beat This! beats + downbeats
→ phrase/section detection → `<file>.structure.json` sidecar next to the stem
file (and next to the source file).
- `structure.py` is numpy-only and unit tested on synthetic EDM
  (`tests/test_structure.py`). Sections: Intro, Build, Drop, Breakdown,
  Groove, Outro (or Verse/Hook for low-contrast music). Phrase grid = 8 bars,
  origin chosen where the music changes most.
- Windows install: `windows/Install Stemprep.bat` → venv in
  `%LOCALAPPDATA%\stemprep\venv`, CPU torch, Desktop shortcut "Stemprep".
- Output: `~/Music/stemprep/Downloads/<playlist>/`, `~/Music/stemprep/Stems/<playlist>/`.

### Mixxx (C++)
- `src/track/trackstructure.{h,cpp}`: parses the sidecar, `alignTo(beats)`
  snaps downbeats (bar phase by majority vote), phrases and sections to the
  track's **own beat grid** (robust to decoder offsets and grid edits;
  handles double/half-tempo grids). Cached per BeatsPointer.
- `Track::getStructure()/reloadStructure()`, signal `structureUpdated()`
  (not stored in the DB).
- `src/mixer/phrasecontrol.{h,cpp}` (owned by BaseTrackPlayerImpl): controls
  `phrase_jump_forward/backward`, `section_jump_forward/backward` (beat-exact
  via `beatjump`, keeps position in bar), `beats_until_phrase`,
  `section_index`, `structure_loaded`, `structure_reload`; one-time auto hot
  cues at Build/Drop/Breakdown etc. (`[Structure] AutoHotcues`, marks
  `mixxx_cues_applied` in the sidecar).
- Waveform: `allshader/waveformrenderbeat.cpp` now uses RGBAMaterial: faint
  beats, 2px bar lines, 3px colored phrase/section lines, section strip at the
  bottom. Optional skin attributes `<BarColor>`, `<PhraseColor>`.
  (Legacy QPainter renderer not changed yet.)
- Overview (`widget/woverview.cpp`): section strip with labels.
- Tests: `src/test/trackstructuretest.cpp`.

### DDJ-SB2 mapping
New files `res/controllers/Pioneer-DDJ-SB2-Stems.midi.xml` +
`Pioneer-DDJ-SB2-Stems-scripts.js` (originals untouched):
- SHIFT+PLAY = `engine.brake` / `engine.softStart`
- CUE LOOP pads: stem mute (lit = playing), SHIFT = solo; falls back to EQ
  kills when no stems
- BANK pads: section/phrase jumps; pad 4 blinks in the bar before a phrase
- Options at top of the script. Smoke-tested with a stub engine in node.

## Ideas / next steps (from the user's wishes)
- Make the brake also available as a deck control so the skin can use it.
- Legacy (non-GL) waveform renderer: bar/phrase lines.
- Section labels drawn on the scrolling waveform (currently only colors;
  labels are on the overview and as hot cue labels).
- Optional: run stemprep analysis from inside Mixxx (context menu → run tool).
- Tune `structure.py` on real tracks (thresholds in `_classify_blocks`,
  `detect_sections`).

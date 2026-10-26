# Custom Mixxx for erdnuz — handoff notes

This fork (`erdnuz/mixxx`, branch **`custom-dj`**, based on upstream **2.6** beta)
adds stems + bar/phrase/section awareness for a Pioneer **DDJ-SB2** on
**Windows** (i5-8350U, Intel UHD 620, no NVIDIA GPU). The user uninstalled
stock Mixxx 2.5.6; this build (portable zip) is their only Mixxx. No C++
compiler on the PC: C++ changes are only verified by the CI build.

User's music: `~/Music/stemprep/Downloads/<playlist>/` (496 spotDL mp3s in 11
playlist folders like "130 fweak", avg 3.8 min). Stemprep is installed in
`%LOCALAPPDATA%\stemprep\venv` as an **editable** install of this checkout's
`tools/stemprep`, so code changes apply immediately.

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

## How stems reach a deck (two tiers; user's decision)

1. Track loaded in Mixxx → `src/mixer/stemprepqueue.cpp` writes a request to
   `%LOCALAPPDATA%\stemprep\queue` and starts `pythonw -m stemprep worker`
   (no console). The worker (`stemprep/worker.py`) does, per track:
   analysis from the mix (`pipeline.analyze_track`, sidecar `"tier": "mix"`,
   ~8 s) then **Spleeter** fast stems (`make_stems`, quality "fast", AAC
   128k, `Stems/<pl>/fast/`, ~1 min on battery). It never runs Demucs.
2. **Demucs** only via `stemprep hq` (Desktop menu 7), run overnight by the
   user; hq files go to `Stems/<pl>/`, the fast file is deleted, sidecar
   relinked.
3. Mixxx plays the *library track* (the Downloads mp3) with stems from the
   file named in its sidecar (`"stems"`), via
   `SoundSourceProxy::openAudioSourceForDecoding()` (playback + analyzer
   only; tags/cover still from the mp3). Gate in
   `TrackStructure::stemCacheFor()`: file exists, `source_size` matches,
   |`stems_offset_ms`| ≤ 5, `stems_sample_rate` == track rate (stem files are
   written at the source's own rate). Falls back to the mp3 if it can't open.
4. PhraseControl watches the track's folder; when the sidecar changes it
   reloads the structure and, if new stems arrived, emits
   `reloadForNewStems` → BaseTrackPlayerImpl reloads the same track keeping
   position, rate, pitch_adjust and stem volume/mute (deck must be stopped;
   if playing it waits for play=0; skipped while AutoDJ is on;
   `[Structure] AutoReloadStems`). Auto hot cues only from `"tier": "stems"`.
   Control `stems_ready_on_reload`.
- Stems folder must NOT be a Mixxx library folder (scanner would import the
  .stem.mp4 files as tracks). The library holds `Downloads/`.

Measured (i5-8350U, on battery, report in `~/Music/stemprep/Listening test/`):
sections 8 s after load; Spleeter stems ~31 s + stem file 15 s ≈ 61 s total;
Demucs ~6.2 min/track. Spleeter vs Demucs SDR: drums 9.8, bass 8.1, melody
2.8, vocals 1.1 dB. Open-Unmix was slower/worse; Beat This! `small0`
disagrees on downbeats; DirectML on the UHD 620 is no faster than CPU.
Beats: `ml.beats_from_excerpts` (3×20 s, constant-tempo fit, gap counting)
4–6 s on steady tracks; falls back to whole-track tracking (~20–30 s) when
the tempo isn't steady (3 of 6 test tracks: full/half-tempo flips in UKG).
Dev tools: `python -m stemprep.bench`, `python -m stemprep.evaluate`
(scores sections against the user's corrected hot cues in the crate
"stemprep checked").

## What's implemented

### tools/stemprep (Python, runs on the user's PC)
Spotify link / folder → spotDL download (m4a, no re-encode) → Demucs
`htdemucs` stems → NI-style `.stem.mp4` (stream 0 = mix, 1–4 = drums, bass,
melody, vocals; manifest in `moov/udta/stem`) → Beat This! beats + downbeats
→ phrase/section detection → `<file>.structure.json` sidecar next to the stem
file (and next to the source file).
- Tracked playlists (`playlists.py`, state in `<root>/playlists.json`):
  `stemprep add|sync|list|remove`. Sync reads only the playlist listing
  (`get_simple_songs`), full spotDL metadata (`reinit_song`) only for tracks
  being downloaded; lyrics fetching is off. Existing files in any format are
  adopted by name. Removed tracks are reported, files kept. Writes
  `Downloads/<folder>/<folder>.m3u8` (the library tracks) for import into Mixxx.
- Frame features are cached in `Stems/<playlist>/.stemprep/*.features.npz`;
  `stemprep reanalyze` reruns structure detection from them in seconds and
  keeps `mixxx_cues_applied`. `structure.frame_features()` (slow, audio) vs
  `bars_from_frames()` (fast, per bar grid).
- Stem file: the five AAC streams are encoded by parallel ffmpeg processes
  (ffmpeg 4.4 from spotDL is single-threaded per file), then muxed with
  `-c copy`: 71 s → 18 s per 5-min track.
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
- `src/mixer/barcontrol.{h,cpp}` (owned by BaseTrackPlayerImpl): bar-aware
  performance controls: read-only `beat_in_bar`, `beats_until_bar`,
  `bar_in_phrase`; `phrase_sync` (beatjump so the phrase position matches the
  reference deck = sync leader / other playing deck with structure; compares
  phrase fractions so double-tempo grids work), `play_on_phrase` (arm; starts
  on the reference's next phrase), `stem_mask_on_bar` (bitmask of audible
  stems applied to `[ChannelN_StemM],mute` at the next downbeat; resets itself
  to −1; `stem_mask_pending`), `bar_loop` (N bars from the downbeat, exact grid
  positions; same N ends it), `phrase_loop`, `phrase_restart`. Timing: GUI
  `Qt::PreciseTimer`, fires early by `[App],output_latency_ms`, re-checks on
  firing. Math helpers on `TrackStructure::Alignment` (`beatInBar`,
  `phraseStartAtOrBefore`, `positionInPhrase`, `nextPhraseStart`, `syncDelta`,
  `phraseBeats`) are unit tested.
- `src/mixer/brakecontrol.{h,cpp}` (owned by BaseTrackPlayerImpl): `brake`
  (press: brake playing deck / spin up stopped or braking deck),
  `brake_active`, `brake_time` (2 s), `softstart_time` (0.8 s), persisted.
  Drives scratch2 with a cosine ease from elapsed time (5 ms PreciseTimer).
  Test: `src/test/brakecontroltest.cpp`. LateNight has a BRAKE button in
  `decks/row_5_transportLoopJump.xml` (not in the compact variant).
- Waveform: `allshader/waveformrenderbeat.cpp` now uses RGBAMaterial: faint
  beats, 2px bar lines, 3px colored phrase/section lines, section strip at the
  bottom, section names above the strip (pool of 6 TextureMaterial child
  nodes created in the constructor, hidden with 0 vertices; the current
  section's name sticks to the left edge). Optional skin attributes
  `<BarColor>`, `<PhraseColor>`. The legacy QPainter renderer
  (`waveform/renderers/waveformrenderbeat.cpp`) draws bar/phrase lines too,
  but no strip or names.
- Overview (`widget/woverview.cpp`): section strip with labels.
- Tests: `src/test/trackstructuretest.cpp`.

### DDJ-SB2 mapping
New files `res/controllers/Pioneer-DDJ-SB2-Stems.midi.xml` +
`Pioneer-DDJ-SB2-Stems-scripts.js` (originals untouched):
- SHIFT+PLAY = the deck's `brake` control (shared with the skin button);
  options `brakeSeconds` / `softStartSeconds` (null = deck setting); PLAY
  blinks while `brake_active`
- SYNC tap on a stopped deck → also `phrase_sync` (`syncAlignsPhrases`);
  SHIFT+SYNC LED (0x5C) = quantize. Note: components.SyncButton replaces its
  `input` in unshift()/shift(), so overrides must wrap inside `unshift`.
- CUE LOOP pads: stem mute on release (hold + FILTER = that stem's
  `[QuickEffectRack1_[ChannelN_StemM]],super1`), SHIFT = solo; both via
  `stem_mask_on_bar` (`stemsOnBar`); pending pads blink. Releases are matched
  by pad because the SB2 sends them on whichever layer SHIFT is in.
- MANUAL LOOP (0x20) = bar loops 1/2/4/8; SHIFT (0x28–0x2B) = slicer (slip +
  beatjump to beat N, LED = current beat); `performancePads` off = classic.
- BANK pads: section/phrase jumps, LEDs count down the last 4 bars; SHIFT+BANK
  (0x78) = phrase_sync / play_on_phrase / phrase_restart / phrase_loop.
- SHIFT+TEMPO (0x05/0x25) = key in semitones (`keyFader`, own pick-up,
  follows `rate_dir`); SHIFT+KEYLOCK glides `rate` to 0 + `pitch_adjust` 0.
- SHIFT+FX buttons (0x63–0x65) route the unit to [Channel1]/[Headphone]/
  [Channel2]; SHIFT+FX knob (0x00/0x20) = unit `super1`.
- XML rebinding was scripted (by status/midino); `node
  tools/sb2-mapping-test/test.js` loads the real mapping with a stand-in
  engine, checks every XML handler exists and 16 behaviours (runs in CI).
- Options at top of the script.

## Ideas / next steps (from the user's wishes)
- Tune `structure.py` on real tracks (thresholds in `_classify_blocks`,
  `detect_sections`): user corrects auto hot cues in Mixxx, puts tracks in the
  crate "stemprep checked", then `python -m stemprep.evaluate` scores changes
  (after `stemprep reanalyze`). 6 sample tracks have Demucs stems so far
  (the 33-track sample run was stopped; `stemprep hq` would finish it).
- Option the user deferred: Spleeter *inside* Mixxx, streaming ahead of the
  playhead (stems ~2 s after load). Needs ONNX Runtime in the Mixxx Windows
  build + a streaming SoundSource. Spleeter runs ~8-9x real time here.
- Faster fast tier: 3-network Spleeter (other = residual), skip re-encoding
  stream 0, beats on fallback tracks (tempo flips) still take ~20-30 s.
- Optional: run stemprep analysis from inside Mixxx (context menu → run tool).
- Section strip/names in the legacy (non-GL) waveform renderer.

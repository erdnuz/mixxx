Mixxx 2.6 custom build (erdnuz/mixxx, branch custom-dj)
========================================================

Start it with "Mixxx Custom.bat" (not mixxx.exe directly). The .bat keeps this
build's settings and library in %LOCALAPPDATA%\Mixxx-Custom.

Library: add Music\stemprep\Downloads (your tracks). Do NOT add
Music\stemprep\Stems: Mixxx finds each track's stems by itself, and adding
that folder would list every stem file as an extra track.

What's new in this build
------------------------
* Stems for every track, automatically: when you load a track, stemprep
  (installed separately, see tools/stemprep) works in the background:
  bars/phrases/sections in ~8 s, fast stems in about a minute. They are
  switched in when the deck is stopped (position, tempo, pitch and stem
  levels are kept). High quality stems: run "Stemprep" from the Desktop,
  option 7, e.g. overnight.
* Bars and phrases on the waveform: brighter lines on every bar, colored
  lines on phrase and section starts, a colored strip with the section names
  (Intro, Build, Drop, Breakdown, Outro) along the bottom; the overview
  shows the same strip.
* Hot cues are added at builds, drops and breakdowns the first time a track
  with stems analysis is loaded (only into empty slots 1-8). Off:
  [Structure] AutoHotcues 0 in mixxx.cfg.
* BRAKE button on each deck (LateNight skin): slow down to a stop like a
  turntable; press again to spin back up.
* Controls for mappings / keyboard ([ChannelN]):
    phrase_jump_forward/backward, section_jump_forward/backward
    phrase_sync        line this deck's phrase position up with the playing deck
    play_on_phrase     start exactly on the playing deck's next phrase
    stem_mask_on_bar   stems to hear from the next downbeat (bit mask)
    bar_loop (N bars from the downbeat), phrase_loop, phrase_restart
    beat_in_bar, beats_until_bar, bar_in_phrase, beats_until_phrase,
    section_index, structure_loaded, structure_reload
    brake, brake_active, brake_time, softstart_time

Pioneer DDJ-SB2
---------------
In Preferences > Controllers > DDJ-SB2 choose
"Pioneer DDJ-SB2 (Stems + Phrases)".

Transport
* SYNC (tap) on a stopped deck: tempo + beats + bars and phrases line up with
  the playing deck. Hold = sync lock. SHIFT + SYNC = quantize (LED shows it).
* SHIFT + PLAY: brake to a stop, again = spin back up (PLAY blinks meanwhile).
* SHIFT + TEMPO slider: key, in semitones (takes over at the current key).
* SHIFT + KEYLOCK: glide tempo back to 0 and reset the key.

Pads (mode buttons on the controller)
* HOT CUE, AUTO LOOP, ROLL, SAMPLER: as before.
* MANUAL LOOP = BAR LOOPS: 1, 2, 4, 8 bars starting on the downbeat; the
  same pad again ends the loop.
  SHIFT + pad = SLICER: hold pad 1-4 to play from that beat of the bar; on
  release the track carries on where it would have been. The pad of the
  beat that's playing is lit.
* CUE LOOP (SHIFT + MANUAL LOOP), stem tracks: tap = mute/unmute Drums, Bass,
  Melody, Vocals on the next downbeat (pad blinks until then); SHIFT + pad =
  solo; hold a pad + turn FILTER = filter just that stem.
  Normal tracks: low/mid/high kill and mute.
* BANK (SHIFT + SAMPLER): previous / next section, previous / next phrase
  (in phase). In the last 4 bars before a phrase the pads count down.
  SHIFT + pad: 1 phrase sync, 2 start on the other deck's next phrase
  (blinks while waiting, again = cancel), 3 back to this phrase's start,
  4 loop this phrase.

Effects
* FX buttons: tap = select effect, hold = on/off (as before).
* SHIFT + FX buttons (Deck1 / Head / Deck2): apply the effect unit to deck 1,
  the headphones or deck 2 (lit = applied).
* SHIFT + FX knob: the unit's super knob.

Options (on/off for each of these) are at the top of
Pioneer-DDJ-SB2-Stems-scripts.js in the controllers folder.

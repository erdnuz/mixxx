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
* Hot cues (up to 8, in empty slots) are added as soon as the section
  names appear: drops first, then grooves, breakdowns and builds. The
  pads keep that order (DROP, DROP 2, ... BUILD). When the stems are ready they
  move to the improved positions (while the deck is stopped); cues you moved,
  renamed or deleted are left alone. Off: [Structure] AutoHotcues 0 in
  mixxx.cfg.
* BRAKE button on each deck (LateNight skin): slow down to a stop like a
  turntable; press again to spin back up.
* Controls for mappings / keyboard ([ChannelN]):
    phrase_jump_forward/backward, section_jump_forward/backward
    sync_step          next sync step: beats, bars, next hot cues (see SYNC)
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
* SYNC tap, in steps against the playing deck: 1st tap beats, 2nd tap bars,
  3rd tap jumps whole bars so your next hot cue lands on their next hot cue.
  Stopped deck: 1st tap tempo + place in the phrase, 2nd tap = it starts by
  itself so both next hot cues meet (tap again to cancel). Steps already done
  are skipped. Hold SYNC = sync lock on/off. SHIFT + SYNC = quantize.
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
  (blinks while waiting, again = cancel), 3 CUE SYNC (below), 4 loop this
  phrase.

CUE SYNC: make one of your hot cues land exactly on one of theirs
* On the stopped deck press SHIFT + BANK pad 3 (it blinks).
* Optional: press a HOT CUE pad on your deck = your cue (default: your DROP).
* Press a HOT CUE pad on the playing deck = their cue. It's armed: your deck
  syncs, cues up 8 bars before your cue and starts by itself so both cues
  hit together. Examples: their DROP + your DROP = double drop; their
  BREAKDOWN or OUTRO + your DROP = handover.
* Pad 3 twice = both DROPs (quick double drop). Pad 3 while armed = cancel.
  The hot cue pads don't jump while you pick.

Library playlists
* Every folder in a library folder becomes a playlist with its name (e.g.
  "130 fweak"), refreshed after each library rescan, in Spotify order when
  the folder is linked to a Spotify playlist. They are locked because they
  are rewritten; make your own playlists for anything else.
  Off: [Library] FolderPlaylists 0 in mixxx.cfg.
* Link your folders to Spotify: Stemprep on the Desktop, option 8. After
  that, option 1 (sync) downloads new tracks into those folders; rescan the
  library in Mixxx to update the playlists.

Effects
* FX buttons: tap = select effect, hold = on/off (as before).
* SHIFT + FX buttons = beat time of that side's effects (echo delay,
  flanger/phaser/autopan period, tremolo rate): FX 1 half, FX 2 back to the
  default, FX 3 double.
* SHIFT + FX knob: the unit's super knob.

Options (on/off for each of these) are at the top of
Pioneer-DDJ-SB2-Stems-scripts.js in the controllers folder.

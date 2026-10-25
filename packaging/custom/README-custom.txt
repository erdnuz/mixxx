Mixxx 2.6 custom build (erdnuz/mixxx, branch custom-dj)
========================================================

Start it with "Mixxx Custom.bat" (not mixxx.exe directly). The .bat keeps this
build's settings and library in %LOCALAPPDATA%\Mixxx-Custom, so your normal
Mixxx 2.5 install and its library are not touched.

First run: to bring your existing library over, close all Mixxx windows, then
copy mixxxdb.sqlite (and mixxx.cfg if you want your settings) from
%LOCALAPPDATA%\Mixxx to %LOCALAPPDATA%\Mixxx-Custom. Mixxx 2.6 upgrades the
copy; the original stays usable by Mixxx 2.5.

What's new in this build
------------------------
* Stems: load .stem.mp4 files (made by stemprep) and mute / fade Drums, Bass,
  Melody and Vocals per deck.
* Bars and phrases: for tracks analyzed by stemprep, the waveform shows
  brighter lines on every bar (4 beats), colored lines on phrase and section
  starts, and a colored strip along the bottom (Intro, Build, Drop,
  Breakdown, Outro). The overview shows the same strip with labels.
  Bars follow the real downbeats found by the analyzer, not just "every 4th
  beat from the start".
* Hot cues: the first time an analyzed track is loaded, cues are added at the
  builds, drops and breakdowns (only in empty hot cue slots 1-8). Turn this
  off in mixxx.cfg with  [Structure] AutoHotcues 0
* Controls for mappings / keyboard:
    [ChannelN] phrase_jump_forward / phrase_jump_backward
    [ChannelN] section_jump_forward / section_jump_backward
    [ChannelN] beats_until_phrase, section_index, structure_loaded,
               structure_reload (re-read the analysis file)

Pioneer DDJ-SB2
---------------
In Preferences > Controllers > DDJ-SB2 choose
"Pioneer DDJ-SB2 (Stems + Phrases)":
* SHIFT + PLAY: brake to a stop; press again to spin back up.
* CUE LOOP pads (SHIFT + MANUAL LOOP): on stem tracks, pads 1-4 mute/unmute
  Drums / Bass / Melody / Vocals (lit = playing); SHIFT + pad solos a stem.
  On normal tracks they stay low/mid/high kill and mute.
* BANK pads (SHIFT + SAMPLER): previous / next section, previous / next
  phrase. Jumps keep you in phase. Pad 4 blinks in the bar before the next
  phrase.
Options are at the top of Pioneer-DDJ-SB2-Stems-scripts.js in the
controllers folder.

var PioneerDDJSB2 = {};
///////////////////////////////////////////////////////////////
//                       USER OPTIONS                        //
///////////////////////////////////////////////////////////////

// If true, vinyl mode will be enabled when Mixxx starts.
PioneerDDJSB2.vinylModeOnStartup = false;

// If true, the vinyl button activates slip. Vinyl mode is then activated by using shift.
// Allows toggling slip faster, but is counterintuitive.
PioneerDDJSB2.invertVinylSlipButton = false;

// If true, pressing shift + cue will play the track in reverse and enable slip mode,
// which can be used like a censor effect. If false, pressing shift + cue jumps to
// the beginning of the track and stops playback.
PioneerDDJSB2.reverseRollOnShiftCue = false;

// If true, SHIFT + VINYL switches SLIP MODE on/off (lit when on): while on,
// scratching and bar loops go back to where the track would have been as
// soon as you let go of the jog wheel / the loop ends. If false, SHIFT +
// VINYL is slip while held (original mapping).
PioneerDDJSB2.slipReturns = true;

// Sets the jogwheels sensitivity. 1 is default, 2 is twice as sensitive, 0.5 is half as sensitive.
PioneerDDJSB2.jogwheelSensitivity = 1.0;

// Sets how much more sensitive the jogwheels get when holding shift.
// Set to 1 to disable jogwheel sensitivity increase when holding shift.
PioneerDDJSB2.jogwheelShiftMultiplier = 100;

// Time per step (in ms) for pitch speed fade to normal
PioneerDDJSB2.speedRateToNormalTime = 200;

// If true Level-Meter shows VU-Master left & right. If false shows level of active deck.
PioneerDDJSB2.showVumeterMaster = false;

// If true VU-Level twinkle if AutoDJ is ON.
PioneerDDJSB2.twinkleVumeterAutodjOn = true;

// If true, releasing browser knob jumps forward to jumpPreviewPosition.
PioneerDDJSB2.jumpPreviewEnabled = true;
// Position in the track to jump to. 0 is the beginning of the track and 1 is the end.
PioneerDDJSB2.jumpPreviewPosition = 0.5;

// --- Stems + phrases additions --------------------------------------------

// If true, SHIFT + PLAY slows the track down to a stop like a turntable being
// switched off. Pressing it again while stopped (or still slowing down) spins
// the track back up. If false, SHIFT + PLAY plays in reverse (original mapping).
PioneerDDJSB2.shiftPlayBrake = true;
// Seconds the brake takes from full speed to a stop. Leave at null to use the
// deck's setting ([ChannelN],brake_time, default 2), which skins can change too.
PioneerDDJSB2.brakeSeconds = null;
// Seconds to spin back up to full speed (null: [ChannelN],softstart_time, default 0.8).
PioneerDDJSB2.softStartSeconds = null;

// If true, on tracks with stems the CUE LOOP pads (SHIFT + MANUAL LOOP) mute
// and unmute Drums, Bass, Melody and Vocals; a lit pad means the stem is
// playing. SHIFT + pad solos that stem (press again to bring all back).
// Hold a stem pad and turn FILTER to filter just that stem.
// Tracks without stems keep the EQ kill / mute pads.
PioneerDDJSB2.stemPads = true;

// If true, the BANK pads (SHIFT + SAMPLER) navigate the track structure found
// by stemprep: pad 1 / 2 = previous / next section (Intro, Build, Drop...),
// pad 3 / 4 = previous / next phrase. Jumps keep the position inside the bar,
// so the mix stays in phase. In the last 4 bars before a new phrase the pads
// count down (4 lit, 3, 2, then pad 1 blinks). If false, the pads load samplers.
PioneerDDJSB2.phraseBankPads = true;

// If true, SYNC taps go in steps (sync_step): beats, then bars, then the next
// hot cues of both tracks meet (a stopped deck: tempo + phrase, then it starts
// by itself so the next hot cues meet). Holding SYNC turns sync lock on/off. Needs
// structure data on both decks (otherwise a tap is a plain beat sync).
// false = Mixxx's own SYNC button.
PioneerDDJSB2.syncAlignsPhrases = true;

// If true, the stem pads take effect exactly on the next downbeat, so a drop
// or breakdown can be set up ahead. Pending pads blink until then.
PioneerDDJSB2.stemsOnBar = true;

// If true:
//   MANUAL LOOP pads = BAR LOOPS: 1, 2, 4, 8 bars starting on the bar's
//     downbeat (press again to end the loop)
//   SHIFT + pad in MANUAL LOOP mode = SLICER: hold pad N to play from beat N
//     of the current bar; on release the track carries on where it would
//     have been (the pad of the beat that's playing is lit)
//   SHIFT + BANK pads = 1 phrase sync, 2 start on the other deck's next phrase
//     (blinks while waiting; press again to cancel), 3 CUE SYNC (see
//     cueSyncButton: make one of my hot cues land on one of theirs, e.g.
//     double drop or my drop on their breakdown), 4 loop this phrase
// If false: the classic manual loop pads and SHIFT + BANK = sampler eject.
PioneerDDJSB2.performancePads = true;

// SHIFT + TEMPO slider changes the key in whole semitones, up to this many
// either way. SHIFT + KEYLOCK resets tempo and key.
PioneerDDJSB2.keyShiftRange = 6;

/*
    Pioneer DDJ-SB2 mapping for Mixxx, with stem pads, brake and phrase navigation
    Copyright (c) 2017 Be (be.0@gmx.com), licensed under GPL version 2 or later
    Copyright (c) 2014-2015 various contributors, licensed under MIT license

    Contributors and change log:
    - erdnuz: stem mute/solo pads, SHIFT+PLAY brake / soft start, phrase and
      section navigation on the BANK pads, bar/phrase sync, on-the-bar stems,
      bar loops, slicer, per-stem filter, key shift, effect routing (needs the
      custom Mixxx build with structure support and tracks analyzed by
      tools/stemprep)
    - Be (be.0@gmx.com): update effects and autoloop mode for Mixxx 2.1, fix level meter scaling,
      remove LED flickering when pressing shift, start porting to Components
    - Michael Stahl (DG3NEC): original DDJ-SB2 mapping for Mixxx 2.0
    - Joan Ardiaca Jové (joan.ardiaca@gmail.com): Pioneer DDJ-SB mapping for Mixxx 2.0
    - wingcom (wwingcomm@gmail.com): start of Pioneer DDJ-SB mapping
      https://github.com/wingcom/Mixxx-Pioneer-DDJ-SB
    - Hilton Rudham: Pioneer DDJ-SR mapping
      https://github.com/hrudham/Mixxx-Pioneer-DDJ-SR

    GPL license notice for current version:
    This program is free software; you can redistribute it and/or modify it under the terms of the
    GNU General Public License as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
    without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
    the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this program; if
    not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


    MIT License for earlier versions:
    Permission is hereby granted, free of charge, to any person obtaining a copy of this software
    and associated documentation files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or
    substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
    BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

    TODO:
      - bug when touching jog wheel for first time in vinyl mode
*/



///////////////////////////////////////////////////////////////
//               INIT, SHUTDOWN & GLOBAL HELPER              //
///////////////////////////////////////////////////////////////
PioneerDDJSB2.speedRateToNormalTimer = new Array(4);

PioneerDDJSB2.init = function(_id) {
    PioneerDDJSB2.deck = [];
    PioneerDDJSB2.deck[1] = new PioneerDDJSB2.Deck(1);
    PioneerDDJSB2.deck[2] = new PioneerDDJSB2.Deck(2);
    PioneerDDJSB2.deck[3] = new PioneerDDJSB2.Deck(3);
    PioneerDDJSB2.deck[4] = new PioneerDDJSB2.Deck(4);

    PioneerDDJSB2.effectUnit = [];
    PioneerDDJSB2.effectUnit[1] = new PioneerDDJSB2.EffectUnit(1);
    PioneerDDJSB2.effectUnit[2] = new PioneerDDJSB2.EffectUnit(2);

    PioneerDDJSB2.scratchSettings = {
        "alpha": 1.0 / 8,
        "beta": 1.0 / 8 / 32,
        "jogResolution": 720,
        "vinylSpeed": 33 + 1 / 3,
        "safeScratchTimeout": 20
    };

    PioneerDDJSB2.channelGroups = {
        "[Channel1]": 0x00,
        "[Channel2]": 0x01,
        "[Channel3]": 0x02,
        "[Channel4]": 0x03
    };

    PioneerDDJSB2.samplerGroups = {
        "[Sampler1]": 0x00,
        "[Sampler2]": 0x01,
        "[Sampler3]": 0x02,
        "[Sampler4]": 0x03
    };

    PioneerDDJSB2.shiftPressed = false;

    // Fader start position per MIDI channel (deck 1-4 = index 0-3)
    PioneerDDJSB2.chFaderStart = [null, null, null, null];

    PioneerDDJSB2.scratchMode = [false, false, false, false];
    PioneerDDJSB2.slipModeOn = [false, false, false, false];

    PioneerDDJSB2.ledGroups = {
        "hotCue": 0x00,
        "autoLoop": 0x10,
        "manualLoop": 0x20,
        "sampler": 0x30
    };

    PioneerDDJSB2.nonPadLeds = {
        "headphoneCue": 0x54,
        "shiftHeadphoneCue": 0x68,
        "cue": 0x0C,
        "shiftCue": 0x48,
        "keyLock": 0x1A,
        "shiftKeyLock": 0x60,
        "play": 0x0B,
        "shiftPlay": 0x47,
        "vinyl": 0x17,
        "shiftVinyl": 0x4E,
        "sync": 0x58,
        "shiftSync": 0x5C
    };

    PioneerDDJSB2.valueVuMeter = {
        "[Channel1]_current": 0,
        "[Channel2]_current": 0,
        "[Channel3]_current": 0,
        "[Channel4]_current": 0,
        "[Channel1]_enabled": 1,
        "[Channel2]_enabled": 1,
        "[Channel3]_enabled": 1,
        "[Channel4]_enabled": 1,

    };

    PioneerDDJSB2.loopIntervals = [1, 2, 4, 8, 16, 32, 64];

    PioneerDDJSB2.looprollIntervals = [1 / 16, 1 / 8, 1 / 4, 1 / 2, 1, 2, 4, 8];

    PioneerDDJSB2.bindNonDeckControlConnections(false);
    PioneerDDJSB2.initDeck("[Channel1]");
    PioneerDDJSB2.initDeck("[Channel2]");
    PioneerDDJSB2.initDeck("[Channel3]");
    PioneerDDJSB2.initDeck("[Channel4]");

    if (PioneerDDJSB2.twinkleVumeterAutodjOn) {
        PioneerDDJSB2.vuMeterTimer = engine.beginTimer(100, PioneerDDJSB2.vuMeterTwinkle);
    }
    // Blinking LEDs: brake, stems waiting for the bar, start on phrase
    PioneerDDJSB2.blinkTimer = engine.beginTimer(125, PioneerDDJSB2.blinkTick);

    // request the positions of the knobs and faders from the controller
    midi.sendShortMsg(0x9B, 0x09, 0x7f);
};

PioneerDDJSB2.Deck = function(deckNumber) {
    var theDeck = this;
    this.group = "[Channel" + deckNumber + "]";

    this.shiftButton = function(channel, control, value, _status, _group) {
        if (value > 0) {
            theDeck.shift();
            PioneerDDJSB2.shiftPressed = true;
            PioneerDDJSB2.chFaderStart[deckNumber - 1] = null;
        } else {
            theDeck.unshift();
            PioneerDDJSB2.shiftPressed = false;
        }
        // The key slider picks up again next time (no jumps)
        theDeck.keyFader.pickedUp = false;
    };

    this.playButton = new components.PlayButton({
        midi: [0x90 + deckNumber - 1, 0x0B],
        shiftOffset: 60,
        shiftControl: true,
        sendShifted: true,
        isShifted: false,
        unshift: function() {
            this.isShifted = false;
            this.inKey = "play";
        },
        shift: function() {
            this.isShifted = true;
            this.inKey = PioneerDDJSB2.shiftPlayBrake ? "play" : "reverse";
        },
        input: function(channel, control, value, status, group) {
            if (this.isShifted && PioneerDDJSB2.shiftPlayBrake) {
                if (this.isPress(channel, control, value, status)) {
                    PioneerDDJSB2.brakeOrSoftStart(this.group);
                }
                return;
            }
            components.PlayButton.prototype.input.call(this, channel, control, value, status, group);
        },
    });

    this.cueButton = new components.CueButton({
        midi: [0x90 + deckNumber - 1, 0x0C],
        shiftOffset: 60,
        shiftControl: true,
        sendShifted: true,
        reverseRollOnShift: PioneerDDJSB2.reverseRollOnShiftCue,
    });

    this.syncButton = new components.SyncButton({
        midi: [0x90 + deckNumber - 1, 0x58],
        shiftOffset: 4,
        shiftControl: true,
        // The SHIFT LED (0x5C) shows quantize instead, see quantizeLed
        sendShifted: false,
        // SyncButton sets its own input() for each layer: replace the plain one
        unshift: function() {
            components.SyncButton.prototype.unshift.call(this);
            if (!PioneerDDJSB2.syncAlignsPhrases) {
                return;
            }
            // Tap = next sync step (beats, bars, next hot cues); hold = sync lock
            // on/off
            this.input = function(channel, control, value, status, _group) {
                if (this.isPress(channel, control, value, status)) {
                    this.longPressTimer = engine.beginTimer(this.longPressTimeout, () => {
                        this.longPressTimer = 0;
                        script.toggleControl(this.group, "sync_enabled");
                    }, true);
                } else if (this.longPressTimer) {
                    engine.stopTimer(this.longPressTimer);
                    this.longPressTimer = 0;
                    script.triggerControl(this.group, "sync_step");
                }
            };
        },
    });

    var effectUnitNumber = deckNumber;
    if (deckNumber > 2) {
        effectUnitNumber -= 2;
    }

    this.gainKnob = new components.Pot({
        unshift: function() {
            this.group = "[Channel" + deckNumber + "]";
            this.inKey = "pregain";
            this.disconnect();
            this.connect();
        },
        shift: function() {
            var focusedEffect = engine.getValue("[EffectRack1_EffectUnit" + effectUnitNumber + "]", "focused_effect");
            this.group = "[EffectRack1_EffectUnit" + effectUnitNumber + "_Effect" + focusedEffect + "]";
            this.inKey = "parameter1";
            this.disconnect();
            this.connect();
        },
    });

    this.eqKnob = [];
    for (var k = 1; k <= 3; k++) {
        this.eqKnob[k] = new components.Pot({
            number: k,
            unshift: function() {
                this.group = "[EqualizerRack1_[Channel" + deckNumber + "]_Effect1]";
                this.inKey = "parameter" + this.number;
                this.disconnect();
                this.connect();
            },
            shift: function() {
                var focusedEffect = engine.getValue("[EffectRack1_EffectUnit" + effectUnitNumber + "]", "focused_effect");
                this.group = "[EffectRack1_EffectUnit" + effectUnitNumber + "_Effect" + focusedEffect + "]";
                this.inKey = "parameter" + (5 - this.number);
                this.disconnect();
                this.connect();
            },
        });
    }

    this.quickEffectKnob = new components.Pot({
        input: function(channel, control, value, status, group) {
            // Holding a stem pad: this knob filters only that stem
            const stem = PioneerDDJSB2.heldStemPad[theDeck.group];
            if (!this.isShifted && stem !== undefined && PioneerDDJSB2.stemPadsActive(theDeck.group)) {
                const full = this.MSB !== undefined ? (this.MSB << 7) + value : value << 7;
                engine.setParameter(PioneerDDJSB2.stemQuickEffectGroup(theDeck.group, stem),
                    "super1", full / 0x3FFF);
                PioneerDDJSB2.heldStemTurned[theDeck.group] = true;
                return;
            }
            components.Pot.prototype.input.call(this, channel, control, value, status, group);
        },
        unshift: function() {
            this.isShifted = false;
            this.group = "[QuickEffectRack1_[Channel" + deckNumber + "]]";
            this.inKey = "super1";
            this.disconnect();
            this.connect();
        },
        shift: function() {
            this.isShifted = true;
            var focusedEffect = engine.getValue("[EffectRack1_EffectUnit" + effectUnitNumber + "]", "focused_effect");
            this.group = "[EffectRack1_EffectUnit" + effectUnitNumber + "_Effect" + focusedEffect + "]";
            this.inKey = "parameter5";
            this.disconnect();
            this.connect();
        },
    });

    this.tempoFader = new components.Pot({
        inKey: "rate",
        //         relative: true,
        invert: true,
    });

    // SHIFT + TEMPO: key in whole semitones. It only takes over once the
    // slider reaches the current key, so the key never jumps.
    this.keyFader = new components.Pot({
        inKey: "pitch_adjust",
        pickedUp: false,
        input: function(channel, control, value, _status, _group) {
            const full = this.MSB !== undefined ? (this.MSB << 7) + value : value << 7;
            const range = PioneerDDJSB2.keyShiftRange;
            // Same direction as the tempo slider (inverted like it; rate_dir is
            // Mixxx's "slider up = faster/slower" setting)
            const direction = engine.getValue(theDeck.group, "rate_dir") < 0 ? -1 : 1;
            const semitones = direction * Math.round((0.5 - full / 0x3FFF) * 2 * range);
            const current = Math.round(engine.getValue(theDeck.group, "pitch_adjust"));
            if (!this.pickedUp) {
                if (semitones !== current) {
                    return;
                }
                this.pickedUp = true;
            }
            if (semitones !== current) {
                engine.setValue(theDeck.group, "pitch_adjust", semitones);
            }
        },
        // No output and no soft takeover: input() handles the pick-up
        connect: function() {},
        output: function() {},
    });

    this.topPadRow = new components.ComponentContainer();
    this.topPadRow.autoLoopLayer = new components.ComponentContainer();
    this.topPadRow.autoLoopLayer.beatloopButton = new components.Button({
        midi: [0x96 + deckNumber, 0x10],
        unshift: function() {
            this.inKey = "beatloop_activate";
            this.outKey = "beatloop_activate";
            this.disconnect();
            this.connect();
            this.trigger();
        },
        shift: function() {
            this.inKey = "beatlooproll_activate";
            this.outKey = "beatlooproll_activate";
            this.disconnect();
            this.connect();
            this.trigger();
        },
    });

    this.topPadRow.autoLoopLayer.beatloopHalveButton = new components.Button({
        midi: [0x96 + deckNumber, 0x11],
        unshift: function() {
            this.inKey = "loop_halve";
            this.outKey = "loop_halve";
            this.disconnect();
            this.connect();
            this.trigger();
        },
        shift: function() {
            this.inKey = "beatjump_backward";
            this.outKey = "beatjump_backward";
            this.disconnect();
            this.connect();
            this.trigger();
        },
    });

    this.topPadRow.autoLoopLayer.beatloopDoubleButton = new components.Button({
        midi: [0x96 + deckNumber, 0x12],
        unshift: function() {
            this.inKey = "loop_double";
            this.outKey = "loop_double";
            this.disconnect();
            this.connect();
            this.trigger();
        },
        shift: function() {
            this.inKey = "beatjump_forward";
            this.outKey = "beatjump_forward";
            this.disconnect();
            this.connect();
            this.trigger();
        },
    });

    this.topPadRow.autoLoopLayer.reloopButton = new components.Button({
        midi: [0x96 + deckNumber, 0x13],
        outKey: "loop_enabled",
        unshift: function() {
            this.inKey = "reloop_toggle";
        },
        shift: function() {
            this.inKey = "reloop_andstop";
        },
    });

    this.topPadRow.forEachComponent(function(button) {
        button.sendShifted = true;
        button.shiftControl = true;
        button.shiftOffset = 8;
    });

    this.forEachComponent(function(c) {
        if (c.group === undefined) {
            c.group = theDeck.group;
            c.connect();
            c.trigger();
        }
    });
};
PioneerDDJSB2.Deck.prototype = components.ComponentContainer.prototype;

PioneerDDJSB2.shutdown = function() {
    // turn off button LEDs
    var skip = [0x72, 0x1B, 0x69, 0x1E, 0x6B, 0x20, 0x6D, 0x22, 0x6F, 0x70, 0x75];
    for (var channel = 0; channel <= 10; channel++) {
        for (var control = 0; control <= 127; control++) {
            // skip deck toggle buttons and pad mode buttons
            if (skip.indexOf(control) > -1) {
                continue;
            }
            midi.sendShortMsg(0x90 + channel, control, 0);
        }
    }


    // switch to decks 1 and 2 to turn off deck indication lights
    midi.sendShortMsg(0x90, 0x72, 0x7f);
    midi.sendShortMsg(0x91, 0x72, 0x7f);

    // turn off level meters
    for (channel = 0; channel <= 3; channel++) {
        midi.sendShortMsg(0xB0 + channel, 2, 0);
    }
};

// One step of gliding the tempo slider back to 0 (SHIFT + KEYLOCK). Works on
// the slider value directly, so it doesn't depend on the slider direction
// setting (rate_perm_up/down do).
PioneerDDJSB2.speedRateToNormal = function(group, deck) {
    const step = 0.005; // of the full slider range per tick
    const rate = engine.getValue(group, "rate");
    if (Math.abs(rate) <= step) {
        engine.setValue(group, "rate", 0);
        engine.stopTimer(PioneerDDJSB2.speedRateToNormalTimer[deck]);
        PioneerDDJSB2.speedRateToNormalTimer[deck] = 0;
        return;
    }
    engine.setValue(group, "rate", rate - Math.sign(rate) * step);
};


///////////////////////////////////////////////////////////////
//                      VU - Meter                           //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.blinkAutodjState = 0; // new for DDJ-SB2

PioneerDDJSB2.vuMeterTwinkle = function() {
    if (engine.getValue("[AutoDJ]", "enabled")) {
        PioneerDDJSB2.blinkAutodjState = PioneerDDJSB2.blinkAutodjState + 1;
        if (PioneerDDJSB2.blinkAutodjState > 3) {
            PioneerDDJSB2.blinkAutodjState = 0;
        }
        if (PioneerDDJSB2.blinkAutodjState === 0) {
            PioneerDDJSB2.valueVuMeter["[Channel1]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel3]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel2]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel4]_enabled"] = 0;
        }
        if (PioneerDDJSB2.blinkAutodjState === 1) {
            PioneerDDJSB2.valueVuMeter["[Channel1]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel3]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel2]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel4]_enabled"] = 0;
        }
        if (PioneerDDJSB2.blinkAutodjState === 2) {
            PioneerDDJSB2.valueVuMeter["[Channel1]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel3]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel2]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel4]_enabled"] = 1;
        }
        if (PioneerDDJSB2.blinkAutodjState === 3) {
            PioneerDDJSB2.valueVuMeter["[Channel1]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel3]_enabled"] = 0;
            PioneerDDJSB2.valueVuMeter["[Channel2]_enabled"] = 1;
            PioneerDDJSB2.valueVuMeter["[Channel4]_enabled"] = 1;
        }
    } else {
        PioneerDDJSB2.valueVuMeter["[Channel1]_enabled"] = 1;
        PioneerDDJSB2.valueVuMeter["[Channel3]_enabled"] = 1;
        PioneerDDJSB2.valueVuMeter["[Channel2]_enabled"] = 1;
        PioneerDDJSB2.valueVuMeter["[Channel4]_enabled"] = 1;
    }
};


///////////////////////////////////////////////////////////////
//                        AutoDJ                             //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.autodjSkipNext = function(channel, control, value, _status, _group) {
    if (value === 0) {
        return;
    }
    if (engine.getValue("[AutoDJ]", "enabled")) {
        engine.setValue("[AutoDJ]", "skip_next", true);
    }
};

PioneerDDJSB2.autodjToggle = function(channel, control, value, _status, _group) {
    if (value === 0) {
        return;
    }
    if (engine.getValue("[AutoDJ]", "enabled")) {
        engine.setValue("[AutoDJ]", "enabled", false);
    } else {
        engine.setValue("[AutoDJ]", "enabled", true);
    }
};


///////////////////////////////////////////////////////////////
//                      CONTROL BINDING                      //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.bindSamplerControlConnections = function(samplerGroup, isUnbinding) {
    engine.connectControl(samplerGroup, "duration", "PioneerDDJSB2.samplerLeds", isUnbinding);
};

PioneerDDJSB2.bindDeckControlConnections = function(channelGroup, isUnbinding) {
    var i,
        index,
        controlsToFunctions = {
            "pfl": "PioneerDDJSB2.headphoneCueLed",
            "keylock": "PioneerDDJSB2.keyLockLed",
            "loop_in": "PioneerDDJSB2.loopInLed",
            "loop_out": "PioneerDDJSB2.loopOutLed",
            "filterLowKill": "PioneerDDJSB2.lowKillLed",
            "filterMidKill": "PioneerDDJSB2.midKillLed",
            "filterHighKill": "PioneerDDJSB2.highKillLed",
            "mute": "PioneerDDJSB2.muteLed",
            "loop_enabled": "PioneerDDJSB2.loopExitLed",
            "quantize": "PioneerDDJSB2.quantizeLed",
        };

    if (PioneerDDJSB2.invertVinylSlipButton) {
        controlsToFunctions.slipEnabled = "PioneerDDJSB2.slipLed";
    }

    for (i = 1; i <= 8; i++) {
        controlsToFunctions["hotcue_" + i + "_enabled"] = "PioneerDDJSB2.hotCueLeds";
    }

    for (index in PioneerDDJSB2.looprollIntervals) {
        controlsToFunctions["beatlooproll_" + PioneerDDJSB2.looprollIntervals[index] + "_activate"] = "PioneerDDJSB2.beatlooprollLeds";
    }

    script.bindConnections(channelGroup, controlsToFunctions, isUnbinding);
};

PioneerDDJSB2.bindNonDeckControlConnections = function(isUnbinding) {
    var samplerIndex;

    for (samplerIndex = 1; samplerIndex <= 4; samplerIndex++) {
        PioneerDDJSB2.bindSamplerControlConnections("[Sampler" + samplerIndex + "]", isUnbinding);
    }

    if (PioneerDDJSB2.showVumeterMaster) {
        engine.connectControl("[Main]", "vu_meter_left", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
        engine.connectControl("[Main]", "vu_meter_right", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
    } else {
        engine.connectControl("[Channel1]", "vu_meter", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
        engine.connectControl("[Channel2]", "vu_meter", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
        engine.connectControl("[Channel3]", "vu_meter", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
        engine.connectControl("[Channel4]", "vu_meter", "PioneerDDJSB2.VuMeterLeds", isUnbinding);
    }
};

///////////////////////////////////////////////////////////////
//                       DECK SWITCHING                      //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.deckSwitchTable = {
    "[Channel1]": "[Channel1]",
    "[Channel2]": "[Channel2]",
    "[Channel3]": "[Channel3]",
    "[Channel4]": "[Channel4]"

};

PioneerDDJSB2.deckShiftSwitchTable = {
    "[Channel1]": "[Channel3]",
    "[Channel2]": "[Channel4]",
    "[Channel3]": "[Channel1]",
    "[Channel4]": "[Channel2]"
};

PioneerDDJSB2.initDeck = function(group) {
    PioneerDDJSB2.bindDeckControlConnections(group, false);
    PioneerDDJSB2.initStemsAndPhrases(group);
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.shiftKeyLock, PioneerDDJSB2.channelGroups[group] > 1);
    PioneerDDJSB2.toggleScratch(null, null, PioneerDDJSB2.vinylModeOnStartup, null, group);
};


///////////////////////////////////////////////////////////////
//            HIGH RESOLUTION MIDI INPUT HANDLERS            //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.highResMSB = {
    "[Channel1]": {},
    "[Channel2]": {},
    "[Channel3]": {},
    "[Channel4]": {}
};

PioneerDDJSB2.deckFaderMSB = function(channel, control, value, status, group) {
    PioneerDDJSB2.highResMSB[group].deckFader = value;
};

PioneerDDJSB2.deckFaderLSB = function(channel, control, value, status, group) {
    var fullValue = (PioneerDDJSB2.highResMSB[group].deckFader << 7) + value;

    if (PioneerDDJSB2.shiftPressed &&
        engine.getValue(group, "volume") === 0 &&
        fullValue !== 0 &&
        engine.getValue(group, "play") === 0
    ) {
        PioneerDDJSB2.chFaderStart[channel] = engine.getValue(group, "playposition");
        engine.setValue(group, "play", 1);
    } else if (
        PioneerDDJSB2.shiftPressed &&
        engine.getValue(group, "volume") !== 0 &&
        fullValue === 0 &&
        engine.getValue(group, "play") === 1 &&
        PioneerDDJSB2.chFaderStart[channel] !== null
    ) {
        engine.setValue(group, "play", 0);
        engine.setValue(group, "playposition", PioneerDDJSB2.chFaderStart[channel]);
        PioneerDDJSB2.chFaderStart[channel] = null;
    }
    engine.setValue(group, "volume", fullValue / 0x3FFF);
};

///////////////////////////////////////////////////////////////
//           SINGLE MESSAGE MIDI INPUT HANDLERS              //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.headphoneCueButton = function(channel, control, value, status, group) {
    if (value) {
        script.toggleControl(group, "pfl");
    }
};

PioneerDDJSB2.headphoneShiftCueButton = function(channel, control, value, status, group) {
    if (value) {
        script.toggleControl(PioneerDDJSB2.deckShiftSwitchTable[group], "pfl");
    }
};

PioneerDDJSB2.hotCueButtons = function(channel, control, value, status, group) {
    var hotCueIndex = (control >= 0x40 ? control - 0x40 + 5 : control + 1);
    if (PioneerDDJSB2.cueSyncPick && PioneerDDJSB2.pickCueForSync(group, hotCueIndex, value)) {
        return;
    }
    engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "hotcue_" + hotCueIndex + "_activate", value);
};

PioneerDDJSB2.clearHotCueButtons = function(channel, control, value, status, group) {
    var hotCueIndex = (control >= 0x48 ? control - 0x48 + 5 : control - 7);
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "hotcue_" + hotCueIndex + "_clear", 1);
    }
};

PioneerDDJSB2.beatloopRollButtons = function(channel, control, value, status, group) {
    var index = (control <= 0x53 ? control - 0x50 : control - 0x54);
    engine.setValue(
        PioneerDDJSB2.deckSwitchTable[group],
        "beatlooproll_" + PioneerDDJSB2.looprollIntervals[index] + "_activate",
        value
    );
};

PioneerDDJSB2.vinylButton = function(channel, control, value, status, group) {
    if (PioneerDDJSB2.invertVinylSlipButton) {
        engine.setValue(group, "slip_enabled", value / 127);
    } else {
        PioneerDDJSB2.toggleScratch(channel, control, value, status, group);
    }
};

PioneerDDJSB2.slipButton = function(channel, control, value, status, group) {
    if (PioneerDDJSB2.invertVinylSlipButton) {
        PioneerDDJSB2.toggleScratch(channel, control, value, status, group);
    } else if (!PioneerDDJSB2.slipReturns) {
        engine.setValue(group, "slip_enabled", value / 127);
    } else if (value) {
        // SLIP MODE on/off (lit when on): scratches and bar loops return to
        // where the track would have been as soon as they end
        const deck = PioneerDDJSB2.channelGroups[group];
        PioneerDDJSB2.slipModeOn[deck] = !PioneerDDJSB2.slipModeOn[deck];
        PioneerDDJSB2.nonPadLedControl(
            deck, PioneerDDJSB2.nonPadLeds.shiftVinyl, PioneerDDJSB2.slipModeOn[deck]);
        if (!PioneerDDJSB2.slipModeOn[deck]) {
            engine.setValue(group, "slip_enabled", 0);
        }
    }
};

// SLIP MODE: slip while something is going on (jog touched, bar loop)
PioneerDDJSB2.slipStart = function(group) {
    if (PioneerDDJSB2.slipModeOn[PioneerDDJSB2.channelGroups[group]]) {
        engine.setValue(group, "slip_enabled", 1);
    }
};

PioneerDDJSB2.slipEnd = function(group) {
    if (PioneerDDJSB2.slipModeOn[PioneerDDJSB2.channelGroups[group]]) {
        engine.setValue(group, "slip_enabled", 0); // jumps to the slip position
    }
};

PioneerDDJSB2.keyLockButton = function(channel, control, value, status, group) {
    if (value) {
        script.toggleControl(group, "keylock");
    }
};

// SHIFT + KEYLOCK: glide the tempo back to 0 and reset the key. (Used to step
// only once: the timer was one-shot.)
PioneerDDJSB2.shiftKeyLockButton = function(channel, control, value, status, group) {
    const deck = status - 0x90;
    if (!value) {
        return;
    }
    if (PioneerDDJSB2.speedRateToNormalTimer[deck]) {
        engine.stopTimer(PioneerDDJSB2.speedRateToNormalTimer[deck]);
    }
    PioneerDDJSB2.speedRateToNormalTimer[deck] = engine.beginTimer(
        Math.max(20, PioneerDDJSB2.speedRateToNormalTime / 10),
        () => { PioneerDDJSB2.speedRateToNormal(group, deck); });
    engine.setValue(group, "pitch_adjust", 0);
};

PioneerDDJSB2.loopInButton = function(channel, control, value, status, group) {
    engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_in", value ? 1 : 0);
};

PioneerDDJSB2.loopOutButton = function(channel, control, value, status, group) {
    engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_out", value ? 1 : 0);
};

PioneerDDJSB2.loopExitButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "reloop_exit", 1);
    }
};

PioneerDDJSB2.loopHalveButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_scale", 0.5);
    }
};

PioneerDDJSB2.loopDoubleButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_scale", 2.0);
    }
};

PioneerDDJSB2.loopMoveBackButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_move", -1);
    }
};

PioneerDDJSB2.loopMoveForwardButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(PioneerDDJSB2.deckSwitchTable[group], "loop_move", 1);
    }
};

PioneerDDJSB2.loadButton = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(group, "LoadSelectedTrack", 1);
    }
};


///////////////////////////////////////////////////////////////
//                          LED HELPERS                      //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.deckConverter = function(group) {
    var index;

    if (typeof group === "string") {
        for (index in PioneerDDJSB2.deckSwitchTable) {
            if (group === PioneerDDJSB2.deckSwitchTable[index]) {
                return PioneerDDJSB2.channelGroups[group];
            }
        }
        return null;
    }
    return group;
};

PioneerDDJSB2.padLedControl = function(deck, groupNumber, shiftGroup, ledNumber, shift, active) {
    var padLedsBaseChannel = 0x97,
        padLedControl = (shiftGroup ? 0x40 : 0x00) + (shift ? 0x08 : 0x00) + groupNumber + ledNumber,
        midiChannelOffset = PioneerDDJSB2.deckConverter(deck);

    if (midiChannelOffset !== null) {
        midi.sendShortMsg(
            padLedsBaseChannel + midiChannelOffset,
            padLedControl,
            active ? 0x7F : 0x00
        );
    }
};

PioneerDDJSB2.nonPadLedControl = function(deck, ledNumber, active) {
    var nonPadLedsBaseChannel = 0x90,
        midiChannelOffset = PioneerDDJSB2.deckConverter(deck);

    if (midiChannelOffset !== null) {
        midi.sendShortMsg(
            nonPadLedsBaseChannel + midiChannelOffset,
            ledNumber,
            active ? 0x7F : 0x00
        );
    }
};


///////////////////////////////////////////////////////////////
//                             LEDS                          //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.headphoneCueLed = function(value, group, _control) {
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.headphoneCue, value);
    // SHIFT + CUE on the other layer's deck (1<->3, 2<->4) toggles this deck's
    // PFL, so that is where its SHIFT LED shows it
    PioneerDDJSB2.nonPadLedControl(PioneerDDJSB2.deckShiftSwitchTable[group],
        PioneerDDJSB2.nonPadLeds.shiftHeadphoneCue, value);
};

PioneerDDJSB2.quantizeLed = function(value, group, _control) {
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.shiftSync, value);
};

PioneerDDJSB2.keyLockLed = function(value, group, _control) {
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.keyLock, value);
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.shiftKeyLock, value);
};

PioneerDDJSB2.slipLed = function(value, group, _control) {
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.vinyl, value);
    PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.shiftVinyl, value);
};

// The MANUAL LOOP pad LEDs show the bar loops when performancePads is on
PioneerDDJSB2.loopInLed = function(value, group, _control) {
    if (!PioneerDDJSB2.performancePads) {
        PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, false, 0, false, value);
    }
};

PioneerDDJSB2.loopOutLed = function(value, group, _control) {
    if (!PioneerDDJSB2.performancePads) {
        PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, false, 1, false, value);
    }
};

PioneerDDJSB2.loopExitLed = function(value, group, _control) {
    if (PioneerDDJSB2.performancePads) {
        if (!value) {
            PioneerDDJSB2.activeBarLoop[group] = 0; // the loop ended
        }
        PioneerDDJSB2.updateBarLoopLeds(group);
        return;
    }
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, false, 2, false, value);
};

PioneerDDJSB2.loopHalveLed = function(value, group, _control) {
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, false, 3, false, value);
};

PioneerDDJSB2.loopDoubleLed = function(value, group, _control) {
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, false, 3, true, value);
};

PioneerDDJSB2.lowKillLed = function(value, group, _control) {
    if (PioneerDDJSB2.stemPadsActive(group)) {
        return; // the pads show the stems instead
    }
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, 0, false, value);
};

PioneerDDJSB2.midKillLed = function(value, group, _control) {
    if (PioneerDDJSB2.stemPadsActive(group)) {
        return; // the pads show the stems instead
    }
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, 1, false, value);
};

PioneerDDJSB2.highKillLed = function(value, group, _control) {
    if (PioneerDDJSB2.stemPadsActive(group)) {
        return; // the pads show the stems instead
    }
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, 2, false, value);
};

PioneerDDJSB2.muteLed = function(value, group, _control) {
    if (PioneerDDJSB2.stemPadsActive(group)) {
        return; // the pads show the stems instead
    }
    PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, 3, false, value);
};

PioneerDDJSB2.samplerLeds = function(value, group, _control) {
    var sampler = PioneerDDJSB2.samplerGroups[group],
        channel;

    for (channel = 0; channel < 4; channel++) {
        PioneerDDJSB2.padLedControl(channel, PioneerDDJSB2.ledGroups.sampler, false, sampler, false, value);
        PioneerDDJSB2.padLedControl(channel, PioneerDDJSB2.ledGroups.sampler, false, sampler, true, value);
        // BANK pads (and their SHIFT layer) may show the phrase functions instead
        if (!PioneerDDJSB2.phraseBankPads) {
            PioneerDDJSB2.padLedControl(channel, PioneerDDJSB2.ledGroups.sampler, true, sampler, false, value);
        }
        if (!PioneerDDJSB2.performancePads) {
            PioneerDDJSB2.padLedControl(channel, PioneerDDJSB2.ledGroups.sampler, true, sampler, true, value);
        }
    }
};

PioneerDDJSB2.beatlooprollLeds = function(value, group, control) {
    var index,
        padNum,
        shifted;

    for (index in PioneerDDJSB2.looprollIntervals) {
        if (control === "beatlooproll_" + PioneerDDJSB2.looprollIntervals[index] + "_activate") {
            padNum = index % 4;
            shifted = (index >= 4);
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.autoLoop, true, padNum, shifted, value);
        }
    }
};

PioneerDDJSB2.hotCueLeds = function(value, group, control) {
    var shiftedGroup = false,
        padNum = null,
        hotCueNum;

    for (hotCueNum = 1; hotCueNum <= 8; hotCueNum++) {
        if (control === "hotcue_" + hotCueNum + "_enabled") {
            padNum = (hotCueNum - 1) % 4;
            shiftedGroup = (hotCueNum > 4);
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.hotCue, shiftedGroup, padNum, false, value);
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.hotCue, shiftedGroup, padNum, true, value);
        }
    }
};

PioneerDDJSB2.VuMeterLeds = function(value, group, control) {
    // The red LED lights up with MIDI values 119 (0x77) and above. That should only light up when
    // the track is clipping.
    if (engine.getValue(group, "peak_indicator") === 1) {
        value = 119;
    } else {
        // 117 was determined experimentally so the yellow LED only lights
        // up when the level meter in Mixxx is in the yellow region.
        value = Math.floor(value * 117);
    }

    if (!(PioneerDDJSB2.twinkleVumeterAutodjOn && engine.getValue("[AutoDJ]", "enabled"))) {
        var midiChannel;
        if (PioneerDDJSB2.showVumeterMaster) {
            if (control === "vu_meter_left") {
                midiChannel = 0;
            } else if (control === "vu_meter_right") {
                midiChannel = 1;
            }
            // Send for deck 1 or 2
            midi.sendShortMsg(0xB0 + midiChannel, 2, value);
            // Send for deck 3 or 4
            midi.sendShortMsg(0xB0 + midiChannel + 2, 2, value);
        } else {
            midiChannel = parseInt(group.substring(8, 9) - 1);
            midi.sendShortMsg(0xB0 + midiChannel, 2, value);
        }
    } else {
        if (group === "[Main]") {
            if (control === "vu_meter_left") {
                PioneerDDJSB2.valueVuMeter["[Channel1]_current"] = value;
                PioneerDDJSB2.valueVuMeter["[Channel3]_current"] = value;
            } else {
                PioneerDDJSB2.valueVuMeter["[Channel2]_current"] = value;
                PioneerDDJSB2.valueVuMeter["[Channel4]_current"] = value;
            }
        } else {
            PioneerDDJSB2.valueVuMeter[group + "_current"] = value;
        }

        for (var channel = 0; channel < 4; channel++) {
            var midiOut = PioneerDDJSB2.valueVuMeter["[Channel" + (channel + 1) + "]_current"];
            if (PioneerDDJSB2.valueVuMeter["[Channel" + (channel + 1) + "]_enabled"]) {
                midiOut = 0;
            }
            if (midiOut < 5 && PioneerDDJSB2.valueVuMeter["[Channel" + (channel + 1) + "]_enabled"] === 0) {
                midiOut = 5;
            }

            midi.sendShortMsg(
                0xB0 + channel,
                2,
                midiOut
            );
        }
    }
};


///////////////////////////////////////////////////////////////
//                          JOGWHEELS                        //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.getJogWheelDelta = function(value) { // O
    // The Wheel control centers on 0x40; find out how much it's moved by.
    return value - 0x40;
};

PioneerDDJSB2.jogRingTick = function(channel, control, value, status, group) {
    PioneerDDJSB2.pitchBendFromJog(group, PioneerDDJSB2.getJogWheelDelta(value));
};

PioneerDDJSB2.jogRingTickShift = function(channel, control, value, status, group) {
    PioneerDDJSB2.pitchBendFromJog(
        PioneerDDJSB2.deckSwitchTable[group],
        PioneerDDJSB2.getJogWheelDelta(value) * PioneerDDJSB2.jogwheelShiftMultiplier
    );
};

PioneerDDJSB2.jogPlatterTick = function(channel, control, value, status, group) {
    var deck = PioneerDDJSB2.channelGroups[PioneerDDJSB2.deckSwitchTable[group]];
    if (PioneerDDJSB2.scratchMode[deck]) {
        engine.scratchTick(deck + 1, PioneerDDJSB2.getJogWheelDelta(value));
    } else {
        PioneerDDJSB2.pitchBendFromJog(PioneerDDJSB2.deckSwitchTable[group], PioneerDDJSB2.getJogWheelDelta(value));
    }
};

PioneerDDJSB2.jogPlatterTickShift = function(channel, control, value, status, group) {
    var deck = PioneerDDJSB2.channelGroups[PioneerDDJSB2.deckSwitchTable[group]];
    if (PioneerDDJSB2.scratchMode[deck]) {
        engine.scratchTick(deck + 1, PioneerDDJSB2.getJogWheelDelta(value));
    } else {
        PioneerDDJSB2.pitchBendFromJog(
            PioneerDDJSB2.deckSwitchTable[group],
            PioneerDDJSB2.getJogWheelDelta(value) * PioneerDDJSB2.jogwheelShiftMultiplier
        );
    }
};

PioneerDDJSB2.jogTouch = function(channel, control, value, status, group) {
    var deck = PioneerDDJSB2.channelGroups[PioneerDDJSB2.deckSwitchTable[group]];

    if (PioneerDDJSB2.scratchMode[deck]) {
        if (value) {
            PioneerDDJSB2.slipStart(PioneerDDJSB2.deckSwitchTable[group]);
            engine.scratchEnable(
                deck + 1,
                PioneerDDJSB2.scratchSettings.jogResolution,
                PioneerDDJSB2.scratchSettings.vinylSpeed,
                PioneerDDJSB2.scratchSettings.alpha,
                PioneerDDJSB2.scratchSettings.beta,
                true
            );
        } else {
            // In slip mode: back on the beat at once instead of a ramp
            const slipping = PioneerDDJSB2.slipModeOn[deck];
            engine.scratchDisable(deck + 1, !slipping);
            PioneerDDJSB2.slipEnd(PioneerDDJSB2.deckSwitchTable[group]);
        }
    }
};

PioneerDDJSB2.toggleScratch = function(channel, control, value, status, group) {
    var deck = PioneerDDJSB2.channelGroups[group];
    if (value) {
        PioneerDDJSB2.scratchMode[deck] = !PioneerDDJSB2.scratchMode[deck];
        if (!PioneerDDJSB2.invertVinylSlipButton) {
            PioneerDDJSB2.nonPadLedControl(deck, PioneerDDJSB2.nonPadLeds.vinyl, PioneerDDJSB2.scratchMode[deck]);
            if (!PioneerDDJSB2.slipReturns) {
                PioneerDDJSB2.nonPadLedControl(deck, PioneerDDJSB2.nonPadLeds.shiftVinyl, PioneerDDJSB2.scratchMode[deck]);
            }
        }
        if (!PioneerDDJSB2.scratchMode[deck]) {
            engine.scratchDisable(deck + 1, true);
        }
    }
};

PioneerDDJSB2.pitchBendFromJog = function(channel, movement) {
    var group = (typeof channel === "string" ? channel : "[Channel" + channel + 1 + "]");

    engine.setValue(group, "jog", movement / 5 * PioneerDDJSB2.jogwheelSensitivity);
};


///////////////////////////////////////////////////////////////
//                        ROTARY SELECTOR                    //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.rotarySelectorChanged = false; // new for DDJ-SB2

PioneerDDJSB2.getRotaryDelta = function(value) {
    var delta = 0x40 - Math.abs(0x40 - value),
        isCounterClockwise = value > 0x40;

    if (isCounterClockwise) {
        delta *= -1;
    }
    return delta;
};

PioneerDDJSB2.rotarySelector = function(channel, control, value, _status) {
    var delta = PioneerDDJSB2.getRotaryDelta(value);
    engine.setValue("[Playlist]", "SelectTrackKnob", delta);

    PioneerDDJSB2.rotarySelectorChanged = true;
};

PioneerDDJSB2.shiftedRotarySelector = function(channel, control, value, _status) {
    var delta = PioneerDDJSB2.getRotaryDelta(value),
        f = (delta > 0 ? "SelectNextPlaylist" : "SelectPrevPlaylist");

    engine.setValue("[Playlist]", f, Math.abs(delta));
};

PioneerDDJSB2.rotarySelectorClick = function(channel, control, value, _status) {
    if (PioneerDDJSB2.rotarySelectorChanged === true) {
        if (value) {
            engine.setValue("[PreviewDeck1]", "LoadSelectedTrackAndPlay", true);
        } else {
            if (PioneerDDJSB2.jumpPreviewEnabled) {
                engine.setValue("[PreviewDeck1]", "playposition", PioneerDDJSB2.jumpPreviewPosition);
            }
            PioneerDDJSB2.rotarySelectorChanged = false;
        }
    } else {
        if (value) {
            engine.setValue("[PreviewDeck1]", "stop", 1);
        } else {
            PioneerDDJSB2.rotarySelectorChanged = true;
        }
    }
};

PioneerDDJSB2.rotarySelectorShiftedClick = function(channel, control, value, _status) {
    if (value) {
        engine.setValue("[Playlist]", "ToggleSelectedSidebarItem", 1);
    }
};


///////////////////////////////////////////////////////////////
//                             FX                            //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.EffectUnit = function(unitNumber) {
    var eu = this;
    this.group = "[EffectRack1_EffectUnit" + unitNumber + "]";
    engine.setValue(this.group, "show_focus", 1);

    this.EffectButton = function(buttonNumber) {
        this.buttonNumber = buttonNumber;

        this.group = eu.group;
        this.midi = [0x93 + unitNumber, 0x46 + buttonNumber];

        components.Button.call(this);
    };
    this.EffectButton.prototype = new components.Button({
        input: function(channel, control, value, status) {
            if (this.isPress(channel, control, value, status)) {
                this.isLongPressed = false;
                this.longPressTimer = engine.beginTimer(this.longPressTimeout, () => {
                    var effectGroup = "[EffectRack1_EffectUnit" + unitNumber + "_Effect" + this.buttonNumber + "]";
                    script.toggleControl(effectGroup, "enabled");
                    this.isLongPressed = true;
                }, true);
            } else {
                if (!this.isLongPressed) {
                    var focusedEffect = engine.getValue(eu.group, "focused_effect");
                    if (focusedEffect === this.buttonNumber) {
                        engine.setValue(eu.group, "focused_effect", 0);
                    } else {
                        engine.setValue(eu.group, "focused_effect", this.buttonNumber);
                    }
                }
                this.isLongPressed = false;
                engine.stopTimer(this.longPressTimer);
            }
        },
        outKey: "focused_effect",
        output: function(value, _group, _control) {
            this.send((value === this.buttonNumber) ? this.on : this.off);
        },
        // The SHIFT LEDs belong to the beat buttons (beatButton)
        sendShifted: false,
    });

    this.button = [];
    for (var i = 1; i <= 3; i++) {
        this.button[i] = new this.EffectButton(i);

        var effectGroup = "[EffectRack1_EffectUnit" + unitNumber + "_Effect" + i + "]";
        engine.softTakeover(effectGroup, "meta", true);
        engine.softTakeover(eu.group, "mix", true);
    }

    // SHIFT + FX buttons: the beat time of this unit's effects (echo delay,
    // flanger/phaser period, ...): 1 = half, 2 = back to the default,
    // 3 = double. Lit while pressed.
    const beatActions = ["beats_halve", "beats_reset", "beats_double"];
    this.beatButton = [];
    for (let r = 1; r <= 3; r++) {
        this.beatButton[r] = new components.Button({
            midi: [0x93 + unitNumber, 0x62 + r],
            group: eu.group,
            action: beatActions[r - 1],
            input: function(channel, control, value, status, _group) {
                const pressed = this.isPress(channel, control, value, status);
                this.send(pressed ? this.on : this.off);
                if (!pressed) {
                    return;
                }
                const unit = this.group.slice(0, -1); // "[EffectRack1_EffectUnitN"
                for (let e = 1; e <= 3; e++) {
                    script.triggerControl(unit + "_Effect" + e + "]", this.action);
                }
            },
        });
    }

    // SHIFT + FX knob: the unit's super knob (all its effects' meta knobs)
    this.superKnob = new components.Pot({
        group: eu.group,
        inKey: "super1",
        max: 0x3FFF,
    });

    this.knob = new components.Pot({
        unshift: function() {
            this.input = function(channel, control, value, _status) {
                value = (this.MSB << 7) + value;

                var focusedEffect = engine.getValue(eu.group, "focused_effect");
                if (focusedEffect === 0) {
                    engine.setParameter(eu.group, "mix", value / this.max);
                } else {
                    var effectGroup = "[EffectRack1_EffectUnit" + unitNumber + "_Effect" + focusedEffect + "]";
                    engine.setParameter(effectGroup, "meta", value / this.max);
                }
            };
        },
    });

    this.knobSoftTakeoverHandler = engine.makeConnection(eu.group, "focused_effect", function(value, _group, _control) {
        if (value === 0) {
            engine.softTakeoverIgnoreNextValue(eu.group, "mix");
        } else {
            var effectGroup = "[EffectRack1_EffectUnit" + unitNumber + "_Effect" + value + "]";
            engine.softTakeoverIgnoreNextValue(effectGroup, "meta");
        }
    }.bind(this));
};


///////////////////////////////////////////////////////////////
//          BRAKE, STEM PADS AND PHRASE NAVIGATION           //
///////////////////////////////////////////////////////////////

PioneerDDJSB2.stemConnections = {};
PioneerDDJSB2.soloedStem = {};
PioneerDDJSB2.bankLedState = {};
// Stem pad held down (0-3) per deck, and whether FILTER was turned meanwhile
PioneerDDJSB2.heldStemPad = {};
PioneerDDJSB2.heldStemTurned = {};
// Bar loop length (bars) the pads started, 0 = none
PioneerDDJSB2.activeBarLoop = {};
// Slicer pads held per deck
PioneerDDJSB2.slicerHeld = {};
// Blink phase for LEDs that blink (toggled every 125 ms)
PioneerDDJSB2.blinkOn = false;
PioneerDDJSB2.ledCache = {};

// SHIFT + PLAY: slow down to a stop, or spin back up when stopped / braking.
// The deck's own brake control does the work, so the skin's brake button
// and this one share the same state.
PioneerDDJSB2.brakeOrSoftStart = function(group) {
    script.triggerControl(group, "brake");
};

PioneerDDJSB2.stemGroup = function(group, stemNumber) {
    return group.substring(0, group.length - 1) + "_Stem" + stemNumber + "]";
};

PioneerDDJSB2.stemPadsActive = function(group) {
    return PioneerDDJSB2.stemPads && engine.getValue(group, "stem_count") > 0;
};

// Quick effect (filter) of one stem; pad 0-3
PioneerDDJSB2.stemQuickEffectGroup = function(group, pad) {
    return "[QuickEffectRack1_" + PioneerDDJSB2.stemGroup(group, pad + 1) + "]";
};

// Stems audible now (bit 0 = stem 1), or the change still waiting for the bar
PioneerDDJSB2.audibleStemMask = function(group) {
    const pending = engine.getValue(group, "stem_mask_pending");
    if (pending >= 0) {
        return pending;
    }
    let mask = 0;
    for (let stem = 1; stem <= 4; stem++) {
        if (engine.getValue(PioneerDDJSB2.stemGroup(group, stem), "mute") === 0) {
            mask |= 1 << (stem - 1);
        }
    }
    return mask;
};

// Make exactly the stems in mask audible: on the next downbeat
// (stemsOnBar) or right away
PioneerDDJSB2.setStemMask = function(group, mask) {
    if (PioneerDDJSB2.stemsOnBar) {
        engine.setValue(group, "stem_mask_on_bar", mask);
    } else {
        for (let stem = 1; stem <= 4; stem++) {
            engine.setValue(PioneerDDJSB2.stemGroup(group, stem), "mute", (mask >> (stem - 1)) & 1 ? 0 : 1);
        }
    }
};

PioneerDDJSB2.updateCueLoopPadLeds = function(group) {
    let pad;
    if (PioneerDDJSB2.stemPadsActive(group)) {
        const pending = engine.getValue(group, "stem_mask_pending");
        for (pad = 0; pad < 4; pad++) {
            const playing = engine.getValue(PioneerDDJSB2.stemGroup(group, pad + 1), "mute") === 0;
            let on = playing;
            // Changing on the next bar: blink
            if (pending >= 0 && (((pending >> pad) & 1) === 1) !== playing) {
                on = PioneerDDJSB2.blinkOn;
            }
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, pad, false, on);
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, pad, true,
                PioneerDDJSB2.soloedStem[group] === pad + 1);
        }
    } else {
        const kills = ["filterLowKill", "filterMidKill", "filterHighKill", "mute"];
        for (pad = 0; pad < 4; pad++) {
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, pad, false,
                engine.getValue(group, kills[pad]));
            PioneerDDJSB2.padLedControl(group, PioneerDDJSB2.ledGroups.manualLoop, true, pad, true, false);
        }
    }
};

PioneerDDJSB2.soloStem = function(group, stemNumber) {
    if (PioneerDDJSB2.soloedStem[group] === stemNumber) {
        // Second press: everything back on
        PioneerDDJSB2.setStemMask(group, 0xF);
        PioneerDDJSB2.soloedStem[group] = 0;
    } else {
        PioneerDDJSB2.setStemMask(group, 1 << (stemNumber - 1));
        PioneerDDJSB2.soloedStem[group] = stemNumber;
    }
    PioneerDDJSB2.updateCueLoopPadLeds(group);
};

// CUE LOOP pad mode: pads 0x60-0x63, SHIFT + pads 0x68-0x6B.
PioneerDDJSB2.cueLoopPad = function(channel, control, value, status, group) {
    const deckGroup = PioneerDDJSB2.deckSwitchTable[group];
    const pad = control & 0x03;
    const shifted = (control & 0x08) !== 0;

    if (PioneerDDJSB2.stemPadsActive(deckGroup)) {
        // Mute acts on release: holding a pad and turning FILTER filters that
        // stem instead. Releases are matched by pad, because the controller
        // sends them on the SHIFT layer if SHIFT went down meanwhile.
        if (!value) {
            if (PioneerDDJSB2.heldStemPad[deckGroup] !== pad) {
                return;
            }
            delete PioneerDDJSB2.heldStemPad[deckGroup];
            if (!PioneerDDJSB2.heldStemTurned[deckGroup]) {
                PioneerDDJSB2.setStemMask(deckGroup,
                    PioneerDDJSB2.audibleStemMask(deckGroup) ^ (1 << pad));
                PioneerDDJSB2.soloedStem[deckGroup] = 0;
            }
            return;
        }
        if (shifted) {
            PioneerDDJSB2.soloStem(deckGroup, pad + 1);
        } else {
            PioneerDDJSB2.heldStemPad[deckGroup] = pad;
            PioneerDDJSB2.heldStemTurned[deckGroup] = false;
        }
        return;
    }

    // Original behaviour without stems
    if (shifted) {
        // Like the knobs: decks 1/3 use effect unit 1, decks 2/4 unit 2
        const unit = PioneerDDJSB2.channelGroups[deckGroup] % 2 === 0 ? 1 : 2;
        const keys = ["prev_chain", "next_chain"];
        if (pad < 2) {
            engine.setValue("[EffectRack1_EffectUnit" + unit + "]", keys[pad], value ? 1 : 0);
        }
        return;
    }
    const kills = ["filterLowKill", "filterMidKill", "filterHighKill", "mute"];
    if (pad < 3) {
        engine.setValue(deckGroup, kills[pad], value ? 1 : 0);
    } else {
        engine.setValue(deckGroup, "mute", value ? 1 : 0);
    }
};

// BANK pad mode: pads 0x70-0x73.
PioneerDDJSB2.bankPad = function(channel, control, value, status, group) {
    const deckGroup = PioneerDDJSB2.deckSwitchTable[group];
    const pad = control & 0x03;
    if (!PioneerDDJSB2.phraseBankPads) {
        // Original behaviour: load the selected track into sampler 1-4
        if (value) {
            engine.setValue("[Sampler" + (pad + 1) + "]", "LoadSelectedTrack", 1);
        }
        return;
    }
    if (!value) {
        return;
    }
    const keys = ["section_jump_backward", "section_jump_forward",
        "phrase_jump_backward", "phrase_jump_forward"];
    script.triggerControl(deckGroup, keys[pad]);
};

// Send a pad LED only when it changes (some inputs update many times a second)
PioneerDDJSB2.padLedCached = function(group, groupNumber, shiftGroup, pad, shift, on) {
    const key = group + groupNumber + shiftGroup + pad + shift;
    on = !!on;
    if (PioneerDDJSB2.ledCache[key] === on) {
        return;
    }
    PioneerDDJSB2.ledCache[key] = on;
    PioneerDDJSB2.padLedControl(group, groupNumber, shiftGroup, pad, shift, on);
};

// BANK pads: lit when the track has structure. In the last 4 bars before a
// new phrase they count down (4 pads, 3, 2, then pad 1 blinks on the beat).
PioneerDDJSB2.updateBankPadLeds = function(group) {
    const loaded = engine.getValue(group, "structure_loaded") > 0;
    if (PioneerDDJSB2.phraseBankPads) {
        const until = engine.getValue(group, "beats_until_phrase");
        const beatsPerBar = 4;
        const barsLeft = Math.ceil(until / beatsPerBar);
        const countdown = loaded && until > 0 && barsLeft <= 4;
        for (let pad = 0; pad < 4; pad++) {
            let on = loaded;
            if (countdown) {
                on = pad < barsLeft;
                if (barsLeft === 1 && pad === 0) {
                    on = engine.getValue(group, "beat_distance") < 0.5;
                }
            }
            PioneerDDJSB2.padLedCached(group, PioneerDDJSB2.ledGroups.sampler, true, pad, false, on);
        }
    }
    if (PioneerDDJSB2.performancePads) {
        // SHIFT + BANK: phrase sync / start on phrase (blinks while waiting) /
        // phrase restart / phrase loop
        const armed = engine.getValue(group, "play_on_phrase") > 0;
        const cueSync = engine.getValue(group, "cue_sync") > 0 ||
            (PioneerDDJSB2.cueSyncPick !== null && PioneerDDJSB2.cueSyncPick.group === group);
        for (let pad = 0; pad < 4; pad++) {
            let on = loaded;
            if ((pad === 1 && armed) || (pad === 2 && cueSync)) {
                on = PioneerDDJSB2.blinkOn;
            }
            PioneerDDJSB2.padLedCached(group, PioneerDDJSB2.ledGroups.sampler, true, pad, true, on);
        }
    }
};

// MANUAL LOOP pads (bar loops): lit = that loop is on.
// SHIFT layer (slicer): the pad of the beat that's playing.
PioneerDDJSB2.updateBarLoopLeds = function(group) {
    if (!PioneerDDJSB2.performancePads) {
        return;
    }
    const looping = engine.getValue(group, "loop_enabled") > 0;
    const bars = looping ? PioneerDDJSB2.activeBarLoop[group] : 0;
    [1, 2, 4, 8].forEach(function(length, pad) {
        PioneerDDJSB2.padLedCached(group, PioneerDDJSB2.ledGroups.manualLoop, false, pad, false,
            bars === length);
    });
    const beat = engine.getValue(group, "beat_in_bar");
    for (let pad = 0; pad < 4; pad++) {
        PioneerDDJSB2.padLedCached(group, PioneerDDJSB2.ledGroups.manualLoop, false, pad, true,
            beat === pad + 1);
    }
};

// MANUAL LOOP mode pads 0x20-0x23 and SHIFT 0x28-0x2B
PioneerDDJSB2.manualLoopPad = function(channel, control, value, status, group) {
    const pad = control & 0x03;
    const shifted = (control & 0x08) !== 0;
    const hasStructure = engine.getValue(group, "structure_loaded") > 0;
    if (!PioneerDDJSB2.performancePads) {
        const classic = shifted
            ? [PioneerDDJSB2.loopMoveBackButton, PioneerDDJSB2.loopMoveForwardButton, null,
                PioneerDDJSB2.loopDoubleButton]
            : [PioneerDDJSB2.loopInButton, PioneerDDJSB2.loopOutButton, PioneerDDJSB2.loopExitButton,
                PioneerDDJSB2.loopHalveButton];
        if (classic[pad]) {
            classic[pad](channel, control, value, status, group);
        }
        return;
    }
    // SLICER pads held on this deck: pad -> true. Releases are matched by pad
    // (they arrive on the plain layer if SHIFT was let go first).
    const slices = PioneerDDJSB2.slicerHeld[group] = PioneerDDJSB2.slicerHeld[group] || {};
    if (!value) {
        if (slices[pad]) {
            delete slices[pad];
            if (Object.keys(slices).length === 0) {
                // slip mode: carry on where the track would have been
                engine.setValue(group, "slip_enabled", 0);
            }
        }
        return;
    }
    if (!shifted) {
        // BAR LOOPS: 1, 2, 4, 8 bars from the downbeat; the same pad again ends it
        const bars = [1, 2, 4, 8][pad];
        // (the engine applies the change after this returns: decide from the old state)
        const ending = PioneerDDJSB2.activeBarLoop[group] === bars &&
            engine.getValue(group, "loop_enabled") > 0;
        if (!ending && engine.getValue(group, "loop_enabled") === 0) {
            PioneerDDJSB2.slipStart(group); // the loop's end returns (slipLoopEnded)
        }
        if (hasStructure) {
            engine.setValue(group, "bar_loop", bars);
        } else {
            // No bar data: a normal beat loop of that length
            script.toggleControl(group, "beatloop_" + (bars * 4) + "_toggle");
        }
        PioneerDDJSB2.activeBarLoop[group] = ending ? 0 : bars;
        PioneerDDJSB2.updateBarLoopLeds(group);
        return;
    }
    // SLICER: play from beat N of this bar while held
    const beat = engine.getValue(group, "beat_in_bar");
    if (!hasStructure || beat === 0) {
        return;
    }
    if (Object.keys(slices).length === 0) {
        engine.setValue(group, "slip_enabled", 1);
    }
    slices[pad] = true;
    const delta = (pad + 1) - beat;
    if (delta !== 0) {
        engine.setValue(group, "beatjump", delta);
    }
};

// SHIFT + BANK pads 0x78-0x7B
PioneerDDJSB2.shiftBankPad = function(channel, control, value, status, group) {
    const pad = control & 0x03;
    if (!PioneerDDJSB2.performancePads) {
        // Classic: eject sampler 1-4
        engine.setValue("[Sampler" + (pad + 1) + "]", "eject", value ? 1 : 0);
        return;
    }
    if (!value) {
        return;
    }
    switch (pad) {
    case 0:
        script.triggerControl(group, "phrase_sync");
        break;
    case 1:
        script.toggleControl(group, "play_on_phrase");
        break;
    case 2:
        PioneerDDJSB2.cueSyncButton(group);
        break;
    case 3:
        script.triggerControl(group, "phrase_loop");
        break;
    }
    PioneerDDJSB2.updateBankPadLeds(group);
};

// CUE SYNC (SHIFT + BANK pad 3): make a cue of this deck land on a cue of the
// playing deck. Press: pick mode (pad blinks). Then optionally a HOT CUE pad
// on this deck (my cue; default: my first DROP), then a HOT CUE pad on the
// other deck (their cue) - that arms it. Pressing pad 3 again instead arms
// with both DROPs (double drop); pressing it while armed cancels.
PioneerDDJSB2.cueSyncPick = null; // {group, mine}

PioneerDDJSB2.cueSyncButton = function(group) {
    if (engine.getValue(group, "cue_sync") > 0) {
        engine.setValue(group, "cue_sync", 0); // armed: cancel
        PioneerDDJSB2.cueSyncPick = null;
    } else if (PioneerDDJSB2.cueSyncPick && PioneerDDJSB2.cueSyncPick.group === group) {
        PioneerDDJSB2.armCueSync(group, PioneerDDJSB2.cueSyncPick.mine, 0, 0);
    } else {
        PioneerDDJSB2.cueSyncPick = {group: group, mine: 0};
    }
    PioneerDDJSB2.updateBankPadLeds(group);
};

// A HOT CUE pad while picking: returns true if it was used for the pick
PioneerDDJSB2.pickCueForSync = function(group, hotCue, value) {
    const pick = PioneerDDJSB2.cueSyncPick;
    if (!value) {
        return true; // releases of picking presses don't trigger cues either
    }
    if (group === pick.group) {
        pick.mine = hotCue;
        return true;
    }
    PioneerDDJSB2.armCueSync(pick.group, pick.mine, hotCue,
        PioneerDDJSB2.channelGroups[group] + 1);
    return true;
};

PioneerDDJSB2.armCueSync = function(group, mine, theirs, theirDeck) {
    engine.setValue(group, "cue_sync_mine", mine);
    engine.setValue(group, "cue_sync_theirs", theirs);
    engine.setValue(group, "cue_sync_deck", theirDeck);
    engine.setValue(group, "cue_sync", 1);
    PioneerDDJSB2.cueSyncPick = null;
    PioneerDDJSB2.updateBankPadLeds(group);
};

// Every 125 ms: LEDs that blink
PioneerDDJSB2.blinkTick = function() {
    PioneerDDJSB2.blinkOn = !PioneerDDJSB2.blinkOn;
    for (let deck = 1; deck <= 4; deck++) {
        const group = "[Channel" + deck + "]";
        // PLAY blinks while the brake (or spin-up) runs
        if (engine.getValue(group, "brake_active") > 0) {
            PioneerDDJSB2.nonPadLedControl(group, PioneerDDJSB2.nonPadLeds.play, PioneerDDJSB2.blinkOn);
            PioneerDDJSB2.braking[group] = true;
        } else if (PioneerDDJSB2.braking[group]) {
            PioneerDDJSB2.braking[group] = false;
            PioneerDDJSB2.deck[deck].playButton.trigger(); // back to the play state
        }
        if (engine.getValue(group, "stem_mask_pending") >= 0) {
            PioneerDDJSB2.updateCueLoopPadLeds(group);
        }
        if (engine.getValue(group, "play_on_phrase") > 0 || engine.getValue(group, "cue_sync") > 0 ||
                (PioneerDDJSB2.cueSyncPick && PioneerDDJSB2.cueSyncPick.group === group)) {
            PioneerDDJSB2.updateBankPadLeds(group);
        }
    }
};
PioneerDDJSB2.braking = {};

PioneerDDJSB2.initStemsAndPhrases = function(group) {
    if (PioneerDDJSB2.stemConnections[group]) {
        return;
    }
    const connections = [];
    connections.push(engine.makeConnection(group, "stem_count", function() {
        PioneerDDJSB2.soloedStem[group] = 0;
        PioneerDDJSB2.updateCueLoopPadLeds(group);
    }));
    for (let stem = 1; stem <= 4; stem++) {
        const conn = engine.makeConnection(PioneerDDJSB2.stemGroup(group, stem), "mute", function() {
            PioneerDDJSB2.updateCueLoopPadLeds(group);
        });
        if (conn) {
            connections.push(conn);
        }
        // Stem filters (hold stem pad + FILTER) pick up without jumps
        engine.softTakeover(PioneerDDJSB2.stemQuickEffectGroup(group, stem - 1), "super1", true);
    }
    const stemPending = engine.makeConnection(group, "stem_mask_pending", function() {
        PioneerDDJSB2.updateCueLoopPadLeds(group);
    });
    if (stemPending) {
        connections.push(stemPending);
    }
    ["beat_in_bar", "loop_enabled"].forEach(function(key) {
        const conn = engine.makeConnection(group, key, function(value) {
            PioneerDDJSB2.updateBarLoopLeds(group);
            // SLIP MODE: a loop ended (any way): carry on where the track would be
            if (key === "loop_enabled" && value === 0 &&
                    engine.getValue(group, "slip_enabled") > 0 &&
                    Object.keys(PioneerDDJSB2.slicerHeld[group] || {}).length === 0) {
                PioneerDDJSB2.slipEnd(group);
            }
        });
        if (conn) {
            connections.push(conn);
        }
    });
    if (PioneerDDJSB2.brakeSeconds !== null) {
        engine.setValue(group, "brake_time", PioneerDDJSB2.brakeSeconds);
    }
    if (PioneerDDJSB2.softStartSeconds !== null) {
        engine.setValue(group, "softstart_time", PioneerDDJSB2.softStartSeconds);
    }
    ["structure_loaded", "beats_until_phrase", "beat_distance", "play_on_phrase", "cue_sync"].forEach(function(key) {
        const conn = engine.makeConnection(group, key, function() {
            PioneerDDJSB2.updateBankPadLeds(group);
        });
        if (conn) {
            connections.push(conn);
        }
    });
    PioneerDDJSB2.stemConnections[group] = connections;
    PioneerDDJSB2.updateCueLoopPadLeds(group);
    PioneerDDJSB2.updateBankPadLeds(group);
    PioneerDDJSB2.updateBarLoopLeds(group);
};

// Exercise the Pioneer DDJ-SB2 (Stems) mapping without the controller or
// Mixxx: a stand-in `engine` and `midi` record what the script does.
//
//   node tools/sb2-mapping-test/test.js
//
// Loads the same files as Mixxx (common-controller-scripts, lodash,
// midi-components, the mapping), checks that every function named in the
// XML exists, then plays MIDI into the handlers and checks the controls and
// LEDs that come out.

"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const controllers = path.join(__dirname, "..", "..", "res", "controllers");

// --- stand-in engine ---------------------------------------------------------
const values = new Map();
const params = new Map();
const connections = new Map(); // "group,key" -> [callbacks]
const timers = new Map();
let nextTimer = 1;
let log = []; // ["set", group, key, value] / ["param", ...] / ["midi", status, no, value]

const k = (group, key) => group + "," + key;
const defaults = {"rate_dir": 1, "stem_mask_pending": -1};

function notify(group, key, value) {
    for (const cb of connections.get(k(group, key)) || []) {
        cb(value, group, key);
    }
}

global.engine = {
    getValue(group, key) {
        const v = values.get(k(group, key));
        return v !== undefined ? v : (defaults[key] !== undefined ? defaults[key] : 0);
    },
    setValue(group, key, value) {
        value = Number(value);
        log.push(["set", group, key, value]);
        values.set(k(group, key), value);
        notify(group, key, value);
    },
    getParameter(group, key) {
        const v = params.get(k(group, key));
        return v !== undefined ? v : 0.5;
    },
    setParameter(group, key, value) {
        log.push(["param", group, key, value]);
        params.set(k(group, key), value);
    },
    makeConnection(group, key, cb) {
        const list = connections.get(k(group, key)) || [];
        list.push(cb);
        connections.set(k(group, key), list);
        return {
            disconnect() {
                list.splice(list.indexOf(cb), 1);
            },
            trigger() {
                cb(global.engine.getValue(group, key), group, key);
            },
            isConnected: true,
        };
    },
    connectControl(group, key, fn, disconnect) {
        if (disconnect) {
            return;
        }
        const cb = typeof fn === "function" ? fn : vm.runInThisContext(fn);
        return this.makeConnection(group, key, cb);
    },
    trigger(group, key) {
        notify(group, key, this.getValue(group, key));
    },
    beginTimer(ms, cb, oneShot) {
        const id = nextTimer++;
        timers.set(id, {ms, cb, oneShot: !!oneShot});
        return id;
    },
    stopTimer(id) {
        timers.delete(id);
    },
    softTakeover() {},
    softTakeoverIgnoreNextValue() {},
    scratchEnable() {},
    scratchDisable() {},
    scratchTick() {},
    isScratching() {
        return false;
    },
    brake() {},
    spinback() {},
    softStart() {},
    log() {},
    getSetting() {
        return undefined;
    },
};
global.midi = {
    sendShortMsg(status, no, value) {
        log.push(["midi", status, no, value]);
    },
    sendSysexMsg() {},
};
global.console = console;

for (const file of ["common-controller-scripts.js", "lodash.mixxx.js",
    "midi-components-0.0.js", "Pioneer-DDJ-SB2-Stems-scripts.js"]) {
    vm.runInThisContext(fs.readFileSync(path.join(controllers, file), "utf8"), {filename: file});
}
global.print = () => {};
const S = global.PioneerDDJSB2;

// --- helpers --------------------------------------------------------------------
const set = (group, key, value) => values.set(k(group, key), value);
const get = (group, key) => global.engine.getValue(group, key);
const sets = (group, key) => log.filter((e) => e[0] === "set" && e[1] === group && e[2] === key)
    .map((e) => e[3]);
const leds = (status, no) => log.filter((e) => e[0] === "midi" && e[1] === status && e[2] === no)
    .map((e) => e[3]);
const runTimer = (id) => {
    const t = timers.get(id);
    t.cb();
    if (t.oneShot) {
        timers.delete(id);
    }
};
const D1 = "[Channel1]";
let failures = 0;
function test(name, fn) {
    log = [];
    try {
        fn();
        console.log("ok   " + name);
    } catch (e) {
        failures++;
        console.log("FAIL " + name + "\n     " + (e.stack || e).toString().split("\n").slice(0, 3).join("\n     "));
    }
}

// --- tests ------------------------------------------------------------------------
test("init runs", () => {
    S.init("test");
});

test("every function named in the XML exists", () => {
    const xml = fs.readFileSync(path.join(controllers, "Pioneer-DDJ-SB2-Stems.midi.xml"), "utf8");
    const keys = new Set([...xml.matchAll(/<key>(PioneerDDJSB2\.[^<]+)<\/key>/g)].map((m) => m[1]));
    const missing = [...keys].filter((key) => typeof vm.runInThisContext(key) !== "function");
    assert.deepStrictEqual(missing, []);
});

// Deck 1 has a track with structure and 4 stems
set(D1, "structure_loaded", 1);
set(D1, "stem_count", 4);

test("bar loop pads: 1/2/4/8 bars, same pad again ends it, LED follows", () => {
    S.manualLoopPad(0, 0x22, 0x7F, 0x97, D1); // pad 3 = 4 bars
    S.manualLoopPad(0, 0x22, 0x00, 0x97, D1);
    assert.deepStrictEqual(sets(D1, "bar_loop"), [4]);
    global.engine.setValue(D1, "loop_enabled", 1); // the engine starts the loop
    assert.deepStrictEqual(leds(0x97, 0x22).slice(-1), [0x7F]);
    S.manualLoopPad(0, 0x22, 0x7F, 0x97, D1); // again: ends it
    global.engine.setValue(D1, "loop_enabled", 0);
    assert.deepStrictEqual(sets(D1, "bar_loop"), [4, 4]);
    assert.deepStrictEqual(leds(0x97, 0x22).slice(-1), [0x00]);
});

test("slicer: jumps to beat N with slip; release on the plain layer ends slip", () => {
    set(D1, "beat_in_bar", 3);
    S.manualLoopPad(0, 0x28, 0x7F, 0x97, D1); // SHIFT pad 1 = beat 1
    assert.deepStrictEqual(sets(D1, "slip_enabled"), [1]);
    assert.deepStrictEqual(sets(D1, "beatjump"), [-2]);
    S.manualLoopPad(0, 0x20, 0x00, 0x97, D1); // SHIFT let go first
    assert.deepStrictEqual(sets(D1, "slip_enabled"), [1, 0]);
    assert.deepStrictEqual(sets(D1, "bar_loop"), []);
});

test("stem pad tap: mute on the bar via stem_mask_on_bar", () => {
    S.cueLoopPad(0, 0x60, 0x7F, 0x97, D1);
    assert.deepStrictEqual(sets(D1, "stem_mask_on_bar"), []); // nothing on press
    S.cueLoopPad(0, 0x60, 0x00, 0x97, D1);
    assert.deepStrictEqual(sets(D1, "stem_mask_on_bar"), [0xE]); // drums off
});

test("stem pad hold + FILTER: filters that stem only, no mute", () => {
    S.cueLoopPad(0, 0x61, 0x7F, 0x97, D1); // bass
    const knob = S.deck[1].quickEffectKnob;
    knob.inputMSB(0, 0x17, 0x20, 0xB6, D1);
    knob.inputLSB(0, 0x37, 0x00, 0xB6, D1);
    // (midi-components sends an extra value on the very first message: look at the last)
    const filtered = log.filter((e) => e[0] === "param" && e[1] === "[QuickEffectRack1_[Channel1_Stem2]]");
    assert.ok(filtered.length >= 1);
    assert.ok(Math.abs(filtered[filtered.length - 1][3] - 0.25) < 0.01);
    assert.deepStrictEqual(log.filter((e) => e[1] === "[QuickEffectRack1_[Channel1]]"), []);
    S.cueLoopPad(0, 0x69, 0x00, 0x97, D1); // released on the SHIFT layer
    assert.deepStrictEqual(sets(D1, "stem_mask_on_bar"), []);
    knob.inputLSB(0, 0x37, 0x01, 0xB6, D1); // knob is the deck filter again
    assert.strictEqual(log.filter((e) => e[1] === "[QuickEffectRack1_[Channel1]]").length, 1);
});

test("SHIFT stem pad: solo on the bar, again = all back", () => {
    S.cueLoopPad(0, 0x6A, 0x7F, 0x97, D1);
    S.cueLoopPad(0, 0x6A, 0x7F, 0x97, D1);
    assert.deepStrictEqual(sets(D1, "stem_mask_on_bar"), [0x4, 0xF]);
});

test("pending stem change blinks", () => {
    set(D1, "stem_mask_pending", 0xE); // drums going off
    S.blinkTick();
    const first = leds(0x97, 0x60).slice(-1)[0];
    S.blinkTick();
    const second = leds(0x97, 0x60).slice(-1)[0];
    assert.notStrictEqual(first, second);
    set(D1, "stem_mask_pending", -1);
});

test("SHIFT + BANK pads: phrase sync, start on phrase, (cue sync), phrase loop", () => {
    for (let pad = 0; pad < 4; pad++) {
        S.shiftBankPad(0, 0x78 + pad, 0x7F, 0x97, D1);
    }
    assert.deepStrictEqual(sets(D1, "phrase_sync").slice(0, 1), [1]);
    assert.deepStrictEqual(sets(D1, "play_on_phrase"), [1]);
    assert.deepStrictEqual(sets(D1, "phrase_loop").slice(0, 1), [1]);
    S.cueSyncPick = null; // pad 3 started picking for cue sync
});

test("cue sync: pick my cue, then theirs on the other deck, arms; pads don't jump", () => {
    S.shiftBankPad(0, 0x7A, 0x7F, 0x97, D1); // SHIFT + BANK 3: pick mode
    S.hotCueButtons(0, 0x01, 0x7F, 0x97, D1); // my hot cue 2
    S.hotCueButtons(0, 0x01, 0x00, 0x97, D1);
    S.hotCueButtons(0, 0x02, 0x7F, 0x98, "[Channel2]"); // their hot cue 3
    assert.deepStrictEqual(sets(D1, "cue_sync_mine"), [2]);
    assert.deepStrictEqual(sets(D1, "cue_sync_theirs"), [3]);
    assert.deepStrictEqual(sets(D1, "cue_sync_deck"), [2]);
    assert.deepStrictEqual(sets(D1, "cue_sync"), [1]);
    assert.deepStrictEqual(log.filter((e) => e[0] === "set" && /hotcue_\d_activate/.test(e[2])), []);
    S.hotCueButtons(0, 0x00, 0x7F, 0x97, D1); // picking is over: cues work again
    assert.deepStrictEqual(sets(D1, "hotcue_1_activate"), [0x7F]);
    S.shiftBankPad(0, 0x7A, 0x7F, 0x97, D1); // armed: pad 3 cancels
    assert.deepStrictEqual(sets(D1, "cue_sync"), [1, 0]);
});

test("cue sync: pad 3 twice = double drop with both DROP cues", () => {
    S.shiftBankPad(0, 0x7A, 0x7F, 0x97, D1);
    S.shiftBankPad(0, 0x7A, 0x7F, 0x97, D1);
    assert.deepStrictEqual(sets(D1, "cue_sync_mine"), [0]);
    assert.deepStrictEqual(sets(D1, "cue_sync_theirs"), [0]);
    assert.deepStrictEqual(sets(D1, "cue_sync_deck"), [0]);
    assert.deepStrictEqual(sets(D1, "cue_sync"), [1]);
    set(D1, "cue_sync", 0);
});

test("BANK LEDs count down the last 4 bars", () => {
    S.ledCache = {}; // LEDs are only sent on change
    set(D1, "beats_until_phrase", 7); // 2 bars left
    S.updateBankPadLeds(D1);
    const pads = [0x70, 0x71, 0x72, 0x73].map((no) => leds(0x97, no).slice(-1)[0]);
    assert.deepStrictEqual(pads, [0x7F, 0x7F, 0x00, 0x00]);
    set(D1, "beats_until_phrase", 20);
    S.updateBankPadLeds(D1);
});

test("SYNC tap = next sync step; hold = sync lock on/off", () => {
    const sync = S.deck[1].syncButton;
    sync.input(0, 0x58, 0x7F, 0x90, D1);
    sync.input(0, 0x58, 0x00, 0x90, D1);
    assert.deepStrictEqual(sets(D1, "sync_step").slice(0, 1), [1]);
    assert.deepStrictEqual(sets(D1, "sync_enabled"), []);
    sync.input(0, 0x58, 0x7F, 0x90, D1); // hold
    runTimer(sync.longPressTimer);
    sync.input(0, 0x58, 0x00, 0x90, D1);
    assert.deepStrictEqual(sets(D1, "sync_enabled"), [1]);
    assert.deepStrictEqual(sets(D1, "sync_step").filter((v) => v === 1).length, 1);
    sync.input(0, 0x58, 0x7F, 0x90, D1); // hold again: lock off
    runTimer(sync.longPressTimer);
    sync.input(0, 0x58, 0x00, 0x90, D1);
    assert.deepStrictEqual(sets(D1, "sync_enabled"), [1, 0]);
});

test("SHIFT + TEMPO: key in semitones, picks up at the current key", () => {
    const deck = S.deck[1];
    deck.shiftButton(0, 0x3F, 0x7F, 0x90, D1);
    deck.keyFader.inputMSB(0, 0x05, 0x00, 0xB0, D1); // far end: not picked up yet
    deck.keyFader.inputLSB(0, 0x25, 0x00, 0xB0, D1);
    assert.deepStrictEqual(sets(D1, "pitch_adjust"), []);
    deck.keyFader.inputMSB(0, 0x05, 0x40, 0xB0, D1); // centre = current key 0
    deck.keyFader.inputLSB(0, 0x25, 0x00, 0xB0, D1);
    deck.keyFader.inputMSB(0, 0x05, 0x00, 0xB0, D1); // now it follows
    deck.keyFader.inputLSB(0, 0x25, 0x00, 0xB0, D1);
    assert.deepStrictEqual(sets(D1, "pitch_adjust"), [S.keyShiftRange]);
    deck.shiftButton(0, 0x3F, 0x00, 0x90, D1);
});

test("SHIFT + KEYLOCK glides tempo all the way to 0 and resets key", () => {
    set(D1, "rate", 0.1);
    S.shiftKeyLockButton(0, 0x60, 0x7F, 0x90, D1);
    const id = S.speedRateToNormalTimer[0];
    for (let i = 0; i < 100 && timers.has(id); i++) {
        runTimer(id);
    }
    assert.strictEqual(get(D1, "rate"), 0);
    assert.ok(!timers.has(id));
    assert.deepStrictEqual(sets(D1, "pitch_adjust").slice(-1), [0]);
});

test("SHIFT + FX buttons: beat time half / default / double; SHIFT + FX knob = super knob", () => {
    const fx = (e) => "[EffectRack1_EffectUnit1_Effect" + e + "]";
    S.effectUnit[1].beatButton[1].input(0, 0x63, 0x7F, 0x94, "");
    S.effectUnit[1].beatButton[1].input(0, 0x63, 0x00, 0x94, "");
    S.effectUnit[1].beatButton[2].input(0, 0x64, 0x7F, 0x94, "");
    S.effectUnit[1].beatButton[3].input(0, 0x65, 0x7F, 0x94, "");
    for (let e = 1; e <= 3; e++) {
        assert.deepStrictEqual(sets(fx(e), "beats_halve"), [1]);
        assert.deepStrictEqual(sets(fx(e), "beats_reset"), [1]);
        assert.deepStrictEqual(sets(fx(e), "beats_double"), [1]);
    }
    assert.deepStrictEqual(leds(0x94, 0x63), [0x7F, 0x00]); // lit while held, once per press
    S.effectUnit[1].superKnob.inputMSB(0, 0x00, 0x40, 0xB4, "");
    S.effectUnit[1].superKnob.inputLSB(0, 0x20, 0x00, 0xB4, "");
    const p = log.filter((e) => e[0] === "param" && e[2] === "super1" && e[1] === "[EffectRack1_EffectUnit1]");
    assert.ok(p.length >= 1);
    assert.ok(Math.abs(p[p.length - 1][3] - 0.5) < 0.01);
});

test("SHIFT + headphone CUE LED shows the other layer's deck", () => {
    global.engine.setValue("[Channel3]", "pfl", 1);
    assert.deepStrictEqual(leds(0x90, 0x68).slice(-1), [0x7F]); // deck 1's SHIFT LED
    assert.deepStrictEqual(leds(0x92, 0x54).slice(-1), [0x7F]); // deck 3's own LED
});

test("PLAY blinks while braking, then shows play again", () => {
    set(D1, "brake_active", 1);
    S.blinkTick();
    S.blinkTick();
    const blinks = leds(0x90, 0x0B);
    assert.ok(blinks.includes(0x7F) && blinks.includes(0x00));
    set(D1, "brake_active", 0);
    set(D1, "play_indicator", 1);
    log = [];
    S.blinkTick();
    assert.deepStrictEqual(leds(0x90, 0x0B).slice(-1), [0x7F]);
});

test("quantize LED on SHIFT + SYNC", () => {
    global.engine.setValue(D1, "quantize", 1);
    assert.deepStrictEqual(leds(0x90, 0x5C).slice(-1), [0x7F]);
});

console.log(failures ? `\n${failures} failed` : "\nall passed");
process.exit(failures ? 1 : 0);

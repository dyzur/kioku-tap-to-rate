// SPDX-License-Identifier: AGPL-3.0-or-later
// Tap simulation for the injected script, run by JavaScriptCore (JXA), the
// engine inside the WKWebView the reviewer page runs in.
//
//   osascript -l JavaScript tests/sim.js /path/to/tap_to_rate_script.js
//
// The script under test only uses window, document, navigator and pycmd, so
// a small stub of each is enough to fire touches at it and see which
// command it sends.

ObjC.import("Foundation");

// The script under test is injected into the page's <head>, before the one
// that defines pycmd, so pycmd is deliberately not a parameter here: it is
// a global this harness can remove and put back.
var TARGET = null;
pycmd = function (cmd) { if (TARGET) TARGET.commands.push(cmd); };

function readFile(path) {
    var text = $.NSString.stringWithContentsOfFileEncodingError(
        path, $.NSUTF8StringEncoding, null);
    if (!text.isNil()) return ObjC.unwrap(text);
    throw new Error("cannot read " + path);
}

var SOURCE = null;   // filled in by run()

// --- a page to fire touches at -------------------------------------------

function element(closest) {
    // `closest` answers as a real element would: the selector that matches
    // this element or an ancestor, else null.
    return {closest: function () { return closest || null; }};
}

var NOW = 1000;
Date.now = function () { return NOW; };

function Page(options) {
    options = options || {};
    var self = this;
    this.width = 1000;
    this.selection = "";
    this.zoom = 1;
    this.commands = [];
    this.handlers = {};

    this.window = {
        ontouchstart: null,
        innerWidth: this.width,
        visualViewport: {get scale() { return self.zoom; }},
        getSelection: function () { return self.selection; }
    };
    this.document = {
        addEventListener: function (type, handler) {
            (self.handlers[type] = self.handlers[type] || []).push(handler);
        }
    };
    this.navigator = {maxTouchPoints: options.touch === false ? 0 : 5};
    if (this.navigator.maxTouchPoints === 0) delete this.window.ontouchstart;
}

Page.prototype.load = function (config) {
    // Same script the reviewer gets; only the config is swapped.
    var src = SOURCE.replace(/var CFG = \{[\s\S]*?\};\n/, "var CFG = " + JSON.stringify(config) + ";\n");
    TARGET = this;
    var run = new Function("window", "document", "navigator", src);
    run(this.window, this.document, this.navigator);
    return this;
};

Page.prototype.fire = function (type, x, y, opts) {
    opts = opts || {};
    var touch = {clientX: x, clientY: y};
    var event = {
        target: opts.target || element(null),
        touches: [],
        changedTouches: [touch]
    };
    var fingers = opts.fingers === undefined ? 0 : opts.fingers;
    if (type === "touchstart") event.touches = fingers === 2 ? [touch, touch] : [touch];
    if (type === "touchmove") event.touches = fingers === 2 ? [touch, touch] : [touch];
    if (type === "touchend") event.touches = [];
    (this.handlers[type] || []).forEach(function (handler) { handler(event); });
};

// One tap: down, maybe a few moves, up.
Page.prototype.tap = function (x, y, opts) {
    opts = opts || {};
    this.fire("touchstart", x, y, opts);
    if (opts.dragTo) this.fire("touchmove", opts.dragTo[0], opts.dragTo[1], opts);
    if (opts.longPress) NOW += opts.longPress;
    this.fire("touchend", opts.endX === undefined ? x : opts.endX,
        opts.endY === undefined ? y : opts.endY, opts);
    return this.commands.slice();   // a snapshot: tests compare with JSON
};

Page.prototype.side = function (value) {
    this.window.__tapToRate.side(value);
    return this;
};

// --- the checks ----------------------------------------------------------

var failures = 0, checks = 0;

function check(name, actual, expected) {
    checks++;
    var ok = JSON.stringify(actual) === JSON.stringify(expected);
    if (!ok) failures++;
    console.log((ok ? "ok   " : "FAIL ") + name +
        (ok ? "" : "  (got " + JSON.stringify(actual) + ", wanted " + JSON.stringify(expected) + ")"));
}

var BASE = {
    enabled: true,
    question_tap_shows_answer: true,
    answer_left_ease: 1,
    answer_right_ease: 3,
    answer_middle_ease: 0,
    answer_middle_width: 0.25,
    tap_slop_px: 14,
    tap_max_ms: 600,
    cooldown_ms: 250,
    force_any_device: false
};

// Off until the page's own config.json is layered on top.

function config(overrides) {
    var cfg = JSON.parse(JSON.stringify(BASE));
    for (var key in overrides || {}) cfg[key] = overrides[key];
    return cfg;
}

function page(overrides) {
    return new Page().load(config(overrides));
}

function run(argv) {
    SOURCE = readFile(argv[0]);

    // --- the question side: a tap shows the answer
    check("question, tap in the middle shows the answer",
        page().tap(500, 400), ["ans"]);
    check("question, left edge shows the answer too",
        page().tap(20, 400), ["ans"]);
    check("question tap off in the config, tap does nothing",
        page({question_tap_shows_answer: false}).tap(500, 400), []);

    // --- the answer side: left Again, right Good
    check("answer, left half answers Again",
        page().side("answer").tap(200, 400), ["ease1"]);
    check("answer, right half answers Good",
        page().side("answer").tap(800, 400), ["ease3"]);
    check("answer, just left of the middle is Again",
        page().side("answer").tap(499, 400), ["ease1"]);
    check("answer, just right of the middle is Good",
        page().side("answer").tap(501, 400), ["ease3"]);
    check("answer, the split follows the screen, not the card",
        page({answer_left_ease: 2, answer_right_ease: 4}).side("answer").tap(900, 50), ["ease4"]);

    // --- an optional middle zone
    check("answer, middle zone answers Hard",
        page({answer_middle_ease: 2}).side("answer").tap(500, 400), ["ease2"]);
    check("answer, outside the middle zone still Again",
        page({answer_middle_ease: 2}).side("answer").tap(100, 400), ["ease1"]);
    check("answer, no middle zone by default",
        page().side("answer").tap(500, 400), ["ease3"]);

    // --- what must not count as a tap
    check("a drag scrolls, it does not answer",
        page().side("answer").tap(500, 400, {dragTo: [500, 100]}), []);
    check("a small wobble is still a tap",
        page().side("answer").tap(400, 400, {dragTo: [410, 405]}), ["ease1"]);
    check("a long press is not a tap",
        page().side("answer").tap(500, 400, {longPress: 700}), []);
    check("a two-finger touch is not a tap",
        page().side("answer").tap(500, 400, {fingers: 2}), []);
    check("tapping a link is left to the link",
        page().side("answer").tap(500, 400, {target: element("a[href]")}), []);
    check("tapping an audio replay button replays, it does not answer",
        page().side("answer").tap(500, 400, {target: element(".replaybutton")}), []);
    check("tapping the type-in field puts the caret in it",
        page().side("answer").tap(500, 400, {target: element("input")}), []);
    check("zoomed in, taps pan instead of answering",
        (function () { var p = page().side("answer"); p.zoom = 2; return p.tap(500, 400); })(),
        []);
    check("selecting text is not a tap",
        (function () {
            var p = page().side("answer");
            p.fire("touchstart", 500, 400);
            p.selection = "some card text";   // the press started a selection
            p.fire("touchend", 500, 400);
            return p.commands;
        })(),
        []);
    check("a stale selection still lets a tap through",
        (function () {
            var p = page().side("answer");
            p.selection = "left over from before";
            return p.tap(400, 400);
        })(),
        ["ease1"]);

    // --- one tap answers one card
    check("a double tap answers once",
        (function () {
            var p = page().side("answer");
            p.tap(900, 400);
            NOW += 100;                     // inside the cooldown
            p.tap(900, 400);
            NOW += 400;
            p.tap(900, 400);
            return p.commands;
        })(),
        ["ease3", "ease3"]);

    // --- the side comes from Python
    check("back on the question, the next tap shows the answer",
        (function () {
            var p = page().side("answer");
            p.tap(900, 400);
            NOW += 500;
            p.side("question");
            p.tap(900, 400);
            return p.commands;
        })(),
        ["ease3", "ans"]);

    // --- the bridge arrives after our script does
    check("a page loaded before pycmd exists still answers once it does",
        (function () {
            pycmd = undefined;                     // the <head>, no bridge yet
            var p = page().side("answer");
            var before = p.tap(900, 400);
            pycmd = function (cmd) { if (TARGET) TARGET.commands.push(cmd); };
            NOW += 500;
            return [before, p.tap(900, 400)];
        })(),
        [[], ["ease3"]]);

    // --- no touch screen: inert, unless told otherwise
    check("a mouse-only screen gets nothing",
        new Page({touch: false}).load(config()).window.__tapToRate === undefined ? "no script" : "script",
        "no script");
    check("force_any_device runs it anyway",
        new Page({touch: false}).load(config({force_any_device: true})).side("answer").tap(900, 400),
        ["ease3"]);

    console.log(checks + " checks, " + failures + " failed");
    if (failures) throw new Error(failures + " check(s) failed");
    return "all good";
}

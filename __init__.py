# Copyright (C) 2026 the Tap to Rate authors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See LICENSE.

"""Tap to Rate - AnkiMobile's touch gestures on Anki's own reviewer.

On a touch screen one tap on the card does what it does in AnkiMobile:

- question side: the tap shows the answer;
- answer side: a tap on the left half answers Again (1), on the right half
  Good (3). Optionally a middle zone can answer Hard or Easy.

Nothing is added to the layout and no touch is consumed: the script only
listens, so scrolling, pinch-zooming, following links, replaying audio and
selecting text keep working exactly as before.

How it works
------------
Anki's reviewer page talks to Python through ``pycmd()``, and
``aqt.reviewer.Reviewer._linkHandler`` already understands the two commands
the Show Answer button and the rating buttons send: ``ans`` (show the
answer, typing included) and ``ease1``..``ease4`` (answer the card). So the
whole feature is a script appended to the reviewer's page, which sends those
commands on a tap; the question/answer side is pushed in from Python, where
it is known exactly (``reviewer_did_show_question`` / ``..._answer``).

The script stays out of the way: a touch counts only if it is one finger,
moves less than a few pixels, lasts under a moment and selects no text, and
it is ignored on anything with behaviour of its own (links, audio replay
buttons, ``<summary>``, text fields). It is inert where the screen is not a
touch screen, unless ``force_any_device`` says otherwise (handy for trying
it with a mouse on a desktop).
"""

from __future__ import annotations

import json
from typing import Any

import aqt
import aqt.reviewer
from aqt import gui_hooks

SCRIPT_ID = "tap-to-rate"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "question_tap_shows_answer": True,
    "answer_left_ease": 1,
    "answer_right_ease": 3,
    "answer_middle_ease": 0,
    "answer_middle_width": 0.25,
    "tap_slop_px": 14,
    "tap_max_ms": 600,
    "cooldown_ms": 250,
    "force_any_device": False,
}

# What a tap must not be: an element with behaviour of its own, or a field
# the user is typing in. Anything else on the card is fair game.
SKIP_SELECTOR = (
    "a[href], button, input, textarea, select, summary, "
    "audio, video, label, [contenteditable], [onclick], #typeans, "
    ".replaybutton, .soundLink, .soundLinkb, .sound"
)

SCRIPT = (
    r"""
<script id="%SCRIPT_ID%">
(function () {
    if (window.__tapToRate) return;
    var CFG = %CONFIG%;
    var touch = CFG.force_any_device || "ontouchstart" in window ||
        (navigator && navigator.maxTouchPoints > 0);
    if (!touch) return;

    var SKIP = %SKIP%;
    var side = "question";   // pushed in from Python after each card
    var start = null;        // the touch being watched
    var selectionAtStart = "";
    var last = 0;            // when this page last answered

    function interactive(el) {
        return !!(el && el.closest && el.closest(SKIP));
    }

    function zoomed() {
        return !!(window.visualViewport && window.visualViewport.scale > 1.01);
    }

    function selection() {
        try { return String(window.getSelection() || ""); } catch (e) { return ""; }
    }

    document.addEventListener("touchstart", function (e) {
        selectionAtStart = selection();
        start = null;
        if (e.touches.length !== 1 || interactive(e.target) || zoomed()) return;
        var t = e.touches[0];
        start = {x: t.clientX, y: t.clientY, at: Date.now(), moved: false};
    }, {passive: true, capture: true});

    document.addEventListener("touchmove", function (e) {
        if (!start) return;
        if (e.touches.length > 1) { start.moved = true; return; }
        var t = e.touches[0];
        if (Math.abs(t.clientX - start.x) > CFG.tap_slop_px ||
                Math.abs(t.clientY - start.y) > CFG.tap_slop_px) {
            start.moved = true;   // a drag: scrolling, zooming or a swipe
        }
    }, {passive: true, capture: true});

    document.addEventListener("touchcancel", function () { start = null; },
        {passive: true, capture: true});

    document.addEventListener("touchend", function (e) {
        var watched = start;
        start = null;
        if (!watched || watched.moved || e.touches.length) return;
        if (Date.now() - watched.at > CFG.tap_max_ms) return;   // a long press
        var t = e.changedTouches[0];
        if (!t || Math.abs(t.clientX - watched.x) > CFG.tap_slop_px ||
                Math.abs(t.clientY - watched.y) > CFG.tap_slop_px) return;
        // starting, extending or collapsing a selection is not a tap
        if (selection() !== selectionAtStart) return;
        tap(t.clientX);
    }, {passive: true, capture: true});

    function tap(x) {
        // This page's script runs in <head>, before the one that defines
        // pycmd, so the bridge is looked for now, not at load.
        if (typeof pycmd !== "function") return;
        var now = Date.now();
        if (now - last < CFG.cooldown_ms) return;
        if (side !== "answer") {
            if (!CFG.question_tap_shows_answer) return;
            last = now;
            pycmd("ans");
            return;
        }
        var width = window.innerWidth || 1;
        var middle = CFG.answer_middle_ease;
        var ease;
        if (middle && Math.abs(x / width - 0.5) <= CFG.answer_middle_width / 2) {
            ease = middle;
        } else {
            ease = x < width / 2 ? CFG.answer_left_ease : CFG.answer_right_ease;
        }
        last = now;
        pycmd("ease" + ease);
    }

    // Python says which side of the card is showing.
    window.__tapToRate = {
        side: function (value) {
            if (value === "question" || value === "answer") side = value;
        },
        config: CFG
    };
})();
</script>
"""
    .replace("%SCRIPT_ID%", SCRIPT_ID)
    .replace("%SKIP%", json.dumps(SKIP_SELECTOR))
)


def _flag(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "off", "")
    return bool(value)


def _ease(value: Any, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if 1 <= number <= 4 else fallback


def _positive(value: Any, fallback: float, limit: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number <= 0:
        return fallback
    return min(number, limit)


def config() -> dict[str, Any]:
    """The add-on's config, read fresh so an edit applies on the next card,
    with every value checked (a typo must never break the reviewer)."""
    raw: Any = None
    try:
        mw = aqt.mw
        if mw is not None and mw.addonManager is not None:
            raw = mw.addonManager.getConfig(__name__)
    except Exception:
        raw = None
    given = raw if isinstance(raw, dict) else {}

    def get(key: str) -> Any:
        value = given.get(key)
        return DEFAULT_CONFIG[key] if value is None else value

    return {
        "enabled": _flag(get("enabled")),
        "question_tap_shows_answer": _flag(get("question_tap_shows_answer")),
        "answer_left_ease": _ease(get("answer_left_ease"), 1),
        "answer_right_ease": _ease(get("answer_right_ease"), 3),
        "answer_middle_ease": _ease(get("answer_middle_ease"), 0),
        "answer_middle_width": min(
            max(_positive(get("answer_middle_width"), 0.25, 1.0), 0.02), 1.0
        ),
        "tap_slop_px": _positive(get("tap_slop_px"), 14, 60),
        "tap_max_ms": _positive(get("tap_max_ms"), 600, 3000),
        "cooldown_ms": _positive(get("cooldown_ms"), 250, 3000),
        "force_any_device": _flag(get("force_any_device")),
    }


def _inject(web_content: Any, context: Any) -> None:
    """Append the tap script to the reviewer's page (and no other page)."""
    if not isinstance(context, aqt.reviewer.Reviewer):
        return
    try:
        cfg = config()
        if not cfg["enabled"] or SCRIPT_ID in web_content.head:
            return
        web_content.head += SCRIPT.replace("%CONFIG%", json.dumps(cfg))
    except Exception:
        pass


def _set_side(side: str) -> None:
    mw = aqt.mw
    reviewer = getattr(mw, "reviewer", None) if mw is not None else None
    if reviewer is None:
        return
    try:
        reviewer.web.eval(
            'window.__tapToRate && window.__tapToRate.side(%s);' % json.dumps(side)
        )
    except Exception:
        pass


def _on_question(card: Any) -> None:
    _set_side("question")


def _on_answer(card: Any) -> None:
    _set_side("answer")


gui_hooks.webview_will_set_content.append(_inject)
gui_hooks.reviewer_did_show_question.append(_on_question)
gui_hooks.reviewer_did_show_answer.append(_on_answer)

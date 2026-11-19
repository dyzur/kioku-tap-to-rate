# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the add-on's Python side, without Anki.

`aqt` is stubbed just enough to import the add-on: the add-on manager (for
the config), `aqt.reviewer.Reviewer` (for the injection check) and the GUI
hooks (to see what it subscribed to). The JS half is tested by sim.js, run
by run.sh, which JavaScriptCore (the engine inside WKWebView) executes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)


class WebContent:
    def __init__(self) -> None:
        self.head = ""
        self.body = ""


class Reviewer:
    class Web:
        def __init__(self) -> None:
            self.evals: list[str] = []

        def eval(self, js: str) -> None:
            self.evals.append(js)

    def __init__(self) -> None:
        self.web = Reviewer.Web()


def install_stubs(given_config: dict | None) -> types.ModuleType:
    """Fake aqt; returns it, so a test can read gui_hooks and mw."""
    class AddonManager:
        def getConfig(self, module: str) -> dict | None:
            return given_config

    class MainWindow:
        addonManager = AddonManager()

    aqt = types.ModuleType("aqt")
    aqt.mw = MainWindow()
    reviewer = types.ModuleType("aqt.reviewer")
    reviewer.Reviewer = Reviewer
    hooks = types.ModuleType("aqt.gui_hooks")
    hooks.webview_will_set_content = []
    hooks.reviewer_did_show_question = []
    hooks.reviewer_did_show_answer = []
    aqt.reviewer = reviewer
    aqt.gui_hooks = hooks
    sys.modules["aqt"] = aqt
    sys.modules["aqt.reviewer"] = reviewer
    sys.modules["aqt.gui_hooks"] = hooks
    return aqt


def load_addon(config: dict | None = None):
    aqt = install_stubs(config)
    sys.modules.pop("tap_to_rate", None)
    spec = importlib.util.spec_from_file_location(
        "tap_to_rate", os.path.join(ADDON, "__init__.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["tap_to_rate"] = module
    spec.loader.exec_module(module)
    return module, aqt


def script_js(module) -> str:
    """The JS the reviewer gets, config and all."""
    html = module.SCRIPT.replace("%CONFIG%", json.dumps(module.config()))
    start = html.index(">", html.index("<script")) + 1
    return html[start : html.rindex("</script>")]


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("ok   " if condition else "FAIL ") + name + ("" if not detail else f"  ({detail})"))
    if not condition:
        raise SystemExit(1)


def main() -> None:
    # --- the hooks it signs up for
    module, aqt = load_addon(None)
    hooks = aqt.gui_hooks
    check("subscribes to webview_will_set_content", module._inject in hooks.webview_will_set_content)
    check("subscribes to reviewer_did_show_question", module._on_question in hooks.reviewer_did_show_question)
    check("subscribes to reviewer_did_show_answer", module._on_answer in hooks.reviewer_did_show_answer)

    # --- defaults, with no config at all
    cfg = module.config()
    check("default left is Again", cfg["answer_left_ease"] == 1, str(cfg))
    check("default right is Good", cfg["answer_right_ease"] == 3, str(cfg))
    check("default middle zone is off", cfg["answer_middle_ease"] == 0, str(cfg))
    check("default question tap shows the answer", cfg["question_tap_shows_answer"] is True)

    # --- injection: the reviewer only
    content = WebContent()
    module._inject(content, Reviewer())
    check("child of the reviewer page", "touchstart" in content.head and "tap-to-rate" in content.head)
    check("config travels with the script", '"answer_right_ease": 3' in content.head)
    plain = WebContent()
    module._inject(plain, object())
    check("nothing on other pages", plain.head == "")

    # --- the side is pushed in after every card
    module, aqt = load_addon(None)
    module._on_question(None)  # no reviewer yet: must not raise
    check("no reviewer, nothing to do", not hasattr(aqt.mw, "reviewer"))

    reviewer = Reviewer()
    aqt.mw.reviewer = reviewer
    module._on_question(None)
    module._on_answer(None)
    check("question side pushed", reviewer.web.evals[0].endswith('side("question");'))
    check("answer side pushed", reviewer.web.evals[1].endswith('side("answer");'))

    # --- config checks: a typo must never break the reviewer
    module, _ = load_addon(
        {
            "answer_left_ease": 7,  # out of range
            "answer_right_ease": "2",  # a string, but a number
            "answer_middle_ease": None,  # null: keep the default
            "tap_slop_px": "wide",  # not a number
            "answer_middle_width": 5,  # over 1
            "enabled": "false",  # a string that means off
            "force_any_device": 1,
        }
    )
    cfg = module.config()
    check("out-of-range ease falls back", cfg["answer_left_ease"] == 1, str(cfg))
    check("numeric string is accepted", cfg["answer_right_ease"] == 2, str(cfg))
    check("null keeps the default", cfg["answer_middle_ease"] == 0, str(cfg))
    check("non-numeric slop falls back", cfg["tap_slop_px"] == 14, str(cfg))
    check("width is clamped", cfg["answer_middle_width"] == 1.0, str(cfg))
    check("string false is off", cfg["enabled"] is False, str(cfg))
    check("truthy flag is on", cfg["force_any_device"] is True, str(cfg))
    disabled = WebContent()
    module._inject(disabled, Reviewer())
    check("disabled means no script", disabled.head == "")

    # --- hand the JS to sim.js
    module, _ = load_addon({"answer_middle_ease": 2})
    path = os.path.join(tempfile.gettempdir(), "tap_to_rate_script.js")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(script_js(module))
    print("wrote " + path)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Runs both halves of the tests: the Python side with a stubbed aqt, and the
# injected JS in JavaScriptCore (the engine inside the app's web view).
set -euo pipefail
cd "$(dirname "$0")"

python3 tests/test_addon.py
osascript -l JavaScript tests/sim.js "$(python3 -c 'import tempfile, os; print(os.path.join(tempfile.gettempdir(), "tap_to_rate_script.js"))')"

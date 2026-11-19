# Tap to Rate

One tap on the card, like AnkiMobile: **tap the card to flip it, tap the
left side for Again (1), the right side for Good (3)** — on Anki's own
desktop reviewer, which is what [Kioku](https://github.com/krmanik/kioku)
runs on an iPad, iPhone or Android phone.

![license](https://img.shields.io/badge/license-AGPL--3.0-blue)
![tested on](https://img.shields.io/badge/tested%20on-iPad%20%C2%B7%20Kioku-2ea44f)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Written because on Kioku grading a card means reaching down to the bottom
bar for **Show Answer** and then a rating button, every single card. This
add-on gives the whole card that job instead.

## What it does

- **Question side:** one tap anywhere on the card shows the answer.
- **Answer side:** a tap on the **left half** answers **Again (1)**, a tap on
  the **right half** answers **Good (3)**. An optional middle zone can answer
  Hard or Easy instead.
- Works around the card's own content: links, audio replay buttons,
  type-in-the-answer fields, folded sections and text selection keep
  behaving as before.

That is the whole thing: one add-on, about 250 lines, no dependencies, no
settings dialog to wade through.

## Install

Download `tap-to-rate.ankiaddon` from the [latest
release](../../releases/latest) (or build it, see below), then:

**On an iPad or iPhone (Kioku)**

1. Get the file to the device — AirDrop, or drop it into iCloud Drive.
2. **Tools › Add-ons › Install from file…**, pick the `.ankiaddon`. (Kioku
   turns on `UIFileSharingEnabled`, and its document picker copies the file
   into the app, so any Files location works.)
3. **Restart Kioku** — add-ons only load at startup.

**On desktop Anki** the same file installs through **Tools › Add-ons ›
Install from file…**. On a machine with no touch screen it stays inert;
set `"force_any_device": true` to try it with a mouse (click the left or
right half of the card).

Requires a build that runs the desktop app: Kioku (iOS, Android, Termux),
Anki on a computer with a touch screen, or the web/Docker variants. **Not**
for AnkiMobile or AnkiDroid — those cannot run desktop add-ons at all, and
AnkiMobile already does this natively.

## Options

**Tools › Add-ons › Tap to Rate › Config** (the same text is in
[`config.md`](config.md), which Anki shows next to the config).

| Option | Default | What it does |
| --- | --- | --- |
| `enabled` | `true` | Off: the card page gets no script at all. |
| `question_tap_shows_answer` | `true` | Off: a tap on the question does nothing (rate only). |
| `answer_left_ease` | `1` | The rating a tap on the left half gives: 1 Again. |
| `answer_right_ease` | `3` | The rating a tap on the right half gives: 3 Good. |
| `answer_middle_ease` | `0` | Optional middle zone: `0` off, or 2 Hard / 4 Easy. |
| `answer_middle_width` | `0.25` | The middle zone, as a fraction of the width. |
| `tap_slop_px` | `14` | How far a finger may wander and still count as a tap. |
| `tap_max_ms` | `600` | A slower touch is a long press, not a tap. |
| `cooldown_ms` | `250` | Ignore taps this soon after one answered, so one tap answers one card. |
| `force_any_device` | `false` | Also tap-to-rate without a touch screen — a mouse on a desktop. |

Ratings are 1 Again, 2 Hard, 3 Good, 4 Easy, as on the answer buttons.

## How it works

Anki's reviewer page already talks to Python through `pycmd()`, and
`aqt.reviewer.Reviewer._linkHandler` already handles exactly the commands
the buttons send:

| Command | Same as |
| --- | --- |
| `pycmd("ans")` | the **Show Answer** button (`onclick='pycmd("ans");'`) |
| `pycmd("ease1")` … `pycmd("ease4")` | the **Again / Hard / Good / Easy** buttons |

So the add-on does not add a bridge command, a `webview_did_receive_js_message`
handler or anything else Anki does not already do — it fires the existing
button presses at the right moment.

The Python side ([`__init__.py`](__init__.py)) is then only plumbing:

- `gui_hooks.webview_will_set_content` appends the script to the reviewer
  page and to no other page.
- `gui_hooks.reviewer_did_show_question` / `..._did_show_answer` tell the
  script which side of the card is showing, because Python knows that
  exactly and guessing it from the DOM does not.
- The config is read fresh on every page load, so an edit applies without a
  full restart, and every value is checked — a typo in the config falls back
  to the default instead of breaking the reviewer.

## Why not two invisible buttons

Two full-width invisible buttons over the card would work, but they would
also swallow every touch the card needs: links inside the answer would stop
opening, audio replay buttons would stop replaying, text could not be
selected or copied, image occlusion and add-on content would stop
responding, and a scroll gesture starting on the card would be eaten by the
button.

So nothing is added to the layout. A script appended to the reviewer page
only *listens* (capture phase, passive: it never calls `preventDefault`),
decides whether the touch was a tap at all, and then sends one of Anki's own
reviewer commands.

A touch counts as a tap only if it is one finger, short, still, selects no
text, and the page is not zoomed in. It never fires on links, buttons,
inputs and text areas (including the type-in-the-answer box),
`<summary>`/folded sections, audio and video elements, replay buttons, or
anything with `contenteditable` or an `onclick`.

## Tests

```sh
./run-tests.sh    # needs python3, and macOS for the second half
```

- [`tests/test_addon.py`](tests/test_addon.py) imports the add-on against a
  stubbed `aqt` and checks the hooks, the injection (reviewer page only,
  nothing when disabled), the side push, and that a broken config falls back
  to defaults instead of raising.
- [`tests/sim.js`](tests/sim.js) runs the injected script in
  **JavaScriptCore** (via `osascript -l JavaScript` — the same engine as the
  app's WKWebView) with a small stub of `window`/`document`/`navigator`, fires
  touches at it and checks which command, if any, comes out: both sides of
  the card, the optional middle zone, drags, long presses, two fingers,
  links, replay buttons, the type-in field, zoom, text selection, cooldown,
  a page loaded before `pycmd` exists, and a non-touch device.

The tests deliberately do not fake Anki itself. What they cannot cover is
the app under them: whether the web view delivers `touchstart`/`touchend` to
the card page inside Kioku — it does, which is how this add-on was verified
on an iPad, and Kioku's own
[`fullscreen.py`](https://github.com/krmanik/kioku/blob/main/shared/python/kioku/fullscreen.py)
uses the same events in the same page for its exit-full-screen swipe.

## Build

```sh
./build.sh        # -> dist/tap-to-rate.ankiaddon
```

Pushing a tag builds the package on CI and attaches it to a GitHub release:

```sh
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

## Layout

| Path | |
| --- | --- |
| `__init__.py` | the add-on: hooks, config checks, the injected script |
| `manifest.json` | name, package, `mod`, conflicts |
| `config.json` | the shipped defaults (copied into Anki's config on install) |
| `config.md` | the help shown in **Tools › Add-ons › Config** |
| `build.sh` | packs those four into `dist/tap-to-rate.ankiaddon` |
| `run-tests.sh`, `tests/` | the tests, not shipped in the package |
| `.github/workflows/` | tests on every push, package attached on a tag |

## Known limits

- The screen is split at its middle, not the card's, so the same spot always
  gives the same rating.
- A tap inside a card's own `<iframe>` (some add-ons wrap content in one) is
  not seen; the rest of the card and the space around it are.
- Verified on an iPad with Kioku. Not tried yet on the Android/Termux/desktop
  variants — reports welcome.

## License

[GNU AGPL v3 or later](LICENSE), the same as Anki and Kioku.

Thanks to [krmanik](https://github.com/krmanik) for Kioku, which is what
makes running Anki's desktop reviewer on a tablet possible at all.

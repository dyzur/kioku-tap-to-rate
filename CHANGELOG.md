# Changelog

## v0.1.0 — 2026-11-19

First working version, verified on an iPad running
[Kioku](https://github.com/krmanik/kioku).

- A tap on the question side shows the answer; a tap on the left half of the
  answer side rates Again (1), the right half Good (3).
- An optional middle zone rates Hard or Easy (`answer_middle_ease`,
  `answer_middle_width`).
- Nothing is added to the layout and no touch is consumed: scrolling,
  pinch-zoom, links, audio replay, folded sections, text selection and type-in
  fields behave as before.
- Configurable ratings, tap slop, long-press limit and cooldown; every value
  is checked and falls back to its default instead of breaking the reviewer.
- `force_any_device` for trying it with a mouse on a desktop.
- Tests: the Python side against a stubbed `aqt`, and the injected script in
  JavaScriptCore through simulated touches (22 + 26 checks).

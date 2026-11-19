# Tap to Rate

One tap on the card does what it does in AnkiMobile. On the **question**
side a tap shows the answer; on the **answer** side a tap on the left half
answers **Again (1)** and a tap on the right half answers **Good (3)**.

Nothing is added to the screen and no touch is taken away from the page:
scrolling, pinch-zooming, links, audio replay and selecting text behave as
before. A tap is ignored on links, buttons, audio replay buttons, folded
sections and text fields, and a drag, a long press or a text selection is
never a tap.

## Options

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
| `force_any_device` | `false` | Also tap-to-rate where there is no touch screen — a mouse on a desktop, to try it out. |

Ratings are 1 Again, 2 Hard, 3 Good, 4 Easy, as on the answer buttons.

## Notes

- The screen is split at its middle, not the card's, so the same spot gives
  the same rating whatever the card shows.
- A tap inside a card's own `<iframe>` (some add-ons wrap their content in
  one) is not seen; the rest of the card and the space around it are.
- If a card has a type-in-the-answer field, tapping the field still just
  puts the caret in it.

# Tasks: Adaptive filter quality — FAST during interaction, GOOD on idle

Reference: specs/image-rendering/spec.md (requirements), design.md (approach).

## 1. Interaction state on ImageView

- [x] 1.1 Add a `_interacting` boolean and a `set_interacting(bool)` method to
      `ImageView`, alongside a `get_interacting()` accessor.
- [x] 1.2 In `Dragger.button_pressed()` call
      `self.view().set_interacting(True)`; in `Dragger.button_released()` call
      `set_interacting(False)` followed by `self.view().queue_draw()`. Verify
      `SelectorDragger` (which wraps `Dragger`) inherits this for middle-button
      pan without affecting `Selector` rubber-band drag.

## 2. Interaction-driven filter selection

- [x] 2.1 Rewrite `_get_adaptive_filter()` to return `cairo.FILTER_FAST` while
      `get_interacting()` is true, otherwise `self.get_interpolation()`, removing
      the zoom-threshold branches.
- [x] 2.2 Confirm `do_draw` still sets the filter via
      `context.get_source().set_filter(self._get_adaptive_filter())` and that
      static rendering now honours the user's `interpolation` at all zoom levels.

## 3. Scroll-zoom interaction handling

- [x] 3.1 In `do_scroll_event()`, call `set_interacting(True)` on each event and
      arm a `GLib.timeout_add` (default ~150 ms) that clears the flag and calls
      `queue_draw()` when it fires; reset the timeout on each subsequent scroll
      event so a scroll burst stays in FAST until it stops.
- [x] 3.2 Ensure the idle timeout handler is removed if the widget is destroyed
      (guard against firing after teardown).

## 4. Tests

- [x] 4.1 Update `test_adaptive_filter` to assert interaction-driven selection
      (interacting -> FAST; idle -> configured interpolation) instead of the
      old zoom thresholds.
- [x] 4.2 Add a test that a static view at fit zoom (<0.5x) renders with
      `FILTER_GOOD` (or configured interpolation).
- [x] 4.3 Add a test that `Dragger` press/release toggles `get_interacting()`
      and that `Selector` drag does not.
- [x] 4.4 Add a test that a scroll event sets interacting and the idle timeout
      clears it and schedules a redraw.

## 5. Verification & docs

- [x] 5.1 Run `pytest` and confirm no regressions; run `black` and `pylint` and
      confirm coverage and lint scores are not worse than before the change.
- [x] 5.2 If the fix is user-visible, document the improved full-page rendering
      quality in `README.md`.

# Design

## Context

See `proposal.md` - Why. `Selector.button_pressed` is the selection entry
point for both the Select tool and the primary button of the Select & Pan tool,
which delegates to a contained `Selector`. It sets `dragging` and seeds
`drag_start` with both keys present but unset, then calls `update_cursor` and
`_update_selection`.

`ImageView.update_cursor` returns early when `get_pixbuf_size()` is `None`, so
the press reaches `_update_selection` with `drag_start == {"x": None,
"y": None}`. The mid/mid branch copies those values and subtracts them, raising
`TypeError`. The same happens on later motion while no image exists.

The drag origin has two shapes in the tree. `Selector.button_pressed` creates
keys with `None`, while the cursor code tests `"x" not in self.drag_start` and
`"y" not in self.drag_start`, and the existing tests seed `{}`. The intended
"fill the missing axis" path therefore never runs in production.

## Goals / Non-Goals

**Goals:**

- Make a selection press or drag with no image a harmless no-op.
- Leave no drag origin, edge mode or selection change behind after an ignored
  gesture.
- Make the drag-origin handling work for both an absent axis and one whose value
  is `None`.
- Keep selection behaviour with an image exactly as it is.

**Non-Goals:**

- Changing how a selection is drawn once an image is shown.
- Changing the Pan tool or the Select & Pan middle-button pan.
- Changing the right-click context menu.
- Redesigning the whole selector state machine.

## Decisions

### Guard at the selector entry points

Add an early return in `Selector.button_pressed` when
`self.view().get_pixbuf_size() is None`, before changing `dragging`,
`drag_start` or the selection. Also ignore `_update_selection` while no image is
displayed and clear the in-progress gesture, so an image disappearing
mid-drag cannot resume a stale selection.

Guarding here covers the Select tool and the Select & Pan primary button, because
the combined tool delegates primary presses to its `Selector`. The Pan tool
already survives a missing image via its `offset is None` check.

Alternative considered: guard every tool press centrally in `ImageView`.
Rejected because it would change the Pan tool's existing press/release cycle
for no user-visible benefit, and it would hide the selector-specific origin
problem rather than fix it.

### Store only set axes in the drag origin

Initialise the selector's `drag_start` to `{}` and use `.get(axis)` everywhere
the origin is read. Update `cursor_type_at_point` to treat a missing axis and
an axis whose value is `None` the same way, instead of testing for key
membership. This makes the tested shape and the production shape identical and
lets the cursor code actually fill the partial origin it intended to.

Alternative considered: keep `{"x": None, "y": None}` and change only the
membership tests to value checks. It fixes the immediate mismatch, but keeps a
dict whose keys claim coordinates that do not exist. Rejected in favour of a
single rule: an unset axis is absent.

### Fall back instead of casting an unset axis

In `_update_selection`, resolve every unset axis before the arithmetic:

- the mid/mid branch uses the drag origin, falling back to the current
  selection's top-left when the origin is unset;
- the edge branches keep their existing selection-corner fallback and use the
  event coordinate when there is no selection;
- if an axis is still unset, use the event coordinate, so a direct or defensive
  call can never produce `None - float`.

This gives the mid/mid branch the same safety the edge branches already had and
keeps a zero-size selection rather than an exception when there is nothing to
fall back to.

### Test through the tools, not only the helper

Add tests that call `button_pressed` and `motion` with no pixbuf for both
`Selector` and `SelectorDragger`, including the primary and middle buttons, and
that check `dragging`, the selection and the absence of an exception. Add a test
that ignores a press, displays a pixbuf and then performs a real drag, asserting
that the new selection starts at the new press. Keep direct `_update_selection`
coverage for the `{"x": None}` and `{}` origin shapes.

## Risks / Trade-offs

- **Clearing the gesture when the image vanishes mid-drag ends that drag** → The
  user is holding the button while the page disappears; there is nothing useful
  to select, and the next press starts cleanly.
- **Changing the base drag origin to `{}` could affect the Pan tool** → The Pan
  tool writes both coordinates on every press before reading them; its test
  still asserts the full dict after a press.
- **Selection fallback for an unset origin can select a different rectangle
  than before** → This only runs for shapes that previously raised or were
  unreachable in production; the with-image tests pin the normal path.
- **A defensive guard can mask a future bug** → The guard applies only to the
  documented no-image state; the with-image tests and the unsupported-state
  test keep the normal path exercised.

## Migration Plan

No data or configuration migration is needed; the change is confined to input
handling in the running view. Rollback is a code revert.

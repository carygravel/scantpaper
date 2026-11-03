# Proposal

## Why

A primary press on the image view while no page is displayed leaves the
`Selector` tool in a half-started drag. `Selector.button_pressed` sets
`dragging = True` and seeds the drag origin with unset coordinates, then relies
on `update_cursor` to fill them. `update_cursor` returns early when the view has
no pixbuf, so `_update_selection` subtracts a `None` origin and raises
`TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'`. The
press is logged as an uncaught exception and the broken state remains; while
the view is still empty, every motion repeats the same traceback. The window
exists before the first page has rendered, after New File, and after the last
page is deleted, so the failure is timing-dependent rather than user error.

## What Changes

- Ignore a selector primary press when the image view displays no image: do
  not set `dragging`, do not start a selection and do not raise. The context
  menu and the Pan tool keep their current behaviour.
- Start the selector's drag origin empty and treat an absent or `None` axis as
  unset, so the mid/mid and edge branches never compute with an unset origin.
  Give the mid/mid branch the same selection fallback as the edge branches.
- A press after a page appears still starts a normal selection; an ignored
  press leaves no state that affects the next gesture.
- Cover the empty-view press and the subsequent motion with unit tests for
  both the Select and Select & Pan tools, including the production shape of a
  drag origin whose keys are present with `None` values.
- Record the fix in the changelog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `image-view-tools`: add that tool input is ignored while the view displays no
  image. A press or drag SHALL NOT draw a selection, pan, raise an exception or
  leave a partial gesture that affects the next one. Existing selection and
  panning behaviour with an image is unchanged.

## Impact

- `src/scantpaper/imageview.py`: guard `Selector.button_pressed` on a missing
  pixbuf and make the selector's drag-origin handling consistent between
  `button_pressed`, `cursor_type_at_point` and `_update_selection`.
- `src/scantpaper/tests/test_imageview.py`: empty-view press and motion tests,
  the `{"x": None}` origin shape, and a valid press after an ignored one.
- `changelog.md`.
- No dependency, configuration or data-model changes.

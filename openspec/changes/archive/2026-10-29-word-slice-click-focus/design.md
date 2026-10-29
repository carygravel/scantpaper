# Design

## Context

See `proposal.md` - Why. The relevant current state:

- `Canvas._hit_test()` inverts the renderer transform and delegates to
  `_find_bbox_at()`, which returns the deepest box containing a point. That
  includes page, column/block, paragraph and line boxes. `_hit_test()` is used
  only by `_button_pressed()`.
- `Canvas.get_bbox_at()` calls the same `_find_bbox_at()` but is used when a
  new slice needs a parent, so it deliberately may return a container.
- `LayerEditor.create()` passes its `edit` callback into `Canvas.set_text()`,
  and `_boxed_text()` copies that callback onto every box it builds. The
  primary-button handler therefore treats any hit box as focusable.
- Only word boxes receive a confidence value (default 100 when hOCR omits
  `x_wconf`). Containers have `confidence = None`, yet
  `Canvas.set_index_by_bbox()` passes it to the confidence index.
- Both editors - text and annotations - build and store their slices as
  `type == "word"`. Navigation, deletion, hOCR serialising and the confidence
  index all already operate on words only.

## Goals / Non-Goals

**Goals:**

- Make "a slice is a word" the single rule for what a click can focus, in
  both the text and annotation editors.
- Let a primary press on non-slice space begin the existing selection drag,
  so the documented layer-pane add gesture works on a page with a loaded
  layer.
- Keep the geometric hit test and parent lookup unchanged.
- Make a non-slice focus impossible from any caller, not just from the click
  handler.

**Non-Goals:**

- Changing the click-vs-drag timing: a drag still starts on press, and a
  zero-size release is still ignored.
- Clearing the focused slice on a click in empty space.
- Making containers selectable, editable or navigable, or drawing them
  differently.
- Changing how `add`/`copy` choose a parent container.

## Decisions

### 1. Gate focus in the primary-button handler

`Canvas._button_pressed()` SHALL call the edit callback
only when the hit box is a slice; otherwise it leaves focus alone and falls
through to `_start_draw()`. This is the one place that decides between
"focus a slice" and "begin a selection", so the rule is visible and testable.

Alternatives considered:

- **Filter inside `_hit_test()`.** Rejected: `_hit_test()` is the geometric
  primitive whose contract is "deepest box containing the point", and its
  transform tests use a line box to prove that. `get_bbox_at()` shares
  `_find_bbox_at()` and must keep resolving containers for parent lookup.
- **Do not attach the edit callback to non-word boxes.** Rejected as the
  primary fix: `set_text()` wiring is one place, but boxes are also built by
  `add_box()` and in tests, so the policy would be implicit and bypassable.
  It also would not stop a future caller from passing a container to
  `LayerEditor.edit()`.

### 2. Define a slice once on the box

Add a small `Bbox.is_slice` property that returns `self.type == "word"` and
use it in both the click gate and the editor guard. The project has no shared
"word" constant today, and introducing one only for this change would leave
the many existing comparisons inconsistent; a property named after the domain
term keeps the new rule readable without a wider refactor.

### 3. Guard the editor as well as the click handler

`LayerEditor.edit()` SHALL ignore a non-slice bbox: log at debug level and
leave the current focus, control text and canvas indexes untouched. It SHALL
NOT clear the editor, because the spec says a press in container whitespace
leaves the previously focused slice focused. This guard makes the invariant
hold for programmatic callers even though the click gate already prevents the
user path.

Alternative considered: **only guard `LayerEditor.edit()`.** Rejected: the
canvas would still set `focus = True`, so the selection drag would never begin
and the add-selection behaviour would stay broken.

### 4. Keep the confidence index strict

Do not make `ListIter.set_index_by_bbox()` tolerate a `None` value. The index
is built from word boxes only and `add_box_to_index()` already refuses a
`None` confidence, so a `None` reaching it means a non-slice has escaped the
boundary. A silent guard would hide that regression and still leave a
container focusable, with the delete-a-line consequence intact.

### 5. A plain click on non-slice space is inert

`_start_draw()` runs on press and `_button_released()` ignores a rectangle
with zero width or height, so a click without motion produces no
`selection-drawn` signal, no selection change and no focus change. Only a
drag replaces the selection. This matches the proposal's recorded behaviour
and needs no extra state.

## Risks / Trade-offs

- **A selection cannot be started on top of a word.** Pre-existing, and now
  more visible: the user starts the drag in adjacent whitespace. Documented
  here so it is a deliberate limitation; supporting both would need a
  modifier or a draw tool and is out of scope.
- **Container outlines are still drawn but are not click targets.** A user
  who clicks a line's border gets no focus and may start a selection. The
  spec now defines only words as slices; the outlines remain useful for
  hierarchy and confidence display.
- **Programmatic `edit()` calls with a container become silent no-ops.** They
  now log at debug level; the alternative (raising) would put the app back in
  the crash path if any caller is missed.
- **Existing tests pin the old behaviour.** `test_canvas_click_on_bbox_does_
  not_draw_selection` treats a page box as editable, and
  `test_canvas_draw_selection_rectangle` only passes because its page box has
  no callback. Both are updated to describe the new rule; the transform test
  that expects `_hit_test()` to return a line stays as is.

## Migration Plan

Pure application code, no schema or data migration. Reverting the change
restores the previous click handling with no persistence side effects.

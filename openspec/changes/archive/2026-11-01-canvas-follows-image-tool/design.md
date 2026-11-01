# Design

## Context

See `proposal.md` - Why. Three pieces of current state shape the approach:

- `ImageView` owns the active tool as a `Tool` object property and routes
  every button press through it. `app_window` creates the tool from
  `settings["image_control_tool"]` in `_populate_panes` and replaces it in
  `_change_image_tool_cb`.
- `Canvas` has no tool. Its press handler hardcodes the combined tool's
  mapping: primary press focuses or draws a selection, middle press pans.
- The canvases are created later, in
  `session_mixins._add_text_view_layers`, which already binds `zoom`,
  `offset`, `resolution_ratio` and `selection` from the view. The tool is
  not among the bound properties, and `_populate_panes` has already run
  by the time the canvases exist.

The shared tool identifiers are the strings in `const.py`
(`DRAGGER_TOOL`, `SELECTOR_TOOL`, `SELECTORDRAGGER_TOOL`).

## Goals / Non-Goals

**Goals:**

- One button matrix in both viewers, driven by the same tool value.
- The canvas keeps its own pan and selection maths; only the routing is
  new.
- The change works in tabbed and split layouts, including canvases that
  are created after the tool is set and canvases that are hidden at the
  time.

**Non-Goals:**

- Unifying `Canvas` and `ImageView` behind one viewport/tool abstraction.
- Reusing the `Tool` classes for canvas panning; their transforms, DnD
  and interaction hooks are image-view specific.
- Adding selection-edge resizing or a context menu to the canvases.
- Changing the tool set, scroll zoom, or the default tool.

## Decisions

### 1. The tool mode travels as a string property, bound view to canvas

Add a `tool_mode` string property to `ImageView` and to `Canvas`; set it
in `ImageView.set_tool` from a new `mode` attribute on each `Tool`
subclass. Bind it one-way from the view to both canvases in
`_add_text_view_layers` with `SYNC_CREATE`, next to the existing
properties. The canvas default is `SELECTORDRAGGER_TOOL`, so a standalone
canvas keeps its current behaviour.

Alternatives considered:

- **Bind the `Tool` object itself.** The canvas would hold an
  image-view-owned object whose `view()` transforms and DnD hooks are
  wrong for it. Using only `tool.mode` from it would be a trap for the
  next reader.
- **Push the mode from `app_window`.** It would need two call sites
  (startup and change) and an explicit catch-up when the canvases are
  created, because `_populate_panes` runs first. The binding removes the
  ordering dependency and matches how every other shared viewport value
  is synchronised.
- **A bidirectional binding.** The canvas never changes the tool, and a
  second writer would add a loop risk for no benefit.

### 2. The tool decides which buttons it handles

Add `Tool.handles_button(button)`, returning `False` in the base class.
`Selector` and `Dragger` accept the primary button only;
`SelectorDragger` accepts the primary and middle buttons. `ImageView`
consults the predicate before delegating press and release, so the Pan
and Select tools ignore the middle button without type checks in the
widget.

Alternatives considered:

- **A constructor flag on `Dragger`** (`allow_middle=True` when built by
  `SelectorDragger`). It works, but it encodes the combined tool's
  composition in the dragger's constructor and leaves the image view
  delegating every button to every tool.
- **Rejecting non-primary buttons inside `Dragger.button_pressed`.**
  `SelectorDragger` delegates its middle press to an internal `Dragger`,
  so the dragger must accept a middle press in that context. The
  predicate keeps the decision on the outer tool, while the dragger
  stays a permissive delegate.

`Selector.button_pressed` also rejects non-primary buttons as defence in
depth, since tests call tools directly. `Dragger.button_pressed` stays
permissive for the combined tool's delegate call. Releases are gated by
the same predicate so a release cannot end a gesture the tool did not
start.

### 3. The canvas samples the mode at press and reuses its pan path

Extract the existing middle-button pan into `_begin_pan`, `_pan_to` and
`_end_pan`. `_button_pressed` then routes:

- primary and mode `pan` -> `_begin_pan`
- primary and a selecting mode -> the existing focus/selection path
- middle and mode `selectordragger` -> `_begin_pan`
- middle and any other mode -> ignore

`_motion` keeps its current order: a live selection drag first, then a
pan. The press commits the gesture: a tool change between press and
release does not switch an in-progress drag between panning and
selecting. `_button_released` ends whichever gesture is active.

The existing `dragging` and `_drawing` flags are sufficient; focusing a
word still clears `dragging`, which cannot conflict because focus only
happens in the selecting modes where no pan has begun.

Alternatives considered:

- **Reusing the image view's `Dragger`/`Selector`.** They call
  `to_image_coords`, `set_interacting`, `drag_check_threshold` and emit
  `dnd-start`, which the canvas does not provide. Adapting them would be
  the non-goal refactor for a few lines of duplicated maths.

### 4. Cursor feedback mirrors the image view

Add a canvas `_update_cursor(x, y)` called on motion, press and release.
Over the displayed page it shows `grab`/`grabbing` in the Pan mode and
`crosshair` in the selecting modes; off the page it clears the cursor.
Cache the last cursor name so a motion event does not allocate a
`Gdk.Cursor` every time.

### 5. Documentation states the matrix once

README's View Menu section carries the matrix for both viewers, and the
layer-editing paragraph says that drawing a new selection requires a
selecting tool. No settings or session changes: `image_control_tool`
keeps its current values.

## Risks / Trade-offs

- **Pan and Select lose their middle-button actions** -> deliberate, and
  documented; Select & Pan stays the default, so most users see no
  change. Record it in the changelog.
- **A user left in the Pan tool cannot draw a new text-layer selection**
  -> the grab cursor advertises the mode, the toolbar shows the active
  tool, and README says to choose a selecting tool. The default combined
  tool is unaffected.
- **Panning with the Pan tool moves nothing when the page already fits**
  -> existing offset clamping, identical to middle-button panning today;
  not a regression.
- **The new `tool_mode` setter can be written independently of `tool`**
  -> keep `set_tool` as the only mutator and cover the property and
  binding in tests.
- **Coverage gate at 99%** -> the new routing branches, cursor branches
  and the button predicate need direct tests; the tasks list them.
- **Modified requirements lose detail at archive time** -> both deltas
  copy each modified requirement block whole, scenarios included.

## Migration Plan

None. This is a UI interaction change with no session, database,
configuration or saved-file impact. Reverting the commit restores the
previous button handling.

# OCR Editor Add Box - Design

## Context

The Add control (`layer.py:371`) reads the current selection from the image
view (`view.get_selection()`) and places a new slice there. It is unusable
without a selection: on an existing layer it reaches `canvas.add_box` with a
`None` box, and on a fresh layer `_new_layer_json` silently returns `""`
(`layer.py:416`). The Add button is a throwaway local (`layer.py:134`), so it
cannot be disabled. The layer `canvas` (`canvas.py:1235`) only pans
(middle-drag) and focuses an existing box (left-click); it cannot draw a
rectangle.

The view is already the natural home for selection: it exposes a
`selection` GObject property (`imageview.py:523`) with `notify::selection`,
emits `selection-changed`, and both editors (`_text_editor`, `_ann_editor`)
share that one view. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**

- Make the Add control's availability depend on whether a selection exists,
  with a discoverable explanation when it is disabled.
- Let the user draw the selection rectangle in the Text layer and Annotation
  panes, with a single shared selection across the image view and both panes.
- Keep both editors (text and annotations) consistent.

**Non-Goals:**

- No new rectangle-drawing tools or toggles on the image view (its Selector
  already does this); the image view behavior is unchanged.
- No change to how the Add/OK/Copy controls commit slices, beyond enabling
  a layer-pane-drawn rectangle to seed the same path.

## Decisions

### 1. The image view remains the single source of truth for selection

The view owns the `selection` property. Drawing in a layer pane computes the
rectangle in image coordinates and calls `view.set_selection(rect)`. This
automatically satisfies "one selection, drawn from either pane" because every
consumer already reads `view.get_selection()`. The layer canvas renders the
current selection as an overlay by mirroring the view's selection (via the
same `bind_property` pattern already used for `zoom`/`offset` at
`session_mixins.py:458`).

**Alternatives considered:** giving the canvas its own selection and syncing
both ways. Rejected - it creates two sources of truth and a reconciliation
problem; binding canvas selection to the view's keeps one authority.

### 2. The Add button is stored and its state driven from the selection

`LayerControls` stores the add button as an attribute (e.g. `self.add_button`)
instead of a local. `LayerEditor` connects to the view's `notify::selection`
and calls `_update_add_state()`: enabled when `view.get_selection() is not
None`, otherwise disabled. The tooltip switches to a "draw or select a
rectangle first" message while disabled. Both editors connect independently,
so both Add buttons track the shared selection.

**Alternatives considered:** a dedicated "no selection" enable/disable action
routed through the window. Rejected - the selection is per-view and the
editors already own their buttons.

### 3. The layer canvas draws a selection rectangle on left-drag over empty space

The canvas keeps its existing left-click-to-focus behavior when a box is hit
(`canvas.py:1244`), and adds: left-drag over empty space draws a live
selection rectangle; on release the rectangle (in image coordinates) is
committed to the view via `view.set_selection`. The live rectangle is part of
the canvas's selection overlay during the drag.

**Alternatives considered:** a separate draw tool/toggle for the layer pane.
Rejected - the spec calls for simply dragging in the pane; adding a tool
toggle duplicates the image view's Selector and complicates the interaction.

## Risks / Trade-offs

- **Click-vs-drag ambiguity** on the layer canvas (a plain click should still
  focus a box, a drag should draw). Mitigated by only starting a draw on
  motion after button press, and only when the press did not hit an existing
  box.
- **Selection lifecycle** (page change, crop, undo) can clear the selection;
  the Add button must track it. Mitigated by driving state from
  `notify::selection`, which fires on every change including clears.
- **Overlay rendering parity** between image view and layer panes. Mitigated
  by binding canvas selection to the view so both draw the same rectangle.

## Migration Plan

Pure additive UI change; no data migration. The Add button and canvas
drawing are enabled in place. Existing behavior (focus-on-click, pan,
image-tab drawing) is preserved.

## Open Questions

None that affect the specs or task breakdown.

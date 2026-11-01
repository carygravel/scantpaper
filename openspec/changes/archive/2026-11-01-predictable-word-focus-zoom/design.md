# Design

## Context

See `proposal.md` for motivation and `specs/slice-focus-zoom/spec.md` for the
behaviour contract. The current path is:

```
LayerEditor.edit(bbox)                  layer.py
  set_selection(bbox.bbox)
  setzoom_is_fit(False)
  ImageView.zoom_to_selection(0.5)      imageview.py
    zoom_to_box(box, factor)
      fit = min(pane_w / box_w, pane_h / box_h)
      zoom = fit * factor * scale_factor
      centre the box
```

The pieces this design builds on:

- `ImageView.zoom_to_box` already knows the allocation, the HiDPI
  `scale_factor`, the x/y `resolution_ratio`, and the existing
  `zoom_to_fit_limit`.
- `ImageView.zoom` is stored such that rendered logical pixels are
  `image_pixels * zoom / scale_factor`.
- The canvas scene graph keeps the hOCR hierarchy. An OCR word's nearest
  ancestor of type `line` carries the line box and, usually, `x_size`.
  Hand-added slices and annotation notes are words directly under the page and
  have no line ancestor.
- `scantpaperrc` is a dictionary of settings. `app_window` replaces that
  dictionary when Preferences is applied and writes it on quit. The layer bars
  are the `LayerControls` of the text and annotation editors, both appended to
  the shared `edit_hbox`; only the active one is visible.

## Goals / Non-Goals

**Goals:**

- Make the on-screen text size depend on a logical target, not on the slice or
  pane shape.
- Keep the focused slice fully visible with a context margin.
- Let the user tune the target from the layer control bar, with the effect
  visible immediately on the focused slice.
- Persist the tuned level like every other setting.
- Route every focus path through one implementation, so click, confidence
  navigation and automatic advance cannot drift apart.

**Non-Goals:**

- Per-slice or per-page focus levels.
- Animated zooming, or changing panning/selection behaviour.
- Changing the generic View zoom actions (`100%`, fit, in, out).
- A Preferences row, a View-menu entry for the level, or an inline spin button.
- Any session-database or save-format change.

## Decisions

### Target a logical text height, not a pane fraction

`FOCUS_TEXT_HEIGHT` is the on-screen em height in logical pixels. The initial
value is 64, roughly four times a typical UI font height. The focus zoom is:

```
target_zoom = FOCUS_TEXT_HEIGHT * level * scale_factor / text_height
```

where `text_height` is the line's font size in image pixels and `level` is the
user's multiplier. A level of 1.0 therefore renders every line at the same
logical text height regardless of scan resolution, word length or pane size.

Alternatives considered:

- **Keep the fraction-of-pane rule and expose it.** Rejected: the fraction is
  what makes text size depend on both aspect ratios.
- **Target an absolute image zoom.** Rejected: a fixed zoom renders the same
  page differently at 150, 300 and 600 dpi.
- **Target the word bbox height only.** Rejected: glyph extents within a line
  (x-height versus ascenders and descenders) would still change the size.

### Derive the target from the containing line

The nearest ancestor of type `line` is the target source. In order:

1. The line's `x_size`, when present and positive. It is the hOCR font size, is
   already in image pixels, and is independent of the line's rotation.
2. The line box's extent across the line's accumulated rotation: its height for
   0 and 180 degrees, its width for 90 and 270 degrees. The editor creates only
   quarter turns, and hOCR textangle is normally a quarter turn.
3. For any other rotation, the smaller of the line box's width and height.
4. With no line ancestor, the slice's own `x_size`, then the same extent rules
   on the slice box.

Using `x_size` first is what makes a word such as "I" and a word such as "man"
on the same line render identically, and it avoids needing to reconstruct a
rotated rectangle's thickness from its axis-aligned bounding box.

### Bound the target by the fit with a margin

Factor the existing fit calculation out of `zoom_to_box` into a helper that
returns the zoom at which a box fills the allocation. The focus zoom is:

```
fit_zoom = fit_zoom_for(selection)
zoom = min(target_zoom, fit_zoom * (1 - FOCUS_MARGIN))
```

with `FOCUS_MARGIN = 0.1`, so 10% of the pane stays as breathing room on the
limiting axis. The result is clamped to the view's `MIN_ZOOM`/`MAX_ZOOM` and the
existing `zoom_to_fit_limit`, then applied with the existing
`_set_zoom_with_center`, and `zoom_is_fit` is left false.

Alternatives considered:

- **Clip the slice at the target.** Rejected: the user could not see the word
  they are correcting.
- **Require panning to see the whole slice.** Rejected: confidence navigation
  should not also require a pan after every jump.

### Use a compact menu button with a popover slider

`LayerControls` gains a feature-flagged focus control, enabled for both the text
and annotation editors and placed after the last navigation button, before
**Add text**:

```
[first] [prev] [sort v] [next] [last] [zoom icon] [add] [ text .... ]
```

The button is a `Gtk.MenuButton` with the `zoom-fit-best` icon, no label and no
hexpand, so it costs roughly one icon button of bar width. Its popover holds:

- a label "Focus zoom";
- a horizontal `Gtk.Scale` from 50 to 200, step 5, drawing its value as a
  percentage, where 100 is the default;
- a **Reset** button that sets 100.

A new `focus-zoom-changed` signal carries the level as a float. The scale's
`value-changed` emits it while dragging, so the focused slice is re-zoomed live.

Alternatives considered:

- **Inline spin button.** Rejected: about 90-120 px plus a label, and steppers
  are a poor way to find a level by feel.
- **Inline scale.** Rejected: the widest option in a bar whose only elastic
  child is the correction text field.
- **Drop-down of presets.** Viable but coarser; kept as a fallback if the
  popover proves awkward.
- **View menu or Preferences.** Rejected: the adjustment is contextual and
  should be visible while correcting, not a global dialog or a menu visit.

### One setting, owned by the window

Add `"focus zoom"` to `config.DEFAULTS` with a value of `1.0`, and put the
default, minimum, maximum and step in `const.py` alongside
`FOCUS_TEXT_HEIGHT` and `FOCUS_MARGIN`. Replace `ZOOM_CONTEXT_FACTOR`.

`LayerEditor` receives `get_focus_zoom` and `set_focus_zoom` callables.
`app_window` supplies both closures over its settings dictionary; its setter
clamps, stores the value, and pushes it into both control bars with their change
handlers blocked. This keeps one source of truth while only one bar is visible,
and avoids coupling `LayerEditor` to the whole settings dict.

### Re-apply through one focus funnel

`LayerEditor.edit` keeps doing the selection, control and focus work, then calls
an extracted `_apply_focus_zoom(bbox)`. That method asks the view for the focus
zoom using the bbox and its line-derived text height. A level change while a
slice is focused calls the same method with `_current_bbox`; no navigation and
no text-buffer work is repeated.

Because click, first/previous/next/last, accept/delete advance and add/duplicate
all already call `edit`, they inherit the rule without separate code paths.

## Risks / Trade-offs

- **Some hOCR lacks `x_size`.** Fall back to the line box across rotation, then
  to the slice; cover both paths with tests.
- **Lines rotated by a non-quarter turn.** The extent fallback is approximate.
  The editor only creates quarter turns, so this is an edge case; preferring
  `x_size` when present avoids it entirely.
- **Tiny text or a very small scan.** The target can exceed the view's or
  canvas's maximum zoom and be clamped, so the configured text size may not be
  reached. Clamping keeps the view usable and is still closer to the target
  than the old rule.
- **A hand-drawn slice whose bbox is much larger than its text.** The
  slice-height fallback may over-zoom. This matches the current dependence on
  the drawn box; using `x_size` when present mitigates it.
- **Bar width.** The icon-only menu button is about 40 px and has no hexpand;
  the correction field remains the only elastic widget, as today.
- **Live updates during a drag.** Each change is a pure view zoom and centring,
  with no thread or database work, so coalescing is unnecessary.
- **Two control bars, one setting.** The window-level setter updates both with
  blocked handlers, so the hidden bar cannot show a stale value after a switch.

## Migration Plan

No database or file-format migration. Existing configuration files gain the new
key through `add_defaults`, so the behaviour applies with the default level of
100%. Removing `ZOOM_CONTEXT_FACTOR` leaves no persisted state behind; an older
build that reads a config containing `"focus zoom"` simply ignores the unknown
key. New translatable strings are the control label, its tooltip and the reset
action; no existing translations change.

Rollback is a code revert. The stored level is harmless if the feature is
removed.

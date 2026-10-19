## Context

See proposal.md - Why. The relevant current state:

- The `editmode` stateful action (app_window.py:299) is created with a fixed
  initial state `"text"` and its callback `_edit_mode_callback`
  (session_mixins.py:460) only runs when the action is *activated*; the initial
  state never emits `activate`.
- Startup hides both control bars unconditionally
  (app_window.py:430-431), so the menu's tick and the editors disagree until a
  manual toggle — the reported bug.
- `_pack_viewer_tools` (app_window.py:608) hardcodes the text canvas into the
  split pane and detaches the annotation canvas, while `editmode` can still
  select annotations.
- Tabbed mode is a `GtkNotebook` with three pages, Image first, so the default
  page is Image (app.ui:789-799; `_pack_viewer_tools` appends Image first).
- `viewer_tools` is persisted in config (config.py:28,405) and the notebook's
  selected page is not persisted at all.

## Goals / Non-Goals

**Goals:**

- One source of truth for "which layer is active", with tabbed page, split
  canvas and control bar all derived from it.
- Make the annotation layer actually reachable in split modes, or not offered
  at all — never a bar over an off-screen canvas.
- Fix the startup mismatch as a consequence of the model, not a patch.

**Non-Goals:**

- Merging the two canvases into one.
- Changing tab labels or splitting a canvas per view.
- Changing the edit operations themselves (that is `layer-editing`).
- Persisting the tabbed notebook page independently of the active layer.

## Decisions

### D1. Keep `editmode` as the active-layer state; do not derive it from the tab

The `editmode` action remains, but its meaning becomes "the active layer".
In tabbed mode the notebook page mirrors it; in split modes it selects the
packed canvas. Deleting the action (the earlier alternative) is rejected
because split mode still needs a way to choose the layer and the image-only tab
has no layer to derive from. Keeping the action also preserves the View-menu
items and their mnemonics.

- *Alternative:* derive everything from the notebook page. Rejected: no
  notebook page exists in split modes, and the tabbed Image page shows no layer
  to derive from.
- *Alternative:* keep `editmode` purely a bar toggle (today). Rejected: leaves
  three unsynchronised states, the root of the bug.

### D2. The window owns the transition; a single guarded setter

Introduce one internal operation (e.g. `_set_active_layer(mode)`) that applies
the active layer everywhere at once: sets the action state, sets both control
bars' visibility, switches the notebook page (tabbed) or repacks the pane
(split). Both entry points (menu activation, notebook `switch-page`) funnel
through it behind a reentrancy guard, mirroring the existing `_in_tool_change`
pattern in `_change_image_tool_cb` (app_window.py:746-762).

- *Why a guard:* tab change sets the action, whose activation would try to set
  the tab again; the guard breaks the cycle without `handler_block` gymnastics.
- *Alternative:* GObject property bindings between notebook page and action.
  Rejected as harder to reason about across the split/tabbed asymmetry.
- *Why the Image tab keeps the selection:* that page shows the bare scan, so
  there is no layer canvas to show a bar for; the selection is left untouched
  so opening the layer's own page needs no re-selection. Bar visibility is
  therefore a function of the on-screen canvas, not of the selected layer
  alone.

### D3. Startup applies the persisted active layer (default text)

Replace the unconditional `set_active(active=False)` pair (app_window.py:430)
with a single apply after the editors exist, using the persisted setting
(defaulting to `"text"`), so the View menu is correct on first paint. In tabbed
mode the visible page is left alone: the window opens on the Image page so the
scan is shown. The Image page has no layer canvas, so the control bar is hidden
there even though the text layer stays selected; it appears as soon as the
layer's own page is opened. In a split view the layer's canvas and bar are shown
beside the image.

### D4. Split packing selects the active layer's canvas

`_pack_viewer_tools` picks `self._text_editor.canvas` or
`self._ann_editor.canvas` according to the active layer instead of always the
text canvas. `_change_view_cb` (app_window.py:783) must detach the active canvas
(rather than always `t_canvas`) when leaving tabbed mode. `_on_page_loaded`
already builds both editors regardless of what is packed, so no extra work is
needed to populate the newly reachable annotation canvas.

### D5. Persist the active layer beside `viewer_tools`

Store the active layer under a key such as `editmode` in settings, defaulting to
`"text"`, and seed the action from it. This is what makes a restored session or
rc-file reopen the layout the user left, which is the behaviour behind the
original report. Missing or invalid values fall back to the default via the
existing setting-normalisation path.

### D6. Bar visibility follows the on-screen canvas

A single logical active layer always exists (default text), but its control bar
is shown only when its canvas is on screen: the layer's notebook page in tabbed
mode, or the packed pane in a split view. Selecting the Image page leaves the
selection alone and hides the bar; selecting a layer page sets the layer and
shows the bar. Leaving split selects the tab matching the active layer. These
are the rules in the `active-layer-selection` spec.

### D7. The edit bar keeps only its minimum height

The outer `_vpaned` stacks the view above the edit bar and was defaulted to a
half split, which suited the old hidden-at-startup bar but now gives the visible
bar half the window. `_init_split_pane` gains an `end_at_minimum` mode used for
this pane: the divider is placed at `size - handle - end_child_min`, pinning the
bar to its measured minimum and leaving the rest to the view. The inner
image/layer panes keep the half-split default.

## Risks / Trade-offs

- [Tab/action feedback loop] → single guarded setter (D2); precedent
  `_in_tool_change`.
- [`_pack_viewer_tools` is the most layout-tested path] → update
  `test_pack_viewer_tools*` and the `_real_layout_window` suite deliberately;
  the canvas swap is the one behavioural change to assert.
- [Bar show/hide resizes the outer `vpaned` as tabs change] → acceptable and
  arguably desirable; `_init_split_pane` already applies the saved position
  once per process, so it will not fight user adjustments.
- [Annotation editing in split mode is newly reachable] → `_on_page_loaded`
  already creates both editors, and the selection/zoom bindings already exist
  for both canvases (session_mixins.py:427-451); no new editing path is added.
- [New persisted key could be malformed in an existing config] → validation
  already normalises unexpected types; default to `"text"`.

## Migration Plan

No on-disk data migration. A missing `editmode` key defaults to `"text"`, which
matches today's behaviour. Rollback is a revert of the commits; the extra config
key is simply ignored by the old code.

## Open Questions

None blocking. Whether to remember the split divider per active layer is out of
scope; the existing single divider behaviour is unchanged.

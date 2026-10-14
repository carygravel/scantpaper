## Context

The text layer editor is created once per session in
`LayerEditor.__init__` (session_mixins.py `_add_text_view_layers`). During
construction, `LayerControls.__init__` builds the sort combo, sets it to
`set_active(0)` ("confidence", layer.py:117), and that fires a `changed`
signal which emits `sort-changed`. Because `LayerEditor._connect_controls`
(layer.py:228, 260-261) runs *after* `LayerControls` is built, the initial
emit is dropped and `canvas._current_index` stays at its construction default
`"position"` (canvas.py:542). The combo label and the actual navigation order
therefore disagree until the user toggles the combo.

See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- Apply the combo's initially selected sort method to the canvas as soon as
  the editor is wired, so label and navigation agree from the start.
- Reuse the existing `sort-changed` → `_sort` path; do not introduce a
  separate mechanism.

**Non-Goals:**
- Persisting the user's last-chosen sort method across sessions.
- Changing which method is the default (confidence stays default).
- Any change to the annotation editor (it has no sort control).

## Decisions

- **Replay the initial selection after wiring.** In `_connect_controls`,
  after connecting `sort-changed` to `_sort`, read the combo's current active
  method and feed it through the same `_sort` handler. This makes the initial
  state flow through exactly the same code path as a manual toggle, so the two
  can never diverge.
- **Expose the combo's active method from `LayerControls`.** The sort combo is
  currently a local variable in `LayerControls.__init__` (layer.py:111-118),
  so `LayerEditor` cannot read it. Add a small accessor (e.g.
  `get_sort_method()`) on `LayerControls` returning the active method name via
  the existing `ComboBoxText.get_active_index()` (comboboxtext.py:60). This
  keeps the combo encapsulated while letting the editor replay its state.
- **Why replay rather than connect before `set_active(0)`:** moving the
  `set_active(0)` call after the connect would work for the very first
  construction but couples widget build order to handler wiring in a fragile
  way. Replaying the current value in the editor is explicit, testable, and
  robust to future ordering changes.

## Risks / Trade-offs

- **Double application on construction:** replaying calls `_sort` once, which
  merely sets `canvas._current_index`; it has no side effects beyond that, so
  replaying is safe and idempotent. → Mitigation: route through `_sort` which
  is idempotent.
- **Editor uses `_sort` directly vs. a public method:** `_sort` is private.
  Replaying from within `LayerEditor` (which owns `_sort`) avoids exposing it.
  → No risk.

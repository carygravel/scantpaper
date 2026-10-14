# Design: Fix split view panes collapsing on startup

## Context

The split view is built by `_pack_viewer_tools` (app_window.py), called once
at startup from `_add_text_view_layers` (session_mixins.py:498). The split
containers `_hpanei`/`_vpanei` are created fresh in `_populate_panes`.

The root cause is that the `.ui` and `_populate_panes` leave `_vnotebook`
packed in `_vpaned`'s pack1. `GtkPaned.pack1` silently keeps an existing pack1
child, so calling `_vpaned.pack1(_vpanei)` at startup never attaches the split
pane; the tabbed notebook stays in place and no split is shown. At runtime,
`_change_view_cb` first removes the old container, so switching views works,
which is why the split is only seen after cycling through the view modes.

The split panes also never get an explicit divider position, unlike the
thumbnail `_hpaned`, which gets `set_position(settings["thumb panel"])`
(app_window.py:431).

## Goals / Non-Goals

**Goals:**
- A horizontal/vertical split is visibly present on startup with both panes
  usable, before any image loads.
- An imported image is shown without requiring a view-mode change.
- The user's split ratio is retained across sessions (matching the existing
  `"thumb panel"` behaviour).

**Non-Goals:**
- Fixing annotations being hidden in split modes (the `a_canvas` is only
  packed in tabbed mode). Candidate follow-up; out of scope here.
- Changing the tabbed view behaviour.

## Decisions

### D0: Replace the existing `_vpaned` pack1 child before packing

At the start of `_pack_viewer_tools`, remove the current pack1 child of
`_vpaned` (via `get_child1()`/`remove()`) if any, so that `pack1` actually
attaches the intended container instead of silently keeping the leftover
`_vnotebook`. This is the core fix; without it the split panes are never
shown on startup. At runtime it is a no-op because `_change_view_cb` already
removed the old container.

### D1: Set an explicit divider position at pack time

Give each split pane an explicit position instead of leaving it to GtkPaned's
implicit, empty-children default. Because the window is unrealized at pack
time, apply the position on the first size allocation rather than inline.

- If a saved position exists for the active mode, restore it.
- Otherwise, on the first `size-allocate` of the pane, set the divider to half
  the allocated size so both sides are visible.

Implementation sketch (app_window.py):

- Add a helper `_init_split_pane(pane, saved_position)` that:
  1. If `saved_position` is not `None`, calls `pane.set_position(saved_position)`.
  2. Otherwise connects a one-shot `size-allocate` handler that sets
     `pane.set_position(alloc.width // 2)` (horizontal) or
     `alloc.height // 2` (vertical), then disconnects itself.

Call it from `_pack_viewer_tools`' horizontal and vertical branches.

### D2: Persist the split ratio in config

Add two settings, mirroring `"thumb panel"`:

- `"split panel h": None` and `"split panel v": None` in `config.DEFAULTS`
  (None means "use the half default" until the user first drags the divider).

On quit in `_can_quit` (file_menu_mixins.py:968), when the active view is
horizontal/vertical, save `_hpanei.get_position()`/`_vpanei.get_position()`
to the matching key, alongside the existing `"thumb panel"` write.

Restore from config in `_pack_viewer_tools` via D1.

### D3: Prefer the current active pane

Only persist/restore the pane that corresponds to the active `viewer_tools`
mode, so the two orientations do not clobber each other. The other orientation
keeps its own stored value or falls back to the half default.

## Risks / Trade-offs

- The one-shot `size-allocate` handler must disconnect itself reliably, or it
  will fight the user's later divider drags. A guard flag (or
  `handler_disconnect` in the callback) avoids this.
- Restoring an absolute pixel position can look wrong if the window size
  differs from the previous session. Acceptable: this matches the existing
  `"thumb panel"` behaviour and is what the user asked to preserve.
- The config gains two keys; `write_config`/`read_config` handle them like any
  other int/None setting with no special-casing required.
- Testing GTK pane layout headlessly is hard; the existing packing tests use
  `MagicMock`. Tests will assert the new helper is invoked with the right
  arguments and that a saved position is passed through, rather than asserting
  pixel geometry.

## Open Questions

- Whether persisting the ratio is worth the extra two config keys, or whether
  the half-default-only fix is sufficient for now (the observed bug is the
  collapsed pane, not the ratio). Flagged in the proposal as in-scope but
  droppable if it adds too much surface area.

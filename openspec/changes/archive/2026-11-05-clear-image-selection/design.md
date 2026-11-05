# Design

## Context

See `proposal.md` for the motivation and the delta spec for the behavior
contract.

`ImageView.selection` is a boxed `Gdk.Rectangle` property. Its `set_selection`
method already handles `None`: it stores `None`, redraws, emits
`selection-changed`, and fires `notify::selection`. The open question is not
how to clear the widget, but who coordinates the other consumers.

`ApplicationWindow` mirrors the rectangle in `settings["selection"]` through two
handlers: `selection-changed` for `set_selection` calls and
`notify::selection` for property writes such as the Crop dialog's binding. The
Crop dialog is cached in `_windowc` and is bidirectionally bound to the view
selection. Each `LayerEditor` listens to `notify::selection` to enable or
disable Add. Menu actions are registered in `_init_actions`, their sensitivity
is set in `_update_uimanager`, and shortcuts are registered in
`Application._setup_accelerators`.

## Goals / Non-Goals

**Goals:**

- One explicit clear path that resets the selection to `None`, not to a
  zero-size rectangle.
- Reach the clear action from the View menu, the toolbar, and Escape.
- Keep the action's sensitivity consistent with whether a rectangle exists.
- Leave cross-page persistence, clamping, and the selection's visual style
  unchanged.

**Non-Goals:**

- Changing the Selector's click behavior. A plain click still collapses the
  rectangle to a zero-size selection; making that a true clear is a separate
  change.
- Adding click-to-clear in the layer canvas.
- Changing how the selection is painted or themed.

## Decisions

### Decision: Clear at the window level

Add `ApplicationWindow.clear_image_selection` as the single policy point. It
owns the view selection, the `settings["selection"]` mirror, and the cached
Crop dialog; `ImageView` owns none of those. The widget-level primitive remains
`view.set_selection(None)`.

- Rationale: a clear action on `ImageView` would either leave the settings
  mirror and Crop dialog stale or force the widget to know about window state.
  A clear action in `Selector` would not work under Pan or when the layer pane
  has focus.
- Alternative considered: put `clear_selection` on `ImageView` and let the
  existing notifications update the rest. The `selection-changed` handler
  currently raises on `None`, and the Crop binding needs a safe `None` path
  anyway, so the wiring would still be split across the window.

### Decision: Register a normal window action, a menu item, and a toolbar button

Add `clear-image-selection` to `_init_actions`, expose it in `app.ui` in the
View menu after the Pan / Select / Select & pan group, and use the label
"Clear image selection". Add a toolbar button bound to the same action directly
after the three selection-tool buttons. The action name follows the user-facing
behavior and avoids the existing `delete_selection`, which means deleting
selected pages.

Use the stock `edit-clear` icon (resolved to `edit-clear-symbolic` by the icon
theme) with the tooltip "Clear image selection". The semantically ideal
`edit-select-none` is not shipped by the installed Adwaita theme, and
`edit-delete` would clash with the page-delete button, so `edit-clear` is the
closest stock match.

- Rationale: the app already exposes user commands as window actions with
  menu entries, toolbar buttons, and accelerators; the menu and toolbar make
  the capability discoverable, and the shared action gives both controls the
  same availability.
- Alternative considered: handle Escape only in
  `ApplicationWindow._on_key_press`. That is less code, but it leaves the
  command undiscoverable and outside the action/accelerator model. It remains
  a fallback if the accelerator proves to steal Escape from a text-editing
  control.

### Decision: Bind Escape through `_setup_accelerators`

Register `"win.clear-image-selection": ["Escape"]` alongside the other
shortcuts. Rely on GTK's normal dispatch so a focused control that handles
Escape keeps the key. The text-layer editing control registers no Escape
shortcut, so it does not shadow the accelerator.

- Rationale: this keeps all shortcuts in one table and matches how the menu
  action is activated.
- Alternative considered: extend `_on_key_press` with an editable-focus guard.
  That duplicates policy the accelerator already provides and adds a second
  keyboard path to maintain.

### Decision: Make `None` a first-class selection value everywhere

Three places currently assume a rectangle:

- `_view_selection_changed_callback` calls `sel.copy()` unconditionally.
  Change it to mirror `None`.
- `_on_view_selection_notify` ignores `None`, which would leave the old
  rectangle in `settings["selection"]`. Make it mirror `None` as well, and use
  it to update the clear action's sensitivity.
- `Crop.selection` dereferences `newval` for every dimension. Add a `None`
  branch that sets `_selection = None`, zeroes the spin buttons under the
  existing `_updating_selection` guard, and emits `changed-selection`.

- Rationale: the bidirectional binding and the two view handlers cannot be
  removed without changing unrelated behavior, so `None` has to be safe in all
  of them. Keeping two handlers is deliberate: the Crop binding writes the
  property without calling `set_selection`, so `notify::selection` still needs
  to update the settings mirror.
- Alternative considered: unbind the Crop property before clearing and rebind
  afterwards. The binding id is not retained today, and unbinding would add
  state that is easy to leak.

### Decision: Clear settings first, then the view, then the dialog

`clear_image_selection` sets `settings["selection"] = None` first, then calls
`view.set_selection(None)`, then clears the cached Crop selection if it is
still set. The later notifications are idempotent.

- Rationale: consumers that read the settings directly, such as the Crop
  action, see the cleared state immediately; the view call produces the repaint
  and the Add/action updates. The explicit dialog call covers the case where
  the binding is not active, and is safe because the setter now accepts `None`.
- Alternative considered: rely only on `view.set_selection(None)` and the
  binding. It works when everything is connected, but makes the handler's
  correctness depend on binding order and on both callbacks.

### Decision: Action sensitivity follows `view.selection`

Set the action enabled from `_on_view_selection_notify` with
`sel is not None`, and initialize it disabled. Do not add it to the
page-selection loop in `_update_uimanager`, which is driven by the thumbnail
selection and would enable the wrong thing.

- Rationale: the menu item and toolbar button are meaningful only when a
  rectangle exists, and the existing `notify::selection` path is already the
  authoritative signal for both `set_selection` and binding writes.
- Alternative considered: always enable the action and make it a no-op. That
  hides the state from the user and breaks the menu-availability convention.

## Risks / Trade-offs

- **Escape is a broad accelerator** → GTK delivers it to a focused control
  first. The text-layer `Gtk.TextView` registers no Escape shortcut, so it
  does not shadow the accelerator; a control that does register one keeps it.
- **Cached Crop dialog shows stale values** → zeroing its spin buttons on a
  `None` assignment keeps the dialog consistent with the cleared selection.
- **Zero-size click still counts as a selection** → out of scope here; the
  clear action is the only path to `None` until that is addressed separately.
- **Notifications during startup** → guard the action lookup and the view
  before updating sensitivity, because `_init_actions` runs before the viewer
  is packed.

## Migration Plan

No data migration. `settings["selection"]` is session-only and is already
excluded from the config file. The new action and menu item appear after
upgrading; an old zero-size or stale in-memory selection is discarded at the
next launch as before.

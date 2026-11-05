# Proposal

## Why

The image selection rectangle stays for the whole session and has no explicit
way to dismiss it. A plain click only collapses it to a zero-area rectangle,
which still counts as a selection: Add stays enabled, Crop sees a non-empty
selection, and a click in the layer pane or a switch to Pan leaves the box in
place. The only reliable reset is restarting the application. Users therefore
see a translucent grey box over their scans, mistake it for a scan artifact,
and have no obvious way to remove it.

## What Changes

- Add a window action `win.clear-image-selection` whose handler clears the
  shared image/layer selection to `None`, not to a zero-size rectangle.
- Expose the action in the View menu after the Pan / Select / Select & pan
  tools, with the translatable label "Clear image selection".
- Add a toolbar button next to the Pan / Select / Select & pan tools, using
  the stock `edit-clear` icon and the same action.
- Register `Escape` for `win.clear-image-selection` in
  `Application._setup_accelerators()`, so the action is reachable from the
  keyboard.
- Keep the action insensitive while no image selection exists and sensitive
  while one does, matching the other menu actions. Its state follows
  `view.selection`, not the thumbnail page selection.
- Make clearing reset every consumer that currently assumes a rectangle:
  the `settings["selection"]` mirror, the Add controls in both layer editors,
  and the Crop dialog's bound selection.
- Document the menu item and the Escape shortcut in `README.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `selection-across-pages`: adds an explicit end to the selection's lifetime.
  The rectangle can be cleared by the window action, which is also bound to
  Escape. After clearing it is not drawn, not re-applied on page changes, and
  not treated as a crop or Add region. Existing persistence across pages,
  clamping, and session-only storage are unchanged.

## Impact

- `src/scantpaper/app_window.py`: register `clear-image-selection` in
  `_init_actions`; add `clear_image_selection`; sync the action's sensitivity
  from `view.selection`. Make the selection callbacks handle `None`:
  `_view_selection_changed_callback` currently calls `sel.copy()`
  unconditionally, which raises for `None`, and `_on_view_selection_notify`
  ignores `None`, so the settings mirror would keep the old rectangle.
- `src/scantpaper/app.py`: add
  `"win.clear-image-selection": ["Escape"]` to `_setup_accelerators`.
- `src/scantpaper/app.ui`: add the View-menu item with a translatable label
  and the toolbar button bound to the same action.
- `src/scantpaper/dialog/crop.py`: accept `None` in the `selection` setter.
  The view selection is bidirectionally bound to the cached Crop dialog, whose
  setter currently dereferences the rectangle, so clearing would otherwise
  raise there.
- `src/scantpaper/layer.py`: no code change expected; `_update_add_state`
  already listens to `notify::selection` and disables Add on `None`.
- Tests: cover action activation, Escape activation, menu sensitivity,
  settings reset, Add disabled, Crop dialog reset, and clearing when the
  current value is already `None`.
- `README.md`: add the shortcut to the keyboard table and mention the View
  menu item and toolbar button.
- Translations: regenerate the template for the new menu label and tooltip.

Risk: `Escape` is a broad accelerator. The accelerator must not swallow
Escape from the OCR text editing control; a focused widget that handles the
key should keep it, and the text-layer view needs to be checked. Naming is
also easy to confuse: `delete_selection` already means "delete selected
pages", so the new method is `clear_image_selection`, not `clear_selection`.

# Design

## Context

See `proposal.md` - Why and `specs/dialog-layout/spec.md` for the required
behaviour.

The OCR dialog is a resizable `Gtk.Dialog` cached by
`ToolsMenuMixins.ocr_dialog()`. Its content area holds the page-range frame
followed by an `OCRControls` widget. `OCRControls` only creates the
**Advanced Tesseract engine parameters** `Gtk.Expander` when tesseract is
available; the same widget is also embedded in a `Gtk.ScrolledWindow` in the
scan dialog's Postprocessing page.

Two GTK behaviours drive the bug:

- A resizable GTK4 toplevel keeps its current size when its content's natural
  height drops. It does not shrink automatically.
- `Gtk.Widget` expand flags propagate through containers. The page-range
  radio buttons call `set_vexpand(True)` (carried over from GTK3's
  `pack_start(..., expand=True)`), so their inner box, `PageRange`, and the
  surrounding `Gtk.Frame` all report themselves as expanding. When the
  dialog has surplus height, the frame is the only content child that claims
  it, and the radios spread to fill it.

## Goals / Non-Goals

**Goals:**

- Collapsing the advanced expander returns the OCR dialog to the height it
  had immediately before expanding.
- A height the user chose manually is restored unchanged, and the current
  width is kept.
- The page-range frame keeps its natural height in every dialog, including
  when the user enlarges the window by hand.
- The scan dialog keeps its persisted size and is not resized by the embedded
  OCR controls.
- New behaviour is covered by tests that run in the existing headless test
  setup.

**Non-Goals:**

- Persisting or restoring the OCR dialog's size across runs.
- Changing the scan dialog's own size persistence.
- Replacing the expander with a popover or otherwise redesigning the
  advanced-options UI.
- Making the OCR dialog non-resizable.
- Changing page-range values, OCR options, settings, or session data.

## Decisions

### Restore an explicitly captured pre-expand height

When the expander becomes expanded, record
`dialog.get_surface().get_height()`. When it collapses, call
`dialog.set_default_size(surface.get_width(), recorded_height)`.

The `notify::expanded` callback fires before GTK grows the toplevel, so the
recorded value is the pre-expand height (verified under Xvfb).

Alternatives considered:

- **Fit to natural height on every collapse**
  (`set_default_size(width, -1)`): simpler and stateless, but discards a
  height the user chose manually. Rejected because the dialog should respect
  a user resize, consistent with the scan dialog's behaviour.
- **`Gtk.Expander:resize-toplevel`**: this is the built-in property for the
  purpose, but it only shrinks a **non-resizable** toplevel. With the OCR
  dialog made non-resizable, expanding it produced a 1023 px-wide window in
  testing because the wrapped hint label requested its unwrapped width, and
  it removed the user's ability to resize. Rejected.

### Keep the resize policy in the OCR dialog

Subscribe to the expander from `ToolsMenuMixins.ocr_dialog()`, not from
`OCRControls`. The scan dialog embeds `OCRControls` inside a scrolled page
and has its own persisted size; a global "resize the root window" rule in
`OCRControls` would shrink the scan dialog when its Postprocessing expander
is collapsed.

The dialog needs to reach the expander, so give `OCRControls` a small public
read-only `advanced_expander` property that returns the `Gtk.Expander` or
`None` when the Tesseract controls were not created. This avoids an
`AttributeError` for non-tesseract engines and keeps the dialog out of a
private attribute.

### Stop the page-range radios requesting vertical expansion

Remove `widget.set_vexpand(True)` from `PageRange.__init__`. The expand flags
are the cause: with them gone, the frame no longer computes as expanding and
cannot absorb surplus height.

Alternatives considered:

- **`frame.set_valign(Gtk.Align.START)` in `add_page_range()`**: keeps the
  frame at its natural height, but the frame still claims the surplus in the
  parent box, so the gap appears between the frame and the following row
  instead of below the controls. Removing the expand request addresses the
  cause and keeps the radios at their natural spacing in every dialog.

### Test at both the wiring and the window level

- Assert that `PageRange` does not compute as vertically expanding.
- Use the existing mocked OCR-dialog fixture to check that
  `notify::expanded` is connected, that expanding captures the surface
  height, and that collapsing calls `set_default_size()` with the saved
  height and current width. Cover the `surface is None` and absent-expander
  guards.
- Add one integration test that presents a real dialog with the page-range
  frame and an expander, runs the main loop, and asserts the surface height
  returns to its pre-expand value. The suite already runs under Xvfb.

## Risks / Trade-offs

- **Window-manager variance** -> `set_default_size()` is the standard way to
  request a specific toplevel size and worked under the suite's Xvfb; WM
  minimum-size constraints can still impose a floor, which is acceptable.
- **Signal timing** -> if a future GTK release emits `notify::expanded`
  after relayout, the captured height would be the expanded one. A window
  level test that compares the restored height guards against this.
- **The page-range radios no longer spread in enlarged dialogs** -> this is
  the intended visual change. It applies to every dialog using `PageRange`
  (Crop, Save, and the tool dialogs) and makes the frame hug its buttons
  instead of becoming a large empty box.
- **Cached OCR dialog** -> the dialog instance is reused after hiding. The
  saved height is reset after each collapse; if the dialog is hidden while
  the expander is open, it reopens at the expanded height with the expander
  still open, which matches the current state.
- **The dialog may be unmapped** -> `surface` can be `None`; the handler
  skips resizing in that case rather than raising.

## Migration Plan

None. There is no settings, data, or file-format migration; the change is
confined to dialog layout. Rolling back means reverting the code and tests.

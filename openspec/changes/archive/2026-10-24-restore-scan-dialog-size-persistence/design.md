# Design

## Context

Two places carry the scan dialog size between sessions:

- **Restore** (`scan_menu_item_mixins.scan_dialog`): a saved
  `scan_window_width`/`scan_window_height` is passed to the dialog as
  `default_width`/`default_height` constructor kwargs. This still works in GTK4
  (the kwargs map onto `Gtk.Window:default-width/height`, verified).
- **Save** (`file_menu_mixins._can_quit`): on quit,
  `self._windows.get_width()/get_height()` is written into those settings.

The GTK4 migration rewrote the save side from `Gtk.Window.get_size()` to
`Gtk.Widget.get_width()/get_height()` (`e4e067a2`, task 3.9). In GTK4 those
accessors return the widget's allocated content size, but they return 0 once a
toplevel window is hidden: `gtk_widget_real_hide()` explicitly zeroes
`priv->width/height`. GTK3's `Gtk.Window.get_size()` read the GdkWindow
geometry, which survived hiding.

The scan dialog is closed by being hidden, not destroyed (`hide_on_delete`):
the window close button (`Dialog._on_close_request`), the `_Close` button
(`dialog/scan.py`), and Escape (`Dialog._on_key_pressed`) all call
`self.hide()`. So at quit time the dialog is hidden, `get_width()` is 0, and a
`0` is persisted — which the restore guard
(`if settings["scan_window_width"]:`) treats as "no saved size".

## Goals / Non-Goals

**Goals:**
- The scan dialog reopens at its last size after an application restart.
- The live size is persisted when the user quits with the dialog still open.
- A session that only auto-opened the dialog in the background never erases the
  previously saved size.
- Correct the misleading migration comment in `_can_quit()`.

**Non-Goals:**
- Persisting the dialog *position* (GTK4 removed window positioning; behaviour
  unchanged from the migration).
- Changing the size behaviour of the main window or the message dialog, which
  are read while still visible and therefore unaffected.
- Refactoring the single "write settings on quit" flow in `_can_quit()`.

## Decisions

### Decision 1: Snapshot the size on the close path

Record the dialog size at the moment it is hidden, while the window is still
allocated. All three close paths funnel through `hide()`, so override `hide()`
on the `Scan` dialog class (`dialog/scan.py`):

```python
def hide(self) -> None:
    """Hide the dialog, recording its size first (GTK4 zeroes it on hide)."""
    self._last_window_size = (self.get_width(), self.get_height())
    super().hide()
```

Verified that a Python `hide()` override on a `Gtk.Dialog` subclass is
dispatched before GTK's C-side hide runs (which is what zeroes the size).
Putting the override on `Scan` (not the shared `Dialog` base) keeps the
snapshot scoped to the only dialog that persists its size.

*Alternatives rejected:*
- Connecting to the `hide` / `notify::visible` signals. GTK's `hide` signal is
  `G_SIGNAL_RUN_FIRST`, so its default handler (`gtk_widget_real_hide`)
  zeroes the size before user handlers and `notify::visible` fire — too late to
  read a live size.
- Writing the size into `settings` at close time. Splits settings-writing
  across two places, and `_can_quit` would still overwrite it with `get_width()`
  (0) unless that path changed too.
- Reading the size at quit from a child widget of the hidden window
  (children keep their allocation). Fragile and off by window decorations.
- `Gtk.Window.get_default_size()`. Returns the constructed default size, not
  the user-resized size.

### Decision 2: Persist the recorded size on quit, never write zeros

In `_can_quit()`, prefer the snapshot when the dialog was closed earlier, fall
back to a live read when it is still open, and skip the write when a read
yields zero:

```python
if self._windows:
    size = getattr(self._windows, "_last_window_size", None)
    if size is None:  # dialog still open: read its live size
        size = (self._windows.get_width(), self._windows.get_height())
    if size[0] and size[1]:  # never clobber a saved size with a zero
        self.settings["scan_window_width"] = size[0]
        self.settings["scan_window_height"] = size[1]
    logger.info("Killing Sane thread(s)")
    self._windows.thread.quit()
```

This covers every case:
- closed then quit → snapshot is the size the user last saw;
- quit with the dialog open → live read (dialog is visible, non-zero);
- background-opened and never shown → `_last_window_size` is `(0, 0)` and the
  live read is 0, so the previously saved value is kept.

The restore path in `scan_menu_item_mixins.scan_dialog` is unchanged.
The corrected `_can_quit()` comment records the GTK4 gotcha (hidden windows
report size 0) rather than the migration's incorrect "no size accessors".

## Risks / Trade-offs

- The fix depends on the `hide()` override running before GTK zeroes the size.
  Today every close path is Python and hits the override; a future refactor
  that hides the window through C-side GTK internals would bypass it and
  silently regress again. Low risk given the current call sites.
- One small instance attribute (`_last_window_size`) is added to `Scan`.
- The zero-guard means a genuinely zero-sized dialog (e.g. never allocated in
  an exotic WM-less session) deliberately keeps the old saved size rather than
  resetting it.
- Reading a hidden window's size is a GTK4-wide gotcha; the guard pattern is
  noted for any future window that persists its size after being hidden.
- Existing mock-based tests keep passing: `MockWindows` has no
  `_last_window_size`, so `_can_quit` falls back to its `get_width()` and
  `get_height()` mocks (which return 100).

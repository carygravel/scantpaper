## Why

The copy/cut/paste clipboard state is currently stored as a raw attribute
(`self.slist.clipboard`) on the document object and read/written directly
from three places (`edit_menu_mixins.py` handlers, `app_window.py` paste
enablement, and the test fixture). This couples UI/app state to the document's
internals, scatters clipboard logic, and forces the UI to manually refresh the
paste action after every cut/copy/paste. Promoting the clipboard to a
first-class, window-owned object decouples it from the document and lets the UI
react to changes via a signal.

## What Changes

- Introduce a window-owned `Clipboard` object (a `GObject.Object`) that holds
  the copied/cut page data and exposes a `has_data` read-out and a `changed`
  signal.
- Move clipboard *state* off the document: `slist.clipboard` is removed and
  replaced by `self.clipboard` on the application window.
- The document keeps its data operations (`copy_selection`, `cut_selection`,
  `paste_selection`); only the state storage moves.
- `edit_menu_mixins` cut/copy/paste handlers become thin: they read/write
  `self.clipboard.data` instead of `self.slist.clipboard`.
- `app_window` enables/disables the paste action by connecting to the
  clipboard's `changed` signal (replacing the read inside `_update_uimanager`).
- The clipboard persists for the lifetime of the window, so it survives a
  document being replaced (e.g. a new session).
- **Behavior change**: cutting with nothing selected sets the clipboard to
  empty (clears it), matching copy. Previously an empty cut left prior contents
  intact.
- **Behavior (preserved)**: the clipboard is *not* cleared after a paste; it
  remains until the next cut/copy. This is the existing "sticky" behavior.
- **BREAKING** (internal): `self.slist.clipboard` attribute is removed; tests
  and any callers that touch it are updated to use the new `Clipboard` object.

## Capabilities

### New Capabilities

- `clipboard`: The window-scoped copy/cut/paste clipboard, its data storage,
  its `changed` signal, and how cut/copy/paste and the paste-action enablement
  interact with it.

### Modified Capabilities

<!-- None: the existing selection-across-pages spec covers the crop selection
     rectangle and is unrelated to the copy/paste clipboard. -->

## Impact

- `src/scantpaper/edit_menu_mixins.py`: `cut_selection`, `copy_selection`,
  `paste_selection` read/write `self.clipboard.data` instead of
  `self.slist.clipboard`.
- `src/scantpaper/app_window.py`: add `self.clipboard = Clipboard()`; connect
  to `changed` to drive paste-action enablement; remove the
  `self.slist.clipboard` read in `_update_uimanager`.
- `src/scantpaper/basedocument.py`: remove the `self.clipboard = None`
  initialiser (line 57); `copy_selection`/`cut_selection`/`paste_selection`
  data operations are unchanged.
- `src/scantpaper/clipboard.py` (new): the `Clipboard` GObject class.
- `src/scantpaper/tests/test_edit_menu_mixins.py`: update fixture/tests that
  poke `slist.clipboard` to use the new `Clipboard`.
- `src/scantpaper/tests/` (new): tests for the `Clipboard` object (data
  storage, `has_data`, `changed` signal, empty-cut clearing).
- No new dependencies.

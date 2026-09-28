## 1. Clipboard object

- [x] 1.1 Create `src/scantpaper/clipboard.py` with a `Clipboard(GObject.Object)`
      class exposing a `changed` signal, a `data: list[list[object]] | None`
      property whose setter emits `changed`, and a read-only `has_data: bool`
      derived from `data`. Use the typed `property_()` helper from
      `scantpaper.gobject`.
- [x] 1.2 Add `src/scantpaper/tests/test_clipboard.py` covering: storing data,
      empty copy/cut leaves `has_data` false, setting `data` emits `changed`,
      and clearing (setting `data = None`) emits `changed`.

## 2. Wire clipboard into the window

- [x] 2.1 In `ApplicationWindow`, instantiate `self.clipboard = Clipboard()`
      and, once `_actions` is populated, connect its `changed` signal to a
      handler that sets `self._actions["paste"].set_enabled(self.clipboard.has_data)`.
- [x] 2.2 In `_update_uimanager` (`app_window.py:797`), remove the
      `self._actions["paste"].set_enabled(bool(self.slist.clipboard))` read so
      the signal handler is the single owner of paste enablement.

## 3. Thin out the edit menu handlers

- [x] 3.1 Update `cut_selection` in `edit_menu_mixins.py` to assign
      `self.clipboard.data = self.slist.cut_selection()` instead of
      `self.slist.clipboard`.
- [x] 3.2 Update `copy_selection` to assign
      `self.clipboard.data = self.slist.copy_selection()`.
- [x] 3.3 Update `paste_selection` to guard on `self.clipboard.data is None`
      and pass `data=self.clipboard.data` to the two `slist.paste_selection`
      branches (with and without selected pages), preserving behaviour.

## 4. Remove clipboard from the document

- [x] 4.1 Delete `self.clipboard = None` from `BaseDocument.__init__`
      (`basedocument.py:57`).

## 5. Update tests

- [x] 5.1 Update `tests/test_edit_menu_mixins.py` fixture and the cut/copy/paste
      tests to set and assert `self.clipboard.data` (via a `Clipboard` instance
      or mock) instead of `slist.clipboard`, including the empty-cut-clears case.
- [x] 5.2 Add/extend tests for the paste-action enablement driven by the
      clipboard `changed` signal in `tests/test_app_window.py`.

## 6. Quality gates

- [x] 6.1 Run `pytest` and confirm the full suite passes with coverage at or
      above the existing thresholds.
- [x] 6.2 Run `ruff format` and `ruff check`; resolve all findings.
- [x] 6.3 Run `ty check .` and confirm no diagnostics.

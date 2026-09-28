## Context

See proposal.md for motivation. Current state: clipboard data lives as a raw
attribute `self.slist.clipboard` on the `Document` (`BaseDocument`), read and
written directly in three places:

- `edit_menu_mixins.py` — `cut_selection`/`copy_selection`/`paste_selection`
  handlers set and read `self.slist.clipboard` and call `_update_uimanager()`.
- `app_window.py:797` — `_update_uimanager` enables the paste action via
  `bool(self.slist.clipboard)`.
- `tests/test_edit_menu_mixins.py` — the fixture and several tests poke
  `slist.clipboard`.

The document already owns the data operations (`copy_selection`,
`cut_selection`, `paste_selection` in `basedocument.py:355-374`); `paste`
clones pages via `thread.send("clone_pages", ...)`. The codebase already has an
idiomatic GObject signal pattern (`canvas.py` `__gsignals__`) and a typed
`property_()` helper in `gobject.py`.

## Goals / Non-Goals

**Goals:**
- Give the clipboard a first-class, window-owned home decoupled from any single
  `Document`.
- Let the UI react to clipboard changes via a signal instead of manually
  calling `_update_uimanager` after each cut/copy/paste.
- Keep the document's data operations unchanged.

**Non-Goals:**
- Changing how pages are copied, cut, or pasted at the document/thread level.
- Changing clipboard "stickiness" after paste (retained until next cut/copy).
- Introducing a system/OS clipboard or cross-window clipboard.

## Decisions

### Decision: A window-owned `Clipboard` GObject
Create `src/scantpaper/clipboard.py` with a `Clipboard(GObject.Object)` class
holding the page data and emitting a `changed` signal. Instantiate it once on
the application window (`self.clipboard = Clipboard()` in
`ApplicationWindow`), not on the `Document`.

- **Why**: clipboard is app/UI state, not document state; window ownership
  makes it survive document replacement (new session).
- **Alternative considered**: keep it on the document but wrap in accessors.
  Rejected — it keeps the conceptual misplacement and doesn't enable a signal.

### Decision: `data` stored via a typed property that emits `changed`
`Clipboard` exposes `data: list[list[object]] | None` and `has_data: bool`.
The `data` setter emits `changed`; `has_data` is a read-only derived value.
Use the existing typed `property_()` helper from `gobject.py`.

- **Why**: consistent with the codebase's typed-GObject property pattern and
  gives a single choke point that always fires the signal.
- **Alternative considered**: explicit `set_data()/clear()` methods. Rejected
  for a smaller API surface; a plain `data` setter with `has_data` reads
  naturally.
- Empty-cut semantics: `cut_selection`/`copy_selection` return `None` when
  nothing is selected, so `self.clipboard.data = None` naturally clears it.

### Decision: Paste-action enablement via the `changed` signal
`app_window` connects to the clipboard's `changed` signal and sets
`self._actions["paste"].set_enabled(self.clipboard.has_data)` in the handler.
Remove the `bool(self.slist.clipboard)` read from `_update_uimanager`.

- **Why**: eliminates the implicit coupling where every cut/copy/paste handler
  must remember to call `_update_uimanager` for the paste action to stay fresh.
- **Trade-off**: the paste action is enabled/disabled by the signal handler,
  which must be connected once at window setup; ensure the action object exists
  before connecting (connect after `_actions` is populated).

### Decision: Handlers become thin
`edit_menu_mixins` cut/copy/paste handlers read/write `self.clipboard.data`
only:

```python
def cut_selection(self, _a, _p) -> None:
    self.clipboard.data = self.slist.cut_selection()
    self._update_uimanager()

def copy_selection(self, _a, _p) -> None:
    self.clipboard.data = self.slist.copy_selection()
    self._update_uimanager()

def paste_selection(self, _a, _p) -> None:
    if self.clipboard.data is None:
        return
    pages = self.slist.get_selected_indices()
    if pages:
        self.slist.paste_selection(data=self.clipboard.data, dest=pages[-1],
                                   how="after", select_new_pages=True)
    else:
        self.slist.paste_selection(data=self.clipboard.data,
                                   select_new_pages=True)
    self._update_uimanager()
```

`_update_uimanager` calls are retained for the other actions' refresh; the
paste enablement itself is now handled by the signal. Document-level
`cut_selection`/`copy_selection`/`paste_selection` are untouched.

### Decision: Remove `clipboard` from the document
Delete `self.clipboard = None` from `BaseDocument.__init__` (`basedocument.py:57`).

- **Why**: the document no longer owns clipboard state.
- **Alternative considered**: leave it and treat `slist.clipboard` as legacy.
  Rejected — leaving dead state invites confusion and drift.

## Risks / Trade-offs

- **Connect-before-use ordering** — the `changed` signal handler touches
  `self._actions["paste"]`, which must exist when the signal fires. →
  Connect to `changed` only after `_actions` is populated (window setup), and
  have the handler guard on the action being present.
- **Signal vs. `_update_uimanager` duplication** — both the signal handler and
  `_update_uimanager` may touch paste enablement. → Make the signal handler the
  single owner of paste enablement; remove the read from `_update_uimanager`.
- **Behavior change for empty cut** — clearing the clipboard on an empty cut is
  a deliberate change. It is consistent with copy and simpler; the spec records
  it so it is reviewed as intended, not accidental.
- **Coverage** — moving state adds a new module and modifies tests; the
  coverage threshold must not regress. → Add a dedicated `test_clipboard.py`
  covering storage, `has_data`, the `changed` signal, and empty-cut clearing;
  update `test_edit_menu_mixins.py`.

## Migration Plan

This is an internal refactor with no external API. Steps:
1. Add `src/scantpaper/clipboard.py` and its tests.
2. Wire `self.clipboard` into `ApplicationWindow` and connect the `changed`
   signal; remove the `_update_uimanager` paste read.
3. Rewrite `edit_menu_mixins` handlers to use `self.clipboard.data`.
4. Remove `self.clipboard` from `BaseDocument`; update `test_edit_menu_mixins`.
5. Run `pytest`, `ruff format`, `ruff check`, and `ty check .`.

Rollback: revert the individual commits; each step is independently reversible
because document data operations are unchanged.

## Open Questions

None — the deferred unknowns (e.g. cross-window clipboard, OS clipboard) are
explicit non-goals and would change scope, so they are out of this change.

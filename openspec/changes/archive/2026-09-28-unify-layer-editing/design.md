# Design: Unify text layer and annotation editing

## Context

See proposal.md - Why. The relevant current state:

- `SessionMixins` holds five near-identical handler pairs
  (`_create_txt_canvas`/`_create_ann_canvas`, `_edit_ocr_text`/`_edit_annotation`,
  `_ocr_text_button_clicked`/`_ann_text_ok`, `_ocr_text_add`/`_ann_text_new`,
  `_ocr_text_delete`/`_ann_text_delete`) plus `_ocr_text_copy` (no annotation
  equivalent). They differ only by page attribute, canvas, and import method.
- `ApplicationWindow` creates two `Canvas` widgets (`t_canvas`/`a_canvas`,
  app_window.py:487-515) and places them in panes/notebook via
  `_pack_viewer_tools` (app_window.py:596), driven by `viewer_tools`.
- The active control bar is chosen by the `editmode` action via
  `_edit_mode_callback` (session_mixins.py:605), which only toggles the two
  control bars, not the canvases. The two canvases are therefore never
  simultaneously visible.
- `TextLayerControls` (text_layer_control.py) is a `Gtk.Box` widget; the
  annotation editor reuses it but hand-builds its own bar (session_mixins.py:454)
  and leaves sort/navigation buttons unwired.
- Both layers are bboxtree JSON stored on `Page` (`text_layer`, `annotations`);
  `Page.import_hocr`/`import_annotations` parse hOCR into each slot.

## Goals / Non-Goals

**Goals:**
- One `LayerEditor` class that owns canvas + control bar + edit handlers for a
  single editable layer, parameterized by which slot it edits and which
  features it exposes.
- Fix the two annotation bugs (delete writes to text layer; new guards on
  `text_layer`) by construction rather than by patching.
- Remove the dead, unwired sort/navigation buttons from the annotation bar.
- Keep the two canvases separate and never simultaneously visible.

**Non-Goals:**
- Merging the two canvases into one.
- Changing canvas placement / `viewer_tools` layout behaviour.
- Changing `Page`'s data model or `import_hocr`/`import_annotations`.
- Changing how `editmode` interacts with the toolbar at the action level.

## Decisions

### D1. New module `src/scantpaper/layer.py` hosts both the controller and the control bar

Move `TextLayerControls` out of `text_layer_control.py` into `layer.py`,
generalizing it into a `LayerControls` widget driven by feature flags
(`sort`, `nav`, `copy`). Host `LayerEditor` alongside it. Delete
`text_layer_control.py` and update the single importer (`session_mixins.py:26`
and `app_window.py`).

- *Why a new module?* `text_layer_control.py` is already misnamed (reused for
  annotations), and the new class is a controller, not just a widget. A fresh
  `layer.py` gives a neutral home for `LayerEditor` + `LayerControls`.
- *Alternative:* grow `text_layer_control.py`. Rejected: the name over-promises
  and hides that it now hosts a controller, not a widget.
- *Alternative:* split widget and controller across two modules. Rejected
  (YAGNI): they only ever compose as a pair.

### D2. Dependency injection into `LayerEditor` (narrow collaborators), not the window

The editor needs only a few window-level collaborators; inject them rather than
the whole window:

```python
class LayerEditor:
    def __init__(
        self,
        *,
        page_attr: str,                 # "text_layer" | "annotations"
        import_method: str,             # "import_hocr" | "import_annotations"
        sort: bool = False,
        nav: bool = False,
        copy: bool = False,
        view: ImageView,
        get_page: Callable[[], Page | None],
        parse: Callable[[str, Callable[[object], None]], None],  # bboxtree parse
        persist: Callable[[Page], None],  # import_* + thread.set_text
    ):
        self.canvas = Canvas()
        self.controls = LayerControls(sort=sort, nav=nav, copy=copy)
```

- `create(page, offset)`: parse the slot's JSON and `canvas.set_text(...)` with
  `edit_callback=self.edit`; or `canvas.clear_text()` when empty.
- `edit(bbox)`: set the current bbox, fill the control bar buffer, zoom to
  selection, `canvas.set_index_by_bbox`.
- `add`/`copy`/`delete`/`ok`: operate on `self.canvas`, then `self.persist(page)`.
- `set_active(bool)`: show/hide `self.controls`.

- *Why injection over `host=`?* The existing tests already mock exactly these
  collaborators (`view`, `_current_page`, `slist.thread`, canvases, control
  bars), so a narrow-collaborator constructor maps directly onto them and keeps
  the class standalone and unit-testable.
- *Alternative:* `LayerEditor(host)` reading `host._current_page`,
  `host.view`, `host.slist.thread`. More idiomatic to this codebase (which
  passes `self` widely) but couples the class to `ApplicationWindow` internals
  and complicates testing. Leaning: injection.

### D3. The class uses `page_attr`/`import_method`, so the bugs cannot recur

All add/delete/ok paths read the current bbox from `self.canvas`, persist via
`getattr(page, self.import_method)(self.canvas.hocr())`, and write to
`getattr(page, self.page_attr)`. The old `_ann_text_delete`'s wrong
`import_hocr` + `t_canvas` reference becomes impossible because there is no
separate canvas to confuse. The old `_ann_text_new`'s wrong `hasattr(text_layer)`
guard becomes `hasattr(page, self.page_attr)`.

### D4. `editmode` toggling stays in the window via `set_active`

`_edit_mode_callback` (session_mixins.py:605) becomes:

```python
self._text_editor.set_active(mode == "text")
self._ann_editor.set_active(mode == "annotation")
```

Canvas placement (`_pack_viewer_tools`) is untouched and keeps living in the
window, preserving the "never simultaneously visible" invariant.

## Risks / Trade-offs

- [The window still owns layout and editmode, so `LayerEditor` is only a
  partial extraction; `SessionMixins` keeps some wiring.] → Acceptable: layout
  genuinely belongs to the window; the class owns the duplication that caused
  the bugs.
- [Dependency injection adds constructor boilerplate and risks an awkward
  `persist` closure.] → Mitigation: keep the injected callables narrow and
  documented; the window builds them once.
- [Renaming/moving `TextLayerControls` churns `session_mixins.py`,
  `app_window.py`, and tests.] → Accepted; the file is already misnamed, and the
  churn is localized (one production importer).
- [Feature-flag control bar must keep the text layer's sort/nav/copy behaviour
  byte-identical.] → Mitigation: text editor constructed with all three flags
  true; existing `test_text_layer_control.py` cases preserved in the new tests.

## Migration Plan

Refactor in place, guided by the existing tests (which already mock the
collaborators). Sequence: introduce `layer.py` (`LayerControls` then
`LayerEditor`) with new unit tests; rewire `app_window.py` to construct the two
editors; strip the duplicated handlers from `session_mixins.py`; delete
`text_layer_control.py`. Each step keeps `pytest`, `ruff`, and `ty check .`
green. No data or on-disk migration; no rollback concern beyond reverting the
commit.

## Open Questions

- Whether to keep the old `TextLayerControls` name as an alias during the
  transition or delete it outright. Deferrable without affecting the approach.

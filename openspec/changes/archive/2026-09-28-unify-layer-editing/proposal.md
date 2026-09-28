# Unify text layer and annotation editing

## Why

Text layer editing and annotation editing are two parallel, near-identical
pipelines in `SessionMixins`: separate canvases, separate control bars, and five
pairs of copy-pasted handler methods that differ only in which page attribute,
which canvas, and which import method they touch. The duplication has already
produced bugs: the annotation delete path writes to the text layer, and the
annotation "new" path guards on the wrong page attribute. Consolidating the two
into a single editing class removes the duplication and makes these bugs
impossible by construction.

## What Changes

- Introduce a single `LayerEditor` class that owns the canvas, the control bar,
  and the add/copy/delete/ok handlers for one editable layer, parameterized by
  which page attribute it edits (`text_layer` vs `annotations`), which import
  method it uses to persist (`import_hocr` vs `import_annotations`), and which
  features it exposes (sort, navigation, copy).
- Instantiate two `LayerEditor`s in `ApplicationWindow`: one for the text layer
  and one for annotations. The two canvases remain separate widgets and remain
  never simultaneously visible (unchanged: canvas placement is still driven by
  `viewer_tools`, and the active control bar by `editmode`).
- Replace the five duplicated handler pairs (`_create_txt/ann_canvas`,
  `_edit_ocr_text/_edit_annotation`, `_ocr_text_*`/`_ann_text_*`) with the
  class methods.
- Make the control bar (`TextLayerControls`) configurable by feature flags so
  the annotation editor no longer shows dead, unwired sort/navigation buttons
  and no longer needs a hand-built duplicate bar.
- **BREAKING** (internal): `_ann_text_delete` and `_ann_text_new` change
  behaviour to target annotations (not the text layer) — this is the bug fix
  toward the intended behaviour.
- Rename/re-home the module so its name no longer over-promises
  (`text_layer_control.py` is already reused for annotations).

No user-visible behaviour change other than the two bug fixes above.

## Capabilities

This is a pure refactor: no spec-level behaviour changes (the only behavioural
changes are the two bug fixes that restore the *intended* annotation behaviour).
No capability requirements change, so the change opts out of specs via
`skip_specs: true`.

### New Capabilities

- none

### Modified Capabilities

- none

## Impact

- `src/scantpaper/session_mixins.py` — the largest change; the five duplicated
  handler pairs and `_add_text_view_layers` are replaced by wiring two
  `LayerEditor` instances. `_edit_mode_callback` shrinks to toggling the two
  editors' control bars.
- `src/scantpaper/app_window.py` — constructs the two `LayerEditor`s and places
  their canvases in the panes (layout logic unchanged).
- `src/scantpaper/text_layer_control.py` — control bar becomes feature-flag
  driven; likely renamed or absorbed into the new class's module.
- New module (e.g. `src/scantpaper/layer.py`) — hosts `LayerEditor`.
- `src/scantpaper/page.py` — unchanged (still exposes `import_hocr` /
  `import_annotations`; the class chooses which to call).
- Tests: `tests/test_session_mixins.py` and `tests/test_text_layer_control.py`
  are rewritten to exercise the new class instead of the mixed-in handlers.
- No new dependencies.

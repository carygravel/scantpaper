# Tasks: Unify text layer and annotation editing

Reference design.md for the approach. This is a pure refactor (no specs); the
two annotation bug fixes fall out of the design by construction.

## 1. Introduce `LayerControls` widget

- [x] 1.1 Create `src/scantpaper/layer.py` and move the `TextLayerControls`
      widget there, renaming it `LayerControls`.
- [x] 1.2 Generalize the widget with feature flags (`sort`, `nav`, `copy`)
      so the annotation bar no longer builds dead, unwired sort/navigation
      buttons and no longer needs a hand-built duplicate bar.

## 2. Implement `LayerEditor`

- [x] 2.1 Add a `LayerEditor` class in `layer.py` with a narrow-collaborator
      constructor: `page_attr`, `import_method`, feature flags, `view`,
      `get_page`, `parse`, `persist` (design.md - D2).
- [x] 2.2 Implement `create(page, offset)` to parse the slot's JSON via `parse`
      and `canvas.set_text(...)` with `edit_callback=self.edit`, or
      `canvas.clear_text()` when empty (design.md - D3).
- [x] 2.3 Implement `edit(bbox)`: set current bbox, fill the control buffer,
      zoom to selection, and `canvas.set_index_by_bbox`.
- [x] 2.4 Implement `add`/`copy`/`delete`/`ok` handlers operating on
      `self.canvas` and persisting via `getattr(page, self.import_method)`
      then `self.persist(page)`.
- [x] 2.5 Implement `set_active(bool)` to show/hide `self.controls`.
- [x] 2.6 Ensure all add/delete/ok paths read/write only `self.page_attr` and
      `self.canvas`, so the old `_ann_text_delete` (wrote to the text layer)
      and `_ann_text_new` (guarded on `text_layer`) bugs are impossible.

## 3. Rewire `ApplicationWindow`

- [x] 3.1 Construct two `LayerEditor`s in `app_window.py`: a text editor
      (`page_attr="text_layer"`, `import_method="import_hocr"`, sort/nav/copy)
      and an annotation editor (`page_attr="annotations"`,
      `import_method="import_annotations"`), replacing `t_canvas`/`a_canvas`
      and the `_ocr_text_hbox`/`_ann_hbox` construction.
- [x] 3.2 Update `_pack_viewer_tools` to place each editor's `canvas` in the
      panes/notebook exactly as today (layout behaviour unchanged).

## 4. Strip duplicated handlers from `SessionMixins`

- [x] 4.1 Replace `_add_text_view_layers` with wiring that packs each editor's
      `controls` into the edit container and connects their signals.
- [x] 4.2 Replace `_create_txt_canvas`/`_create_ann_canvas`,
      `_edit_ocr_text`/`_edit_annotation`, and the `_ocr_text_*`/`_ann_text_*`
      pairs with the corresponding `LayerEditor` methods.
- [x] 4.3 Replace `_edit_mode_callback` with `set_active` toggling on the two
      editors (design.md - D4).

## 5. Remove the old module

- [x] 5.1 Update the `TextLayerControls` importer (`session_mixins.py:26` and
      `app_window.py`) to `LayerControls`/`LayerEditor`.
- [x] 5.2 Delete `src/scantpaper/text_layer_control.py`.

## 6. Tests and quality gates

- [x] 6.1 Add/rewrite `tests/test_layer.py` covering `LayerEditor` add, copy,
      delete, ok, create, and edit, including the two formerly-buggy annotation
      paths.
- [x] 6.2 Rewrite `tests/test_text_layer_control.py` cases against
      `LayerControls` (sort/nav/copy flag behaviour) and
      `tests/test_session_mixins.py` annotation/text cases against the editors.
- [x] 6.3 Run `pytest`, `ruff format`, `ruff check`, and `ty check .`; confirm
      no new uncovered/partially-covered lines and no new lint/type diagnostics.

"""Test the LayerControls widget and LayerEditor controller."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING, Any, cast

from scantpaper.basethread import Response, ResponseType
from scantpaper.bboxtree import Bboxtree
from scantpaper.const import EMPTY, POINTS_PER_INCH
from scantpaper.layer import LayerControls, LayerEditor
from scantpaper.loop_helpers import safe_mainloop
from scantpaper.page import Page

if TYPE_CHECKING:
    import pytest

    from scantpaper.canvas import Bbox
    from scantpaper.docthread import DocThread
    from scantpaper.imageview import ImageView

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib  # noqa: E402


def make_editor(
    mocker: pytest.MockerFixture,
    *,
    page_attr: str = "text_layer",
    features: tuple[str, ...] = (),
) -> tuple[LayerEditor, Page, DocThread, ImageView]:
    """Build a LayerEditor with mocked collaborators.

    Returns (editor, page, thread, view).
    """
    view = cast("ImageView", mocker.Mock())
    page = cast("Page", mocker.MagicMock())
    page.text_layer = "existing"
    page.annotations = "existing"
    page.get_size.return_value = (100, 100)
    thread = cast("DocThread", mocker.Mock())
    get_page = mocker.Mock(return_value=page)
    editor = LayerEditor(
        page_attr=page_attr,
        view=view,
        thread=thread,
        get_page=get_page,
        features=features,
    )
    return editor, page, thread, view


# ---------------------------------------------------------------------------
# LayerControls widget
# ---------------------------------------------------------------------------


def test_layer_controls_text_features_present() -> None:
    """The text-layer bar has sort, navigation, and copy controls."""
    controls = LayerControls(sort=True, nav=True, copy=True)
    tooltips = {
        child.get_tooltip_text()
        for child in controls.get_children()
        if child.get_tooltip_text() is not None
    }
    assert "Select sort method for OCR boxes" in tooltips
    assert "Go to least confident text" in tooltips
    assert "Go to most confident text" in tooltips
    assert "Duplicate text" in tooltips
    assert "Accept corrections" in tooltips
    assert "Add text" in tooltips
    assert "Delete text" in tooltips


def test_layer_controls_annotation_bar_has_no_sort_nav_copy() -> None:
    """The annotation bar must not expose sort, navigation, or copy controls."""
    controls = LayerControls()
    tooltips = {
        child.get_tooltip_text()
        for child in controls.get_children()
        if child.get_tooltip_text() is not None
    }
    assert "Select sort method for OCR boxes" not in tooltips
    assert "Go to least confident text" not in tooltips
    assert "Duplicate text" not in tooltips
    assert "Accept corrections" in tooltips
    assert "Add text" in tooltips
    assert "Delete text" in tooltips


def test_layer_controls_sort_signal() -> None:
    """Changing the sort combo emits sort-changed with the method name."""
    controls = LayerControls(sort=True)
    received: list[str] = []
    controls.connect("sort-changed", lambda _w, value: received.append(value))

    sort_combo = None
    for child in controls.get_children():
        if child.get_tooltip_text() == "Select sort method for OCR boxes":
            sort_combo = child
            break
    assert sort_combo is not None

    sort_combo.set_active(1)
    assert received[-1] == "position"
    sort_combo.set_active(0)
    assert received[-1] == "confidence"


def test_layer_controls_cancel_button_hides() -> None:
    """The cancel button hides the control bar."""
    controls = LayerControls()
    controls.show_all()
    cancel = None
    for child in controls.get_children():
        if child.get_tooltip_text() == "Cancel corrections":
            cancel = child
            break
    assert cancel is not None
    cancel.clicked()
    assert not controls.get_visible()


def test_layer_controls_set_add_enabled_switches_tooltip() -> None:
    """set_add_enabled() toggles sensitivity and explains the disabled state."""
    controls = LayerControls()
    controls.set_add_enabled(enabled=True)
    assert controls.add_button.get_sensitive()
    assert controls.add_button.get_tooltip_text() == "Add text"

    controls.set_add_enabled(enabled=False)
    assert not controls.add_button.get_sensitive()
    assert "rectangle" in controls.add_button.get_tooltip_text()


# ---------------------------------------------------------------------------
# LayerEditor - Add button gating
# ---------------------------------------------------------------------------


def test_add_button_ghosted_without_selection(mocker: pytest.MockerFixture) -> None:
    """The Add control is disabled when there is no selection."""
    editor, _page, _thread, view = make_editor(mocker)
    view.get_selection.return_value = None
    editor._update_add_state()
    assert not editor.controls.add_button.get_sensitive()


def test_add_button_enabled_with_selection(mocker: pytest.MockerFixture) -> None:
    """The Add control is enabled once a selection exists."""
    editor, _page, _thread, view = make_editor(mocker)
    view.get_selection.return_value = Gdk.Rectangle()
    editor._update_add_state()
    assert editor.controls.add_button.get_sensitive()


def test_add_button_tooltip_explains_disabled(mocker: pytest.MockerFixture) -> None:
    """The disabled Add control tells the user a rectangle is required."""
    editor, _page, _thread, view = make_editor(mocker)
    view.get_selection.return_value = None
    editor._update_add_state()
    assert "rectangle" in editor.controls.add_button.get_tooltip_text()


def test_selection_drawn_commits_to_view(mocker: pytest.MockerFixture) -> None:
    """A rectangle drawn in the layer pane becomes the shared selection."""
    editor, _page, _thread, view = make_editor(mocker)
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = 1, 2, 3, 4
    editor._on_selection_drawn(editor.canvas, rect)
    view.set_selection.assert_called_once_with(rect)


# ---------------------------------------------------------------------------
# LayerEditor - edit
# ---------------------------------------------------------------------------


def test_edit_sets_focus(mocker: pytest.MockerFixture) -> None:
    """edit() focuses the canvas and control bar on the given bbox."""
    editor, _page, _thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    bbox = mocker.Mock()
    bbox.text = "word"
    bbox.bbox = "rect"

    editor.edit(bbox)

    assert editor._current_bbox is bbox
    editor.controls.textbuffer.set_text.assert_called_with("word")
    editor.controls.show_all.assert_called()
    view.set_selection.assert_called_with("rect")
    view.setzoom_is_fit.assert_called_with(zoom_to_fit=False)
    view.zoom_to_selection.assert_called()
    editor.canvas.set_index_by_bbox.assert_called_with(bbox)


def test_ok_and_delete_with_nothing_focused_are_inert(
    mocker: pytest.MockerFixture,
) -> None:
    """Accepting or deleting with no focused slice changes nothing."""
    editor, page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor._current_bbox = None

    editor.ok(None)
    editor.delete(None)

    editor.canvas.update_word.assert_not_called()
    editor.canvas.delete_word.assert_not_called()
    page.import_hocr.assert_not_called()
    thread.set_text.assert_not_called()


def test_edit_none_clears_control(mocker: pytest.MockerFixture) -> None:
    """edit(None) empties the control and focuses nothing."""
    editor, _page, _thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.edit(None)
    assert editor._current_bbox is None
    editor.controls.textbuffer.set_text.assert_called_once_with(EMPTY)
    editor.canvas.set_index_by_bbox.assert_not_called()


# ---------------------------------------------------------------------------
# LayerEditor - ok / copy / delete
# ---------------------------------------------------------------------------


def test_ok_commits_and_reedits(mocker: pytest.MockerFixture) -> None:
    """ok() updates the box, imports hocr, persists, and re-edits."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "corrected"
    view.get_selection.return_value = "sel"
    bbox = mocker.Mock()
    bbox.text = "old"
    editor._current_bbox = bbox

    editor.ok(None)

    editor.canvas.update_word.assert_called_once_with(bbox, "corrected", "sel")
    page.import_hocr.assert_called_with(editor.canvas.hocr())
    thread.set_text.assert_called_once_with(page.id, page.text_layer)
    editor.controls.textbuffer.set_text.assert_called()


def test_copy_duplicates_box(mocker: pytest.MockerFixture) -> None:
    """copy() adds a box and commits."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "dup"
    view.get_selection.return_value = "sel"
    new_bbox = mocker.Mock()
    editor.canvas.add_box.return_value = new_bbox

    editor.copy(None)

    editor.canvas.add_box.assert_called_with(text="dup", bbox="sel")
    page.import_hocr.assert_called_with(editor.canvas.hocr())
    thread.set_text.assert_called_once_with(page.id, page.text_layer)
    assert editor._current_bbox is new_bbox


def test_delete_removes_box(mocker: pytest.MockerFixture) -> None:
    """delete() removes the current box and commits."""
    editor, page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    current = mocker.Mock()
    editor.canvas.get_current_bbox.return_value = current
    bbox = mocker.Mock()
    editor._current_bbox = bbox

    editor.delete(None)

    editor.canvas.delete_word.assert_called_once_with(bbox)
    page.import_hocr.assert_called_with(editor.canvas.hocr())
    thread.set_text.assert_called_once_with(page.id, page.text_layer)
    editor.controls.textbuffer.set_text.assert_called()


# ---------------------------------------------------------------------------
# LayerEditor - add
# ---------------------------------------------------------------------------


def test_add_existing_layer(mocker: pytest.MockerFixture) -> None:
    """add() with an existing layer adds a box, imports, and persists."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "newword"
    view.get_selection.return_value = "sel"
    new_bbox = mocker.Mock()
    editor.canvas.add_box.return_value = new_bbox

    editor.add(None)

    editor.canvas.add_box.assert_called_with(text="newword", bbox="sel")
    page.import_hocr.assert_called_with(editor.canvas.hocr())
    thread.set_text.assert_called_once_with(page.id, page.text_layer)
    assert editor._current_bbox is new_bbox


def test_add_default_text_when_empty(mocker: pytest.MockerFixture) -> None:
    """add() falls back to the default text when the buffer is empty."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = EMPTY
    view.get_selection.return_value = "sel"

    editor.add(None)

    editor.canvas.add_box.assert_called_with(text="my-new-word", bbox="sel")
    thread.set_text.assert_called_once_with(page.id, page.text_layer)


def test_add_creates_new_layer(mocker: pytest.MockerFixture) -> None:
    """add() with no existing layer seeds the layer and creates the canvas."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "seed"
    view.get_selection.return_value = mocker.Mock(x=0, y=0, width=10, height=10)
    view.get_offset.return_value = mocker.Mock(x=1, y=2)

    del page.text_layer

    editor.add(None)

    assert page.text_layer is not None
    assert "seed" in stored_layer(page, editor)
    thread.set_text.assert_called_once_with(page.id, page.text_layer)


def test_new_layer_json_none_selection(mocker: pytest.MockerFixture) -> None:
    """_new_layer_json() bails out when the page or selection is missing."""
    editor, _page, _thread, _view = make_editor(mocker)
    assert editor._new_layer_json(None, "text") == ""


def test_add_new_layer_runs_create_callback(mocker: pytest.MockerFixture) -> None:
    """add()'s new-layer path runs the create finished callback."""
    editor, page, thread, view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.canvas.get_first_bbox.return_value = "first"
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "seed"
    view.get_selection.return_value = mocker.Mock(x=0, y=0, width=10, height=10)
    view.get_offset.return_value = mocker.Mock(x=1, y=2)
    del page.text_layer
    edit = mocker.patch.object(editor, "edit")

    captured: dict[str, object] = {}

    def fake_parse(_json_string: str, finished_callback: object | None = None) -> None:
        captured["cb"] = finished_callback

    thread.parse_bboxtree.side_effect = fake_parse

    editor.add(None)

    # Populate the canvas through the async parse callback.
    on_parsed = captured["cb"]
    assert callable(on_parsed)
    on_parsed(mocker.Mock(info={"bboxes": [], "sorted_word_indices": []}))
    # The finished callback is wired through canvas.set_text.
    editor.canvas.set_text.call_args.kwargs["finished_callback"](None)
    edit.assert_called_with("first")
    thread.set_text.assert_called_once_with(page.id, page.text_layer)


# ---------------------------------------------------------------------------
# LayerEditor - annotation bug fixes
# ---------------------------------------------------------------------------


def test_annotation_add_guards_on_annotations_attr(
    mocker: pytest.MockerFixture,
) -> None:
    """The annotation add path guards on 'annotations', not 'text_layer'."""
    editor, page, thread, view = make_editor(mocker, page_attr="annotations")
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "note"
    view.get_selection.return_value = mocker.Mock(x=0, y=0, width=10, height=10)

    del page.annotations  # page HAS text_layer but NOT annotations

    editor.add(None)

    # The new-layer branch was taken (it would not be if the old bug that
    # checked 'text_layer' were still present, since text_layer exists here).
    assert page.annotations is not None
    assert "note" in page.annotations
    thread.set_annotations.assert_called_once_with(page.id, page.annotations)


def test_annotation_add_existing_layer_uses_import_annotations(
    mocker: pytest.MockerFixture,
) -> None:
    """add() on an existing annotation layer imports via import_annotations."""
    editor, page, thread, view = make_editor(mocker, page_attr="annotations")
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.controls.textbuffer.get_text.return_value = "note"
    view.get_selection.return_value = "sel"
    editor.canvas.add_box.return_value = mocker.Mock()

    editor.add(None)

    page.import_annotations.assert_called_with(editor.canvas.hocr())
    thread.set_annotations.assert_called_once_with(page.id, page.annotations)


def test_annotation_delete_uses_own_canvas_and_importer(
    mocker: pytest.MockerFixture,
) -> None:
    """Annotation delete writes annotations via its own canvas and importer."""
    editor, page, thread, _view = make_editor(mocker, page_attr="annotations")
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.canvas.get_current_bbox.return_value = mocker.Mock()
    bbox = mocker.Mock()
    editor._current_bbox = bbox

    editor.delete(None)

    editor.canvas.delete_word.assert_called_once_with(bbox)
    page.import_annotations.assert_called_with(editor.canvas.hocr())
    thread.set_annotations.assert_called_once_with(page.id, page.annotations)
    # The old bug used the *text* canvas/importer.
    assert not hasattr(editor, "t_canvas")


# ---------------------------------------------------------------------------
# LayerEditor - create / set_active / sort
# ---------------------------------------------------------------------------


def test_create_with_layer(mocker: pytest.MockerFixture) -> None:
    """create() parses the layer and populates the canvas."""
    editor, page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    offset = mocker.Mock(x=10, y=20)
    page.text_layer = "some json"

    captured: dict[str, object] = {}

    def fake_parse(json_string: str, finished_callback: object | None = None) -> None:
        captured["json"] = json_string
        captured["cb"] = finished_callback

    thread.parse_bboxtree.side_effect = fake_parse

    editor.create(page, offset)

    assert captured["json"] == "some json"
    result = mocker.Mock()
    result.info = {"bboxes": [{"bbox": [0, 0, 1, 1]}], "sorted_word_indices": [0]}
    captured_cb = captured["cb"]
    assert callable(captured_cb)
    captured_cb(result)
    editor.canvas.set_text.assert_called()
    editor.canvas.set_offset.assert_called_with(10, 20)
    editor.canvas.show.assert_called()


def test_create_without_layer(mocker: pytest.MockerFixture) -> None:
    """create() with an empty layer clears the canvas and runs the callback."""
    editor, page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    page.text_layer = None
    finished = mocker.Mock()

    editor.create(page, mocker.Mock(x=0, y=0), finished_callback=finished)

    thread.parse_bboxtree.assert_not_called()
    editor.canvas.clear_text.assert_called_once()
    finished.assert_called_once()


def test_create_clears_stale_focus_before_rebuild(
    mocker: pytest.MockerFixture,
) -> None:
    """create() drops focus on the previous tree's slice before rebuilding."""
    editor, page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor._current_bbox = mocker.Mock()
    page.text_layer = "some json"
    thread.parse_bboxtree.side_effect = lambda _json_string, **_kwargs: None

    editor.create(page, mocker.Mock(x=0, y=0))

    assert editor._current_bbox is None, "rebuild clears the stale focused slice"
    editor.controls.textbuffer.set_text.assert_called_once_with(EMPTY)


def test_clear_resets_focus_and_empties(mocker: pytest.MockerFixture) -> None:
    """clear() forgets the focused slice and empties the control and canvas."""
    editor, _page, _thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor._current_bbox = mocker.Mock()

    editor.clear()

    assert editor._current_bbox is None
    editor.controls.textbuffer.set_text.assert_called_once_with(EMPTY)
    editor.canvas.clear_text.assert_called_once()


def test_set_active_toggles_controls(mocker: pytest.MockerFixture) -> None:
    """set_active() shows or hides the control bar."""
    editor, _page, _thread, _view = make_editor(mocker)
    editor.controls = mocker.Mock()
    editor.set_active(active=True)
    editor.controls.show_all.assert_called_once()
    editor.set_active(active=False)
    editor.controls.hide.assert_called_once()


def test_sort_method(mocker: pytest.MockerFixture) -> None:
    """_sort() sorts the canvas by the requested method."""
    editor, _page, _thread, _view = make_editor(mocker, features=("sort",))
    editor.canvas = mocker.Mock()
    editor._sort(None, "confidence")
    editor.canvas.sort_by_confidence.assert_called_once()
    editor._sort(None, "position")
    editor.canvas.sort_by_position.assert_called_once()


def test_commit_no_page_is_noop(mocker: pytest.MockerFixture) -> None:
    """_commit() does nothing when there is no current page."""
    editor, _page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor._get_page.return_value = None
    editor._commit()
    thread.set_text.assert_not_called()


def test_add_no_page_is_noop(mocker: pytest.MockerFixture) -> None:
    """add() does nothing when there is no current page."""
    editor, _page, thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor._get_page.return_value = None
    editor.add(None)
    thread.set_text.assert_not_called()
    editor.canvas.add_box.assert_not_called()


# ---------------------------------------------------------------------------
# Integration: a real LayerEditor driving a real Canvas
# ---------------------------------------------------------------------------

THREE_WORD_HOCR = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 4.1.1' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 500 100'>
   <div class='ocr_carea' id='block_1_1' title="bbox 0 0 500 100">
    <p class='ocr_par'>
     <span class='ocr_line' id='line_1_1' title="bbox 0 0 500 100">
      <span class='ocr_word' id='word_1_1' title="bbox 0 0 100 100">
       <span class='xocr_word' id='xword_1_1' title="x_wconf 10">ALPHA</span>
      </span>
      <span class='ocr_word' id='word_1_2' title="bbox 100 0 200 100">
       <span class='xocr_word' id='xword_1_2' title="x_wconf 20">BRAVO</span>
      </span>
      <span class='ocr_word' id='word_1_3' title="bbox 200 0 300 100">
       <span class='xocr_word' id='xword_1_3' title="x_wconf 30">CHARLIE</span>
      </span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""


def make_real_editor(
    mocker: pytest.MockerFixture,
    page: Page,
    *,
    page_attr: str = "text_layer",
    features: tuple[str, ...] = (),
) -> LayerEditor:
    """Build a LayerEditor with a real Canvas and a page-backed thread."""
    thread = cast("DocThread", mocker.Mock())

    def parse_bboxtree(json_string: str, finished_callback: object = None) -> None:
        """Parse synchronously and hand the real bboxes to the canvas."""
        tree = Bboxtree(json_string)
        bboxes = list(tree.each_bbox())
        indices = [
            i
            for i, box in enumerate(bboxes)
            if box.get("type") == "word" and box.get("text", "")
        ]
        cast("Any", finished_callback)(
            Response(
                type=ResponseType.FINISHED,
                request=cast("Any", None),
                info={"bboxes": bboxes, "sorted_word_indices": indices},
                status=None,
                num_completed_jobs=0,
                total_jobs=0,
                pending=None,
            )
        )

    cast("Any", thread).parse_bboxtree = parse_bboxtree
    view = cast("ImageView", mocker.Mock())
    selection = Gdk.Rectangle()
    selection.x = 0
    selection.y = 0
    selection.width = 10
    selection.height = 10
    offset = Gdk.Rectangle()
    offset.x = 0
    offset.y = 0
    view.get_selection.return_value = selection
    view.get_offset.return_value = offset
    editor = LayerEditor(
        page_attr=page_attr,
        view=view,
        thread=thread,
        get_page=lambda: page,
        features=features,
    )
    editor.canvas._pixbuf_size = {"width": page.width, "height": page.height}
    return editor


def create_editor(editor: LayerEditor, page: Page) -> None:
    """Populate the editor's canvas, spinning the loop until parsing lands."""
    loop = safe_mainloop()
    editor.create(page, None, finished_callback=loop.quit)
    loop.run()


def stored_layer(page: Page, editor: LayerEditor) -> str:
    """Return the page's serialised layer for the editor's page attribute.

    The layer is Optional because a page starts with no text or annotation layer
    at all; these assertions are all about what the editor has written.
    """
    value = cast("str | None", getattr(page, editor.page_attr))
    assert value is not None
    return value


def settle() -> None:
    """Let an action that seeds a new layer finish parsing.

    add() seeds the layer through create(), which parses on an idle callback,
    so the editor is only populated once the main loop has had a turn.
    safe_mainloop supplies the safety net if that callback never arrives.
    """
    loop = safe_mainloop()
    GLib.idle_add(loop.quit)
    loop.run()


def test_editor_delete_persists_hocr_without_word(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Deleting text through the editor persists hOCR without that word."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)

        editor.edit(cast("Bbox", editor.canvas.get_first_bbox()))
        assert editor._current_bbox.text == "ALPHA"

        editor.delete(None)

        assert "ALPHA" not in stored_layer(page, editor)
        assert "BRAVO" in stored_layer(page, editor)
        assert "CHARLIE" in stored_layer(page, editor)


def test_editor_empty_text_deletes_word(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Clearing the text buffer and accepting removes the word."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)

        editor.edit(cast("Bbox", editor.canvas.get_first_bbox()))
        editor.controls.textbuffer.set_text(EMPTY)

        editor.ok(None)

        assert "ALPHA" not in stored_layer(page, editor)
        assert "BRAVO" in stored_layer(page, editor)


def test_editor_empty_ok_focuses_a_different_slice(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Emptying a slice shows another slice, never the deleted text again."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)

        editor.canvas.sort_by_position()
        editor.edit(editor.canvas.get_first_bbox())
        assert editor._current_bbox.text == "ALPHA"

        editor.controls.textbuffer.set_text(EMPTY)
        editor.ok(None)

        assert editor._current_bbox is not None
        assert editor._current_bbox.text != "ALPHA"
        assert editor._controls_text() == editor._current_bbox.text
        assert "ALPHA" not in stored_layer(page, editor)


def test_editor_deleting_every_slice_ends_inert(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Deleting the final slice leaves an empty control and no focused slice."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)
        editor.canvas.sort_by_confidence()

        for text in ["ALPHA", "BRAVO", "CHARLIE"]:
            word = next(
                w for w in editor.canvas._words_in_reading_order() if w.text == text
            )
            editor.edit(word)
            editor.delete(None)

        assert editor._current_bbox is None
        assert editor._controls_text() == EMPTY
        assert page.text_layer is None


def test_editor_navigation_falls_back_to_previous_on_last_delete(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Deleting the last slice in an order focuses the one before it."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)
        editor.canvas.sort_by_position()

        editor.edit(editor.canvas.get_last_bbox())
        assert cast("Bbox", editor._current_bbox).text == "CHARLIE"

        editor.delete(None)

        assert editor._current_bbox is not None
        assert editor._current_bbox.text == "BRAVO"


def test_editor_typing_after_delete_applies_to_survivor(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """A correction typed right after a deletion lands on the survivor."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)
        editor.canvas.sort_by_position()

        editor.edit(editor.canvas.get_first_bbox())
        editor.delete(None)
        survivor = editor._current_bbox
        assert survivor is not None
        assert survivor.text == "BRAVO"

        editor.controls.textbuffer.set_text("BRAVO-CORRECTED")
        editor.ok(None)

        assert "ALPHA" not in stored_layer(page, editor)
        assert '"text": "BRAVO"' not in stored_layer(page, editor)
        assert "BRAVO-CORRECTED" in stored_layer(page, editor)


def test_editor_sort_switch_keeps_focused_slice_and_text(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Switching sort order keeps the same slice focused and nothing lost."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page, features=("sort",))
        create_editor(editor, page)

        editor.canvas.sort_by_confidence()
        editor.edit(editor.canvas.get_first_bbox())
        focused = editor._current_bbox
        assert focused is not None
        assert focused.text == "ALPHA"

        editor._sort(None, "position")

        assert editor._current_bbox is focused
        assert editor._controls_text() == "ALPHA"
        for text in ["ALPHA", "BRAVO", "CHARLIE"]:
            assert stored_layer(page, editor).count(text) == 1


def test_editor_rebuild_while_focused_drops_stale_focus(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Rebuilding the canvas drops the old tree's focus before ok/delete act.

    Loading a page again -- e.g. after an undo -- gives the editor a fresh
    tree; a correction then must not apply to a slice of the detached tree.
    """
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page)
        create_editor(editor, page)
        editor.canvas.sort_by_position()

        editor.edit(cast("Bbox", editor.canvas.get_first_bbox()))
        assert editor._current_bbox is not None
        assert editor._current_bbox.text == "ALPHA"

        # A rebuild (page switch / undo) gives the canvas a fresh tree.
        editor.create(page, None)

        assert editor._current_bbox is None, "rebuild drops the stale focus"
        assert editor._controls_text() == EMPTY, "rebuild empties the control"

        editor.ok(None)
        assert "ALPHA" in stored_layer(page, editor), "inert ok changes nothing"

        editor.delete(None)
        assert "ALPHA" in stored_layer(page, editor), "inert delete removes nothing"

        # Run the rebuild's idle pass, then a real slice in the rebuilt tree
        # still corrects and deletes normally.
        settle()
        editor.canvas.sort_by_position()
        editor.edit(cast("Bbox", editor.canvas.get_first_bbox()))
        assert editor._current_bbox is not None
        assert editor._current_bbox.text == "ALPHA"
        editor.controls.textbuffer.set_text("ALPHA-CORRECTED")
        editor.ok(None)
        assert "ALPHA-CORRECTED" in stored_layer(page, editor)

        editor.delete(None)
        assert "ALPHA" not in stored_layer(page, editor)


def test_editor_never_focuses_a_detached_slice(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """After every editor action the focused slice is still in the tree."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        page.import_hocr(THREE_WORD_HOCR)
        editor = make_real_editor(mocker, page, features=("sort", "copy"))
        create_editor(editor, page)
        editor.canvas.sort_by_position()

        def in_scene_graph() -> bool:
            bbox = editor._current_bbox
            return bbox is not None and bbox in editor.canvas._words_in_reading_order()

        editor.edit(editor.canvas.get_first_bbox())
        assert in_scene_graph()

        editor.add(None)
        assert in_scene_graph()

        editor.copy(None)
        assert in_scene_graph()

        editor.controls.textbuffer.set_text("REVISED")
        editor.ok(None)
        assert in_scene_graph()

        editor.controls.textbuffer.set_text(EMPTY)
        editor.ok(None)
        assert in_scene_graph()

        editor.delete(None)
        assert in_scene_graph()


def test_annotation_layer_parity(rose_pnm: str, mocker: pytest.MockerFixture) -> None:
    """Add, correct and delete all work for the annotation layer."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        editor = make_real_editor(mocker, page, page_attr="annotations")

        # a page with no annotation layer gains one from the first note
        editor.create(page, None)
        editor.add(None)
        settle()
        assert editor._current_bbox is not None
        assert "my-new-annotation" in stored_layer(page, editor)
        create_editor(editor, page)

        editor.edit(editor.canvas.get_first_bbox())
        editor.controls.textbuffer.set_text("FIRST-NOTE")
        editor.ok(None)
        assert "FIRST-NOTE" in stored_layer(page, editor)

        editor.copy(None)
        assert stored_layer(page, editor).count("FIRST-NOTE") == 2

        editor.edit(editor.canvas.get_first_bbox())
        editor.delete(None)
        assert page.annotations is not None
        assert stored_layer(page, editor).count("FIRST-NOTE") == 1

        # the surviving note round-trips through the canvas hOCR
        tree = Bboxtree()
        tree.from_hocr(editor.canvas.hocr())
        notes = [box["text"] for box in tree.each_bbox() if box["type"] == "word"]
        assert notes == ["FIRST-NOTE"]

        editor.edit(editor.canvas.get_first_bbox())
        editor.delete(None)
        assert page.annotations is None


def test_annotation_placeholder_is_used_for_an_empty_control(
    rose_pnm: str, mocker: pytest.MockerFixture
) -> None:
    """Adding a note to an empty control seeds the documented placeholder."""
    with tempfile.TemporaryDirectory() as dirname:
        page = Page(
            filename=rose_pnm,
            format="Portable anymap",
            resolution=POINTS_PER_INCH,
            dir=dirname,
        )
        editor = make_real_editor(mocker, page, page_attr="annotations")

        editor.create(page, None)
        editor.add(None)
        settle()

        assert editor._current_bbox is not None
        assert page.annotations is not None
        assert "my-new-annotation" in stored_layer(page, editor)

"""Test the LayerControls widget and LayerEditor controller."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from scantpaper.const import EMPTY
from scantpaper.layer import LayerControls, LayerEditor

if TYPE_CHECKING:
    import pytest

    from scantpaper.docthread import DocThread
    from scantpaper.imageview import ImageView
    from scantpaper.page import Page


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


def test_edit_none_is_noop(mocker: pytest.MockerFixture) -> None:
    """edit(None) does not touch the canvas or controls."""
    editor, _page, _thread, _view = make_editor(mocker)
    editor.canvas = mocker.Mock()
    editor.controls = mocker.Mock()
    editor.edit(None)
    editor.controls.textbuffer.set_text.assert_not_called()
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

    bbox.update_box.assert_called_with("corrected", "sel")
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

    bbox.delete_box.assert_called()
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
    assert "seed" in page.text_layer
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

    bbox.delete_box.assert_called()
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

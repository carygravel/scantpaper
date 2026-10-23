"""test document module."""

from __future__ import annotations

import datetime
import unittest.mock
import weakref
from functools import partial
from types import FunctionType
from typing import TYPE_CHECKING, cast

import pytest

from scantpaper.document import Document, _extract_metadata

if TYPE_CHECKING:
    from collections.abc import Callable


class _LifetimeMarker:
    """Weak-referenceable marker stored in an options dict."""


class MockResponse:
    """A mock response class."""

    def __init__(self, info: object) -> None:
        """Initialize mock response."""
        self.info = info


class MockThread:
    """A mock thread class."""

    def __init__(self) -> None:
        """Initialize mock thread."""
        self.get_file_info = unittest.mock.Mock()
        self.import_file = unittest.mock.Mock()
        self.import_page = unittest.mock.Mock()
        self.split_page = unittest.mock.Mock()
        self.unpaper = unittest.mock.Mock()
        self.user_defined = unittest.mock.Mock()
        self.undo = unittest.mock.Mock()
        self.redo = unittest.mock.Mock()
        self.get_selection = unittest.mock.Mock()
        self.get_resolution = unittest.mock.Mock()
        self.send = unittest.mock.Mock()


def create_doc() -> Document:
    """Create a mock document instance."""
    with unittest.mock.patch(
        "scantpaper.document.BaseDocument.__init__", return_value=None
    ):
        d = Document()
        d.thread = MockThread()
        d.create_pidfile = unittest.mock.Mock(return_value="pidfile")
        d.dir = "/tmp"
        d.add_page = unittest.mock.Mock()
        d.get_selected_indices = unittest.mock.Mock(return_value=[0])
        d.select = unittest.mock.Mock()
        d.row_changed_signal = "row-changed"
        d.selection_changed_signal = "selection-changed"
        d.get_model = unittest.mock.Mock()
        d.get_selection = unittest.mock.Mock()
        d._data_list = []
        return d


def test_import_files_encrypted() -> None:
    """Test import_files with encrypted file."""
    doc = create_doc()
    password_callback = unittest.mock.Mock(return_value="password")
    doc.import_files(paths=["file.pdf"], password_callback=password_callback)
    kwargs = doc.thread.get_file_info.call_args[1]
    kwargs["finished_callback"](MockResponse({"encrypted": True}))
    assert doc.thread.get_file_info.call_count == 2


def test_import_files_multiple_success() -> None:
    """Test success importing multiple single-page files."""
    doc = create_doc()
    metadata_callback = unittest.mock.Mock()
    finished_callback = unittest.mock.Mock()
    info = [
        {"format": "image", "path": "i1.png", "pages": 1, "title": "T1"},
        {"format": "image", "path": "i2.png", "pages": 1, "title": "T2"},
    ]
    options = {
        "metadata_callback": metadata_callback,
        "finished_callback": finished_callback,
        "paths": ["i1.png", "i2.png"],
        "error_callback": None,
    }
    doc._get_file_info_finished_callback2_multiple_files(info, options)
    assert metadata_callback.call_count == 2
    assert doc.thread.import_file.call_count == 2


def test_multiple_files_renumber_once_on_finish() -> None:
    """Test a multi-file import renumbers once at the end of the batch."""
    doc = create_doc()
    finished_callback = unittest.mock.Mock()
    info = [
        {"format": "image", "path": "i1.png", "pages": 1, "title": "T1"},
        {"format": "image", "path": "i2.png", "pages": 1, "title": "T2"},
    ]
    options = {
        "finished_callback": finished_callback,
        "paths": ["i1.png", "i2.png"],
        "error_callback": None,
    }
    with unittest.mock.patch.object(doc, "renumber") as mock_renumber:
        doc._get_file_info_finished_callback2_multiple_files(info, options)

        # Only the last import_file carries the batch finished_callback
        last_kwargs = doc.thread.import_file.call_args_list[-1][1]
        assert "finished_callback" in last_kwargs
        last_kwargs["finished_callback"](MockResponse(None))

        assert mock_renumber.call_count == 1
        finished_callback.assert_called_once()


def test_get_file_info_finished_callback2_pagerange() -> None:
    """Test pagerange_callback."""
    doc = create_doc()
    pagerange_callback = unittest.mock.Mock(return_value=(2, 3))
    info = [{"format": "PDF", "path": "f.pdf", "pages": 5}]
    doc._get_file_info_finished_callback2(
        info, {"pagerange_callback": pagerange_callback}
    )
    assert doc.thread.import_file.call_args[1]["first"] == 2


def test_get_file_info_finished_callback2_no_pagerange() -> None:
    """Test pagerange_callback."""
    doc = create_doc()
    pagerange_callback = unittest.mock.Mock(return_value=(None, 3))
    info = [{"format": "PDF", "path": "f.pdf", "pages": 5}]
    assert (
        doc._get_file_info_finished_callback2(
            info, {"pagerange_callback": pagerange_callback}
        )
        is None
    )


def test_get_file_info_finished_callback2_session_file() -> None:
    """Test session file handling in get_file_info_finished_callback2."""
    doc = create_doc()
    info = [{"format": "session file", "path": "f.session"}]
    options = {"finished_callback": unittest.mock.Mock()}
    with unittest.mock.patch.object(doc, "open_session") as open_session:
        doc._get_file_info_finished_callback2(info, options)
        open_session.assert_called_with(db="f.session", **options)


def test_post_process_rotate() -> None:
    """Test _post_process_rotate."""
    doc = create_doc()
    doc.rotate = unittest.mock.Mock()
    options = {"rotate": 90, "finished_callback": unittest.mock.Mock()}
    doc._post_process_rotate(cast("int", cast("object", "uuid")), options)
    doc.rotate.assert_called()

    updated_page_callback = doc.rotate.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called_with("new_uuid", options)


def test_post_process_unpaper() -> None:
    """Test _post_process_unpaper."""
    doc = create_doc()
    doc.unpaper = unittest.mock.Mock()
    unpaper_obj = unittest.mock.Mock()
    options = {"unpaper": unpaper_obj, "finished_callback": unittest.mock.Mock()}
    doc._post_process_unpaper(cast("int", cast("object", "uuid")), options)
    doc.unpaper.assert_called()

    updated_page_callback = doc.unpaper.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called()


def test_post_process_udt() -> None:
    """Test _post_process_udt."""
    doc = create_doc()
    doc.user_defined = unittest.mock.Mock()
    options = {"udt": "cmd", "finished_callback": unittest.mock.Mock()}
    doc._post_process_udt(cast("int", cast("object", "uuid")), options)
    doc.user_defined.assert_called()

    updated_page_callback = doc.user_defined.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called()


def test_post_process_ocr() -> None:
    """Test _post_process_ocr."""
    doc = create_doc()
    doc.ocr_pages = unittest.mock.Mock()
    options = {
        "ocr": True,
        "engine": "t",
        "language": "l",
        "variables": "user_words_file=/tmp/words.txt",
        "finished_callback": unittest.mock.Mock(),
    }
    doc._post_process_ocr(cast("int", cast("object", "uuid")), options)
    doc.ocr_pages.assert_called()
    assert doc.ocr_pages.call_args[1]["variables"] == "user_words_file=/tmp/words.txt"

    ocr_finished_callback = doc.ocr_pages.call_args[1]["finished_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        ocr_finished_callback(None)
        mock_pps.assert_called_with(None, options)


def _captured_options(callback: object) -> dict[str, object]:
    """Return the options captured by a partial or closure callback."""
    if isinstance(callback, partial):
        return cast("dict[str, object]", callback.keywords["options"])
    assert isinstance(callback, FunctionType)
    closure = callback.__closure__ or ()
    cells = dict(zip(callback.__code__.co_freevars, closure, strict=True))
    return cast("dict[str, object]", cells["kwargs"].cell_contents)


def _track_options(options: dict[str, object]) -> weakref.ReferenceType[object]:
    """Track whether an options dict stays alive through a weak marker."""
    marker = _LifetimeMarker()
    options["_lifetime_marker"] = marker
    return weakref.ref(marker)


def test_generated_and_direct_callbacks_stay_out_of_options() -> None:
    """Callbacks are passed separately so their options are refcounted."""
    doc = create_doc()
    doc.split_page(page=1)
    direct_kwargs = doc.thread.split_page.call_args.kwargs
    direct_callback = direct_kwargs["data_callback"]
    direct_options = _captured_options(direct_callback)
    assert "data_callback" not in direct_options

    options_ref = _track_options(direct_options)
    doc.thread.split_page.reset_mock()
    del direct_kwargs, direct_callback, direct_options
    assert options_ref() is None, "direct options released without cyclic GC"


@pytest.mark.parametrize("method", ["unpaper", "user_defined"])
def test_unpaper_and_user_defined_keep_callback_out_of_options(method: str) -> None:
    """The remaining direct methods also avoid a self-referencing options dict."""
    doc = create_doc()
    getattr(doc, method)(page=1)
    thread_method = getattr(doc.thread, method)
    request_kwargs = thread_method.call_args.kwargs
    callback = request_kwargs["data_callback"]
    options = _captured_options(callback)
    assert "data_callback" not in options

    options_ref = _track_options(options)
    thread_method.reset_mock()
    del request_kwargs, callback, options
    assert options_ref() is None, "options released without cyclic GC"


def test_import_file_keeps_callback_out_of_options() -> None:
    """Import callbacks capture the outer options without a cycle."""
    doc = create_doc()
    doc.import_file(info={}, first_page=1, last_page=1)

    request_kwargs = doc.thread.import_file.call_args.kwargs
    callback = request_kwargs["data_callback"]
    options = _captured_options(callback)
    assert "data_callback" not in options

    assert doc.create_pidfile.call_args.args[1] == "import_file"
    options_ref = _track_options(options)
    doc.thread.import_file.reset_mock()
    doc.create_pidfile.reset_mock()
    del request_kwargs, callback, options
    assert options_ref() is None, "options released without cyclic GC"


def test_import_file_continues_without_pidfile() -> None:
    """A failed pidfile leaves the import running without cancellation support."""
    doc = create_doc()
    doc.create_pidfile = unittest.mock.Mock(return_value=None)

    doc.import_file(info={}, first_page=1, last_page=1)

    doc.create_pidfile.assert_called_once()
    assert doc.thread.import_file.call_args.kwargs["pidfile"] is None


def test_file_info_pidfile_uses_process_name() -> None:
    """File information requests name their process in create_pidfile()."""
    doc = create_doc()
    doc.import_files(paths=["file.pdf"])
    assert doc.create_pidfile.call_args.args[1] == "get_file_info"


def test_import_scan_remains_cycle_free() -> None:
    """The copy-based scan callback construction stays cycle-free."""
    doc = create_doc()
    doc.import_scan(resolution=300, rotate=None)

    request_kwargs = doc.thread.import_page.call_args.kwargs
    callback = request_kwargs["data_callback"]
    options = _captured_options(callback)
    assert "data_callback" not in options

    options_ref = _track_options(options)
    doc.thread.import_page.reset_mock()
    del request_kwargs, callback, options
    assert options_ref() is None, "scan options released without cyclic GC"


def test_import_scan() -> None:
    """Test import_scan."""
    doc = create_doc()
    doc.import_scan(resolution=300, rotate=None)
    data_callback = doc.thread.import_page.call_args[1]["data_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
        mock_pps.assert_called()


def test_post_process_enforce_depth() -> None:
    """Test _post_process_enforce_depth converts via the threshold handler."""
    doc = create_doc()
    doc.threshold = unittest.mock.Mock()
    options = {
        "enforce_depth": True,
        "depth_threshold": 20,
        "finished_callback": unittest.mock.Mock(),
    }
    doc._post_process_scan(cast("int", cast("object", "uuid")), options)
    doc.threshold.assert_called()
    assert doc.threshold.call_args[1]["threshold"] == 20
    assert doc.threshold.call_args[1]["page"] == "uuid"
    assert "finished_callback" not in doc.threshold.call_args[1]

    updated_page_callback = doc.threshold.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        assert mock_pps.call_args[0][0] == "new_uuid"
        chained = mock_pps.call_args[0][1]
        assert "enforce_depth" not in chained, "flag consumed after conversion"
        assert chained["depth_threshold"] == 20
        assert chained["finished_callback"] is options["finished_callback"]


def test_post_process_enforce_depth_runs_before_rotate() -> None:
    """The depth conversion is the first post-process step."""
    doc = create_doc()
    doc.threshold = unittest.mock.Mock()
    doc.rotate = unittest.mock.Mock()
    options = {
        "enforce_depth": True,
        "depth_threshold": 20,
        "rotate": 90,
        "finished_callback": unittest.mock.Mock(),
    }
    doc._post_process_scan(cast("int", cast("object", "uuid")), options)
    doc.threshold.assert_called()
    doc.rotate.assert_not_called()

    updated_page_callback = doc.threshold.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called()


def test_post_process_scan_without_enforce_depth() -> None:
    """Imports without the flag do not convert."""
    doc = create_doc()
    doc.threshold = unittest.mock.Mock()
    doc._post_process_scan(
        cast("int", cast("object", "uuid")), {"finished_callback": None}
    )
    doc.threshold.assert_not_called()


def test_split_page() -> None:
    """Test split_page."""
    doc = create_doc()
    doc.split_page(first_page=1, last_page=1)
    data_callback = doc.thread.split_page.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_split_page_no_info() -> None:
    """Test split_page with improper input."""
    doc = create_doc()
    logger_callback = unittest.mock.Mock()
    doc.split_page(first_page=1, last_page=1, logger_callback=logger_callback)
    data_callback = doc.thread.split_page.call_args[1]["data_callback"]
    data_callback(MockResponse({}))
    logger_callback.assert_called()


def test_ocr_pages() -> None:
    """Test ocr_pages."""
    doc = create_doc()
    doc.tesseract = unittest.mock.Mock()
    doc.ocr_pages(pages=["uuid"], engine="tesseract")
    doc.tesseract.assert_called()


def test_unpaper_method() -> None:
    """Test unpaper."""
    doc = create_doc()
    doc.unpaper(page="uuid")
    data_callback = doc.thread.unpaper.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_unpaper_no_info() -> None:
    """Test unpaper with improper input."""
    doc = create_doc()
    logger_callback = unittest.mock.Mock()
    doc.unpaper(page="uuid", logger_callback=logger_callback)
    data_callback = doc.thread.unpaper.call_args[1]["data_callback"]
    data_callback(MockResponse({}))
    logger_callback.assert_called()


def test_user_defined_method() -> None:
    """Test user_defined method."""
    doc = create_doc()
    doc.user_defined(page="uuid", command="ls")
    data_callback = doc.thread.user_defined.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_undo_redo() -> None:
    """Test undo and redo."""
    doc = create_doc()
    # Mock data property using patch.object on Document class
    with unittest.mock.patch.object(
        Document, "data", new_callable=unittest.mock.PropertyMock
    ) as mock_data:
        mock_data.side_effect = lambda *args: (
            doc._data_list if not args else setattr(doc, "_data_list", args[0])
        )

        def mock_send(process: str, *_args: object, **kwargs: object) -> None:
            if process == "undo":
                cast("Callable[..., object]", kwargs["finished_callback"])(
                    MockResponse({"snapshot": "new_data", "selection": [0]})
                )
            elif process == "redo":
                cast("Callable[..., object]", kwargs["finished_callback"])(
                    MockResponse({"snapshot": "newer_data", "selection": [0]})
                )

        doc.thread.send = mock_send

        doc.undo()
        assert doc._data_list == "new_data"
        doc.unundo()
        assert doc._data_list == "newer_data"


def test_undo_redo_with_error_callback() -> None:
    """Test undo and redo with an error callback."""
    doc = create_doc()
    error_callback = unittest.mock.Mock()
    with unittest.mock.patch.object(
        Document, "data", new_callable=unittest.mock.PropertyMock
    ) as mock_data:
        mock_data.return_value = doc._data_list

        last_call = {}

        def mock_send(process: str, *_args: object, **kwargs: object) -> None:
            last_call.update(kwargs)
            if process in ("undo", "redo"):
                cast("Callable[..., object]", kwargs["finished_callback"])(
                    MockResponse({"snapshot": "new_data", "selection": [0]})
                )

        doc.thread.send = mock_send

        doc.undo(error_callback=error_callback)
        assert last_call["error_callback"] is error_callback
        doc.unundo(error_callback=error_callback)
        assert last_call["error_callback"] is error_callback


def test_get_selected_properties() -> None:
    """Test get_selected_properties."""
    doc = create_doc()
    mock_p1 = unittest.mock.Mock()
    mock_p1.resolution = [300, 300]
    doc._data_list = [[0, 0, mock_p1]]
    with unittest.mock.patch.object(
        Document, "data", new_callable=unittest.mock.PropertyMock
    ) as mock_data:
        mock_data.return_value = doc._data_list
        doc.thread.get_resolution.return_value = (300, 300)
        assert doc.get_selected_properties() == (300, 300)


def test_extract_metadata_isoformat() -> None:
    """Test _extract_metadata."""
    info = {
        "format": "Portable Document Format",
        "datetime": "2023-01-01T12:00:00Z",
        "author": "Me",
    }
    meta = _extract_metadata(info)
    assert meta["author"] == "Me"
    assert isinstance(meta["datetime"], datetime.datetime)

    # test ValueError in fromisoformat
    info["format"] = "Portable Document Format"
    info["datetime"] = "2023-13-01T12:00:00Z"  # Invalid month 13
    meta = _extract_metadata(info)
    assert "datetime" not in meta

    # test without minutes in timezone
    info["datetime"] = "2023-01-01T12:00:00+01"
    meta = _extract_metadata(info)
    assert isinstance(meta["datetime"], datetime.datetime)

    # test with NONE value
    info["title"] = "NONE"
    meta = _extract_metadata(info)
    assert "title" not in meta

    # test invalid datetime
    info["datetime"] = "invalid"
    meta = _extract_metadata(info)
    assert "datetime" not in meta

    # test compatibility code for older python versions (sys.version_info < 3.11)
    with unittest.mock.patch("sys.version_info", (3, 10)):
        # Z to +00:00
        info["format"] = "Portable Document Format"
        info["datetime"] = "2023-01-01T12:00:00Z"
        meta = _extract_metadata(info)
        assert isinstance(meta["datetime"], datetime.datetime)

        # Append :00 to timezone without minutes
        info["datetime"] = "2023-01-01T12:00:00+01"
        meta = _extract_metadata(info)
        assert isinstance(meta["datetime"], datetime.datetime)

        # test DJVU format too
        info["format"] = "DJVU"
        info["datetime"] = "2023-01-01T12:00:00Z"
        meta = _extract_metadata(info)
        assert isinstance(meta["datetime"], datetime.datetime)


def test_extract_metadata_placeholder_title() -> None:
    """Test _extract_metadata with placeholder titles."""
    info = {
        "format": "Portable Document Format",
        "datetime": "2023-01-01T12:00:00Z",
    }
    for title in ["Untitled", "'Untitled'", "UNTITLED", "  untitled  "]:
        info["title"] = title
        meta = _extract_metadata(info)
        assert "title" not in meta, f"placeholder title {title!r} dropped"

    info["title"] = "La Voz de Galicia"
    meta = _extract_metadata(info)
    assert meta["title"] == "La Voz de Galicia"


def test_begin_undo_batch_forwards_to_thread() -> None:
    """begin_undo_batch sends a begin_batch request to the thread."""
    doc = create_doc()
    doc.begin_undo_batch()
    doc.thread.send.assert_called_once_with("begin_batch")


def test_end_undo_batch_forwards_to_thread() -> None:
    """end_undo_batch sends an end_batch request to the thread."""
    doc = create_doc()
    doc.end_undo_batch()
    doc.thread.send.assert_called_once_with("end_batch")

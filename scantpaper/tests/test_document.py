"test document module"

import unittest.mock
import datetime
from document import Document, _extract_metadata


class MockResponse:
    "A mock response class"

    def __init__(self, info):
        "Initialize mock response"
        self.info = info


class MockThread:
    "A mock thread class"

    def __init__(self):
        "Initialize mock thread"
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


def create_doc():
    "Create a mock document instance"
    with unittest.mock.patch("document.BaseDocument.__init__", return_value=None):
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


def test_import_files_encrypted():
    "test import_files with encrypted file"
    doc = create_doc()
    password_callback = unittest.mock.Mock(return_value="password")
    doc.import_files(paths=["file.pdf"], password_callback=password_callback)
    kwargs = doc.thread.get_file_info.call_args[1]
    kwargs["finished_callback"](MockResponse({"encrypted": True}))
    assert doc.thread.get_file_info.call_count == 2


def test_import_files_multiple_success():
    "test success importing multiple single-page files"
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


def test_get_file_info_finished_callback2_pagerange():
    "test pagerange_callback"
    doc = create_doc()
    pagerange_callback = unittest.mock.Mock(return_value=(2, 3))
    info = [{"format": "PDF", "path": "f.pdf", "pages": 5}]
    doc._get_file_info_finished_callback2(
        info, {"pagerange_callback": pagerange_callback}
    )
    assert doc.thread.import_file.call_args[1]["first"] == 2


def test_get_file_info_finished_callback2_no_pagerange():
    "test pagerange_callback"
    doc = create_doc()
    pagerange_callback = unittest.mock.Mock(return_value=(None, 3))
    info = [{"format": "PDF", "path": "f.pdf", "pages": 5}]
    assert (
        doc._get_file_info_finished_callback2(
            info, {"pagerange_callback": pagerange_callback}
        )
        is None
    )


def test_post_process_rotate():
    "test _post_process_rotate"
    doc = create_doc()
    doc.rotate = unittest.mock.Mock()
    options = {"rotate": 90, "finished_callback": unittest.mock.Mock()}
    doc._post_process_rotate("uuid", options)
    doc.rotate.assert_called()

    updated_page_callback = doc.rotate.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called_with("new_uuid", options)


def test_post_process_unpaper():
    "test _post_process_unpaper"
    doc = create_doc()
    doc.unpaper = unittest.mock.Mock()
    unpaper_obj = unittest.mock.Mock()
    options = {"unpaper": unpaper_obj, "finished_callback": unittest.mock.Mock()}
    doc._post_process_unpaper("uuid", options)
    doc.unpaper.assert_called()

    updated_page_callback = doc.unpaper.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called()


def test_post_process_udt():
    "test _post_process_udt"
    doc = create_doc()
    doc.user_defined = unittest.mock.Mock()
    options = {"udt": "cmd", "finished_callback": unittest.mock.Mock()}
    doc._post_process_udt("uuid", options)
    doc.user_defined.assert_called()

    updated_page_callback = doc.user_defined.call_args[1]["updated_page_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        updated_page_callback(MockResponse({"type": "page", "row": [0, 0, "new_uuid"]}))
        mock_pps.assert_called()


def test_post_process_ocr():
    "test _post_process_ocr"
    doc = create_doc()
    doc.ocr_pages = unittest.mock.Mock()
    options = {
        "ocr": True,
        "engine": "t",
        "language": "l",
        "finished_callback": unittest.mock.Mock(),
    }
    doc._post_process_ocr("uuid", options)
    doc.ocr_pages.assert_called()

    ocr_finished_callback = doc.ocr_pages.call_args[1]["finished_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        ocr_finished_callback(None)
        mock_pps.assert_called_with(None, options)


def test_import_scan():
    "test import_scan"
    doc = create_doc()
    doc.import_scan(resolution=300, rotate=None)
    data_callback = doc.thread.import_page.call_args[1]["data_callback"]
    with unittest.mock.patch.object(doc, "_post_process_scan") as mock_pps:
        data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
        mock_pps.assert_called()


def test_split_page():
    "test split_page"
    doc = create_doc()
    doc.split_page(first_page=1, last_page=1)
    data_callback = doc.thread.split_page.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_split_page_no_info():
    "test split_page with improper input"
    doc = create_doc()
    logger_callback = unittest.mock.Mock()
    doc.split_page(first_page=1, last_page=1, logger_callback=logger_callback)
    data_callback = doc.thread.split_page.call_args[1]["data_callback"]
    data_callback(MockResponse({}))
    logger_callback.assert_called()


def test_ocr_pages():
    "test ocr_pages"
    doc = create_doc()
    doc.tesseract = unittest.mock.Mock()
    doc.ocr_pages(pages=["uuid"], engine="tesseract")
    doc.tesseract.assert_called()


def test_unpaper_method():
    "test unpaper"
    doc = create_doc()
    doc.unpaper(page="uuid")
    data_callback = doc.thread.unpaper.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_unpaper_no_info():
    "test unpaper with improper input"
    doc = create_doc()
    logger_callback = unittest.mock.Mock()
    doc.unpaper(page="uuid", logger_callback=logger_callback)
    data_callback = doc.thread.unpaper.call_args[1]["data_callback"]
    data_callback(MockResponse({}))
    logger_callback.assert_called()


def test_user_defined_method():
    "test user_defined method"
    doc = create_doc()
    doc.user_defined(page="uuid", command="ls")
    data_callback = doc.thread.user_defined.call_args[1]["data_callback"]
    data_callback(MockResponse({"type": "page", "row": [0, 0, "uuid"]}))
    doc.add_page.assert_called()


def test_undo_redo():
    "test undo and redo"
    doc = create_doc()
    # Mock data property using patch.object on Document class
    with unittest.mock.patch.object(
        Document, "data", new_callable=unittest.mock.PropertyMock
    ) as mock_data:
        mock_data.side_effect = lambda *args: (
            doc._data_list if not args else setattr(doc, "_data_list", args[0])
        )

        doc.thread.undo.return_value = "new_data"
        doc.thread.redo.return_value = "newer_data"
        doc.thread.get_selection.return_value = [0]

        doc.undo()
        assert doc._data_list == "new_data"
        doc.unundo()
        assert doc._data_list == "newer_data"


def test_get_selected_properties():
    "test get_selected_properties"
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


def test_extract_metadata_isoformat():
    "test _extract_metadata"
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

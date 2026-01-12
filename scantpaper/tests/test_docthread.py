"Tests for DocThread"

import threading
from docthread import DocThread, _calculate_crop_tuples
from page import Page


def test_do_tesseract_path_fallback(mocker):
    "test do_tesseract when path is ./"

    # Mock DocThread to avoid real DB connection if possible, but here we just
    # spoof _write_tid.
    # Using a memory database for simplicity in this test
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    # Mock get_languages to return path="./"
    mocker.patch("tesserocr.get_languages", return_value=("./", []))

    # Mock glob to simulate finding tessdata
    mock_glob = mocker.patch(
        "glob.glob", return_value=["/usr/share/tesseract-ocr/4.00/tessdata"]
    )

    # Mock PyTessBaseAPI
    mock_api = mocker.patch("tesserocr.PyTessBaseAPI")
    mock_api_instance = mock_api.return_value
    mock_api_instance.__enter__.return_value = mock_api_instance
    mock_api_instance.ProcessPages.return_value = True

    # Mock Page
    mock_page = mocker.Mock(spec=Page)
    mock_page.image_object = mocker.Mock()
    mock_page.id = 1

    # Mock get_page
    mocker.patch.object(thread, "get_page", return_value=mock_page)

    # Mock replace_page and other methods that hit DB
    mocker.patch.object(thread, "replace_page")
    mocker.patch.object(thread, "find_page_number_by_page_id")

    # Mock pathlib.Path
    mock_path = mocker.patch("pathlib.Path")
    mock_path_instance = mock_path.return_value
    mock_path_instance.with_suffix.return_value = mock_path_instance
    mock_path_instance.read_text.return_value = "hocr content"

    # Mock cancel
    thread.cancel = False

    request = mocker.Mock()
    request.args = [{"page": 1, "language": "eng", "dir": "/tmp"}]

    thread.do_tesseract(request)

    # Check if glob was called
    mock_glob.assert_called_with("/usr/share/tesseract-ocr/*/tessdata")

    # Check if PyTessBaseAPI was initialized with the found path
    mock_api.assert_called_with(
        lang="eng", path="/usr/share/tesseract-ocr/4.00/tessdata"
    )


def test_do_tesseract_path_fallback_not_found(temp_db, clean_up_files, mocker):
    "test do_tesseract when path is ./ and no system tessdata found"
    thread = DocThread(db=temp_db.name)
    thread._write_tid = threading.get_native_id()

    # Mock get_languages to return path="./"
    mocker.patch("tesserocr.get_languages", return_value=("./", []))

    # Mock glob to return empty list
    mocker.patch("glob.glob", return_value=[])

    # Mock PyTessBaseAPI to prevent RuntimeError
    mocker.patch("tesserocr.PyTessBaseAPI")

    # Mock get_page
    mock_page = mocker.Mock(spec=Page)
    mock_page.image_object = mocker.Mock()
    mock_page.id = 1
    mock_page.image_id = 1
    mocker.patch.object(thread, "get_page", return_value=mock_page)

    # Mock finding page number
    mocker.patch.object(thread, "find_page_number_by_page_id", return_value=1)
    mocker.patch.object(thread, "find_row_id_by_page_number", return_value=1)

    # Mock DB operations
    mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_fetchone", return_value=[1])
    mocker.patch.object(thread, "_fetchall", return_value=[])
    mocker.patch.object(thread, "_take_snapshot")
    mocker.patch.object(thread, "_insert_image", return_value=(1, "thumb"))
    mocker.patch.object(thread, "_insert_page", return_value=1)

    # Mock _con for commit
    thread._con[threading.get_native_id()] = mocker.Mock()

    # Mock pathlib.Path
    mock_path = mocker.patch("pathlib.Path")
    mock_path_instance = mock_path.return_value
    mock_path_instance.with_suffix.return_value = mock_path_instance
    mock_path_instance.read_text.return_value = "hocr content"

    request = mocker.Mock()
    request.args = [{"page": 1, "language": "eng", "dir": "/tmp"}]

    thread.do_tesseract(request)

    # Check if error was reported
    request.error.assert_called()
    assert "tessdata directory not found" in str(request.error.call_args)

    clean_up_files(thread.db_files)


def test_calculate_crop_tuples(mocker):
    "test _calculate_crop_tuples"

    mock_image = mocker.Mock()
    mock_image.width = 100
    mock_image.height = 200

    # Test vertical split
    options = {"direction": "v", "position": 40}
    tuples = _calculate_crop_tuples(options, mock_image)
    assert tuples == (
        (0, 0, 40, 200),
        (40, 0, 100, 200),
        (40, 0, 60, 200),
    )

    # Test horizontal split
    options = {"direction": "h", "position": 50}
    tuples = _calculate_crop_tuples(options, mock_image)
    assert tuples == (
        (0, 0, 100, 50),
        (0, 50, 100, 200),
        (0, 50, 100, 150),
    )


def test_get_thumb(mocker):
    "test get_thumb"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_execute = mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_fetchone", return_value=(b"fake_thumb_bytes",))
    mock_pixbuf = mocker.Mock()
    mocker.patch.object(thread, "_bytes_to_pixbuf", return_value=mock_pixbuf)

    result = thread.get_thumb(1)

    mock_execute.assert_called_once_with("SELECT thumb FROM page WHERE id = ?", (1,))
    assert result == mock_pixbuf

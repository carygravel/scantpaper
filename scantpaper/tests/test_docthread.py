"Tests for DocThread"

import threading
import subprocess
import pytest
from const import APPLICATION_ID, USER_VERSION
from docthread import DocThread, _calculate_crop_tuples
from importthread import CancelledError
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


def test_open_session_file(mocker):
    "test open session file"

    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_connect")
    mock_execute = mocker.patch.object(thread, "_execute")
    mocker.patch.object(
        thread,
        "_fetchone",
        side_effect=[
            (APPLICATION_ID,),  # application_id
            (USER_VERSION,),  # user_version
            (10,),  # action_id
        ],
    )

    thread.open("test.db")

    assert thread._db == "test.db"
    assert thread._action_id == 10
    assert mock_execute.call_count == 3
    mock_execute.assert_any_call("PRAGMA application_id")
    mock_execute.assert_any_call("PRAGMA user_version")
    mock_execute.assert_any_call("SELECT MAX(action_id) FROM page_order")


def test_open_session_file_invalid_app_id(mocker):
    "test open session file with invalid application id"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_connect")
    mocker.patch.object(thread, "_execute")
    mocker.patch.object(
        thread,
        "_fetchone",
        return_value=(12345,),  # Invalid application_id
    )

    with pytest.raises(TypeError, match="is not a gscan2pdf session file"):
        thread.open("test.db")


def test_do_set_saved(mocker):
    "test do_set_saved"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_execute = mocker.patch.object(thread, "_execute")
    thread._con[threading.get_native_id()] = mocker.Mock()

    request = mocker.Mock()

    # Test single page_id, default saved=True
    request.args = [1]
    thread.do_set_saved(request)
    mock_execute.assert_called_with(
        "UPDATE page SET saved = ? WHERE id IN (?)", (True, 1)
    )

    # Test single page_id, explicit saved=False
    request.args = [1, False]
    thread.do_set_saved(request)
    mock_execute.assert_called_with(
        "UPDATE page SET saved = ? WHERE id IN (?)", (False, 1)
    )

    # Test multiple page_ids
    request.args = [[1, 2, 3], True]
    thread.do_set_saved(request)
    mock_execute.assert_called_with(
        "UPDATE page SET saved = ? WHERE id IN (?, ?, ?)", (True, 1, 2, 3)
    )


def test_run_unpaper_cmd_rtl(mocker):
    "test _run_unpaper_cmd with rtl direction"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "Processing sheet 1.pnm\n"
    mock_run.return_value.stderr = ""

    mocker.patch("os.path.getsize", return_value=100)
    mock_temp = mocker.patch("tempfile.NamedTemporaryFile")
    mock_temp.return_value.name = "temp_file"

    request = mocker.Mock()
    request.args = [
        {
            "dir": "/tmp",
            "options": {
                "command": ["unpaper", "--output-pages", "2", "out"],
                "direction": "rtl",
            },
        }
    ]

    out, out2 = thread._run_unpaper_cmd(request)

    # With RTL, out and out2 should be swapped
    # Normally out is the first temp file created (output-pages arg -2)
    # out2 is the second temp file created (output-pages arg -1)
    # The method swaps them if direction is rtl
    assert out != out2


def test_run_unpaper_cmd_rtl_error(mocker):
    "test _run_unpaper_cmd error handling"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    # Mock os.path.getsize to return 0 (empty file), triggering the error check
    mocker.patch("os.path.getsize", return_value=0)
    mock_temp = mocker.patch("tempfile.NamedTemporaryFile")
    mock_temp.return_value.name = "temp_file"

    request = mocker.Mock()
    request.args = [
        {
            "dir": "/tmp",
            "options": {
                "command": ["unpaper", "--output-pages", "2", "out"],
                "direction": "rtl",
            },
        }
    ]

    # Test stderr error
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = "some error"

    with pytest.raises(subprocess.CalledProcessError):
        thread._run_unpaper_cmd(request)
    request.data.assert_called_with("some error")

    # Reset command for the second call
    request.args[0]["options"]["command"] = ["unpaper", "--output-pages", "2", "out"]

    # Test stdout error (after processing replacement)
    mock_run.return_value.stdout = "Processing sheet 1.pnm\nError processing"
    mock_run.return_value.stderr = ""

    with pytest.raises(subprocess.CalledProcessError):
        thread._run_unpaper_cmd(request)
    request.data.assert_called_with("Error processing")


def test_check_cancelled():
    "test check_cancelled"

    thread = DocThread(db=":memory:")
    thread.cancel = False
    # should not raise
    thread.check_cancelled()

    thread.cancel = True
    with pytest.raises(CancelledError):
        thread.check_cancelled()


def test_do_analyse_empty_image(mocker):
    "test do_analyse with an empty image"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_page = mocker.Mock(spec=Page)
    mock_page.image_object = mocker.Mock()
    mock_page.id = 1
    mocker.patch.object(thread, "get_page", return_value=mock_page)
    mocker.patch.object(thread, "replace_page")
    mocker.patch.object(thread, "find_page_number_by_page_id")

    # Mock ImageStat.Stat to return count=[0]
    mock_stat = mocker.patch("PIL.ImageStat.Stat")
    mock_stat.return_value.count = [0]

    request = mocker.Mock()
    request.args = [{"list_of_pages": [1]}]

    thread.do_analyse(request)

    assert mock_page.mean == [0.0]
    assert mock_page.std_dev == [0.0]


def test_executemany_no_params(mocker):
    "test _executemany when params is None to cover line 111"
    thread = DocThread(db=":memory:")
    tid = threading.get_native_id()

    # Pre-populate _con and _cur to bypass _connect's real DB connection
    # and provide a mock cursor.
    mock_cur = mocker.Mock()
    thread._con[tid] = mocker.Mock()
    thread._cur[tid] = mock_cur

    # This should trigger line 111: self._cur[tid].executemany(query)
    thread._executemany("dummy query")

    mock_cur.executemany.assert_called_once_with("dummy query")


def test_open_newer_version(mocker):
    "test open session file with newer version"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_connect")
    mocker.patch.object(thread, "_execute")
    mocker.patch.object(
        thread,
        "_fetchone",
        side_effect=[
            (APPLICATION_ID,),
            (USER_VERSION + 1,),
            (1,),
        ],
    )
    mock_logger = mocker.patch("docthread.logger")

    thread.open("test.db")

    mock_logger.warning.assert_called()
    assert "%s was created by a newer version of gscan2pdf." in str(
        mock_logger.warning.call_args
    )


def test_insert_image_not_found(mocker):
    "test _insert_image with non-existent if_different_from"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_page = mocker.Mock(spec=Page)
    mock_page.to_bytes.return_value = b"image"

    mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_fetchone", return_value=None)

    with pytest.raises(ValueError, match="Image id 1 not found"):
        thread._insert_image(mock_page, if_different_from=1)


def test_add_page_exists(mocker):
    "test add_page when page already exists"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_take_snapshot")
    mocker.patch.object(thread, "find_row_id_by_page_number", return_value=1)

    mock_page = mocker.Mock(spec=Page)

    with pytest.raises(ValueError, match="Page 1 already exists"):
        thread.add_page(mock_page, number=1)


def test_replace_page_not_found(mocker):
    "test replace_page when page does not exist"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_take_snapshot")
    mocker.patch.object(thread, "find_row_id_by_page_number", return_value=None)

    mock_page = mocker.Mock(spec=Page)

    with pytest.raises(ValueError, match="Page 1 does not exist"):
        thread.replace_page(mock_page, number=1)


def test_do_delete_pages_row_ids(mocker):
    "test do_delete_pages with row_ids"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_take_snapshot")
    mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_executemany")
    mocker.patch.object(thread, "_fetchall", return_value=[])
    tid = threading.get_native_id()
    thread._con[tid] = mocker.Mock()
    thread._cur[tid] = mocker.Mock()

    request = mocker.Mock()
    request.args = [{"row_ids": [1, 2]}]

    thread.do_delete_pages(request)

    # We can inspect the calls if needed, or rely on execution
    assert thread._execute.call_count >= 1


def test_do_delete_pages_not_found(mocker):
    "test do_delete_pages when page number does not exist"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_take_snapshot")
    mocker.patch.object(thread, "find_row_id_by_page_number", return_value=None)

    request = mocker.Mock()
    request.args = [{"numbers": [1]}]

    with pytest.raises(ValueError, match="Page 1 does not exist"):
        thread.do_delete_pages(request)


def test_do_delete_pages_no_args(mocker):
    "test do_delete_pages with no args"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_take_snapshot")

    request = mocker.Mock()
    request.args = [{}]

    with pytest.raises(ValueError, match="Specify either row_id, page_id or number"):
        thread.do_delete_pages(request)


def test_find_page_number_by_page_id_found(mocker):
    "test find_page_number_by_page_id when found"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_fetchone", return_value=[5])

    result = thread.find_page_number_by_page_id(1)
    assert result == 5


def test_get_page_errors(mocker):
    "test get_page error conditions"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    # Test no args
    with pytest.raises(
        ValueError, match="Please specify either page number or page id"
    ):
        thread.get_page()

    mocker.patch.object(thread, "_execute")
    mocker.patch.object(thread, "_fetchone", return_value=None)

    # Test number not found
    with pytest.raises(ValueError, match="Page number 1 not found"):
        thread.get_page(number=1)

    # Test id not found
    with pytest.raises(ValueError, match="Page id 1 not found"):
        thread.get_page(id=1)


def test_do_tesseract_no_lang(mocker):
    "test do_tesseract with no language"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_page = mocker.Mock(spec=Page)
    mocker.patch.object(thread, "get_page", return_value=mock_page)

    request = mocker.Mock()
    request.args = [{"page": 1, "language": None}]

    with pytest.raises(ValueError, match="No tesseract language specified"):
        thread.do_tesseract(request)


def test_do_unpaper_ioerror(mocker):
    "test do_unpaper handling IOError"
    thread = DocThread(db=":memory:")
    thread._write_tid = threading.get_native_id()

    mock_page = mocker.Mock(spec=Page)
    mock_page.id = 1
    mock_page.get_depth.return_value = 1
    # Raising IOError from image.save to trigger the except block
    mock_page.image_object = mocker.Mock()
    mock_page.image_object.save.side_effect = IOError("Mocked IOError")

    mocker.patch.object(thread, "get_page", return_value=mock_page)

    request = mocker.Mock()
    request.args = [{"page": 1, "dir": "/tmp", "options": {"command": []}}]

    thread.do_unpaper(request)

    request.error.assert_called()
    assert "Error creating file in /tmp: Mocked IOError" in str(request.error.call_args)

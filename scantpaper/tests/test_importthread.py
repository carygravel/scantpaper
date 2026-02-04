"Tests for Importhread"

import subprocess
import unittest.mock
from types import SimpleNamespace
import pytest
from importthread import Importhread
from helpers import Proc


def test_get_file_info_session(mocker, temp_db):
    "Test that a SQLite database is identified as a session file"

    # Mock exec_command to return SQLite signature
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(
        returncode=0,
        stdout="SQLite 3.x database, last consolidated Tue Sep 14 10:23:44 2021",
        stderr="",
    )

    thread = Importhread()

    # path, password
    request = SimpleNamespace(args=(temp_db.name, None))
    info = thread.do_get_file_info(request)

    assert info["format"] == "session file"
    assert info["path"] == temp_db.name


def test_get_file_info_file_not_found():
    "Test that a non-existent file raises FileNotFoundError"

    thread = Importhread()

    request = SimpleNamespace(args=("/non/existent/file", None))
    with pytest.raises(FileNotFoundError, match="File /non/existent/file not found"):
        thread.do_get_file_info(request)


def test_get_file_info_zero_length(mocker, tmp_path):
    "Test that a zero-length file raises a RuntimeError"

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(returncode=0, stdout="empty", stderr="")

    thread = Importhread()

    request = SimpleNamespace(args=(str(empty_file), None))
    with pytest.raises(RuntimeError, match="Error importing zero-length file"):
        thread.do_get_file_info(request)


def test_get_djvu_info_no_djvudump(mocker):
    "Test that error is raised when djvudump is not found"
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(
        returncode=0,
        stdout="",
        stderr="command not found",
    )
    thread = Importhread()
    with pytest.raises(
        RuntimeError, match="Please install djvulibre-bin in order to open DjVu files"
    ):
        thread._get_djvu_info(None, None)


def test_get_djvu_info_corrupt(mocker):
    "Test that error is raised when structure corrupt"
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(
        returncode=0,
        stdout="""  FORM:DJVM [338]
    DIRM [53]         Document directory (bundled, 2 files 2 pages)
    FORM:DJVU [132] {2025-02-25.djvu} [P1]
      INFO [10]         DjVu 157x196, v24, 72 dpi, gamma=2.2
      INCL [15]         Indirection chunk --> {shared_anno.iff}
      BG44 [49]         IW4 data #1, 74 slices, v1.2 (b&w), 157x196
      BG44 [7]          IW4 data #2, 15 slices
      BG44 [4]          IW4 data #3, 10 slices
    FORM:DJVI [124] {shared_anno.iff} [S]
      ANTz [112]        Page annotation (hyperlinks, etc.)
""",
        stderr="",
    )
    thread = Importhread()
    with pytest.raises(
        RuntimeError, match="Unknown DjVu file structure. Please contact the author"
    ):
        thread._get_djvu_info({}, None)


@unittest.mock.patch("subprocess.run")
@unittest.mock.patch("subprocess.check_output")
@unittest.mock.patch("importthread.Page")
def test_do_import_djvu_annotation_error(mock_page, mock_co, mock_run):
    "Test that error is raised when import_djvu_ann raises an error"
    mock_run.return_value = Proc(
        returncode=0,
        stdout="",
        stderr="",
    )
    mock_co.return_value = Proc(
        returncode=0,
        stdout="",
        stderr="",
    )
    # Configure the mock Page instance
    mock_page_instance = mock_page.return_value
    mock_page_instance.import_djvu_ann.side_effect = PermissionError(
        "parsing DjVU annotation layer"
    )

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    mock_request.args = (
        {
            "first": 1,
            "last": 1,
            "dir": "/tmp",
            "info": {
                "path": "/to/file.djvu",
                "ppi": [300],
                "width": [100],
                "height": [100],
            },
        },
        None,
    )
    thread._do_import_djvu(mock_request)

    # Assert that the error was logged and the request.error was called
    mock_request.error.assert_called_once_with("Error: parsing DjVU annotation layer")


@unittest.mock.patch("subprocess.run")
def test_get_pdf_info_error(mock_run):
    "Test that request.error is thrown when pdfinfo returns error"
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["pdfinfo", "-isodates", "path/to/file.pdf"],
        output="",
        stderr="Permission denied",
    )
    thread = Importhread()
    mock_request = unittest.mock.Mock()
    thread._get_pdf_info({}, None, None, mock_request)
    mock_request.error.assert_called_once_with("Permission denied")


@unittest.mock.patch("subprocess.run")
@unittest.mock.patch("subprocess.check_output")
def test_get_pdf_images_error(mock_co, mock_run):
    "Test that request.error is thrown when pdfimages returns error"
    mock_co.return_value = """page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   1     0 image     157   196  gray    1   1  ccitt  no   [inline]      72    72    0B 0.0%
"""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["pdfimages", "-f"],
        output="",
        stderr="Permission denied",
    )
    thread = Importhread()
    mock_request = unittest.mock.Mock()
    mock_request.args = (
        {
            "first": 1,
            "last": 1,
            "dir": "/tmp",
            "password": "",
            "info": {
                "path": "/to/file.djvu",
            },
        },
        None,
    )
    thread._do_import_pdf(mock_request)
    mock_request.error.assert_called_once_with("Error extracting images from PDF")

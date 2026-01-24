"Tests for savethread.py"

import datetime
from unittest.mock import MagicMock, patch, mock_open
import pytest
from savethread import (
    SaveThread,
    prepare_output_metadata,
    _set_timestamp,
    _post_save_hook,
    _encrypt_pdf,
    _add_annotations_to_pdf,
)
from basethread import Request
from page import Page


class MockSaveThread(SaveThread):
    "Mock subclass of SaveThread for testing"

    def __init__(self):
        super().__init__()
        self.responses = MagicMock()
        self.paper_sizes = {}
        self.cancel = False
        self._write_tid = None
        self.progress = 0
        self.message = ""
        self.mock_pages = {}

    def get_page(self, page_id=None, **kwargs):
        "Mock get_page"
        if page_id is None:
            page_id = kwargs.get("id")
        if page_id in self.mock_pages:
            return self.mock_pages[page_id]
        raise ValueError(f"Page {page_id} not found")

    def do_set_saved(self, request):
        "Mock do_set_saved"

    def find_page_number_by_page_id(self, _page_id):
        "Mock find_page_number_by_page_id"
        return 1

    def replace_page(self, _page, _number):
        "Mock replace_page"
        return [1, None, "uuid"]

    def send(self, process, *args, **kwargs):
        "Mock send"
        return "uuid"


@pytest.fixture
def mock_thread_instance():
    "Fixture for MockSaveThread"
    return MockSaveThread()


@pytest.fixture
def mock_page_instance():
    "Fixture for mocked Page"
    page = MagicMock(spec=Page)
    page.id = 1
    page.uuid = "uuid1"
    page.resolution = (300, 300, "PixelsPerInch")
    page.get_resolution.return_value = (300, 300, "PixelsPerInch")
    page.text_layer = None
    page.annotations = None
    page.write_image_for_pdf = MagicMock()
    page.write_image_for_djvu = MagicMock()
    page.write_image_for_tiff = MagicMock()
    page.export_text.return_value = "Page Text"
    page.export_hocr.return_value = (
        "<html><body><div class='ocr_page'>HOCR</div></body></html>"
    )
    page.image_object = MagicMock()
    return page


# pylint: disable=redefined-outer-name


def test_save_pdf(mock_thread_instance, mock_page_instance):
    "Test save_pdf method"
    mock_thread_instance.mock_pages[1] = mock_page_instance

    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {},
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory") as mock_tempdir, patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf_data"
    ) as mock_img2pdf, patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ) as mock_pdf_to_hocr, patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ) as mock_hocr_to_ocr_pdf, patch(
        "savethread.os.remove"
    ), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ) as mock_post_save_hook, patch(
        "savethread.pathlib.Path"
    ) as mock_path:

        mock_tempdir.return_value.__enter__.return_value = "/tmp/tempdir"
        mock_path.return_value.__truediv__.return_value = "/tmp/tempdir/file"

        mock_thread_instance.do_save_pdf(request)

        assert mock_img2pdf.called
        assert mock_pdf_to_hocr.called
        assert mock_hocr_to_ocr_pdf.called
        assert mock_page_instance.write_image_for_pdf.called
        assert mock_post_save_hook.called


def test_save_pdf_with_hocr(mock_thread_instance, mock_page_instance):
    "Test save_pdf method with HOCR"
    mock_page_instance.text_layer = "some text layer data"
    mock_thread_instance.mock_pages[1] = mock_page_instance

    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {},
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory"), patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf_data"
    ), patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ), patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ), patch(
        "savethread.os.remove"
    ), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.pathlib.Path"
    ):

        mock_thread_instance.do_save_pdf(request)

        # Verify HOCR was exported/written
        assert mock_page_instance.export_hocr.called


def test_save_djvu(mock_thread_instance, mock_page_instance):
    "Test save_djvu method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.djvu",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {},
        "pidfile": "pidfile",
    }
    request = Request("save_djvu", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile") as mock_temp, patch(
        "savethread.exec_command"
    ) as mock_exec, patch("savethread.os.remove"), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.subprocess.run"
    ) as mock_run:

        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp.djvu"
        mock_exec.return_value.returncode = 0

        mock_thread_instance.do_save_djvu(request)

        assert mock_page_instance.write_image_for_djvu.called
        # Check djvm call
        args, _ = mock_exec.call_args
        assert args[0][0] == "djvm"

        # Check metadata call
        assert mock_run.called
        assert "djvused" in mock_run.call_args[0][0]


def test_save_djvu_failure(mock_thread_instance, mock_page_instance):
    "Test save_djvu method with merging failure"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.djvu",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {},
        "pidfile": "pidfile",
    }
    request = Request("save_djvu", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile") as mock_temp, patch(
        "savethread.exec_command"
    ) as mock_exec, patch("savethread.os.remove"), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.subprocess.run"
    ):

        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp.djvu"
        mock_exec.return_value.returncode = 1

        mock_thread_instance.do_save_djvu(request)

        assert mock_thread_instance.responses.put.called
        # Verify the error message was sent
        args, _ = mock_thread_instance.responses.put.call_args
        assert args[0].type.name == "ERROR"


def test_save_tiff(mock_thread_instance, mock_page_instance):
    "Test save_tiff method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.tif",
        "list_of_pages": [1],
        "options": {"compression": "jpeg", "quality": 75},
        "pidfile": "pidfile",
    }
    request = Request("save_tiff", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile") as mock_temp, patch(
        "savethread.subprocess.run"
    ) as mock_run, patch("savethread.os.remove"), patch("savethread._post_save_hook"):

        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp.tif"

        mock_thread_instance.do_save_tiff(request)

        assert mock_page_instance.write_image_for_tiff.called
        assert mock_run.called
        assert "tiffcp" in mock_run.call_args[0][0]
        assert "-c" in mock_run.call_args[0][0]
        assert "jpeg:75" in mock_run.call_args[0][0]


def test_save_tiff_ps(mock_thread_instance, mock_page_instance):
    "Test save_tiff method to PS"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.tif",
        "list_of_pages": [1],
        "options": {"ps": "/tmp/output.ps"},
        "pidfile": "pidfile",
    }
    request = Request("save_tiff", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile"), patch(
        "savethread.subprocess.run"
    ), patch("savethread.exec_command") as mock_exec, patch(
        "savethread.os.remove"
    ), patch(
        "savethread._post_save_hook"
    ):

        mock_exec.return_value.returncode = 0
        mock_exec.return_value.stderr = ""

        mock_thread_instance.do_save_tiff(request)

        assert mock_exec.called
        assert "tiff2ps" in mock_exec.call_args[0][0]


def test_save_tiff_ps_failure(mock_thread_instance, mock_page_instance):
    "Test save_tiff method to PS with failure"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.tif",
        "list_of_pages": [1],
        "options": {"ps": "/tmp/output.ps"},
        "pidfile": "pidfile",
    }
    request = Request("save_tiff", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile"), patch(
        "savethread.subprocess.run"
    ), patch("savethread.exec_command") as mock_exec, patch(
        "savethread.os.remove"
    ), patch(
        "savethread._post_save_hook"
    ):

        mock_exec.return_value.returncode = 1
        mock_exec.return_value.stderr = "Error converting"

        mock_thread_instance.do_save_tiff(request)

        assert mock_exec.called
        assert mock_thread_instance.responses.put.called
        args, _ = mock_thread_instance.responses.put.call_args
        assert args[0].type.name == "ERROR"


def test_save_image(mock_thread_instance, mock_page_instance):
    "Test save_image method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.png",
        "list_of_pages": [1],
        "options": {},
    }
    request = Request("save_image", (options,), mock_thread_instance.responses)

    with patch("savethread._post_save_hook") as mock_hook:
        mock_thread_instance.do_save_image(request)
        assert mock_page_instance.image_object.save.called
        mock_hook.assert_called_with("/tmp/output.png", {})


def test_save_image_multiple(mock_thread_instance, mock_page_instance):
    "Test save_image method with multiple pages"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    mock_thread_instance.mock_pages[2] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output-%d.png",
        "list_of_pages": [1, 2],
        "options": {},
    }
    request = Request("save_image", (options,), mock_thread_instance.responses)

    with patch("savethread._post_save_hook") as mock_hook:
        mock_thread_instance.do_save_image(request)
        assert mock_page_instance.image_object.save.call_count == 2
        mock_hook.assert_any_call("/tmp/output-1.png", {})
        mock_hook.assert_any_call("/tmp/output-2.png", {})


def test_save_text(mock_thread_instance, mock_page_instance):
    "Test save_text method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {"path": "/tmp/output.txt", "list_of_pages": [1]}
    request = Request("save_text", (options,), mock_thread_instance.responses)

    with patch("savethread.open", mock_open()) as mock_file, patch(
        "savethread._post_save_hook"
    ):

        mock_thread_instance.do_save_text(request)

        assert mock_page_instance.export_text.called
        mock_file().write.assert_called_with("Page Text")


def test_save_hocr(mock_thread_instance, mock_page_instance):
    "Test save_hocr method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {"path": "/tmp/output.hocr", "list_of_pages": [1], "options": {}}
    request = Request("save_hocr", (options,), mock_thread_instance.responses)

    with patch("savethread.open", mock_open()) as mock_file, patch(
        "savethread._post_save_hook"
    ):

        mock_thread_instance.do_save_hocr(request)

        assert mock_page_instance.export_hocr.called
        mock_file().write.assert_called()


def test_user_defined(mock_thread_instance, mock_page_instance):
    "Test user_defined method"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "page": 1,
        "dir": "/tmp",
        "command": "echo %i %o %r",
        "uuid": "uuid",
        "page_uuid": "page_uuid",
    }
    request = Request("user_defined", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.NamedTemporaryFile") as mock_temp, patch(
        "savethread.subprocess.run"
    ) as mock_run, patch("savethread.Image.open"), patch("savethread.Page"):

        # Mock the context manager return values directly
        mock_infile = MagicMock()
        mock_infile.name = "infile"
        mock_outfile = MagicMock()
        mock_outfile.name = "outfile"

        mock_temp.return_value.__enter__.side_effect = [
            mock_infile,
            mock_outfile,
        ]

        mock_run.return_value.stdout = "stdout"
        mock_run.return_value.stderr = ""

        mock_thread_instance.do_user_defined(request)

        assert mock_page_instance.image_object.save.called
        assert mock_run.called
        assert mock_thread_instance.responses.put.called


def test_set_timestamp():
    "Test _set_timestamp function"
    options = {
        "path": "/tmp/file",
        "metadata": {"datetime": datetime.datetime(2023, 1, 1, 12, 0, 0)},
        "options": {"set_timestamp": True},
    }

    with patch("savethread.os.utime") as mock_utime:
        _set_timestamp(options)
        assert mock_utime.called


def test_post_save_hook():
    "Test _post_save_hook function"
    with patch("savethread.subprocess.run") as mock_run:
        _post_save_hook("/tmp/file", {"post_save_hook": "echo %i"})
        assert mock_run.called
        assert "echo" in mock_run.call_args[0][0]
        assert "/tmp/file" in mock_run.call_args[0][0]


def test_encrypt_pdf():
    "Test _encrypt_pdf function"
    request = MagicMock()
    with patch("savethread.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        options = {"path": "/tmp/output.pdf", "options": {"user-password": "password"}}
        ret = _encrypt_pdf("/tmp/input.pdf", options, request)
        assert ret == 0
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "pdftk" in cmd
        assert "user_pw" in cmd


def test_prepare_output_metadata():
    "Test prepare_output_metadata function"
    metadata = {
        "datetime": datetime.datetime(2023, 1, 1, 12, 0, 0),
        "author": "Author",
        "title": "Title",
    }
    out = prepare_output_metadata("PDF", metadata)
    assert out["author"] == "Author"
    assert out["creationdate"] == metadata["datetime"]
    assert out["creator"].startswith("gscan2pdf v")


def test_save_pdf_prepend(mock_thread_instance, mock_page_instance):
    "Test save_pdf method with prepend"
    mock_thread_instance.mock_pages[1] = mock_page_instance
    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {"prepend": "/tmp/existing.pdf"},
        "pidfile": "pidfile",
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory"), patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf"
    ), patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ), patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ), patch(
        "savethread.os.remove"
    ), patch(
        "savethread.os.rename"
    ) as mock_rename, patch(
        "savethread.exec_command"
    ) as mock_exec, patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.pathlib.Path"
    ):

        mock_exec.return_value.returncode = 0
        mock_thread_instance.do_save_pdf(request)

        assert mock_rename.called
        assert mock_exec.called
        assert "pdfunite" in mock_exec.call_args[0][0]


def test_add_annotations_to_pdf():
    "Test _add_annotations_to_pdf function"
    mock_pdf_page = MagicMock()
    mock_gs_page = MagicMock()
    mock_gs_page.get_resolution.return_value = (300, 300, "units")
    mock_gs_page.height = 1000
    mock_gs_page.annotations = {
        "bbox": [[0, 0, 100, 100]],
        "children": [{"type": "text", "text": "foo", "bbox": [10, 10, 50, 50]}],
    }

    with patch("savethread.Bboxtree") as mock_bboxtree, patch(
        "savethread.px2pt", side_effect=lambda x, y: x
    ):

        mock_bboxtree.return_value.each_bbox.return_value = [
            {"type": "highlight", "text": "foo", "bbox": [10, 10, 50, 50]}
        ]

        _add_annotations_to_pdf(mock_pdf_page, mock_gs_page)

        assert mock_pdf_page.annotation.called


def test_save_pdf_with_password(mock_thread_instance, mock_page_instance):
    "Test save_pdf method with password protection"
    mock_thread_instance.mock_pages[1] = mock_page_instance

    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {"user-password": "password"},
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory"), patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf_data"
    ), patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ), patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ), patch(
        "savethread.os.remove"
    ), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.pathlib.Path"
    ), patch(
        "savethread._encrypt_pdf", return_value=0
    ) as mock_encrypt:

        mock_thread_instance.do_save_pdf(request)

        assert mock_encrypt.called


def test_save_pdf_with_password_failure(mock_thread_instance, mock_page_instance):
    "Test save_pdf method with password protection failure"
    mock_thread_instance.mock_pages[1] = mock_page_instance

    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {"user-password": "password"},
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory"), patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf_data"
    ), patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ), patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ), patch(
        "savethread.os.remove"
    ), patch(
        "savethread._set_timestamp"
    ) as mock_timestamp, patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.pathlib.Path"
    ), patch(
        "savethread._encrypt_pdf", return_value=1
    ) as mock_encrypt:

        mock_thread_instance.do_save_pdf(request)

        assert mock_encrypt.called
        assert not mock_timestamp.called


def test_save_pdf_ps_failure(mock_thread_instance, mock_page_instance):
    "Test save_pdf method with PS conversion failure"
    mock_thread_instance.mock_pages[1] = mock_page_instance

    options = {
        "dir": "/tmp",
        "path": "/tmp/output.pdf",
        "list_of_pages": [1],
        "metadata": {"datetime": datetime.datetime.now()},
        "options": {"ps": "/tmp/output.ps", "pstool": "pdf2ps"},
        "pidfile": "pidfile",
    }
    request = Request("save_pdf", (options,), mock_thread_instance.responses)

    with patch("savethread.tempfile.TemporaryDirectory"), patch(
        "savethread.tempfile.NamedTemporaryFile"
    ), patch("savethread.open", mock_open()), patch(
        "savethread.img2pdf.convert", return_value=b"pdf_data"
    ), patch(
        "savethread.ocrmypdf.api._pdf_to_hocr"
    ), patch(
        "savethread.ocrmypdf.api._hocr_to_ocr_pdf"
    ), patch(
        "savethread.os.remove"
    ), patch(
        "savethread._set_timestamp"
    ), patch(
        "savethread._post_save_hook"
    ), patch(
        "savethread.pathlib.Path"
    ), patch(
        "savethread.exec_command"
    ) as mock_exec:

        # Simulate failure
        mock_exec.return_value.returncode = 1
        mock_exec.return_value.stderr = "Error converting"

        mock_thread_instance.do_save_pdf(request)

        assert mock_exec.called
        assert mock_thread_instance.responses.put.called

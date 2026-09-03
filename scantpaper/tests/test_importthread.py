"""Tests for Importhread."""

import pathlib
import subprocess
import unittest.mock
from types import SimpleNamespace

import pytest
from helpers import Proc
from importthread import (
    Importhread,
    _composite_over_white,
    _correlate_pdf_images,
    _parse_pdfimages_list,
)
from PIL import Image

_PDFIMAGES_LIST_HEADER = (
    "page   num  type   width height color comp bpc  enc interp"
    "  object ID x-ppi y-ppi size ratio\n"
    "--------------------------------------------------------------------------------------------\n"
)


def _pdfimages_list(*lines):
    """Build a pdfimages -list capture from the given image data lines."""
    return _PDFIMAGES_LIST_HEADER + "\n".join(lines) + "\n"


def test_parse_pdfimages_list():
    """Test _parse_pdfimages_list parses a data line into an entry."""
    out = _pdfimages_list(
        "   1     0 image     600   200  gray    1   8  image  no"
        "        20  0    72    72  992B 0.8%"
    )
    assert _parse_pdfimages_list(out) == [
        {
            "page": 1,
            "num": 0,
            "type": "image",
            "x_ppi": 72.0,
            "y_ppi": 72.0,
        }
    ]


def test_parse_pdfimages_list_types():
    """Test _parse_pdfimages_list captures image, smask and stencil types."""
    out = _pdfimages_list(
        "   1     0 image     600   200  gray    1   8  image  no"
        "        20  0    72    72  992B 0.8%",
        "   1     1 smask     600   200  gray    1   8  image  no"
        "        20  0    72    72 8624B 7.2%",
        "   1     2 stencil   600   200  gray    1   1  image  no"
        "        20  0    72    72 1500B 0.8%",
    )
    entries = _parse_pdfimages_list(out)
    assert [entry["type"] for entry in entries] == ["image", "smask", "stencil"]


def test_parse_pdfimages_list_no_images():
    """Test _parse_pdfimages_list returns an empty list for header-only output."""
    out = _pdfimages_list()
    assert not _parse_pdfimages_list(out)


def test_parse_pdfimages_list_inline():
    """Test _parse_pdfimages_list handles inline images without an object ID."""
    out = _pdfimages_list(
        "   1     0 image     157   196  gray    1   1  ccitt  no"
        "   [inline]      72    72    0B 0.0%"
    )
    assert _parse_pdfimages_list(out) == [
        {
            "page": 1,
            "num": 0,
            "type": "image",
            "x_ppi": 72.0,
            "y_ppi": 72.0,
        }
    ]


def test_composite_over_white_opaque_and_transparent(tmp_path):
    """Test that compositing over white keeps opaque pixels and makes transparent ones white."""
    image = Image.new("L", (2, 1))
    image.putpixel((0, 0), 200)
    image.putpixel((1, 0), 0)
    mask = Image.new("L", (2, 1))
    mask.putpixel((0, 0), 255)
    mask.putpixel((1, 0), 0)
    image_path = tmp_path / "img.pgm"
    mask_path = tmp_path / "mask.pgm"
    image.save(image_path)
    mask.save(mask_path)

    assert _composite_over_white(image_path, mask_path) is True

    result = Image.open(image_path)
    assert result.getpixel((0, 0)) == 200, "opaque mask keeps the image value"
    assert result.getpixel((1, 0)) == 255, "transparent mask becomes white"


def test_composite_over_white_half_alpha(tmp_path):
    """Test that a 50% mask blends image and white to the midpoint."""
    image_path = tmp_path / "img.pgm"
    mask_path = tmp_path / "mask.pgm"
    Image.new("L", (1, 1), 200).save(image_path)
    Image.new("L", (1, 1), 128).save(mask_path)

    assert _composite_over_white(image_path, mask_path) is True

    result = Image.open(image_path)
    assert result.getpixel((0, 0)) == 227  # (200*128 + 255*127) // 255


def test_composite_over_white_color(tmp_path):
    """Test that a color image is composited per channel."""
    image_path = tmp_path / "img.ppm"
    mask_path = tmp_path / "mask.pgm"
    Image.new("RGB", (1, 1), (10, 20, 30)).save(image_path)
    Image.new("L", (1, 1), 128).save(mask_path)

    assert _composite_over_white(image_path, mask_path) is True

    result = Image.open(image_path)
    assert result.getpixel((0, 0)) == (132, 137, 142)


def test_composite_over_white_size_mismatch(tmp_path):
    """Test that a size mismatch returns False and leaves the files untouched."""
    image_path = tmp_path / "img.pgm"
    mask_path = tmp_path / "mask.pgm"
    Image.new("L", (2, 2), 200).save(image_path)
    Image.new("L", (3, 3), 128).save(mask_path)
    before_image = image_path.read_bytes()
    before_mask = mask_path.read_bytes()

    assert _composite_over_white(image_path, mask_path) is False
    assert image_path.read_bytes() == before_image, "image file untouched"
    assert mask_path.read_bytes() == before_mask, "mask file untouched"


def test_correlate_pdf_images_pairs_smask(mocker):
    """Test that an image entry is paired with the smask that follows it."""
    mocker.patch.object(pathlib.Path, "glob", return_value=["x-000.pnm", "x-001.pnm"])
    remove = mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    entries = [
        {"page": 1, "num": 0, "type": "image", "x_ppi": 300.0, "y_ppi": 300.0},
        {"page": 1, "num": 1, "type": "smask", "x_ppi": 300.0, "y_ppi": 300.0},
    ]

    result, warning = _correlate_pdf_images(entries)

    assert warning is False
    assert result == [("x-000.pnm", 300.0, 300.0, "x-001.pnm")]
    assert not remove.called, "paired mask is not removed by the correlator"


def test_correlate_pdf_images_removes_unpaired_smask(mocker):
    """Test that an smask without a preceding image is removed."""
    mocker.patch.object(pathlib.Path, "glob", return_value=["x-000.pnm", "x-001.pnm"])
    remove = mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    entries = [
        {"page": 1, "num": 0, "type": "smask", "x_ppi": 300.0, "y_ppi": 300.0},
        {"page": 1, "num": 1, "type": "image", "x_ppi": 300.0, "y_ppi": 300.0},
    ]

    result, warning = _correlate_pdf_images(entries)

    assert warning is False
    assert result == [("x-001.pnm", 300.0, 300.0, None)]
    remove.assert_any_call(pathlib.Path("x-000.pnm"))


def test_get_file_info_session(mocker, temp_db):
    """Test that a SQLite database is identified as a session file."""
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
    """Test that a non-existent file raises FileNotFoundError."""
    thread = Importhread()

    request = SimpleNamespace(args=("/non/existent/file", None))
    with pytest.raises(FileNotFoundError, match="File /non/existent/file not found"):
        thread.do_get_file_info(request)


def test_get_file_info_zero_length(mocker, tmp_path):
    """Test that a zero-length file raises a RuntimeError."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(returncode=0, stdout="empty", stderr="")

    thread = Importhread()

    request = SimpleNamespace(args=(str(empty_file), None))
    with pytest.raises(RuntimeError, match="Error importing zero-length file"):
        thread.do_get_file_info(request)


def test_get_file_info_no_stdout(mocker):
    """Test that a zero-length file raises a RuntimeError."""
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(returncode=-1, stdout=None, stderr="not found")
    thread = Importhread()
    request = SimpleNamespace(args=("", None))
    with pytest.raises(RuntimeError, match="Error getting file info for : not found"):
        thread.do_get_file_info(request)


def test_get_djvu_info_no_djvudump(mocker):
    """Test that error is raised when djvudump is not found."""
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(
        returncode=-1,
        stdout=None,
        stderr="not found",
    )
    thread = Importhread()
    with pytest.raises(
        RuntimeError, match="Please install djvulibre-bin in order to open DjVu files"
    ):
        thread._get_djvu_info({}, None)


def test_get_djvu_info_no_djvused(mocker):
    """Test that error is raised when djvused is not found."""
    mock_exec = mocker.patch("importthread.exec_command")

    # First call for djvudump succeeds
    mock_exec.side_effect = [
        Proc(0, "DjVu 100x100, 300 dpi\n 1 page", ""),
        Proc(-1, None, "not found"),
    ]

    thread = Importhread()
    with pytest.raises(
        RuntimeError, match="Please install djvulibre-bin in order to open DjVu files"
    ):
        thread._get_djvu_info(
            {"pages": 1, "width": [100], "height": [100], "ppi": [300]}, None
        )


def test_get_tif_info_no_tiffinfo(mocker):
    """Test that error is raised when tiffinfo is not found."""
    mock_exec = mocker.patch("importthread.exec_command")
    mock_exec.return_value = Proc(
        returncode=-1,
        stdout=None,
        stderr="not found",
    )
    thread = Importhread()
    with pytest.raises(
        RuntimeError, match="Please install libtiff-tools in order to open TIFF files"
    ):
        thread._get_tif_info({}, None, None)


def test_get_djvu_info_corrupt(mocker):
    """Test that error is raised when structure corrupt."""
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
    with pytest.raises(RuntimeError, match="Unknown DjVu file structure"):
        thread._get_djvu_info({}, None)


@unittest.mock.patch("importthread.exec_command_run")
@unittest.mock.patch("importthread.Page")
def test_do_import_djvu_annotation_error(mock_page, mock_run):
    """Test that error is raised when import_djvu_ann raises an error."""
    mock_run.return_value = Proc(
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


@unittest.mock.patch("importthread.exec_command_run")
def test_get_pdf_info_error(mock_run):
    """Test that request.error is thrown when pdfinfo returns error."""
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


@unittest.mock.patch("importthread.exec_command_run")
def test_get_pdf_images_error(mock_run):
    """Test that request.error is thrown when pdfimages returns error."""
    mock_run.side_effect = [
        Proc(
            returncode=0,
            stdout=_PDFIMAGES_LIST_HEADER
            + "   1     0 image     157   196  gray    1   1  ccitt  no   [inline]"
            + "      72    72    0B 0.0%"
            + "\n",
            stderr="",
        ),
        subprocess.CalledProcessError(
            returncode=1,
            cmd=["pdfimages", "-f"],
            output="",
            stderr="Permission denied",
        ),
    ]
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


@unittest.mock.patch("importthread.exec_command_run")
@unittest.mock.patch.object(pathlib.Path, "glob")
@unittest.mock.patch("importthread.Page")
def test_import_pdf_image_error(mock_page, mock_glob, mock_run):
    """Test that request.error is thrown when importing individual images fails."""
    mock_run.side_effect = [
        Proc(
            returncode=0,
            stdout=_PDFIMAGES_LIST_HEADER
            + "   1     0 image     157   196  gray    1   1  ccitt  no   [inline]"
            + "      72    72    0B 0.0%"
            + "\n",
            stderr="",
        ),
        unittest.mock.Mock(returncode=0),
    ]

    # Simulate the presence of image files
    mock_glob.side_effect = [[], ["x-01.pnm"]]

    # Simulate an error during Page initialization
    mock_page.side_effect = PermissionError("Error importing PDF")

    thread = Importhread()
    mock_request = unittest.mock.Mock()
    mock_request.args = (
        {
            "first": 1,
            "last": 1,
            "dir": "/tmp",
            "password": "",
            "info": {
                "path": "/to/file.pdf",
            },
        },
        None,
    )

    # Call the method
    thread._do_import_pdf(mock_request)

    # Assert that the error was logged and the request.error was called
    mock_request.error.assert_called_once_with("Error importing PDF")


_LIST_IMAGE = _pdfimages_list(
    "   1     0 image     600   200  gray    1   8  image  no        20  0    72    72  992B 0.8%"
)

_LIST_IMAGE_SMASK = _pdfimages_list(
    "   1     0 image     600   200  gray    1   8  image  no        20  0    72    72  992B 0.8%",
    "   1     1 smask     600   200  gray    1   8  image  no        20  0    72    72 8624B 7.2%",
)

_LIST_IMAGE_SMASK_DIFFERENT_PPI = _pdfimages_list(
    "   1     0 image     600   200  gray    1   8  image  no        20  0   150   150  992B 0.8%",
    "   1     1 smask     600   200  gray    1   8  image  no        20  0    72    72 8624B 7.2%",
)

_LIST_TWO_IMAGES = _pdfimages_list(
    "   1     0 image     600   200  gray    1   8  image  no        20  0    72    72  992B 0.8%",
    "   1     1 image     600   200  gray    1   8  image  no        20  0    72    72  992B 0.8%",
)


def _pdf_import_args(first, last):
    """Build the args for _do_import_pdf."""
    return {
        "first": first,
        "last": last,
        "dir": "/tmp",
        "password": "",
        "info": {"path": "/to/file.pdf"},
    }


def _pdf_import_request(mock_request, first, last):
    """Attach args to a mocked request."""
    mock_request.args = (_pdf_import_args(first, last), None)


def _pdf_exec_command_run_side_effect(list_output):
    """Mock exec_command_run for _do_import_pdf tests."""

    def _side_effect(cmd, _pidfile=None, **_kwargs):
        if "-list" in cmd:
            return Proc(returncode=0, stdout=list_output, stderr="")
        return unittest.mock.Mock(returncode=0)

    return _side_effect


@unittest.mock.patch.object(pathlib.Path, "unlink", autospec=True)
@unittest.mock.patch("importthread.exec_command_run")
@unittest.mock.patch.object(pathlib.Path, "glob")
@unittest.mock.patch("importthread.Page")
def test_import_pdf_skips_smask(mock_page, mock_glob, mock_run, mock_remove):
    """Test that a soft mask is not imported as a page."""
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_IMAGE_SMASK)
    mock_glob.side_effect = [[], ["x-000.pnm", "x-001.pnm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    assert mock_page.call_count == 1, "only the image is imported as a page"
    assert mock_page.call_args.kwargs["filename"] == "x-000.pnm"
    mock_remove.assert_any_call(pathlib.Path("x-001.pnm"))
    mock_request.error.assert_not_called()


def test_import_pdf_no_warning_for_smask(mocker):
    """Test that an image plus soft mask does not trigger a warning."""
    mocker.patch("importthread.Page")
    mock_glob = mocker.patch.object(pathlib.Path, "glob")
    mock_run = mocker.patch("importthread.exec_command_run")
    mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_IMAGE_SMASK)
    mock_glob.side_effect = [[], ["x-000.pnm", "x-001.pnm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    mock_request.error.assert_not_called()


def test_import_pdf_warning_for_two_images(mocker):
    """Test that two real images on a page trigger a warning."""
    mock_page = mocker.patch("importthread.Page")
    mock_glob = mocker.patch.object(pathlib.Path, "glob")
    mock_run = mocker.patch("importthread.exec_command_run")
    mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_TWO_IMAGES)
    mock_glob.side_effect = [[], ["x-000.pnm", "x-001.pnm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    assert mock_page.call_count == 2, "both images imported as pages"
    args, _kwargs = mock_request.error.call_args
    assert args[0] is None, "warning not an error"
    assert "expects one image per page" in args[1]


def test_import_pdf_resolution_from_own_entry(mocker):
    """Test that the imported page resolution comes from its own -list entry."""
    mock_page = mocker.patch("importthread.Page")
    mock_glob = mocker.patch.object(pathlib.Path, "glob")
    mock_run = mocker.patch("importthread.exec_command_run")
    mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    mock_run.side_effect = _pdf_exec_command_run_side_effect(
        _LIST_IMAGE_SMASK_DIFFERENT_PPI
    )
    mock_glob.side_effect = [[], ["x-000.pnm", "x-001.pnm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    assert mock_page.call_count == 1
    assert mock_page.call_args.kwargs["resolution"] == (150.0, 150.0, "PixelsPerInch")


def test_import_pdf_count_mismatch_fallback(mocker):
    """Test that a count mismatch imports every file and warns."""
    mock_page = mocker.patch("importthread.Page")
    mock_glob = mocker.patch.object(pathlib.Path, "glob")
    mock_run = mocker.patch("importthread.exec_command_run")
    mocker.patch.object(pathlib.Path, "unlink", autospec=True)
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_IMAGE)
    mock_glob.side_effect = [[], ["x-000.pnm", "x-001.pnm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    assert mock_page.call_count == 2, "every extracted file imported"
    args, _kwargs = mock_request.error.call_args
    assert args[0] is None, "warning not an error"
    assert "expects one image per page" in args[1]


@unittest.mock.patch.object(pathlib.Path, "unlink", autospec=True)
@unittest.mock.patch("importthread.exec_command_run")
@unittest.mock.patch.object(pathlib.Path, "glob")
@unittest.mock.patch("importthread.Page")
def test_import_pdf_cleans_up_leftover_files(
    mock_page, mock_glob, mock_run, mock_remove
):
    """Test that leftover extraction files are removed before the next page."""
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_IMAGE)
    mock_glob.side_effect = [
        [],
        ["x-000.pnm"],
        ["x-002.pnm"],
        ["x-000.pnm"],
    ]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 2)

    thread._do_import_pdf(mock_request)

    assert mock_page.call_count == 2, "one page imported per PDF page"
    mock_remove.assert_any_call(pathlib.Path("x-002.pnm"))


@unittest.mock.patch.object(pathlib.Path, "unlink", autospec=True)
@unittest.mock.patch("importthread.exec_command_run")
@unittest.mock.patch.object(pathlib.Path, "glob")
def test_import_pdf_imports_composited_image(
    mock_glob, mock_run, mock_remove, monkeypatch, tmp_path
):
    """Test that an image with a soft mask is imported as a single composited page."""
    image = Image.new("L", (2, 1))
    image.putpixel((0, 0), 200)
    image.putpixel((1, 0), 0)
    image.save(tmp_path / "x-000.pgm")
    mask = Image.new("L", (2, 1))
    mask.putpixel((0, 0), 255)
    mask.putpixel((1, 0), 0)
    mask.save(tmp_path / "x-001.pgm")
    monkeypatch.chdir(tmp_path)
    mock_run.side_effect = _pdf_exec_command_run_side_effect(_LIST_IMAGE_SMASK)
    mock_glob.side_effect = [[], ["x-000.pgm", "x-001.pgm"]]

    thread = Importhread()
    thread.add_page = unittest.mock.Mock()
    mock_request = unittest.mock.Mock()
    _pdf_import_request(mock_request, 1, 1)

    thread._do_import_pdf(mock_request)

    assert thread.add_page.call_count == 1, "only the composited image is imported"
    page = thread.add_page.call_args[0][0]
    assert page.image_object.size == (2, 1)
    assert page.image_object.getpixel((0, 0)) == 200, "opaque mask keeps the value"
    assert page.image_object.getpixel((1, 0)) == 255, "transparent mask becomes white"
    mock_remove.assert_any_call(pathlib.Path("x-001.pgm"))


@unittest.mock.patch("importthread.exec_command_run")
def test_extract_text_from_pdf_error(mock_run):
    """Test that request.error is thrown when pdftotext fails."""
    # Simulate a subprocess error when running pdftotext
    mock_run.return_value = unittest.mock.Mock(returncode=1)

    thread = Importhread()
    mock_request = unittest.mock.Mock()
    mock_request.args = (
        {
            "info": {
                "path": "/to/file.pdf",
            },
            "dir": "/tmp",
            "password": "",
        },
        None,
    )

    # Call the method and check for the error
    thread._extract_text_from_pdf(mock_request, 1)
    mock_request.error.assert_called_once_with("Error extracting text layer from PDF")


def test_request_pidfile_from_attribute():
    """Test _request_pidfile returns a pidfile attached as a request attribute."""
    thread = Importhread()
    pidfile = SimpleNamespace()
    request = SimpleNamespace(pidfile=pidfile, args=())
    assert thread._request_pidfile(request) is pidfile


def test_request_pidfile_from_args_dict():
    """Test _request_pidfile finds a pidfile in the request args dict."""
    thread = Importhread()
    pidfile = SimpleNamespace()
    request = SimpleNamespace(pidfile=None, args=({"pidfile": pidfile},))
    assert thread._request_pidfile(request) is pidfile


def test_request_pidfile_none():
    """Test _request_pidfile returns None when no pidfile is present."""
    thread = Importhread()
    request = SimpleNamespace(pidfile=None, args=())
    assert thread._request_pidfile(request) is None


def test_request_completed_deregisters_pidfile():
    """Test _request_completed removes the pidfile from running_pids."""
    thread = Importhread()
    pidfile = "pidfile"
    thread.running_pids[pidfile] = pidfile
    request = SimpleNamespace(pidfile=pidfile, args=())
    thread._request_completed(request)
    assert pidfile not in thread.running_pids


def test_request_completed_ignores_missing():
    """Test _request_completed tolerates a pidfile not in running_pids."""
    thread = Importhread()
    pidfile = "pidfile"
    request = SimpleNamespace(pidfile=pidfile, args=())
    thread._request_completed(request)
    assert pidfile not in thread.running_pids

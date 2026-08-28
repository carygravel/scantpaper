"Tests for conftest helper functions"

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from conftest import _create_qbfox_image
from gi.repository import GLib
from PIL import Image, ImageFont


def test_qbfox_font_fallback():
    "Test _create_qbfox_image falls back to system font path"

    call_count = [0]
    original_truetype = ImageFont.truetype

    def mock_truetype(path, size):
        call_count[0] += 1
        if call_count[0] == 1:
            raise OSError("font not found")
        return original_truetype(path, size)

    with patch("PIL.ImageFont.truetype", side_effect=mock_truetype):
        img = _create_qbfox_image()
        assert img is not None
        assert call_count[0] >= 2


def test_qbfox_no_bbox():
    "Test _create_qbfox_image handles getbbox returning None"

    def mock_getbbox(_self):
        return None

    with patch.object(Image.Image, "getbbox", mock_getbbox):
        img = _create_qbfox_image()
        assert img is not None


KNOWN_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def test_qbfox_fc_match_fallback():
    """Test _create_qbfox_image uses fc-match when all explicit paths fail"""
    original_truetype = ImageFont.truetype

    def mock_truetype(path, size, **kwargs):
        if path in KNOWN_FONT_PATHS:
            raise OSError("font not found")
        return original_truetype(KNOWN_FONT_PATHS[0], size, **kwargs)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "/usr/share/fonts/truetype/arundina/ArundinaSans.ttf"

    with (
        patch("PIL.ImageFont.truetype", side_effect=mock_truetype),
        patch("subprocess.run", return_value=mock_result),
    ):
        img = _create_qbfox_image()
        assert img is not None


def test_qbfox_load_default_with_size():
    """Test _create_qbfox_image falls back to load_default(size=...)"""
    original_truetype = ImageFont.truetype

    def mock_truetype(path, size, **kwargs):
        if path in KNOWN_FONT_PATHS:
            raise OSError("font not found")
        return original_truetype(path, size, **kwargs)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with (
        patch("PIL.ImageFont.truetype", side_effect=mock_truetype),
        patch("subprocess.run", return_value=mock_result),
    ):
        img = _create_qbfox_image()
        assert img is not None


def test_qbfox_load_default_bitmap():
    """Test _create_qbfox_image falls back to bitmap load_default()"""
    original_truetype = ImageFont.truetype

    def mock_truetype(path, size, **kwargs):
        if path in KNOWN_FONT_PATHS:
            raise OSError("font not found")
        return original_truetype(path, size, **kwargs)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    original_load_default = ImageFont.load_default

    def mock_load_default_with_size(size=None):
        if size is not None:
            raise TypeError("this PIL version does not support size")
        return original_load_default()

    with (
        patch("PIL.ImageFont.truetype", side_effect=mock_truetype),
        patch("subprocess.run", return_value=mock_result),
        patch("PIL.ImageFont.load_default", side_effect=mock_load_default_with_size),
    ):
        img = _create_qbfox_image()
        assert img is not None


def test_qbfox_small_bbox_scale():
    """Test _create_qbfox_image scales up when cropped image is too small"""

    def mock_getbbox(_self):
        return (0, 0, 10, 10)

    with patch.object(Image.Image, "getbbox", mock_getbbox):
        img = _create_qbfox_image()
        assert img is not None


def test_clean_up_files_non_existent(clean_up_files):
    """Test clean_up_files handles non-existent files without error"""
    clean_up_files(["/nonexistent/file.txt"])


def test_get_page_sync_error(get_page_sync):
    """Test get_page_sync raises ValueError on error callback"""

    thread = MagicMock()

    def send_side_effect(*_, **kwargs):
        error_callback = kwargs["error_callback"]
        GLib.idle_add(lambda: error_callback(SimpleNamespace(status="mock_error")))

    thread.send.side_effect = send_side_effect

    with pytest.raises(ValueError, match="mock_error"):
        get_page_sync(thread)

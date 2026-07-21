"Tests for conftest helper functions"

from unittest.mock import patch
from PIL import Image, ImageFont
from conftest import _create_qbfox_image


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

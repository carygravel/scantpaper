"Test tesseract helper functions"

import re
import shutil
import pytest
from tesseract import languages, _iso639_1to3, locale_installed, get_tesseract_codes


def test_tesseract_code_conversions():
    "Test tesseract helper functions"

    assert languages(["eng", "deu", "chi-sim-vert"]) == {
        "chi-sim-vert": "Chinese - Simplified (vertical)",
        "eng": "English",
        "deu": "German",
    }, "test languages()"
    assert _iso639_1to3("en") == "eng", "_iso639_1to3 en"
    assert _iso639_1to3("C") == "eng", "_iso639_1to3 C"
    assert _iso639_1to3("zh") == "chi-sim", "_iso639_1to3 zh"
    assert locale_installed("en_GB", ["eng"]) == "", "language installed"
    assert re.search(
        r"install", locale_installed("de_DE", ["eng"])
    ), "language installable"
    assert re.search(
        r"developers", locale_installed("kw_KW", ["eng"])
    ), "language not installable"
    assert re.search(
        r"necessary", locale_installed("zz_ZZ", ["eng"])
    ), "language unknown"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_get_tesseract_codes():
    "test get_tesseract_codes()"
    assert isinstance(get_tesseract_codes(), list), "get_tesseract_codes() returns list"

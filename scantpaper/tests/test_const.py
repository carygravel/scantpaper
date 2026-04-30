"Tests for i18n helpers"

import sys
from unittest.mock import patch
import pytest
import const


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Requires Python 3.11 or higher")
def test_import_tomllib_for_python_311(monkeypatch):
    "Mock sys.version_info to simulate Python 3.11+"
    monkeypatch.setattr(sys, "version_info", (3, 11))

    # Reload the const module to apply the mocked version_info
    import importlib  # pylint: disable=import-outside-toplevel
    import const  # pylint: disable=import-outside-toplevel, redefined-outer-name, reimported

    importlib.reload(const)

    # Check if tomllib is imported
    assert const.tomllib.__name__ == "tomllib"


def test_import_tomli_for_python_310(monkeypatch):
    "Mock sys.version_info to simulate Python < 3.11"
    monkeypatch.setattr(sys, "version_info", (3, 10))

    # Reload the const module to apply the mocked version_info
    import importlib  # pylint: disable=import-outside-toplevel
    import const  # pylint: disable=import-outside-toplevel, redefined-outer-name, reimported

    importlib.reload(const)

    # Check if tomli is imported as tomllib
    assert const.tomllib.__name__ == "tomli"


def test_get_metadata():
    "Test getting metadata."
    with patch("importlib.metadata.version", side_effect="l"), patch(
        "pathlib.Path.is_file", return_value=False
    ):
        assert const.get_version() == "l"

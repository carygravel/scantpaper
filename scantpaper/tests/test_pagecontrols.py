"tests for PageControls dialog component"

import pytest
from dialog.pagecontrols import PageControls


def test_side_to_scan_invalid_value():
    "Test that ValueError is raised for invalid side-to-scan values"
    page_controls = PageControls()

    with pytest.raises(ValueError, match="Invalid value for side-to-scan: invalid"):
        PageControls.side_to_scan.fset(page_controls, "invalid")

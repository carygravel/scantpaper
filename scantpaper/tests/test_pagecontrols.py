"tests for PageControls dialog component"

from unittest.mock import MagicMock
import pytest
from dialog.pagecontrols import PageControls


def test_side_to_scan_invalid_value():
    "Test that ValueError is raised for invalid side-to-scan values"
    page_controls = PageControls()

    with pytest.raises(ValueError, match="Invalid value for side-to-scan: invalid"):
        PageControls.side_to_scan.fset(page_controls, "invalid")


def test_do_spin_buttoni_value_changed():
    "Test that spin_buttoni.set_value(value) is called when value is 0"
    page_controls = PageControls()

    # Mock the spin_buttoni object
    spin_buttoni = MagicMock()
    spin_buttoni.get_value.return_value = 0  # Simulate the spin button value being 0

    # Call the method
    page_controls._do_spin_buttoni_value_changed(spin_buttoni)

    # Assert that spin_buttoni.set_value() was called with the expected value
    spin_buttoni.set_value.assert_called_once_with(-page_controls.page_number_increment)

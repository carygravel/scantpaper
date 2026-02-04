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


def test_update_start_page_value_less_than_one():
    "Test that update_start_page sets value to 1 when value < 1"
    page_controls = PageControls()

    # Mock the document and its pages_possible method
    mock_document = MagicMock()

    # Simulate pages_possible returning 0 for values < 1, then 1 for value >= 1
    def pages_possible_side_effect(value, _step):
        return 0 if value < 1 else 1

    mock_document.pages_possible.side_effect = pages_possible_side_effect
    page_controls.document = mock_document

    # Set page_number_start to a value less than 1
    page_controls._page_number_start = -5

    # Call the method
    page_controls.update_start_page()

    # Assert that page_number_start is set to 1
    assert page_controls.page_number_start == 1


def test_reset_start_page_no_document():
    "Test that reset_start_page returns immediately when document is None"
    page_controls = PageControls()
    page_controls.document = None
    # Call the method and ensure no exceptions are raised
    page_controls.reset_start_page()


def test_reset_start_page_no_data():
    "Test that reset_start_page sets page_number_start to 1 when document has no data"
    page_controls = PageControls()

    # Mock the document with no data
    mock_document = MagicMock()
    mock_document.data = []
    page_controls.document = mock_document

    # Call the method
    page_controls.reset_start_page()

    # Assert that page_number_start is set to 1
    assert page_controls.page_number_start == 1

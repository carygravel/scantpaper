"Tests for the EditMenuMixins."

from unittest.mock import MagicMock
from edit_menu_mixins import EditMenuMixins


def test_copy_selection():
    "Test that copy_selection"

    class MockWindow(EditMenuMixins):
        "Mock window for testing EditMenuMixins."

        def __init__(self):
            self.slist = MagicMock()
            self._update_uimanager = MagicMock()

    window = MockWindow()

    # Call the method
    window.copy_selection(None, None)

    # Assert that slist.copy_selection was called correctly
    window.slist.copy_selection.assert_called_once_with()

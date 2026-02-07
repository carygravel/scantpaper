"Tests for postprocess_controls.py"

from unittest.mock import MagicMock
import pytest
from postprocess_controls import RotateControlRow, RotateControls, OCRControls
from session_mixins import SessionMixins
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


# Mock tesseract functions
def mock_get_tesseract_codes():
    "mock get_tesseract_codes"
    return ["eng", "deu"]


def mock_languages(_codes):
    "mock languages"
    return {"eng": "English", "deu": "German"}


@pytest.fixture
def mock_ocr_setup(mocker):
    "fixture for ocr setup"
    mocker.patch(
        "postprocess_controls.get_tesseract_codes", side_effect=mock_get_tesseract_codes
    )
    mocker.patch("postprocess_controls.languages", side_effect=mock_languages)


def test_ocr_controls_default_language(mock_ocr_setup):
    "Test that OCRControls defaults to the first language if none provided"

    controls = OCRControls(
        available_engines=[["tesseract", "Tesseract", "desc"]],
        engine="tesseract",
        language=None,  # Explicitly None
        active=False,
        threshold=False,
        threshold_value=50,
    )

    # If language is None, we expect language to be set to index of first
    # language (sorted).
    assert controls.language is not None


def test_error_callback_crash(mocker):
    "Test that _error_callback does not crash with int page"

    # Mocking SessionMixins which contains _error_callback
    class MockApp(SessionMixins):
        "Mock App"

        def __init__(self):
            self.slist = mocker.Mock()
            self.post_process_progress = mocker.Mock()
            self.settings = {"message": {}}

    app = MockApp()

    # Setup mock response
    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": 2}]  # int page
    mock_response.request.process = "tesseract"
    mock_response.type.name = "ERROR"
    mock_response.status = "Some error"

    # Mock slist behavior
    # find_page_by_uuid is called.
    app.slist.find_page_by_uuid.return_value = 0
    app.slist.data = [[1, None, 2]]  # [page_num, thumb, page_id]

    # This should not raise AttributeError anymore
    try:
        app._error_callback(mock_response)  # pylint: disable=protected-access
    except AttributeError as exc:
        pytest.fail(f"Raised AttributeError: {exc}")


def test_rotate_control_row_init():
    "Test RotateControlRow initialization"
    row = RotateControlRow()
    assert isinstance(row.cbutton, Gtk.CheckButton)
    assert isinstance(row.side_cmbx, Gtk.ComboBox)
    assert isinstance(row.angle_cmbx, Gtk.ComboBox)


class TestRotateControls:
    "Tests for RotateControls class"

    @pytest.fixture
    def rotate_controls(self):
        "Fixture to create RotateControls instance"
        return RotateControls()

    def test_init(self, rotate_controls):
        "Test initialization"
        assert isinstance(rotate_controls, Gtk.Box)
        assert rotate_controls.get_orientation() == Gtk.Orientation.VERTICAL
        assert rotate_controls._rotate_facing == 0
        assert rotate_controls._rotate_reverse == 0
        assert rotate_controls.can_duplex is True

    def test_rotate_facing_property(self, rotate_controls):
        "Test rotate_facing property"
        rotate_controls.rotate_facing = 90
        assert rotate_controls.rotate_facing == 90
        assert rotate_controls._rotate_facing == 90
        # Should verify _update_gui called, checked by UI state implicitly

        # Set same value, should return early (coverage check)
        rotate_controls.rotate_facing = 90

    def test_rotate_reverse_property(self, rotate_controls):
        "Test rotate_reverse property"
        rotate_controls.rotate_reverse = 180
        assert rotate_controls.rotate_reverse == 180
        assert rotate_controls._rotate_reverse == 180

        # Set same value
        rotate_controls.rotate_reverse = 180

    def test_can_duplex_property(self, rotate_controls):
        "Test can_duplex property"
        rotate_controls.can_duplex = False
        assert rotate_controls.can_duplex is False
        assert not rotate_controls._side1.side_cmbx.get_visible()
        assert not rotate_controls._side2.side_cmbx.get_visible()

        rotate_controls.can_duplex = True
        assert rotate_controls.can_duplex is True
        assert rotate_controls._side1.side_cmbx.get_visible()
        assert rotate_controls._side2.side_cmbx.get_visible()

        # Set same value
        rotate_controls.can_duplex = True

    def test_toggled_rotate_callback(self, rotate_controls):
        "Test _toggled_rotate_callback"
        # Initially disabled
        assert not rotate_controls._side2.get_sensitive()

        # Enable rotation
        rotate_controls._side1.cbutton.set_active(True)
        # Side 1 defaults to 'both', so side 2 should remain disabled
        # Note: SIDE = [["both", ...], ["facing", ...], ["reverse", ...]]
        # Default index is usually 0 ('both')
        rotate_controls._side1.side_cmbx.set_active(0)

        # Manually trigger callback if not triggered by set_active/set_active_index mock
        # But here we use real Gtk objects, so signals might fire if in main loop,
        # but unit tests often need manual triggering or ensuring main loop runs.
        # Let's call the handler directly to test logic.
        rotate_controls._toggled_rotate_callback(None)
        assert not rotate_controls._side2.get_sensitive()

        # Change to 'facing' (index 1)
        rotate_controls._side1.side_cmbx.set_active(1)
        rotate_controls._toggled_rotate_callback(None)
        assert rotate_controls._side2.get_sensitive()

        # Disable rotation again
        rotate_controls._side1.cbutton.set_active(False)
        rotate_controls._toggled_rotate_callback(None)
        assert not rotate_controls._side2.get_sensitive()

    def test_toggled_rotate_side_callback(self, rotate_controls):
        "Test _toggled_rotate_side_callback"
        # Enable rotation first
        rotate_controls._side1.cbutton.set_active(True)

        # Select 'both' (index 0)
        rotate_controls._side1.side_cmbx.set_active(0)
        rotate_controls._toggled_rotate_side_callback(rotate_controls._side1.side_cmbx)
        assert not rotate_controls._side2.get_sensitive()
        assert not rotate_controls._side2.cbutton.get_active()

        # Select 'facing' (index 1)
        rotate_controls._side1.side_cmbx.set_active(1)
        rotate_controls._toggled_rotate_side_callback(rotate_controls._side1.side_cmbx)
        assert rotate_controls._side2.get_sensitive()
        # Verify side2 combobox content logic (should exclude 'both' and 'facing')
        # It essentially sets it to remaining option, usually 'reverse'

        # Select 'reverse' (index 2)
        rotate_controls._side1.side_cmbx.set_active(2)
        rotate_controls._toggled_rotate_side_callback(rotate_controls._side1.side_cmbx)
        assert rotate_controls._side2.get_sensitive()

    def test_update_attributes(self, rotate_controls):
        "Test _update_attributes logic"
        rotate_controls._side1.cbutton.set_active(True)
        rotate_controls._side1.angle_cmbx.set_active_index(90)
        rotate_controls._side1.side_cmbx.set_active_index("facing")
        rotate_controls._update_attributes()
        assert rotate_controls._rotate_facing == 90
        assert rotate_controls._rotate_reverse == 0

        rotate_controls._side1.side_cmbx.set_active_index("reverse")
        rotate_controls._update_attributes()
        assert rotate_controls._rotate_facing == 0
        assert rotate_controls._rotate_reverse == 90

        rotate_controls._side1.side_cmbx.set_active_index("both")
        rotate_controls._update_attributes()
        assert rotate_controls._rotate_facing == 90
        assert rotate_controls._rotate_reverse == 90

        rotate_controls._side2.cbutton.set_active(True)
        rotate_controls._side2.angle_cmbx.set_active_index(180)
        rotate_controls._side2.side_cmbx.set_active_index("facing")
        rotate_controls._update_attributes()
        assert rotate_controls._rotate_facing == 180
        assert rotate_controls._rotate_reverse == 90

    def test_update_attributes_side2_reverse(self, rotate_controls):
        "Test more _update_attributes logic"
        rotate_controls._side1.cbutton.set_active(True)
        rotate_controls._side2.cbutton.set_active(True)
        rotate_controls._side1.angle_cmbx.set_active_index(90)
        rotate_controls._side2.angle_cmbx.set_active_index(180)
        rotate_controls._side2.side_cmbx.set_active_index("reverse")
        rotate_controls._update_attributes()
        assert rotate_controls._rotate_facing == 90
        assert rotate_controls._rotate_reverse == 180

    def test_update_gui(self, rotate_controls):
        "Test _update_gui logic"
        # Case 1: Both 90
        rotate_controls._rotate_facing = 90
        rotate_controls._rotate_reverse = 90
        rotate_controls._update_gui()

        assert rotate_controls._side1.cbutton.get_active()
        assert rotate_controls._side1.side_cmbx.get_active_index() == "both"
        assert rotate_controls._side1.angle_cmbx.get_active_index() == 90

        # Case 2: Facing 90, Reverse 0
        rotate_controls._rotate_facing = 90
        rotate_controls._rotate_reverse = 0
        rotate_controls._update_gui()

        assert rotate_controls._side1.side_cmbx.get_active_index() == "facing"
        assert not rotate_controls._side2.cbutton.get_active()

        # Case 3: Facing 90, Reverse 180
        rotate_controls._rotate_facing = 90
        rotate_controls._rotate_reverse = 180
        rotate_controls._update_gui()

        assert rotate_controls._side1.side_cmbx.get_active_index() == "facing"
        assert rotate_controls._side2.cbutton.get_active()
        assert rotate_controls._side2.side_cmbx.get_active_index() == "reverse"
        assert rotate_controls._side2.angle_cmbx.get_active_index() == 180

        # Case 4: Facing 0, Reverse 270
        rotate_controls._rotate_facing = 0
        rotate_controls._rotate_reverse = 270
        rotate_controls._update_gui()

        assert rotate_controls._side1.side_cmbx.get_active_index() == "reverse"
        assert rotate_controls._side1.angle_cmbx.get_active_index() == 270


class TestOCRControls:
    "Tests for OCRControls class"

    @pytest.fixture
    def mock_deps(self, mocker):
        "Mock external dependencies"
        mocker.patch(
            "postprocess_controls.get_tesseract_codes", return_value=["eng", "deu"]
        )
        mocker.patch(
            "postprocess_controls.languages",
            return_value={"eng": "English", "deu": "German"},
        )
        return mocker

    def test_init_no_engines(self, mock_deps):
        "Test initialization with no engines"
        controls = OCRControls(available_engines=[])
        assert not controls._active_button.get_active()
        assert not controls.get_children()[0].get_sensitive()

    def test_init_with_tesseract(self, mock_deps):
        "Test initialization with tesseract"
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])
        assert isinstance(controls, Gtk.Box)
        # Check if active button is present
        assert controls._active_button.get_label() == "OCR scanned pages"

    def test_properties(self, mock_deps):
        "Test properties"
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])

        # active
        controls.active = True
        assert controls._active_button.get_active()

        # threshold
        controls.threshold = True

        # threshold_value
        controls.threshold_value = 60
        assert controls.threshold_value == 60

        # engines + active
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]], active=True
        )
        assert controls._active_button.get_active()

    def test_callbacks(self, mock_deps):
        "Test callback methods"
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])

        # on_toggled_active
        mock_hbox = MagicMock()
        controls.on_toggled_active(MagicMock(get_active=lambda: True), mock_hbox)
        assert controls.active
        mock_hbox.set_sensitive.assert_called_with(True)

        # on_toggled_threshold
        mock_spin = MagicMock()
        controls.on_toggled_threshold(MagicMock(get_active=lambda: True), mock_spin)
        assert controls.threshold
        mock_spin.set_sensitive.assert_called_with(True)

        # on_threshold_changed
        controls.on_threshold_changed(None, 75)
        assert controls.threshold_value == 75

        # on_language_changed
        mock_combo = MagicMock()
        mock_combo.get_active_index.return_value = "deu"
        controls.on_language_changed(mock_combo)
        assert controls.language == "deu"

    def test_add_tess_languages(self, mock_deps):
        "Test _add_tess_languages"
        _controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])
        # It's called in init if tesseract is present.
        # We can check if the combobox contains expected data.
        # But `_add_tess_languages` returns an hbox which is local in init.
        # However, it connects `on_language_changed`.

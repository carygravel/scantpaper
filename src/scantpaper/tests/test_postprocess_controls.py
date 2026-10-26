"""Tests for postprocess_controls.py."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import gi
import pytest

from scantpaper.postprocess_controls import (
    OCRControls,
    RotateControlRow,
    RotateControls,
)
from scantpaper.session_mixins import SessionMixins

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

if TYPE_CHECKING:
    import pathlib


# Mock tesseract functions
def mock_get_tesseract_codes() -> list[str]:
    """Mock get_tesseract_codes."""
    return ["eng", "deu", "fra"]


def mock_languages(_codes: list[str]) -> dict[str, str]:
    """Mock languages."""
    return {"eng": "English", "deu": "German", "fra": "French"}


def mock_get_tesseract_variables() -> set[str]:
    """Mock get_tesseract_variables."""
    return {"user_words_file", "tessedit_char_whitelist"}


@pytest.fixture
def mock_ocr_setup(mocker: pytest.MockerFixture) -> None:
    """Fixture for ocr setup."""
    mocker.patch(
        "scantpaper.postprocess_controls.get_tesseract_codes",
        side_effect=mock_get_tesseract_codes,
    )
    mocker.patch(
        "scantpaper.postprocess_controls.languages", side_effect=mock_languages
    )
    mocker.patch(
        "scantpaper.postprocess_controls.get_tesseract_variables",
        side_effect=mock_get_tesseract_variables,
    )


@pytest.mark.usefixtures("mock_ocr_setup")
def test_ocr_controls_default_language() -> None:
    """Test that OCRControls defaults to the first language if none provided."""
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


def test_error_callback_crash(mocker: pytest.MockerFixture) -> None:
    """Test that _error_callback does not crash with int page."""

    # Mocking SessionMixins which contains _error_callback
    class MockApp(SessionMixins):
        """Mock App."""

        def __init__(self) -> None:
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

    app._error_callback(mock_response)  # Should not raise an exception


def test_rotate_control_row_init() -> None:
    """Test RotateControlRow initialization."""
    row = RotateControlRow()
    assert isinstance(row.cbutton, Gtk.CheckButton)
    assert isinstance(row.side_cmbx, Gtk.ComboBox)
    assert isinstance(row.angle_cmbx, Gtk.ComboBox)


class TestRotateControls:
    """Tests for RotateControls class."""

    @pytest.fixture
    def rotate_controls(self) -> RotateControls:
        """Fixture to create RotateControls instance."""
        return RotateControls()

    def test_init(self, rotate_controls: RotateControls) -> None:
        """Test initialization."""
        assert isinstance(rotate_controls, Gtk.Box)
        assert rotate_controls.get_orientation() == Gtk.Orientation.VERTICAL
        assert rotate_controls.rotate_facing == 0
        assert rotate_controls.rotate_reverse == 0
        assert rotate_controls.can_duplex is True

    def test_init_with_properties(self) -> None:
        """Test initialization with properties (prevents AttributeError regression)."""
        controls = RotateControls(
            rotate_facing=90, rotate_reverse=180, can_duplex=False
        )
        assert controls.rotate_facing == 90
        assert controls.rotate_reverse == 180
        assert controls.can_duplex is False
        assert not controls._side1.side_cmbx.get_visible()

    def test_init_preserves_loaded_rotation(self) -> None:
        """Loaded config values (e.g. 270) must not be clobbered by defaults."""
        controls = RotateControls(rotate_facing=270, rotate_reverse=270)
        assert controls.rotate_facing == 270
        assert controls.rotate_reverse == 270
        assert controls._side1.side_cmbx.get_active_index() == "both"
        assert controls._side1.angle_cmbx.get_active_index() == 270

    def test_rotate_facing_property(self, rotate_controls: RotateControls) -> None:
        """Test rotate_facing property."""
        rotate_controls.rotate_facing = 90
        assert rotate_controls.rotate_facing == 90

        # Set same value, should return early (coverage check)
        rotate_controls.rotate_facing = 90

    def test_rotate_reverse_property(self, rotate_controls: RotateControls) -> None:
        """Test rotate_reverse property."""
        rotate_controls.rotate_reverse = 180
        assert rotate_controls.rotate_reverse == 180

        # Set same value
        rotate_controls.rotate_reverse = 180

    def test_can_duplex_property(self, rotate_controls: RotateControls) -> None:
        """Test can_duplex property."""
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

    def test_toggled_rotate_callback(self, rotate_controls: RotateControls) -> None:
        """Test _toggled_rotate_callback."""
        # Initially disabled
        assert not rotate_controls._side2.get_sensitive()

        # Enable rotation
        rotate_controls._side1.cbutton.set_active(True)
        # Side 1 defaults to 'both', so side 2 should remain disabled
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

    def test_toggled_rotate_side_callback(
        self, rotate_controls: RotateControls
    ) -> None:
        """Test _toggled_rotate_side_callback."""
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

    def test_update_attributes(self, rotate_controls: RotateControls) -> None:
        """Test _update_attributes logic."""
        rotate_controls._side1.cbutton.set_active(True)
        rotate_controls._side1.angle_cmbx.set_active_index(90)
        rotate_controls._side1.side_cmbx.set_active_index("facing")
        assert rotate_controls.rotate_facing == 90
        assert rotate_controls.rotate_reverse == 0

        rotate_controls._side1.side_cmbx.set_active_index("reverse")
        assert rotate_controls.rotate_facing == 0
        assert rotate_controls.rotate_reverse == 90

        rotate_controls._side1.side_cmbx.set_active_index("both")
        assert rotate_controls.rotate_facing == 90
        assert rotate_controls.rotate_reverse == 90

        rotate_controls._side2.cbutton.set_active(True)
        rotate_controls._side2.angle_cmbx.set_active_index(180)
        rotate_controls._side2.side_cmbx.set_active_index("facing")
        assert rotate_controls.rotate_facing == 180
        assert rotate_controls.rotate_reverse == 90

    def test_update_attributes_side2_reverse(
        self, rotate_controls: RotateControls
    ) -> None:
        """Test more _update_attributes logic."""
        rotate_controls._side1.cbutton.set_active(True)
        rotate_controls._side2.cbutton.set_active(True)
        rotate_controls._side1.angle_cmbx.set_active_index(90)
        rotate_controls._side2.angle_cmbx.set_active_index(180)
        rotate_controls._side2.side_cmbx.set_active_index("reverse")
        rotate_controls._update_attributes(None)
        assert rotate_controls.rotate_facing == 90
        assert rotate_controls.rotate_reverse == 180

    def test_update_gui(self, rotate_controls: RotateControls) -> None:
        """Test _update_gui logic."""
        # Case 1: Both 90
        rotate_controls.rotate_facing = 90
        rotate_controls.rotate_reverse = 90
        assert rotate_controls._side1.cbutton.get_active()
        assert rotate_controls._side1.side_cmbx.get_active_index() == "both"
        assert rotate_controls._side1.angle_cmbx.get_active_index() == 90

        # Case 2: Facing 90, Reverse 0
        rotate_controls.rotate_facing = 90
        rotate_controls.rotate_reverse = 0
        assert rotate_controls._side1.side_cmbx.get_active_index() == "facing"
        assert not rotate_controls._side2.cbutton.get_active()

        # Case 3: Facing 90, Reverse 180
        rotate_controls.rotate_facing = 90
        rotate_controls.rotate_reverse = 180
        assert rotate_controls._side1.side_cmbx.get_active_index() == "facing"
        assert rotate_controls._side2.cbutton.get_active()
        assert rotate_controls._side2.side_cmbx.get_active_index() == "reverse"
        assert rotate_controls._side2.angle_cmbx.get_active_index() == 180

        # Case 4: Facing 0, Reverse 270
        rotate_controls.rotate_facing = 0
        rotate_controls.rotate_reverse = 270
        assert rotate_controls._side1.side_cmbx.get_active_index() == "reverse"
        assert rotate_controls._side1.angle_cmbx.get_active_index() == 270


class TestOCRControls:
    """Tests for OCRControls class."""

    def test_init_no_engines(self) -> None:
        """Test initialization with no engines."""
        controls = OCRControls(available_engines=[])
        assert not controls._active_button.get_active()
        assert not next(iter(controls.observe_children())).get_sensitive()

    def test_init_without_tesseract(self) -> None:
        """Test initialization with a non-tesseract engine only."""
        controls = OCRControls(
            available_engines=[["gocr", "GOCR", "desc"]], variables="a=b"
        )
        # The advanced options field is only built for tesseract, so the
        # raw variables value is read and written without a widget.
        assert controls.variables == "a=b"
        controls.variables = "c=d"
        assert controls.variables == "c=d"
        assert not hasattr(controls, "_variables_view")
        # Likewise the mode selectors are not built, so their raw values are
        # read and written without a widget.
        assert controls.psm == ""
        assert controls.engine_mode == "default"
        controls.psm = "7"
        controls.engine_mode = "lstm"
        assert controls.psm == "7"
        assert controls.engine_mode == "lstm"

    def test_init_with_tesseract(self) -> None:
        """Test initialization with tesseract."""
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])
        assert isinstance(controls, Gtk.Box)
        # Check if active button is present
        assert controls._active_button.get_label() == "OCR scanned pages"

    def test_properties(self) -> None:
        """Test properties."""
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])

        # active
        controls.active = True
        assert controls._active_button.get_active()

        # threshold
        controls.threshold = True

        # threshold_value
        controls.threshold_value = 60
        assert controls.threshold_value == 60

        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])
        assert controls.threshold_value == 20.0

        # engines + active
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]], active=True
        )
        assert controls._active_button.get_active()

    def test_callbacks(self) -> None:
        """Test callback methods."""
        controls = OCRControls(available_engines=[["tesseract", "Tesseract", "Desc"]])

        # on_toggled_active
        mock_hbox = MagicMock()
        controls.on_toggled_active(MagicMock(get_active=lambda: True), mock_hbox)
        assert controls.active
        mock_hbox.set_sensitive.assert_called_with(sensitive=True)

        # on_toggled_threshold
        mock_spin = MagicMock()
        controls.on_toggled_threshold(MagicMock(get_active=lambda: True), mock_spin)
        assert controls.threshold
        mock_spin.set_sensitive.assert_called_with(sensitive=True)

        # on_threshold_changed
        controls.on_threshold_changed(None, 75)
        assert controls.threshold_value == 75

        # on_language_changed
        mock_combo = MagicMock()
        mock_combo.get_active_index.return_value = "deu"
        controls.on_language_changed(mock_combo)
        assert controls.language == "deu"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_multiple_languages(self) -> None:
        """Test adding and removing additional languages."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng",
            active=True,
        )
        assert controls.language == "deu+eng"
        assert controls._additional_checks["eng"].get_active()

        controls._additional_checks["fra"].set_active(True)
        assert controls.language == "deu+eng+fra"

        controls._additional_checks["eng"].set_active(False)
        assert controls.language == "deu+fra"

        controls._additional_checks["fra"].set_active(False)
        assert controls.language == "deu"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_additional_language_order(self) -> None:
        """Test that additional languages keep the selection order."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu",
            active=True,
        )
        controls._additional_checks["fra"].set_active(True)
        controls._additional_checks["eng"].set_active(True)
        assert controls.language == "deu+fra+eng"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_primary_change_removes_additional(self) -> None:
        """Test changing the primary language."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng+fra",
            active=True,
        )
        controls._primary_cmbx.set_active_index("eng")
        assert controls.language == "eng+fra"
        assert not controls._additional_checks["deu"].get_active()

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_primary_not_offered_as_additional(self) -> None:
        """Test that the primary language is not in the additional list."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng",
            active=True,
        )
        assert "deu" not in controls._additional_checks
        assert "eng" in controls._additional_checks
        controls._additional_checks["eng"].set_active(True)
        assert controls.language == "deu+eng"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_language_setter_reloads_ui(self) -> None:
        """Test that assigning language after construction reloads the combo."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        controls.language = "deu"
        assert controls._primary_cmbx.get_active_index() == "deu"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_primary_change_to_non_additional(self) -> None:
        """Test changing the primary to a language not in the additional list."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng",
            active=True,
        )
        controls._primary_cmbx.set_active_index("fra")
        assert controls.language == "fra+eng"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_missing_additional_language(self) -> None:
        """Test that a stored additional language no longer installed is kept."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng+zzz",
            active=True,
        )
        assert "zzz" in controls._additional_checks
        assert "not installed" in controls._additional_checks["zzz"].get_label()
        assert controls.language == "eng+zzz"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_additional_toggled_edges(self) -> None:
        """Test the additional-language toggle edge branches."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        # Toggling the primary on does not add it as additional.
        controls._on_additional_language_toggled(
            MagicMock(get_active=lambda: True), "eng"
        )
        assert controls.language == "eng"
        # Untoggling a code that is not in the additional list is a no-op.
        controls._on_additional_language_toggled(
            MagicMock(get_active=lambda: False), "fra"
        )
        assert controls.language == "eng"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_additional_toggled_while_syncing(self) -> None:
        """Test that toggles are ignored while the UI is being rebuilt."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        controls._syncing = True
        controls._on_additional_language_toggled(
            MagicMock(get_active=lambda: True), "fra"
        )
        assert controls.language == "eng"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_missing_language(self, mocker: pytest.MockerFixture) -> None:
        """Test that a stored language that is no longer installed is kept."""
        mocker.patch(
            "scantpaper.postprocess_controls.get_tesseract_codes",
            return_value=["eng"],
        )
        mocker.patch(
            "scantpaper.postprocess_controls.languages",
            return_value={"eng": "English"},
        )
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng",
            active=True,
        )
        assert controls.language == "deu+eng"
        assert controls._primary_cmbx.get_active_index() == "deu"
        assert "not installed" in controls._primary_cmbx.get_active_text()
        assert controls._additional_checks["eng"].get_active()
        error = controls.validation_error
        assert error is not None
        assert "deu" in error

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_variables(self) -> None:
        """Test the advanced options field and its sensitivity."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            variables="user_words_file=/tmp/words.txt",
            active=False,
        )
        assert controls.variables == "user_words_file=/tmp/words.txt"
        assert not controls._options_box.get_sensitive()

        controls.active = True
        assert controls._options_box.get_sensitive()

        controls.variables = "tessedit_char_whitelist=0123"
        buffer = controls._variables_view.get_buffer()
        text = buffer.get_text(
            buffer.get_start_iter(), buffer.get_end_iter(), include_hidden_chars=True
        )
        assert text == "tessedit_char_whitelist=0123"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_advanced_options_wording(self) -> None:
        """Test the field describes engine parameters, not command-line options."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        assert "engine parameters" in controls._advanced_expander.get_label()
        hint = controls._advanced_hint.get_label()
        assert "name=value" in hint
        assert "--user-words" in hint

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_page_segmentation_mode(self) -> None:
        """Test the page segmentation mode combo and its fallback."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        assert controls.psm == ""

        controls._psm_cmbx.set_active_index("7")
        assert controls.psm == "7"

        controls.psm = 999
        assert controls.psm == ""

        stored = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            psm="6",
            active=True,
        )
        assert stored.psm == "6"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_engine_mode(self) -> None:
        """Test the OCR engine mode combo, selection and reload."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        assert controls.engine_mode == "default"

        controls._engine_mode_cmbx.set_active_index("lstm")
        assert controls.engine_mode == "lstm"

        reloaded = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            engine_mode=controls.engine_mode,
            active=True,
        )
        assert reloaded.engine_mode == "lstm"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_unknown_engine_mode_falls_back(self) -> None:
        """Test an unrecognised stored engine mode falls back to the default."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            engine_mode="bogus",
            active=True,
        )
        assert controls.engine_mode == "default"

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_validation_error(
        self, mocker: pytest.MockerFixture, tmp_path: pathlib.Path
    ) -> None:
        """Test OCR option validation."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )
        assert controls.validation_error is None

        words = tmp_path / "words.txt"
        words.write_text("fox\n")
        controls.variables = f"user_words_file={words}"
        assert controls.validation_error is None

        controls.variables = "user_words_file=/nonexistent/words.txt"
        error = controls.validation_error
        assert error is not None
        assert "user_words_file" in error
        assert "/nonexistent/words.txt" in error

        controls.variables = "--user-words /tmp/words.txt"
        error = controls.validation_error
        assert error is not None
        assert "--user-words" in error
        assert "user_words_file" in error

        controls.variables = "--psm 6"
        error = controls.validation_error
        assert error is not None
        assert "command-line" in error

        controls.variables = "bad"
        error = controls.validation_error
        assert error is not None
        assert "line 1" in error

        controls.variables = "unknown_variable=x"
        error = controls.validation_error
        assert error is not None
        assert "unknown_variable" in error

        controls.variables = "unknown_variable=x\nother_unknown=y"
        error = controls.validation_error
        assert error is not None
        assert "unknown_variable" in error
        assert "other_unknown" in error

        mocker.patch(
            "scantpaper.postprocess_controls.get_tesseract_codes",
            return_value=["eng"],
        )
        mocker.patch(
            "scantpaper.postprocess_controls.languages",
            return_value={"eng": "English"},
        )
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="deu+eng",
            active=True,
        )
        error = controls.validation_error
        assert error is not None
        assert "deu" in error

        mocker.patch(
            "scantpaper.postprocess_controls.get_tesseract_codes",
            return_value=[],
        )
        mocker.patch(
            "scantpaper.postprocess_controls.languages",
            return_value={},
        )
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language=None,
            active=True,
        )
        assert controls.language is None
        error = controls.validation_error
        assert error is not None
        assert "No OCR language selected" in error

    @pytest.mark.usefixtures("mock_ocr_setup")
    def test_validation_error_managed_variables(self) -> None:
        """The variables owned by a dedicated control are rejected."""
        controls = OCRControls(
            available_engines=[["tesseract", "Tesseract", "Desc"]],
            language="eng",
            active=True,
        )

        controls.variables = "tessedit_pageseg_mode=6"
        error = controls.validation_error
        assert error is not None
        assert "tessedit_pageseg_mode" in error
        assert "Page segmentation mode" in error

        controls.variables = "tessedit_ocr_engine_mode=1"
        error = controls.validation_error
        assert error is not None
        assert "tessedit_ocr_engine_mode" in error
        assert "OCR engine mode" in error


@pytest.mark.usefixtures("mock_ocr_setup")
def test_engine_property() -> None:
    """Test engine property."""
    controls = OCRControls(
        available_engines=[["tesseract", "Tesseract", "Desc"]], engine="tesseract"
    )
    assert controls.get_property("engine") == "tesseract"

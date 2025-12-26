"Tests for postprocess controls fixes."

import pytest
from postprocess_controls import OCRControls
from session_mixins import SessionMixins


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


def test_ocr_controls_default_language(
    mock_ocr_setup,
):  # pylint: disable=unused-argument
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

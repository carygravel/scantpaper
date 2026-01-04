"Coverage tests for dialog.save"

# pylint: disable=protected-access, redefined-outer-name, unused-argument, no-member

import datetime as dt
from unittest.mock import MagicMock
import pytest
import gi
from dialog.save import Save, filter_table

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_save_dialog(mocker):
    "Fixture to provide a Save dialog with mocked dependencies"
    mocker.patch("dialog.save.Dialog.__init__", return_value=None)
    mocker.patch("dialog.save.Dialog.get_content_area", return_value=Gtk.Box())
    mocker.patch("dialog.save.Dialog.get_style_context", return_value=MagicMock())

    # Mocking filter_table to avoid issues with missing dependencies in tests
    mocker.patch(
        "dialog.save.filter_table",
        side_effect=lambda t, types: [row for row in t if row[0] in types],
    )

    dialog = Save(
        title="test save",
        image_types=["pdf", "jpg", "tif", "ps", "djvu"],
        ps_backends=["pdftops", "pdf2ps"],
    )
    # Manually initialize some widgets that might be skipped by mocked __init__
    dialog.meta_now_widget = MagicMock(spec=Gtk.RadioButton)
    dialog.meta_now_widget.get_active.return_value = False
    dialog._meta_datetime_widget = Gtk.Entry()

    return dialog


def test_filter_table():
    "Test filter_table function"
    table = [("a", 1), ("b", 2), ("c", 3)]
    types = ["a", "c"]
    assert filter_table(table, types) == [("a", 1), ("c", 3)]


def test_metadata_properties(mocker):
    "Test metadata properties and suggestions"
    dialog = Save(meta_title="initial title")

    # Title
    assert dialog.meta_title == "initial title"
    dialog.meta_title = "new title"
    assert dialog.meta_title == "new title"

    # Suggestions
    dialog.meta_title_suggestions = ["s1", "s2"]
    assert "s1" in dialog.meta_title_suggestions

    # Author
    dialog.meta_author = "author"
    assert dialog.meta_author == "author"
    dialog.meta_author_suggestions = ["a1"]
    assert "a1" in dialog.meta_author_suggestions

    # Subject
    dialog.meta_subject = "subject"
    assert dialog.meta_subject == "subject"
    dialog.meta_subject_suggestions = ["sub1"]
    assert "sub1" in dialog.meta_subject_suggestions

    # Keywords
    dialog.meta_keywords = "k1, k2"
    assert dialog.meta_keywords == "k1, k2"
    dialog.meta_keywords_suggestions = ["kw1"]
    assert "kw1" in dialog.meta_keywords_suggestions


def test_include_time_toggle(mocker):
    "Test include_time property"
    dialog = Save()
    dialog.include_time = True
    assert dialog.include_time is True
    # Verify it updates widgets
    assert dialog.meta_now_widget.get_child().get_text() == "Now"

    dialog.include_time = False
    assert dialog.include_time is False
    assert dialog.meta_now_widget.get_child().get_text() == "Today"


def test_meta_datetime_property(mocker):
    "Test meta_datetime property logic"
    mock_now = dt.datetime(2023, 1, 1, 12, 0, 0)

    # Patch datetime.datetime in dialog.save
    mock_datetime_cls = mocker.patch("dialog.save.datetime.datetime")
    mock_datetime_cls.now.return_value = mock_now
    mock_datetime_cls.fromisoformat.side_effect = dt.datetime.fromisoformat

    dialog = Save()

    # Test 'Now' active
    dialog.meta_now_widget.set_active(True)
    assert dialog.meta_now_widget.get_active() is True
    assert dialog.meta_datetime == mock_now

    # Test 'Now' inactive
    dialog._meta_specify_widget.set_active(True)
    assert dialog.meta_now_widget.get_active() is False
    test_date = dt.datetime(2022, 1, 1)
    dialog.meta_datetime = test_date
    assert dialog.meta_datetime == test_date


def test_insert_text_handler_inc_dec(mocker):
    "Test increment/decrement date via + and - keys"
    dialog = Save()
    dialog._meta_specify_widget.set_active(True)
    entry = dialog._meta_datetime_widget
    entry.set_text("2023-01-01")

    # Increment
    dialog._insert_text_handler(entry, "+", 1, 10)
    assert entry.get_text() == "2023-01-02"

    # Decrement
    dialog._insert_text_handler(entry, "-", 1, 10)
    assert entry.get_text() == "2023-01-01"


def test_insert_text_handler_filtering(mocker):
    "Test character filtering in _insert_text_handler"
    dialog = Save()
    entry = dialog._meta_datetime_widget

    # Allow numbers and dashes for date
    dialog.include_time = False
    entry.set_text("")
    dialog._insert_text_handler(entry, "2023-01-01", 10, 0)
    assert entry.get_text() == "2023-01-01"

    # Block letters
    entry.set_text("")
    dialog._insert_text_handler(entry, "abc", 3, 0)
    assert entry.get_text() == ""


def test_add_image_type(mocker):
    "Test add_image_type and UI setup"
    # Mock filter_table which is imported into save
    mocker.patch("dialog.save.filter_table", side_effect=lambda x, y: x)

    dialog = Save(image_types=["pdf", "tif", "jpg"], ps_backends=["pdftops"])
    dialog.add_image_type()


def test_image_type_changed_callback(mocker):
    "Test image type changed logic"
    mocker.patch("dialog.save.filter_table", side_effect=lambda x, y: x)
    dialog = Save(
        image_types=["pdf", "tif", "jpg", "ps", "djvu"], ps_backends=["pdftops"]
    )
    dialog.add_image_type()

    mock_combo = MagicMock()
    data = [MagicMock() for _ in range(5)]  # vboxp, hboxpq, hboxc, hboxtq, hboxps

    # Change to TIFF
    mock_combo.get_active_index.return_value = "tif"
    dialog._image_type_changed_callback(mock_combo, data)
    assert dialog.image_type == "tif"

    # Change to JPEG
    mock_combo.get_active_index.return_value = "jpg"
    dialog._image_type_changed_callback(mock_combo, data)
    assert dialog.image_type == "jpg"

    # Change to PS
    mock_combo.get_active_index.return_value = "ps"
    dialog._image_type_changed_callback(mock_combo, data)
    assert dialog.image_type == "ps"


def test_pdf_compression_changed_callback(mocker):
    "Test PDF compression changed callback"
    dialog = Save()
    mock_hboxq = MagicMock()
    mock_combo = MagicMock()

    # Set to JPEG (should show quality)
    mock_combo.get_active_index.return_value = "jpg"
    dialog._pdf_compression_changed_callback(mock_combo, mock_hboxq)
    mock_hboxq.show.assert_called()

    # Set to LZW (should hide quality)
    mock_combo.get_active_index.return_value = "lzw"
    dialog._pdf_compression_changed_callback(mock_combo, mock_hboxq)
    mock_hboxq.hide.assert_called()


def test_encrypt_clicked_callback(mocker):
    "Test encryption dialog creation"
    dialog = Save()
    dialog.can_encrypt_pdf = True
    # Mock Dialog to prevent window popping up
    mock_dialog_cls = mocker.patch("dialog.save.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.get_content_area.return_value = Gtk.Box()

    dialog._encrypt_clicked_callback(None)
    mock_dialog_cls.assert_called()


def test_update_config_dict(mocker):
    "Test update_config_dict"
    dialog = Save()
    dialog._meta_specify_widget.set_active(True)
    dialog.meta_author = "author"
    dialog.meta_title = "title"
    dialog.meta_datetime = dt.datetime(2023, 1, 1)

    config = {}
    dialog.update_config_dict(config)
    assert config["author"] == "author"
    assert config["title"] == "title"
    assert "datetime offset" in config


def test_datetime_focus_out_callback(mocker):
    "Test _datetime_focus_out_callback"
    dialog = Save()
    dialog._meta_specify_widget.set_active(True)
    mock_entry = MagicMock()
    mock_entry.get_text.return_value = "2023-01-01"

    dialog._datetime_focus_out_callback(mock_entry, None)
    assert dialog.meta_datetime == dt.datetime(2023, 1, 1)


def test_clicked_specify_date_button(mocker):
    "Test _clicked_specify_date_button"
    dialog = Save()
    mock_hboxe = MagicMock()
    mock_widget = MagicMock()

    # Active
    mock_widget.get_active.return_value = True
    dialog._clicked_specify_date_button(mock_widget, mock_hboxe)
    mock_hboxe.show.assert_called()
    assert dialog.select_datetime is True

    # Inactive
    mock_widget.get_active.return_value = False
    dialog._clicked_specify_date_button(mock_widget, mock_hboxe)
    mock_hboxe.hide.assert_called()
    assert dialog.select_datetime is False

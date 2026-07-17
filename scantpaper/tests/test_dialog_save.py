"Coverage tests for dialog.save"

import datetime as dt
from unittest.mock import MagicMock

import gi
from dialog.save import Save, filter_table

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_filter_table():
    "Test filter_table function"
    table = [("a", 1), ("b", 2), ("c", 3)]
    types = ["a", "c"]
    assert filter_table(table, types) == [("a", 1), ("c", 3)]


def test_metadata_properties():
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


def test_include_time_toggle():
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
    # Capture the real class and its fromisoformat before patching
    real_datetime = dt.datetime
    real_fromisoformat = dt.datetime.fromisoformat

    # Patch datetime.datetime in dialog.save
    mock_datetime_cls = mocker.patch("dialog.save.datetime.datetime")
    mock_datetime_cls.now.return_value = mock_now
    mock_datetime_cls.fromisoformat.side_effect = real_fromisoformat

    dialog = Save()

    # Test 'Now' active
    dialog.meta_now_widget.set_active(True)
    assert dialog.meta_now_widget.get_active() is True
    assert dialog.meta_datetime == mock_now

    # Test 'Now' inactive
    dialog._meta_specify_widget.set_active(True)
    assert dialog.meta_now_widget.get_active() is False
    test_date = real_datetime(2022, 1, 1)
    dialog.meta_datetime = test_date
    assert dialog.meta_datetime == test_date


def test_insert_text_handler_inc_dec(mocker):
    "Test increment/decrement date via + and - keys"
    mocker.patch("dialog.save.GLib.idle_add", side_effect=lambda f, *a: f(*a))
    dialog = Save()
    dialog.show_all()
    dialog._meta_specify_widget.set_active(True)
    entry = dialog._meta_datetime_widget
    entry.get_buffer().set_text("2023-01-01", -1)
    entry.stop_emission_by_name = mocker.Mock()

    # Increment
    dialog._insert_text_handler(entry, "+", 1, 10)
    assert entry.get_text() == "2023-01-02"

    # Decrement
    dialog._insert_text_handler(entry, "-", 1, 10)
    assert entry.get_text() == "2023-01-01"


def test_insert_text_handler_filtering(mocker):
    "Test character filtering in _insert_text_handler"
    mocker.patch("dialog.save.GLib.idle_add", side_effect=lambda f, *a: f(*a))
    dialog = Save()
    dialog.show_all()
    entry = dialog._meta_datetime_widget
    entry.stop_emission_by_name = mocker.Mock()

    # Allow numbers and dashes for date
    dialog.include_time = False
    entry.get_buffer().set_text("", -1)
    dialog._insert_text_handler(entry, "2023-01-01", 10, 0)
    assert entry.get_text() == "2023-01-01"

    # Block letters
    entry.get_buffer().set_text("", -1)
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


def test_pdf_compression_changed_callback():
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
    "Test encryption dialog creation and callbacks"
    dialog = Save()
    dialog.can_encrypt_pdf = True
    dialog.pdf_user_password = "pre_existing_password"
    # Mock Dialog to prevent window popping up
    mock_dialog_cls = mocker.patch("dialog.save.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_box = Gtk.Box()
    mock_dialog.get_content_area.return_value = mock_box

    # Capture actions added to the dialog
    actions = []

    def mock_add_actions(act_list):
        nonlocal actions
        actions = act_list

    mock_dialog.add_actions.side_effect = mock_add_actions

    # Trigger callback
    dialog._encrypt_clicked_callback(None)
    mock_dialog_cls.assert_called()

    # Find OK and Cancel callbacks
    ok_cb = None
    cancel_cb = None
    for name, cb in actions:
        if name == "gtk-ok":
            ok_cb = cb
        elif name == "gtk-cancel":
            cancel_cb = cb

    assert ok_cb is not None
    assert cancel_cb is not None

    # Test OK callback (covers line 762)
    # Find the userentry in the box to set its value
    # In _encrypt_clicked_callback: passvbox.pack_start(grid, ...)
    # grid has userentry at (1, 0)
    grid = None
    for child in mock_box.get_children():
        if isinstance(child, Gtk.Grid):
            grid = child
            break
    assert grid is not None

    userentry = grid.get_child_at(1, 0)
    assert isinstance(userentry, Gtk.Entry)
    userentry.set_text("secret_password")

    ok_cb()
    assert dialog.pdf_user_password == "secret_password"
    mock_dialog.destroy.assert_called()

    # Test Cancel callback (covers line 772)
    mock_dialog.destroy.reset_mock()
    cancel_cb()
    mock_dialog.destroy.assert_called()


def test_update_config_dict():
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


def test_datetime_focus_out_callback():
    "Test _datetime_focus_out_callback"
    dialog = Save()
    dialog._meta_specify_widget.set_active(True)
    mock_entry = MagicMock()
    mock_entry.get_text.return_value = "2023-01-01"

    dialog._datetime_focus_out_callback(mock_entry, None)
    assert dialog.meta_datetime == dt.datetime(2023, 1, 1)


def test_clicked_specify_date_button():
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


def test_pdf_selected_callback(mocker):
    "Test _pdf_selected_callback"
    dialog = Save()
    dialog.image_type = "appendpdf"
    dialog.pdf_compression = "jpg"
    dialog._meta_box_widget = MagicMock()
    args = [
        mocker.Mock(spec=Gtk.Box),
        mocker.Mock(spec=Gtk.Box),
        mocker.Mock(spec=Gtk.Box),
        mocker.Mock(spec=Gtk.Box),
        mocker.Mock(spec=Gtk.Box),
    ]
    dialog._pdf_selected_callback(args)
    dialog._meta_box_widget.hide.assert_called()
    args[1].show.assert_called()  # hboxpq


def test_meta_datetime_reads_from_widget_immediately():
    """
    Regression test for issue #68:

    1. Open the Save Dialog: Go to File -> Save (or use the Save icon).
    2. Enable Date Specification: In the "Date/Time" section of the Save
       dialog, select the "Specify" radio button.
    3. Edit the Date: Click into the date entry field (e.g., 2026-05-09) and
       type a different date (e.g., 2026-01-01).
    4. The "Trap": Immediately after typing the last digit of the new date, do
       NOT press Tab and do NOT click into another text field. Keep the text
       cursor (focus) inside the date entry box.
    5. Click Save: Click the "Save" button at the bottom of the dialog.
    6. Verify the Result:
        Check the filename (if your default filename pattern uses the date). It
        will likely still use the old date.
        Check the modified date of the resulting file on your disk. It will
        show the date that was there before you started typing, not the one you
        just entered.

    Test that meta_datetime property reads directly from the Gtk.Entry widget.
    This ensures that even if a 'focus-out-event' hasn't fired (e.g. user clicks
    'Save' immediately after typing), the updated date is still captured.
    """
    # Initialize dialog with an arbitrary date
    initial_date = dt.datetime(2026, 5, 8, 10, 0, 0)
    dialog = Save(
        image_types=["pdf"],
        image_type="pdf",
        meta_datetime=initial_date,
        select_datetime=True,
    )

    dialog.show_all()
    # Ensure "Specify" is active so it doesn't just return 'now'
    dialog._meta_specify_widget.set_active(True)

    # Simulate the user typing a new date into the entry widget
    dialog._meta_datetime_widget.get_buffer().set_text("2026-01-01", -1)

    # ASSERTION: The property getter should return the NEW date parsed from the widget,
    # even though we haven't triggered a focus-out signal or updated the property setter.
    # BEFORE FIX: This would return 2026-05-08
    # AFTER FIX: This returns 2026-01-01
    assert dialog.meta_datetime.date() == dt.date(2026, 1, 1)


def test_meta_datetime_preserves_time_when_not_included():
    """
    Test that if include_time is False, we still preserve the original time
    if the date part hasn't changed in the widget.
    """
    initial_datetime = dt.datetime(2026, 5, 8, 12, 34, 56)
    dialog = Save(
        image_types=["pdf"],
        image_type="pdf",
        meta_datetime=initial_datetime,
        select_datetime=True,
        include_time=False,
    )
    dialog.show_all()
    dialog._meta_specify_widget.set_active(True)

    # Widget text will be "2026-05-08" (time truncated in UI)
    assert dialog._meta_datetime_widget.get_text() == "2026-05-08"

    # Property should still return the full datetime because the date hasn't changed
    assert dialog.meta_datetime == initial_datetime
    assert dialog.meta_datetime.hour == 12


def test_meta_datetime_preserves_datetime_when_not_changed():
    """
    Test that if include_time is True, we return the original datetime
    if the widget text hasn't changed.
    """
    initial_datetime = dt.datetime(2026, 5, 8, 12, 34, 56)
    dialog = Save(
        image_types=["pdf"],
        image_type="pdf",
        meta_datetime=initial_datetime,
        select_datetime=True,
        include_time=True,
    )
    dialog.show_all()
    dialog._meta_specify_widget.set_active(True)

    # Widget text will be "2026-05-08 12:34:56"
    assert dialog._meta_datetime_widget.get_text() == "2026-05-08 12:34:56"

    # Property should return the original object (covers line 111)
    assert dialog.meta_datetime is initial_datetime


def test_meta_datetime_returns_date_when_initial_was_date():
    """
    Test that if the initial _meta_datetime was a date object,
    it returns a date object (covers lines 115-116).
    """
    initial_date = dt.date(2026, 5, 8)
    dialog = Save(
        image_types=["pdf"],
        image_type="pdf",
        meta_datetime=initial_date,
        select_datetime=True,
        include_time=False,
    )
    dialog.show_all()
    dialog._meta_specify_widget.set_active(True)

    # Change the date in the widget
    dialog._meta_datetime_widget.get_buffer().set_text("2026-01-01", -1)

    # Should return a date object
    res = dialog.meta_datetime
    assert isinstance(res, dt.date)
    assert not isinstance(res, dt.datetime)
    assert res == dt.date(2026, 1, 1)


def test_meta_datetime_when_initial_is_none():
    """
    Test meta_datetime property when initial value is None (covers line 117).
    """
    dialog = Save(
        image_types=["pdf"],
        image_type="pdf",
        meta_datetime=None,
        select_datetime=True,
        include_time=True,
    )
    dialog.show_all()
    dialog._meta_specify_widget.set_active(True)
    dialog._meta_datetime_widget.get_buffer().set_text("2026-05-08 12:34:56", -1)

    assert dialog.meta_datetime == dt.datetime(2026, 5, 8, 12, 34, 56)

    dialog.include_time = False
    assert dialog.meta_datetime == dt.date(2026, 5, 8)

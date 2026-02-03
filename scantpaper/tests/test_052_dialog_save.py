"test dialog.save"

from datetime import date, datetime, timedelta
from dialog import Dialog
from dialog.save import Save
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class MockedDateTime(datetime):
    "mock now"

    @classmethod
    def now(cls):  # pylint: disable=arguments-differ
        return datetime(2018, 1, 1, 0, 0, 0)


def test_basic(mocker):
    "basic tests"
    mocker.patch("dialog.save.datetime.datetime", MockedDateTime)
    dialog = Save(
        title="title",
        transient_for=Gtk.Window(),
        meta_datetime=date(2017, 1, 1),
        select_datetime=True,
        meta_title="title",
        meta_title_suggestions=["title-suggestion"],
        meta_author="author",
        meta_author_suggestions=["author-suggestion"],
        meta_subject="subject",
        meta_subject_suggestions=["subject-suggestion"],
        meta_keywords="keywords",
        meta_keywords_suggestions=["keyword-suggestion"],
    )
    assert isinstance(dialog, Save)

    assert dialog.meta_datetime == date(  # pylint: disable=comparison-with-callable
        2017, 1, 1
    ), "date"
    assert dialog.meta_author == "author", "author"
    assert dialog.meta_title == "title", "title"
    assert dialog.meta_subject == "subject", "subject"
    assert dialog.meta_keywords == "keywords", "keywords"

    dialog._meta_author_widget.set_text("author2")
    assert dialog.meta_author == "author2", "author from Entry()"

    config = {
        "author": "old author",
        "title": "old title",
        "subject": "old subject",
        "keywords": "old keywords",
        "datetime offset": timedelta(seconds=0),
        "other key": "other key",
    }
    dialog.update_config_dict(config)
    assert config == {
        "author": "author2",
        "author-suggestions": [
            "author-suggestion",
        ],
        "title": "title",
        "title-suggestions": [
            "title-suggestion",
        ],
        "subject": "subject",
        "subject-suggestions": [
            "subject-suggestion",
        ],
        "keywords": "keywords",
        "keywords-suggestions": [
            "keyword-suggestion",
        ],
        "datetime offset": timedelta(days=-365, hours=0, minutes=0, seconds=0),
        "other key": "other key",
    }, "updated config"

    metadata = {
        "author": "old author",
        "title": "old title",
        "subject": "old subject",
        "keywords": "old keywords",
        "datetime": datetime(2017, 1, 1, 23, 59, 5),
        "other key": "other key",
    }
    dialog.update_from_import_metadata(metadata)
    assert dialog.meta_datetime == datetime(2017, 1, 1, 23, 59, 5), "date"
    assert dialog.meta_author == "old author", "author"
    assert dialog.meta_title == "old title", "title"
    assert dialog.meta_subject == "old subject", "subject"
    assert dialog.meta_keywords == "old keywords", "keywords"


def test_datetime():
    "test datetime"
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
        select_datetime=True,
    )
    assert dialog.meta_datetime == datetime(  # pylint: disable=comparison-with-callable
        2017, 1, 1, 23, 59, 5
    ), "date and time"


def test_now(mocker):
    "test not setting datetime"
    now = datetime(2018, 1, 1, 0, 0, 0)
    mocker.patch("dialog.save.datetime.datetime", MockedDateTime)
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
    )
    assert (
        dialog.meta_datetime == now  # pylint: disable=comparison-with-callable
    ), "now"


def test_image_type_selection(mocker):
    "test image type selection updates UI"
    dialog = Save(
        transient_for=Gtk.Window(),
        image_types=["djvu", "tif", "ps", "pdf"],
        ps_backends=["pdf2ps", "pdftops"],
    )
    # Mock resize to avoid X11 errors or unnecessary logic
    dialog.resize = mocker.Mock()

    dialog.add_image_type()

    def find_combobox(container):
        "Find the image type combobox by searching children"
        for child in container.get_children():
            if not isinstance(child, Gtk.Box) or child == dialog._meta_box_widget:
                continue
            grand_children = child.get_children()
            has_label = any(
                isinstance(gc, Gtk.Label) and gc.get_text() == "Document type"
                for gc in grand_children
            )
            if has_label:
                for gc in grand_children:
                    if isinstance(gc, Gtk.ComboBox):
                        return gc
        return None

    combobi = find_combobox(dialog.get_content_area())
    assert combobi is not None, "Could not find Image Type ComboBox"

    # Test setting to 'djvu'
    combobi.set_active_index("djvu")
    assert dialog.image_type == "djvu"
    assert dialog._meta_box_widget.get_visible()

    # Test setting to 'tif'
    combobi.set_active_index("tif")
    assert dialog.image_type == "tif"
    assert not dialog._meta_box_widget.get_visible()

    # Test setting to 'ps'
    combobi.set_active_index("ps")
    assert dialog.image_type == "ps"

    # Test setting to 'pdf'
    combobi.set_active_index("pdf")
    assert dialog.image_type == "pdf"
    assert dialog._meta_box_widget.get_visible()


def test_pdf_options(mocker):
    "test PDF specific options"
    dialog = Save(
        transient_for=Gtk.Window(),
        can_encrypt_pdf=True,
        image_types=["pdf"],
        ps_backends=["pdf2ps"],
    )
    dialog.resize = mocker.Mock()
    dialog.add_image_type()
    mock_dialog_cls = mocker.patch("dialog.save.Dialog")
    mock_instance = mock_dialog_cls.return_value

    # Mock get_content_area to return a Box (so pack_start works)
    mock_content_area = mocker.Mock(spec=Gtk.Box)
    mock_instance.get_content_area.return_value = mock_content_area

    # Simulate clicking encrypt
    dialog._encrypt_clicked_callback(None)

    # Capture the actions passed to add_actions
    # passwin.add_actions([("gtk-ok", clicked_ok_callback), ...])
    args, _ = mock_instance.add_actions.call_args
    actions = args[0]
    ok_callback = next(cb for name, cb in actions if name == "gtk-ok")

    # Now we need to set the text in the userentry.
    # But we don't have reference to userentry. It was created locally.
    # However, it was attached to the grid.
    # The grid was added to passvbox (the mock content area).
    # passvbox.pack_start(grid, ...) called.
    # args[0] of pack_start is the grid.
    pack_args, _ = mock_content_area.pack_start.call_args
    grid = pack_args[0]

    # Find entry in grid
    userentry = None
    for child in grid.get_children():
        if isinstance(child, Gtk.Entry):
            userentry = child
            break

    assert userentry is not None
    userentry.set_text("secret")

    # Trigger OK
    ok_callback(None)
    assert dialog.pdf_user_password == "secret"

    # Verify downsample logic
    dialog.downsample = False
    assert dialog.downsample is False

    dialog.downsample = True
    assert dialog.downsample is True

    # Verify PDF compression change
    hboxq = mocker.Mock()
    widget = mocker.Mock()
    widget.get_active_index.return_value = "jpg"

    dialog._pdf_compression_changed_callback(widget, hboxq)
    assert dialog.pdf_compression == "jpg"
    hboxq.show.assert_called_once()

    widget.get_active_index.return_value = "lzw"
    dialog._pdf_compression_changed_callback(widget, hboxq)
    assert dialog.pdf_compression == "lzw"
    hboxq.hide.assert_called_once()


def test_date_entry_validation(mocker):
    "test date entry validation"
    dialog = Save(transient_for=Gtk.Window())

    entry = dialog._meta_datetime_widget
    # Mock stop_emission_by_name and insert_text
    # We use mocker.patch.object to avoid RecursionError by keeping real block/unblock
    entry.stop_emission_by_name = mocker.Mock()
    entry.insert_text = mocker.Mock()

    # Test valid date char
    mocker.patch.object(entry, "get_text", return_value="2020")
    dialog._insert_text_handler(entry, "-", 0, 4)
    entry.insert_text.assert_called_with("-", 4)

    entry.insert_text.reset_mock()

    # Test invalid date char
    dialog._insert_text_handler(entry, "a", 0, 4)
    entry.insert_text.assert_not_called()

    # Test include_time=True
    dialog.include_time = True
    # Refresh entry text mock
    mocker.patch.object(entry, "get_text", return_value="2020-01-01 ")
    dialog._insert_text_handler(entry, ":", 0, 11)
    entry.insert_text.assert_called_with(":", 11)


def test_edit_date_button(mocker):
    "test _clicked_edit_date_button"

    dialog = Save(
        transient_for=Gtk.Window(),
        meta_datetime=datetime(2020, 1, 1),
        select_datetime=True,
    )

    captured_dialogs = []
    original_dialog = Dialog

    class CapturedDialog(original_dialog):
        "capture dialog instances"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured_dialogs.append(self)

    mocker.patch("dialog.save.Dialog", CapturedDialog)

    # Patch Gtk.Calendar and Gtk.Button using original classes
    captured_calendar = []
    captured_button = []
    original_calendar = Gtk.Calendar
    original_button = Gtk.Button

    class CapturedCalendar(original_calendar):
        "capture calendar instances"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured_calendar.append(self)

    class CapturedButton(original_button):
        "capture button instances"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured_button.append(self)

    mocker.patch("gi.repository.Gtk.Calendar", CapturedCalendar)
    mocker.patch("gi.repository.Gtk.Button", CapturedButton)
    dialog._clicked_edit_date_button(None)
    assert len(captured_dialogs) > 0

    passwin = captured_dialogs[0]
    mocker.patch.object(passwin, "destroy")
    assert len(captured_calendar) > 0

    calendar = captured_calendar[0]

    # Find "Today" button
    today_b = None
    for btn in captured_button:
        if btn.get_label() == "Today":
            today_b = btn
            break

    assert today_b is not None

    # Simulate day selection on calendar
    mocker.patch.object(
        calendar, "get_date", return_value=(2021, 1, 2)
    )  # 2021, Feb 2nd
    calendar.emit("day-selected")
    assert dialog.meta_datetime == datetime(2021, 2, 2)

    # Simulate double click
    calendar.emit("day-selected-double-click")
    passwin.destroy.assert_called_once()

    # Simulate "Today" button click
    today_b.clicked()
    expected_today = date.today().isoformat()
    assert dialog._meta_datetime_widget.get_text() == expected_today


def test_image_type_changed_branches(mocker):
    "test branches in _image_type_changed_callback"
    dialog = Save(transient_for=Gtk.Window())
    dialog.resize = mocker.Mock()

    # Mocks for data
    vboxp = mocker.Mock(spec=Gtk.Box)
    hboxpq = mocker.Mock(spec=Gtk.Box)
    hboxc = mocker.Mock(spec=Gtk.Box)
    hboxtq = mocker.Mock(spec=Gtk.Box)
    hboxps = mocker.Mock(spec=Gtk.Box)
    data = [vboxp, hboxpq, hboxc, hboxtq, hboxps]
    widget = mocker.Mock()

    # Test 'tif' with jpeg compression
    widget.get_active_index.return_value = "tif"
    dialog.tiff_compression = "jpeg"
    dialog._image_type_changed_callback(widget, data)
    hboxtq.show.assert_called()

    # Test 'tif' without jpeg compression
    hboxtq.show.reset_mock()
    hboxtq.hide = mocker.Mock()
    dialog.tiff_compression = "lzw"
    dialog._image_type_changed_callback(widget, data)
    hboxtq.hide.assert_called()

    # Test 'ps'
    widget.get_active_index.return_value = "ps"
    dialog._image_type_changed_callback(widget, data)
    hboxps.show.assert_called()

    # Test 'jpg'
    widget.get_active_index.return_value = "jpg"
    dialog._image_type_changed_callback(widget, data)
    hboxtq.show.assert_called()

    # Test other
    widget.get_active_index.return_value = "png"
    dialog._image_type_changed_callback(widget, data)
    hboxps.hide.assert_called()


def test_datetime_focus_out():
    "test _datetime_focus_out_callback"
    dialog = Save(transient_for=Gtk.Window(), select_datetime=True)

    # Ensure now widget is NOT active so it doesn't return datetime.now()
    dialog.meta_now_widget.set_active(False)
    dialog._meta_specify_widget.set_active(True)
    entry = dialog._meta_datetime_widget
    entry.set_text("2022-02-22")

    # Simulate focus out
    dialog._datetime_focus_out_callback(entry, None)
    assert dialog.meta_datetime == datetime(2022, 2, 22)


def test_datetime_setter():
    "test meta_datetime setter updates widget"
    dialog = Save(transient_for=Gtk.Window(), include_time=True)
    new_dt = datetime(2023, 3, 23, 12, 0, 0)
    dialog.meta_datetime = new_dt
    assert dialog._meta_datetime_widget.get_text() == "2023-03-23 12:00:00"


def test_tiff_compression_selection(mocker):
    "test tiff compression selection updates UI"
    dialog = Save(
        transient_for=Gtk.Window(),
        image_types=["tif"],
        ps_backends=["pdf2ps"],
    )
    dialog.resize = mocker.Mock()
    dialog.add_image_type()

    def find_widget_by_label(container, label_text, widget_type):
        "Find a widget by its sibling label text"
        for child in container.get_children():
            if isinstance(child, Gtk.Box):
                res = find_widget_by_label(child, label_text, widget_type)
                if res:
                    return res
                grand_children = child.get_children()
                has_label = any(
                    isinstance(gc, Gtk.Label) and gc.get_text() == label_text
                    for gc in grand_children
                )
                if has_label:
                    for gc in grand_children:
                        if isinstance(gc, widget_type):
                            return gc
        return None

    content_area = dialog.get_content_area()
    combobtc = find_widget_by_label(content_area, "Compression", Gtk.ComboBox)
    assert combobtc is not None, "Could not find Compression ComboBox"

    def find_box_containing_label(container, label_text):
        for child in container.get_children():
            if isinstance(child, Gtk.Box):
                if any(
                    isinstance(gc, Gtk.Label) and gc.get_text() == label_text
                    for gc in child.get_children()
                ):
                    return child
                res = find_box_containing_label(child, label_text)
                if res:
                    return res
        return None

    hboxtq = find_box_containing_label(content_area, "JPEG Quality")
    assert hboxtq is not None, "Could not find JPEG Quality Box"

    # Test setting to 'jpeg'
    combobtc.set_active_index("jpeg")
    assert dialog.tiff_compression == "jpeg"
    assert hboxtq.get_visible()

    # Test setting to 'lzw'
    combobtc.set_active_index("lzw")
    assert dialog.tiff_compression == "lzw"
    assert not hboxtq.get_visible()
    dialog.resize.assert_called()


def test_other_save_dialog_callbacks(mocker):
    "test other callbacks in Save dialog"
    dialog = Save(
        transient_for=Gtk.Window(),
        image_types=["pdf", "ps"],
        ps_backends=["pdf2ps", "pdftops"],
    )
    dialog.add_image_type()
    content_area = dialog.get_content_area()

    def find_widget_by_label(container, label_text, widget_type):
        "Find a widget by its sibling label text"
        for child in container.get_children():
            if isinstance(child, Gtk.Box):
                res = find_widget_by_label(child, label_text, widget_type)
                if res:
                    return res
                grand_children = child.get_children()
                has_label = any(
                    isinstance(gc, Gtk.Label) and gc.get_text() == label_text
                    for gc in grand_children
                )
                if has_label:
                    for gc in grand_children:
                        if isinstance(gc, widget_type):
                            return gc
        return None

    # Test ps_backend_changed_callback
    combops = find_widget_by_label(content_area, "Postscript backend", Gtk.ComboBox)
    assert combops is not None
    combops.set_active_index("pdf2ps")
    assert dialog.ps_backend == "pdf2ps"

    # Test downsample callbacks
    def find_checkbutton(container, label_text):
        for child in container.get_children():
            if isinstance(child, Gtk.CheckButton) and child.get_label() == label_text:
                return child
            if isinstance(child, Gtk.Box):
                res = find_checkbutton(child, label_text)
                if res:
                    return res
        return None

    downsample_btn = find_checkbutton(content_area, "Downsample to")
    assert downsample_btn is not None

    def find_all_spinbuttons_near_label(container, label_text):
        found = []
        for child in container.get_children():
            if isinstance(child, Gtk.Box):
                grand_children = child.get_children()
                if any(
                    isinstance(gc, Gtk.Label) and gc.get_text() == label_text
                    for gc in grand_children
                ):
                    for gc in grand_children:
                        if isinstance(gc, Gtk.SpinButton):
                            found.append(gc)
                found.extend(find_all_spinbuttons_near_label(child, label_text))
        return found

    downsample_spins = find_all_spinbuttons_near_label(content_area, "PPI")
    assert len(downsample_spins) > 0
    downsample_spin = downsample_spins[0]

    downsample_btn.set_active(True)
    assert dialog.downsample is True
    assert downsample_spin.get_sensitive() is True

    downsample_spin.set_value(300)
    # Trigger the value-changed signal
    downsample_spin.emit("value-changed")
    assert dialog.downsample_dpi == 300

    # Test jpg_quality_changed_callback
    # Find all JPEG Quality spinbuttons and test the one that is NOT the TIFF one
    quality_spins = find_all_spinbuttons_near_label(content_area, "JPEG Quality")
    assert len(quality_spins) > 0

    # Let's just test all of them and see if any updates jpeg_quality
    # In PDF case, it should be one of them.
    found_pdf_spin = False
    for spin in quality_spins:
        spin.set_value(95)
        spin.emit("value-changed")
        if dialog.jpeg_quality == 95:
            found_pdf_spin = True
            break
    assert found_pdf_spin, "Could not find PDF JPEG Quality SpinButton"


def test_date_entry_inc_dec(mocker):
    "test + and - keys in date entry"
    dialog = Save(transient_for=Gtk.Window())
    entry = dialog._meta_datetime_widget
    entry.set_text("2020-01-01")

    # Mock stop_emission_by_name but keep other behavior
    entry.stop_emission_by_name = mocker.Mock()

    # Test + key
    dialog._insert_text_handler(entry, "+", 1, 10)
    assert entry.get_text() == "2020-01-02"

    # Test - key
    dialog._insert_text_handler(entry, "-", 1, 10)
    assert entry.get_text() == "2020-01-01"

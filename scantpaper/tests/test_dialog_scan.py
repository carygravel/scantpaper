"test scan dialog current_scan_options property"

from types import SimpleNamespace
import gi
from dialog.scan import Scan, _build_profile_table
from scanner.profile import Profile

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_current_scan_options_property():
    "test current_scan_options property getter and setter"

    dialog = Scan(
        title="title",
        transient_for=Gtk.Window(),
    )

    # Test initial value (should be a Profile)
    # Based on _current_scan_options initialization in Scan class
    assert isinstance(dialog.current_scan_options, Profile)

    # Test setter
    new_profile = Profile(backend=[("mode", "Color")])
    dialog.current_scan_options = new_profile
    assert dialog.current_scan_options == new_profile


def test_ignore_duplex_capabilities_property():
    "test ignore_duplex_capabilities property getter and setter"

    dialog = Scan(
        title="title",
        transient_for=Gtk.Window(),
    )

    # Test initial value
    assert not dialog.ignore_duplex_capabilities, "Initial value should be False"

    # Test setter
    dialog.ignore_duplex_capabilities = True
    assert dialog.ignore_duplex_capabilities, "Value should be True after setting"


def test_show(mocker):
    "test show method"
    # pylint: disable=protected-access
    dialog = Scan(title="title", transient_for=Gtk.Window())

    # Mock PageControls.show to avoid GTK warnings or errors if not fully initialized
    mocker.patch("dialog.scan.PageControls.show")

    # Mock internal components
    dialog.framex = mocker.Mock()
    dialog._flatbed_or_duplex_callback = mocker.Mock()
    dialog.thread = mocker.Mock()

    mock_options = mocker.Mock()
    mock_options.num_options.return_value = 0
    dialog.available_scan_options = mock_options
    dialog._flatbed_or_duplex_callback.reset_mock()

    dialog._hide_geometry = mocker.Mock()

    # Mock combobp
    dialog.combobp = mocker.Mock()
    dialog.combobp.get_active_text.return_value = "A4"  # Not "Manual" and not None
    dialog.show()

    # Assertions
    dialog.framex.hide.assert_called_once()
    dialog._flatbed_or_duplex_callback.assert_called_once()
    dialog._hide_geometry.assert_called_once_with(dialog.available_scan_options)
    assert dialog.cursor == "default"

    dialog.cursor = "wait"
    assert dialog.cursor == "wait", "Cursor should be 'wait' after setting"


def test_device_dropdown_changed(mocker):
    "test do_device_dropdown_changed callback"
    # pylint: disable=protected-access

    dialog = Scan(title="title", transient_for=Gtk.Window())

    # Mock get_devices to verify call
    dialog.get_devices = mocker.Mock()

    # Use real device_list setter to populate combobox
    dev1 = SimpleNamespace(name="dev1", label="Device 1")
    dialog.device_list = [dev1]

    # device_list setter populates combobd.
    # It inserts "Device 1" at 0.
    # "Rescan" should be at 1.

    # Test selecting device
    dialog.combobd.set_active(0)
    # pylint: disable=comparison-with-callable
    assert dialog.device == "dev1"
    dialog.get_devices.assert_not_called()

    # Test selecting Rescan
    dialog.combobd.set_active(1)

    # Assertions
    assert dialog.device is None
    dialog.get_devices.assert_called_once()


def test_edit_paper_apply(mocker):
    "test _edit_paper and applying changes"
    # pylint: disable=protected-access

    dialog = Scan(title="title", transient_for=Gtk.Window())
    dialog.paper_formats = {"A4": {"x": 210, "y": 297, "l": 0, "t": 0}}

    # Mock PaperList
    mock_paperlist_cls = mocker.patch("dialog.scan.PaperList")
    mock_slist = mock_paperlist_cls.return_value
    # Set data that will be read by do_apply_paper_sizes
    # Row format: [name, x, y, l, t]
    mock_slist.data = [["NewFormat", 100, 200, 0, 0]]

    # Mock Dialog
    mock_dialog_cls = mocker.patch("dialog.scan.Dialog")
    mock_window = mock_dialog_cls.return_value
    # Mock get_content_area to return a box we can inspect?
    mock_vbox = mocker.Mock()
    mock_window.get_content_area.return_value = mock_vbox

    # Mock main module if it's used
    mock_main = mocker.patch("dialog.scan.main", create=True)

    # Patch Gtk in dialog.scan to avoid TypeErrors when mixing real/mock widgets
    mock_gtk = mocker.patch("dialog.scan.Gtk")

    # We need to capture the 'Apply' button callback.
    # The button is created with Gtk.Button.new_with_label(_("Apply"))

    apply_callback = None

    def mock_new_with_label(label):
        btn = mocker.Mock()
        if label == "Apply":  # Assuming no translation or "Apply" is passed

            def connect(signal, callback, *_args):
                if signal == "clicked":
                    nonlocal apply_callback
                    apply_callback = callback

            btn.connect.side_effect = connect
        return btn

    mock_gtk.Button.new_with_label.side_effect = mock_new_with_label

    # Set ignored_paper_formats to test the warning dialog path
    dialog.ignored_paper_formats = ["BadFormat"]

    # Call _edit_paper
    dialog._edit_paper()

    assert apply_callback is not None

    # Call the callback
    # pylint: disable=not-callable
    apply_callback(None)  # argument is widget, ignored

    # Verify paper_formats updated
    assert "NewFormat" in dialog.paper_formats
    assert dialog.paper_formats["NewFormat"] == {"x": 100, "y": 200, "l": 0, "t": 0}

    # Verify message dialog shown
    mock_main.show_message_dialog.assert_called_once()

    # Verify window destroyed
    mock_window.destroy.assert_called_once()


def test_delete_profile_frontend_item(mocker):
    "test deleting a frontend item from the profile editor"
    # pylint: disable=protected-access

    # Setup
    profile = Profile()
    profile.add_frontend_option("test_option", "value")
    options = mocker.Mock()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # Call the function
    _build_profile_table(profile, options, vbox)

    # Find the delete button
    # vbox children: frameb, framef
    children = vbox.get_children()
    framef = None
    for child in children:
        if isinstance(child, Gtk.Frame) and child.get_label() == "Frontend options":
            framef = child
            break

    assert framef is not None, "Frontend options frame not found"

    listbox = framef.get_child()
    rows = listbox.get_children()
    assert len(rows) == 1, "Should have 1 row"

    hbox = rows[0].get_child()
    hbox_children = hbox.get_children()
    button = None
    for child in hbox_children:
        if isinstance(child, Gtk.Button):
            button = child
            break

    assert button is not None, "Delete button not found"

    # Mock logger to verify debug message
    mock_logger = mocker.patch("dialog.scan.logger")

    # Click the button
    button.clicked()

    # Verify option removed
    assert "test_option" not in profile.frontend

    # Verify logging
    mock_logger.debug.assert_called_with(
        "removing option '%s' from profile", "test_option"
    )

    # Verify UI updated (listbox should be empty)
    children = vbox.get_children()
    framef_new = None
    for child in children:
        if isinstance(child, Gtk.Frame) and child.get_label() == "Frontend options":
            framef_new = child
            break

    listbox_new = framef_new.get_child()
    rows_new = listbox_new.get_children()
    assert len(rows_new) == 0, "Should have 0 rows after deletion"


def test_delete_profile_backend_item(mocker):
    "test deleting a backend item from the profile editor"
    # pylint: disable=protected-access

    # Setup
    profile = Profile(backend=[("mode", "Color")])

    # Mock options.by_name to return something valid
    mock_opt = mocker.Mock()
    mock_opt.title = "Scan Mode"
    options = mocker.Mock()
    options.by_name.return_value = mock_opt

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # Call the function
    _build_profile_table(profile, options, vbox)

    # Find the delete button
    # vbox children: frameb, framef
    children = vbox.get_children()
    frameb = None
    for child in children:
        if isinstance(child, Gtk.Frame) and child.get_label() == "Backend options":
            frameb = child
            break

    assert frameb is not None, "Backend options frame not found"

    listbox = frameb.get_child()
    rows = listbox.get_children()
    assert len(rows) == 1, "Should have 1 row"

    hbox = rows[0].get_child()
    hbox_children = hbox.get_children()
    button = None
    for child in hbox_children:
        if isinstance(child, Gtk.Button):
            button = child
            break

    assert button is not None, "Delete button not found"

    # Mock logger to verify debug message
    mock_logger = mocker.patch("dialog.scan.logger")

    # Click the button
    button.clicked()

    # Verify option removed
    # profile.backend is a list of tuples or dicts, depending on init
    # In this case it should be a list of tuples: [('mode', 'Color')]
    # After deletion it should be empty
    assert len(profile.backend) == 0

    # Verify logging
    mock_logger.debug.assert_called_with("removing option '%s' from profile", "mode")

    # Verify UI updated (listbox should be empty)
    children = vbox.get_children()
    frameb_new = None
    for child in children:
        if isinstance(child, Gtk.Frame) and child.get_label() == "Backend options":
            frameb_new = child
            break

    listbox_new = frameb_new.get_child()
    rows_new = listbox_new.get_children()
    assert len(rows_new) == 0, "Should have 0 rows after deletion"


def test_rescan_hides_widgets(mocker):
    "test that selecting rescan hides the device widgets"
    # pylint: disable=protected-access

    dialog = Scan(title="title", transient_for=Gtk.Window())

    # Mock get_devices to verify call and prevent actual execution
    dialog.get_devices = mocker.Mock()

    # Setup device list
    dev1 = SimpleNamespace(name="dev1", label="Device 1")
    dialog.device_list = [dev1]

    # Find labeld
    # hboxd contains labeld (start) and combobd (end)
    children = dialog.hboxd.get_children()
    labeld = None
    for child in children:
        if isinstance(child, Gtk.Label):
            labeld = child
            break
    assert labeld is not None

    # Spy on hide methods
    # We patch the hide method on the instances
    mock_combobd_hide = mocker.patch.object(dialog.combobd, "hide")
    mock_labeld_hide = mocker.patch.object(labeld, "hide")

    # Select Rescan (index 1)
    # device_list has 1 item (index 0). Rescan is index 1.
    dialog.combobd.set_active(1)

    # Verification
    mock_combobd_hide.assert_called_once()
    mock_labeld_hide.assert_called_once()
    assert dialog.device is None
    dialog.get_devices.assert_called_once()


def test_cursor_setter_with_window(mocker):
    "test cursor setter when window exists"
    dialog = Scan(title="title", transient_for=Gtk.Window())

    # Mock get_window
    mock_window = mocker.Mock()
    mocker.patch.object(dialog, "get_window", return_value=mock_window)

    # Mock Gdk interactions
    mock_gdk = mocker.patch("dialog.scan.Gdk")
    mock_display = mocker.Mock()
    mock_gdk.Display.get_default.return_value = mock_display
    mock_cursor = mocker.Mock()
    mock_gdk.Cursor.new_from_name.return_value = mock_cursor

    # Set cursor
    dialog.cursor = "wait"

    # Assertions
    mock_gdk.Display.get_default.assert_called_once()
    mock_gdk.Cursor.new_from_name.assert_called_once_with(mock_display, "wait")
    mock_window.set_cursor.assert_called_once_with(mock_cursor)
    assert dialog.cursor == "wait"

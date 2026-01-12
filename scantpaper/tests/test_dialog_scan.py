"test scan dialog current_scan_options property"

from types import SimpleNamespace
import gi
from dialog.scan import Scan
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


def test_show(mocker):
    "test show method"
    # pylint: disable=protected-access
    dialog = Scan(title="title", transient_for=Gtk.Window())

    # Mock PageControls.show to avoid GTK warnings or errors if not fully initialized
    mocker.patch("dialog.scan.PageControls.show")

    # Mock internal components
    dialog.framex = mocker.Mock()
    dialog._flatbed_or_duplex_callback = mocker.Mock()
    dialog.available_scan_options = mocker.Mock()
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

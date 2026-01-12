"test scan dialog current_scan_options property"

import gi
from dialog.scan import Scan
from scanner.profile import Profile

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_current_scan_options_property():
    "test current_scan_options property getter and setter"

    window = Gtk.Window()
    dialog = Scan(
        title="title",
        transient_for=window,
    )

    # Test initial value (should be a Profile)
    # Based on _current_scan_options initialization in Scan class
    assert isinstance(dialog.current_scan_options, Profile)

    # Test setter
    new_profile = Profile(backend=[("mode", "Color")])
    dialog.current_scan_options = new_profile
    assert dialog.current_scan_options == new_profile

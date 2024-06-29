"test scan dialog"

import gi
from dialog.sane import SaneScanDialog
from scanner.profile import Profile

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position

TIMEOUT = 10000


def test_1():
    "Check options are reset before applying a profile"

    dlg = SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )
    dlg._add_profile("my profile", Profile(backend=[("resolution", 100)]))

    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.device = "test"
    dlg.scan_options()

    loop.run()
    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    def changed_scan_option_cb(_arg, _arg2, _arg3, _arg4):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    dlg.set_option(dlg.available_scan_options.by_name("tl-x"), 10)

    loop.run()
    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    def changed_profile_cb(widget, profile):
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert dlg.current_scan_options == Profile(
            backend=[("resolution", 100)]
        ), "reset before applying profile"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"
    loop.run()

    assert asserts == 1, "all callbacks ran"
    dlg.thread.quit()

"test scan dialog"

from scanner.profile import Profile


def test_1(sane_scan_dialog, mainloop_with_timeout):
    "Check options are reset before applying a profile"

    dlg = sane_scan_dialog
    dlg._add_profile("my profile", Profile(backend=[("resolution", 100)]))
    loop = mainloop_with_timeout()
    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.device = "test"
    dlg.scan_options()
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb(_arg, _arg2, _arg3, _arg4):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    dlg.set_option(dlg.available_scan_options.by_name("tl-x"), 10)
    loop.run()

    loop = mainloop_with_timeout()

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

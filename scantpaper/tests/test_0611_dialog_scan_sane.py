"test scan dialog"

from scanner.profile import Profile


def test_1(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    loop = mainloop_with_timeout()
    callbacks = 0
    dialog._add_profile("my profile", Profile(backend=[("resolution", 52)]))

    def changed_scan_option_cb(_widget, option, value, uuid):
        dialog.disconnect(dialog.option_signal)
        assert dialog.current_scan_options == Profile(
            frontend={"num_pages": 1}, backend=[("resolution", 52)]
        ), "current-scan-options"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert profile == "my profile", "changed-profile"
        nonlocal callbacks
        callbacks += 1

    dialog.option_signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dialog.scan_options("test:0")
    loop.run()

    assert dialog.profile is None, "reloading scan options unsets profile"
    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()

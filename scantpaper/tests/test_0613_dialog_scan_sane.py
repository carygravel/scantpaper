"test scan dialog"
from scanner.profile import Profile


def test_1(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    def changed_current_scan_options_cb(_widget, profile, _uuid):
        nonlocal callbacks
        dialog.disconnect(dialog.signal)
        assert profile == Profile(
            frontend={"num_pages": 1}, backend=[("resolution", 51)]
        ), "emitted changed-current-scan-options"
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("resolution"), 51)
    loop = mainloop_with_timeout()
    loop.run()

    assert callbacks == 1, "all callbacks executed"

    dialog.thread.quit()

"test scan dialog"

from scanner.profile import Profile


def test_1(
    sane_scan_dialog,
    set_device_wait_reload,
    set_option_in_mainloop,
    mainloop_with_timeout,
):
    """Check that with the cycle-sane-handle option activated, after scanning,
    the open-device process has fired, and then that options are still the same"""

    dialog = sane_scan_dialog
    dialog.cycle_sane_handle = True
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    assert set_option_in_mainloop(dialog, "resolution", 51), "set resolution"
    assert dialog.current_scan_options == Profile(
        backend=[("resolution", 51)]
    ), "set resolution before scan"

    def finished_process_cb(_widget, process):
        if process == "open_device":
            dialog.disconnect(dialog.open_signal)
            nonlocal callbacks
            callbacks += 1

    def changed_scan_option_cb(self, option, value, uuid):
        dialog.disconnect(dialog.option_signal)
        assert dialog.current_scan_options == Profile(
            backend=[("resolution", 51)]
        ), "set resolution after scan"
        assert (
            dialog.option_widgets["resolution"] is not None
        ), "resolution widget should be defined by the time the scan options have been updated"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.open_signal = dialog.connect("finished-process", finished_process_cb)
    dialog.option_signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    loop = mainloop_with_timeout()
    dialog.scan()
    loop.run()

    assert callbacks == 2, "all callbacks executed"

    dialog.thread.quit()

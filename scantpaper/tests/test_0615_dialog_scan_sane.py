"test scan dialog"
from scanner.profile import Profile


def test_1(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """There are some backends where the paper-width and -height options are
    only valid when the ADF is active. Therefore, changing the paper size
    when the flatbed is active tries to set these options, causing an
    "invalid argument" error, which is normally not possible, as the
    option is ghosted.
    Test this by setting up a profile with "bool-soft-select-soft-detect"
    and then a valid option. Check that:
    a. no error message is produced
    b. the rest of the profile is correctly applied
    c. the appropriate signals are still emitted."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    dialog._add_profile(
        "my profile",
        Profile(backend=[("bool-soft-select-soft-detect", True), ("mode", "Color")]),
    )
    loop = mainloop_with_timeout()
    callbacks = 0

    def process_error_cb(response):
        assert False, "Should not throw error"

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.profile_signal)
        assert dialog.current_scan_options == Profile(
            frontend={"num_pages": 1}, backend=[("mode", "Color")]
        )
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("process-error", process_error_cb)
    dialog.profile_signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    assert callbacks == 1, "all callbacks executed"

    dialog.thread.quit()

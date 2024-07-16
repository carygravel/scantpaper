"test scan dialog"
from scanner.profile import Profile


def test_1(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """Setting a profile means setting a series of options; setting the
    first, waiting for it to finish, setting the second, and so on. If one
    of the settings is already applied, and therefore does not fire a
    signal, then there is a danger that the rest of the profile is not
    set."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    dialog._add_profile(
        "g51",
        Profile(backend=[("page-height", 297), ("y", 297), ("resolution", 51)]),
    )
    dialog._add_profile(
        "c50",
        Profile(backend=[("page-height", 297), ("y", 297), ("resolution", 50)]),
    )
    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.profile_signal)
        assert (
            dialog.thread.device_handle.resolution == 51.0
        ), "correctly updated widget"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.profile_signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "g51"
    loop.run()
    loop = mainloop_with_timeout()

    def changed_profile_cb2(_widget, _profile):
        dialog.disconnect(dialog.profile_signal)
        assert dialog.current_scan_options == Profile(
            backend=[("page-height", 297), ("resolution", 50), ("br-y", 200.0)]
        ), "fired signal and set profile"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.profile_signal = dialog.connect("changed-profile", changed_profile_cb2)
    dialog.profile = "c50"
    loop.run()

    assert callbacks == 2, "all callbacks executed"

    dialog.thread.quit()

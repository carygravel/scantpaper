"""test scan dialog."""

import logging

from scanner.profile import Profile

logger = logging.getLogger(__name__)


def test_reloads_in_profile(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    mainloop_with_timeout,
    sane_scan_mocks,
):
    """Given a profile of scan options that trigger multiple reloads.

    Check the changed-profile signal is only emitted once.
    """
    sane_scan_mocks.patch_all(mocker)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")
    callbacks = 0
    loop = mainloop_with_timeout()

    def added_profile_cb(_widget, name, _profile):
        assert name == "my profile", "added-profile signal emitted"
        nonlocal callbacks
        callbacks += 1

    dialog.connect("added-profile", added_profile_cb)
    dialog._add_profile(
        "my profile",
        Profile(
            backend=[
                ("br-x", 210.0),
                ("br-y", 297.0),
                ("source", "Automatic Document Feeder"),
                ("scan-area", "A4"),
                ("y-resolution", 150),
                ("x-resolution", 150),
                ("brightness", 10),
                ("contrast", 10),
            ]
        ),
    )

    def changed_profile_cb(_widget, profile):
        assert profile == "my profile", "changed-profile"
        assert dialog.current_scan_options == Profile(
            backend=[
                ("scan-area", "A4"),
                ("br-y", 297.0),
                ("y-resolution", 150),
                ("source", "Automatic Document Feeder"),
                ("x-resolution", 150),
                ("brightness", 10),
                ("br-x", 210.0),
                ("contrast", 10),
            ],
        ), "profile with multiple reloads"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    assert callbacks == 2, "changed-profile only called once"

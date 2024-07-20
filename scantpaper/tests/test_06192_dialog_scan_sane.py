"test scan dialog"
from scanner.profile import Profile


def test_1(
    sane_scan_dialog,
    set_device_wait_reload,
    set_paper_in_mainloop,
    mainloop_with_timeout,
):
    """Having applied geometry settings via a paper size, if a profile is set
    that changes the geometry, ensure the paper size is unset"""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    dialog.paper_formats = {
        "10x10": {
            "l": 0,
            "y": 10,
            "x": 10,
            "t": 0,
        },
    }
    assert set_paper_in_mainloop(dialog, "10x10"), "set 10x10"

    dialog._add_profile("20x20", Profile(backend=[("br-y", 20)]))
    loop = mainloop_with_timeout()

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert dialog.paper is None, "paper undefined after changing geometry"
        assert (
            dialog.combobp.get_active_text() == "Manual"
        ), "paper undefined means manual geometry"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "20x20"
    loop.run()

    # If a profile is set, and setting a paper changes the geometry,
    # the profile should be unset.
    assert set_paper_in_mainloop(dialog, "10x10"), "set 10x10 again"
    assert dialog.profile is None, "profile undefined after changing geometry"

    loop = mainloop_with_timeout()

    def changed_paper3(_widget, _paper):
        dialog.disconnect(dialog.signal)
        assert dialog.paper is None, "manual geometry means undefined paper"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-paper", changed_paper3)
    dialog.combobp.set_active_by_text("Manual")
    loop.run()

    dialog._add_profile(
        "10x10",
        Profile(
            frontend={"paper": "10x10"},
            backend=[("tl-y", 0), ("tl-x", 0), ("br-y", 10), ("br-x", 10)],
        ),
    )
    loop = mainloop_with_timeout()

    def changed_profile_cb2(_widget, _profile):
        dialog.disconnect(dialog.signal)
        assert dialog._get_paper_by_geometry() == "10x10", "get_paper_by_geometry()"
        assert dialog.paper == "10x10", "paper size updated after changing profile"
        assert dialog.combobp.get_active_text() == "10x10", "updated paper combobox"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb2)
    dialog.profile = "10x10"
    loop.run()

    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()

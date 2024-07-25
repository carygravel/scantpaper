"test scan dialog"
from types import SimpleNamespace
from scanner.profile import Profile


def test_1(
    sane_scan_dialog,
    mainloop_with_timeout,
):
    """Scan options are set to defaults before applying profile. Check
    that this doesn't happen immediately after initially opening the device.
    Ensure num_pages defaults to all with Source = Automatic Document Feeder
    in the default scan options"""

    dialog = sane_scan_dialog
    callbacks = 0
    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        dialog.set_current_scan_options(
            Profile(
                frontend={"num_pages": 0},
                backend=[("source", "Automatic Document Feeder")],
            )
        )
        nonlocal callbacks
        callbacks += 1

    def changed_current_scan_options_cb(_widget, profile, _uuid):
        dialog.disconnect(dialog.signal)
        assert dialog.num_pages == 0
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dialog.device_list = [
        SimpleNamespace(name="test:0", vendor="", model="", label=""),
    ]
    dialog.device = "test:0"
    loop.run()

    assert callbacks == 2, "callbacks executed once each"

    dialog.thread.quit()

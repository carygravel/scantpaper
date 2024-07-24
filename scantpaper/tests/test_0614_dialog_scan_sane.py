"test scan dialog"
import pytest
from scanner.profile import Profile


@pytest.mark.skip(
    reason="Until https://github.com/python-pillow/Sane/issues/92 is fixed, we cannot push buttons"
)
def test_button(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test button"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_scan_option_cb(widget, option, value, _data):
        nonlocal callbacks
        dialog.disconnect(dialog.signal)
        assert dialog.current_scan_options == Profile(
            backend=[("enable-test-options", True)]
        ), "enabled test options"
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("enable-test-options"), True)
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb2(_widget, _option, _value, _data):
        nonlocal callbacks
        dialog.disconnect(dialog.signal)
        assert dialog.current_scan_options == Profile(
            backend=[("enable-test-options", True), ("button", None)],
        ), "enabled test options"
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb2)
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("button"), None)
    loop.run()

    assert callbacks == 2, "all callbacks executed"

    dialog.thread.quit()

"test scan dialog"


def test_1(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    def changed_paper_formats(_widget, _formats):
        assert dialog.ignored_paper_formats == ["large"], "ignored paper formats"
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-paper-formats", changed_paper_formats)
    dialog.paper_formats = {
        "large": {
            "l": 0,
            "y": 3000,
            "x": 3000,
            "t": 0,
        },
        "small": {
            "l": 0,
            "y": 30,
            "x": 30,
            "t": 0,
        },
    }

    def changed_paper(_widget, paper):
        assert paper == "small", "do not change paper if it is too big"
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-paper", changed_paper)

    def changed_scan_option_cb(widget, option, value, _data):

        if option == "br-y":
            nonlocal callbacks
            dialog.disconnect(dialog.signal)
            callbacks += 1
            loop.quit()

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    loop = mainloop_with_timeout()
    dialog.paper = "large"
    dialog.paper = "small"
    loop.run()

    ######################################

    def changed_scan_option_cb2(_widget, option, _value, _data):
        dialog.disconnect(dialog.signal)
        assert (
            option == "resolution"
        ), "set other options after ignoring non-existant one"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb2)
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("non-existant option"), "dummy")
    dialog.set_option(options.by_name("resolution"), 51)
    loop = mainloop_with_timeout()
    loop.run()

    assert callbacks == 4, "all callbacks executed"

    dialog.thread.quit()

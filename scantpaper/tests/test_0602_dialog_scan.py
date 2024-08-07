"test scan dialog"

from gi.repository import GLib
from scanner.profile import Profile


def test_1(sane_scan_dialog, mainloop_with_timeout, set_option_in_mainloop):
    "first test with test backend"

    dialog = sane_scan_dialog
    dialog.paper_formats = {
        "new": {
            "l": 0.0,
            "y": 10.0,
            "x": 10.0,
            "t": 0.0,
        }
    }

    dialog.num_pages = 2

    asserts = 0

    def reloaded_scan_options_cb(_dialog):
        nonlocal signal
        nonlocal asserts
        nonlocal loop
        dialog.disconnect(signal)
        loop.quit()

    dialog.device = "test"
    dialog.scan_options()
    loop = mainloop_with_timeout()
    signal = dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    loop.run()

    options = dialog.available_scan_options

    # Check that profiles are being saved properly,
    assert set_option_in_mainloop(dialog, "tl-x", 10)
    assert set_option_in_mainloop(dialog, "tl-y", 10)
    dialog.save_current_profile("profile 1")
    assert dialog.profiles["profile 1"] == Profile(
        backend=[
            ("tl-x", 10),
            ("tl-y", 10),
        ],
    ), "applied 1st profile"
    assert dialog.profile == "profile 1", "saving current profile sets profile"

    assert set_option_in_mainloop(dialog, "tl-x", 20)
    assert set_option_in_mainloop(dialog, "tl-y", 20)
    dialog.save_current_profile("profile 2")
    assert dialog.profiles["profile 2"] == Profile(
        backend=[("tl-x", 20), ("tl-y", 20)]
    ), "applied 2nd profile"
    assert dialog.profiles["profile 1"] == Profile(
        backend=[
            ("tl-x", 10),
            ("tl-y", 10),
        ],
    ), "applied 2nd profile without affecting 1st"
    dialog._remove_profile("profile 1")
    assert dialog.profiles["profile 2"] == Profile(
        backend=[("tl-x", 20), ("tl-y", 20)]
    ), "remove_profile()"
    assert dialog.thread.device_handle.source == "Flatbed", "source defaults to Flatbed"
    assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages"
    assert not dialog.framen.is_sensitive(), "num-page gui ghosted"
    dialog.num_pages = 2
    assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages2"
    assert options.flatbed_selected(
        dialog.thread.device_handle
    ), "flatbed_selected() via value"
    assert not dialog._vboxx.get_visible(), "flatbed, so hide vbox for page numbering"

    asserts = asserts_2(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts)
    asserts_3(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts)


def asserts_2(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts):
    "splitting test_1 up into chunks"
    options = dialog.available_scan_options

    dialog.allow_batch_flatbed = True
    dialog.num_pages = 2

    def changed_num_pages_cb(self, _data):
        nonlocal asserts
        nonlocal signal
        dialog.disconnect(signal)
        assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages3"
        assert not dialog.framen.is_sensitive(), "num-page gui ghosted2"
        asserts += 1

    signal = dialog.connect("changed-num-pages", changed_num_pages_cb)
    dialog.allow_batch_flatbed = False
    loop = mainloop_with_timeout()
    assert (
        dialog.adf_defaults_scan_all_pages == 1
    ), "default adf-defaults-scan-all-pages"

    def changed_scan_option_cb(widget, option, value, _data):

        if option == "source":
            nonlocal asserts
            nonlocal signal
            dialog.disconnect(signal)
            assert (
                dialog.num_pages == 0
            ), "adf-defaults-scan-all-pages should force num-pages"
            assert not options.flatbed_selected(
                dialog.thread.device_handle
            ), "not flatbed_selected() via value"
            asserts += 1
            loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.set_option(options.by_name("source"), "Automatic Document Feeder")
    loop.run()

    assert set_option_in_mainloop(dialog, "source", "Flatbed")
    dialog.num_pages = 1

    loop = mainloop_with_timeout()

    def changed_scan_option_cb3(_widget, _option, _value, _data):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        assert False, "should not try to set invalid option"
        loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb3)

    def changed_current_scan_options_cb(_arg1, _arg2, _arg3):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        loop.quit()

    signal2 = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    dialog.set_current_scan_options(Profile(backend=[("mode", "Lineart")]))
    loop.run()
    return asserts


def asserts_3(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts):
    "splitting test_1 up into chunks"
    loop = mainloop_with_timeout()

    def changed_scan_option_cb4(_widget, _option, _value, _data):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        assert False, "should not try to set option if value already correct"
        loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb4)

    def changed_current_scan_options_cb2(_arg1, _arg2, _arg3):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        loop.quit()

    signal2 = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb2
    )

    def add_mode_gray_cb():
        dialog.set_current_scan_options(Profile(backend=[("mode", "Gray")]))

    GLib.idle_add(add_mode_gray_cb)
    loop.run()

    dialog.adf_defaults_scan_all_pages = 0
    assert set_option_in_mainloop(dialog, "source", "Automatic Document Feeder")
    assert dialog.num_pages == 1, "adf-defaults-scan-all-pages should force num-pages 2"
    assert dialog._vboxx.get_visible(), "simplex ADF, so show vbox for page numbering"

    # bug in 2.5.3 where setting paper via default options only
    # set combobox without setting options
    loop = mainloop_with_timeout()

    def changed_paper_cb(_arg1, _arg2):
        nonlocal asserts
        nonlocal signal
        dialog.disconnect(signal)
        assert dialog.current_scan_options == Profile(
            frontend={"paper": "new"},
            backend=[
                ("tl-x", 0.0),
                ("tl-y", 0.0),
                ("br-x", 10.0),
                ("br-y", 10.0),
            ],
        ), "set paper with conflicting options"
        asserts += 1
        loop.quit()

    signal = dialog.connect("changed-paper", changed_paper_cb)
    dialog.set_current_scan_options(
        Profile(
            backend=[
                ("tl-x", 20.0),
                ("tl-y", 20.0),
            ],
            frontend={"paper": "new"},
        )
    )
    loop.run()

    # bug previous to v2.1.7 where having having set double sided and
    # reverse, and then switched from ADF to flatbed, clicking scan produced
    # the error message that the facing pages should be scanned first
    dialog.side_to_scan = "reverse"
    assert set_option_in_mainloop(dialog, "source", "Flatbed")
    assert dialog.sided == "single", "selecting flatbed forces single sided"
    assert set_option_in_mainloop(dialog, "br-y", 9.0)
    loop = mainloop_with_timeout()
    dialog.connect("changed-paper", lambda x, y: loop.quit)
    dialog.paper = None
    loop.run()
    assert dialog.current_scan_options == Profile(
        backend=[
            ("tl-x", 0.0),
            ("tl-y", 0.0),
            ("br-x", 10.0),
            ("source", "Flatbed"),
            ("br-y", 9.0),
        ],
    ), "set Manual paper"
    assert (
        dialog.combobp.get_num_rows() == 3
    ), "available paper reapplied after setting/changing device"
    assert dialog.combobp.get_active_text() == "Manual", "paper combobox has a value"
    assert asserts == 3, "call callbacks run"
    dialog.thread.quit()

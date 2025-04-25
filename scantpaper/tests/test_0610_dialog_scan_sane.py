"test scan dialog"

from types import SimpleNamespace
import pytest
from dialog.sane import SaneScanDialog
from scanner.options import Options
from scanner.profile import Profile


def test_1(sane_scan_dialog):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    assert isinstance(dialog, SaneScanDialog), "Created SaneScanDialog"
    assert dialog.device == "", "device"
    assert dialog.device_list == [], "device-list"
    assert dialog.dir is None, "dir"
    assert dialog.num_pages == 1, "num-pages"
    assert dialog.max_pages == 0, "max-pages"
    assert dialog.page_number_start == 1, "page-number-start"
    assert dialog.page_number_increment == 1, "page-number-increment"
    assert dialog.side_to_scan == "facing", "side-to-scan"
    assert str(dialog.available_scan_options) == str(
        Options([])
    ), "available-scan-options"

    callbacks = 0

    def changed_num_pages_cb(_widget, n):
        dialog.disconnect(dialog.signal)
        assert n == 0, "changed-num-pages"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-num-pages", changed_num_pages_cb)
    dialog.allow_batch_flatbed = True
    dialog.num_pages = 0

    def changed_page_number_start_cb(_widget, n):
        dialog.disconnect(dialog.signal)
        assert n == 2, "changed-page-number-start"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect(
        "changed-page-number-start", changed_page_number_start_cb
    )
    dialog.page_number_start = 2

    def changed_page_number_increment_cb(_widget, n):
        dialog.disconnect(dialog.signal)
        assert n == 2, "changed-page-number-increment"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect(
        "changed-page-number-increment", changed_page_number_increment_cb
    )
    dialog.page_number_increment = 2

    def changed_side_to_scan_cb(_widget, side):
        dialog.disconnect(dialog.signal)
        assert side == "reverse", "changed-side-to-scan"
        assert dialog.page_number_increment == -2, "reverse side gives increment -2"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-side-to-scan", changed_side_to_scan_cb)
    dialog.side_to_scan = "reverse"
    assert callbacks == 4, "all callbacks executed"


def test_2(sane_scan_dialog, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    callbacks = 0
    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        dialog.disconnect(dialog.reloaded_signal)
        loop.quit()

    def changed_device_list_cb(_widget, device_list):
        dialog.disconnect(dialog.signal)
        assert dialog.device_list == [
            SimpleNamespace(name="test:0", vendor="", model="test:0", label="test:0"),
            SimpleNamespace(name="test:1", vendor="", model="test:1", label="test:1"),
        ], "add model field if missing"

        assert dialog.combobd.get_num_rows() == 3, "we still have the rescan item"
        nonlocal callbacks
        callbacks += 1

        def changed_device_cb(_widget, name):
            dialog.disconnect(dialog.signal)
            assert name == "test:0", "changed-device"
            nonlocal callbacks
            callbacks += 1

        dialog.signal = dialog.connect("changed-device", changed_device_cb)
        dialog.device = "test:0"

    dialog.reloaded_signal = dialog.connect(
        "reloaded-scan-options", reloaded_scan_options_cb
    )
    dialog.signal = dialog.connect("changed-device-list", changed_device_list_cb)
    dialog.device_list = [
        SimpleNamespace(name="test:0", vendor="", model="", label=""),
        SimpleNamespace(name="test:1", vendor="", model="", label=""),
    ]
    loop.run()

    def added_profile_cb(_widget, name, profile):
        dialog.disconnect(dialog.signal)
        assert name == "my profile", "added-profile signal emitted"
        assert profile == Profile(
            backend=[("resolution", 51), ("mode", "Color")]
        ), "added-profile profile"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("added-profile", added_profile_cb)
    dialog._add_profile(
        "my profile", Profile(backend=[("resolution", 51), ("mode", "Color")])
    )

    def added_profile_cb2(_widget, name, profile):
        dialog.disconnect(dialog.signal)
        assert name == "my profile", "replaced profile"
        assert profile == Profile(
            backend=[("resolution", 52), ("mode", "Color")]
        ), "new added-profile profile"
        assert dialog.combobsp.get_num_rows() == 1, "replaced entry in combobox"
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("added-profile", added_profile_cb2)
    dialog._add_profile(
        "my profile", Profile(backend=[("resolution", 52), ("mode", "Color")])
    )

    assert callbacks == 4, "all callbacks executed"
    dialog.thread.quit()


def test_3(sane_scan_dialog, mainloop_with_timeout, set_device_wait_reload):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    loop = mainloop_with_timeout()
    callbacks = 0
    dialog._add_profile(
        "my profile", Profile(backend=[("resolution", 52), ("mode", "Color")])
    )

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert profile == "my profile", "changed-profile"
        assert dialog.current_scan_options == Profile(
            backend=[("resolution", 52), ("mode", "Color")],
        ), "current-scan-options with profile"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    loop = mainloop_with_timeout()

    dialog._add_profile(
        "my profile2", Profile(backend=[("resolution", 52), ("mode", "Color")])
    )

    def changed_profile_cb2(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert profile == "my profile2", "set profile with identical options"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb2)
    dialog.profile = "my profile2"
    loop.run()

    assert callbacks == 2, "all callbacks executed"
    dialog.thread.quit()


def test_4(sane_scan_dialog, mainloop_with_timeout, set_device_wait_reload):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    dialog._add_profile(
        "my profile", Profile(backend=[("resolution", 52), ("mode", "Color")])
    )

    loop = mainloop_with_timeout()
    callbacks = 0

    def changed_scan_option_cb(_widget, option, value, uuid):
        dialog.disconnect(dialog.signal)
        assert (
            dialog.profile is None
        ), "changing an option deselects the current profile"
        assert dialog.current_scan_options == Profile(
            backend=[("resolution", 51)]
        ), "current-scan-options without profile"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("resolution"), 51)
    loop.run()

    geometry_widgets = options.geometry.keys()
    assert len(geometry_widgets) in [
        4,
        6,
    ], "Only 4 or 6 options should be flagged as geometry"

    ######################################

    loop = mainloop_with_timeout()

    def changed_profile_cb3(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert profile == "my profile", "reset profile back to my profile"
        assert dialog.current_scan_options == Profile(
            backend=[("resolution", 52), ("mode", "Color")]
        ), "current-scan-options after reset to profile my profile"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    # Reset profile for next test
    dialog.signal = dialog.connect("changed-profile", changed_profile_cb3)
    dialog.profile = "my profile"
    loop.run()

    ######################################

    loop = mainloop_with_timeout()

    def changed_profile_cb4(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert (
            profile is None
        ), "changing an option fires the changed-profile signal if a profile is set"
        assert dialog.current_scan_options == Profile(
            backend=[("mode", "Color"), ("resolution", 51)]
        ), "current-scan-options without profile (again)"
        assert (
            dialog.thread.device_handle.resolution == 51.0
        ), "option value updated when reloaded"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb4)
    dialog.set_option(options.by_name("resolution"), 51)
    loop.run()

    ######################################

    def removed_profile_cb(_widget, profile):
        assert profile == "my profile", "removed-profile"
        nonlocal callbacks
        callbacks += 1

    dialog.connect("removed-profile", removed_profile_cb)
    dialog._remove_profile("my profile")
    assert callbacks == 4, "all callbacks executed"
    dialog.thread.quit()


def test_5(sane_scan_dialog, mainloop_with_timeout, set_device_wait_reload):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    loop = mainloop_with_timeout()
    callbacks = 0

    dialog._add_profile(
        "cli geometry",
        Profile(backend=[("l", 1), ("y", 50), ("x", 50), ("t", 2), ("resolution", 50)]),
    )

    def changed_profile_cb5(_widget, _profile):
        dialog.disconnect(dialog.signal)
        options = dialog.available_scan_options
        backend = []
        if options.by_name("page-height"):
            backend.append(("page-height", 52))
        if options.by_name("page-width"):
            backend.append(("page-width", 51))
        backend.append(("tl-x", 1))
        backend.append(("br-y", 52))
        backend.append(("br-x", 51))
        backend.append(("tl-y", 2))

        # resolution=50 is the default,
        # so doesn't appear in current-scan-options
        # ( resolution, 50 )
        assert dialog.current_scan_options == Profile(
            backend=backend
        ), "CLI geometry option names"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.signal = dialog.connect("changed-profile", changed_profile_cb5)
    dialog.profile = "cli geometry"
    loop.run()

    assert callbacks == 1, "all callbacks executed"
    dialog.thread.quit()


def test_6(sane_scan_dialog, mainloop_with_timeout, set_device_wait_reload):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    def changed_paper_formats(_widget, _formats):
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-paper-formats", changed_paper_formats)
    dialog.paper_formats = {
        "new2": {
            "l": 0,
            "y": 10,
            "x": 10,
            "t": 0,
        }
    }

    loop = mainloop_with_timeout()

    def changed_paper_cb(widget, paper):
        assert paper == "new2", "changed-paper"
        assert not widget.option_widgets["tl-x"].is_visible(), "geometry hidden"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("changed-paper", changed_paper_cb)
    dialog.paper = "new2"
    loop.run()
    assert callbacks == 2, "all callbacks executed"
    dialog.thread.quit()


def test_7(sane_scan_dialog, mainloop_with_timeout, set_device_wait_reload):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    def changed_paper_formats(_widget, _formats):
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-paper-formats", changed_paper_formats)
    dialog.paper_formats = {
        "new2": {
            "l": 0,
            "y": 10,
            "x": 10,
            "t": 0,
        }
    }

    loop = mainloop_with_timeout()

    def changed_paper_cb(widget, paper):
        assert paper == "new2", "changed-paper"
        assert not widget.option_widgets["tl-x"].is_visible(), "geometry hidden"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("changed-paper", changed_paper_cb)

    s_signal, c_signal, f_signal = None, None, None

    def started_process_cb(_widget, process):
        dialog.disconnect(s_signal)
        nonlocal callbacks
        callbacks += 1

    def changed_progress_cb(_widget, progress, _arg):
        dialog.disconnect(c_signal)
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb(_widget, process):
        dialog.disconnect(f_signal)
        assert process == "set_option br-x to 10.0", "finished-process set_option"
        nonlocal callbacks
        callbacks += 1

    s_signal = dialog.connect("started-process", started_process_cb)
    c_signal = dialog.connect("changed-progress", changed_progress_cb)
    f_signal = dialog.connect("finished-process", finished_process_cb)
    dialog.paper = "new2"
    loop.run()
    assert callbacks == 5, "all callbacks executed"
    dialog.thread.quit()


def test_8(sane_scan_dialog, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    loop = mainloop_with_timeout()
    signal = None

    def reloaded_scan_options_cb(_arg):
        dialog.disconnect(signal)
        loop.quit()

    signal = dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dialog.device_list = [
        SimpleNamespace(name="test:0", vendor="", model="", label=""),
        SimpleNamespace(name="test:1", vendor="", model="", label=""),
    ]
    dialog.device = "test:0"
    loop.run()
    callbacks = 0

    loop = mainloop_with_timeout()
    n = 0

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1

    def finished_process_cb2(_widget, process):
        if process == "scan_pages":
            assert n == 1, "new-scan emitted once"

            def changed_device_cb(_widget, name):
                dialog.disconnect(dialog.signal)
                assert name == "test:1", "changed-device via combobox"
                nonlocal callbacks
                callbacks += 1

            # changing device via the combobox
            # should really change the device!
            dialog.signal = dialog.connect("changed-device", changed_device_cb)

            def reloaded_scan_options_cb(_arg):
                e_signal = None

                def process_error_cb(_widget, process, message):
                    dialog.disconnect(e_signal)
                    assert process == "open_device", "caught error opening device"
                    nonlocal callbacks
                    callbacks += 1
                    loop.quit()

                e_signal = dialog.connect("process-error", process_error_cb)

                # setting an unknown device should throw an error
                dialog.device = "error"

            dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
            dialog.combobd.set_active(1)

    dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb2)
    dialog.page_number_start = 1
    dialog.sided = "double"
    dialog.allow_batch_flatbed = True
    dialog.num_pages = 1
    dialog.side_to_scan = "facing"
    assert dialog.num_pages == 0, "num-pages after selecting facing"
    dialog.num_pages = 1
    dialog.scan()
    loop.run()

    assert callbacks == 2, "all callbacks executed"
    dialog.thread.quit()


def test_error_handling(sane_scan_dialog, mainloop_with_timeout):
    "test error handling of scan dialog with sane backend"

    dialog = sane_scan_dialog
    callbacks = 0
    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        dialog.disconnect(dialog.reloaded_signal)

        def process_error_cb(_widget, process, message):
            dialog.disconnect(dialog.e_signal)
            assert process == "set_option", "caught error setting scan option"
            nonlocal callbacks
            callbacks += 1
            loop.quit()

        def changed_scan_option_cb(_widget, option, value, uuid):
            dialog.disconnect(dialog.signal)
            assert False, "don't emit changed-scan-option signal on error"
            loop.quit()

        dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
        dialog.e_signal = dialog.connect("process-error", process_error_cb)
        options = dialog.available_scan_options
        dialog.set_option(options.by_name("mode"), "non-existent mode")

    dialog.reloaded_signal = dialog.connect(
        "reloaded-scan-options", reloaded_scan_options_cb
    )
    dialog.device_list = [
        SimpleNamespace(name="test:0", vendor="", model="", label=""),
    ]
    dialog.device = "test:0"
    loop.run()
    assert (
        dialog.current_scan_options == Profile()
    ), "current-scan-options unchanged if invalid option requested"
    assert callbacks == 1, "all callbacks executed"
    dialog.thread.quit()


def test_profile_unset(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    loop = mainloop_with_timeout()
    callbacks = 0
    dialog._add_profile("my profile", Profile(backend=[("resolution", 52)]))

    def changed_scan_option_cb(_widget, option, value, uuid):
        dialog.disconnect(dialog.option_signal)
        assert dialog.current_scan_options == Profile(
            backend=[("resolution", 52)]
        ), "current-scan-options"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    def changed_profile_cb(_widget, profile):
        dialog.disconnect(dialog.signal)
        assert profile == "my profile", "changed-profile"
        nonlocal callbacks
        callbacks += 1

    dialog.option_signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dialog.scan_options("test:0")
    loop.run()

    assert dialog.profile is None, "reloading scan options unsets profile"
    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()


def test_large_paper(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
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


def test_change_current_scan_option_signal(
    sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test basic functionality of scan dialog with sane backend"

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0

    def changed_current_scan_options_cb(_widget, profile, _uuid):
        nonlocal callbacks
        dialog.disconnect(dialog.signal)
        assert profile == Profile(
            backend=[("resolution", 51)]
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


def test_option_dependency(
    sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
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
            backend=[("mode", "Color")]
        ), "correctly set rest of profile"
        nonlocal callbacks
        callbacks += 1
        loop.quit()

    dialog.connect("process-error", process_error_cb)
    dialog.profile_signal = dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    assert callbacks == 1, "all callbacks executed"

    dialog.thread.quit()


def test_option_chains(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
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


def test_scan_pages(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """The test backend conveniently gives us
    Source = Automatic Document Feeder,
    which returns SANE_STATUS_NO_DOCS after the 10th scan.
    Test that we catch this.
    this should also unblock num-page to allow-batch-flatbed."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    n = 0
    loop = mainloop_with_timeout()

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1
        if pagenumber == 10:
            nonlocal callbacks
            callbacks += 1
        elif pagenumber > 10:
            assert False, "new-scan emitted 10 times"
            callbacks = 0
            loop.quit()

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            assert n == 10, "new-scan emitted 10 times"
            nonlocal callbacks
            callbacks += 1

    def changed_scan_option_cb(widget, option, value, _data):
        dialog.num_pages = 0
        dialog.scan()
        nonlocal callbacks
        callbacks += 1

    dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb)
    dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.set_option(
        dialog.available_scan_options.by_name("source"), "Automatic Document Feeder"
    )
    loop.run()

    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()


def test_scan_reverse_pages(
    sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    """The test backend conveniently gives us
    Source = Automatic Document Feeder,
    which returns SANE_STATUS_NO_DOCS after the 10th scan.
    Test that we catch this.
    this should also unblock num-page to allow-batch-flatbed."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    n = 0
    loop = mainloop_with_timeout()

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1
        if pagenumber == 2:
            nonlocal callbacks
            callbacks += 1
        elif pagenumber < 2:
            assert False, "new-scan emitted 10 times"
            callbacks = 0
            loop.quit()

    def changed_scan_option_cb(widget, option, value, _data):
        dialog.num_pages = 0
        dialog.page_number_increment = -2
        dialog.scan()
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            assert n == 10, "new-scan emitted 10 times"
            nonlocal callbacks
            callbacks += 1

    def error_process_cb(_widget, process):
        nonlocal callbacks
        callbacks = 0
        assert False, "Should not throw error"

    dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb)
    dialog.connect("process-error", error_process_cb)
    dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.side_to_scan = "reverse"
    dialog.page_number_start = 20
    dialog.max_pages = 10
    dialog.set_option(
        dialog.available_scan_options.by_name("source"), "Automatic Document Feeder"
    )
    loop.run()

    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()


def test_empty_device_list(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        nonlocal asserts
        asserts += 1
        return []

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    dlg = sane_scan_dialog

    def changed_device_list_cb(self, devices):
        assert devices == [], "changed-device-list called with empty array"
        nonlocal asserts
        asserts += 1

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()
    dlg.get_devices()

    loop.run()
    assert asserts == 2, "all callbacks runs"

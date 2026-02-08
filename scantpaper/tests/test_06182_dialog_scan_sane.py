"test scan dialog"

from types import SimpleNamespace
import logging
from frontend import enums
from scanner.options import Option
from scanner.profile import Profile

logger = logging.getLogger(__name__)


def test_impossible_options(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test ignoring options with impossible values"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        nonlocal asserts
        asserts += 1
        devices = [("mock_device", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(_self, _request):
        """option with min>max"""
        return [
            Option(
                index=0,
                name="",
                title="Number of options",
                desc="Read-only option that specifies how many options a specific device supports.",
                type=1,
                unit=0,
                size=4,
                cap=4,
                constraint=None,
            ),
            Option(
                name="brightness",
                title="Brightness",
                index=1,
                desc="Controls the brightness of the acquired image.",
                constraint=(0, -444909896, 32648),
                unit=0,
                type=enums.TYPE_INT,
                cap=37,
                size=1,
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    dlg = sane_scan_dialog

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        assert dlg.device_list == [
            SimpleNamespace(
                name="mock_device", vendor="", model="mock_device", label="mock_device"
            ),
        ], "successfully mocked getting device list"
        dlg.device = "mock_device"
        nonlocal asserts
        asserts += 1

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)
        nonlocal asserts
        asserts += 1

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert asserts == 3, "all callbacks runs"


def test_cancel_scan(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """Cancel the scan immediately after starting it and test that:
    a. the new-scan signal is not emitted.
    b. we can successfully scan afterwards."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    n = 0
    loop = mainloop_with_timeout()

    def started_process_cb(_widget, process):
        dialog.disconnect(dialog.start_signal)
        dialog.cancel_scan()
        nonlocal callbacks
        callbacks += 1

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            dialog.disconnect(dialog.new_signal)
            dialog.disconnect(dialog.finished_signal)
            assert n < 2, "Did not throw new-scan signal twice"
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.num_pages = 2
    dialog.start_signal = dialog.connect("started-process", started_process_cb)
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb)
    dialog.finished_signal = dialog.connect("finished-process", finished_process_cb)
    dialog.scan()
    loop.run()

    # On some scanners, cancel-between-pages options, which fixed
    # a problem where some brother scanners reported SANE_STATUS_NO_DOCS
    # despite using the flatbed, stopped the ADF from feeding more that 1
    # sheet. We can't test the fix directly, but at least make sure the code
    # is reached by piggybacking the next two lines."""
    loop = mainloop_with_timeout()

    def new_scan_cb2(_widget, _image_ob, _pagenumber, _xres, _yres):
        dialog.disconnect(dialog.new_signal)
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb2(_widget, process):
        if process == "scan_pages":
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.cancel_between_pages = True
    assert dialog.available_scan_options.flatbed_selected(
        dialog.thread.device_handle
    ), "flatbed selected"
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb2)
    dialog.connect("finished-process", finished_process_cb2)
    dialog.scan()
    loop.run()

    assert callbacks == 4, "all callbacks executed"

    dialog.thread.quit()


def test_option_dependency(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            cap=5,
            constraint=["Flatbed", "ADF", "Duplex"],
            desc="Selects the scan source (such as a document-feeder).",
            index=1,
            size=1,
            name="source",
            title="Scan source",
            type=3,
            unit=0,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Top Left X",
            index=2,
            size=1,
            name="tl-x",
            title="Top Left X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 296.925994873047, 0),
            desc="Top Left Y",
            index=3,
            size=1,
            name="tl-y",
            title="Top Left Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Bottom Right X",
            index=4,
            size=1,
            name="br-x",
            title="Bottom Right X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 296.925994873047, 0),
            desc="Bottom Right Y",
            index=5,
            size=1,
            name="br-y",
            title="Bottom Right Y",
            type=2,
            unit=3,
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Flatbed",
            resolution=75,
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        return raw_options

    def mocked_do_set_option(self, _request):
        "mocked_do_set_option"
        info = 0
        key, value = _request.args
        if key == "source" and value == "ADF":
            for i in [3, 5]:
                raw_options[i] = raw_options[i]._replace(constraint=(0, 800, 0))
            info = enums.INFO_RELOAD_OPTIONS
        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    dlg.paper_formats = {
        "US Legal": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 356.0},
        "US Letter": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 279.0},
    }
    assert dlg.ignored_paper_formats == ["US Legal"], "flatbed paper"

    def changed_scan_option_cb(self, option, value, uuid):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.ignored_paper_formats == [], "ADF paper"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    options = dlg.available_scan_options
    dlg.set_option(options.by_name("source"), "ADF")

    loop.run()

    assert asserts == 1, "all callbacks ran"


def test_unsetting_profile(
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


def test_restore_options_after_cycle(
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


def test_scanner_with_no_source(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test behavour with scanner without source option"

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            type=2,
            size=1,
            desc="Bottom-right y position of scan area. You should use it in "
            '"User defined" mode only!',
            index=14,
            constraint=(0, 355.599990844727, 0),
            name="br-y",
            cap=5,
            unit=3,
            title="br-y",
        ),
        Option(
            size=1,
            type=3,
            desc="Scan mode",
            index=2,
            name="mode",
            constraint=["Gray", "Color", "Black & White", "Error Diffusion", "ATEII"],
            cap=5,
            unit=0,
            title="Scan mode",
        ),
        Option(
            size=1,
            type=2,
            index=11,
            desc='Top-left x position of scan area. You should use it in "User defined" mode only!',
            name="tl-x",
            constraint=(0, 216, 0),
            title="tl-x",
            cap=5,
            unit=3,
        ),
        Option(
            name="resolution",
            constraint=[150, 200, 300, 400, 600],
            title="Scan resolution",
            cap=5,
            unit=4,
            type=1,
            size=1,
            desc="Scan resolution",
            index=3,
        ),
        Option(
            desc='Top-left y position of scan area. You should use it in "User defined" mode only!',
            index=12,
            type=2,
            size=1,
            title="tl-y",
            cap=5,
            unit=3,
            name="tl-y",
            constraint=(0, 355.599990844727, 0),
        ),
        Option(
            type=3,
            size=1,
            desc="scanmode,choose simplex or duplex scan",
            index=8,
            constraint=["Simplex", "Duplex"],
            name="ScanMode",
            title="ScanMode",
            cap=5,
            unit=0,
        ),
        Option(
            constraint=(0, 216, 0),
            name="br-x",
            unit=3,
            cap=5,
            title="br-x",
            type=2,
            size=1,
            desc="Bottom-right x position of scan area. You should use it in "
            '"User defined" mode only!',
            index=13,
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(self, _request):
        "mocked_do_get_options"
        self.device_handle = SimpleNamespace(
            mode="Gray",
            ScanMode="Simplex",
            resolution=150,
            tl_x=0,
            tl_y=0,
            br_x=216,
            br_y=355.599990844727,
        )
        return raw_options

    def mocked_do_set_option(_self, _request):
        "mocked_do_set_option"
        return 0

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_scan_option_cb(self, option, value, uuid):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.num_pages == 1, "num-pages reset to 1 because no source option"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    options = dlg.available_scan_options
    dlg.num_pages = 2
    dlg.set_option(options.by_name("ScanMode"), "Duplex")

    loop.run()

    assert asserts == 1, "all callbacks ran"


def test_defaults(
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


def test_hiding_geometry(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test behavour with scanner without source option"

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            type=2,
            size=1,
            desc="Bottom-right y position of scan area.",
            index=1,
            constraint=(0, 299.212005615234, 0),
            name="br-y",
            cap=5,
            unit=3,
            title="Bottom-right y",
        ),
        Option(
            size=1,
            type=2,
            index=2,
            desc="Top-left x position of scan area.",
            name="tl-x",
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            index=3,
            type=2,
            size=1,
            title="Top-left y",
            cap=5,
            unit=3,
            name="tl-y",
            constraint=(0, 299.212005615234, 0),
        ),
        Option(
            constraint=(0, 215.900009155273, 0),
            name="br-x",
            unit=3,
            cap=5,
            title="Bottom-right x",
            type=2,
            size=1,
            desc="Bottom-right x position of scan area.",
            index=4,
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(self, _request):
        "mocked_do_get_options"
        self.device_handle = SimpleNamespace(
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=299.212005615234,
        )
        return raw_options

    def mocked_do_set_option(_self, _request):
        "mocked_do_set_option"
        return 0

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")
    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_paper_formats(_widget, _formats):
        nonlocal callbacks
        callbacks += 1

    def changed_paper(_widget, paper):
        assert paper == "US Letter", "changed-paper"
        assert not dialog.option_widgets["tl-x"].is_visible(), "geometry hidden"
        assert (
            dialog.thread.device_handle.br_x == 215.900009155273
        ), "option value rounded down to max"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-paper-formats", changed_paper_formats)
    dialog.paper_formats = {
        "US Letter": {
            "l": 0,
            "y": 279,
            "x": 216,
            "t": 0,
        },
    }
    dialog.connect("changed-paper", changed_paper)
    dialog.paper = "US Letter"
    loop.run()

    assert callbacks == 2, "all callbacks ran"


def test_combobox_on_reload(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    """Check the scan options in a combobox are updated if necessary, if
    values are changed by a reload"""

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            index=1,
            name="source",
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            type=3,
            unit=0,
            size=1,
            cap=5,
            constraint=["Flatbed", "ADF", "Duplex"],
        ),
        Option(
            index=2,
            name="resolution",
            title="Scan resolution",
            desc="Sets the resolution of the scanned image.",
            type=1,
            unit=4,
            size=1,
            cap=5,
            constraint=[75, 100, 200, 300],
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(self, _request):
        "mocked_do_get_options"
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="Flatbed",
        )
        return raw_options

    def mocked_do_set_option(self, _request):
        "mocked_do_set_option"
        info = 0
        key, value = _request.args
        if key == "source" and value == "Flatbed":
            raw_options[2] = raw_options[2]._replace(
                constraint=[75, 100, 200, 300, 600, 1200]
            )
            info = enums.INFO_RELOAD_OPTIONS
        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")

    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_scan_option_cb(self, option, value, uuid):
        dialog.disconnect(dialog.signal)
        widget = self.option_widgets["resolution"]
        model = widget.get_model()
        resolutions = []
        for row in model:
            path, _itr = row
            resolutions.append(path)
        assert resolutions == [
            "75",
            "100",
            "200",
            "300",
            "600",
            "1200",
        ], "resolution widget updated"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.set_option(dialog.available_scan_options.by_name("source"), "Flatbed")
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb2(_self, _option, value, _uuid):
        dialog.disconnect(dialog.signal)
        assert value == 600, "resolution values updated"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb2)
    widget = dialog.option_widgets["resolution"]
    widget.set_active(4)
    loop.run()

    assert callbacks == 2, "all callbacks ran"

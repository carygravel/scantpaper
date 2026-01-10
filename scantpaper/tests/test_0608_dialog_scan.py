"test scan dialog"

from types import SimpleNamespace
from frontend import enums
from scanner.options import Option
from scanner.profile import Profile


def mocked_do_get_devices(_cls, _request):
    "mocked_do_get_devices"
    devices = [("mock_name", "", "", "")]
    return [
        SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1]) for x in devices
    ]


def trigger_get_devices(dlg, mainloop_with_timeout):
    "Trigger get_devices to cover mocked_do_get_devices"
    loop = mainloop_with_timeout()

    def reloaded_devices_cb(_arg1, _arg2):
        loop.quit()

    handler = dlg.connect("changed-device-list", reloaded_devices_cb)
    dlg.get_devices()
    loop.run()
    dlg.disconnect(handler)


def test_infinite_reloads(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """Force a reload for every option to trigger an infinite reload loop and test
        that the reload-recursion-limit is respected."""
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_formats = {"A4": {"x": 210, "y": 297, "t": 0, "l": 0}}

    def changed_paper_cb(_arg1, _arg2):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[("resolution", 100), ("source", "Flatbed")],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.num_reloads < 6, "finished reload loops without recursion limit"


def test_changed_profile(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """The changed-profile signal was being emitted too early, resulting in
        the profile dropdown being set to None"""
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    dlg._add_profile(
        "my profile", Profile(backend=[("resolution", 100), ("source", "Flatbed")])
    )
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_profile_cb(_widget, profile):
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert profile == "my profile", "changed-profile"
        assert dlg.current_scan_options == Profile(
            backend=[("resolution", 100), ("source", "Flatbed")],
        ), "current-scan-options with profile"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"

    loop.run()

    assert asserts == 1, "all callbacks ran"


def test_source_default(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(_self, _request):
        """An Acer flatbed scanner using a snapscan backend had no default for the source
        option, and as it only had one possibility, which was never set, the source
        option never had a value. Check that the number of pages frame is ghosted."""
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
                index=1,
                name="source",
                title="Scan source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=53,
                constraint=["Flatbed"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

    options = dlg.available_scan_options
    assert options.flatbed_selected(
        dlg.thread.device_handle
    ), "flatbed_selected() without value"
    assert not dlg.framen.is_sensitive(), "num-page gui ghosted"
    dlg.num_pages = 2
    assert dlg.num_pages == 1, "allow-batch-flatbed should force num-pages"
    dlg.allow_batch_flatbed = True
    dlg.num_pages = 2
    assert dlg.num_pages == 2, "num-pages"
    assert dlg.framen.is_sensitive(), "num-page gui not ghosted"

    loop.run()


def test_more_profiles(sane_scan_dialog, mainloop_with_timeout):
    "Check options are reset before applying a profile"

    dlg = sane_scan_dialog
    dlg._add_profile("my profile", Profile(backend=[("resolution", 100)]))
    loop = mainloop_with_timeout()
    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.device = "test"
    dlg.scan_options()
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb(_arg, _arg2, _arg3, _arg4):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    dlg.set_option(dlg.available_scan_options.by_name("tl-x"), 10)
    loop.run()

    loop = mainloop_with_timeout()

    def changed_profile_cb(widget, profile):
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert dlg.current_scan_options == Profile(
            backend=[("resolution", 100)]
        ), "reset before applying profile"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"
    loop.run()

    assert asserts == 1, "all callbacks ran"
    dlg.thread.quit()


def test_inexact_quant(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.87219238281,
            br_y=279.364013671875,
            swcrop=False,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.87219238281, 0.0211639404296875),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 279.364013671875, 0.0211639404296875),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.87219238281, 0.0211639404296875),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 279.364013671875, 0.0211639404296875),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
        Option(
            unit=0,
            name="swcrop",
            type=0,
            index=7,
            cap=69,
            size=1,
            desc="Request driver to remove border from pages digitally.",
            title="Software crop",
            constraint=None,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """Reload if inexact due to quant > 0 to test that this doesn't trigger an
        infinite reload loop."""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break
        info = 0
        if isinstance(opt.constraint, tuple) and opt.constraint[2] > 0:
            value = int(value / opt.constraint[2] + 0.5) * opt.constraint[2]
            info = enums.INFO_RELOAD_OPTIONS
        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    # Use a paper that sets geometry to inexact values
    dlg.paper_formats = {"A4": {"x": 210.1, "y": 279.1, "t": 0.1, "l": 0.1}}

    def changed_paper_cb(_arg1, _arg2):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[
                ("resolution", 100),
                ("source", "Flatbed"),
                ("swcrop", False),
            ],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.num_reloads < 6, "finished reload loops without recursion limit"


def test_button_press(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            tl_x=0,
            tl_y=0,
            br_x=216.699996948242,
            br_y=300.0,
            clear_calibration=None,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[4800, 2400, 1200, 600, 300, 150, 100, 75],
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 216.699996948242, 0.0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=4,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=5,
            name="tl-y",
            size=1,
            constraint=(0, 300.0, 0.0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 216.699996948242, 0.0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=6,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 300.0, 0.0),
            index=7,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
        Option(
            unit=0,
            name="clear-calibration",
            type=4,
            index=8,
            cap=5,
            size=1,
            desc="Clear calibration cache",
            title="Clear calibration",
            constraint=None,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """Reload clear-calibration button pressed to test that this doesn't trigger an
        infinite reload loop."""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break
        info = 0
        if key == "clear-calibration":
            info = enums.INFO_RELOAD_OPTIONS
        else:
            setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_formats = {"A4": {"x": 210, "y": 279, "t": 0, "l": 0}}
    asserts = 0

    def changed_paper_cb(_arg1, _arg2):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("resolution", 100),
                ("clear-calibration", None),
                ("br-x", 210.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "A4"},
        ), "all options applied"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[
                ("resolution", 100),
                ("clear-calibration", None),
                ("br-x", 210.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.num_reloads < 6, "finished reload loops without recursion limit"
    assert asserts == 1, "ran all callbacks"


def test_get_invalid_option(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    """test getting an invalid option (gscan2pdf bug #313).
    scanimage was segfaulting when retrieving the options from a Brother
    ADS-2800W via --help. xsane and simplescan worked.

    gscan2pdf tested this with 06092_dialog_scan, but without a load of
    debugging help from someone with access to a similar scanner, it is
    hard to predict how the python sane module would react, so skipping
    this until we have a problem to reproduce."""

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
        Option(
            cap=enums.CAP_SOFT_SELECT + enums.CAP_SOFT_DETECT,
            name=None,  # "select-detect"
            title=None,
            desc=None,
            constraint=None,
            size=1,
            type=enums.TYPE_BOOL,
            unit=None,
            index=7,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """The changed-profile signal was being emitted too early, resulting in
        the profile dropdown being set to None"""
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")

    assert dlg.available_scan_options.by_index(7) == Option(
        cap=0,
        name=None,  # "select-detect"
        title=None,
        desc=None,
        constraint=None,
        size=1,
        type=enums.TYPE_BOOL,
        unit=None,
        index=7,
    ), "make options that throw an error undetectable and unselectable"

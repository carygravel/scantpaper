"test scan dialog"

from types import SimpleNamespace
import logging
from scanner.options import Option
from scanner.profile import Profile
from frontend.image_sane import decode_info
from frontend import enums

logger = logging.getLogger(__name__)


def test_infinite_reloads_due_to_tolerance(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Document Table",
            enable_resampling=None,
            resolution=75,
            resolution_bind=True,
            x_resolution=75,
            y_resolution=75,
            scan_area="Manual",
            mode="Color",
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
            rotate="0 degrees",
            blank_threshold=0,
            brightness=0,
            contrast=0,
            threshold=128,
            gamma="1.8",
            image_count=None,
            jpeg_quality=90,
            transfer_format="RAW",
            transfer_size=1048576,
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
            cap=5,
            constraint=["ADF", "Document Table"],
            desc="Document Source",
            index=1,
            size=1,
            name="source",
            title="Document Source",
            type=3,
            unit=0,
        ),
        Option(
            cap=100,
            desc="This option provides the user with a wider range of supported"
            " resolutions.  Resolutions not supported by the hardware will"
            " be achieved through image processing methods.",
            index=2,
            size=1,
            name="enable-resampling",
            title="Enable Resampling",
            type=0,
            unit=0,
            constraint=None,
        ),
        Option(
            cap=5,
            constraint=(50, 1200, 0),
            desc="Resolution",
            index=4,
            size=1,
            name="resolution",
            title="Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=69,
            desc="Bind X and Y resolutions",
            index=5,
            size=1,
            name="resolution-bind",
            title="Bind X and Y resolutions",
            type=0,
            unit=0,
            constraint=None,
        ),
        Option(
            cap=68,
            constraint=(50, 1200, 0),
            desc="X Resolution",
            index=6,
            size=1,
            name="x-resolution",
            title="X Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=68,
            constraint=(50, 1200, 0),
            desc="Y Resolution",
            index=7,
            size=1,
            name="y-resolution",
            title="Y Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=5,
            constraint=[
                "Executive/Portrait",
                "ISO/A4/Portrait",
                "ISO/A5/Portrait",
                "ISO/A5/Landscape",
                "ISO/A6/Portrait",
                "ISO/A6/Landscape",
                "JIS/B5/Portrait",
                "JIS/B6/Portrait",
                "JIS/B6/Landscape",
                "Letter/Portrait",
                "Manual",
                "Maximum",
            ],
            desc="Scan Area",
            index=8,
            size=1,
            name="scan-area",
            title="Scan Area",
            type=3,
            unit=0,
        ),
        Option(
            cap=13,
            constraint=["Monochrome", "Grayscale", "Color"],
            desc="Image Type",
            index=9,
            size=1,
            name="mode",
            title="Image Type",
            type=3,
            unit=0,
        ),
        Option(
            cap=32,
            desc="Scan area and image size related options.",
            index=10,
            size=0,
            name="device-03-geometry",
            title="Geometry",
            type=5,
            unit=0,
            constraint=None,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Bottom Right X",
            index=11,
            size=1,
            name="br-x",
            title="Bottom Right X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Bottom Right Y",
            index=12,
            size=1,
            name="br-y",
            title="Bottom Right Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Top Left X",
            index=13,
            size=1,
            name="tl-x",
            title="Top Left X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Top Left Y",
            index=14,
            size=1,
            name="tl-y",
            title="Top Left Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=32,
            desc="Image modification options.",
            index=15,
            size=0,
            name="device-04-enhancement",
            title="Enhancement",
            type=5,
            unit=0,
            constraint=None,
        ),
        Option(
            cap=13,
            constraint=[
                "0 degrees",
                "90 degrees",
                "180 degrees",
                "270 degrees",
                "Auto",
            ],
            desc="Rotate",
            index=16,
            size=1,
            name="rotate",
            title="Rotate",
            type=3,
            unit=0,
        ),
        Option(
            cap=13,
            constraint=(0, 100, 0),
            desc="Skip Blank Pages Settings",
            index=17,
            size=1,
            name="blank-threshold",
            title="Skip Blank Pages Settings",
            type=2,
            unit=0,
        ),
        Option(
            cap=13,
            constraint=(-100, 100, 0),
            desc="Change brightness of the acquired image.",
            index=18,
            size=1,
            name="brightness",
            title="Brightness",
            type=1,
            unit=0,
        ),
        Option(
            cap=13,
            constraint=(-100, 100, 0),
            desc="Change contrast of the acquired image.",
            index=19,
            size=1,
            name="contrast",
            title="Contrast",
            type=1,
            unit=0,
        ),
        Option(
            cap=13,
            constraint=(0, 255, 0),
            desc="Threshold",
            index=20,
            size=1,
            name="threshold",
            title="Threshold",
            type=1,
            unit=0,
        ),
        Option(
            cap=32,
            desc="",
            index=21,
            size=0,
            name="device--",
            title="Other",
            type=5,
            unit=0,
            constraint=None,
        ),
        Option(
            cap=69,
            constraint=["1.0", "1.8"],
            desc="Gamma",
            index=22,
            size=1,
            name="gamma",
            title="Gamma",
            type=3,
            unit=0,
        ),
        Option(
            cap=101,
            constraint=(0, 999, 0),
            desc="Image Count",
            index=23,
            size=1,
            name="image-count",
            title="Image Count",
            type=1,
            unit=0,
        ),
        Option(
            cap=69,
            constraint=(1, 100, 0),
            desc="JPEG Quality",
            index=24,
            size=1,
            name="jpeg-quality",
            title="JPEG Quality",
            type=1,
            unit=0,
        ),
        Option(
            cap=5,
            constraint=["JPEG", "RAW"],
            desc="Selecting a compressed format such as JPEG normally results "
            "in faster device side processing.",
            index=25,
            size=1,
            name="transfer-format",
            title="Transfer Format",
            type=3,
            unit=0,
        ),
        Option(
            cap=69,
            constraint=(1, 268435455, 0),
            desc="Transfer Size",
            index=26,
            size=1,
            name="transfer-size",
            title="Transfer Size",
            type=1,
            unit=0,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """An Epson ET-4750 was triggering a reload on setting br-x and -y,
        and the reloaded values were outside the tolerance.
        Ensure that the reload limit is not hit"""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break

        info = 0
        if key == "br-x" and value == 216 or key == "br-y" and value == 279:
            value = 215.899993896484 if key == "br-x" else 279.399993896484
            info = (
                21936
                + enums.INFO_RELOAD_PARAMS
                + enums.INFO_RELOAD_OPTIONS
                + enums.INFO_INEXACT
            )
            logger.info(
                f"sane_set_option {opt.index} ({opt.name})"
                + f" to {value} returned info "
                + f"{info} ({decode_info(info)})"
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg._add_profile(
        "my profile",
        Profile(
            backend=[
                ("scan-area", "Letter/Portrait"),
                ("br-x", 216),
                ("br-y", 279),
            ]
        ),
    )
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_profile_cb(_widget, profile):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert profile == "my profile", "changed-profile"
        assert dlg.current_scan_options == Profile(
            backend=[
                ("scan-area", "Letter/Portrait"),
                ("br-x", 215.899993896484),
                ("br-y", 279.0),
            ],
        ), "current-scan-options with profile"
        assert dlg.thread.device_handle.br_x == 215.899993896484, "br-x value"
        assert dlg.thread.device_handle.br_y == 279.399993896484, "br-y value"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"

    loop.run()

    assert dlg.num_reloads < 5, "didn't hit reload recursion limit"
    assert asserts == 1, "all callbacks ran"


def test_inexact(
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
            constraint=["ADF", "Document Table"],
            desc="Document Source",
            index=1,
            size=1,
            name="source",
            title="Document Source",
            type=3,
            unit=0,
        ),
        Option(
            cap=5,
            constraint=(50, 1200, 0),
            desc="Resolution",
            index=4,
            size=1,
            name="resolution",
            title="Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=5,
            constraint=(0, 356.0, 0),
            desc="Bottom Right X",
            index=11,
            size=1,
            name="br-x",
            title="Bottom Right X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 356.0, 0),
            desc="Bottom Right Y",
            index=12,
            size=1,
            name="br-y",
            title="Bottom Right Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Top Left X",
            index=13,
            size=1,
            name="tl-x",
            title="Top Left X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Top Left Y",
            index=14,
            size=1,
            name="tl-y",
            title="Top Left Y",
            type=2,
            unit=3,
        ),
    ]

    def mocked_do_get_devices(_cls, _request):
        "mock for do_get_devices"
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Document Table",
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
        """A fujitsu:fi-4220C2dj was ignoring paper change requests because setting
        initial geometry set INFO_INEXACT"""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break

        info = 0
        if key in ["br-x", "br-y", "tl-x", "tl-y"]:
            info = enums.INFO_RELOAD_PARAMS + enums.INFO_INEXACT
            value -= 0.5

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)
    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg.paper_formats = {
        "US Legal": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 356.0},
        "US Letter": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 279.0},
    }
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_paper_cb(_widget, _paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("br-x", 216.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "US Letter"},
        ), "set first paper"
        assert dlg.thread.device_handle.br_x == 215.5, "br-x value"
        assert dlg.thread.device_handle.br_y == 278.5, "br-y value"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(Profile(frontend={"paper": "US Letter"}))

    loop.run()

    loop = mainloop_with_timeout()

    def changed_paper_cb2(_widget, _paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("br-x", 216.0),
                ("br-y", 356.0),
            ],
            frontend={"paper": "US Legal"},
        ), "set second paper after SANE_INFO_INEXACT"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb2)
    dlg.set_current_scan_options(Profile(frontend={"paper": "US Legal"}))
    loop.run()

    assert asserts == 2, "all callbacks ran"


def test_infinite_reloads_due_to_inexact(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Document Table",
            resolution=75,
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
            cct_1=1.07818603515625,
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
            cap=5,
            constraint=["ADF", "Document Table"],
            desc="Document Source",
            index=1,
            size=1,
            name="source",
            title="Document Source",
            type=3,
            unit=0,
        ),
        Option(
            cap=5,
            constraint=(50, 1200, 0),
            desc="Resolution",
            index=4,
            size=1,
            name="resolution",
            title="Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Bottom Right X",
            index=11,
            size=1,
            name="br-x",
            title="Bottom Right X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Bottom Right Y",
            index=12,
            size=1,
            name="br-y",
            title="Bottom Right Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Top Left X",
            index=13,
            size=1,
            name="tl-x",
            title="Top Left X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Top Left Y",
            index=14,
            size=1,
            name="tl-y",
            title="Top Left Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=69,
            constraint=None,
            desc="",
            index=15,
            size=1,
            name="cct-1",
            title="",
            type=2,
            unit=0,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """An EPSON DS-1660W was setting tl-y=0.99 instead of 1, but not
        setting SANE_INFO_INEXACT, which was hitting the
        reload-recursion-limit."""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break

        info = 0
        if key in ["br-x", "br-y", "tl-x", "tl-y"]:
            info = 21870
            if value == 1:
                value = 0.999984741210938
            logger.info(
                f"sane_set_option {opt.index} ({opt.name})"
                + f" to {value} returned info "
                + f"{info} ({decode_info(info)})"
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg.paper_formats = {"new": {"l": 0.0, "t": 1.0, "x": 10.0, "y": 10.0}}
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_paper_cb(_widget, paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("tl-y", 1.0),
                ("br-x", 10.0),
                ("br-y", 11.0),
            ],
            frontend={"paper": "new"},
        ), "set inexact paper without SANE_INFO_INEXACT"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(Profile(frontend={"paper": "new"}))

    loop.run()

    assert asserts == 1, "all callbacks ran"

    # EPSON DS-1660W calls the flatbed a document table
    options = dlg.available_scan_options
    assert options.flatbed_selected(
        dlg.thread.device_handle
    ), "Document Table means flatbed"

    # as cct-1 does not have a title, test for label text
    assert (
        dlg._get_label_for_option("cct-1") == "cct-1"
    ), "text for option with no title"

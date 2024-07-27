"test scan dialog"

from types import SimpleNamespace
import logging
from scanner.options import Option
from scanner.profile import Profile
from frontend import enums

logger = logging.getLogger(__name__)

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
        name="brightness",
        title="Brightness",
        desc="Controls the brightness of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 1),
    ),
    Option(
        index=2,
        name="contrast",
        title="Contrast",
        desc="Controls the contrast of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 1),
    ),
    Option(
        index=3,
        name="resolution",
        title="Scan resolution",
        desc="Sets the resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=5,
        constraint=[600],
    ),
    Option(
        index=4,
        name="x-resolution",
        title="X-resolution",
        desc="Sets the horizontal resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=69,
        constraint=[150, 225, 300, 600, 900, 1200],
    ),
    Option(
        index=5,
        name="y-resolution",
        title="Y-resolution",
        desc="Sets the vertical resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=69,
        constraint=[150, 225, 300, 600, 900, 1200, 1800, 2400],
    ),
    Option(
        index=6,
        name="",
        title="Geometry",
        desc="",
        type=5,
        unit=0,
        size=1,
        cap=64,
        constraint=None,
    ),
    Option(
        index=7,
        name="scan-area",
        title="Scan area",
        desc="Select an area to scan based on well-known media sizes.",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=[
            "Maximum",
            "A4",
            "A5 Landscape",
            "A5 Portrait",
            "B5",
            "Letter",
            "Executive",
            "CD",
        ],
    ),
    Option(
        size=1,
        type=2,
        index=8,
        desc="Top-left x position of scan area.",
        name="tl-x",
        constraint=(0, 215.899993896484, 0),
        title="Top-left x",
        cap=5,
        unit=3,
    ),
    Option(
        desc="Top-left y position of scan area.",
        index=9,
        type=2,
        size=1,
        title="Top-left y",
        cap=5,
        unit=3,
        name="tl-y",
        constraint=(0, 297.179992675781, 0),
    ),
    Option(
        constraint=(0, 215.899993896484, 0),
        name="br-x",
        unit=3,
        cap=5,
        title="Bottom-right x",
        type=2,
        size=1,
        desc="Bottom-right x position of scan area.",
        index=10,
    ),
    Option(
        type=2,
        size=1,
        desc="Bottom-right y position of scan area.",
        index=11,
        constraint=(0, 297.179992675781, 0),
        name="br-y",
        cap=5,
        unit=3,
        title="Bottom-right y",
    ),
    Option(
        index=12,
        name="source",
        title="Scan source",
        desc="Selects the scan source (such as a document-feeder).",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=["Flatbed", "Automatic Document Feeder"],
    ),
]


def mocked_do_get_devices(_cls, _request):
    "mock for do_get_devices"
    devices = [("mock_name", "", "", "")]
    return [
        SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1]) for x in devices
    ]


def mocked_do_open_device(self, request):
    "open device"
    device_name = request.args[0]
    self.device = device_name
    request.data(f"opened device '{self.device_name}'")


def mocked_do_get_options(self, _request):
    "mocked_do_get_options"
    self.device_handle = SimpleNamespace(
        brightness=0,
        contrast=0,
        resolution=600,
        x_resolution=300,
        y_resolution=300,
        scan_area="Maximum",
        tl_x=0,
        tl_y=0,
        br_x=215.899993896484,
        br_y=297.179992675781,
        source="Flatbed",
    )
    return raw_options


def mocked_do_set_option(self, _request):
    "mocked_do_set_option"
    info = 0
    key, value = _request.args
    if key == "source" and value == "Automatic Document Feeder":
        raw_options[10] = raw_options[10]._replace(constraint=(0, 215.899993896484, 0))
        setattr(self.device_handle, "br_x", 215.899993896484)
        raw_options[11] = raw_options[11]._replace(constraint=(0, 355.599990844727, 0))
        setattr(self.device_handle, "br_y", 355.599990844727)
        info = enums.INFO_RELOAD_OPTIONS
    elif key in ["x_resolution", "y_resolution", "scan_area"]:
        info = enums.INFO_RELOAD_OPTIONS
    setattr(self.device_handle, key.replace("-", "_"), value)
    return info


def test_reloads_in_profile(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    """Given a profile of scan options that trigger multiple reloads, check
    the changed-profile signal is only emitted once"""

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)
    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")
    callbacks = 0
    loop = mainloop_with_timeout()

    def added_profile_cb(_widget, name, profile):
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
        print(f"dialog.current_scan_options {dialog.current_scan_options}")
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

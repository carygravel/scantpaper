"test scan dialog"

from types import SimpleNamespace
import logging
import pytest
from PIL import Image
from scanner.options import Option
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
    setattr(self.device_handle, key.replace("-", "_"), value)
    return info


def mocked_do_scan_page(self, _request):
    "mocked_do_scan_page page"
    if self.device_handle is None:
        raise ValueError("must open device before starting scan")
    return Image.new("1", (100, 100))


def test_scan_resolution(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    mainloop_with_timeout,
    set_option_in_mainloop,
):
    """Test the resolution options passed with the new-scan signal"""

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    mocker.patch("dialog.sane.SaneThread.do_scan_page", mocked_do_scan_page)
    dialog = sane_scan_dialog
    callbacks = 0
    set_device_wait_reload(dialog, "mock_name")
    loop = mainloop_with_timeout()

    def new_scan_cb(_widget, _image_ob, _pagenumber, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 300, "x-resolution defaults"
        assert yres == 300, "y-resolution defaults"
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.num_pages = 1
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb)
    dialog.scan()
    loop.run()

    # wait for resolution option to propagate to current-scan-options before
    # scanning
    assert set_option_in_mainloop(dialog, "resolution", 600), "set resolution"

    loop = mainloop_with_timeout()

    def new_scan_cb2(_widget, _image_ob, _pagenumber, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 600, "x-resolution from resolution option"
        assert yres == 600, "y-resolution from resolution option"
        nonlocal callbacks
        callbacks += 1

    dialog.new_signal = dialog.connect("new-scan", new_scan_cb2)
    dialog.scan()
    loop.run()

    # wait for resolution option to propagate to current-scan-options before
    # scanning
    assert set_option_in_mainloop(dialog, "x-resolution", 150), "set x-resolution"

    loop = mainloop_with_timeout()

    def new_scan_cb3(_widget, _image_ob, _pagenumber, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 150, "x-resolution from x-resolution option"
        assert yres == 600, "y-resolution from resolution option"
        nonlocal callbacks
        callbacks += 1

    dialog.new_signal = dialog.connect("new-scan", new_scan_cb3)
    dialog.scan()
    loop.run()

    assert callbacks == 6, "changed-profile only called once"


def test_scan_source_adf(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    set_option_in_mainloop,
):
    """Test setting source to ADF triggers reload options"""

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    mocker.patch("dialog.sane.SaneThread.do_scan_page", mocked_do_scan_page)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")

    # This should trigger the first if branch in mocked_do_set_option
    assert set_option_in_mainloop(
        dialog, "source", "Automatic Document Feeder"
    ), "set source to ADF"


def test_scan_page_no_device():
    """Test scanning without device raises ValueError"""
    with pytest.raises(ValueError, match="must open device before starting scan"):
        mocked_do_scan_page(SimpleNamespace(device_handle=None), None)

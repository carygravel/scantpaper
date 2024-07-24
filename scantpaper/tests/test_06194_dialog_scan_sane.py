"test scan dialog"

from types import SimpleNamespace
import logging
from scanner.options import Option

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
        type=2,
        size=1,
        desc='Bottom-right y position of scan area. You should use it in "User defined" mode only!',
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
        desc='Bottom-right x position of scan area. You should use it in "User defined" mode only!',
        index=13,
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


def test_scanner_with_no_source(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test behavour with scanner without source option"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)
    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        dlg.device = "mock_name"

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()
    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)
        nonlocal asserts

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
        asserts += 1

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()
    loop.run()

    assert asserts == 2, "all callbacks ran"

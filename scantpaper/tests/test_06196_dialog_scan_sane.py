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
        tl_x=0,
        tl_y=0,
        br_x=215.900009155273,
        br_y=299.212005615234,
    )
    return raw_options


def mocked_do_set_option(_self, _request):
    "mocked_do_set_option"
    return 0


def test_hiding_geometry(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test behavour with scanner without source option"

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)
    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    dialog = sane_scan_dialog
    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_device_list_cb(_arg1, arg2):
        dialog.disconnect(dialog.signal)
        dialog.device = "mock_name"
        nonlocal callbacks
        callbacks += 1

    def reloaded_scan_options_cb(_arg):
        dialog.disconnect(dialog.reloaded_signal)
        dialog.paper = "US Letter"
        nonlocal callbacks
        callbacks += 1

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

    dialog.signal = dialog.connect("changed-device-list", changed_device_list_cb)
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
    dialog.reloaded_signal = dialog.connect(
        "reloaded-scan-options", reloaded_scan_options_cb
    )
    dialog.get_devices()
    loop.run()

    assert callbacks == 4, "all callbacks ran"

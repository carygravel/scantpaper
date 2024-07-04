"test scan dialog"

from types import SimpleNamespace
import logging
import gi
from dialog.sane import SaneScanDialog
from scanner.options import Option
from scanner.profile import Profile
from frontend.image_sane import decode_info
from frontend import enums

logger = logging.getLogger(__name__)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position

TIMEOUT = 10000


def test_1(mocker):
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

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

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
            logger.info(
                f"sane_set_option {opt.index} ({opt.name})"
                + f" to {value} returned info "
                + f"{info} ({decode_info(info)})"
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )

    dlg.paper_formats = {
        "US Legal": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 356.0},
        "US Letter": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 279.0},
    }

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        dlg.device = "mock_name"

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)

    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)
        nonlocal asserts

        def changed_paper_cb(_widget, paper):
            dlg.disconnect(dlg.signal)
            nonlocal asserts
            assert dlg.current_scan_options == Profile(
                backend=[
                    ("br-x", 216.0),
                    ("br-y", 279.0),
                ],
                frontend={"num_pages": 1, "paper": "US Letter"},
            ), "set first paper"
            assert dlg.thread.device_handle.br_x == 215.5, "br-x value"
            assert dlg.thread.device_handle.br_y == 278.5, "br-y value"
            asserts += 1
            loop.quit()

        dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
        dlg.set_current_scan_options(Profile(frontend={"paper": "US Letter"}))
        asserts += 1

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()
    loop.run()

    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    def changed_paper_cb(_widget, paper):
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

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(Profile(frontend={"paper": "US Legal"}))
    loop.run()

    assert asserts == 3, "all callbacks ran"

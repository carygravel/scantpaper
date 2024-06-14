"test scan dialog"

from types import SimpleNamespace
import gi
from dialog.sane import SaneScanDialog
from scanner.options import Option
from scanner.profile import Profile
import sane

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
            index=1,
            name="resolution",
            title="Scan resolution",
            desc="Sets the resolution of the scanned image.",
            type=1,
            unit=4,
            size=4,
            cap=5,
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
        """An Officejet_4620_series was resetting the resolution and geometry when
        changing from ADF to Flatbed. Ensure that valid parts of the current profile
        are still active (updating if necessary) after changing an option that forces
        a reload."""
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        info = 0
        if key == "source" and value in "Flatbed":
            raw_options[1] = Option(
                index=1,
                name="resolution",
                title="Scan resolution",
                desc="Sets the resolution of the scanned image.",
                type=1,
                unit=4,
                size=4,
                cap=5,
                constraint=[75, 100, 200, 300, 600, 1200],
            )
            self.device_handle.resolution = 75
            self.device_handle.br_x = 215.900009155273
            info = sane._sane.INFO_RELOAD_OPTIONS

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        dlg.device = "mock_name"

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)

    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    dlg.paper_formats = {"A4": {"x": 210, "y": 297, "t": 0, "l": 0}}

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)

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

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert dlg.thread.device_handle.resolution == 100, "reset resolution"
    assert dlg.thread.device_handle.br_x == 210, "reset br-x"
    assert dlg.paper == "A4", "reset paper"

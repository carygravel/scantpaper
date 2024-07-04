"test scan dialog"

from types import SimpleNamespace
import gi
from dialog.sane import SaneScanDialog
from scanner.options import Option

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position

TIMEOUT = 10000


def test_1(mocker):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        nonlocal asserts
        asserts += 1
        devices = [("mock_name", "", "", "")]
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

    dlg = SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )

    def changed_device_list_cb(_arg1, arg2):
        nonlocal asserts
        asserts += 1
        dlg.disconnect(dlg.signal)
        dlg.device = "mock_name"

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)

    loop = GLib.MainLoop()
    GLib.timeout_add(TIMEOUT, loop.quit)  # to prevent it hanging

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)
        nonlocal asserts

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
        asserts += 1

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert asserts == 3, "all callbacks runs"

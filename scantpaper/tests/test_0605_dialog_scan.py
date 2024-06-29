"test scan dialog"

from types import SimpleNamespace
import gi
from dialog.sane import SaneScanDialog
from scanner.options import Option
from scanner.profile import Profile

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

    def mocked_do_get_options(self, _request):
        """A Samsung CLX-4190 has a doc-source options instead of source, meaning that
        the property allow-batch-flatbed had to be enabled to scan more than one
        page from the ADF. Override enough to test for this."""
        self.device_handle.doc_source = "Auto"
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
                name="doc-source",
                title="Doc source",
                desc="Selects source of the document to be scanned",
                type=3,
                unit=0,
                size=1,
                cap=5,
                constraint=["Auto", "Flatbed", "ADF Simplex"],
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
        asserts += 1

        def changed_current_scan_options_cb(_arg1, _arg2, _arg3):
            nonlocal asserts
            dlg.disconnect(dlg.signal)
            assert dlg.num_pages == 0, "num-pages"
            asserts += 1
            loop.quit()

        dlg.signal = dlg.connect(
            "changed-current-scan-options", changed_current_scan_options_cb
        )
        dlg.set_current_scan_options(Profile(frontend={"num_pages": 0}))

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert asserts == 4, "all callbacks runs"

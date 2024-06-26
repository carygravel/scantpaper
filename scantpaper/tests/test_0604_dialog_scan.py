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
        nonlocal asserts
        asserts += 1
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(self, _request):
        """A Canon Lide 220 was producing scanimage output without a val for source,
        producing the error: Use of uninitialized value in pattern match (m//)
        when loading the options. Override enough to test for this."""
        nonlocal asserts
        asserts += 1
        self.device_handle.source = None
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
                name="",
                title="Scan mode",
                desc="",
                type=5,
                unit=0,
                size=1,
                cap=0,
                constraint=None,
            ),
            Option(
                index=2,
                name="source",
                title="Source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=37,
                constraint=["Flatbed", "Transparency Adapter"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return 0

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

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

        def changed_scan_option_cb(_widget, _option, _value, _uuid):
            nonlocal asserts
            asserts += 1
            loop.quit()

        dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
        options = dlg.available_scan_options
        dlg.set_option(options.by_name("source"), "Flatbed")

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert asserts == 6, "all callbacks runs"

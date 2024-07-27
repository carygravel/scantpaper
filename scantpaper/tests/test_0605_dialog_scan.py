"test scan dialog"

from types import SimpleNamespace
from scanner.options import Option
from scanner.profile import Profile


def test_1(mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

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

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

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

    loop.run()
    assert asserts == 1, "all callbacks runs"

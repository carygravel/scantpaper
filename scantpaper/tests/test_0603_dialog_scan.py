"test scan dialog"

from types import SimpleNamespace
from scanner.options import Option


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
        """Options with opt.type == SANE_TYPE_GROUP don't necessarily then have
        opt.name defined, which was triggering an error
        when reloading the options. Override enough to test for this."""
        nonlocal asserts
        asserts += 1
        self.device_handle.source = "Auto"
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
                title="Scan source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=69,
                constraint=["Auto", "Flatbed", "ADF"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return 0

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

    def changed_scan_option_cb(_widget, _option, _value, _uuid):
        nonlocal asserts
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    options = dlg.available_scan_options
    dlg.set_option(options.by_name("source"), "ADF")

    loop.run()
    assert asserts == 2, "all callbacks runs"

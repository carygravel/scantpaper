"test scan dialog"

from types import SimpleNamespace
from scanner.options import Option
from frontend import enums


def test_1(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test ignoring options with impossible values"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        nonlocal asserts
        asserts += 1
        devices = [("mock_device", "", "", "")]
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
        """option with min>max"""
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
                name="brightness",
                title="Brightness",
                index=1,
                desc="Controls the brightness of the acquired image.",
                constraint=(0, -444909896, 32648),
                unit=0,
                type=enums.TYPE_INT,
                cap=37,
                size=1,
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    dlg = sane_scan_dialog

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        assert dlg.device_list == [
            SimpleNamespace(
                name="mock_device", vendor="", model="mock_device", label="mock_device"
            ),
        ], "successfully mocked getting device list"
        dlg.device = "mock_device"
        nonlocal asserts
        asserts += 1

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)
        nonlocal asserts
        asserts += 1

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()
    assert asserts == 3, "all callbacks runs"

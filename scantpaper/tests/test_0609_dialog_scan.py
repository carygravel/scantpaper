"test scan dialog"

from types import SimpleNamespace
from scanner.options import Option
from scanner.profile import Profile
from frontend import enums


def test_1(mocker, sane_scan_dialog, mainloop_with_timeout):
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
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
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
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """The changed-profile signal was being emitted too early, resulting in
        the profile dropdown being set to None"""
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg._add_profile(
        "my profile", Profile(backend=[("resolution", 100), ("source", "Flatbed")])
    )

    def changed_device_list_cb(_arg1, arg2):
        dlg.disconnect(dlg.signal)
        dlg.device = "mock_name"

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()
    asserts = 0

    def reloaded_scan_options_cb(_arg):
        dlg.disconnect(dlg.reloaded_signal)

        def changed_profile_cb(_widget, profile):
            nonlocal asserts
            dlg.disconnect(dlg.signal)
            assert profile == "my profile", "changed-profile"
            assert dlg.current_scan_options == Profile(
                backend=[("resolution", 100), ("source", "Flatbed")],
            ), "current-scan-options with profile"
            asserts += 1
            loop.quit()

        dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
        dlg.profile = "my profile"

    dlg.reloaded_signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.get_devices()

    loop.run()

    assert asserts == 1, "all callbacks ran"

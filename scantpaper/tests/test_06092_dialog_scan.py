"test scan dialog"

from types import SimpleNamespace
from scanner.options import Option
from frontend import enums
import pytest


@pytest.mark.skip("not sure how to mock the backend behaviour")
def test_get_invalid_option(mocker, sane_scan_dialog, set_device_wait_reload):
    """test getting an invalid option (gscan2pdf bug #313).
    scanimage was segfaulting when retrieving the options from a Brother
    ADS-2800W via --help. xsane and simplescan worked.

    gscan2pdf tested this with 06092_dialog_scan, but without a load of
    debugging help from someone with access to a similar scanner, it is
    hard to predict how the python sane module would react, so skipping
    this until we have a problem to reproduce."""

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
        Option(
            cap=enums.CAP_SOFT_SELECT + enums.CAP_SOFT_DETECT,
            name=None,  # "select-detect"
            title=None,
            desc=None,
            constraint=None,
            size=1,
            type=enums.TYPE_BOOL,
            unit=None,
            index=7,
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
    set_device_wait_reload(dlg, "mock_name")

    assert dlg.available_scan_options.by_index(7) == Option(
        cap=0,
        name=None,  # "select-detect"
        title=None,
        desc=None,
        constraint=None,
        size=1,
        type=enums.TYPE_BOOL,
        unit=None,
        index=7,
    ), "make options that throw an error undetectable and unselectable"

"test scan dialog"

from types import SimpleNamespace
import logging
from scanner.options import Option
from frontend import enums

logger = logging.getLogger(__name__)

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
        name="source",
        title="Scan source",
        desc="Selects the scan source (such as a document-feeder).",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=["Flatbed", "ADF", "Duplex"],
    ),
    Option(
        index=2,
        name="resolution",
        title="Scan resolution",
        desc="Sets the resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=5,
        constraint=[75, 100, 200, 300],
    ),
]


def mocked_do_get_devices(_cls, _request):
    "mock for do_get_devices"
    devices = [("mock_name", "", "", "")]
    return [
        SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1]) for x in devices
    ]


def mocked_do_open_device(self, request):
    "open device"
    device_name = request.args[0]
    self.device = device_name
    request.data(f"opened device '{self.device_name}'")


def mocked_do_get_options(self, _request):
    "mocked_do_get_options"
    self.device_handle = SimpleNamespace(
        resolution=75,
        source="Flatbed",
    )
    return raw_options


def mocked_do_set_option(self, _request):
    "mocked_do_set_option"
    info = 0
    key, value = _request.args
    if key == "source" and value == "Flatbed":
        raw_options[2] = raw_options[2]._replace(
            constraint=[75, 100, 200, 300, 600, 1200]
        )
        info = enums.INFO_RELOAD_OPTIONS
    setattr(self.device_handle, key.replace("-", "_"), value)
    return info


def test_combobox_on_reload(mocker, sane_scan_dialog, mainloop_with_timeout):
    """Check the scan options in a combobox are updated if necessary, if
    values are changed by a reload"""

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)
    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
    dialog = sane_scan_dialog
    callbacks = 0
    loop = mainloop_with_timeout()

    def changed_device_list_cb(_arg1, arg2):
        dialog.disconnect(dialog.signal)
        dialog.device = "mock_name"
        nonlocal callbacks
        callbacks += 1

    def reloaded_scan_options_cb(_arg):
        dialog.disconnect(dialog.reloaded_signal)
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-device-list", changed_device_list_cb)
    dialog.reloaded_signal = dialog.connect(
        "reloaded-scan-options", reloaded_scan_options_cb
    )
    dialog.get_devices()
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb(self, option, value, uuid):
        dialog.disconnect(dialog.signal)
        widget = self.option_widgets["resolution"]
        model = widget.get_model()
        resolutions = []
        for row in model:
            path, _itr = row
            resolutions.append(path)
        assert resolutions == [
            "75",
            "100",
            "200",
            "300",
            "600",
            "1200",
        ], "resolution widget updated"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    options = dialog.available_scan_options
    dialog.set_option(options.by_name("source"), "Flatbed")
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb2(_self, _option, value, _uuid):
        dialog.disconnect(dialog.signal)
        assert value == 600, "resolution values updated"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.signal = dialog.connect("changed-scan-option", changed_scan_option_cb2)
    widget = dialog.option_widgets["resolution"]
    widget.set_active(4)
    loop.run()

    assert callbacks == 4, "all callbacks ran"

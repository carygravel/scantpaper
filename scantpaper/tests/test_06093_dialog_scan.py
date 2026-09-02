"""test scan dialog"""

import logging
from types import SimpleNamespace

import pytest
from frontend import enums
from frontend.image_sane import decode_info
from scanner.profile import Profile

from tests.scan_mocks import build_scan_options

logger = logging.getLogger(__name__)


def test_infinite_reloads_due_to_tolerance(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    """Test more of scan dialog by mocking do_open_device() & do_get_options()"""

    def mocked_do_open_device(self, request):
        """Open device"""
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Document Table",
            enable_resampling=None,
            resolution=75,
            resolution_bind=True,
            x_resolution=75,
            y_resolution=75,
            scan_area="Manual",
            mode="Color",
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
            rotate="0 degrees",
            blank_threshold=0,
            brightness=0,
            contrast=0,
            threshold=128,
            gamma="1.8",
            image_count=None,
            jpeg_quality=90,
            transfer_format="RAW",
            transfer_size=1048576,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    raw_options = build_scan_options(
        [
            "source-adf-document-table",
            "enable-resampling",
            "resolution-50-1200",
            "resolution-bind",
            "x-resolution-50-1200",
            "y-resolution-50-1200",
            "scan-area-executive-iso",
            "mode-image-type",
            "device-03-geometry",
            "br-x-bottom-right-x",
            "br-y-bottom-right-y",
            "tl-x-top-left-x",
            "tl-y-top-left-y",
            "device-04-enhancement",
            "rotate",
            "blank-threshold",
            "brightness-0-100",
            "contrast-0-100",
            "threshold",
            "device--",
            "gamma",
            "image-count",
            "jpeg-quality",
            "transfer-format",
            "transfer-size",
        ]
    )

    def mocked_do_get_options(_self, _request):
        """mocked_do_get_options"""
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        """An Epson ET-4750 was triggering a reload on setting br-x and -y,
        and the reloaded values were outside the tolerance.
        Ensure that the reload limit is not hit
        """
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break

        info = 0
        if (key == "br-x" and value == 216) or (key == "br-y" and value == 279):
            value = 215.899993896484 if key == "br-x" else 279.399993896484
            info = (
                21936
                + enums.INFO_RELOAD_PARAMS
                + enums.INFO_RELOAD_OPTIONS
                + enums.INFO_INEXACT
            )
            logger.info(
                "sane_set_option %s (%s) to %s returned info %s (%s)",
                opt.index,
                opt.name,
                value,
                info,
                decode_info(info),
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg._add_profile(
        "my profile",
        Profile(
            backend=[
                ("scan-area", "Letter/Portrait"),
                ("br-x", 216),
                ("br-y", 279),
            ]
        ),
    )
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_profile_cb(_widget, profile):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert profile == "my profile", "changed-profile"
        assert dlg.current_scan_options == Profile(
            backend=[
                ("scan-area", "Letter/Portrait"),
                ("br-x", 215.899993896484),
                ("br-y", 279.0),
            ],
        ), "current-scan-options with profile"
        assert dlg.thread.device_handle.br_x == 215.899993896484, "br-x value"
        assert dlg.thread.device_handle.br_y == 279.399993896484, "br-y value"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"

    loop.run()

    assert dlg.num_reloads < 5, "didn't hit reload recursion limit"
    assert asserts == 1, "all callbacks ran"


def test_inexact(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    mainloop_with_timeout,
    inexact_scan_mocks,
):
    """Test more of scan dialog by mocking do_open_device() & do_get_options()"""
    inexact_scan_mocks.patch_all(mocker)

    dlg = sane_scan_dialog
    dlg.paper_sizes = {
        "US Legal": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 356.0},
        "US Letter": {"l": 0.0, "t": 0.0, "x": 216.0, "y": 279.0},
    }
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_paper_cb(_widget, _paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("br-x", 216.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "US Letter"},
        ), "set first paper"
        assert dlg.thread.device_handle.br_x == 215.5, "br-x value"
        assert dlg.thread.device_handle.br_y == 278.5, "br-y value"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(Profile(frontend={"paper": "US Letter"}))

    loop.run()

    loop = mainloop_with_timeout()

    def changed_paper_cb2(_widget, _paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("br-x", 216.0),
                ("br-y", 356.0),
            ],
            frontend={"paper": "US Legal"},
        ), "set second paper after SANE_INFO_INEXACT"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb2)
    dlg.set_current_scan_options(Profile(frontend={"paper": "US Legal"}))
    loop.run()

    assert asserts == 2, "all callbacks ran"


@pytest.mark.parametrize(
    "inexact_scan_mocks",
    [{"options": ["cct-1"], "handle": {"cct_1": 1.07818603515625}}],
    indirect=True,
)
def test_infinite_reloads_due_to_inexact(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    mainloop_with_timeout,
    inexact_scan_mocks,
):
    """Test that SANE_INFO_INEXACT geometry changes do not hit the reload-recursion-limit"""
    inexact_scan_mocks.patch_open_get(mocker)

    def mocked_do_set_option(self, _request):
        """An EPSON DS-1660W was setting tl-y=0.99 instead of 1, but not
        setting SANE_INFO_INEXACT, which was hitting the
        reload-recursion-limit.
        """
        key, value = _request.args
        opt = next((o for o in inexact_scan_mocks.raw_options if o.name == key), None)

        info = 0
        if key in ["br-x", "br-y", "tl-x", "tl-y"]:
            info = 21870
            if value == 1:
                value = 0.999984741210938
            logger.info(
                "sane_set_option %s (%s) to %s returned info %s (%s)",
                opt.index,
                opt.name,
                value,
                info,
                decode_info(info),
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    dlg.paper_sizes = {"new": {"l": 0.0, "t": 1.0, "x": 10.0, "y": 10.0}}
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_paper_cb(_widget, _paper):
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("tl-y", 1.0),
                ("br-x", 10.0),
                ("br-y", 11.0),
            ],
            frontend={"paper": "new"},
        ), "set inexact paper without SANE_INFO_INEXACT"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(Profile(frontend={"paper": "new"}))

    loop.run()

    assert asserts == 1, "all callbacks ran"

    # EPSON DS-1660W calls the flatbed a document table
    options = dlg.available_scan_options
    assert options.flatbed_selected(dlg.thread.get_option_value), (
        "Document Table means flatbed"
    )

    # as cct-1 does not have a title, test for label text
    assert dlg._get_label_for_option("cct-1") == "cct-1", (
        "text for option with no title"
    )

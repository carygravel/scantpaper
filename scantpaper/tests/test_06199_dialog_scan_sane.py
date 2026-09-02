"test scan dialog"

import logging
from types import SimpleNamespace

import pytest

logger = logging.getLogger(__name__)


def test_scan_resolution(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    mainloop_with_timeout,
    set_option_in_mainloop,
    sane_scan_mocks,
):
    """Test the resolution options passed with the new-scan signal"""

    sane_scan_mocks.patch_all(mocker)
    dialog = sane_scan_dialog
    callbacks = 0
    set_device_wait_reload(dialog, "mock_name")
    loop = mainloop_with_timeout()

    def new_scan_cb(_widget, _image_ob, _insert_after, _side, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 300, "x-resolution defaults"
        assert yres == 300, "y-resolution defaults"
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.num_pages = 1
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb)
    dialog.scan()
    loop.run()

    # wait for resolution option to propagate to current-scan-options before
    # scanning
    assert set_option_in_mainloop(dialog, "resolution", 600), "set resolution"

    loop = mainloop_with_timeout()

    def new_scan_cb2(_widget, _image_ob, _insert_after, _side, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 600, "x-resolution from resolution option"
        assert yres == 600, "y-resolution from resolution option"
        nonlocal callbacks
        callbacks += 1

    dialog.new_signal = dialog.connect("new-scan", new_scan_cb2)
    dialog.scan()
    loop.run()

    # wait for resolution option to propagate to current-scan-options before
    # scanning
    assert set_option_in_mainloop(dialog, "x-resolution", 150), "set x-resolution"

    loop = mainloop_with_timeout()

    def new_scan_cb3(_widget, _image_ob, _insert_after, _side, xres, yres):
        dialog.disconnect(dialog.new_signal)
        assert xres == 150, "x-resolution from x-resolution option"
        assert yres == 600, "y-resolution from resolution option"
        nonlocal callbacks
        callbacks += 1

    dialog.new_signal = dialog.connect("new-scan", new_scan_cb3)
    dialog.scan()
    loop.run()

    assert callbacks == 6, "changed-profile only called once"


def test_scan_source_adf(
    mocker,
    sane_scan_dialog,
    set_device_wait_reload,
    set_option_in_mainloop,
    sane_scan_mocks,
):
    """Test setting source to ADF triggers reload options"""

    sane_scan_mocks.patch_all(mocker)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")

    # This should trigger the first if branch in mocked_do_set_option
    assert set_option_in_mainloop(dialog, "source", "Automatic Document Feeder"), (
        "set source to ADF"
    )


def test_scan_page_no_device(sane_scan_mocks):
    """Test scanning without device raises ValueError"""
    with pytest.raises(ValueError, match="must open device before starting scan"):
        sane_scan_mocks.mocked_do_scan_page(SimpleNamespace(device_handle=None), None)

"""test scan dialog"""

from scanner.profile import Profile


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
    dlg.paper = "US Letter"
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
    dlg.paper = "US Legal"
    loop.run()

    assert asserts == 2, "all callbacks ran"

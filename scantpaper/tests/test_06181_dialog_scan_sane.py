"test scan dialog"


# TODO: combine with 06022
def test_1(mocker, sane_scan_dialog, mainloop_with_timeout):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        nonlocal asserts
        asserts += 1
        return []

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    dlg = sane_scan_dialog

    def changed_device_list_cb(self, devices):
        assert devices == [], "changed-device-list called with empty array"
        nonlocal asserts
        asserts += 1

    dlg.signal = dlg.connect("changed-device-list", changed_device_list_cb)
    loop = mainloop_with_timeout()
    dlg.get_devices()

    loop.run()
    assert asserts == 2, "all callbacks runs"

"test scan dialog"
from scanner.profile import Profile


def test_scan_pages(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """The test backend conveniently gives us
    Source = Automatic Document Feeder,
    which returns SANE_STATUS_NO_DOCS after the 10th scan.
    Test that we catch this.
    this should also unblock num-page to allow-batch-flatbed."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    n = 0
    loop = mainloop_with_timeout()

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1
        if pagenumber == 10:
            nonlocal callbacks
            callbacks += 1
        elif pagenumber > 10:
            assert False, "new-scan emitted 10 times"
            callbacks = 0
            loop.quit()

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            assert n == 10, "new-scan emitted 10 times"
            nonlocal callbacks
            callbacks += 1

    def changed_scan_option_cb(widget, option, value, _data):
        dialog.num_pages = 0
        dialog.scan()
        nonlocal callbacks
        callbacks += 1

    dialog.connect("new-scan", new_scan_cb)
    dialog.connect("finished-process", finished_process_cb)
    dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.set_option(
        dialog.available_scan_options.by_name("source"), "Automatic Document Feeder"
    )
    loop.run()

    assert callbacks == 3, "all callbacks executed"

    dialog.thread.quit()

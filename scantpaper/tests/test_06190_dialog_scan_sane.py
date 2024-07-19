"test scan dialog"


# TODO: combine this with 0618
def test_cancel_scan(sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout):
    """Cancel the scan immediately after starting it and test that:
    a. the new-scan signal is not emitted.
    b. we can successfully scan afterwards."""

    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "test:0")
    callbacks = 0
    n = 0
    loop = mainloop_with_timeout()

    def started_process_cb(_widget, process):
        dialog.disconnect(dialog.start_signal)
        dialog.cancel_scan()
        nonlocal callbacks
        callbacks += 1

    def new_scan_cb(_widget, image_ob, pagenumber, xres, yres):
        nonlocal n
        n += 1

    def finished_process_cb(_widget, process):
        if process == "scan_pages":
            dialog.disconnect(dialog.new_signal)
            dialog.disconnect(dialog.finished_signal)
            assert n < 2, "Did not throw new-scan signal twice"
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.num_pages = 2
    dialog.start_signal = dialog.connect("started-process", started_process_cb)
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb)
    dialog.finished_signal = dialog.connect("finished-process", finished_process_cb)
    dialog.scan()
    loop.run()

    # On some scanners, cancel-between-pages options, which fixed
    # a problem where some brother scanners reported SANE_STATUS_NO_DOCS
    # despite using the flatbed, stopped the ADF from feeding more that 1
    # sheet. We can't test the fix directly, but at least make sure the code
    # is reached by piggybacking the next two lines."""
    loop = mainloop_with_timeout()

    def new_scan_cb2(_widget, _image_ob, _pagenumber, _xres, _yres):
        dialog.disconnect(dialog.new_signal)
        nonlocal callbacks
        callbacks += 1

    def finished_process_cb2(_widget, process):
        if process == "scan_pages":
            nonlocal callbacks
            callbacks += 1
            loop.quit()

    dialog.cancel_between_pages = True
    assert dialog.available_scan_options.flatbed_selected(
        dialog.thread.device_handle
    ), "flatbed selected"
    dialog.new_signal = dialog.connect("new-scan", new_scan_cb2)
    dialog.connect("finished-process", finished_process_cb2)
    dialog.scan()
    loop.run()

    assert callbacks == 4, "all callbacks executed"

    dialog.thread.quit()

import os
import gi
from frontend.image_sane import SaneThread
import logging
import PIL

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1():

    # Glib.set_application_name("gscan2pdf")

    # logger = Log.Log4perl.get_logger
    # SaneThread.setup(logger)

    path = None
    thread = SaneThread()
    thread.start()

    def finished_callback(response):
        assert isinstance(response.info, PIL.Image.Image), "scan_page finished_callback returned image"
        assert response.info.size == (157, 196), "scan_page finished_callback image size"

    def open_callback(response):
        assert response.process == "open_device", "open_callback"
        uid = thread.scan_page(
            finished_callback=finished_callback,
        )
        thread.monitor(uid, block=True)  # for started_callback scan_page
        thread.monitor(uid, block=True)  # for finished_callback scan_page

    uid = thread.open_device(device_name="test", finished_callback=open_callback)
    thread.monitor(uid, block=True)  # for started_callback open_device
    thread.monitor(uid, block=True)  # for finished_callback open_device
    assert False, "end"

    #   next test thread.scan_pages

    # Gtk.main()

    #########################

    os.remove(path)

    thread.quit()

    assert thread.decode_info(0) == "none", "no info"
    assert thread.decode_info(1) == "SANE_INFO_INEXACT", "SANE_INFO_INEXACT"
    assert (
        thread.decode_info(3) == "SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "combination"
    assert (
        thread.decode_info(11) == "? + SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "missing"

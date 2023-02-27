import os
import gi
from frontend.image_sane import SaneThread
import logging

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1():

    # Glib.set_application_name("gscan2pdf")

    # logger = Log.Log4perl.get_logger
    # SaneThread.setup(logger)

    path = None
    thread = SaneThread()

    def open_callback():
        def new_page_callback(status, path=None):
            assert status == 5, "SANE_STATUS_GOOD"
            assert os.path.getsize(path) == 30807, "PNM created with expected size"

        def finished_callback():
            Gtk.main_quit()

        thread.scan_pages(
            dir=".",
            npages=1,
            new_page_callback=new_page_callback,
            finished_callback=finished_callback,
        )

    thread.open_device(
        device_name="test", finished_callback=open_callback
    )
    Gtk.main()

    #########################

    os.remove(path)

    thread.quit()

    assert thread.decode_info(0) == "none", "no info"
    assert (
        thread.decode_info(1) == "SANE_INFO_INEXACT"
    ), "SANE_INFO_INEXACT"
    assert (
        thread.decode_info(3)
        == "SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "combination"
    assert (
        thread.decode_info(11)
        == "? + SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "missing"

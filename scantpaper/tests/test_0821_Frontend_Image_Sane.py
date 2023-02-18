import os
import gi
from frontend.image_sane import Image_Sane
import logging

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1():

    Glib.set_application_name("gscan2pdf")

    logger = Log.Log4perl.get_logger
    Gscan2pdf.Frontend.Image_Sane.setup(logger)

    path = None

    def anonymous_01():
        def anonymous_02(status, path=None):
            assert status == 5, "SANE_STATUS_GOOD"
            assert os.path.getsize(path) == 30807, "PNM created with expected size"

        def anonymous_03():
            Gtk.main_quit()

        Gscan2pdf.Frontend.Image_Sane.scan_pages(
            dir=".",
            npages=1,
            new_page_callback=anonymous_02,
            finished_callback=anonymous_03,
        )

    Gscan2pdf.Frontend.Image_Sane.open_device(
        device_name="test", finished_callback=anonymous_01
    )
    Gtk.main()

    #########################

    os.remove(path)

    Gscan2pdf.Frontend.Image_Sane.quit()

    assert Gscan2pdf.Frontend.Image_Sane.decode_info(0) == "none", "no info"
    assert (
        Gscan2pdf.Frontend.Image_Sane.decode_info(1) == "SANE_INFO_INEXACT"
    ), "SANE_INFO_INEXACT"
    assert (
        Gscan2pdf.Frontend.Image_Sane.decode_info(3)
        == "SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "combination"
    assert (
        Gscan2pdf.Frontend.Image_Sane.decode_info(11)
        == "? + SANE_INFO_RELOAD_OPTIONS + SANE_INFO_INEXACT"
    ), "missing"

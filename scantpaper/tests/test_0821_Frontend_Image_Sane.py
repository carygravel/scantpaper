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

    def new_page_callback(response):
        assert isinstance(
            response.info, PIL.Image.Image
        ), "scan_page finished_callback returned image"
        assert response.info.size == (
            157,
            196,
        ), "scan_page finished_callback image size"

    def open_callback(response):
        assert response.process == "open_device", "open_callback"
        uid = thread.scan_page(
            finished_callback=new_page_callback,
        )
        thread.monitor(uid, block=True)  # for started_callback scan_page
        thread.monitor(uid, block=True)  # for finished_callback scan_page

    uid = thread.open_device(device_name="test", finished_callback=open_callback)
    thread.monitor(uid, block=True)  # for started_callback open_device
    thread.monitor(uid, block=True)  # for finished_callback open_device

    def scan_pages_finished_callback(response):
        assert response.process == "scan_page", "scan_pages_finished_callback"

    uid = thread.scan_pages(
        new_page_callback=new_page_callback,
        finished_callback=scan_pages_finished_callback,
    )
    thread.monitor(uid, block=True)  # for started_callback scan_page
    thread.monitor(uid, block=True)  # for finished_callback scan_page

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

    def scan_error_callback(response):
        assert response.process == "scan_page", "scan_page without opening device"
        assert (
            response.status == "must open device before starting scan"
        ), "scan_error_callback status"

    uid = thread.scan_page(error_callback=scan_error_callback)
    thread.monitor(uid, block=True)  # for started_callback scan_page
    thread.monitor(uid, block=True)  # for error_callback scan_page

    def get_devices_callback(response):
        assert response.process == "get_devices", "get_devices_finished_callback"
        assert isinstance(response.info, list), "get_devices_finished_callback"

    uid = thread.get_devices(finished_callback=get_devices_callback)
    thread.monitor(uid, block=True)  # for started_callback open_device
    thread.monitor(uid, block=True)  # for finished_callback open_device

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
    thread.monitor(None, block=True)  # for log open_device
    thread.monitor(uid, block=True)  # for finished_callback open_device

    def scan_pages_finished_callback(response):
        assert response.process == "scan_page", "scan_pages_finished_callback"
        assert thread.num_pages_scanned == 2, "scanned 2 pages"

    uid = thread.scan_pages(
        num_pages=2,
        new_page_callback=new_page_callback,
        finished_callback=scan_pages_finished_callback,
    )
    thread.monitor(uid, block=True)  # for started_callback scan_page 1
    thread.monitor(uid, block=True)  # for finished_callback scan_page 1
    thread.monitor(None, block=True)  # for started_callback scan_page 2
    thread.monitor(None, block=True)  # for finished_callback scan_page 2

    def open_again_callback(response):
        assert response.process == "open_device", "open without closing"

    uid = thread.open_device(device_name="test", finished_callback=open_again_callback)
    thread.monitor(uid, block=True)  # for started_callback open_device
    thread.monitor(None, block=True)  # for log open_device
    thread.monitor(uid, block=True)  # for finished_callback open_device
    assert isinstance(thread.device_handle.opt, dict), "opt is a dict of options"
    assert isinstance(
        thread.device_handle.optlist, list
    ), "optlist is a list of option names"

    assert not int(
        repr(getattr(thread.device_handle, "enable_test_options"))
    ), "enable_test_options defaults to False"
    uid = thread.set_option("enable_test_options", True)
    thread.monitor(uid, block=True)  # for started_callback set_option
    thread.monitor(uid, block=True)  # for finished_callback set_option
    assert int(
        repr(getattr(thread.device_handle, "enable_test_options"))
    ), "enable_test_options changed to True"

    def get_options_callback(response):
        assert response.process == "get_options", "get_options"
        assert isinstance(response.info, list), "get_options return a list of options"

    uid = thread.get_options(finished_callback=get_options_callback)
    thread.monitor(uid, block=True)  # for started_callback get_options
    thread.monitor(uid, block=True)  # for finished_callback get_options

    def close_device_callback(response):
        assert response.process == "close_device", "close_device"

    uid = thread.close_device(finished_callback=close_device_callback)
    thread.monitor(uid, block=True)  # for started_callback close_device
    thread.monitor(None, block=True)  # for log close_device
    thread.monitor(uid, block=True)  # for finished_callback close_device
    assert thread.device_handle is None, "closed device"

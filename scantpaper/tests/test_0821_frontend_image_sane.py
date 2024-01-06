"test frontend/image_sane.py"
from frontend.image_sane import SaneThread
import PIL
import pytest


def monitor_multiple(thread, num_calls):
    "helper function to save calls to monitor()"
    for _ in range(num_calls):
        thread.monitor(block=True)


def test_1():
    "test frontend/image_sane.py"
    thread = SaneThread()
    thread.start()

    def scan_error_callback(response):
        assert (
            response.request.process == "scan_page"
        ), "scan_page without opening device"
        assert (
            response.status == "must open device before starting scan"
        ), "scan_error_callback status"

    thread.scan_page(error_callback=scan_error_callback)
    # for scan_page started_callback, error_callback
    monitor_multiple(thread, 2)

    assert thread.requests.empty(), "request queue is empty"


@pytest.mark.skip(
    reason="for reasons I don't understand, this segfaults when run with other tests"
)
def test_2():
    "test frontend/image_sane.py #2"
    thread = SaneThread()
    thread.start()

    def get_devices_callback(response):
        assert (
            response.request.process == "get_devices"
        ), "get_devices_finished_callback"
        assert isinstance(response.info, list), "get_devices_finished_callback"

    thread.get_devices(finished_callback=get_devices_callback)
    # for open_device started_callback, finished_callback
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"


def test_3():
    "test frontend/image_sane.py #3"
    thread = SaneThread()
    thread.start()

    def open_callback(response):
        assert response.request.process == "open_device", "open_callback"

    thread.open_device(device_name="test", finished_callback=open_callback)
    # for open_device started_callback, log, finished_callback
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"
    assert thread.device_name == "test", "set device_name"

    def new_page_callback(response):
        assert isinstance(
            response.info, PIL.Image.Image
        ), "scan_page finished_callback returned image"
        assert response.info.size[0] > 0, "scan_page finished_callback image width"
        assert response.info.size[1] > 0, "scan_page finished_callback image height"

    thread.scan_page(finished_callback=new_page_callback)
    # for scan_page started_callback, finished_callback
    monitor_multiple(thread, 4)
    assert thread.requests.empty(), "request queue is empty"

    def scan_pages_finished_callback(response):
        assert response.request.process == "scan_page", "scan_pages_finished_callback"
        assert thread.num_pages_scanned == 2, "scanned 2 pages"

    thread.scan_pages(
        num_pages=2,
        new_page_callback=new_page_callback,
        finished_callback=scan_pages_finished_callback,
    )
    # for scan_page started_callback, finished_callback, page 1 & 2
    monitor_multiple(thread, 5)

    assert thread.requests.empty(), "request queue is empty"

    def open_again_callback(response):
        assert response.request.process == "open_device", "open without closing"

    thread.open_device(device_name="test", finished_callback=open_again_callback)
    # for open_device started_callback, log, finished_callback
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"

    def get_options_callback(response):
        assert response.request.process == "get_options", "get_options"
        assert isinstance(response.info, list), "get_options return a list of options"
        assert response.info[21][1] == "enable-test-options"

    thread.get_options(finished_callback=get_options_callback)
    # for get_options started_callback, finished_callback
    monitor_multiple(thread, 5)

    assert thread.requests.empty(), "request queue is empty"

    def get_option_callback(response):
        assert response.info == 0, "enable-test-options defaults to False"

    thread.get_option("enable-test-options", finished_callback=get_option_callback)
    # for get_options started_callback, finished_callback
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"

    thread.set_option("enable-test-options", True)
    # thread.set_option("enable_test_options", 1)
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"

    def get_option_callback2(response):
        assert response.info == 1, "enable-test-options now True"

    thread.get_option("enable-test-options", finished_callback=get_option_callback2)
    # for get_options started_callback, finished_callback
    monitor_multiple(thread, 3)

    assert thread.requests.empty(), "request queue is empty"

    thread.cancel()
    thread.get_options()  # dummy process
    assert not thread.requests.empty(), "request queue is not empty"
    # for close_device started_callback, log empty request queue, log, finished_callback
    monitor_multiple(thread, 4)
    assert thread.requests.empty(), "request queue is empty"

    def close_device_callback(response):
        assert response.request.process == "close_device", "close_device"

    thread.close_device(finished_callback=close_device_callback)
    # for close_device started_callback, log, finished_callback
    monitor_multiple(thread, 5)
    assert thread.device_handle is None, "closed device"

    assert thread.requests.empty(), "request queue is empty"

"test frontend/image_sane.py"
from frontend.image_sane import SaneThread
import PIL


def monitor_multiple(thread, uid_list):
    "helper function to save calls to monitor()"
    for uid in uid_list:
        thread.monitor(uid, block=True)


def test_1():
    "test frontend/image_sane.py"
    thread = SaneThread()
    thread.start()

    def scan_error_callback(response):
        assert response.process == "scan_page", "scan_page without opening device"
        assert (
            response.status == "must open device before starting scan"
        ), "scan_error_callback status"

    uid = thread.scan_page(error_callback=scan_error_callback)
    monitor_multiple(
        thread, [uid, uid]
    )  # for scan_page started_callback, error_callback

    def get_devices_callback(response):
        assert response.process == "get_devices", "get_devices_finished_callback"
        assert isinstance(response.info, list), "get_devices_finished_callback"

    uid = thread.get_devices(finished_callback=get_devices_callback)
    # for open_device started_callback, finished_callback
    monitor_multiple(thread, [uid, uid])


def test_2():
    "test frontend/image_sane.py #2"
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
        # for scan_page started_callback, finished_callback
        monitor_multiple(thread, [uid, uid])

    uid = thread.open_device(device_name="test", finished_callback=open_callback)
    # for open_device started_callback, log, finished_callback
    monitor_multiple(thread, [uid, None, uid])

    def scan_pages_finished_callback(response):
        assert response.process == "scan_page", "scan_pages_finished_callback"
        assert thread.num_pages_scanned == 2, "scanned 2 pages"

    uid = thread.scan_pages(
        num_pages=2,
        new_page_callback=new_page_callback,
        finished_callback=scan_pages_finished_callback,
    )
    # for scan_page started_callback, finished_callback, page 1 & 2
    monitor_multiple(thread, [uid, uid, None, None])

    def open_again_callback(response):
        assert response.process == "open_device", "open without closing"

    uid = thread.open_device(device_name="test", finished_callback=open_again_callback)
    # for open_device started_callback, log, finished_callback
    monitor_multiple(thread, [uid, None, uid])
    assert isinstance(thread.device_handle.opt, dict), "opt is a dict of options"
    assert isinstance(
        thread.device_handle.optlist, list
    ), "optlist is a list of option names"

    assert not int(
        repr(getattr(thread.device_handle, "enable_test_options"))
    ), "enable_test_options defaults to False"
    uid = thread.set_option("enable_test_options", True)
    # for set_option started_callback, finished_callback
    monitor_multiple(thread, [uid, uid])
    assert int(
        repr(getattr(thread.device_handle, "enable_test_options"))
    ), "enable_test_options changed to True"

    def get_options_callback(response):
        assert response.process == "get_options", "get_options"
        assert isinstance(response.info, list), "get_options return a list of options"

    uid = thread.get_options(finished_callback=get_options_callback)
    # for get_options started_callback, finished_callback
    monitor_multiple(thread, [uid, uid])

    uid = thread.cancel()
    thread.get_options()  # dummy process
    assert not thread.requests.empty(), "request queue is not empty"
    # for close_device started_callback, log empty request queue, log, finished_callback
    monitor_multiple(thread, [uid, None, None, uid])
    assert thread.requests.empty(), "request queue is empty"

    def close_device_callback(response):
        assert response.process == "close_device", "close_device"

    uid = thread.close_device(finished_callback=close_device_callback)
    # for close_device started_callback, log, finished_callback
    monitor_multiple(thread, [uid, None, uid])
    assert thread.device_handle is None, "closed device"

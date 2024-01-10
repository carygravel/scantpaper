"test frontend/image_sane.py"
from frontend.image_sane import SaneThread
import PIL
from gi.repository import GLib


def test_1():
    "test frontend/image_sane.py"
    thread = SaneThread()
    thread.start()

    asserts = 0

    def scan_error_callback(response):
        nonlocal asserts
        assert (
            response.request.process == "scan_page"
        ), "scan_page without opening device"
        assert (
            response.status == "must open device before starting scan"
        ), "scan_error_callback status"
        asserts += 1

    thread.scan_page(error_callback=scan_error_callback)
    thread.send("quit")
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 1, "checked all expected responses #1"


def test_2():
    "test frontend/image_sane.py #2"
    thread = SaneThread()
    thread.start()

    asserts = 0

    def get_devices_callback(response):
        nonlocal asserts
        assert (
            response.request.process == "get_devices"
        ), "get_devices_finished_callback"
        assert isinstance(response.info, list), "get_devices_finished_callback"
        asserts += 1

    thread.get_devices(finished_callback=get_devices_callback)
    thread.send("quit")
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 1, "checked all expected responses #2"


def test_3():
    "test frontend/image_sane.py #3"
    thread = SaneThread()
    thread.start()

    asserts = 0

    mlp = GLib.MainLoop()

    def open_callback(response):
        nonlocal asserts
        assert response.request.process == "open_device", "open_callback"
        asserts += 1
        mlp.quit()

    thread.open_device(device_name="test", finished_callback=open_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert thread.device_name == "test", "set device_name"
    assert asserts == 1, "checked all expected responses #3"

    mlp = GLib.MainLoop()

    def scan_page_finished_callback(response):
        nonlocal asserts
        assert isinstance(
            response.info, PIL.Image.Image
        ), "scan_page finished_callback returned image"
        assert response.info.size[0] > 0, "scan_page finished_callback image width"
        assert response.info.size[1] > 0, "scan_page finished_callback image height"
        asserts += 1
        mlp.quit()

    thread.scan_page(finished_callback=scan_page_finished_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 2, "checked all expected responses #4"

    def new_page_callback(response):
        nonlocal asserts
        assert isinstance(
            response.info, PIL.Image.Image
        ), "scan_page finished_callback returned image"
        assert response.info.size[0] > 0, "scan_page finished_callback image width"
        assert response.info.size[1] > 0, "scan_page finished_callback image height"
        asserts += 1

    mlp = GLib.MainLoop()

    def scan_pages_finished_callback(response):
        nonlocal asserts
        assert response.request.process == "scan_page", "scan_pages_finished_callback"
        assert thread.num_pages_scanned == 2, "scanned 2 pages"
        asserts += 1
        mlp.quit()

    thread.scan_pages(
        num_pages=2,
        new_page_callback=new_page_callback,
        finished_callback=scan_pages_finished_callback,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 5, "checked all expected responses #5"

    mlp = GLib.MainLoop()

    def open_again_callback(response):
        nonlocal asserts
        assert response.request.process == "open_device", "open without closing"
        asserts += 1
        mlp.quit()

    thread.open_device(device_name="test", finished_callback=open_again_callback)
    thread.send("quit")
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 6, "checked all expected responses #6"


def test_4():
    "test frontend/image_sane.py #4"
    thread = SaneThread()
    thread.start()

    mlp = GLib.MainLoop()

    asserts = 0

    def get_options_callback(response):
        nonlocal asserts
        assert response.request.process == "get_options", "get_options"
        assert isinstance(response.info, list), "get_options return a list of options"
        assert response.info[21][1] == "enable-test-options"
        asserts += 1
        mlp.quit()

    thread.open_device(device_name="test")
    thread.get_options(finished_callback=get_options_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 1, "checked all expected responses #7"

    mlp = GLib.MainLoop()

    def get_option_callback(response):
        nonlocal asserts
        assert response.info == 0, "enable-test-options defaults to False"
        asserts += 1
        mlp.quit()

    thread.get_option("enable-test-options", finished_callback=get_option_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 2, "checked all expected responses #8"

    mlp = GLib.MainLoop()
    thread.set_option(
        "enable-test-options", True, finished_callback=lambda response: mlp.quit()
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()

    def get_option_callback2(response):
        nonlocal asserts
        assert response.info == 1, "enable-test-options now True"
        asserts += 1
        mlp.quit()

    thread.get_option("enable-test-options", finished_callback=get_option_callback2)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 3, "checked all expected responses #9"

    # FIXME: get cancel() working
    # ran_finished = False

    # mlp = GLib.MainLoop()
    # def get_options_callback2(response):
    #     nonlocal ran_finished
    #     ran_finished = True
    #     mlp.quit()

    # ran_cancelled = False

    # def cancelled_callback(response):
    #     nonlocal ran_cancelled
    #     ran_cancelled = True
    #     mlp.quit()

    # thread.get_options(
    #     finished_callback=get_options_callback2, cancelled_callback=cancelled_callback
    # )
    # thread.cancel(cancelled_callback=cancelled_callback)
    # GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    # mlp.run()

    # assert not ran_finished, "cancelled jobs don't run the finished callback"
    # assert ran_cancelled, "ran the cancelled callback"

    mlp = GLib.MainLoop()

    def close_device_callback(response):
        nonlocal asserts
        assert response.request.process == "close_device", "close_device"
        asserts += 1
        mlp.quit()

    thread.close_device(finished_callback=close_device_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert thread.device_handle is None, "closed device"
    thread.send("quit")
    assert asserts == 4, "checked all expected responses #10"

"test frontend/image_sane.py"

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import PIL
from gi.repository import GLib
from frontend import enums
from frontend.image_sane import SaneThread


def test_error_handling():
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

    def new_page_callback(image, _pagenumber):
        nonlocal asserts
        assert isinstance(
            image, PIL.Image.Image
        ), "scan_page finished_callback returned image"
        assert image.size[0] > 0, "scan_page finished_callback image width"
        assert image.size[1] > 0, "scan_page finished_callback image height"
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


def test_5_edge_cases():
    "test frontend/image_sane.py edge cases"
    thread = SaneThread()
    thread.start()

    mlp = GLib.MainLoop()
    asserts = 0

    # Open device
    def open_callback(response):
        nonlocal asserts
        assert response.request.process == "open_device"
        asserts += 1
        mlp.quit()

    thread.open_device(device_name="test", finished_callback=open_callback)
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 1, "opened device"

    # 1. Read-only attribute
    def error_callback_readonly(response):
        nonlocal asserts
        assert "Read-only attribute: dev" in response.status
        asserts += 1
        mlp.quit()

    thread.set_option("dev", "foo", error_callback=error_callback_readonly)
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 2, "checked read-only attribute"

    # 2. Inactive option
    def error_callback_inactive(response):
        nonlocal asserts
        assert "Inactive option: three_pass" in response.status
        asserts += 1
        mlp.quit()

    thread.set_option("three-pass", True, error_callback=error_callback_inactive)
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 3, "checked inactive option"

    # 3. Non-existent option
    def finished_callback_nonexistent(response):
        nonlocal asserts
        assert response.info == 0
        asserts += 1
        mlp.quit()

    thread.set_option(
        "nonexistent-opt", 123, finished_callback=finished_callback_nonexistent
    )
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 4, "checked nonexistent option"

    # 4. Enable test options
    def finished_callback_enable(response):
        nonlocal asserts
        assert isinstance(response.info, int)
        asserts += 1
        mlp.quit()

    thread.set_option(
        "enable-test-options", True, finished_callback=finished_callback_enable
    )
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 5, "enabled test options"

    # 5. Fixed type conversion
    def finished_callback_fixed(response):
        nonlocal asserts
        assert isinstance(response.info, int)
        asserts += 1
        mlp.quit()

    thread.set_option("fixed", 42, finished_callback=finished_callback_fixed)
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()
    assert asserts == 6, "checked fixed type conversion"

    thread.send("quit")
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()


def test_6_mock_device():
    "test with mocked device for specific edge cases"

    class MockDevice:
        "Custom mock device class to avoid MagicMock hasattr issues and ensure structure"

        def __init__(self):
            "Initialize mock device with options and dev mock"
            self.opt = {}
            self.dev = MagicMock()
            # Initial setup for first reload test
            # We need __load_option_dict for hasattr check
            self.__dict__["__load_option_dict"] = MagicMock()
            # And _SaneThread__load_option_dict because SaneThread mangles the call
            self.__dict__["_SaneThread__load_option_dict"] = self.__dict__[
                "__load_option_dict"
            ]

        def close(self):
            "Mock close method"

    with patch("sane.open") as mock_open:
        mock_dev_instance = MockDevice()
        mock_open.return_value = mock_dev_instance

        # Setup options
        opt_group = SimpleNamespace(
            name="group-option",
            type=enums.TYPE_GROUP,
            cap=enums.CAP_SOFT_SELECT,
            index=1,
        )

        opt_unsettable = SimpleNamespace(
            name="unsettable-option",
            type=enums.TYPE_BOOL,
            cap=enums.CAP_SOFT_DETECT,  # Not SOFT_SELECT (1)
            index=2,
        )

        opt_reload = SimpleNamespace(
            name="reload-option",
            type=enums.TYPE_BOOL,
            cap=enums.CAP_SOFT_SELECT,
            index=3,
        )

        mock_dev_instance.opt = {
            "group_option": opt_group,
            "unsettable_option": opt_unsettable,
            "reload_option": opt_reload,
        }

        # Setup set_option return values on the inner 'dev' mock
        def set_option_side_effect(index, _value):
            if index == 3:
                return enums.INFO_RELOAD_OPTIONS
            return 0

        mock_dev_instance.dev.set_option.side_effect = set_option_side_effect

        thread = SaneThread()
        thread.start()

        mlp = GLib.MainLoop()
        asserts = 0

        # Open device (mocks sane.open)
        def open_cb(response):
            nonlocal asserts
            assert response.request.process == "open_device"
            asserts += 1
            mlp.quit()

        thread.open_device("mock_device", finished_callback=open_cb)
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

        # 1. Test Group Option (Line 103)
        def error_cb_group(response):
            nonlocal asserts
            assert "Groups don't have values: group_option" in response.status
            asserts += 1
            mlp.quit()

        thread.set_option("group-option", "val", error_callback=error_cb_group)
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

        # 2. Test Unsettable Option (Line 107)
        def error_cb_unsettable(response):
            nonlocal asserts
            assert (
                "Option can't be set by software: unsettable_option" in response.status
            )
            asserts += 1
            mlp.quit()

        thread.set_option("unsettable-option", True, error_callback=error_cb_unsettable)
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

        # 3. Test Reload Option with __load_option_dict (Line 116)
        def finished_cb_reload(_response):
            nonlocal asserts
            asserts += 1
            mlp.quit()

        thread.set_option("reload-option", True, finished_callback=finished_cb_reload)
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

        mock_dev_instance.__dict__["__load_option_dict"].assert_called_once()

        # Reset for next part
        mock_dev_instance.dev.set_option.reset_mock()
        mock_dev_instance.dev.set_option.side_effect = set_option_side_effect

        # 4. Test Reload Option with _SaneDev__load_option_dict (Line 117-118)
        # Remove __load_option_dict and aliases
        del mock_dev_instance.__dict__["__load_option_dict"]
        del mock_dev_instance.__dict__["_SaneThread__load_option_dict"]

        mock_dev_instance.__dict__["_SaneDev__load_option_dict"] = MagicMock()

        thread.set_option("reload-option", False, finished_callback=finished_cb_reload)
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

        mock_dev_instance.__dict__["_SaneDev__load_option_dict"].assert_called_once()

        assert asserts == 5

        thread.send("quit")
        GLib.timeout_add(2000, mlp.quit)
        mlp.run()

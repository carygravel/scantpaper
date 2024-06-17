"subclass basethread for SANE"
from types import SimpleNamespace
from basethread import BaseThread
import sane


def _set_default_callbacks(kwargs):
    for callback in [
        "started_callback",
        "running_callback",
        "error_callback",
        "new_page_callback",
        "finished_callback",
    ]:
        if callback not in kwargs:
            kwargs[callback] = None


class SaneThread(BaseThread):
    "subclass basethread for SANE"

    device_handle = None
    device_name = None
    num_pages_scanned = 0
    num_pages = 0

    def do_quit(self, _request):
        "exit"
        self.device_handle = None
        sane.exit()

    @classmethod
    def do_get_devices(cls, _request):
        "get devices"
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in sane.get_devices()
        ]

    def do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        # close the handle if it is open
        if self.device_handle is not None:
            self.device_handle = None
            sane.exit()

        self.device_handle = sane.open(device_name)
        self.device_name = device_name
        request.data(f"opened device '{self.device_name}'")

    def do_get_option(self, request):
        "get options"
        name = request.args[0]
        return getattr(self.device_handle, name.replace("-", "_"))

    def do_get_options(self, _request):
        "get options"
        return self.device_handle.get_options()

    def do_set_option(self, request):
        """Until sane.__setattr__() returns the INFO, put its functionality
        here to return it ourselves"""
        key, value = request.args
        key = key.replace("-", "_")
        d = self.device_handle.__dict__
        if key in ("dev", "optlist", "area", "sane_signature", "scanner_model"):
            raise AttributeError("Read-only attribute: " + key)

        if key not in self.device_handle.opt:
            d[key] = value
            return 0

        opt = d["opt"][key]
        if opt.type == sane._sane.TYPE_BUTTON:
            raise AttributeError("Buttons don't have values: " + key)
        if opt.type == sane._sane.TYPE_GROUP:
            raise AttributeError("Groups don't have values: " + key)
        if not sane._sane.OPTION_IS_ACTIVE(opt.cap):
            raise AttributeError("Inactive option: " + key)
        if not sane._sane.OPTION_IS_SETTABLE(opt.cap):
            raise AttributeError("Option can't be set by software: " + key)
        if isinstance(value, int) and opt.type == sane._sane.TYPE_FIXED:
            # avoid annoying errors of backend if int is given instead float:
            value = float(value)
        result = d["dev"].set_option(opt.index, value)
        # do binary AND to find if we have to reload options:
        if result & sane._sane.INFO_RELOAD_OPTIONS:
            self.device_handle.__load_option_dict()

        return result

    def do_scan_page(self, _request):
        "scan page"
        if self.device_handle is None:
            raise ValueError("must open device before starting scan")
        return self.device_handle.scan()

    def do_cancel(self, _request):
        "cancel"
        if self.device_handle is not None:
            self.device_handle.cancel()

    def do_close_device(self, request):
        "close device"
        if self.device_handle is None:
            request.data("Ignoring close_device() call - no device open.")
        else:
            self.device_handle.close()
            self.device_handle = None
            request.data(f"closing device '{self.device_name}'")
            self.device_name = None

    def get_devices(self, **kwargs):
        "get devices"
        return self.send("get_devices", **kwargs)

    def open_device(self, device_name, **kwargs):
        "open device"
        return self.send("open_device", device_name, **kwargs)

    def get_options(self, **kwargs):
        "get options"
        return self.send("get_options", **kwargs)

    def get_option(self, name, **kwargs):
        "get option"
        return self.send("get_option", name, **kwargs)

    def set_option(self, name, value, **kwargs):
        "set option"
        return self.send("set_option", name, value, **kwargs)

    def scan_page(self, **kwargs):
        "scan page"
        return self.send("scan_page", **kwargs)

    def _scan_pages_callback(self, response, **kwargs):
        self.num_pages_scanned += 1
        _set_default_callbacks(kwargs)
        if kwargs["new_page_callback"] is not None:
            kwargs["new_page_callback"](response)
        if self.num_pages is not None and self.num_pages_scanned >= self.num_pages:
            if kwargs["finished_callback"] is not None:
                kwargs["finished_callback"](response)
            return
        self.scan_page(
            started_callback=kwargs["started_callback"],
            running_callback=kwargs["running_callback"],
            error_callback=kwargs["error_callback"],
            finished_callback=lambda response: self._scan_pages_callback(
                response,
                running_callback=kwargs["running_callback"],
                finished_callback=kwargs["finished_callback"],
                error_callback=kwargs["error_callback"],
                new_page_callback=kwargs["new_page_callback"],
            ),
        )

    def scan_pages(self, num_pages=1, **kwargs):
        "scan pages"
        self.num_pages_scanned = 0
        self.num_pages = num_pages
        _set_default_callbacks(kwargs)
        return self.scan_page(
            started_callback=kwargs["started_callback"],
            running_callback=kwargs["running_callback"],
            error_callback=kwargs["error_callback"],
            finished_callback=lambda response: self._scan_pages_callback(
                response,
                running_callback=kwargs["running_callback"],
                finished_callback=kwargs["finished_callback"],
                error_callback=kwargs["error_callback"],
                new_page_callback=kwargs["new_page_callback"],
            ),
        )

    def close_device(self, **kwargs):
        "close device"
        return self.send("close_device", **kwargs)

    def quit(self, **kwargs):
        "quit"
        return self.send("quit", **kwargs)

    def cancel(self, **kwargs):
        "Flag the scan routine to abort"

        # empty process queue first to stop any new process from starting
        while not self.requests.empty():
            self.requests.get()

        # Then send the thread a cancel signal
        # _self["abort_scan"] = 1
        # uuid = str(uuid_object())
        # callback[uuid]["cancelled"] = callback

        # Add a cancel request to ensure the reply is not blocked
        return self.send("cancel", **kwargs)

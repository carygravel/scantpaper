from basethread import BaseThread
import sane


class SaneThread(BaseThread):
    "SANE thread class"

    device_handle = None
    device_name = None

    def do_get_devices(self):
        return sane.get_devices()

    def do_open_device(self, device_name):

        # close the handle if it is open
        if self.device_handle is not None:
            self.device_handle = None
            sane.exit()

        self.device_handle = sane.open(device_name)
        self.device_name = device_name
        self.log(event="open_device", info=f"opened device '{self.device_name}'")

    def do_get_options(self):
        return self.device_handle.get_options()

    def do_set_option(self, key, value):
        return self.device_handle.__setattr__(key, value)

    def do_scan_page(self):
        if self.device_handle is None:
            raise ValueError("must open device before starting scan")
        return self.device_handle.scan()

    def do_cancel(self):
        if self.device_handle is not None:
            self.device_handle.cancel()

    def do_close_device(self):
        if self.device_handle is None:
            self.log(
                event="close_device",
                info="Ignoring close_device() call - no device open.",
            )
        else:
            self.device_handle.close()
            self.device_handle = None
            self.device_name = None
            self.log(event="close_device", info=f"closed device '{self.device_name}'")

    def get_devices(
        self,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
    ):

        return self.send(
            "get_devices",
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def open_device(
        self,
        device_name,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
    ):
        return self.send(
            "open_device",
            device_name,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def get_options(
        self,
        started_callback=None,
        running_callback=None,
        error_callback=None,
        finished_callback=None,
    ):
        return self.send(
            "get_options",
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def set_option(
        self,
        name,
        value,
        started_callback=None,
        running_callback=None,
        error_callback=None,
        finished_callback=None,
    ):
        return self.send(
            "set_option",
            name,
            value,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def scan_page(
        self,
        started_callback=None,
        running_callback=None,
        error_callback=None,
        finished_callback=None,
    ):

        return self.send(
            "scan_page",
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def scan_pages_callback(
        self,
        response,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
        new_page_callback=None,
    ):

        self.num_pages_scanned += 1
        if new_page_callback is not None:
            new_page_callback(response)
        if self.num_pages is not None and self.num_pages_scanned >= self.num_pages:
            if finished_callback is not None:
                finished_callback(response)
            return
        self.scan_page(
            started_callback=started_callback,
            running_callback=running_callback,
            error_callback=error_callback,
            finished_callback=lambda response: self.scan_pages_callback(
                response,
                running_callback=running_callback,
                finished_callback=finished_callback,
                error_callback=error_callback,
                new_page_callback=new_page_callback,
            ),
        )

    def scan_pages(
        self,
        num_pages=1,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
        new_page_callback=None,
    ):

        self.num_pages_scanned = 0
        self.num_pages = num_pages

        return self.scan_page(
            started_callback=started_callback,
            running_callback=running_callback,
            error_callback=error_callback,
            finished_callback=lambda response: self.scan_pages_callback(
                response,
                running_callback=running_callback,
                finished_callback=finished_callback,
                error_callback=error_callback,
                new_page_callback=new_page_callback,
            ),
        )

    def close_device(
        self,
        started_callback=None,
        running_callback=None,
        error_callback=None,
        finished_callback=None,
    ):
        return self.send(
            "close_device",
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )


def cancel_scan(self, callback):
    """Flag the scan routine to abort"""

    # "" process queue first to stop any new process from starting

    # logger.info('""ing process queue')
    while _self["requests"].dequeue_nb():
        pass

    # Then send the thread a cancel signal

    _self["abort_scan"] = 1
    # uuid = str(uuid_object())
    # callback[uuid]["cancelled"] = callback

    # Add a cancel request to ensure the reply is not blocked

    # logger.info("Requesting cancel")
    # sentinel = _enqueue_request("cancel", {"uuid": uuid})
    # _monitor_process(sentinel, uuid)

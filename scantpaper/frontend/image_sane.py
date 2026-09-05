"""subclass basethread for SANE."""

import gc
import logging
import math
import threading
from types import SimpleNamespace

import sane
from basethread import BaseThread
from frontend import enums

logger = logging.getLogger(__name__)

# Global flag to track if sane.init() has been called
# Using a list so we can modify it from within functions
_sane_initialized = [False]


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
    """subclass basethread for SANE."""

    device_handle = None
    device_name = None
    num_pages_scanned = 0
    num_pages = 0
    scan_page_progress = 0.0
    scan_page_total_lines = None
    _scan_progress_cb = None
    _scan_active = False
    _cancel_requested = False

    def handler_wrapper(self, request, handler):
        """Override the handler wrapper logic to deal with SANE_STATUS_NO_DOCS."""
        try:
            request.finished(handler(request))
            if request.process == "quit":
                return False
        except Exception as err:
            # BLE001 — the handler is a do_<process> SANE method that may
            # raise arbitrary Python/SANE C-level errors, so no narrower
            # set is catchable; the error is wrapped and routed to the
            # caller via request.error()/request.finished() below.
            logger.exception(
                "Error running process '%s'",
                request.process,
            )
            if (
                request.process == "scan_page"
                and str(err) == "Document feeder out of documents"
            ):
                request.finished(None, str(err))
            elif request.process == "scan_page" and self._cancel_requested:
                request.cancelled()
            else:
                request.error(None, str(err))
                if request.process == "scan_page" and self.device_handle is not None:
                    self.cancel()
        return True

    def do_quit(self, _request):
        """Exit."""
        # Close the device handle properly before setting to None
        if self.device_handle is not None:
            try:
                self.device_handle.close()
            except Exception as e:  # noqa: BLE001
                # BLE001 — device_handle.close() maps to SANE C bindings that
                # can raise arbitrary errors during teardown; any failure here
                # is best-effort cleanup, so we catch broadly and log.
                logger.debug("Ignoring error closing device handle: %s", e)
            self.device_handle = None

        # Force garbage collection to ensure all device handles are freed
        # This prevents segfaults when calling sane.exit()
        gc.collect()

        # Now it's safe to call sane.exit() since all handles are cleaned up
        if _sane_initialized[0]:
            try:
                sane.exit()
            except Exception as e:  # noqa: BLE001
                # BLE001 — sane.exit() maps to SANE C bindings that can raise
                # arbitrary errors during teardown; any failure here is
                # best-effort cleanup, so we catch broadly and log.
                logger.debug("Ignoring error during sane.exit(): %s", e)
            _sane_initialized[0] = False

    @classmethod
    def do_get_devices(cls, _request):
        """Get devices."""
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[2], label=x[3])
            for x in sane.get_devices()
        ]

    def do_open_device(self, request):
        """Open device."""
        device_name = request.args[0]
        # close the handle if it is open
        if self.device_handle is not None:
            self.device_handle.close()
            self.device_handle = None

        # Ensure SANE is initialized globally (only call once across all threads)
        if not _sane_initialized[0]:
            sane.init()
            _sane_initialized[0] = True

        self.device_handle = sane.open(device_name)
        self.device_name = device_name
        request.data(f"opened device '{self.device_name}'")

    def do_get_option(self, request):
        """Get options."""
        name = request.args[0]
        return getattr(self.device_handle, name.replace("-", "_"))

    def do_get_options(self, _request):
        """Get options."""
        return self.device_handle.get_options()

    def do_get_option_blocking(self, request):
        """Read a single option value in the worker and signal the caller."""
        name, holder, event = request.args
        try:
            holder.append(getattr(self.device_handle, name.replace("-", "_")))
        except Exception as err:  # noqa: BLE001
            # BLE001 — reading a SANE device attribute can raise arbitrary
            # Python/SANE C-level errors, so no narrower set is catchable;
            # the worker must not die, and the error is wrapped and returned
            # to the caller via holder below.
            holder.append(err)
        finally:
            event.set()

    def do_set_option(self, request):
        """Reimplement sane.__setattr__() to return INFO until it does so natively."""
        key, value = request.args
        key = key.replace("-", "_")
        dic = self.device_handle.__dict__
        if key in ("dev", "optlist", "area", "sane_signature", "scanner_model"):
            raise AttributeError("Read-only attribute: " + key)

        if key not in self.device_handle.opt:
            dic[key] = value
            return 0

        opt = dic["opt"][key]
        if opt.type == enums.TYPE_GROUP:
            raise AttributeError("Groups don't have values: " + key)
        if not enums.OPTION_IS_ACTIVE(opt.cap):
            raise AttributeError("Inactive option: " + key)
        if not enums.OPTION_IS_SETTABLE(opt.cap):
            raise AttributeError("Option can't be set by software: " + key)
        if isinstance(value, int) and opt.type == enums.TYPE_FIXED:
            # avoid annoying errors from backend if int is given instead float:
            value = float(value)
        info = dic["dev"].set_option(opt.index, value)

        # binary AND to find if we have to reload options:
        if info & enums.INFO_RELOAD_OPTIONS:
            if hasattr(self.device_handle, "__load_option_dict"):
                self.device_handle.__load_option_dict()
            elif hasattr(self.device_handle, "_SaneDev__load_option_dict"):
                self.device_handle._SaneDev__load_option_dict()

        logger.info(
            f"sane_set_option {opt.index} ({opt.name})"
            + ("" if opt.type == enums.TYPE_BUTTON else f" to {value}")
            + " returned info "
            + f"{info} ({decode_info(info)})"
            if info is not None
            else None
        )

        return info

    def do_scan_page(self, request):
        """Scan page."""
        if self.device_handle is None:
            msg = "must open device before starting scan"
            raise ValueError(msg)
        cancel_between_pages = request.args[0] if request.args else False
        self.scan_page_progress = 0.0
        logger.debug("calling sane_start() on device %s", self.device_name)
        self.device_handle.start()
        logger.debug("sane_start() returned successfully")
        params = self.device_handle.get_parameters()
        logger.debug("sane_get_parameters(): %s", params)
        _, _, (_, lines), _, _ = params
        self.scan_page_total_lines = lines if lines > 0 else None

        def _progress_cb(current_line, total_lines):
            if total_lines > 0:
                self.scan_page_progress = min(1.0, current_line / total_lines)

        self._scan_progress_cb = _progress_cb
        self._cancel_requested = False
        self._scan_active = True
        try:
            return self.device_handle.snap(
                no_cancel=not cancel_between_pages, progress=self._scan_progress_cb
            )
        finally:
            self._scan_active = False

    def do_cancel(self, _request):
        """Cancel."""
        if self.device_handle is not None:
            self.device_handle.cancel()

    def do_close_device(self, request):
        """Close device."""
        if self.device_handle is None:
            request.data("Ignoring close_device() call - no device open.")
        else:
            self.device_handle.close()
            self.device_handle = None
            request.data(f"closing device '{self.device_name}'")
            self.device_name = None

    def get_devices(self, **kwargs):
        """Get devices."""
        return self.send("get_devices", **kwargs)

    def open_device(self, device_name, **kwargs):
        """Open device."""
        return self.send("open_device", device_name, **kwargs)

    def get_options(self, **kwargs):
        """Get options."""
        return self.send("get_options", **kwargs)

    def get_option(self, name, **kwargs):
        """Get option."""
        return self.send("get_option", name, **kwargs)

    def set_option(self, name, value, **kwargs):
        """Set option."""
        return self.send("set_option", name, value, **kwargs)

    def get_option_value(self, name, timeout=10):
        """Fetch a single option value synchronously via the worker thread."""
        holder = []
        event = threading.Event()
        self.send("get_option_blocking", name, holder, event)
        if not event.wait(timeout):
            msg = f"Timed out reading option '{name}'"
            raise TimeoutError(msg)
        result = holder[0]
        if isinstance(result, Exception):
            raise result
        return result

    def scan_page(self, *, cancel_between_pages=False, **kwargs):
        """Scan page."""
        return self.send("scan_page", cancel_between_pages, **kwargs)

    def _scan_pages_finished_callback(self, response, **kwargs):
        _set_default_callbacks(kwargs)
        cancel_between_pages = kwargs.get("cancel_between_pages", False)
        if response.info is not None:
            self.num_pages_scanned += 1
            if kwargs["new_page_callback"] is not None:
                kwargs["new_page_callback"](response.info)
        if response.status == "Document feeder out of documents" or (
            self.num_pages != 0 and self.num_pages_scanned >= self.num_pages
        ):
            self.cancel()
            if kwargs["finished_callback"] is not None:
                kwargs["finished_callback"](response)
            return
        self.scan_page(
            cancel_between_pages=cancel_between_pages,
            started_callback=kwargs["started_callback"],
            running_callback=kwargs["running_callback"],
            error_callback=kwargs["error_callback"],
            finished_callback=lambda response: self._scan_pages_finished_callback(
                response,
                cancel_between_pages=cancel_between_pages,
                running_callback=kwargs["running_callback"],
                finished_callback=kwargs["finished_callback"],
                error_callback=kwargs["error_callback"],
                new_page_callback=kwargs["new_page_callback"],
            ),
            cancelled_callback=lambda response: self._scan_pages_cancelled_callback(
                response,
                finished_callback=kwargs["finished_callback"],
            ),
        )

    def _scan_pages_cancelled_callback(self, response, **kwargs):
        """Handle a page transfer interrupted by a cancel: terminate the session cleanly."""
        # the queued "cancel" request terminates the device session via do_cancel;
        # the partial page was never handed to new_page_callback
        if kwargs["finished_callback"] is not None:
            kwargs["finished_callback"](response)

    def scan_pages(self, *, cancel_between_pages=False, **kwargs):
        """Scan pages."""
        self.num_pages_scanned = 0
        self.num_pages = kwargs["num_pages"]
        _set_default_callbacks(kwargs)
        return self.scan_page(
            cancel_between_pages=cancel_between_pages,
            started_callback=kwargs["started_callback"],
            running_callback=kwargs["running_callback"],
            error_callback=kwargs["error_callback"],
            finished_callback=lambda response: self._scan_pages_finished_callback(
                response,
                cancel_between_pages=cancel_between_pages,
                running_callback=kwargs["running_callback"],
                finished_callback=kwargs["finished_callback"],
                error_callback=kwargs["error_callback"],
                new_page_callback=kwargs["new_page_callback"],
            ),
            cancelled_callback=lambda response: self._scan_pages_cancelled_callback(
                response,
                finished_callback=kwargs["finished_callback"],
            ),
        )

    def close_device(self, **kwargs):
        """Close device."""
        return self.send("close_device", **kwargs)

    def quit(self, **kwargs):
        """Quit."""
        return self.send("quit", **kwargs)

    def cancel(self, **kwargs):
        """Flag the scan routine to abort."""
        # drop queued requests, notifying their requesters
        self.drain_cancelled_requests()

        # Mark the transfer as deliberately cancelled before anything else:
        # whatever the backend reports for the interrupted page (a cancelled
        # status, or an error like "Invalid argument" on backends whose
        # sane_cancel is not safe to call from another thread), the failure
        # is classified as CANCELLED by handler_wrapper and never surfaced
        # as an error to the user.
        self._cancel_requested = True

        # Queue the cancel request first, so that the serialized do_cancel
        # runs even if the best-effort direct call below raises.
        request = self.send("cancel", **kwargs)

        # During an active transfer, cancel the device directly from this
        # thread: SANE allows sane_cancel to be called from a thread other
        # than the one blocked in a transfer, and this is what unblocks the
        # worker's snap() call so that an in-flight page is interrupted.
        # Some backends raise on a cross-thread cancel racing a read, so this
        # call is best-effort; the queued cancel request already guarantees
        # the session is torn down by the worker.
        if self._scan_active and self.device_handle is not None:
            try:
                self.device_handle.cancel()
            except Exception:
                logger.exception("Error cancelling device")
        return request


def decode_info(info):
    """Decode the info binary mask for logs that are easier to read."""
    if info == 0:
        return "none"
    opts = ["INEXACT", "RELOAD_OPTIONS", "RELOAD_PARAMS"]
    this = []

    # number of binary digits required
    num = math.log2(info)
    num = int(num) + (1 if num > int(num) else 0)

    i = len(opts)
    while num > i:
        if info >= 2 ** (num - 1):
            this.append("?")
            info -= 2 ** (num - 1)
        num -= 1

    while num > -1:
        if info >= 2**num:
            this.append(opts[num])
            info -= 2**num
        num -= 1

    return " + ".join(this)

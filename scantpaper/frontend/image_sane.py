import math
import os
from basethread import BaseThread
import sane
import uuid
import tempfile  # To create temporary files

BUFFER_SIZE = 32 * 1024  # default size
_POLL_INTERVAL = 100  # ms
_8_BIT = 8
MAXVAL_8_BIT = 2 ** _8_BIT - 1
_16_BIT = 16
MAXVAL_16_BIT = 2 ** _16_BIT - 1
LARGE_STATUS = 99
NOT_FOUND = -1
uuid_object = uuid.uuid1()

(prog_name, logger, callback, _self) = (None, None, {}, None)


class SaneThread(BaseThread):
    "SANE thread class"

    device_handle = None
    device_name = None

    def do_get_devices(self):
        return sane.get_devices()

    def do_open_device(self, device_name):
        print(f"in do_open_device {device_name}")

        # close the handle if it is open
        if self.device_handle is not None:
            self.device_handle = None
            sane.exit()

        print(f"before sane.open {device_name}")
        self.device_handle = sane.open(device_name)
        print(f"after sane.open {device_name}")
        self.device_name = device_name

        # https://stackoverflow.com/questions/40909762/implementing-custom-ouput-logging-from-multiple-threads-in-python
        # logger.debug(f"opened device '{self.device_name}'")
        print(f"leaving do_open_device {device_name}")

    def do_get_options(self):
        return self.device_handle.get_options()

    def do_set_option(self, key, value):
        return self.device_handle.__setattr__(key, value)

    def do_scan_page(self):
        print("in do_scan_page")
        if self.device_handle is None:
            raise ValueError("must open device before starting scan")
        print("before scan")
        return self.device_handle.scan()
        print("after scan")

    def do_cancel(self):

        if self.device_handle is not None:
            self.device_handle.cancel()
        # self.return.enqueue(
        # { "type" : 'cancelled', "uuid" : uuid } )

    def get_devices(
        self,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
    ):

        # uuid = str(uuid_object())
        # callback[uuid]["started"]  = started_callback
        # callback[uuid]["running"]  = running_callback
        # callback[uuid]["finished"] = finished_callback
        return self.send(
            "get_devices",
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )
        # _monitor_process( sentinel, uuid )

    def open_device(
        self,
        device_name,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
    ):
        print(f"in open_device {device_name}")
        # uuid = str(uuid_object())
        # callback[uuid]["started"]  = options["started_callback"]
        # callback[uuid]["running"]  = options["running_callback"]
        # def anonymous_02():
        #     _self["device_name"] = options["device_name"]
        #     options["finished_callback"]()

        # callback[uuid]["finished"] = anonymous_02
        # callback[uuid]["error"] = options["error_callback"]
        # sentinel =       _enqueue_request( 'open',
        #     { "uuid" : uuid, "device_name" : options["device_name"] } )
        return self.send(
            "open_device",
            device_name,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )
        # _monitor_process( sentinel, uuid )

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


def is_connected():
    return "device_name" in _self


def device():
    return _self["device_name"]


def close_device(_class, options):

    uuid = str(uuid_object())
    callback[uuid]["started"] = options["started_callback"]
    callback[uuid]["running"] = options["running_callback"]

    def anonymous_03():
        _self["device_name"] = options["device_name"]
        options["finished_callback"]()

    callback[uuid]["finished"] = anonymous_03
    callback[uuid]["error"] = options["error_callback"]
    sentinel = _enqueue_request(
        "close", {"uuid": uuid, "device_name": options["device_name"]}
    )
    _monitor_process(sentinel, uuid)


def cancel_scan(self, callback):
    """Flag the scan routine to abort"""

    # "" process queue first to stop any new process from starting

    logger.info('""ing process queue')
    while _self["requests"].dequeue_nb():
        pass

    # Then send the thread a cancel signal

    _self["abort_scan"] = 1
    uuid = str(uuid_object())
    callback[uuid]["cancelled"] = callback

    # Add a cancel request to ensure the reply is not blocked

    logger.info("Requesting cancel")
    sentinel = _enqueue_request("cancel", {"uuid": uuid})
    _monitor_process(sentinel, uuid)


def _thaw_deref(ref):

    if ref is not None:
        ref = thaw(ref)
        if type(ref) == "SCALAR":
            ref = ref

    return ref


def check_return_queue():
    while True:
        data = _self["return"].dequeue_nb()
        if data is None:
            break
        if "type" not in data:
            logger.error(f"Bad data bundle {data} in return queue.")
            continue

        if "uuid" not in data:
            logger.error("Bad uuid in return queue.")
            continue

        # if we have pressed the cancel button, ignore everything in the returns
        # queue until it flags 'cancelled'.

        if _self["cancel"]:
            if data["type"] == "cancelled":
                _self["cancel"] = False
                if "cancelled" in callback[data["uuid"]]:
                    callback[data["uuid"]]["cancelled"](_thaw_deref(data["info"]))
                    del callback[data["uuid"]]

            else:
                continue

        if data["type"] == "error":
            if data["status"] == "STATUS_NO_DOCS":
                data["type"] = "finished"

            else:
                if "error" in callback[data["uuid"]]:
                    callback[data["uuid"]]["error"](data["message"], data["status"])
                    del callback[data["uuid"]]

                return Glib.SOURCE_CONTINUE

        if data["type"] == "finished":
            if "started" in callback[data["uuid"]]:
                callback[data["uuid"]]["started"]()

            if "finished" in callback[data["uuid"]]:
                if data["process"] == "set-option":
                    callback[data["uuid"]]["finished"](data["info"], data["status"])

                else:
                    callback[data["uuid"]]["finished"](
                        _thaw_deref(data["info"]), data["status"]
                    )

                del callback[data["uuid"]]

    return Glib.SOURCE_CONTINUE


def _log2(n):

    return math.log(n) / math.log(2)


def decode_info(info):

    if info == 0:
        return "none"
    opts = ["SANE_INFO_INEXACT", "SANE_INFO_RELOAD_OPTIONS", "SANE_INFO_RELOAD_PARAMS"]
    this = []
    n = _log2(info)
    if n > int(n):
        n = int(n) + 1

    i = opts
    while n > i:
        if info >= 2 ** (n - 1):
            this.append("?")
            info -= 2 ** (n - 1)

        n -= 1

    while n > NOT_FOUND:
        if info >= 2 ** n:
            this.append(opts[n])
            info -= 2 ** n

        n -= 1

    return " + ".join(this)


def _thread_main(self):

    for request in self["requests"].dequeue():

        # Signal the sentinel that the request was started.

        request["sentinel"] += 1
        if request["action"] == "quit":
            break
        elif request["action"] == "get-devices":
            do_get_devices(self, request["uuid"])

        elif request["action"] == "open":
            do_open_device(self, request["uuid"], request["device_name"])

        elif request["action"] == "close":
            if self.device_handle is not None:
                logger.debug(f"closing device '{self}->{device_name}'")
                self.device_handle = None

            else:
                logger.debug("Ignoring close_device() call - no device open.")

        elif request["action"] == "get-options":
            do_get_options(self, request["uuid"])

        elif request["action"] == "set-option":
            do_set_option(self, request["uuid"], request["index"], request["value"])

        elif request["action"] == "scan-page":
            do_scan_page(self, request["uuid"], request["path"])

        elif request["action"] == "cancel":
            do_cancel(self, request["uuid"])
        else:
            logger.info(f"Ignoring unknown request {_}")
            continue

        # Signal the sentinel that the request was completed.

        request["sentinel"] += 1


def do_write_pnm_header(fh, format, width, height, depth):

    # The netpbm-package does not define raw image data with maxval > 255.
    # But writing maxval 65535 for 16bit data gives at least a chance
    # to read the image.

    if (
        format == "FRAME_RED"
        or format == "FRAME_GREEN"
        or format == "FRAME_BLUE"
        or format == "FRAME_RGB"
    ):
        fh.write(
            "P6\n# SANE data follows\n%d %d\n%d\n"
            % (width, height, MAXVAL_16_BIT if (depth > _8_BIT) else MAXVAL_8_BIT)
        )

    else:
        if depth == 1:
            fh.write("P4\n# SANE data follows\n%d %d\n" % (width, height))

        else:
            fh.write(
                "P5\n# SANE data follows\n%d %d\n%d\n"
                % (width, height, MAXVAL_16_BIT if (depth > _8_BIT) else MAXVAL_8_BIT)
            )


def do_scan_page_to_fh(device, fh):

    first_frame = 1
    offset = 0
    must_buffer = 0
    (image, status) = ({}, None)
    format_name = ["gray", "RGB", "red", "green", "blue"]
    total_bytes = 0
    (parm, last_frame) = (None, None)
    while not last_frame:
        status = "STATUS_GOOD"
        if not first_frame:
            try:
                device.start()

            except:
                status = _.status()
                logger.info(f"{prog_name}: sane_start: " + _.error())

            if status != "STATUS_GOOD":
                cleanup(parm, total_bytes)

        try:
            parm = device.get_parameters()

        except:
            status = _.status()
            logger.info(f"{prog_name}: sane_get_parameters: " + _.error())

        if status != "STATUS_GOOD":
            cleanup(parm, total_bytes)
        _log_frame_info(first_frame, parm, format_name)
        (must_buffer, offset) = _initialise_scan(fh, first_frame, parm)
        hundred_percent = _scan_data_size(parm)
        while True:

            # Pick up flag from cancel_scan()

            if _self["abort_scan"]:
                device.cancel()
                logger.info("Scan cancelled")
                return "STATUS_CANCELLED"

            (buffer, len) = (None, None)
            try:
                (buffer, len) = device.read(BUFFER_SIZE)
                total_bytes += len

            except:
                status = _.status()
                logger.info(f"{prog_name}: sane_read: " + _.error())

            progr = total_bytes / hundred_percent
            if progr > 1:
                progr = 1
            _self["scan_progress"] = progr
            if status != "STATUS_GOOD":
                if parm["depth"] == _8_BIT:
                    logger.info(
                        f"{prog_name}: min/max graylevel value = %d/%d"
                        % (MAXVAL_8_BIT, 0)
                    )

                if status != "STATUS_EOF":
                    return status
                break

            if must_buffer:
                offset = _buffer_scan(offset, parm, image, len, buffer)

            else:
                if not data:
                    cleanup(parm, total_bytes)
                fh.write(buffer)

        first_frame = 0
        last_frame = parm["last_frame"]

    if must_buffer:
        _write_buffer_to_fh(fh, parm, image)
        cleanup(parm, total_bytes)

    return status


def cleanup(parm, total_bytes):
    expected_bytes = parm["bytes_per_line"] * parm["lines"] * _number_frames(parm)
    if parm["lines"] < 0:
        expected_bytes = 0
    if total_bytes > expected_bytes and expected_bytes != 0:
        logger.info(
            "%s: WARNING: read more data than announced by backend "
            + "(%u/%u)" % (prog_name, total_bytes, expected_bytes)
        )

    else:
        logger.info("%s: read %u bytes in total" % (prog_name, total_bytes))


def _log_frame_info(first_frame, parm, format_name):

    if first_frame:
        if parm["lines"] >= 0:
            logger.info(
                f"{prog_name}: scanning image of size %dx%d pixels at "
                + "%d bits/pixel"
                % (
                    parm["pixels_per_line"],
                    parm["lines"],
                    _8_BIT * parm["bytes_per_line"] / parm["pixels_per_line"],
                )
            )

        else:
            logger.info(
                f"{prog_name}: scanning image %d pixels wide and "
                + "variable height at %d bits/pixel"
                % (
                    parm["pixels_per_line"],
                    _8_BIT * parm["bytes_per_line"] / parm["pixels_per_line"],
                )
            )

        logger.info(
            f"{prog_name}: acquiring %s frame"
            % (
                format_name[parm["format"]]
                if parm["format"] <= "FRAME_BLUE"
                else "Unknown"
            )
        )


def _initialise_scan(fh, first_frame, parm):

    (must_buffer, offset) = (None, None)
    if first_frame:
        if (
            parm["format"] == "FRAME_RED"
            or parm["format"] == "FRAME_GREEN"
            or parm["format"] == "FRAME_BLUE"
        ):
            if parm["depth"] != _8_BIT:
                raise f"Red/Green/Blue frames require depth={_8_BIT}\n"

            must_buffer = 1
            offset = parm["format"] - "FRAME_RED"

        elif parm["format"] == "FRAME_RGB":
            if parm["depth"] != _8_BIT:
                raise f"RGB frames require depth={_8_BIT} or {_16_BIT}\n"

        if parm["format"] == "FRAME_RGB" or parm["format"] == "FRAME_GRAY":
            if parm["depth"] != 1:
                raise f"Valid depths are 1, {_8_BIT} or {_16_BIT}\n"

            if parm["lines"] < 0:
                must_buffer = 1
                offset = 0

            else:
                do_write_pnm_header(
                    fh,
                    parm["format"],
                    parm["pixels_per_line"],
                    parm["lines"],
                    parm["depth"],
                )

    else:
        if parm["format"] < "FRAME_RED" or parm["format"] > "FRAME_BLUE":
            raise "Encountered unknown format\n"
        offset = parm["format"] - "FRAME_RED"

    return (must_buffer, offset)


def _scan_data_size(parm):
    """Return size of final scan (ignoring header)"""
    return parm["bytes_per_line"] * parm["lines"] * _number_frames(parm)


def _number_frames(parm):
    """Return number of frames"""
    return (
        1 if (parm["format"] == "FRAME_RGB" or parm["format"] == "FRAME_GRAY") else 3
    )  ## no critic (ProhibitMagicNumbers)


def _buffer_scan(offset, parm, image, len, buffer):
    """We're either scanning a multi-frame image or the
    scanner doesn't know what the eventual image height
    will be (common for hand-held scanners).  In either
    case, we need to buffer all data before we can write
    the header"""
    number_frames = _number_frames(parm)
    for _ in range(len(buffer)):
        image["data"][offset + number_frames * _] = buffer[_]

    offset += number_frames * len
    return offset


def _write_buffer_to_fh(fh, parm, image):

    if parm["lines"] > 0:
        image["height"] = parm["lines"]

    else:
        image["height"] = len(image["data"]) / parm["bytes_per_line"]
        image["height"] /= _number_frames(parm)

    do_write_pnm_header(
        fh, parm["format"], parm["pixels_per_line"], image["height"], parm["depth"]
    )
    for data in image["data"]:
        if not data:
            cleanup(parm, total_bytes)
        fh.write(data)

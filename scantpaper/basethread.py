"A thread backed by internal queues for simple messaging"

import collections
import contextlib
import logging
import os
import queue
import threading
import uuid
import weakref
from enum import Enum

from gi.repository import GLib

logger = logging.getLogger(__name__)

_RUNNING_TICK_MS = 200

Response = collections.namedtuple(
    "Response",
    [
        "type",
        "request",
        "info",
        "status",
        "num_completed_jobs",
        "total_jobs",
        "pending",
    ],
)  # , "pid"
ResponseTypes = ["QUEUED", "STARTED", "FINISHED", "CANCELLED", "ERROR", "DATA"]
ResponseType = Enum("ResponseType", ResponseTypes)

CALLBACKS = ["queued", "started", "running", "data", "finished", "cancelled", "error"]


class Request:
    "Attributes and methods around requests"

    def __init__(
        self, process_name, process_args, return_queue, *args, notify_cb=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.process = process_name
        self.uuid = uuid.uuid1()
        self.args = process_args
        self.return_queue = return_queue
        self._notify_cb = notify_cb

    def put(self, info, rtype=ResponseType.FINISHED, status=None):
        "put a response on the return queue"
        if self.return_queue is not None:
            self.return_queue.put(
                Response(
                    type=rtype,
                    request=self,
                    info=info,
                    status=status,
                    num_completed_jobs=None,
                    total_jobs=None,
                    pending=None,
                )
            )
        if self._notify_cb is not None:
            self._notify_cb()

    def queued(self, info=None, status=None):
        "queued notification"
        self.put(info, ResponseType.QUEUED, status)

    def started(self, info=None, status=None):
        "started notification"
        self.put(info, ResponseType.STARTED, status)

    def finished(self, info=None, status=None):
        "finished notification"
        self.put(info, ResponseType.FINISHED, status)

    def error(self, info=None, status=None):
        "error notification"
        self.put(info, ResponseType.ERROR, status)

    def cancelled(self, info=None, status=None):
        "cancelled notification"
        self.put(info, ResponseType.CANCELLED, status)

    def data(self, info, status=None):
        "pass data back to main thread"
        self.put(info, ResponseType.DATA, status)


class BaseThread(threading.Thread):
    "A thread backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.requests = queue.Queue()
        self.responses = queue.Queue()
        self.callbacks = {}
        self.additional_callbacks = {}
        self.before = {}
        self.after = {}
        self.num_completed_jobs = 0
        self.total_jobs = 0
        self._notify_r, self._notify_w = os.pipe()
        os.set_blocking(self._notify_r, False)
        os.set_blocking(self._notify_w, False)
        self._finalizer = weakref.finalize(self, self._cleanup_thread, self.requests)
        self._io_watch_id = GLib.io_add_watch(
            self._notify_r, GLib.PRIORITY_DEFAULT, GLib.IO_IN, self._on_readable
        )
        self._tick_id = GLib.timeout_add(_RUNNING_TICK_MS, self._tick)
        for callback in CALLBACKS:
            self.before[callback] = set()
            self.after[callback] = set()

    @staticmethod
    def _cleanup_thread(requests_queue):
        "cleanup function that does not hold a reference to self"
        try:
            # We don't need a response queue for finalization
            request = Request("quit", [], None)
            requests_queue.put(request)
        except Exception:  # noqa: BLE001
            # S110, BLE001 — swallowed intentionally: during interpreter shutdown
            # the queue may be closed/None, logging is unreliable there, and
            # requests_queue.put() can raise arbitrary errors, so we ignore them.
            pass

    def _release_sources(self):
        "schedule removal of GLib sources and pipe FDs on the main thread"

        def _cleanup():
            GLib.source_remove(self._io_watch_id)
            GLib.source_remove(self._tick_id)
            with contextlib.suppress(OSError):
                os.close(self._notify_r)
            with contextlib.suppress(OSError):
                os.close(self._notify_w)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_cleanup)

    def _notify(self):
        "wake up the GLib main loop to process responses"
        with contextlib.suppress(OSError):
            os.write(self._notify_w, b"\x01")

    def _on_readable(self, _fd, _condition):
        "called when the notification pipe is readable"
        try:
            while True:
                os.read(self._notify_r, 1024)
        except BlockingIOError:
            pass
        self.monitor()
        return GLib.SOURCE_CONTINUE

    def _tick(self):
        "periodic tick for running callbacks (progress reporting)"
        self._execute_callbacks_for_stage("running", None)
        return GLib.SOURCE_CONTINUE

    def quit(self):
        "quit the thread"
        return self.send("quit")

    def input_handler(self, request):
        "dummy input handler to be overridden as required"
        return request.args

    def do_quit(self, _request):
        "quit function does nothing"

    def register_callback(self, name, when, reference_cb):
        """register a callback, giving it a name, and defining whether it
        should be triggered before or after the reference callback"""
        if when not in ["before", "after"]:
            msg = "when can only be 'before' or 'after'"
            raise ValueError(msg)
        if reference_cb not in [
            "queued",
            "started",
            "running",
            "data",
            "cancelled",
            "finished",
        ]:
            msg = (
                "reference_cb can only be 'queued', 'started', 'running', "
                "'data', 'cancelled', or 'finished'"
            )
            raise ValueError(msg)
        getattr(self, when)[reference_cb].add(name)
        self.additional_callbacks[name] = when, reference_cb

    def send(
        self,
        process,
        *args,
        **kwargs,
    ):
        "Puts the process and args as a `Request` on the requests queue"
        request = Request(process, args, self.responses, notify_cb=self._notify)
        callbacks = {"started": False}
        for callback in CALLBACKS:
            name = callback + "_callback"
            if name in kwargs:
                callbacks[name] = kwargs[name]
        for k, val in kwargs.items():
            if k[:-9] in self.additional_callbacks:
                callbacks[k] = val
            # Non-callback kwargs (e.g. a pidfile for a get_file_info request)
            # are attached to the request so the handler can reach them.
            elif k not in callbacks:
                setattr(request, k, val)
        if not self.callbacks:
            self.total_jobs = 0
            self.num_completed_jobs = 0
        self.callbacks[request.uuid] = callbacks
        self.requests.put(request)
        self.total_jobs += 1
        request.queued()
        self._notify()
        return request.uuid

    def run(self):
        "override the run() method of threading. Not called directly here"
        while True:
            request = self.requests.get()
            request.started()
            request.args = self.input_handler(request)
            handler = getattr(self, f"do_{request.process}", None)
            if handler is None:
                request.error(None, f"no handler for [{request.process}]")
            elif not self.handler_wrapper(request, handler):
                break
            self.requests.task_done()
        self._release_sources()

    def handler_wrapper(self, request, handler):
        "separate the handler wrapper logic so that it can be overriden by subclasses"
        try:
            request.finished(handler(request))
            if request.process == "quit":
                return False
            self._request_completed(request)
        except Exception as err:
            # BLE001 — the handler is a do_<process> method that may raise
            # arbitrary exceptions from external code (SANE, file I/O, ...),
            # so no narrower set can be caught; the error is wrapped and
            # returned to the caller via request.error() below.
            logger.exception(
                "Error running process '%s': %s",
                request.process,
                err,
            )
            self._request_completed(request)
            request.error(None, str(err))
        return True

    def _request_completed(self, _request):
        "hook called when a request's handler has finished or failed"

    def drain_cancelled_requests(self):
        "emit a CANCELLED response for every request still queued and unstarted"
        drained = []
        while True:
            try:
                drained.append(self.requests.get(False))
            except queue.Empty:
                break
        for request in drained:
            request.cancelled()

    def monitor(self):
        "monitor the thread, triggering one response callback"
        self._execute_callbacks_for_stage("running", None)
        if not self.responses.empty():
            self._monitor_response()
            GLib.idle_add(self._drain_one)
        return GLib.SOURCE_CONTINUE

    def _drain_one(self):
        "Process one response from the queue, scheduling the next if needed"
        self._execute_callbacks_for_stage("running", None)
        if not self.responses.empty():
            self._monitor_response()
            return GLib.SOURCE_CONTINUE
        return GLib.SOURCE_REMOVE

    def _execute_callbacks_for_stage(self, stage, result):
        """helper method to run the callbacks associated with each stage
        (started, running, finished)"""
        if stage == "running":
            for uid, callbacks in self.callbacks.items():
                if callbacks["started"]:
                    self._execute_stage_callbacks(stage, uid, result)
        else:
            self._execute_stage_callbacks(stage, result.request.uuid, result)

    def _execute_stage_callbacks(self, stage, uid, data):
        if uid not in self.callbacks:
            return
        for callback in self.before[stage]:
            self._execute_single_callback(callback + "_callback", stage, uid, data)
        self._execute_single_callback(stage + "_callback", stage, uid, data)
        for callback in self.after[stage]:
            self._execute_single_callback(callback + "_callback", stage, uid, data)

    def _execute_single_callback(self, callback, stage, uid, data):
        if data is not None:
            data = data._replace(
                num_completed_jobs=self.num_completed_jobs,
                total_jobs=self.total_jobs,
                pending=not self.requests.empty(),
            )
        if (
            callback in self.callbacks[uid]
            and self.callbacks[uid][callback] is not None
        ):
            try:
                self.callbacks[uid][callback](data)
            except Exception as err:
                # BLE001 — the callback is user-supplied arbitrary code that
                # can raise anything, so no narrower set is catchable; the
                # error is routed to the caller's error_callback below.
                logger.exception(
                    "Error running %s callback '%s' for process '%s' with args: %s: %s",
                    stage,
                    callback,
                    data.request.process,
                    data.request.args,
                    err,
                )
                if (
                    callback != "error_callback"
                    and "error_callback" in self.callbacks[uid]
                    and self.callbacks[uid]["error_callback"] is not None
                ):
                    data = data._replace(status=str(err))
                    self.callbacks[uid]["error_callback"](data)

    def _monitor_response(self):
        try:
            result = self.responses.get(False)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        stage = result.type.name.lower()
        callback = stage + "_callback"
        uid = result.request.uuid
        if uid in self.callbacks and callback not in [
            "queued_callback",
            "started_callback",
            "data_callback",
        ]:
            # The request has reached a terminal state, so stop invoking its
            # running callback before dispatching the terminal callback. This
            # prevents a modal dialog opened from within the callback from
            # keeping the progress bar pulsing in its nested main loop.
            self.callbacks[uid]["started"] = False
        self._execute_callbacks_for_stage(stage, result)
        if uid in self.callbacks:
            if callback in ["queued_callback", "started_callback", "data_callback"]:
                if callback in self.callbacks[uid] and callback != "data_callback":
                    del self.callbacks[uid][callback]
                if callback == "started_callback":
                    self.callbacks[uid]["started"] = True
                elif callback == "data_callback":
                    logger.info(
                        "process %s sent '%s'", result.request.process, result.info
                    )
            else:  # finished, cancelled, error
                del self.callbacks[uid]
                self.num_completed_jobs += 1
                return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

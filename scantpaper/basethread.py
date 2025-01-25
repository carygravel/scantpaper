"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from enum import Enum
import uuid
import logging
import weakref
from gi.repository import GLib

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

logger = logging.getLogger(__name__)

CALLBACKS = ["queued", "started", "running", "data", "finished", "error"]


class Request:
    "Attributes and methods around requests"

    def __init__(self, process_name, process_args, return_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = process_name
        self.uuid = uuid.uuid1()
        self.args = process_args
        self.return_queue = return_queue

    def put(self, info, rtype=ResponseType.FINISHED, status=None):
        "put a response on the return queue"
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
        self._finalizer = weakref.finalize(self, self.quit)
        for callback in CALLBACKS:
            self.before[callback] = set()
            self.after[callback] = set()

    def quit(self):
        "called automatically by weakref.finalize() when thread is destroyed"
        return self.send("quit")

    def input_handler(self, request):  # pylint: disable=no-self-use
        "dummy input handler to be overridden as required"
        return request.args

    def do_quit(self, _request):
        "quit function does nothing"

    def register_callback(self, name, when, reference_cb):
        """register a callback, giving it a name, and defining whether it
        should be triggered before or after the reference callback"""
        if when not in ["before", "after"]:
            raise ValueError("when can only be 'before' or 'after'")
        if reference_cb not in ["queued", "started", "running", "data", "finished"]:
            raise ValueError(
                "reference_cb can only be 'queued', 'started', 'running', 'data', or 'finished'"
            )
        getattr(self, when)[reference_cb].add(name)
        self.additional_callbacks[name] = when, reference_cb

    def send(
        self,
        process,
        *args,
        **kwargs,
    ):
        "Puts the process and args as a `Request` on the requests queue"
        request = Request(process, args, self.responses)
        callbacks = {"started": False}
        for callback in CALLBACKS:
            name = callback + "_callback"
            if name in kwargs:
                callbacks[name] = kwargs[name]
        for k, val in kwargs.items():
            if k[:-9] in self.additional_callbacks:
                callbacks[k] = val
        self.callbacks[request.uuid] = callbacks
        self.requests.put(request)
        self.total_jobs += 1
        request.queued()
        GLib.timeout_add(100, self.monitor)
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
            else:
                if not self.handler_wrapper(request, handler):
                    break
            self.requests.task_done()

    def handler_wrapper(self, request, handler):
        "separate the handler wrapper logic so that it can be overriden by subclasses"
        try:
            request.finished(handler(request))
            if request.process == "quit":
                return False
        except Exception as err:  # pylint: disable=broad-except
            logger.error(
                "Error running process '%s': %s",
                request.process,
                err,
            )
            request.error(None, str(err))
        return True

    def monitor(self, block=False):
        "monitor the thread, triggering callbacks as required"
        if block:
            return self._monitor_response(block)
        # no point in returning if there are still responses
        while not self.responses.empty():
            return self._monitor_response(block)
        self.total_jobs = 0
        return GLib.SOURCE_CONTINUE

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
        for callback in getattr(self, "before")[stage]:
            self._execute_single_callback(callback + "_callback", stage, uid, data)
        self._execute_single_callback(stage + "_callback", stage, uid, data)
        for callback in getattr(self, "after")[stage]:
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
            except Exception as err:  # pylint: disable=broad-except
                logger.error(
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

    def _monitor_response(self, block=False):
        self._execute_callbacks_for_stage("running", None)
        try:
            result = self.responses.get(block)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        stage = result.type.name.lower()
        callback = stage + "_callback"
        self._execute_callbacks_for_stage(stage, result)
        uid = result.request.uuid
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

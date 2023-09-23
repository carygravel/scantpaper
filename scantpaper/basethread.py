"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from enum import Enum
import uuid
import logging
from gi.repository import GLib

Response = collections.namedtuple("Response", ["type", "request", "info", "status"])
ResponseTypes = ["QUEUED", "STARTED", "FINISHED", "CANCELLED", "ERROR", "LOG"]
ResponseType = Enum("ResponseType", ResponseTypes)

logger = logging.getLogger(__name__)


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

    def log(self, info, status=None):
        "logger for basethread"
        self.put(info, ResponseType.LOG, status)


class BaseThread(threading.Thread):
    "A thread backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.requests = queue.Queue()
        self.responses = queue.Queue()
        self.callbacks = {}
        self.additional_callbacks = {}
        self.before = {
            "queued": set(),
            "started": set(),
            "running": set(),
            "logged": set(),
            "finished": set(),
            "error": set(),
        }
        self.after = {
            "queued": set(),
            "started": set(),
            "running": set(),
            "logged": set(),
            "finished": set(),
            "error": set(),
        }

    def do_quit(self):
        "quit function does nothing"

    def register_callback(self, name, when, reference_cb):
        """register a callback, giving it a name, and defining whether it
        should be triggered before or after the reference callback"""
        if when not in ["before", "after"]:
            raise ValueError("when can only be 'before' or 'after'")
        if reference_cb not in ["queued", "started", "running", "finished"]:
            raise ValueError(
                "reference_cb can only be 'queued', 'started', 'running', or 'finished'"
            )
        getattr(self, when)[reference_cb].add(name)
        self.additional_callbacks[name] = when, reference_cb

    def send(
        self,
        process,
        *args,
        queued_callback=None,
        started_callback=None,
        running_callback=None,
        logged_callback=None,
        finished_callback=None,
        error_callback=None,
        **kwargs,
    ):
        "Puts the process and args as a `Request` on the requests queue"
        request = Request(process, args, self.responses)
        callbacks = {
            "queued_callback": queued_callback,
            "started_callback": started_callback,
            "started": False,
            "running_callback": running_callback,
            "logged_callback": logged_callback,
            "finished_callback": finished_callback,
            "error_callback": error_callback,
        }
        for k, val in kwargs.items():
            if k[:-9] in self.additional_callbacks:
                callbacks[k] = val
        self.callbacks[request.uuid] = callbacks
        self.requests.put(request)
        request.queued()
        GLib.timeout_add(100, self.monitor, request.uuid)
        return request.uuid

    def run(self):
        while True:
            request = self.requests.get()
            request.started()
            handler = getattr(self, f"do_{request.process}", None)
            if handler is None:
                request.error(None, f"no handler for [{request.process}]")
            else:
                try:
                    request.finished(handler(request))
                    if request.process == "quit":
                        break
                except Exception as err:  # pylint: disable=broad-except
                    request.error(None, str(err))
            self.requests.task_done()

    def monitor(self, uid, block=False):
        "monitor the thread, triggering callbacks as required"
        if block:
            return self._monitor_response(uid, block)
        # no point in returning if there are still responses
        while not self.responses.empty():
            return self._monitor_response(uid, block)

    def _run_callbacks(self, uid, stage, data=None):
        """helper method to run the callbacks associated with each stage
        (started, running, finished)"""
        if uid is None or uid not in self.callbacks:
            return
        if stage == "running" and not self.callbacks[uid]["started"]:
            return
        for callback in getattr(self, "before")[stage]:
            if callback + "_callback" in self.callbacks[uid]:
                self.callbacks[uid][callback + "_callback"](data)
        if (
            stage + "_callback" in self.callbacks[uid]
            and self.callbacks[uid][stage + "_callback"] is not None
        ):
            self.callbacks[uid][stage + "_callback"](data)
        for callback in getattr(self, "after")[stage]:
            if callback + "_callback" in self.callbacks[uid]:
                self.callbacks[uid][callback + "_callback"](data)

    def _monitor_response(self, uid, block=False):
        self._run_callbacks(uid, "running")
        try:
            result = self.responses.get(block)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        stage = ResponseTypes[result.type.value - 1].lower()
        if stage == "log":
            stage = "logged"
        callback = stage + "_callback"
        self._run_callbacks(uid, stage, result)
        if uid in self.callbacks:
            if callback in ["queued_callback", "started_callback", "logged_callback"]:
                if callback in self.callbacks[uid]:
                    del self.callbacks[uid][callback]
                if callback == "started_callback":
                    self.callbacks[uid]["started"] = True
                elif callback == "logged_callback":
                    logger.info(
                        "process %s sent '%s'", result.request.process, result.info
                    )
            else:  # finished, cancelled, error
                del self.callbacks[uid]
                return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

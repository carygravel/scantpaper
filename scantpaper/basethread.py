"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from enum import Enum
import uuid
import logging
from gi.repository import GLib

Request = collections.namedtuple("Request", ["event", "uuid", "args"])
Response = collections.namedtuple(
    "Response", ["type", "process", "uuid", "info", "status"]
)
ResponseTypes = ["STARTED", "FINISHED", "CANCELLED", "ERROR", "LOG"]
ResponseType = Enum("ResponseType", ResponseTypes)

logger = logging.getLogger(__name__)


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
            "started": set(),
            "running": set(),
            "finished": set(),
            "error": set(),
        }
        self.after = {
            "started": set(),
            "running": set(),
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
        if reference_cb not in ["started", "running", "finished"]:
            raise ValueError(
                "reference_cb can only be 'started', 'running', or 'finished'"
            )
        getattr(self, when)[reference_cb].add(name)
        self.additional_callbacks[name] = when, reference_cb

    def send(
        self,
        event,
        *args,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
        **kwargs,
    ):
        "Puts the event and args as a `Request` on the requests queue"
        request = Request(event, uuid.uuid1(), args)
        callbacks = {
            "started_callback": started_callback,
            "started": False,
            "running_callback": running_callback,
            "finished_callback": finished_callback,
            "error_callback": error_callback,
        }
        for k, val in kwargs.items():
            if k[:-9] in self.additional_callbacks:
                callbacks[k] = val
        self.callbacks[request.uuid] = callbacks
        self.requests.put(request)
        GLib.timeout_add(100, self.monitor, request.uuid)
        return request.uuid

    def log(self, event="", info="", uid="", status=""):
        "logger for basethread"
        self.responses.put(
            Response(
                type=ResponseType.LOG,
                process=event,
                info=info,
                uuid=uid,
                status=status,
            )
        )

    def run(self):
        while True:
            event, uid, args = self.requests.get()
            self.responses.put(
                Response(
                    type=ResponseType.STARTED,
                    process=event,
                    info=None,
                    uuid=uid,
                    status=None,
                )
            )
            handler = getattr(self, f"do_{event}", None)
            if handler is None:
                self.responses.put(
                    Response(
                        type=ResponseType.ERROR,
                        process=event,
                        info=None,
                        uuid=uid,
                        status=f"no handler for [{event}]",
                    )
                )
            else:
                try:
                    self.responses.put(
                        Response(
                            type=ResponseType.FINISHED,
                            process=event,
                            info=handler(*args),
                            uuid=uid,
                            status=None,
                        )
                    )
                    if event == "quit":
                        break
                except Exception as err:  # pylint: disable=broad-except
                    self.responses.put(
                        Response(
                            type=ResponseType.ERROR,
                            process=event,
                            info=None,
                            uuid=uid,
                            status=str(err),
                        )
                    )
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
        if ResponseTypes[result.type.value - 1] == "LOG":
            logger.info("process %s sent '%s'", result.process, result.info)
            return GLib.SOURCE_CONTINUE
        stage = ResponseTypes[result.type.value - 1].lower()
        callback = stage + "_callback"
        self._run_callbacks(uid, stage, result)
        if callback == "started_callback":
            del self.callbacks[uid][callback]
            self.callbacks[uid]["started"] = True
        else:  # finished, cancelled, error
            if uid in self.callbacks:
                del self.callbacks[uid]
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

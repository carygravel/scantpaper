"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from enum import Enum
import uuid
from gi.repository import GLib

Request = collections.namedtuple("Request", ["event", "uuid", "args"])
Response = collections.namedtuple(
    "Response", ["type", "process", "uuid", "info", "status"]
)
ResponseTypes = ["STARTED", "FINISHED", "CANCELLED", "ERROR"]
ResponseType = Enum("ResponseType", ResponseTypes)


class BaseThread(threading.Thread):
    "A thread backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.requests = queue.Queue()
        self.responses = queue.Queue()
        self.callbacks = {}

    def do_quit(self):
        "quit function does nothing"

    def send(
        self,
        event,
        *args,
        started_callback=None,
        running_callback=None,
        finished_callback=None,
        error_callback=None,
    ):
        "Puts the event and args as a `Request` on the requests queue"
        request = Request(event, uuid.uuid1(), args)
        self.callbacks[request.uuid] = {
            "started_callback": started_callback,
            "started": False,
            "running_callback": running_callback,
            "finished_callback": finished_callback,
            "error_callback": error_callback,
        }
        self.requests.put(request)
        GLib.timeout_add(100, self.monitor, request.uuid)
        return request.uuid

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
        if not block:
            # no point in returning if there are still responses
            while not self.responses.empty():
                return self._monitor_response(uid, block)
        else:
            return self._monitor_response(uid, block)

    def _monitor_response(self, uid, block=False):
        if (
            self.callbacks[uid]["started"]
            and "running_callback" in self.callbacks[uid]
            and self.callbacks[uid]["running_callback"] is not None
        ):
            self.callbacks[uid]["running_callback"]()
        try:
            result = self.responses.get(block)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        callback = ResponseTypes[result.type.value - 1].lower() + "_callback"
        if (
            uid == result.uuid
            and uid in self.callbacks
            and callback in self.callbacks[uid]
            and self.callbacks[uid][callback] is not None
        ):
            self.callbacks[uid][callback](result)
            if callback == "started_callback":
                del self.callbacks[uid][callback]
                self.callbacks[uid]["started"] = True
            else:  # finished, cancelled, error
                del self.callbacks[uid]
                return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

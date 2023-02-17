"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from enum import Enum
from gi.repository import GLib

Request = collections.namedtuple("Request", ["event", "args"])
Response = collections.namedtuple(
    "Response", ["type", "process", "uuid", "info", "status"]
)
ResponseType = Enum("ResponseType", ["FINISHED", "CANCELLED", "ERROR"])


class BaseThread(threading.Thread):
    "A thread backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = queue.Queue()
        self.responses = queue.Queue()

    def send(self, event, *args, finished_callback=None):
        "Puts the event and args as a `Request` on the requests queue"
        request = Request(event, args)
        self.requests.put(request)
        GLib.timeout_add(100, self._monitor_thread, finished_callback)

    def run(self):
        while True:
            event, args = self.requests.get()
            if event == "quit":
                break
            handler = getattr(self, f"do_{event}", None)
            if not handler:
                raise NotImplementedError(f"Process has no handler for [{event}]")
            request = handler(*args)
            self.responses.put(request)

    def _monitor_thread(self, finished_callback):
        try:
            result = self.responses.get(False)
            if finished_callback is not None:
                finished_callback(result)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        return GLib.SOURCE_REMOVE

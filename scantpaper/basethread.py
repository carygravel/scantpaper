"A thread backed by internal queues for simple messaging"
import threading
import queue
import collections
from gi.repository import GLib

Msg = collections.namedtuple("Msg", ["event", "args"])


class BaseThread(threading.Thread):
    "A thread backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = queue.Queue()
        self.responses = queue.Queue()

    def send(self, event, *args, finished_callback=None):
        "Puts the event and args as a `Msg` on the requests queue"
        msg = Msg(event, args)
        self.requests.put(msg)
        GLib.timeout_add(100, self._monitor_thread, finished_callback)

    def run(self):
        while True:
            event, args = self.requests.get()
            if event == "quit":
                break
            handler = getattr(self, f"do_{event}", None)
            if not handler:
                raise NotImplementedError(f"Process has no handler for [{event}]")
            msg = handler(*args)
            self.responses.put(msg)

    def _monitor_thread(self, finished_callback):
        try:
            result = self.responses.get(False)
            if finished_callback is not None:
                finished_callback(result)
        except queue.Empty:
            return GLib.SOURCE_CONTINUE
        return GLib.SOURCE_REMOVE

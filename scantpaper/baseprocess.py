"A process backed by internal queues for simple messaging"
import multiprocessing
import collections

Msg = collections.namedtuple("Msg", ["event", "args"])


class BaseProcess(multiprocessing.Process):
    "A process backed by internal queues for simple messaging"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = multiprocessing.Queue()
        self.responses = multiprocessing.Queue()

    def send(self, event, *args):
        "Puts the event and args as a `Msg` on the requests queue"
        msg = Msg(event, args)
        self.requests.put(msg)

    def run(self):
        while True:
            event, args = self.requests.get()
            if event == "quit":
                break
            handler = getattr(self, "do_%s" % event, None)
            if not handler:
                raise NotImplementedError("Process has no handler for [%s]" % event)
            msg = handler(*args)
            self.responses.put(msg)

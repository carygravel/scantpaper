"test basethread class"
from basethread import BaseThread, Response, ResponseType


class MyThread(BaseThread):
    "test thread class"

    response_counter = 0

    def do_div(self, arg1, arg2):  # pylint: disable=no-self-use
        "test method"
        return arg1 / arg2

    def callback(self, response):
        "callback"
        print(
            f"in callback with response {response} response_counter {self.response_counter}",
            flush=True,
        )
        assert response._replace(uuid="") == EXPECTED[self.response_counter], str(
            self.response_counter
        )
        self.response_counter += 1


EXPECTED = [
    Response(type=ResponseType.STARTED, process="div", uuid="", info=None, status=None),
    Response(type=ResponseType.FINISHED, process="div", uuid="", info=0.5, status=None),
    Response(
        type=ResponseType.ERROR,
        process="div",
        uuid="",
        info=None,
        status="division by zero",
    ),
    Response(
        type=ResponseType.ERROR,
        process="nodiv",
        uuid="",
        info=None,
        status="no handler for [nodiv]",
    ),
]


def test_1():
    "test baseprocess class"
    thread = MyThread()
    thread.start()
    thread.send(
        "div", 1, 2, started_callback=thread.callback, finished_callback=thread.callback
    )
    thread.monitor(block=True)  # for started_callback
    assert thread.response_counter == 1, "checked all expected responses #1"
    thread.monitor(block=True)  # for finished_callback
    assert thread.response_counter == 2, "checked all expected responses #2"

    thread.send("div", 1, 0, error_callback=thread.callback)
    thread.monitor(block=True)  # for started_callback
    thread.monitor(block=True)  # for error_callback
    assert thread.response_counter == 3, "checked all expected responses #3"

    thread.send("nodiv", 1, 2, error_callback=thread.callback)
    thread.monitor(block=True)  # for started_callback
    thread.monitor(block=True)  # for error_callback
    assert thread.response_counter == 4, "checked all expected responses #4"

    thread.send("quit")

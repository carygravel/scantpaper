"test basethread class"
from basethread import BaseThread, Response, ResponseType


class MyThread(BaseThread):
    "test thread class"

    response_counter = 0

    def do_div(self, request):  # pylint: disable=no-self-use
        "test method"
        arg1, arg2 = request.args
        request.data("arg1 / arg2")
        return arg1 / arg2

    def callback(self, response=None):
        "callback"
        if response is None:
            assert response == EXPECTED[self.response_counter], str(
                self.response_counter
            )
        else:
            assert (
                response._replace(request="") == EXPECTED[self.response_counter]
            ), str(self.response_counter)
        self.response_counter += 1


EXPECTED = [
    Response(type=ResponseType.QUEUED, request="", info=None, status=None),
    Response(type=ResponseType.STARTED, request="", info=None, status=None),
    None,  # running
    Response(type=ResponseType.DATA, request="", info="arg1 / arg2", status=None),
    None,  # running
    Response(type=ResponseType.FINISHED, request="", info=0.5, status=None),
    Response(
        type=ResponseType.ERROR,
        request="",
        info=None,
        status="division by zero",
    ),
    Response(
        type=ResponseType.ERROR,
        request="",
        info=None,
        status="no handler for [nodiv]",
    ),
    Response(
        type=ResponseType.FINISHED, request="", info=0.5, status=None
    ),  # after_finished
]


def test_1():
    "test baseprocess class"
    thread = MyThread()
    thread.start()
    thread.send(
        "div",
        1,
        2,
        queued_callback=thread.callback,
        started_callback=thread.callback,
        running_callback=thread.callback,
        data_callback=thread.callback,
        finished_callback=thread.callback,
    )
    # FIXME: implement GLib.MainLoop() as per test 103
    thread.monitor(block=True)  # for queued_callback
    assert thread.response_counter == 1, "checked all expected responses #1"
    thread.monitor(block=True)  # for started_callback
    assert thread.response_counter == 2, "checked all expected responses #2"
    thread.monitor(block=True)  # for data_callback
    assert thread.response_counter == 4, "checked all expected responses #3"
    thread.monitor(block=True)  # for finished_callback
    assert thread.response_counter == 6, "checked all expected responses #3"

    thread.send("div", 1, 0, error_callback=thread.callback)
    thread.monitor(block=True)  # for queued_callback
    thread.monitor(block=True)  # for started_callback
    thread.monitor(block=True)  # for error_callback
    assert thread.response_counter == 6, "checked all expected responses #4"

    thread.send("nodiv", 1, 2, error_callback=thread.callback)
    thread.monitor(block=True)  # for queued_callback
    thread.monitor(block=True)  # for started_callback
    thread.monitor(block=True)  # for error_callback
    assert thread.response_counter == 7, "checked all expected responses #5"

    thread.register_callback("after_finished", "after", "finished")
    thread.send("div", 1, 2, after_finished_callback=thread.callback)
    thread.monitor(block=True)  # for queued_callback
    thread.monitor(block=True)  # for started_callback
    thread.monitor(block=True)  # for after_finished_callback
    assert thread.response_counter == 8, "checked all expected responses #6"

    thread.send("quit")

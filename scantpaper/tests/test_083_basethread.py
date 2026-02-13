"test basethread class"

from basethread import BaseThread, Response, ResponseType
from gi.repository import GLib


class MyThread(BaseThread):
    "test thread class"

    def do_div(self, request):  # pylint: disable=no-self-use
        "test method"
        arg1, arg2 = request.args
        request.data("arg1 / arg2")
        return arg1 / arg2


EXPECTED = [
    Response(
        type=ResponseType.QUEUED,
        request="",
        info=None,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    Response(
        type=ResponseType.STARTED,
        request="",
        info=None,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    None,  # running
    Response(
        type=ResponseType.DATA,
        request="",
        info="arg1 / arg2",
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    None,  # running
    Response(
        type=ResponseType.FINISHED,
        request="",
        info=0.5,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    Response(
        type=ResponseType.ERROR,
        request="",
        info=None,
        status="division by zero",
        num_completed_jobs=1,
        total_jobs=2,
        pending=False,
    ),
    Response(
        type=ResponseType.ERROR,
        request="",
        info=None,
        status="no handler for [nodiv]",
        num_completed_jobs=2,
        total_jobs=3,
        pending=False,
    ),
    Response(
        type=ResponseType.FINISHED,
        request="",
        info=0.5,
        status=None,
        num_completed_jobs=3,
        total_jobs=4,
        pending=False,
    ),  # before_finished
    Response(
        type=ResponseType.FINISHED,
        request="",
        info=0.5,
        status=None,
        num_completed_jobs=4,
        total_jobs=5,
        pending=False,
    ),  # after_finished
]


def test_1():
    "test baseprocess class"

    n_callbacks = 0

    def callback(response=None):
        "callback"
        nonlocal n_callbacks
        if response is None:
            assert response == EXPECTED[n_callbacks], str(n_callbacks)
        else:
            assert response._replace(request="") == EXPECTED[n_callbacks], str(
                n_callbacks
            )
        n_callbacks += 1
        if response is not None and response.type == ResponseType.FINISHED:
            mlp.quit()

    thread = MyThread()
    thread.start()
    thread.send(
        "div",
        1,
        2,
        queued_callback=callback,
        started_callback=callback,
        running_callback=callback,
        data_callback=callback,
        finished_callback=callback,
    )

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert n_callbacks == 6, "checked all expected responses #1"

    thread.send("div", 1, 0, error_callback=callback)

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert n_callbacks == 7, "checked all expected responses #2"

    thread.send("nodiv", 1, 2, error_callback=callback)

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert n_callbacks == 8, "checked all expected responses #5"

    thread.register_callback("before_finished", "before", "finished")
    thread.send("div", 1, 2, before_finished_callback=callback)

    thread.register_callback("after_finished", "after", "finished")
    thread.send("div", 1, 2, after_finished_callback=callback)

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert n_callbacks == 8, "checked all expected responses #6"

    thread.send("quit")

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()


def test_empty_queue():
    "test _monitor_response with empty queue"
    thread = BaseThread()
    assert thread._monitor_response(block=False) == GLib.SOURCE_CONTINUE

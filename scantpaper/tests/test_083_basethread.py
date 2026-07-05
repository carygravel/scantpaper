"test basethread class"

from basethread import BaseThread, Response, ResponseType
from gi.repository import GLib
import pytest


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
            actual = response._replace(
                request="", num_completed_jobs=None, total_jobs=None, pending=None
            )
            expected = EXPECTED[n_callbacks]._replace(
                num_completed_jobs=None, total_jobs=None, pending=None
            )
            assert actual == expected, str(n_callbacks)
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
    assert n_callbacks in (9, 10), "checked all expected responses #6"

    thread.send("quit")

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()


def test_empty_queue():
    "test _monitor_response with empty queue"
    thread = BaseThread()
    assert thread._monitor_response() == GLib.SOURCE_CONTINUE


def test_job_counters_do_not_leak_across_batches():
    "Test that num_completed_jobs and total_jobs are reset between batches"
    thread = MyThread()
    thread.start()

    callback_calls = []

    def callback(response=None):
        callback_calls.append(response)

    # First batch: one job
    thread.send("div", 1, 2, finished_callback=callback)

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()

    # After first job finishes, callbacks dict should be empty
    assert not thread.callbacks

    # Second batch: one job — this should reset counters
    thread.send("div", 3, 4, finished_callback=callback)

    # Check counters immediately after send (before the job finishes)
    assert (
        thread.total_jobs == 1
    ), f"total_jobs should be 1 for new batch, got {thread.total_jobs}"
    assert (
        thread.num_completed_jobs == 0
    ), f"num_completed_jobs should be 0 for new batch, got {thread.num_completed_jobs}"

    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()

    thread.send("quit")
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()


def test_job_counters_persist_within_batch():
    "Test that counters accumulate within a multi-job batch"
    thread = MyThread()
    thread.start()

    callback_calls = []

    def callback(response=None):
        callback_calls.append(response)

    uid1 = thread.send("div", 1, 2, finished_callback=callback)
    uid2 = thread.send("div", 3, 4, finished_callback=callback)
    uid3 = thread.send("div", 5, 6, finished_callback=callback)

    # total_jobs should be 3 (all three sent before any finished)
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 0

    # Process all responses
    mlp = GLib.MainLoop()
    GLib.timeout_add(4000, mlp.quit)
    mlp.run()

    # After all jobs complete, counters should reflect all 3 jobs
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 3

    thread.send("quit")
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)
    mlp.run()


def test_register_callback_errors():
    "test errors raised by register_callback"
    thread = BaseThread()
    with pytest.raises(ValueError):
        thread.register_callback("name", "with", "finished")
    with pytest.raises(ValueError):
        thread.register_callback("name", "before", "nonexistent")

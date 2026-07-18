"test basethread class"

import pytest
from basethread import BaseThread, Response, ResponseType
from gi.repository import GLib
from loop_helpers import safe_mainloop


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
        if response is not None and response.type in (
            ResponseType.FINISHED,
            ResponseType.ERROR,
        ):
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

    mlp = safe_mainloop(2000)
    mlp.run()
    assert n_callbacks == 6, "checked all expected responses #1"

    thread.send("div", 1, 0, error_callback=callback)

    mlp = safe_mainloop(2000)
    mlp.run()
    assert n_callbacks == 7, "checked all expected responses #2"

    thread.send("nodiv", 1, 2, error_callback=callback)

    mlp = safe_mainloop(2000)
    mlp.run()
    assert n_callbacks == 8, "checked all expected responses #5"

    thread.register_callback("before_finished", "before", "finished")
    thread.send("div", 1, 2, before_finished_callback=callback)

    thread.register_callback("after_finished", "after", "finished")
    thread.send("div", 1, 2, after_finished_callback=callback)

    mlp = safe_mainloop(2000)
    mlp.run()
    assert n_callbacks in (9, 10), "checked all expected responses #6"

    thread.send("quit", finished_callback=lambda response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_calibrate_env_override(monkeypatch):
    "test _calibrate_poll_interval with a valid SCANTPAPER_POLL_INTERVAL_MS"
    from basethread import _calibrate_poll_interval

    monkeypatch.setenv("SCANTPAPER_POLL_INTERVAL_MS", "25")
    assert _calibrate_poll_interval() == 25

    monkeypatch.setenv("SCANTPAPER_POLL_INTERVAL_MS", "0")
    assert _calibrate_poll_interval() == 5

    monkeypatch.setenv("SCANTPAPER_POLL_INTERVAL_MS", "200")
    assert _calibrate_poll_interval() == 100


def test_calibrate_env_override_invalid(monkeypatch):
    "test _calibrate_poll_interval with non-numeric SCANTPAPER_POLL_INTERVAL_MS"
    from basethread import _calibrate_poll_interval

    monkeypatch.setenv("SCANTPAPER_POLL_INTERVAL_MS", "abc")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    assert _calibrate_poll_interval() == 10


def test_calibrate_benchmark(monkeypatch):
    "test the actual GLib benchmark path"
    from basethread import _calibrate_poll_interval

    monkeypatch.delenv("SCANTPAPER_POLL_INTERVAL_MS", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    result = _calibrate_poll_interval()
    assert 5 <= result <= 100


def test_mainloop_wrapper_getattr():
    "test that __getattr__ proxies to the underlying GLib.MainLoop"
    mlp = safe_mainloop(2000)
    ctx = mlp.get_context()
    assert ctx is not None


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
        if response is not None and response.type == ResponseType.FINISHED:
            mlp.quit()

    # First batch: one job
    thread.send("div", 1, 2, finished_callback=callback)

    mlp = safe_mainloop(2000)
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

    mlp = safe_mainloop(2000)
    mlp.run()

    thread.send("quit", finished_callback=lambda response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_job_counters_persist_within_batch():
    "Test that counters accumulate within a multi-job batch"
    thread = MyThread()
    thread.start()

    callback_calls = []
    n_callbacks = 0

    def callback(response=None):
        nonlocal n_callbacks
        callback_calls.append(response)
        if response is not None and response.type == ResponseType.FINISHED:
            n_callbacks += 1
            if n_callbacks == 3:
                mlp.quit()

    uid1 = thread.send("div", 1, 2, finished_callback=callback)
    uid2 = thread.send("div", 3, 4, finished_callback=callback)
    uid3 = thread.send("div", 5, 6, finished_callback=callback)

    # total_jobs should be 3 (all three sent before any finished)
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 0

    # Process all responses
    mlp = safe_mainloop(4000)
    mlp.run()

    # After all jobs complete, counters should reflect all 3 jobs
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 3

    thread.send("quit", finished_callback=lambda response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_register_callback_errors():
    "test errors raised by register_callback"
    thread = BaseThread()
    with pytest.raises(ValueError):
        thread.register_callback("name", "with", "finished")
    with pytest.raises(ValueError):
        thread.register_callback("name", "before", "nonexistent")


def test_running_callback_on_empty_queue():
    "Test that monitor triggers running callbacks even when response queue is empty"
    from basethread import Request

    thread = BaseThread()
    running_called = []

    def running_cb(_response):
        running_called.append(True)

    # Manually add a callback with started=True so running_cb is eligible
    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {"started": True, "running_callback": running_cb}

    # Call monitor with empty queue — running_cb SHOULD be called
    # because running callbacks should fire on every monitor tick,
    # not only when there are responses to drain
    result = thread.monitor()

    assert result == GLib.SOURCE_CONTINUE
    assert len(running_called) >= 1, (
        "running callback must be called on empty queue; "
        "monitor() only calls _execute_callbacks_for_stage('running', ...) "
        "inside _monitor_response(), which is skipped when queue is empty"
    )


def test_none_callback():
    "test that None callbacks don't cause errors"
    thread = MyThread()
    thread.start()

    errors = []

    def error_callback(response):
        errors.append(response)

    # Send a job with finished_callback explicitly set to None
    # This should not raise an error when the callback is executed
    thread.register_callback("after_finished", "after", "finished")
    thread.send(
        "div",
        1,
        2,
        finished_callback=None,
        error_callback=error_callback,
        after_finished_callback=lambda response: mlp.quit(),
    )

    mlp = safe_mainloop(2000)
    mlp.run()

    # Should not have any errors
    assert not errors, f"Unexpected errors: {errors}"

    thread.send("quit", finished_callback=lambda response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()

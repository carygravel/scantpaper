"test basethread class"

from unittest.mock import MagicMock

import pytest
from basethread import BaseThread, Request, Response, ResponseType
from gi.repository import GLib
from loop_helpers import safe_mainloop


class MyThread(BaseThread):
    "test thread class"

    def do_div(self, request):
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


def test_pipe_notification():
    "test that _notify wakes up the IO watcher and processes responses"
    thread = BaseThread()
    thread.start()

    responses_received = []

    def on_finished(response):
        responses_received.append(response)
        mlp.quit()

    thread.send("quit", finished_callback=on_finished)

    mlp = safe_mainloop(2000)
    mlp.run()
    assert len(responses_received) == 1
    assert responses_received[0].type == ResponseType.FINISHED


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

    error_callback = MagicMock()

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
    error_callback.assert_not_called()

    thread.send("quit", finished_callback=lambda response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_monitor_processes_one_at_a_time():
    "test that monitor processes exactly one response per call"
    from unittest.mock import patch
    from basethread import Request

    thread = BaseThread()
    finished_calls = []

    def finished_cb(response):
        finished_calls.append(response)

    # Manually enqueue two finished responses
    req1 = Request("test", (), thread.responses)
    req2 = Request("test", (), thread.responses)
    thread.callbacks[req1.uuid] = {"started": True, "finished_callback": finished_cb}
    thread.callbacks[req2.uuid] = {"started": True, "finished_callback": finished_cb}
    req1.finished(info="result1")
    req2.finished(info="result2")

    assert thread.responses.qsize() == 2

    # Patch idle_add so it does not actually schedule — we want to call
    # monitor() manually and observe the queue state after one call.
    with patch("basethread.GLib.idle_add"):
        thread.monitor()

    # Exactly one response should have been consumed
    assert len(finished_calls) == 1
    assert finished_calls[0].info == "result1"
    assert thread.responses.qsize() == 1


def test_monitor_schedules_idle_when_responses_remain():
    "test that GLib.idle_add is called when responses still in queue"
    from unittest.mock import patch
    from basethread import Request

    thread = BaseThread()

    req = Request("test", (), thread.responses)
    thread.callbacks[req.uuid] = {"started": True, "finished_callback": lambda r: None}
    req.finished(info="result")

    with patch("basethread.GLib.idle_add") as mock_idle:
        thread.monitor()
        mock_idle.assert_called_once_with(thread._drain_one)


@pytest.mark.parametrize("terminal_type", [ResponseType.FINISHED, ResponseType.ERROR])
def test_running_callback_suppressed_during_terminal_dispatch(mocker, terminal_type):
    "test that running callbacks don't fire while a terminal callback is dispatched"
    from basethread import Request

    thread = BaseThread()
    running_cb = mocker.Mock()
    terminal_dispatched = []

    def terminal_cb(_response):
        # Simulates a nested main loop firing the running stage while the
        # terminal callback is still being processed (e.g. a modal dialog
        # opened from within the error callback)
        thread._execute_callbacks_for_stage("running", None)
        terminal_dispatched.append(True)

    request = Request("test", (), thread.responses)
    stage = terminal_type.name.lower()
    thread.callbacks[request.uuid] = {
        "started": True,
        "running_callback": running_cb,
        stage + "_callback": terminal_cb,
    }
    request.put(info="done", rtype=terminal_type)

    thread._monitor_response()

    assert terminal_dispatched == [True]
    running_cb.assert_not_called()


def test_cleanup_thread_exception_caught(mocker):
    "Test _cleanup_thread catches exceptions from queue.put during interpreter shutdown"
    mock_queue = mocker.Mock()
    mock_queue.put.side_effect = Exception("queue closed")
    BaseThread._cleanup_thread(mock_queue)
    mock_queue.put.assert_called_once()


def test_stage_callback_exception_invokes_error_callback():
    "test that a failing non-error stage callback triggers the error_callback"
    thread = BaseThread()
    error_callback = MagicMock()

    def failing_callback(_response):
        raise ValueError("boom")

    request = Request("div", (1, 2), None)
    data = Response(
        type=ResponseType.FINISHED,
        request=request,
        info=None,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    )
    uid = "test-uid"
    thread.callbacks[uid] = {
        "finished_callback": failing_callback,
        "error_callback": error_callback,
    }

    thread._execute_single_callback("finished_callback", "finished", uid, data)

    error_callback.assert_called_once()
    assert error_callback.call_args[0][0].status == "boom"


def test_release_sources_close_oserror(mocker):
    "Test _release_sources catches OSError from os.close"
    thread = BaseThread()
    thread._io_watch_id = 999999
    thread._tick_id = 999998
    thread._notify_r = 999
    thread._notify_w = 1000

    mock_close = mocker.patch("basethread.os.close", side_effect=OSError)
    thread._release_sources()
    mlp = safe_mainloop(500)
    GLib.timeout_add(100, mlp.quit)
    mlp.run()
    assert mock_close.call_count >= 2

"""test basethread class."""

from __future__ import annotations

import gc
import threading
import weakref
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import GLib
from typing_extensions import override

from scantpaper.basethread import BaseThread, Request, Response, ResponseType
from scantpaper.loop_helpers import safe_mainloop

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable


class MyThread(BaseThread):
    """test thread class."""

    def do_div(self, request: Request) -> float:
        """Test method."""
        arg1, arg2 = request.args
        request.data("arg1 / arg2")
        return cast("float", arg1) / cast("float", arg2)


EXPECTED = [
    Response(
        type=ResponseType.QUEUED,
        request=cast("Request", cast("object", "")),
        info=None,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    Response(
        type=ResponseType.STARTED,
        request=cast("Request", cast("object", "")),
        info=None,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    None,  # running
    Response(
        type=ResponseType.DATA,
        request=cast("Request", cast("object", "")),
        info="arg1 / arg2",
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    None,  # running
    Response(
        type=ResponseType.FINISHED,
        request=cast("Request", cast("object", "")),
        info=0.5,
        status=None,
        num_completed_jobs=0,
        total_jobs=1,
        pending=False,
    ),
    Response(
        type=ResponseType.ERROR,
        request=cast("Request", cast("object", "")),
        info=None,
        status="division by zero",
        num_completed_jobs=1,
        total_jobs=2,
        pending=False,
    ),
    Response(
        type=ResponseType.ERROR,
        request=cast("Request", cast("object", "")),
        info=None,
        status="no handler for [nodiv]",
        num_completed_jobs=2,
        total_jobs=3,
        pending=False,
    ),
    Response(
        type=ResponseType.FINISHED,
        request=cast("Request", cast("object", "")),
        info=0.5,
        status=None,
        num_completed_jobs=3,
        total_jobs=4,
        pending=False,
    ),  # before_finished
    Response(
        type=ResponseType.FINISHED,
        request=cast("Request", cast("object", "")),
        info=0.5,
        status=None,
        num_completed_jobs=4,
        total_jobs=5,
        pending=False,
    ),  # after_finished
]


def test_1() -> None:
    """Test baseprocess class."""
    n_callbacks = 0

    def callback(response: Response | None = None) -> None:
        """React to the callback."""
        nonlocal n_callbacks
        if response is None:
            assert response == EXPECTED[n_callbacks], str(n_callbacks)
        else:
            actual = response._replace(
                request=cast("Request", cast("object", "")),
                num_completed_jobs=None,
                total_jobs=None,
                pending=None,
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

    thread.send("quit", finished_callback=lambda _response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_mainloop_wrapper_getattr() -> None:
    """Test that __getattr__ proxies to the underlying GLib.MainLoop."""
    mlp = safe_mainloop(2000)
    ctx = cast("Callable[[], object]", mlp.get_context)()
    assert ctx is not None


def test_empty_queue() -> None:
    """Test _monitor_response with empty queue."""
    thread = BaseThread()
    assert thread._monitor_response() == GLib.SOURCE_CONTINUE


def test_job_counters_do_not_leak_across_batches() -> None:
    """Test that num_completed_jobs and total_jobs are reset between batches."""
    thread = MyThread()
    thread.start()

    callback_calls = []

    def callback(response: Response | None = None) -> None:
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
    assert thread.total_jobs == 1, (
        f"total_jobs should be 1 for new batch, got {thread.total_jobs}"
    )
    assert thread.num_completed_jobs == 0, (
        f"num_completed_jobs should be 0 for new batch, got {thread.num_completed_jobs}"
    )

    mlp = safe_mainloop(2000)
    mlp.run()

    thread.send("quit", finished_callback=lambda _response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_job_counters_persist_within_batch() -> None:
    """Test that counters accumulate within a multi-job batch."""
    thread = MyThread()
    thread.start()

    callback_calls = []
    n_callbacks = 0

    def callback(response: Response | None = None) -> None:
        nonlocal n_callbacks
        callback_calls.append(response)
        if response is not None and response.type == ResponseType.FINISHED:
            n_callbacks += 1
            if n_callbacks == 3:
                mlp.quit()

    thread.send("div", 1, 2, finished_callback=callback)
    thread.send("div", 3, 4, finished_callback=callback)
    thread.send("div", 5, 6, finished_callback=callback)

    # total_jobs should be 3 (all three sent before any finished)
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 0

    # Process all responses
    mlp = safe_mainloop(4000)
    mlp.run()

    # After all jobs complete, counters should reflect all 3 jobs
    assert thread.total_jobs == 3
    assert thread.num_completed_jobs == 3

    thread.send("quit", finished_callback=lambda _response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_register_callback_errors() -> None:
    """Test errors raised by register_callback."""
    thread = BaseThread()
    with pytest.raises(ValueError, match="when can only be"):
        thread.register_callback("name", "with", "finished")
    with pytest.raises(ValueError, match="reference_cb can only be"):
        thread.register_callback("name", "before", "nonexistent")


def test_pipe_notification() -> None:
    """Test that _notify wakes up the IO watcher and processes responses."""
    thread = BaseThread()
    thread.start()

    responses_received = []

    def on_finished(response: Response) -> None:
        responses_received.append(response)
        mlp.quit()

    thread.send("quit", finished_callback=on_finished)

    mlp = safe_mainloop(2000)
    mlp.run()
    assert len(responses_received) == 1
    assert responses_received[0].type == ResponseType.FINISHED


def test_running_callback_on_empty_queue() -> None:
    """Test that monitor triggers running callbacks even when response queue is empty."""
    thread = BaseThread()
    running_called = []

    def running_cb(_response: Response) -> None:
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


def test_none_callback() -> None:
    """Test that None callbacks don't cause errors."""
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
        after_finished_callback=lambda _response: mlp.quit(),
    )

    mlp = safe_mainloop(2000)
    mlp.run()

    # Should not have any errors
    error_callback.assert_not_called()

    thread.send("quit", finished_callback=lambda _response: mlp.quit())
    mlp = safe_mainloop(2000)
    mlp.run()


def test_monitor_processes_one_at_a_time() -> None:
    """Test that monitor processes exactly one response per call."""
    thread = BaseThread()
    finished_calls = []

    def finished_cb(response: Response) -> None:
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
    with patch("scantpaper.basethread.GLib.idle_add"):
        thread.monitor()

    # Exactly one response should have been consumed
    assert len(finished_calls) == 1
    assert finished_calls[0].info == "result1"
    assert thread.responses.qsize() == 1


def test_monitor_schedules_idle_when_responses_remain() -> None:
    """Test that GLib.idle_add is called when responses still in queue."""
    thread = BaseThread()

    req = Request("test", (), thread.responses)
    thread.callbacks[req.uuid] = {"started": True, "finished_callback": lambda _r: None}
    req.finished(info="result")

    with patch("scantpaper.basethread.GLib.idle_add") as mock_idle:
        thread.monitor()
        mock_idle.assert_called_once_with(thread._drain_one)


@pytest.mark.parametrize(
    "terminal_type",
    [ResponseType.FINISHED, ResponseType.ERROR, ResponseType.CANCELLED],
)
def test_running_callback_suppressed_during_terminal_dispatch(
    mocker: pytest.MockerFixture, terminal_type: ResponseType
) -> None:
    """Test that running callbacks don't fire while a terminal callback is dispatched."""
    thread = BaseThread()
    running_cb = mocker.Mock()
    terminal_dispatched = []

    def terminal_cb(_response: Response) -> None:
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


def test_cancelled_response_dispatches_cancelled_callback(
    mocker: pytest.MockerFixture,
) -> None:
    """CANCELLED fires cancelled_callback, suppresses finished, and cleans the registry."""
    thread = BaseThread()
    cancelled_cb = mocker.Mock()
    finished_cb = mocker.Mock()

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "cancelled_callback": cancelled_cb,
        "finished_callback": finished_cb,
    }
    request.cancelled(info="aborted")

    thread._monitor_response()

    cancelled_cb.assert_called_once()
    assert cancelled_cb.call_args.args[0].type == ResponseType.CANCELLED
    finished_cb.assert_not_called()
    assert request.uuid not in thread.callbacks, "cancelled job removed from registry"
    assert thread.num_completed_jobs == 1, "cancelled job counted as complete"


def test_drain_cancelled_requests_notifies_queued_jobs(
    mocker: pytest.MockerFixture,
) -> None:
    """drain_cancelled_requests drops queued requests and notifies their requesters."""
    thread = BaseThread()
    cancelled_cb = mocker.Mock()
    finished_cb = mocker.Mock()

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": False,
        "cancelled_callback": cancelled_cb,
        "finished_callback": finished_cb,
    }
    thread.requests.put(request)

    thread.drain_cancelled_requests()

    assert thread.requests.empty(), "queued requests drained"
    assert thread.responses.qsize() == 1, "cancelled response emitted per request"

    thread._monitor_response()

    cancelled_cb.assert_called_once()
    assert cancelled_cb.call_args.args[0].type == ResponseType.CANCELLED
    finished_cb.assert_not_called()
    assert request.uuid not in thread.callbacks, "registry entry removed"


def test_stage_callback_exception_invokes_error_callback() -> None:
    """Test that a failing non-error stage callback triggers the error_callback."""
    thread = BaseThread()
    error_callback = MagicMock()

    def failing_callback(_response: Response) -> None:
        msg = "boom"
        raise ValueError(msg)

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

    thread._execute_single_callback(
        "finished_callback", "finished", cast("uuid.UUID", cast("object", uid)), data
    )

    error_callback.assert_called_once()
    assert error_callback.call_args[0][0].status == "boom"


@pytest.mark.filterwarnings("ignore:Source ID .* was not found.*")
def test_release_sources_close_oserror(mocker: pytest.MockerFixture) -> None:
    """Test _release_sources catches OSError from os.close."""
    thread = BaseThread()
    thread._io_watch_id = 999999
    thread._tick_id = 999998
    thread._notify_r = 999
    thread._notify_w = 1000

    mock_close = mocker.patch("scantpaper.basethread.os.close", side_effect=OSError)
    thread._release_sources()
    mlp = safe_mainloop(500)
    GLib.timeout_add(100, mlp.quit)
    mlp.run()
    assert mock_close.call_count >= 2


def test_quit_all_live_threads() -> None:
    """Test quit_all_live_threads stops all registered live threads."""
    t1 = BaseThread()
    t2 = BaseThread()
    t1.start()
    t2.start()
    assert t1 in BaseThread.LiveThreads
    assert t2 in BaseThread.LiveThreads

    BaseThread.quit_all_live_threads()

    t1.join(timeout=2)
    t2.join(timeout=2)
    assert not t1.is_alive(), "t1 quit"
    assert not t2.is_alive(), "t2 quit"


def test_quit_all_live_threads_stops_dropped_thread() -> None:
    """Test a dropped, un-quit worker is still stopped by quit_all_live_threads.

    The run() frame keeps the worker alive (and therefore visible to the
    LiveThreads WeakSet) even after the owner drops all references.
    """
    thread = BaseThread()
    thread_ref = weakref.ref(thread)
    thread.start()
    del thread
    gc.collect()
    assert thread_ref() is not None, "worker kept alive by its run() frame"

    BaseThread.quit_all_live_threads()

    for _ in range(100):
        mlp = safe_mainloop(100)
        GLib.timeout_add(50, mlp.quit)
        mlp.run()
        gc.collect()
        if thread_ref() is None:
            break
    assert thread_ref() is None, "dropped worker ended by LiveThreads teardown"


def test_run_releases_sources_when_input_handler_raises(
    mocker: pytest.MockerFixture,
) -> None:
    """Test run() releases sources even when the loop exits abnormally."""
    recorded_exceptions: list[BaseException] = []

    class ExplodingThread(BaseThread):
        @override
        def input_handler(self, request: Request) -> object:
            del request
            msg = "boom"
            raise RuntimeError(msg)

    thread = ExplodingThread()
    original_hook = threading.excepthook

    def record_excepthook(args: threading.ExceptHookArgs) -> None:
        recorded_exceptions.append(cast("BaseException", args.exc_value))

    threading.excepthook = record_excepthook
    try:
        thread.start()
        thread.requests.put(Request("div", (1, 2), None))
        thread.join(timeout=2)
    finally:
        threading.excepthook = original_hook

    assert len(recorded_exceptions) == 1, "worker exception reached excepthook"
    assert not thread.is_alive(), "worker exited after abnormal loop termination"

    mock_source_remove = mocker.patch("scantpaper.basethread.GLib.source_remove")
    mock_os_close = mocker.patch("scantpaper.basethread.os.close")
    mlp = safe_mainloop(500)
    GLib.timeout_add(100, mlp.quit)
    mlp.run()

    mock_source_remove.assert_any_call(thread._io_watch_id)
    mock_source_remove.assert_any_call(thread._tick_id)
    assert mock_os_close.call_count >= 2, "notification pipe closed after cleanup"


def test_quit_all_live_threads_logs_exception(
    mocker: pytest.MockerFixture,
) -> None:
    """Test quit_all_live_threads logs and continues when quit() raises."""
    t1 = BaseThread()
    t2 = BaseThread()
    t1.start()
    t2.start()

    real_quit = t1.quit

    def raising_quit() -> None:
        real_quit()
        msg = "boom"
        raise RuntimeError(msg)

    mocker.patch.object(t1, "quit", side_effect=raising_quit)
    mock_logger = mocker.patch("scantpaper.basethread.logger")

    BaseThread.quit_all_live_threads()

    mock_logger.exception.assert_called_once()

    t1.join(timeout=2)
    t2.join(timeout=2)
    assert not t1.is_alive(), "t1 quit"
    assert not t2.is_alive(), "t2 quit"


def _failing_callback() -> Callable[[Response | None], None]:
    """Return a progress callback that fails once, then returns quietly.

    A callback that keeps raising would leave the thread's progress tick
    logging a traceback for the rest of the session, long after the test has
    finished asserting. The repeat case is covered directly instead.
    """
    failed: list[bool] = []

    def callback(_response: Response | None) -> None:
        if not failed:
            failed.append(True)
            msg = "boom"
            raise ValueError(msg)

    return callback


# --- thread-response-dispatch regression tests -------------------------
# These cover the failure modes that let a misbehaving progress callback
# strand work in an indefinite "busy" state. Each docstring records why the
# test failed before thread-callback-dispatch-safety.


def test_running_callback_send_does_not_break_dispatch_pass() -> None:
    """A running callback that calls send() must not break the pass.

    Fails before the change with `RuntimeError: dictionary changed size
    during iteration`: the callback calls `BaseThread.send()`, which
    inserts into the registry that the pass is iterating.
    """
    thread = BaseThread()
    dispatched: list[uuid.UUID] = []
    sent: list[uuid.UUID] = []

    def running_cb(_response: Response | None) -> None:
        # Send once: a callback that keeps re-sending would be re-run by the
        # thread's progress tick for the rest of the session, growing the
        # registry without bound and starving every other main loop.
        if not sent:
            sent.append(thread.send("test", "follow-up"))
        dispatched.append(first.uuid)

    first = Request("test", (), thread.responses)
    thread.callbacks[first.uuid] = {"started": True, "running_callback": running_cb}

    assert thread.monitor() == GLib.SOURCE_CONTINUE
    assert dispatched == [first.uuid]
    assert len(sent) == 1
    assert len(thread.callbacks) == 2, "follow-up request registered"
    assert thread.requests.qsize() == 1, "follow-up request queued"


def test_running_callback_retiring_another_request_completes_pass() -> None:
    """A running callback that retires another request must not break the pass.

    Fails before the change with `RuntimeError: dictionary changed size
    during iteration`: a modal dialog opened from a progress callback runs
    a nested main loop, which can deliver another request's terminal
    response and delete its registry entry mid-pass.
    """
    thread = BaseThread()
    dispatched: list[uuid.UUID] = []

    def first_cb(_response: Response | None) -> None:
        dispatched.append(first.uuid)
        # Stands in for a nested main loop delivering a queued terminal
        # response, which retires `second` while the pass is still running.
        thread._monitor_response()

    def third_cb(_response: Response | None) -> None:
        dispatched.append(third.uuid)

    retired_cb = MagicMock()

    first = Request("test", (), thread.responses)
    thread.callbacks[first.uuid] = {"started": True, "running_callback": first_cb}
    second = Request("test", (), thread.responses)
    thread.callbacks[second.uuid] = {
        "started": True,
        "running_callback": retired_cb,
        "finished_callback": MagicMock(),
    }
    third = Request("test", (), thread.responses)
    thread.callbacks[third.uuid] = {"started": True, "running_callback": third_cb}
    second.finished(info="done")

    assert thread.monitor() == GLib.SOURCE_CONTINUE
    assert dispatched == [first.uuid, third.uuid], "retired request not dispatched"
    retired_cb.assert_not_called()
    assert second.uuid not in thread.callbacks, "retired mid-pass"
    assert third.uuid in thread.callbacks, "untouched request still active"


def test_running_callback_registering_request_gets_no_progress() -> None:
    """A request registered mid-pass gets no progress until it has started."""
    thread = BaseThread()
    dispatched: list[uuid.UUID] = []
    follow_up: list[uuid.UUID] = []

    def first_cb(_response: Response | None) -> None:
        # Send once; see test_running_callback_send_does_not_break_dispatch_pass.
        if not follow_up:
            follow_up.append(thread.send("test", "follow-up"))
        dispatched.append(first.uuid)

    def second_cb(_response: Response | None) -> None:
        dispatched.append(second.uuid)

    first = Request("test", (), thread.responses)
    thread.callbacks[first.uuid] = {"started": True, "running_callback": first_cb}
    second = Request("test", (), thread.responses)
    thread.callbacks[second.uuid] = {"started": True, "running_callback": second_cb}

    assert thread.monitor() == GLib.SOURCE_CONTINUE
    assert dispatched == [first.uuid, second.uuid], "follow-up not progressed"
    assert len(follow_up) == 1
    assert not thread.callbacks[follow_up[0]]["started"], "follow-up unstarted"


def test_running_callback_failure_routes_to_error_callback() -> None:
    """A raising running callback must be routed to the error_callback.

    Fails before the change with `AttributeError: 'NoneType' object has no
    attribute 'request'`: the running stage passes no response, but the
    failure path read `data.request` to name the process.
    """
    thread = BaseThread()
    error_callback = MagicMock()

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "request": request,
        "running_callback": _failing_callback(),
        "error_callback": error_callback,
    }

    thread._execute_callbacks_for_stage("running", None)

    error_callback.assert_called_once()
    routed = cast("Response", error_callback.call_args.args[0])
    assert routed.status == "boom"
    assert routed.type == ResponseType.ERROR
    assert routed.request is request, "the failing request reaches the handler"
    assert routed.num_completed_jobs == 0
    assert routed.total_jobs == 0


def test_running_callback_failure_without_recorded_request_is_logged() -> None:
    """An entry recording no request is logged, not routed, and does not raise."""
    thread = BaseThread()
    error_callback = MagicMock()

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "running_callback": _failing_callback(),
        "error_callback": error_callback,
    }

    with patch("scantpaper.basethread.logger") as mock_logger:
        thread._execute_callbacks_for_stage("running", None)

    error_callback.assert_not_called()
    logged = "\n".join(str(call.args) for call in mock_logger.exception.call_args_list)
    assert "unknown" in logged


def test_running_callback_failure_log_names_the_failing_process() -> None:
    """The failure log names the process recorded for the failing request."""
    thread = BaseThread()

    request = Request("div", (1, 2), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "request": request,
        "running_callback": _failing_callback(),
        "error_callback": MagicMock(),
    }

    with patch("scantpaper.basethread.logger") as mock_logger:
        thread._execute_callbacks_for_stage("running", None)

    logged = "\n".join(str(call.args) for call in mock_logger.exception.call_args_list)
    assert "div" in logged, "process named from the recorded request"
    assert "None" not in logged, "no placeholder process name"


def test_responses_around_raising_callback_are_still_delivered(
    mocker: pytest.MockerFixture,
) -> None:
    """Responses queued before and after a raising callback are delivered.

    Fails before the change because the raising `running` callback escaped
    `_execute_single_callback` entirely, so the drain chain broke and the
    response queued after it was never dispatched.
    """
    thread = BaseThread()
    finished = MagicMock()
    error_callback = MagicMock()

    failing = Request("test", (), thread.responses)
    thread.callbacks[failing.uuid] = {
        "started": True,
        "request": failing,
        "running_callback": _failing_callback(),
        "error_callback": error_callback,
    }
    before = Request("test", (), thread.responses)
    thread.callbacks[before.uuid] = {
        "started": True,
        "request": before,
        "finished_callback": finished,
    }
    after = Request("test", (), thread.responses)
    thread.callbacks[after.uuid] = {
        "started": True,
        "request": after,
        "finished_callback": finished,
    }
    before.finished(info="before")
    after.finished(info="after")

    mocker.patch("scantpaper.basethread.GLib.idle_add")

    assert thread.monitor() == GLib.SOURCE_CONTINUE
    assert thread._drain_one() == GLib.SOURCE_CONTINUE
    assert thread._drain_one() == GLib.SOURCE_REMOVE, "chain ends when drained"

    error_callback.assert_called_once()
    routed = cast("Response", error_callback.call_args.args[0])
    assert routed.status == "boom"
    assert routed.request is failing
    delivered = [
        cast("Response", call.args[0]).info for call in finished.call_args_list
    ]
    assert delivered == ["before", "after"]


def test_later_request_response_delivered_after_callback_failure() -> None:
    """A request sent after a failing one still receives its response."""
    thread = BaseThread()
    finished = MagicMock()
    error_callback = MagicMock()

    failing = Request("test", (), thread.responses)
    thread.callbacks[failing.uuid] = {
        "started": True,
        "request": failing,
        "running_callback": _failing_callback(),
        "error_callback": error_callback,
    }

    assert thread.monitor() == GLib.SOURCE_CONTINUE
    error_callback.assert_called_once()

    later = Request("test", (), thread.responses)
    thread.callbacks[later.uuid] = {"started": True, "finished_callback": finished}
    later.finished(info="done")

    # SOURCE_REMOVE: a terminal response retires the request it belongs to.
    assert thread._monitor_response() == GLib.SOURCE_REMOVE
    finished.assert_called_once()
    assert finished.call_args.args[0].info == "done"


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        pytest.param("_on_readable", (0, 0), id="on-readable"),
        pytest.param("_tick", (), id="tick"),
    ],
)
def test_pump_source_survives_raising_callback(
    method_name: str, args: tuple[int, ...], mocker: pytest.MockerFixture
) -> None:
    """No pump source may be destroyed by a raising callback.

    Fails before the change: `_on_readable` and `_tick` let the exception
    escape, so PyGObject removed the source. With the pipe watch gone,
    queued responses were never drained again and the cancellation response
    was never dispatched.
    """
    thread = BaseThread()
    mocker.patch.object(
        thread, "_execute_callbacks_for_stage", side_effect=ValueError("boom")
    )
    mocker.patch.object(thread, "_monitor_response", side_effect=ValueError("boom"))

    method = cast("Callable[..., bool]", getattr(thread, method_name))
    assert method(*args) == GLib.SOURCE_CONTINUE


def test_drain_chain_survives_raising_callback(
    mocker: pytest.MockerFixture,
) -> None:
    """The drain chain must stay alive while responses remain.

    Fails before the change: the exception escaped and PyGObject removed the
    idle source, so the responses still queued behind it were never drained.
    """
    thread = BaseThread()
    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {"started": True}
    request.finished(info="still queued")

    mocker.patch.object(
        thread, "_execute_callbacks_for_stage", side_effect=ValueError("boom")
    )

    assert thread._drain_one() == GLib.SOURCE_CONTINUE
    assert not thread.responses.empty(), "response left for the next pass"


def test_drain_chain_ends_when_drained_after_failure(
    mocker: pytest.MockerFixture,
) -> None:
    """The drain chain still ends once there is nothing left to drain."""
    thread = BaseThread()
    mocker.patch.object(
        thread, "_execute_callbacks_for_stage", side_effect=ValueError("boom")
    )

    assert thread._drain_one() == GLib.SOURCE_REMOVE


def test_on_readable_failure_keeps_draining_responses() -> None:
    """A raising callback must not stop responses being drained.

    Fails before the change with the safety-timeout error: the exception
    removed the io watch, so the queued response was never delivered.
    """
    thread = BaseThread()
    finished = MagicMock()

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "request": request,
        "running_callback": _failing_callback(),
        "error_callback": MagicMock(),
    }
    later = Request("test", (), thread.responses)
    thread.callbacks[later.uuid] = {
        "started": True,
        "request": later,
        "finished_callback": finished,
    }
    later.finished(info="done")

    assert thread._on_readable(0, 0) == GLib.SOURCE_CONTINUE
    assert thread.responses.qsize() == 0, "response was drained"
    finished.assert_called_once()
    assert finished.call_args.args[0].info == "done"


def test_repeatedly_failing_callback_is_reported_each_pass() -> None:
    """A callback that keeps failing is reported on every pass.

    Dispatched directly rather than through a ticking source: a real
    request that failed this way would keep logging until it reached a
    terminal state, which is a defect to surface rather than a state to
    leave behind a test.
    """
    thread = BaseThread()
    error_callback = MagicMock()

    def always_failing_cb(_response: Response | None) -> None:
        msg = "boom"
        raise ValueError(msg)

    request = Request("test", (), thread.responses)
    thread.callbacks[request.uuid] = {
        "started": True,
        "request": request,
        "running_callback": always_failing_cb,
        "error_callback": error_callback,
    }

    thread._execute_callbacks_for_stage("running", None)
    thread._execute_callbacks_for_stage("running", None)

    assert error_callback.call_count == 2
    for call in error_callback.call_args_list:
        assert cast("Response", call.args[0]).status == "boom"
    assert request.uuid in thread.callbacks, "still active, still reported"

    # Stop the callback before returning, or the thread's progress tick keeps
    # reporting this failure for the rest of the session.
    thread.callbacks[request.uuid]["started"] = False

"""Tests for loop_helpers module."""

import pytest

from scantpaper.loop_helpers import _MainLoopWrapper


class _FakeLoop:
    """Duck-typed loop stub for unit-testing the wrapper."""

    def __init__(self) -> None:
        self.run_count = 0
        self.quit_count = 0

    def is_running(self):
        return False

    def run(self):
        self.run_count += 1

    def quit(self):
        self.quit_count += 1


def test_mainloop_wrapper_timeout_raises():
    """The wrapper raises TimeoutError when the safety timer fires."""
    loop = _FakeLoop()
    wrapper = _MainLoopWrapper(loop)
    wrapper.on_timeout()
    with pytest.raises(TimeoutError, match="Safety timeout fired"):
        wrapper.run()


def test_mainloop_wrapper_quit_before_run():
    """A quit before run() short-circuits run() without starting the loop."""
    loop = _FakeLoop()
    wrapper = _MainLoopWrapper(loop)
    wrapper.quit()
    wrapper.run()
    assert loop.run_count == 0
    assert loop.quit_count == 1

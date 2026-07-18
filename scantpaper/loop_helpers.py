"Safe GLib.MainLoop wrapper that fails if the safety timeout fires"

from gi.repository import GLib

SAFETY_TIMEOUT = 2000  # ms – safety-net for GLib.MainLoop


class _MainLoopWrapper:
    "Wraps GLib.MainLoop to fail if the safety timeout fires"

    def __init__(self, loop):
        self._loop = loop
        self._timed_out = False
        self._quit_before_run = False

    def _on_timeout(self):
        self._timed_out = True
        self._loop.quit()

    def run(self):
        if self._quit_before_run:
            return
        self._loop.run()
        assert not self._timed_out, (
            "Safety timeout fired – the operation under test did not complete "
            "within the allowed time. If this test is expected to be slow, "
            "increase SAFETY_TIMEOUT in loop_helpers.py."
        )

    def quit(self, *_args):
        if not self._loop.is_running():
            self._quit_before_run = True
        self._loop.quit()

    def __getattr__(self, name):
        return getattr(self._loop, name)


def safe_mainloop(timeout=SAFETY_TIMEOUT):
    "Return a MainLoop wrapper that fails if the safety timeout fires"
    loop = GLib.MainLoop()
    wrapper = _MainLoopWrapper(loop)
    GLib.timeout_add(timeout, wrapper._on_timeout)
    return wrapper

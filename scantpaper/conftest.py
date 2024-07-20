"Some helper functions to reduce boilerplate"

from types import SimpleNamespace
import pytest
from dialog.sane import SaneScanDialog
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position


def pytest_configure(config):
    "globals"
    config.timeout = 10000


@pytest.fixture
def sane_scan_dialog():
    "return a SaneScanDialog instance"
    return SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )


@pytest.fixture
def import_in_mainloop():
    "import paths in a blocking mainloop"

    def anonymous(slist, paths):
        mlp = GLib.MainLoop()
        slist.import_files(
            paths=paths,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def mainloop_with_timeout(request):
    "start a mainloop with a timeout"

    def anonymous():
        loop = GLib.MainLoop()
        GLib.timeout_add(request.config.timeout, loop.quit)  # to prevent it hanging
        return loop

    return anonymous


@pytest.fixture
def set_device_wait_reload(mainloop_with_timeout):
    "set the device and wait for the options to load"

    def anonymous(dialog, device):
        loop = mainloop_with_timeout()
        signal = None

        def reloaded_scan_options_cb(_arg):
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
        dialog.device_list = [
            SimpleNamespace(name=device, vendor="", model="", label=""),
        ]
        dialog.device = device
        loop.run()

    return anonymous


@pytest.fixture
def set_option_in_mainloop(mainloop_with_timeout):
    "set the given option, and wait for it to finish"

    def anonymous(dialog, name, value):
        loop = mainloop_with_timeout()
        callback_ran = False

        def callback(_arg1, _arg2, _arg3, _arg4):
            nonlocal loop
            nonlocal signal
            nonlocal callback_ran
            callback_ran = True
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("changed-scan-option", callback)
        options = dialog.available_scan_options
        dialog.set_option(options.by_name(name), value)
        loop.run()
        return callback_ran

    return anonymous


@pytest.fixture
def set_paper_in_mainloop(mainloop_with_timeout):
    "set the given paper, and wait for it to finish"

    def anonymous(dialog, paper):
        loop = mainloop_with_timeout()
        callback_ran = False

        def changed_paper(_widget, _paper):
            nonlocal loop
            nonlocal signal
            nonlocal callback_ran
            callback_ran = True
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("changed-paper", changed_paper)
        dialog.paper = paper
        loop.run()
        return callback_ran

    return anonymous

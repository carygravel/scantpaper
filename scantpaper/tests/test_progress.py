"Test Progress widget"

from unittest.mock import Mock
from progress import Progress
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_progress_init():
    "Test initialization"
    progress = Progress()
    assert isinstance(progress, Gtk.Box)
    children = progress.get_children()
    assert len(children) == 2
    assert any(isinstance(c, Gtk.ProgressBar) for c in children)
    assert any(isinstance(c, Gtk.Button) for c in children)


def test_progress_methods():
    "Test simple methods"
    progress = Progress()

    # Identify children
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    progress.set_fraction(0.5)
    assert pbar.get_fraction() == 0.5

    progress.set_text("Test")
    assert pbar.get_text() == "Test"

    progress.pulse()


def test_progress_signal():
    "Test cancel button signal"
    progress = Progress()

    signal_received = False

    def on_clicked(_widget):
        nonlocal signal_received
        signal_received = True

    progress.connect("clicked", on_clicked)

    # Find button and click it
    btn = [c for c in progress.get_children() if isinstance(c, Gtk.Button)][0]
    btn.clicked()

    assert signal_received


def test_progress_queued():
    "Test queued method"
    progress = Progress()

    response = Mock()
    response.request.process = "test_process"
    response.num_completed_jobs = 1
    response.total_jobs = 10

    progress.queued(response)

    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    # "Process 2 of 10 (test_process)"
    assert "test_process" in pbar.get_text()
    assert abs(pbar.get_fraction() - (1 + 0.5) / 10) < 0.001
    assert progress.get_visible()

    # Test that cancel logic connected in queued works (hides the progress)
    # Note: queued connects a signal handler that calls self.hide()
    # The button click will trigger self.emit("clicked"), which triggers the handler.
    btn = [c for c in progress.get_children() if isinstance(c, Gtk.Button)][0]
    btn.clicked()
    assert not progress.get_visible()


def test_progress_update():
    "Test update method"
    progress = Progress()

    response = Mock()
    response.request.process = "test_process"
    response.num_completed_jobs = 2
    response.total_jobs = 10

    progress.update(response)

    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    assert "test_process" in pbar.get_text()
    assert abs(pbar.get_fraction() - (2 + 0.5) / 10) < 0.001

    # Test update without process name
    response.request.process = None
    progress.update(response)
    # "Process 3 of 10"
    assert "Process" in pbar.get_text()


def test_progress_finish():
    "Test finish method"
    progress = Progress()
    progress.show()

    response = Mock()
    response.pending = False

    # Setup _signal by calling queued first, because finish tries to disconnect it
    response_q = Mock()
    response_q.request.process = "test"
    response_q.num_completed_jobs = 0
    response_q.total_jobs = 10
    progress.queued(response_q)

    assert progress._signal is not None  # pylint: disable=protected-access

    progress.finish(response)
    assert not progress.get_visible()
    # Cannot easily check if disconnected, but can check if signal handler runs?
    # Actually, GObject doesn't expose `connected` status easily.
    # But if we click, it shouldn't hide (if it was visible), but finish hides it.

    # Check if finish handles None response
    progress.show()
    progress.finish(None)
    assert not progress.get_visible()

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


def test_set_fraction_clamps_values():
    "Test that set_fraction clamps values to [0.0, 1.0]"
    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    progress.set_fraction(1.5)
    assert pbar.get_fraction() == 1.0

    progress.set_fraction(-0.5)
    assert pbar.get_fraction() == 0.0

    progress.set_fraction(0.75)
    assert pbar.get_fraction() == 0.75

    progress.set_fraction(1.0)
    assert pbar.get_fraction() == 1.0

    progress.set_fraction(0.0)
    assert pbar.get_fraction() == 0.0


def test_progress_queued_clamps_fraction():
    "Test that queued clamps fraction when num_completed >= total"
    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    response = Mock()
    response.request.process = "test"
    response.num_completed_jobs = 10
    response.total_jobs = 10

    progress.queued(response)
    assert pbar.get_fraction() <= 1.0


def test_progress_update_clamps_fraction():
    "Test that update clamps fraction when num_completed_jobs >= total_jobs"
    progress = Progress()
    response = Mock()
    response.type = None  # not DATA
    response.request.process = "test"
    response.num_completed_jobs = 10
    response.total_jobs = 10

    progress.update(response)

    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    assert pbar.get_fraction() <= 1.0


def test_progress_update_data_string():
    "Test that update sets text when response.info is a string"
    from basethread import ResponseType

    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    response = Mock()
    response.type = ResponseType.DATA
    response.info = "Processing file..."

    progress.update(response)
    assert pbar.get_text() == "Processing file..."
    assert progress.get_visible()


def test_progress_update_data_float_clamps():
    "Test that update clamps float DATA values > 1.0"
    from basethread import ResponseType

    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    response = Mock()
    response.type = ResponseType.DATA
    response.info = 1.5

    progress.update(response)
    assert pbar.get_fraction() == 1.0


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

    # Check if finish handles None response
    progress.show()
    progress.finish(None)
    assert not progress.get_visible()

    assert progress._signal is None  # pylint: disable=protected-access


def test_progress_finish_with_pending():
    "Test finish with pending=True does not hide but disconnects signal"
    progress = Progress()
    progress.show()

    # Setup _signal via queued
    response_q = Mock()
    response_q.request.process = "test"
    response_q.num_completed_jobs = 0
    response_q.total_jobs = 10
    progress.queued(response_q)

    assert progress._signal is not None  # pylint: disable=protected-access
    assert progress.get_visible()

    response = Mock()
    response.pending = True
    progress.finish(response)

    # Should still be visible (pending is True, so not hidden)
    assert progress.get_visible()
    # Signal should still be disconnected
    assert progress._signal is None  # pylint: disable=protected-access


def test_progress_queued_no_total():
    "Test queued does nothing when total is 0"
    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    response = Mock()
    response.request.process = "test"
    response.num_completed_jobs = 0
    response.total_jobs = 0

    progress.queued(response)

    assert pbar.get_text() is None
    assert not progress.get_visible()
    assert progress._signal is None  # pylint: disable=protected-access


def test_progress_queued_no_process_name():
    "Test queued does nothing when process_name is None"
    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    response = Mock()
    response.request.process = None
    response.num_completed_jobs = 0
    response.total_jobs = 10

    progress.queued(response)

    assert pbar.get_text() is None
    assert not progress.get_visible()
    assert progress._signal is None  # pylint: disable=protected-access


def test_progress_update_data_other_type():
    "Test update with DATA type and non-str/non-float info returns early"
    from basethread import ResponseType

    progress = Progress()
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]

    # Set some initial text/fraction to verify they don't change
    progress.set_text("initial")
    progress.set_fraction(0.5)
    assert pbar.get_text() == "initial"
    assert abs(pbar.get_fraction() - 0.5) < 0.001

    response = Mock()
    response.type = ResponseType.DATA
    response.info = 123  # int, neither str nor float

    progress.update(response)
    # Text and fraction should remain unchanged (early return)
    assert pbar.get_text() == "initial"
    assert abs(pbar.get_fraction() - 0.5) < 0.001


def test_progress_child_widgets_visible_after_show_all():
    "Test that child widgets are visible after calling show_all()"
    progress = Progress()

    # Initially, nothing should be visible
    assert not progress.get_visible()

    # After show_all(), the progress and its children should be visible
    progress.show_all()
    assert progress.get_visible()

    # Get child widgets
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    btn = [c for c in progress.get_children() if isinstance(c, Gtk.Button)][0]

    # Children should be visible
    assert pbar.get_visible()
    assert btn.get_visible()

    # Now hide and show_all again (simulating the app_window.py pattern)
    progress.hide()
    assert not progress.get_visible()

    progress.show_all()
    assert progress.get_visible()
    assert pbar.get_visible()
    assert btn.get_visible()


def test_progress_visibility_after_hide_then_show():
    "Test that show() makes progress visible after hide(), not show_all()"
    progress = Progress()

    # Get child widgets
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    btn = [c for c in progress.get_children() if isinstance(c, Gtk.Button)][0]

    # Prepare: show_all() then hide() (app_window.py pattern)
    progress.show_all()
    progress.hide()

    # Child widgets should still be flagged as "visible" (just their parent is hidden)
    assert pbar.get_visible()
    assert btn.get_visible()
    assert not progress.get_visible()

    # Now call show() - this should make the progress visible
    progress.show()
    assert progress.get_visible()
    assert pbar.get_visible()
    assert btn.get_visible()


def test_progress_child_widgets_shown_after_init():
    "Test that Progress child widgets are shown after init"
    progress = Progress()

    # Get child widgets
    pbar = [c for c in progress.get_children() if isinstance(c, Gtk.ProgressBar)][0]
    btn = [c for c in progress.get_children() if isinstance(c, Gtk.Button)][0]

    # After creation, parent is not visible, but children are
    assert not progress.get_visible()
    assert pbar.get_visible(), "ProgressBar should be visible after init"
    assert btn.get_visible(), "Button should be visible after init"

    # Call show() on parent - this should make the container visible
    # (children are already visible)
    progress.show()
    assert progress.get_visible()
    assert pbar.get_visible()
    assert btn.get_visible()

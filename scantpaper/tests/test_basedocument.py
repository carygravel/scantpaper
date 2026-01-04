"Coverage tests for basedocument.py"

import os
import signal
import tempfile
import threading
import pathlib
import shutil
import queue
from unittest.mock import MagicMock, patch
import pytest
import gi
from document import Document
from basedocument import drag_data_received_callback, ID_URI, ID_PAGE

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture(autouse=True)
def mock_thread(mocker):
    "Automatically mock DocThread for all tests in this module"
    mock_cls = mocker.patch("basedocument.DocThread")
    mock_inst = mock_cls.return_value

    # Mock queues to return None once then raise Empty to break loops in cancel()
    mock_inst.requests = MagicMock()
    mock_inst.requests.get.side_effect = [None, queue.Empty]
    mock_inst.responses = MagicMock()
    mock_inst.responses.get.side_effect = [None, queue.Empty]

    mock_inst.running_pids = {}
    mock_inst.lock = threading.Lock()
    mock_inst._dir = "/tmp"
    mock_inst._con = MagicMock()

    # Mock DocThread.send to avoid blocking on queues
    mock_inst.send = MagicMock()

    return mock_inst


def test_create_pidfile_error():
    "Test create_pidfile error handling"
    slist = Document(dir="/non-existent-directory")

    error_called = False

    def error_callback(page, process, message):
        nonlocal error_called
        error_called = True
        assert "unable to write to" in message

    options = {"error_callback": error_callback, "page": 1}

    pidfile = slist.create_pidfile(options)
    assert pidfile is None
    assert error_called


def test_cancel(mock_thread):
    "Test cancel method"
    mock_thread.running_pids = {"dummy.pid": "dummy.pid"}
    slist = Document()

    # Patch slurp where it's used in basedocument
    # slurp returns content of pidfile as string
    with patch("basedocument.slurp", return_value="12345"), patch(
        "os.killpg"
    ) as mock_killpg, patch("os.getpgid", return_value=12345):

        cancel_callback = MagicMock()
        process_callback = MagicMock()

        slist.cancel(cancel_callback, process_callback)

        assert slist.thread.cancel is True
        process_callback.assert_called_with("12345")
        mock_killpg.assert_called_once_with(12345, signal.SIGKILL)
        assert "dummy.pid" not in slist.thread.running_pids


def test_add_page_extra():
    "Test add_page with replace and insert-after"
    slist = Document()

    # Initial page - using integer ID to avoid GObject Value errors
    slist.add_page(1, None, 101)
    assert len(slist.data) == 1

    # Replace
    slist.add_page(1, None, 102, replace=101)
    assert len(slist.data) == 1
    assert slist.data[0][2] == 102

    # Insert after
    slist.add_page(2, None, 103, **{"insert-after": 102})
    assert len(slist.data) == 2
    assert slist.data[1][2] == 103

    # Test error case for _find_page_by_ref
    with pytest.raises(ValueError):
        slist.add_page(3, None, 104, replace=999)


def test_delete_selection_extra_edge_cases():
    "Test delete_selection_extra edge cases"
    slist = Document()

    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    # Mock delete_selection to actually remove the rows since we've mocked the thread
    def mock_delete_selection(_self=None, context=None):
        indices = slist.get_selected_indices()
        for i in reversed(indices):
            del slist.data[i]

    slist.delete_selection = mock_delete_selection

    slist.select(2)  # select page 3
    slist.delete_selection_extra()
    assert len(slist.data) == 2
    assert slist.get_selected_indices() == [1]  # should select page 2

    slist.select([0, 1])
    slist.delete_selection_extra()
    assert len(slist.data) == 0


def test_save_open_session():
    "Test save_session and open_session"
    slist = Document()
    temp_dir = tempfile.mkdtemp()
    slist.dir = pathlib.Path(temp_dir)
    slist.add_page(1, None, 101)

    # Create a dummy document.db
    db_path = slist.dir / "document.db"
    with open(db_path, "w", encoding="utf-8") as f:
        f.write("dummy db")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_name = tmp.name

    try:
        slist.save_session(tmp_name)
        assert os.path.exists(tmp_name)

        slist2 = Document()
        temp_dir2 = tempfile.mkdtemp()
        slist2.dir = pathlib.Path(temp_dir2)
        error_callback = MagicMock()

        # Mock thread methods used in open_session
        slist2.thread.open = MagicMock()
        slist2.thread.page_number_table.return_value = [[1, None, 101]]

        slist2.open_session(db=tmp_name, error_callback=error_callback)
        assert len(slist2.data) == 1
        assert slist2.data[0][2] == 101
        error_callback.assert_not_called()

        shutil.rmtree(temp_dir2)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        shutil.rmtree(temp_dir)


def test_renumber_ascending():
    "Test renumber ascending logic when start/step are undefined"
    slist = Document()
    # Manually set non-ascending numbers
    slist.get_model().handler_block(slist.row_changed_signal)
    slist.data = [[5, None, 101], [2, None, 102], [3, None, 103]]
    slist.get_model().handler_unblock(slist.row_changed_signal)

    slist.renumber()
    assert slist.data[0][0] == 5
    assert slist.data[1][0] == 6
    assert slist.data[2][0] == 7


def test_generated_methods():
    "Test generated methods like save_pdf and rotate"
    slist = Document()

    # Test save_pdf (generated by _save_method_generator)
    slist.save_pdf(filename="test.pdf")
    slist.thread.save_pdf.assert_called_once()

    # Test rotate (generated by _modify_method_generator)
    slist.rotate(angle=90)
    slist.thread.rotate.assert_called_once()


def test_on_row_deleted():
    "Test _on_row_deleted"
    slist = Document()
    mock_path = MagicMock()
    mock_path.get_indices.return_value = [0]

    slist._on_row_deleted(None, mock_path)
    slist.thread.send.assert_called_with("delete_pages", {"row_ids": [0]})


def test_pages_possible_extra():
    "Test pages_possible edge cases"
    slist = Document()

    # Empty document, negative step
    # start=10, step=-2 -> 10, 8, 6, 4, 2 -> 5 pages
    assert slist.pages_possible(10, -2) == 5

    # start=10, step=-3 -> 10, 7, 4, 1 -> 4 pages
    # 10 / 3 = 3.33 -> 4
    assert slist.pages_possible(10, -3) == 4


def test_drag_data_received_callback(mocker):
    "Test drag_data_received_callback"

    # Mock Gtk.drag_finish
    mocker.patch("basedocument.Gtk.drag_finish")

    tree = MagicMock(spec=Document)
    context = MagicMock()
    selection_data = MagicMock()

    # Test fired twice handling
    tree.drops = {123: 1}
    drag_data_received_callback(tree, context, 0, 0, selection_data, 0, 123)
    assert not tree.drops

    # Test ID_URI
    tree.drops = {}
    selection_data.get_uris.return_value = ["file:///tmp/test.png"]
    drag_data_received_callback(tree, context, 0, 0, selection_data, ID_URI, 456)
    tree.import_files.assert_called_with(paths=["file:///tmp/test.png"])

    # Test ID_PAGE
    tree.get_selected_indices.return_value = [0]
    tree.get_dest_row_at_pos.return_value = (
        Gtk.TreePath.new_from_string("1"),
        Gtk.TreeViewDropPosition.AFTER,
    )
    tree.copy_selection.return_value = "some_data"
    drag_data_received_callback(tree, context, 0, 0, selection_data, ID_PAGE, 789)
    tree.paste_selection.assert_called_with(
        data="some_data", dest="1", how=Gtk.TreeViewDropPosition.AFTER
    )

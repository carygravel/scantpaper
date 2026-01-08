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

    def error_callback(_page, _process, message):
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
    def mock_delete_selection(_self=None, context=None, **kwargs):
        indices = slist.get_selected_indices()
        for i in reversed(indices):
            del slist.data[i]
        if "finished_callback" in kwargs:
            kwargs["finished_callback"]()

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


def test_index_for_page_direction():
    "Test index_for_page with negative direction"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    # Search for page 2 from end to start
    assert slist.index_for_page(2, min_page=0, max_page=2, direction=-1) == 1
    # Search for non-existent page
    assert slist.index_for_page(4, direction=-1) == -1


def test_pages_possible_infinite():
    "Test pages_possible infinite cases"
    slist = Document()

    # Empty document, step > 0
    assert slist.pages_possible(1, 1) == -1  # INFINITE is -1

    # Start page after end of document
    slist.add_page(1, None, 101)
    assert slist.pages_possible(5, 1) == -1


def test_paste_selection_complex(mock_thread):
    "Test paste_selection with specific destination and position"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    data_to_paste = [[1, None, 101]]

    # Mock the clone_pages response
    def mock_send(cmd, _args, data_callback=None, finished_callback=None):
        if cmd == "clone_pages":
            response = MagicMock()
            response.info = {"type": "page", "new_pages": [[3, None, 103]]}
            data_callback(response)

    slist.thread.send = mock_send

    # Paste AFTER index 0 (so at index 1)
    slist.paste_selection(
        data=data_to_paste, dest=0, how=Gtk.TreeViewDropPosition.AFTER
    )

    assert len(slist.data) == 3
    assert slist.data[1][2] == 103


def test_valid_renumber_complex():
    "Test valid_renumber with various scenarios"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    # Invalid start
    assert not slist.valid_renumber(0, 1, "all")
    # Invalid step
    assert not slist.valid_renumber(1, 0, "all")

    # selection="all", negative step resulting in negative page number
    # 3 pages, start 2, step -1 -> 2, 1, 0 (invalid)
    assert not slist.valid_renumber(2, -1, "all")

    # selection="selected", overlap with non-selected
    slist.select(0)  # select page 1 (uuid 101)
    # try to renumber page 1 to 2, but 2 is already taken by non-selected
    assert not slist.valid_renumber(2, 1, "selected")


def test_get_page_index_errors():
    "Test get_page_index error handling"
    slist = Document()
    error_callback = MagicMock()

    # Range "all" on empty document
    assert slist.get_page_index("all", error_callback) == []
    error_callback.assert_called_with(None, "Get page", "No pages to process")

    # Range "selected" with no selection
    slist.add_page(1, None, 101)
    slist.get_selection().unselect_all()
    assert slist.get_page_index("selected", error_callback) == []
    error_callback.assert_called_with(None, "Get page", "No pages selected")


def test_renumber_selected():
    "Test renumbering only selected pages"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    slist.select(1)  # page 2 (index 1)
    slist.renumber(start=10, step=1, selection="selected")
    assert slist.data[0][0] == 10
    assert slist.data[1][0] == 11
    assert slist.data[2][0] == 12


def test_on_row_changed_sorting():
    "Test _on_row_changed triggers renumbering and maintains selection"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    # Edit page 2 to become page 0 (should sort before page 1)
    slist.data[1][0] = 0
    # Manually trigger row-changed
    slist._on_row_changed(None, None, None)

    # After sort and renumber, they should be 1 and 2
    # renumber() sets ascending if no start/step given.
    assert slist.data[0][2] == 102


def test_find_page_by_uuid_none():
    "Test find_page_by_uuid with None"
    slist = Document()
    assert slist.find_page_by_uuid(None) is None


def test_open_session_error_copy(mock_thread):
    "Test open_session when shutil.copy fails"
    slist = Document()
    error_callback = MagicMock()
    with patch("shutil.copy", side_effect=OSError("copy failed")):
        slist.open_session(db="some.db", error_callback=error_callback)
        error_callback.assert_called_once()


def test_modify_method_callback():
    "Test the callback generated by _modify_method_generator"
    slist = Document()
    slist.add_page = MagicMock()

    # Generic response with type='page'
    response = MagicMock()
    response.info = {"type": "page", "row": (1, None, 101)}

    # Trigger a modify method to get the callback
    # We need to capture the data_callback passed to thread.rotate or similar
    # generated methods use getattr(self.thread, _method_name)
    captured_callback = None

    def mock_rotate(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("data_callback")

    slist.thread.rotate = mock_rotate
    slist.rotate(angle=90)

    assert captured_callback is not None
    captured_callback(response)
    slist.add_page.assert_called_with(1, None, 101, type="page", row=(1, None, 101))

    # Test logger_callback branch
    logger_cb = MagicMock()
    slist.rotate(angle=90, logger_callback=logger_cb)
    response.info = {"type": "other"}
    captured_callback(response)
    logger_cb.assert_called_with(response)


def test_open_session_error_no_db():
    "Test open_session with missing db key"
    slist = Document()
    error_callback = MagicMock()
    slist.open_session(error_callback=error_callback)
    error_callback.assert_called_once()


def test_drag_data_received_callback_no_rows(mocker):
    "Test drag_data_received_callback with no selection"
    tree = MagicMock(spec=Document)
    tree.get_selected_indices.return_value = []
    drag_data_received_callback(tree, MagicMock(), 0, 0, MagicMock(), ID_PAGE, 123)
    tree.paste_selection.assert_not_called()


def test_drag_data_received_callback_abort(mocker):
    "Test drag_data_received_callback abort case"
    context = MagicMock()
    drag_data_received_callback(MagicMock(), context, 0, 0, MagicMock(), 999, 123)
    context.abort.assert_called_once()


def test_drag_data_received_callback_uri(mocker):
    "Test drag_data_received_callback with URI list"
    mocker.patch("basedocument.Gtk.drag_finish")
    tree = MagicMock(spec=Document)
    context = MagicMock()
    data = MagicMock()
    data.get_uris.return_value = ["file:///tmp/test.png"]

    drag_data_received_callback(tree, context, 0, 0, data, ID_URI, 123)
    tree.import_files.assert_called_with(paths=["file:///tmp/test.png"])


def test_pages_possible_extra():
    "Test pages_possible edge cases"
    slist = Document()

    # Empty document, negative step
    # start=10, step=-2 -> 10, 8, 6, 4, 2 -> 5 pages
    assert slist.pages_possible(10, -2) == 5

    # start=10, step=-3 -> 10, 7, 4, 1 -> 4 pages
    assert slist.pages_possible(10, -3) == 4


def test_drag_data_received_callback_repeat(mocker):
    "Test drag_data_received_callback ignore repeated drops"
    mocker.patch("basedocument.Gtk.drag_finish")
    tree = MagicMock()
    tree.drops = {123: 1}
    drag_data_received_callback(tree, MagicMock(), 0, 0, MagicMock(), ID_PAGE, 123)
    assert not tree.drops

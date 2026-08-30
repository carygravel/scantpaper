"Coverage tests for basedocument.py"

# pylint: disable=redefined-outer-name, protected-access  # tests access private members and pytest fixtures

import os
import pathlib
import queue
import shutil
import signal
import tempfile
import threading
import uuid
from unittest.mock import MagicMock, Mock, patch

import gi
import pytest
from basedocument import ID_PAGE, ID_URI, drag_data_received_callback
from docthread import INSERT_AT_START
from document import Document
from loop_helpers import safe_mainloop

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position  # noqa: E402
    GLib,
    Gtk,
)


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
    def mock_send(_process, *_args, **kwargs):
        def run_callbacks():
            if "data_callback" in kwargs:
                response = MagicMock()
                response.info = {"type": "page"}
                kwargs["data_callback"](response)
            if "finished_callback" in kwargs:
                kwargs["finished_callback"](None)
            return False

        GLib.idle_add(run_callbacks)
        return uuid.uuid4()

    mock_inst.send.side_effect = mock_send

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


def test_create_pidfile_registers_in_running_pids(tmp_path):
    "Test create_pidfile registers the pidfile in running_pids"
    slist = Document(dir=tmp_path)
    slist.thread.running_pids = {}
    pidfile = slist.create_pidfile({})
    assert pidfile is not None
    assert pidfile in slist.thread.running_pids
    assert slist.thread.running_pids[pidfile] is pidfile


def test_cancel(mock_thread):
    "Test cancel method"
    mock_thread.running_pids = {"dummy.pid": "dummy.pid"}
    slist = Document()

    # Patch slurp where it's used in basedocument
    # slurp returns content of pidfile as string
    with (
        patch("basedocument.slurp", return_value="12345"),
        patch("os.killpg") as mock_killpg,
        patch("os.getpgid", return_value=12345),
    ):

        cancel_callback = MagicMock()
        process_callback = MagicMock()

        slist.cancel(cancel_callback, process_callback)

        assert slist.thread.cancel is True
        process_callback.assert_called_with(12345)
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
    with pytest.raises(ValueError, match="does not exist"):
        slist.add_page(3, None, 104, replace=999)


def test_delete_selection_extra_edge_cases():
    "Test delete_selection_extra edge cases"
    slist = Document()

    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    # Mock delete_selection to actually remove the rows since we've mocked the thread
    def mock_delete_selection(_self=None, context=None, **kwargs):
        del context
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
    db_path = slist.dir.name + ".sdb"
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

        # Override send to simulate async responses synchronously
        def mock_send(process, *_args, **kwargs):
            if process == "open":
                if "finished_callback" in kwargs:
                    kwargs["finished_callback"](MagicMock())
            elif process == "page_number_table" and "finished_callback" in kwargs:
                kwargs["finished_callback"](MagicMock(info=[[1, None, 101]]))
            return MagicMock()

        slist2.thread.send = mock_send

        slist2.open_session(db=tmp_name, error_callback=error_callback)
        assert len(slist2.data) == 1
        assert slist2.data[0][2] == 101
        error_callback.assert_not_called()

        shutil.rmtree(temp_dir2)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        if os.path.exists(db_path):
            os.remove(db_path)
        open_session_db = slist2.dir.name + ".sdb"
        if os.path.exists(open_session_db):
            os.remove(open_session_db)
        shutil.rmtree(temp_dir)


def test_renumber_ascending():
    "Test renumber makes page numbers consecutive 1..n"
    slist = Document()
    # Manually set non-ascending numbers
    slist.get_model().handler_block(slist.row_changed_signal)
    slist.data = [[5, None, 101], [2, None, 102], [3, None, 103]]
    slist.get_model().handler_unblock(slist.row_changed_signal)

    slist.renumber()
    assert slist.data[0][0] == 1
    assert slist.data[1][0] == 2
    assert slist.data[2][0] == 3


def test_generated_methods(mock_thread):
    "Test generated methods like save_pdf and rotate"
    slist = Document()

    # Test save_pdf (generated by _save_method_generator)
    slist.save_pdf(filename="test.pdf")
    mock_thread.save_pdf.assert_called_once()

    # Test rotate (generated by _modify_method_generator)
    slist.rotate(angle=90)
    mock_thread.rotate.assert_called_once()


def test_add_page_insert_before():
    "Test add_page inserts at the start of the document"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103, **{"insert-after": INSERT_AT_START})
    assert [row[2] for row in slist.data] == [103, 101, 102], "inserted at start"
    assert [row[0] for row in slist.data] == [1, 2, 3], "renumbered consecutively"


def test_add_page_renumbers():
    "Test add_page keeps page numbers consecutive"
    slist = Document()

    # Empty document, out-of-order add
    slist.add_page(10, None, 101)
    slist.add_page(10, None, 102)
    assert [row[0] for row in slist.data] == [1, 2], "renumbered consecutively"

    # Insert after a given page renumbers the remainder
    slist.add_page(10, None, 103, **{"insert-after": 101})
    assert [row[2] for row in slist.data] == [101, 103, 102], "inserted after 101"
    assert [row[0] for row in slist.data] == [1, 2, 3], "renumbered consecutively"


def test_add_page_in_order_append_skips_renumber():
    "Test add_page does not renumber when an in-order page is appended"
    slist = Document()
    slist.add_page(1, None, 101)

    with patch("basedocument.BaseDocument.renumber") as mock_renumber:
        slist.add_page(2, None, 102)

    mock_renumber.assert_not_called()
    assert [row[0] for row in slist.data] == [1, 2], "numbers remain consecutive"


def test_add_page_out_of_order_append_renumbers():
    "Test add_page renumbers when an out-of-order page is appended"
    slist = Document()
    slist.add_page(10, None, 101)

    with patch("basedocument.BaseDocument.renumber") as mock_renumber:
        slist.add_page(10, None, 102)

    mock_renumber.assert_called_once()


def test_paste_selection_complex():
    "Test paste_selection with specific destination and position"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    data_to_paste = [[1, None, 101]]

    # Mock the clone_pages response
    def mock_send(cmd, _args, data_callback=None, finished_callback=None):
        del finished_callback
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


def test_open_session_error_copy():
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
    captured = {}

    def mock_rotate(**kwargs):
        captured["data_callback"] = kwargs.get("data_callback")

    slist.thread.rotate = mock_rotate
    slist.rotate(angle=90)

    assert captured["data_callback"] is not None
    captured["data_callback"](response)
    slist.add_page.assert_called_with(1, None, 101, type="page", row=(1, None, 101))

    # Test logger_callback branch
    logger_cb = MagicMock()
    slist.rotate(angle=90, logger_callback=logger_cb)
    response.info = {"type": "other"}
    captured["data_callback"](response)
    logger_cb.assert_called_with(response)


def test_open_session_error_no_db():
    "Test open_session with missing db key"
    slist = Document()
    error_callback = MagicMock()
    slist.open_session(error_callback=error_callback)
    error_callback.assert_called_once()


def test_drag_data_received_callback_no_rows():
    "Test drag_data_received_callback with no selection"
    tree = MagicMock(spec=Document)
    tree.get_selected_indices.return_value = []
    drag_data_received_callback(tree, MagicMock(), 0, 0, MagicMock(), ID_PAGE, 123)
    tree.paste_selection.assert_not_called()


def test_drag_data_received_callback_abort():
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


def test_drag_data_received_callback_path_to_string():
    "Test that path.to_string() is called when a valid path is provided"
    # Mock the tree and context
    tree = MagicMock()
    context = MagicMock()

    # Mock the row returned by get_dest_row_at_pos
    mock_path = MagicMock()
    mock_path.to_string.return_value = "mock_path"
    tree.get_dest_row_at_pos.return_value = (mock_path, Gtk.TreeViewDropPosition.AFTER)

    # Mock the copy_selection method to return an empty list
    tree.copy_selection.return_value = []

    # Mock the data and other parameters
    data = MagicMock()
    data.get_uris.return_value = []
    xpos, ypos, info, time = 0, 0, ID_PAGE, 0

    # Patch Gtk.drag_finish to avoid the TypeError
    with patch("gi.repository.Gtk.drag_finish") as mock_drag_finish:
        # Call the drag_data_received_callback
        drag_data_received_callback(tree, context, xpos, ypos, data, info, time)

        # Assert that path.to_string() was called
        mock_path.to_string.assert_called_once()

        # Assert that tree.paste_selection was called with the correct path
        tree.paste_selection.assert_called_once_with(
            data=[], dest="mock_path", how=Gtk.TreeViewDropPosition.AFTER
        )

        # Assert that Gtk.drag_finish was called
        mock_drag_finish.assert_called_once_with(context, True, False, time)


def test_on_row_changed_moves_page():
    "Test _on_row_changed moves the edited page to its number's position"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    slist.select(0)
    slist.data[0][0] = 3
    assert [row[2] for row in slist.data] == [102, 103, 101], "page moved to position 3"
    assert [row[0] for row in slist.data] == [1, 2, 3], "renumbered consecutively"


def test_drag_data_received_callback_repeat(mocker):
    "Test drag_data_received_callback ignore repeated drops"
    mocker.patch("basedocument.Gtk.drag_finish")
    tree = MagicMock()
    tree.drops = {123: 1}
    drag_data_received_callback(tree, MagicMock(), 0, 0, MagicMock(), ID_PAGE, 123)
    assert not tree.drops


def test_cut_selection():
    "Test cut_selection"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    # Mock delete_selection_extra since it is tested separately and complex
    slist.delete_selection_extra = MagicMock()

    slist.get_selection().unselect_all()
    slist.select(0)
    data = slist.cut_selection()

    assert len(data) == 1
    assert data[0][2] == 101
    slist.delete_selection_extra.assert_called_once()


def test_copy_selection_empty():
    "Test copy_selection with no selection"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.get_selection().unselect_all()

    assert slist.copy_selection() is None


def test_set_paper_sizes(mock_thread):
    "Test set_paper_sizes"
    slist = Document()
    sizes = {"A4": (210, 297)}
    slist.set_paper_sizes(sizes)

    mock_thread.send.assert_called_with("set_paper_sizes", sizes)


def test_paste_selection_default_dest():
    "Test paste_selection with default destination (append)"
    slist = Document()
    slist.add_page(1, None, 101)

    data_to_paste = [[1, None, 101]]

    def mock_send(cmd, _args, data_callback=None, finished_callback=None):
        del finished_callback
        if cmd == "clone_pages":
            response = MagicMock()
            response.info = {"type": "page", "new_pages": [[2, None, 102]]}
            data_callback(response)

    slist.thread.send = mock_send

    finished_callback = MagicMock()
    slist.paste_selection(data=data_to_paste, finished_callback=finished_callback)

    assert len(slist.data) == 2
    assert slist.data[1][2] == 102
    finished_callback.assert_called_once()


def test_delete_selection_with_context():
    "Test delete_selection with duplicate context"
    slist = Document()
    slist.add_page(1, None, 101)

    slist.select(0)
    context = MagicMock()
    # Need to make context hashable
    context.__hash__ = MagicMock(return_value=12345)

    # First call - should proceed
    slist.thread.send = MagicMock()
    slist.delete_selection(context=context)
    slist.thread.send.assert_called_once()

    # Second call with same context - should be ignored
    slist.thread.send.reset_mock()
    slist.delete_selection(context=context)
    slist.thread.send.assert_not_called()

    # Third call with new context (or after reset) - simulating reset mechanism
    # The code deletes slist._context on successful ignore? No, it deletes it if found.
    # Actually logic:
    # if context in self._context: self._context={}; return
    # else: self._context[context]=1
    # So the second call returns early AND clears _context.
    # So a third call with same context should proceed again.

    slist.delete_selection(context=context)
    slist.thread.send.assert_called_once()


def test_selection_changed_blocked(mock_thread):
    "Test _on_selection_changed when signals blocked"
    slist = Document()
    slist._block_signals = True
    slist.add_page(1, None, 101)
    slist.select(0)

    # Signal handler is connected to thread.send("set_selection", ...)
    # But mock_thread is autouse.
    # We need to check if send was called with "set_selection"
    # Wait, add_page triggers selection change internally but we blocked our custom flag
    # Let's verify manually calling the handler
    slist._on_selection_changed(None)
    # Should not have sent anything
    calls = [
        c
        for c in mock_thread.send.call_args_list
        if c.args and c.args[0] == "set_selection"
    ]
    assert not calls

    slist._block_signals = False
    slist._on_selection_changed(None)
    calls = [
        c
        for c in mock_thread.send.call_args_list
        if c.args and c.args[0] == "set_selection"
    ]
    assert calls


def test_drag_drop_callback_logic():
    "Test drag_drop_callback logic"
    # This is an internal function defined in __init__, so we can't test it directly easily
    # without emitting the signal.
    slist = Document()
    tree = slist

    # Mock the necessary Gtk methods on the tree instance
    tree.drag_dest_get_target_list = MagicMock()
    tree.drag_dest_find_target = MagicMock()
    tree.drag_get_data = MagicMock()

    MagicMock()

    # Case 1: No target found
    tree.drag_dest_find_target.return_value = None
    # We emit "drag-drop" signal
    # But connecting to the signal and emitting it runs the real callback.
    # The real callback uses methods on 'tree' which is 'slist'.
    # So mocking slist methods should work.

    # However, Gtk signal emission might be tricky without a main loop or realized widget.
    # But we can try to find the callback function in the signal connections?
    # Easier to trigger it via emit if possible.
    # Or just rely on the fact that we can't easily reach it without heavy mocking of Gtk.


def test_drag_data_get_and_drop_callbacks(mocker):
    "Test drag_data_get_callback and drag_drop_callback by capturing them"
    captured_callbacks = {}
    original_connect = Gtk.TreeView.connect

    def mocked_connect(self, signal_name, callback):
        captured_callbacks[signal_name] = callback
        return original_connect(self, signal_name, callback)

    mocker.patch("gi.repository.Gtk.TreeView.connect", mocked_connect)
    slist = Document()

    # Test drag_data_get_callback
    assert "drag-data-get" in captured_callbacks
    selection_data = MagicMock()
    selection_data.get_target.return_value = "Glib::Scalar"
    captured_callbacks["drag-data-get"](slist, MagicMock(), selection_data, ID_PAGE, 0)
    selection_data.set.assert_called_with("Glib::Scalar", 8, [])

    # Test drag_drop_callback
    assert "drag-drop" in captured_callbacks
    slist.drag_dest_get_target_list = MagicMock(return_value=True)
    slist.drag_dest_find_target = MagicMock(return_value="text/uri-list")
    slist.drag_get_data = MagicMock()
    result = captured_callbacks["drag-drop"](slist, MagicMock(), 0, 0, 0)
    assert result is True
    slist.drag_get_data.assert_called_once()

    # Case where no target found
    slist.drag_dest_find_target.return_value = None
    result = captured_callbacks["drag-drop"](slist, MagicMock(), 0, 0, 0)
    assert result is False


def test_delete_selection_extra_reselect():
    "Test delete_selection_extra re-selecting nearest page"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    def mock_delete_selection(_self=None, context=None, **kwargs):
        del context
        # We MUST capture the indices before deleting anything from data.
        indices_to_del = sorted(slist.get_selected_indices(), reverse=True)
        model = slist.get_model()
        for i in indices_to_del:
            itr = model.iter_nth_child(None, i)
            model.remove(itr)

        if "finished_callback" in kwargs:
            kwargs["finished_callback"]()

    slist.delete_selection = mock_delete_selection

    # Delete the middle page (index 1, uuid 102)
    slist.get_selection().unselect_all()
    slist.select(1)
    slist.delete_selection_extra()
    assert len(slist.data) == 2
    assert slist.data[0][2] == 101
    assert slist.data[1][2] == 103
    # After deletion, _after_delete should select index 1 (uuid 103)
    assert slist.get_selected_indices() == [1]

    # Delete the last page (index 1, uuid 103)
    slist.get_selection().unselect_all()
    slist.select(1)
    slist.delete_selection_extra()
    assert len(slist.data) == 1
    assert slist.data[0][2] == 101
    # After deletion, index 1 becomes invalid, so it should select index 0
    assert slist.get_selected_indices() == [0]

    # Delete all (index 0, uuid 101)
    slist.get_selection().unselect_all()
    slist.select(0)
    slist.delete_selection_extra()
    assert len(slist.data) == 0


def test_find_page_by_uuid_index():
    "Test find_page_by_uuid returns the page index"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    assert slist.find_page_by_uuid(102) == 1, "found page index"
    assert slist.find_page_by_uuid(999) is None, "missing page returns None"


def test_get_page_index_selected_none():
    "Test get_page_index with 'selected' and no pages selected"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.get_selection().unselect_all()
    error_callback = MagicMock()
    assert slist.get_page_index("selected", error_callback) == []
    error_callback.assert_called_with(None, "Get page", "No pages selected")


def test_init_with_kwargs():
    "Test BaseDocument __init__ with kwargs"
    slist = Document(custom_attr="value")
    assert vars(slist)["custom_attr"] == "value"


def test_create_pidfile_permission_error():
    "Test create_pidfile with PermissionError"
    slist = Document()
    with patch("tempfile.TemporaryFile", side_effect=PermissionError("no permission")):
        assert slist.create_pidfile({}) is None


def test_cancel_empty_queues(mock_thread):
    "Test cancel method with already empty queues"
    mock_thread.requests.get.side_effect = queue.Empty
    mock_thread.responses.get.side_effect = queue.Empty
    slist = Document()
    slist.cancel(MagicMock())
    assert slist.thread.cancel is True


def test_paste_selection_after_into_or_after():
    "Test paste_selection with INTO_OR_AFTER"
    slist = Document()
    slist.add_page(1, None, 101)

    data_to_paste = [[1, None, 101]]

    def mock_send(cmd, _args, data_callback=None, finished_callback=None):
        del finished_callback
        if cmd == "clone_pages":
            response = MagicMock()
            response.info = {"type": "page", "new_pages": [[2, None, 102]]}
            data_callback(response)

    slist.thread.send = mock_send

    slist.paste_selection(
        data=data_to_paste, dest=0, how=Gtk.TreeViewDropPosition.INTO_OR_AFTER
    )
    assert len(slist.data) == 2
    assert slist.data[1][2] == 102


def test_cancel_with_pid_1(mock_thread):
    "Test cancel method does not kill PID 1"
    mock_thread.running_pids = {"pid1.pid": "pid1.pid"}
    slist = Document()

    with patch("basedocument.slurp", return_value=1), patch("os.killpg") as mock_killpg:
        slist.cancel(MagicMock())
        mock_killpg.assert_not_called()


def test_cancel_with_empty_pid(mock_thread):
    "Test cancel method with empty pid from slurp"
    mock_thread.running_pids = {"empty.pid": "empty.pid"}
    slist = Document()

    with (
        patch("basedocument.slurp", return_value=""),
        patch("os.killpg") as mock_killpg,
    ):
        slist.cancel(MagicMock())
        mock_killpg.assert_not_called()


def test_cancel_already_dead_pid(mock_thread):
    "Test cancel handles a pid that is already dead (ProcessLookupError)"
    mock_thread.running_pids = {"dead.pid": "dead.pid"}
    slist = Document()

    with (
        patch("basedocument.slurp", return_value="99999"),
        patch("os.killpg", side_effect=ProcessLookupError),
    ):
        slist.cancel(MagicMock())

    assert "dead.pid" not in slist.thread.running_pids, "pidfile deregistered"


def test_delete_selection_callback_removes_rows():
    "Test delete_selection data_callback removes rows from model"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    # We need to trigger the _data_callback in delete_selection
    captured = {}

    def mock_send(cmd, args, data_callback=None, **kwargs):
        del args, kwargs
        if cmd == "delete_pages":
            captured["data_callback"] = data_callback

    slist.thread.send = mock_send
    slist.select([0, 1])
    slist.delete_selection()

    assert captured["data_callback"] is not None
    response = MagicMock()
    response.info = {"type": "page"}
    # The callback uses 'model' and 'paths' from the outer scope
    # We need to make sure they are available or mocked.
    # In the real code:
    # model, paths = self.get_selection().get_selected_rows()
    # It relies on these being captured in the closure.

    # Before calling, verify model has 2 rows
    assert len(slist.get_model()) == 2
    captured["data_callback"](response)
    # After calling, model should be empty because we selected 0 and 1
    assert len(slist.get_model()) == 0


def test_delete_all_pages_sends_page_ids_and_clears_on_response():
    "Test delete_all_pages sends all page ids and clears rows in data_callback"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)

    captured = {}

    def mock_send(cmd, args, data_callback=None, **kwargs):
        captured["cmd"] = cmd
        captured["args"] = args
        captured["data_callback"] = data_callback
        captured["kwargs"] = kwargs

    slist.thread.send = mock_send
    finished = Mock()
    slist.delete_all_pages(finished_callback=finished)

    assert captured["cmd"] == "delete_pages"
    assert captured["args"] == {"page_ids": [101, 102]}
    assert (
        "finished_callback" not in captured["kwargs"]
    ), "finished_callback not forwarded to the thread"

    # rows are only removed once the thread responds
    assert len(slist.get_model()) == 2

    response = MagicMock()
    response.info = {"type": "page", "remove": [0, 1]}
    captured["data_callback"](response)

    assert len(slist.get_model()) == 0
    finished.assert_called_once_with()


def test_delete_all_pages_finished_called_on_other_response():
    "Test delete_all_pages calls finished_callback even for other responses"
    slist = Document()
    slist.add_page(1, None, 101)

    captured = {}

    def mock_send(cmd, _args, data_callback=None, **kwargs):
        del cmd, kwargs
        captured["data_callback"] = data_callback

    slist.thread.send = mock_send
    finished = Mock()
    slist.delete_all_pages(finished_callback=finished)

    response = MagicMock()
    response.info = {"type": "other"}
    captured["data_callback"](response)

    assert len(slist.get_model()) == 1, "rows untouched"
    finished.assert_called_once_with()


def test_delete_all_pages_without_finished_callback():
    "Test delete_all_pages works without a finished_callback"
    slist = Document()
    slist.add_page(1, None, 101)

    captured = {}

    def mock_send(cmd, args, data_callback=None, **kwargs):
        del cmd
        captured["args"] = args
        captured["data_callback"] = data_callback
        captured["kwargs"] = kwargs

    slist.thread.send = mock_send
    slist.delete_all_pages()

    assert captured["args"] == {"page_ids": [101]}
    assert captured["kwargs"] == {}, "no extra kwargs forwarded"

    response = MagicMock()
    response.info = {"type": "page", "remove": [0]}
    captured["data_callback"](response)

    assert len(slist.get_model()) == 0


def test_delete_selection_extra_signal():
    "Test delete_selection_extra emits changed signal"
    slist = Document()
    slist.add_page(1, None, 101)
    mock_changed = MagicMock()
    slist.selection_changed_signal = slist.get_selection().connect(
        "changed", mock_changed
    )
    slist.select([0])
    slist.delete_selection_extra()

    mlp = safe_mainloop()
    GLib.idle_add(mlp.quit)
    mlp.run()

    mock_changed.assert_called()


def test_paste_selection_insert_after():
    "Test paste_selection with Gtk.TreeViewDropPosition.AFTER"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(5, None, 105)

    data_to_paste = [[1, None, 101]]

    def mock_send(cmd, _args, data_callback=None, finished_callback=None):
        del finished_callback
        if cmd == "clone_pages":
            response = MagicMock()
            response.info = {"type": "page", "new_pages": [[2, None, 102]]}
            data_callback(response)

    slist.thread.send = mock_send

    # dest is path string or index? code says dest = int(kwargs["dest"])
    slist.paste_selection(
        data=data_to_paste, dest=0, how=Gtk.TreeViewDropPosition.AFTER
    )
    # 102 should be inserted at index 1
    assert slist.data[1][2] == 102
    assert slist.data[1][0] == 2  # renumbered to dest-1[0] + 1 = 1 + 1 = 2


def test_delete_renumbers():
    "Delete renumbers remaining pages consecutively"
    slist = Document()
    slist.add_page(1, None, 101)
    slist.add_page(2, None, 102)
    slist.add_page(3, None, 103)

    slist.get_selection().unselect_all()
    slist.select(1)  # select page 2
    mlp = safe_mainloop()

    def _done(_result=None):
        mlp.quit()

    slist.delete_selection(finished_callback=_done)
    mlp.run()

    assert [row[0] for row in slist.data] == [1, 2], "pages renumbered"
    assert [row[2] for row in slist.data] == [101, 103], "correct pages remain"


def test_create_pidfile_ioerror():
    "Test create_pidfile with IOError"
    slist = Document()
    # Mock tempfile.TemporaryFile to raise IOError
    with patch("tempfile.TemporaryFile", side_effect=OSError("disk full")):
        assert slist.create_pidfile({}) is None


def test_open_session_error_callback():
    "Test open_session error callback during send"
    slist = Document()
    temp_dir = tempfile.mkdtemp()
    slist.dir = pathlib.Path(temp_dir)
    db_path = slist.dir / "test.db"
    db_path.write_text("dummy", encoding="utf-8")
    errors = []

    def mock_send(_process, *_args, **kwargs):
        def run_callbacks():
            if "error_callback" in kwargs:
                response = MagicMock()
                response.status = "open failed"
                kwargs["error_callback"](response)
            return False

        GLib.idle_add(run_callbacks)
        return MagicMock()

    slist.thread.send = mock_send
    slist.open_session(
        db=str(db_path), error_callback=lambda _src, _msg, status: errors.append(status)
    )
    mlp = safe_mainloop(500)
    GLib.timeout_add(100, mlp.quit)
    mlp.run()
    assert errors == ["open failed"]
    shutil.rmtree(temp_dir)

"test Renumber class"

from unittest.mock import MagicMock
import tempfile
import gi
from document import Document
from dialog.renumber import Renumber

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1(rose_pnm, mainloop_with_timeout, temp_db, clean_up_files):
    "basic tests for Renumber class"
    slist = Document(db=temp_db.name)
    dialog = Renumber(document=slist, transient_for=Gtk.Window())
    assert isinstance(dialog, Renumber)
    assert dialog.start == 1, "default start for empty document"
    assert dialog.increment == 1, "default step for empty document"
    assert dialog.range == "selected", "default range for empty document"

    with tempfile.TemporaryDirectory() as tempdir:
        kwargs = {
            "filename": rose_pnm.name,
            "resolution": 72,
            "page": 1,
            "dir": tempdir,
        }
        slist.import_scan(**kwargs)
        kwargs["page"] = 2
        loop1 = mainloop_with_timeout()
        kwargs["finished_callback"] = lambda response: loop1.quit()
        slist.import_scan(**kwargs)
        loop1.run()
        slist.select(1)
        assert slist.get_selected_indices() == [1], "selected"
        dialog.update()  # normally triggered by select()
        assert dialog.start == 2, "start for document with start clash"
        assert dialog.increment == 1, "step for document with start clash"

        #########################

        slist.data[1][0] = 3
        kwargs["page"] = 5
        del kwargs["finished_callback"]
        slist.import_scan(**kwargs)
        kwargs["page"] = 7
        loop2 = mainloop_with_timeout()
        kwargs["finished_callback"] = lambda response: loop2.quit()
        slist.import_scan(**kwargs)
        loop2.run()
        slist.select([2, 3])
        assert slist.get_selected_indices() == [2, 3], "selected"
        dialog.update()  # normally triggered by select()
        assert dialog.start == 4, "start for document with start and step clash"
        assert dialog.increment == 1, "step for document with start and step clash"

        #########################

        dialog.increment = 0
        assert dialog.start == 4, "start for document with negative step"
        assert dialog.increment == -2, "step for document with negative step"

        asserted = False

        def before_renumber_cb(*args):
            nonlocal asserted
            asserted = True

        dialog.connect("before-renumber", before_renumber_cb)
        dialog.renumber()
        assert asserted, "before-renumber signal fired on renumber"

    #########################

    clean_up_files(slist.thread.db_files)


def test_renumber_properties(mocker):
    "Test properties and their setters"
    dialog = Renumber(transient_for=Gtk.Window())

    # Test start setter
    mock_emit = mocker.patch.object(dialog, "emit")

    # Change value
    dialog.start = 10
    assert dialog.start == 10
    mock_emit.assert_called_with("changed-start", 10)

    # Same value (no-op)
    mock_emit.reset_mock()
    dialog.start = 10
    mock_emit.assert_not_called()

    # Test increment setter
    # Change value
    dialog.increment = 5
    assert dialog.increment == 5
    mock_emit.assert_called_with("changed-increment", 5)

    # Same value (no-op)
    mock_emit.reset_mock()
    dialog.increment = 5
    mock_emit.assert_not_called()

    # Test range setter
    # Change value
    dialog.range = "all"
    assert dialog.range == "all"
    mock_emit.assert_called_with("changed-range", "all")

    # Same value (no-op)
    mock_emit.reset_mock()
    dialog.range = "all"
    mock_emit.assert_not_called()


def test_renumber_document_change():
    "Test changing the document and signal disconnection"
    dialog = Renumber(transient_for=Gtk.Window())
    doc1 = MagicMock()
    doc1.get_model.return_value = MagicMock()
    doc1.get_selection.return_value = MagicMock()

    # Mock connect to return a dummy handler id
    doc1.get_model.return_value.connect.return_value = 101
    doc1.get_selection.return_value.connect.return_value = 102

    # Set initial document
    dialog.document = doc1
    assert dialog._row_signal is not None
    assert dialog._selection_signal is not None

    # Create doc2
    doc2 = MagicMock()
    doc2.get_model.return_value = MagicMock()
    doc2.get_selection.return_value = MagicMock()

    # Set new document
    dialog.document = doc2

    doc2.disconnect.assert_any_call(101)  # 101 was row_signal
    doc2.disconnect.assert_any_call(102)  # 102 was selection_signal

    # And check same value setter
    doc2.disconnect.reset_mock()
    dialog.document = doc2
    doc2.disconnect.assert_not_called()


def test_renumber_update_logic():
    "Test the update logic with conflicting settings"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()

    # Mock data length for range calculation
    doc.data = [0] * 10  # 10 pages
    doc.get_selected_indices.return_value = [0, 1, 2]

    dialog._document = (
        doc  # Set directly to avoid callback overhead if needed, or use property
    )

    # Setup valid_renumber to fail initially then succeed
    # It is called in a while loop: while not slist.valid_renumber(...)
    # We want to break the loop eventually.
    # valid_renumber args: start, step, range

    # Scenario: start=1, step=1. Valid? No.
    # Update modifies start/step.
    # We need to control valid_renumber return values based on inputs.

    def side_effect(start, _step, _rng):
        # Allow if start > 5
        if start > 5:
            return True
        return False

    doc.valid_renumber.side_effect = side_effect

    # Force _start_old / _step_old to calculate dstart/dstep
    dialog._start_old = 1
    dialog._step_old = 1

    # Change start to 2 (dstart = 1)
    dialog._start = 2

    # Loop Logic:
    # start=2, step=1. valid? No.
    # n depends on range. default "selected". len([0,1,2]) - 1 = 2.
    # start + step*n = 2 + 1*2 = 4. 4 < 1? No.
    # start += dstart (1) -> 3. step += dstep (0) -> 1.
    # 3, 1 valid? No.
    # ...
    # 6, 1 valid? Yes.

    dialog.update()

    assert dialog.start == 6
    assert dialog.increment == 1

    # Test range="all" path
    dialog.range = "all"

    # n = len(doc.data) - 1 = 9
    # Reset valid_renumber to fail unless start > 10
    def side_effect_all(start, _step, _rng):
        return start > 10

    doc.valid_renumber.side_effect = side_effect_all

    dialog._start = 2
    dialog._start_old = 1
    dialog.update()

    # Should loop until start > 10
    assert dialog.start == 11


def test_renumber_update_negative_adjustment():
    "Test update logic when adjustments make page numbers negative"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()
    doc.data = [0] * 10
    doc.get_selected_indices.return_value = [0, 1, 2]
    dialog._document = doc

    # Scenario: decrementing start
    dialog._start_old = 5
    dialog._step_old = 1
    dialog._start = 4  # dstart = -1
    dialog._increment = 1  # dstep = 0

    # valid_renumber always false to trigger logic, but need a break condition
    # to avoid infinite loop.
    # Let's say it becomes valid if start is very small? No, logic prevents small.
    # Logic: if start + step * n < 1: ...
    # n = 2.
    # Let's make step negative to force < 1

    dialog._increment = -10
    dialog._step_old = -10
    # start=4, step=-10. n=2. 4 + (-20) = -16 < 1.
    # dstart = -1. dstart < 0 is True. -> dstart = 1.
    # So it reverses the direction of change?

    # We need valid_renumber to return True eventually.
    count = 0

    def side_effect(_start, _step, _rng):
        nonlocal count
        count += 1
        if count > 2:
            return True
        return False

    doc.valid_renumber.side_effect = side_effect

    dialog.update()

    # Just ensuring it doesn't crash and eventually exits
    assert count > 0


def test_renumber_execution_error(mocker):
    "Test renumber() when valid_renumber returns False"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()
    dialog._document = doc

    doc.valid_renumber.return_value = False

    mock_emit = mocker.patch.object(dialog, "emit")

    dialog.renumber()

    mock_emit.assert_called_with("error", mocker.ANY)


def test_renumber_update_all_pages_negative():
    "Test update logic with range='all' and negative page numbers"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()
    doc.data = [0] * 5  # n = 4
    dialog.document = doc
    dialog.range = "all"

    # Force initialization of old values
    dialog._start_old = 10
    dialog._step_old = 1
    dialog._start = 1
    dialog._increment = -1

    # We want to trigger update() and hit start + step * n < 1
    # with dstart < 0 and then dstart >= 0
    doc.valid_renumber.side_effect = [False, False, False, True, True, True]

    # Trigger update manually to control dstart/dstep precisely
    # dstart = 1 - 10 = -9
    # dstep = -1 - 1 = -2
    # but dstep becomes 0 because both changed
    dialog.update()

    # Loop Logic:
    # 1. start=1, step=-1. valid? No.
    #    n=4. 1 + -1*4 = -3 < 1.
    #    dstart=-9 < 0. So dstart = 1.
    #    start += 1 -> 2. step += 0 -> -1.
    # 2. start=2, step=-1. valid? No.
    #    2 + -1*4 = -2 < 1.
    #    dstart=1 >= 0. So dstep = 1.
    #    start += 1 -> 3. step += 1 -> 0.
    #    if step == 0: step += 1 -> 1.
    # 3. start=3, step=1. valid? No (3rd False).
    #    3 + 1*4 = 7 >= 1.
    #    start += 1 -> 4. step += 1 -> 2.
    # 4. start=4, step=2. valid? Yes (from side effect).
    assert dialog.start == 4
    assert dialog.increment == 2


def test_renumber_update_step_zero_branch():
    "Test update logic when step becomes 0"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()
    doc.data = [0] * 3
    doc.get_selected_indices.return_value = [0, 1]  # n = 1
    dialog.document = doc

    dialog._start_old = 1
    dialog._step_old = 1
    dialog._start = 1
    dialog._increment = 1

    doc.valid_renumber.side_effect = [False, True, True, True]

    # Change increment to 0 (dstep = -1)
    dialog.increment = 0

    # Loop Logic:
    # 1. start=1, step=0. valid? No (step=0 is invalid)
    #    n=1. 1 + 0*1 = 1. Not < 1.
    #    start += 0 -> 1. step += -1 -> -1.
    #    if step == 0: ... (not 0)
    # 2. start=1, step=-1. valid? Yes.
    assert dialog.increment == -1


def test_renumber_update_step_becomes_zero():
    "Test update logic when step becomes 0 during loop and is adjusted"
    dialog = Renumber(transient_for=Gtk.Window())
    doc = MagicMock()
    doc.data = [0] * 3
    doc.get_selected_indices.return_value = [0, 1]  # n = 1
    dialog.document = doc

    dialog._start_old = 1
    dialog._step_old = 2
    dialog._start = 1
    dialog._increment = 1  # dstep = -1

    doc.valid_renumber.side_effect = [False, False, True, True, True]

    dialog.update()

    # Loop Logic:
    # 1. start=1, step=1. valid? No.
    #    n=1. 1 + 1*1 = 2. Not < 1.
    #    start += 0 -> 1. step += -1 -> 0.
    #    if step == 0: step += -1 -> -1.
    # 2. start=1, step=-1. valid? No.
    #    n=1. 1 - 1 = 0 < 1.
    #    dstart=0 >= 0. So dstep = 1.
    #    start += 0 -> 1. step += 1 -> 0.
    #    if step == 0: step += 1 -> 1.
    # 3. start=1, step=1. valid? Yes.
    assert dialog.increment == 1

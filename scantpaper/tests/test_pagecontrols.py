"tests for PageControls dialog component"

import tempfile
from unittest.mock import MagicMock

import gi
import pytest
from dialog.pagecontrols import PageControls, _extended_pagenumber_checkbox_callback
from dialog.scan import Scan
from document import Document

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def test_side_to_scan_invalid_value():
    "Test that ValueError is raised for invalid side-to-scan values"
    page_controls = PageControls()

    set_side_to_scan = vars(PageControls.side_to_scan)["fset"]

    with pytest.raises(ValueError, match="Invalid value for side-to-scan: invalid"):
        set_side_to_scan(page_controls, "invalid")


def test_do_spin_buttoni_value_changed():
    "Test that the position advance spin button sets the increment, allowing 0"
    page_controls = PageControls()

    spin_buttoni = MagicMock()
    spin_buttoni.get_value.return_value = 0
    page_controls._do_spin_buttoni_value_changed(spin_buttoni)
    assert page_controls.page_number_increment == 0


def test_do_start_page_changed():
    "Test that _do_start_page_changed sets the page-number-start property"
    page_controls = PageControls()

    spin_buttons = MagicMock()
    spin_buttons.get_value.return_value = 5
    page_controls._do_start_page_changed(spin_buttons)
    assert page_controls.page_number_start == 5


def test_reset_batch():
    "Test that _reset_batch clears the facing batch tracking"
    page_controls = PageControls()
    page_controls._batch_start = 1
    page_controls._batch_n = 3
    page_controls.max_pages = 3
    page_controls._reset_batch()
    assert page_controls._batch_start is None
    assert page_controls._batch_n == 0
    assert page_controls.max_pages == 0


def test_fix_batch():
    "Test that _fix_batch bounds the reverse pass by the facing batch"
    page_controls = PageControls()
    page_controls._batch_start = 1
    page_controls._batch_n = 3
    page_controls.allow_batch_flatbed = True
    page_controls.num_pages = 0
    page_controls._fix_batch()
    assert page_controls.max_pages == 3
    assert page_controls.num_pages == 3


def test_extended_pagenumber_checkbox_callback():
    "Test that the extended page numbering checkbox shows/hides the frames"
    page_controls = PageControls()
    page_controls.frames = MagicMock()
    page_controls.framex = MagicMock()
    widget = MagicMock()

    # Extended numbering active
    widget.get_active.return_value = True
    _extended_pagenumber_checkbox_callback(widget, None, [page_controls])
    page_controls.frames.hide.assert_called_once()
    page_controls.framex.show_all.assert_called_once()

    # Extended numbering inactive
    page_controls.frames.hide.reset_mock()
    page_controls.framex.show_all.reset_mock()
    widget.get_active.return_value = False
    _extended_pagenumber_checkbox_callback(widget, None, [page_controls])
    page_controls.frames.show_all.assert_called_once()
    page_controls.framex.hide.assert_called_once()


def test_page_controls(rose_pnm, temp_db, mainloop_with_timeout):
    "test PageControls"
    page_controls = Scan(title="title", transient_for=Gtk.Window())
    assert isinstance(page_controls, PageControls), "Created PageControls dialog"

    slist = Document(db=temp_db.name)
    with tempfile.TemporaryDirectory() as tempdir:
        loop1 = mainloop_with_timeout()
        slist.import_scan(
            filename=rose_pnm,
            resolution=72,
            dir=tempdir,
            finished_callback=lambda _response: loop1.quit(),
        )
        loop1.run()
        page_controls.document = slist
        assert page_controls.page_number_start == 1, (
            "page-number-start unaffected by document"
        )

        # Single-sided scans append without touching the facing batch
        page_controls.sided = "single"
        insert_after, side = page_controls._insert_target(1)
        assert insert_after is None, "single-sided scans append"
        assert side == "facing", "single-sided scans append"

        # Double-sided facing pass tracks the batch after the last page
        page_controls.sided = "double"
        page_controls.side_to_scan = "facing"
        insert_after, side = page_controls._insert_target(1)
        assert insert_after is None, "facing scans append"
        assert side == "facing", "facing scans append"
        assert page_controls._batch_start == 2, (
            "facing batch starts after the last page"
        )
        assert page_controls._batch_n == 1, "facing batch counts scanned pages"

        # Reverse pass inserts the back page after its front page
        page_controls._batch_start = 1
        page_controls._batch_n = 1
        page_controls.side_to_scan = "reverse"
        insert_after, side = page_controls._insert_target(1)
        assert side == "reverse"
        assert insert_after == slist.data[0][2], (
            "reverse page inserted after front page"
        )

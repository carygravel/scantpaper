"""tests for PageControls dialog component."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import gi
import pytest

from scantpaper.const import POINTS_PER_INCH
from scantpaper.dialog.pagecontrols import (
    PageControls,
    _extended_pagenumber_checkbox_callback,
)
from scantpaper.dialog.scan import Scan
from scantpaper.document import Document

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.loop_helpers import _MainLoopWrapper


def test_side_to_scan_invalid_value() -> None:
    """Test that ValueError is raised for invalid side-to-scan values."""
    page_controls = PageControls()

    set_side_to_scan = vars(PageControls.side_to_scan)["fset"]

    with pytest.raises(ValueError, match="Invalid value for side-to-scan: invalid"):
        set_side_to_scan(page_controls, "invalid")


def test_do_spin_buttoni_value_changed() -> None:
    """Test that the position advance spin button sets the increment, allowing 0."""
    page_controls = PageControls()

    spin_buttoni = MagicMock()
    spin_buttoni.get_value.return_value = 0
    page_controls._do_spin_buttoni_value_changed(spin_buttoni)
    assert page_controls.page_number_increment == 0


def test_refresh_flatbed_source_without_thread() -> None:
    """An unset thread keeps the last known source value."""
    page_controls = PageControls()
    page_controls._flatbed_source_cached = False
    assert page_controls._refresh_flatbed_source() is False


def test_refresh_flatbed_source_keeps_last_value_on_error() -> None:
    """A source read failure keeps the last known value."""
    page_controls = PageControls()
    page_controls.thread = MagicMock()
    page_controls.available_scan_options = MagicMock()
    page_controls.available_scan_options.flatbed_selected.side_effect = TimeoutError
    page_controls._flatbed_source_cached = False

    assert page_controls._refresh_flatbed_source() is False


def test_do_start_page_changed() -> None:
    """Test that _do_start_page_changed sets the page-number-start property."""
    page_controls = PageControls()

    spin_buttons = MagicMock()
    spin_buttons.get_value.return_value = 5
    page_controls._do_start_page_changed(spin_buttons)
    assert page_controls.page_number_start == 5


def test_do_clicked_scan_all() -> None:
    """Test that activating the 'all pages' button selects all pages."""
    page_controls = PageControls()
    page_controls.allow_batch_flatbed = True
    page_controls.num_pages = 3

    bscanall = MagicMock()
    bscanall.get_active.return_value = True
    page_controls._do_clicked_scan_all(bscanall, None)
    assert page_controls.num_pages == 0, "all pages selected"

    page_controls.num_pages = 3
    bscanall.get_active.return_value = False
    page_controls._do_clicked_scan_all(bscanall, None)
    assert page_controls.num_pages == 3, "inactive button leaves num_pages alone"


def test_do_clicked_scan_number() -> None:
    """Test that activating the '# pages' button takes the spin button value."""
    page_controls = PageControls()
    page_controls.allow_batch_flatbed = True
    page_controls._flatbed_source_cached = False
    page_controls.num_pages = 0

    bscannum = MagicMock()
    bscannum.get_active.return_value = True
    spin_buttonn = MagicMock()
    spin_buttonn.get_value.return_value = 5

    page_controls._do_clicked_scan_number(bscannum, spin_buttonn)
    assert page_controls.num_pages == 5, "page count taken from the spin button"

    page_controls.num_pages = 0
    bscannum.get_active.return_value = False
    page_controls._do_clicked_scan_number(bscannum, spin_buttonn)
    assert page_controls.num_pages == 0, "inactive button leaves num_pages alone"


def test_do_buttons_clicked() -> None:
    """Test that the sided buttons set the sided property."""
    page_controls = PageControls()

    buttons = MagicMock()
    buttons.get_active.return_value = True
    page_controls._do_buttons_clicked(buttons)
    assert page_controls.sided == "single"

    buttons.get_active.return_value = False
    page_controls._do_buttons_clicked(buttons)
    assert page_controls.sided == "double"


def test_reset_batch() -> None:
    """Test that _reset_batch clears the facing batch tracking."""
    page_controls = PageControls()
    page_controls._batch_start = 1
    page_controls._batch_n = 3
    page_controls.max_pages = 3
    page_controls._reset_batch()
    assert page_controls._batch_start is None
    assert page_controls._batch_n == 0
    assert page_controls.max_pages == 0


def test_fix_batch() -> None:
    """Test that _fix_batch bounds the reverse pass by the facing batch."""
    page_controls = PageControls()
    page_controls._batch_start = 1
    page_controls._batch_n = 3
    page_controls.allow_batch_flatbed = True
    page_controls._flatbed_source_cached = False
    page_controls.num_pages = 0
    page_controls._fix_batch()
    assert page_controls.max_pages == 3
    assert page_controls.num_pages == 3


def test_extended_pagenumber_checkbox_callback() -> None:
    """Test that the extended page numbering checkbox shows/hides the frames."""
    page_controls = PageControls()
    page_controls.frames = MagicMock()
    page_controls.framex = MagicMock()
    widget = MagicMock()

    # Extended numbering active
    widget.get_active.return_value = True
    _extended_pagenumber_checkbox_callback(widget, None, [page_controls])
    page_controls.frames.hide.assert_called_once()
    page_controls.framex.show.assert_called_once()

    # Extended numbering inactive
    page_controls.frames.hide.reset_mock()
    page_controls.framex.show.reset_mock()
    widget.get_active.return_value = False
    _extended_pagenumber_checkbox_callback(widget, None, [page_controls])
    page_controls.frames.show.assert_called_once()
    page_controls.framex.hide.assert_called_once()


def test_page_controls(
    rose_pnm: str,
    temp_db: object,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Test PageControls."""
    page_controls = Scan(title="title", transient_for=Gtk.Window())
    assert isinstance(page_controls, PageControls), "Created PageControls dialog"

    slist = Document(db=temp_db.name)
    with tempfile.TemporaryDirectory() as tempdir:
        loop1 = mainloop_with_timeout()
        slist.import_scan(
            filename=rose_pnm,
            resolution=POINTS_PER_INCH,
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


def test_page_options_rows_keep_their_natural_height() -> None:
    """Rows in the page options page do not request vertical expansion."""
    page_controls = Scan(title="title", transient_for=Gtk.Window())
    page = page_controls._notebook_pages[0]

    assert page.get_valign() == Gtk.Align.START, "page content is top-aligned"
    assert not page.compute_expand(Gtk.Orientation.VERTICAL), (
        "page content claims surplus height"
    )
    assert not page_controls.framen.compute_expand(Gtk.Orientation.VERTICAL), (
        "# Pages frame claims surplus height"
    )
    assert not page_controls.frames.compute_expand(Gtk.Orientation.VERTICAL), (
        "Source document frame claims surplus height"
    )


def test_page_options_frame_keeps_natural_height_in_tall_window(
    wait_until: Callable[[Callable[[], bool]], None],
) -> None:
    """A window taller than the page does not stretch the # Pages frame."""
    dialog = Scan(title="title")
    dialog.set_default_size(450, 1000)
    dialog.present()
    frame = dialog.framen
    natural_height = frame.measure(Gtk.Orientation.VERTICAL, -1)[1]

    wait_until(lambda: dialog.get_mapped() and frame.get_height() > 0)

    assert frame.get_height() <= natural_height + 2, (
        "the # Pages frame absorbed the surplus window height"
    )
    dialog.destroy()


def test_page_options_scroll_in_short_window(
    wait_until: Callable[[Callable[[], bool]], None],
) -> None:
    """A window shorter than the page keeps the page scrollable."""
    dialog = Scan(title="title")
    dialog.set_default_size(450, 300)
    dialog.present()
    page = dialog.notebook.get_nth_page(0)
    adjustment = page.get_vadjustment()

    wait_until(
        lambda: dialog.get_mapped() and adjustment.get_upper() > 0,
    )

    assert adjustment.get_upper() > adjustment.get_page_size(), (
        "the page does not scroll in a short window"
    )
    dialog.destroy()

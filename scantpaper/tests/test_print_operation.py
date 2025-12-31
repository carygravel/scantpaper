"Tests for the PrintOperation class"

from unittest.mock import MagicMock
import pytest
from print_operation import PrintOperation
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_slist():
    "Fixture for mock simplelist"
    slist = MagicMock()
    # Mock data structure: [page_number, ?, page_object]
    page1 = MagicMock()
    page1.get_pixbuf.return_value.get_width.return_value = 100
    page1.get_pixbuf.return_value.get_height.return_value = 100
    page1.resolution = (72, 72, "pixels")

    page2 = MagicMock()
    page3 = MagicMock()
    page3.get_pixbuf.return_value.get_width.return_value = 100
    page3.get_pixbuf.return_value.get_height.return_value = 100
    page3.resolution = (72, 72, "pixels")

    slist.data = [[1, "uuid1", page1], [2, "uuid2", page2], [3, "uuid3", page3]]
    return slist


def test_init(mock_slist):
    "Test initialization"
    settings = Gtk.PrintSettings()
    op = PrintOperation(slist=mock_slist, settings=settings)
    assert op.slist == mock_slist


def test_begin_print_all(mock_slist):
    "Test begin_print_callback with ALL pages"
    settings = MagicMock()
    settings.get_print_pages.return_value = Gtk.PrintPages.ALL

    op = PrintOperation(slist=mock_slist, settings=None)
    op.get_print_settings = MagicMock(return_value=settings)
    op.set_n_pages = MagicMock()

    op.begin_print_callback(op, None)

    op.set_n_pages.assert_called_once_with(3)


def test_begin_print_ranges(mock_slist):
    "Test begin_print_callback with RANGES"
    settings = MagicMock()
    settings.get_print_pages.return_value = Gtk.PrintPages.RANGES

    # Gtk PageRange is inclusive. 0-0 means page 1.
    page_range = MagicMock()
    page_range.start = 0
    page_range.end = 0
    settings.get_page_ranges.return_value = [page_range]

    op = PrintOperation(slist=mock_slist, settings=None)
    op.get_print_settings = MagicMock(return_value=settings)
    op.set_n_pages = MagicMock()

    op.begin_print_callback(op, None)

    # With current code, range(1, 1) is empty, so 0 pages.
    # This expects the BUG behavior to confirm it.
    # If the bug exists, this will pass with 0.
    # If I want to fix it, I will assert 1 and it will fail.
    # Let's assert 1 to see it fail, validating the bug.
    op.set_n_pages.assert_called_once_with(1)


def test_draw_page(mock_slist, mocker):
    "Test draw_page_callback"
    op = PrintOperation(slist=mock_slist, settings=None)

    context = MagicMock()
    cr = MagicMock()
    context.get_cairo_context.return_value = cr
    context.get_width.return_value = 200
    context.get_height.return_value = 200

    mock_cairo_set = mocker.patch("print_operation.Gdk.cairo_set_source_pixbuf")

    op.draw_page_callback(op, context, 0)

    cr.scale.assert_called_with(2.0, 2.0)
    mock_cairo_set.assert_called_with(cr, mock_slist.data[0][2].get_pixbuf(), 0, 0)
    cr.paint.assert_called_once()


def test_draw_page_mapped(mock_slist, mocker):
    "Test draw_page_callback with mapping"
    op = PrintOperation(slist=mock_slist, settings=None)

    # Simulate mapped pages: print only index 2 (Page 3)
    op.page_list = [2]

    context = MagicMock()
    cr = MagicMock()
    context.get_cairo_context.return_value = cr
    context.get_width.return_value = 100
    context.get_height.return_value = 100

    mock_cairo_set = mocker.patch("print_operation.Gdk.cairo_set_source_pixbuf")

    op.draw_page_callback(op, context, 0)

    # Verify it used page index 2
    page3_pixbuf = mock_slist.data[2][2].get_pixbuf()
    mock_cairo_set.assert_called_with(cr, page3_pixbuf, 0, 0)

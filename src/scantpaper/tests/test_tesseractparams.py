"""Test the Tesseract parameter browser dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

from scantpaper.dialog.tesseractparams import TesseractParametersDialog
from scantpaper.tesseract import TesseractParameter

if TYPE_CHECKING:
    import pytest

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gtk, Pango  # noqa: E402

PARAMETERS = (
    TesseractParameter("user_defined_dpi", "70", "User defined image DPI"),
    TesseractParameter("tessedit_char_whitelist", "", "Whitelist of characters"),
    TesseractParameter("user_words_file", "", "User words file"),
    TesseractParameter("tessedit_pageseg_mode", "3", "Page segmentation mode"),
    TesseractParameter("tessedit_ocr_engine_mode", "3", ""),
)

MANAGED = {
    "tessedit_pageseg_mode": "Page segmentation mode",
    "tessedit_ocr_engine_mode": "OCR engine mode",
}


def make_dialog(
    parameters: tuple[TesseractParameter, ...] | None = PARAMETERS,
) -> TesseractParametersDialog:
    """Build the dialog under test."""
    return TesseractParametersDialog(parameters=parameters, managed=MANAGED)


def row_names(dialog: TesseractParametersDialog) -> list[str]:
    """Return the names currently shown, in model order."""
    return [str(row[0]) for row in dialog._list.data]


def test_columns_and_rows() -> None:
    """The dialog shows the name, default and description of every parameter."""
    dialog = make_dialog()

    titles = [column.get_title() for column in dialog._list.get_columns()]
    assert titles == ["Name", "Default", "Description"]
    assert row_names(dialog) == [
        "tessedit_char_whitelist",
        "tessedit_ocr_engine_mode",
        "tessedit_pageseg_mode",
        "user_defined_dpi",
        "user_words_file",
    ]
    rows = {str(row[0]): row for row in dialog._list.data}
    assert rows["user_defined_dpi"][1] == "70"
    assert rows["user_defined_dpi"][2] == "User defined image DPI"
    assert rows["tessedit_char_whitelist"][1] == ""
    column = dialog._list.get_column(0)
    assert column is not None
    assert column.get_cells()[0].get_property("family") == "monospace"
    description = dialog._list.get_column(2)
    assert description is not None
    assert description.get_expand() is True
    cell = description.get_cells()[0]
    assert cell.get_property("wrap-mode") == Pango.WrapMode.WORD_CHAR
    assert cell.get_property("wrap-width") > 0
    assert dialog._scrolled.get_child() is dialog._list


def test_unavailable_list() -> None:
    """An unreadable list is reported without blocking OCR."""
    dialog = make_dialog(parameters=None)

    assert dialog._search.get_sensitive() is False
    assert dialog._list.get_visible() is False
    assert dialog._scrolled.get_visible() is False
    assert dialog._status.get_visible() is True
    assert "unavailable" in dialog._status.get_text()
    assert dialog._insert_button.get_sensitive() is False
    assert dialog.selected_name is None


def test_populate_is_a_no_op_when_the_list_is_unavailable() -> None:
    """Repopulating an unavailable list leaves its message alone."""
    dialog = make_dialog(parameters=None)
    message = dialog._status.get_text()

    dialog._populate("dpi")

    assert row_names(dialog) == []
    assert dialog._status.get_text() == message


def test_selected_name_is_none_without_a_selection() -> None:
    """No selected row means no name to insert."""
    dialog = make_dialog()
    dialog._list.get_selection().unselect_all()

    assert dialog._selected_name() is None


def test_map_focuses_the_filter(mocker: pytest.MockerFixture) -> None:
    """Opening the dialog puts the keyboard focus in the filter entry."""
    dialog = make_dialog()
    grab_focus = mocker.patch.object(dialog._search, "grab_focus")

    dialog._on_map(dialog)

    grab_focus.assert_called_once_with()


def test_filter_by_name() -> None:
    """The filter narrows the list to matching names."""
    dialog = make_dialog()

    dialog._search.set_text("dpi")
    dialog._search.emit("search-changed")

    assert row_names(dialog) == ["user_defined_dpi"]


def test_filter_by_description() -> None:
    """The filter also matches text that appears only in a description."""
    dialog = make_dialog()

    dialog._search.set_text("characters")
    dialog._search.emit("search-changed")

    assert row_names(dialog) == ["tessedit_char_whitelist"]


def test_filter_is_case_insensitive() -> None:
    """Upper and lower case filter text match the same rows."""
    dialog = make_dialog()

    dialog._search.set_text("DPI")
    dialog._search.emit("search-changed")
    upper = row_names(dialog)

    dialog._search.set_text("dpi")
    dialog._search.emit("search-changed")

    assert row_names(dialog) == upper


def test_filter_without_a_match() -> None:
    """A filter that matches nothing says so instead of showing a blank table."""
    dialog = make_dialog()

    dialog._search.set_text("no such parameter")
    dialog._search.emit("search-changed")

    assert row_names(dialog) == []
    assert dialog._status.get_visible() is True
    assert dialog._status.get_text() == "No parameters match"


def test_managed_parameter_is_annotated_and_not_insertable() -> None:
    """A parameter owned by a control names it and cannot be inserted."""
    dialog = make_dialog()
    rows = {str(row[0]): row for row in dialog._list.data}
    description = str(rows["tessedit_pageseg_mode"][2])

    assert "Set by the Page segmentation mode control" in description
    assert (
        str(rows["tessedit_ocr_engine_mode"][2]) == "Set by the OCR engine mode control"
    )

    responses: list[int] = []
    dialog.connect("response", lambda _dialog, response: responses.append(response))
    index = row_names(dialog).index("tessedit_pageseg_mode")
    dialog._list.select([index])

    assert dialog._insert_button.get_sensitive() is False
    dialog._insert()
    assert dialog.selected_name is None

    dialog._on_row_activated(
        dialog._list,
        Gtk.TreePath.new_from_string(str(index)),
        dialog._list.get_column(0),
    )

    assert Gtk.ResponseType.OK not in responses
    assert dialog.selected_name is None


def test_escape_and_close_emit_a_close_response() -> None:
    """Escape and the window close action both let a waiting loop return."""
    dialog = make_dialog()
    responses: list[int] = []
    dialog.connect("response", lambda _dialog, response: responses.append(response))

    assert (
        dialog._on_key_pressed(
            Gtk.EventControllerKey(),
            Gdk.KEY_Escape,
            0,
            Gdk.ModifierType(0),
        )
        is True
    )
    assert (
        dialog._on_key_pressed(
            Gtk.EventControllerKey(),
            Gdk.KEY_a,
            0,
            Gdk.ModifierType(0),
        )
        is False
    )
    dialog._close()
    assert dialog._on_close_request(dialog) is True

    assert responses == [Gtk.ResponseType.CLOSE, Gtk.ResponseType.CLOSE]


def test_row_activation_returns_the_selected_name() -> None:
    """Enter or a double click on an insertable row settles the dialog on OK."""
    dialog = make_dialog()
    responses: list[int] = []
    dialog.connect("response", lambda _dialog, response: responses.append(response))
    index = row_names(dialog).index("user_defined_dpi")

    dialog._on_row_activated(
        dialog._list,
        Gtk.TreePath.new_from_string(str(index)),
        dialog._list.get_column(0),
    )

    assert responses == [Gtk.ResponseType.OK]
    assert dialog.selected_name == "user_defined_dpi"

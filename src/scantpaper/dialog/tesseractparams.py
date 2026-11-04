"""Browse the engine parameters the installed Tesseract reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi
from typing_extensions import override

from scantpaper.dialog import Dialog
from scantpaper.i18n import _
from scantpaper.simplelist import SimpleList

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from scantpaper.tesseract import TesseractParameter

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import (  # noqa: E402
    Gdk,
    Gtk,
    Pango,
)

# Keep the description readable without letting one long row widen the dialog
# beyond the screen.
_DESCRIPTION_WRAP_WIDTH = 420


class TesseractParametersDialog(Dialog):
    """List the Tesseract engine parameters and insert their names."""

    def __init__(
        self,
        *,
        parameters: Sequence[TesseractParameter] | None,
        managed: Mapping[str, str],
        transient_for: Gtk.Window | None = None,
    ) -> None:
        """Initialise the parameter browser."""
        super().__init__(
            title=_("Tesseract parameters"),
            transient_for=transient_for,
            modal=True,
        )
        self._parameters = parameters
        self._managed = managed
        self.selected_name: str | None = None

        content = self.get_content_area()

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(_("Filter parameters"))
        self._search.set_sensitive(parameters is not None)
        self._search.connect("search-changed", self._on_search_changed)
        content.append(self._search)

        self._status = Gtk.Label()
        self._status.set_wrap(True)
        self._status.set_xalign(0.0)
        self._status.set_visible(False)
        content.append(self._status)

        self._list = SimpleList(
            **{
                _("Name"): "text",
                _("Default"): "text",
                _("Description"): "text",
            }
        )
        self._list.set_vexpand(True)
        self._list.get_selection().connect("changed", self._on_selection_changed)
        self._list.connect("row-activated", self._on_row_activated)
        self._name_column = cast("Gtk.TreeViewColumn", self._list.get_column(0))
        for cell in self._name_column.get_cells():
            cell.set_property("family", "monospace")
        description_column = cast("Gtk.TreeViewColumn", self._list.get_column(2))
        description_column.set_expand(True)
        description_column.set_resizable(True)
        for cell in description_column.get_cells():
            cell.set_property("wrap-mode", Pango.WrapMode.WORD_CHAR)
            cell.set_property("wrap-width", _DESCRIPTION_WRAP_WIDTH)

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._scrolled.set_min_content_height(260)
        self._scrolled.set_vexpand(True)
        self._scrolled.set_hexpand(True)
        self._scrolled.set_child(self._list)
        content.append(self._scrolled)

        buttons = self.add_actions(
            [(_("_Insert"), self._insert), (_("_Close"), self._close)]
        )
        self._insert_button = buttons[0]
        self._insert_button.set_sensitive(False)

        self.set_default_size(720, 420)
        self.connect("map", self._on_map)

        if parameters is None:
            self._search.set_sensitive(False)
            self._list.set_visible(False)
            self._scrolled.set_visible(False)
            self._status.set_text(
                _(
                    "The Tesseract parameter list is unavailable. OCR can still "
                    "run with the parameters already entered."
                )
            )
            self._status.set_visible(True)
        else:
            self._populate("")

    def _on_map(self, _widget: Gtk.Widget) -> None:
        """Give the filter entry the keyboard focus when the dialog opens."""
        self._search.grab_focus()

    def _description(self, parameter: TesseractParameter) -> str:
        """Return the description, annotated when a control owns the name."""
        control = self._managed.get(parameter.name)
        if control is None:
            return parameter.description
        note = _("Set by the %(control)s control") % {"control": control}
        if parameter.description:
            return f"{parameter.description} {note}"
        return note

    def _populate(self, text: str) -> None:
        """Repopulate the list from the cached parameters, sorted by name."""
        if self._parameters is None:
            return
        needle = text.casefold()
        rows = [
            [parameter.name, parameter.default, self._description(parameter)]
            for parameter in self._parameters
            if needle
            in f"{parameter.name} {parameter.default} {parameter.description}".casefold()
        ]
        rows.sort(key=lambda row: cast("str", row[0]).casefold())
        self._list.data.clear()
        self._list.data.extend(rows)
        self._insert_button.set_sensitive(False)
        self._status.set_text(_("No parameters match"))
        self._status.set_visible(not rows)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Refilter the list when the search text changes."""
        self._populate(entry.get_text())

    def _selected_name(self) -> str | None:
        """Return the name of the selected row, if any."""
        indices = self._list.get_selected_indices()
        if not indices:
            return None
        return cast("str", self._list.data[indices[0]][0])

    def _is_insertable(self, name: str | None) -> bool:
        """Return whether a name may be written into the advanced field."""
        return name is not None and name not in self._managed

    def _on_selection_changed(self, _selection: Gtk.TreeSelection) -> None:
        """Enable Insert only for an insertable selection."""
        self._insert_button.set_sensitive(self._is_insertable(self._selected_name()))

    def _on_row_activated(
        self,
        _list: Gtk.TreeView,
        path: Gtk.TreePath,
        _column: Gtk.TreeViewColumn,
    ) -> None:
        """Insert the activated row, as Enter or a double click does."""
        self._list.select([path.get_indices()[0]])
        if self._is_insertable(self._selected_name()):
            self.response(Gtk.ResponseType.OK)

    def _insert(self) -> None:
        """Record the selected name; the response has already been emitted."""
        name = self._selected_name()
        if self._is_insertable(name):
            self.selected_name = name

    def _close(self) -> None:
        """Close without inserting."""

    @override
    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        """Close on Escape via a response so a waiting loop returns."""
        if keyval == Gdk.KEY_Escape:
            self.response(Gtk.ResponseType.CLOSE)
            return True
        return False

    @override
    def _on_close_request(self, _widget: Gtk.Widget) -> bool:
        """Close via a response so a waiting loop returns."""
        self.response(Gtk.ResponseType.CLOSE)
        return True

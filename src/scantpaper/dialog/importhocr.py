"""Dialog for importing an hOCR text layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

from scantpaper.const import DIALOG_ROW_SPACING
from scantpaper.dialog import Dialog
from scantpaper.helpers import add_filter, chooser_path, run_dialog
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gio,
    Gtk,
)


class ImportHocrDialog(Dialog):
    """Choose an hOCR file and the pages to import it into."""

    def __init__(
        self,
        *args: object,
        page_range: str = "selected",
        cwd: str = "",
        on_accept: Callable[[str, str], None] | None = None,
        **kwargs: object,
    ) -> None:
        """Initialise the import dialog."""
        super().__init__(*args, **kwargs)
        self._cwd = cwd
        self._path = ""
        self._on_accept = on_accept
        self.page_range = page_range

        vbox = self.get_content_area()
        hbox = Gtk.Box(spacing=DIALOG_ROW_SPACING)
        vbox.append(hbox)
        hbox.append(Gtk.Label(label=_("hOCR file")))
        self._entry = Gtk.Entry()
        self._entry.set_editable(False)
        self._entry.set_hexpand(True)
        hbox.append(self._entry)
        button = Gtk.Button(label=_("Browse"))
        button.connect("clicked", self._choose_file)
        hbox.append(button)

        self.add_page_range()

        note = Gtk.Label(label=_("Pages are matched to the hOCR pages in order."))
        note.set_wrap(True)
        note.set_xalign(0.0)
        vbox.append(note)

        self._ok = self.add_actions(
            [(_("_OK"), self._accept), (_("_Cancel"), self.hide)]
        )[0]
        self._ok.set_sensitive(False)

    def _choose_file(self, _button: Gtk.Button) -> None:
        """Choose the hOCR file to import."""
        chooser = Gtk.FileChooserDialog(
            title=_("Open hOCR file"),
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_buttons(
            _("Cancel"),
            Gtk.ResponseType.CANCEL,
            _("Open"),
            Gtk.ResponseType.OK,
        )
        add_filter(chooser, _("hOCR files"), ["hocr", "html", "htm"])
        if self._cwd:
            chooser.set_current_folder(Gio.File.new_for_path(self._cwd))
        if run_dialog(chooser) == Gtk.ResponseType.OK:
            self._path = chooser_path(chooser)
            self._entry.set_text(self._path)
            self._ok.set_sensitive(True)
        chooser.destroy()

    def _accept(self) -> None:
        """Pass the chosen file and page range to the caller."""
        if not self._path:
            return
        if self._on_accept is not None:
            self._on_accept(self._path, self.page_range)
        self.hide()

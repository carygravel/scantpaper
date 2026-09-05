"""provide controls for editing the text layer."""

import logging
from typing import ClassVar

import gi
from comboboxtext import ComboBoxText
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)

INDEX = [
    [
        "confidence",
        _("Sort by confidence"),
        _("Sort OCR text boxes by confidence."),
    ],
    ["position", _("Sort by position"), _("Sort OCR text boxes by position.")],
]


class TextLayerControls(Gtk.Box):
    """provide controls for editing the text layer."""

    __gsignals__: ClassVar[dict] = {
        "text-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "bbox-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "sort-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "go-to-first": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-previous": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-next": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-last": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "ok-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "copy-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "add-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "delete-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, *args, **kwargs):
        """Initialise the text layer control with navigation and editing buttons."""
        super().__init__(*args, **kwargs)
        textview = Gtk.TextView()
        textview.set_tooltip_text(_("Text layer"))
        self._textbuffer = textview.get_buffer()

        fbutton = self._make_icon_button(
            "go-first", _("Go to least confident text"), "go-to-first"
        )
        pbutton = self._make_icon_button(
            "go-previous", _("Go to previous text"), "go-to-previous"
        )
        sort_cmbx = ComboBoxText(data=INDEX)
        sort_cmbx.set_tooltip_text(_("Select sort method for OCR boxes"))
        sort_cmbx.connect(
            "changed",
            lambda _: self.emit("sort-changed", INDEX[sort_cmbx.get_active()][0]),
        )
        sort_cmbx.set_active(0)
        nbutton = self._make_icon_button("go-next", _("Go to next text"), "go-to-next")
        lbutton = self._make_icon_button(
            "go-last", _("Go to most confident text"), "go-to-last"
        )
        abutton = self._make_icon_button("list-add", _("Add text"), "add-clicked")

        obutton = self._make_mnemonic_button(
            _("_OK"), _("Accept corrections"), "ok-clicked"
        )
        cbutton = self._make_mnemonic_button(
            _("_Cancel"), _("Cancel corrections"), close=True
        )
        ubutton = self._make_mnemonic_button(
            _("_Copy"), _("Duplicate text"), "copy-clicked"
        )
        dbutton = self._make_mnemonic_button(
            _("_Delete"), _("Delete text"), "delete-clicked"
        )

        self.pack_start(fbutton, expand=False, fill=False, padding=0)
        self.pack_start(pbutton, expand=False, fill=False, padding=0)
        self.pack_start(sort_cmbx, expand=False, fill=False, padding=0)
        self.pack_start(nbutton, expand=False, fill=False, padding=0)
        self.pack_start(lbutton, expand=False, fill=False, padding=0)
        self.pack_start(textview, expand=True, fill=True, padding=0)
        self.pack_end(dbutton, expand=False, fill=False, padding=0)
        self.pack_end(cbutton, expand=False, fill=False, padding=0)
        self.pack_end(obutton, expand=False, fill=False, padding=0)
        self.pack_end(ubutton, expand=False, fill=False, padding=0)
        self.pack_end(abutton, expand=False, fill=False, padding=0)

    def _make_icon_button(self, icon, tooltip, signal):
        """Build an icon button that emits the given signal."""
        button = Gtk.Button()
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _: self.emit(signal))
        return button

    def _make_mnemonic_button(self, label, tooltip, signal=None, *, close=False):
        """Build a mnemonic button that emits the given signal or closes."""
        button = Gtk.Button.new_with_mnemonic(label=label)
        button.set_tooltip_text(tooltip)
        if close:
            button.connect("clicked", lambda _: self.hide())
        else:
            button.connect("clicked", lambda _: self.emit(signal))
        return button

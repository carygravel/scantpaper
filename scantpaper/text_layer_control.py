"provide controls for editing the text layer"

import logging
import gi
from comboboxtext import ComboBoxText
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)

INDEX = [
    [
        "confidence",
        _("Sort by confidence"),
        _("Sort OCR text boxes by confidence."),
    ],
    ["position", _("Sort by position"), _("Sort OCR text boxes by position.")],
]


class TextLayerControls(Gtk.HBox):
    "provide controls for editing the text layer"

    __gsignals__ = {
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
        super().__init__(*args, **kwargs)
        textview = Gtk.TextView()
        textview.set_tooltip_text(_("Text layer"))
        self._textbuffer = textview.get_buffer()
        fbutton = Gtk.Button()
        fbutton.set_image(Gtk.Image.new_from_icon_name("go-first", Gtk.IconSize.BUTTON))
        fbutton.set_tooltip_text(_("Go to least confident text"))
        fbutton.connect("clicked", lambda _: self.emit("go-to-first"))
        pbutton = Gtk.Button()
        pbutton.set_image(
            Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
        )
        pbutton.set_tooltip_text(_("Go to previous text"))
        pbutton.connect("clicked", lambda _: self.emit("go-to-previous"))
        sort_cmbx = ComboBoxText(data=INDEX)
        sort_cmbx.set_tooltip_text(_("Select sort method for OCR boxes"))
        sort_cmbx.connect(
            "changed", lambda _: self.emit("sort-changed", sort_cmbx.get_active_text())
        )
        sort_cmbx.set_active(0)
        nbutton = Gtk.Button()
        nbutton.set_image(Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        nbutton.set_tooltip_text(_("Go to next text"))
        nbutton.connect("clicked", lambda _: self.emit("go-to-next"))
        lbutton = Gtk.Button()
        lbutton.set_image(Gtk.Image.new_from_icon_name("go-last", Gtk.IconSize.BUTTON))
        lbutton.set_tooltip_text(_("Go to most confident text"))
        lbutton.connect("clicked", lambda _: self.emit("go-to-last"))
        obutton = Gtk.Button.new_with_mnemonic(label=_("_OK"))
        obutton.set_tooltip_text(_("Accept corrections"))
        obutton.connect("clicked", lambda _: self.emit("ok-clicked"))
        cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        cbutton.set_tooltip_text(_("Cancel corrections"))
        cbutton.connect("clicked", lambda _: self.hide())
        ubutton = Gtk.Button.new_with_mnemonic(label=_("_Copy"))
        ubutton.set_tooltip_text(_("Duplicate text"))
        ubutton.connect("clicked", lambda _: self.emit("copy-clicked"))
        abutton = Gtk.Button()
        abutton.set_image(Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
        abutton.set_tooltip_text(_("Add text"))
        abutton.connect("clicked", lambda _: self.emit("add-clicked"))
        dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        dbutton.set_tooltip_text(_("Delete text"))
        dbutton.connect("clicked", lambda _: self.emit("delete-clicked"))
        self.pack_start(fbutton, False, False, 0)
        self.pack_start(pbutton, False, False, 0)
        self.pack_start(sort_cmbx, False, False, 0)
        self.pack_start(nbutton, False, False, 0)
        self.pack_start(lbutton, False, False, 0)
        self.pack_start(textview, True, True, 0)
        self.pack_end(dbutton, False, False, 0)
        self.pack_end(cbutton, False, False, 0)
        self.pack_end(obutton, False, False, 0)
        self.pack_end(ubutton, False, False, 0)
        self.pack_end(abutton, False, False, 0)

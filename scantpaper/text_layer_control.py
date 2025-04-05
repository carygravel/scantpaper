"provide controls for editing the text layer"

import logging
import gi
from comboboxtext import ComboBoxText
from const import EMPTY, ZOOM_CONTEXT_FACTOR
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
        self.pack_start(textview, False, False, 0)
        self.pack_end(dbutton, False, False, 0)
        self.pack_end(cbutton, False, False, 0)
        self.pack_end(obutton, False, False, 0)
        self.pack_end(ubutton, False, False, 0)
        self.pack_end(abutton, False, False, 0)


class TextLayerMixins:
    "provide methods for editing the text layer"

    def _add_text_view_layers(self):
        # split panes for detail view/text layer canvas and text layer dialog
        self._ocr_text_hbox = TextLayerControls()
        self.builder.get_object("edit_hbox").pack_start(
            self._ocr_text_hbox, False, False, 0
        )
        self._ocr_text_hbox.connect(
            "go-to-first", lambda _: self._edit_ocr_text(self.t_canvas.get_first_bbox())
        )
        self._ocr_text_hbox.connect(
            "go-to-previous",
            lambda _: self._edit_ocr_text(self.t_canvas.get_previous_bbox()),
        )
        self._ocr_text_hbox.connect("sort-changed", self._changed_text_sort_method)
        self._ocr_text_hbox.connect(
            "go-to-next", lambda _: self._edit_ocr_text(self.t_canvas.get_next_bbox())
        )
        self._ocr_text_hbox.connect(
            "go-to-last", lambda _: self._edit_ocr_text(self.t_canvas.get_last_bbox())
        )
        self._ocr_text_hbox.connect("ok-clicked", self._ocr_text_button_clicked)
        self._ocr_text_hbox.connect("copy-clicked", self._ocr_text_copy)
        self._ocr_text_hbox.connect("add-clicked", self._ocr_text_add)
        self._ocr_text_hbox.connect("delete-clicked", self._ocr_text_delete)

        # split panes for detail view/text layer canvas and text layer dialog
        self._ann_hbox = self.builder.get_object("ann_hbox")
        ann_textview = Gtk.TextView()
        ann_textview.set_tooltip_text(_("Annotations"))
        self._ann_textbuffer = ann_textview.get_buffer()
        ann_obutton = Gtk.Button.new_with_mnemonic(label=_("_Ok"))
        ann_obutton.set_tooltip_text(_("Accept corrections"))
        ann_obutton.connect("clicked", self._ann_text_ok)
        ann_cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        ann_cbutton.set_tooltip_text(_("Cancel corrections"))
        ann_cbutton.connect("clicked", self._ann_hbox.hide)
        ann_abutton = Gtk.Button()
        ann_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        )
        ann_abutton.set_tooltip_text(_("Add annotation"))
        ann_abutton.connect("clicked", self._ann_text_new)
        ann_dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        ann_dbutton.set_tooltip_text(_("Delete annotation"))
        ann_dbutton.connect("clicked", self._ann_text_delete)
        self._ann_hbox.pack_start(ann_textview, False, False, 0)
        self._ann_hbox.pack_end(ann_dbutton, False, False, 0)
        self._ann_hbox.pack_end(ann_cbutton, False, False, 0)
        self._ann_hbox.pack_end(ann_obutton, False, False, 0)
        self._ann_hbox.pack_end(ann_abutton, False, False, 0)
        self._pack_viewer_tools()

    def _text_zoom_changed_callback(self, canvas, _zoom):
        self.view.handler_block(self.view.zoom_changed_signal)
        self.view.set_zoom(canvas.get_scale())
        self.view.handler_unblock(self.view.zoom_changed_signal)

    def _text_offset_changed_callback(self):
        self.view.handler_block(self.view.offset_changed_signal)
        offset = self.t_canvas.get_offset()
        self.view.set_offset(offset["x"], offset["y"])
        self.view.handler_unblock(self.view.offset_changed_signal)

    def _ann_zoom_changed_callback(self):
        self.view.handler_block(self.view.zoom_changed_signal)
        self.view.set_zoom(self.a_canvas.get_scale())
        self.view.handler_unblock(self.view.zoom_changed_signal)

    def _ann_offset_changed_callback(self):
        self.view.handler_block(self.view.offset_changed_signal)
        offset = self.a_canvas.get_offset()
        self.view.set_offset(offset["x"], offset["y"])
        self.view.handler_unblock(self.view.offset_changed_signal)

    def _ocr_text_button_clicked(self, _widget):
        self._take_snapshot()
        text = self._ocr_textbuffer.get_text(
            self._ocr_textbuffer.get_start_iter(),
            self._ocr_textbuffer.get_end_iter(),
            False,
        )
        logger.info("Corrected '%s'->'%s'", self._current_ocr_bbox.text, text)
        self._current_ocr_bbox.update_box(text, self.view.get_selection())
        self._current_page.import_hocr(self.t_canvas.hocr())
        self._edit_ocr_text(self._current_ocr_bbox)

    def _ocr_text_copy(self, _widget):
        self._current_ocr_bbox = self.t_canvas.add_box(
            text=self._ocr_textbuffer.get_text(
                self._ocr_textbuffer.get_start_iter(),
                self._ocr_textbuffer.get_end_iter(),
                False,
            ),
            bbox=self.view.get_selection(),
        )
        self._current_page.import_hocr(self.t_canvas.hocr())
        self._edit_ocr_text(self._current_ocr_bbox)

    def _ocr_text_add(self, _widget):
        self._take_snapshot()
        text = self._ocr_textbuffer.get_text(
            self._ocr_textbuffer.get_start_iter(),
            self._ocr_textbuffer.get_end_iter(),
            False,
        )
        if text is None or text == EMPTY:
            text = _("my-new-word")

        # If we don't yet have a canvas, create one
        selection = self.view.get_selection()
        if hasattr(self._current_page, "text_layer"):
            logger.info("Added '%s'", text)
            self._current_ocr_bbox = self.t_canvas.add_box(
                text=text, bbox=self.view.get_selection()
            )
            self._current_page.import_hocr(self.t_canvas.hocr())
            self._edit_ocr_text(self._current_ocr_bbox)
        else:
            logger.info("Creating new text layer with '%s'", text)
            self._current_page.text_layer = (
                '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},'
                '{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]'
                % (
                    self._current_page["width"],
                    self._current_page["height"],
                    selection["x"],
                    selection["y"],
                    selection["x"] + selection["width"],
                    selection["y"] + selection["height"],
                    text,
                )
            )

            def ocr_new_page(_widget):
                self._current_ocr_bbox = self.t_canvas.get_first_bbox()
                self._edit_ocr_text(self._current_ocr_bbox)

            self._create_txt_canvas(self._current_page, ocr_new_page)

    def _ocr_text_delete(self, _widget):
        self._current_ocr_bbox.delete_box()
        self._current_page.import_hocr(self.t_canvas.hocr())
        self._edit_ocr_text(self.t_canvas.get_current_bbox())

    def _ann_text_ok(self, _widget):
        text = self._ann_textbuffer.get_text(
            self._ann_textbuffer.get_start_iter(),
            self._ann_textbuffer.get_end_iter(),
            False,
        )
        logger.info("Corrected '%s'->'%s'", self._current_ann_bbox.text, text)
        self._current_ann_bbox.update_box(text, self.view.get_selection())
        self._current_page.import_annotations(self.a_canvas.hocr())
        self._edit_annotation(self._current_ann_bbox)

    def _ann_text_new(self, _widget):
        text = self._ann_textbuffer.get_text(
            self._ann_textbuffer.get_start_iter(),
            self._ann_textbuffer.get_end_iter(),
            False,
        )
        if text is None or text == EMPTY:
            text = _("my-new-annotation")

        # If we don't yet have a canvas, create one
        selection = self.view.get_selection()
        if hasattr(self._current_page, "text_layer"):
            logger.info("Added '%s'", text)
            self._current_ann_bbox = self.a_canvas.add_box(
                text=text, bbox=self.view.get_selection()
            )
            self._current_page.import_annotations(self.a_canvas.hocr())
            self._edit_annotation(self._current_ann_bbox)
        else:
            logger.info("Creating new annotation canvas with '%s'", text)
            self._current_page["annotations"] = (
                '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},'
                '{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]'
                % (
                    self._current_page["width"],
                    self._current_page["height"],
                    selection["x"],
                    selection["y"],
                    selection["x"] + selection["width"],
                    selection["y"] + selection["height"],
                    text,
                )
            )

            def ann_text_new_page(_widget):
                self._current_ann_bbox = self.a_canvas.get_first_bbox()
                self._edit_annotation(self._current_ann_bbox)

            self._create_ann_canvas(self._current_page, ann_text_new_page)

    def _ann_text_delete(self, _widget):
        self._current_ann_bbox.delete_box()
        self._current_page.import_hocr(self.a_canvas.hocr())
        self._edit_annotation(self.t_canvas.get_current_bbox())

    def _edit_mode_callback(self, action, parameter):
        "Show/hide the edit tools"
        action.set_state(parameter)
        if parameter.get_string() == "text":
            self._ocr_text_hbox.show()
            self._ann_hbox.hide()
            return
        self._ocr_text_hbox.hide()
        self._ann_hbox.show()

    def _edit_ocr_text(self, widget, _target=None, ev=None, bbox=None):
        "Edit OCR text"
        logger.debug("edit_ocr_text(%s, %s, %s, %s)", widget, _target, ev, bbox)
        if not ev:
            bbox = widget

        if bbox is None:
            return

        self._current_ocr_bbox = bbox
        self._ocr_textbuffer.set_text(bbox.text)
        self._ocr_text_hbox.show_all()
        self.view.set_selection(bbox.bbox)
        self.view.setzoom_is_fit(False)
        self.view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            self.t_canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            self.t_canvas.set_index_by_bbox(bbox)

    def _edit_annotation(self, widget, _target=None, ev=None, bbox=None):
        "Edit annotation"
        if not ev:
            bbox = widget

        self._current_ann_bbox = bbox
        self._ann_textbuffer.set_text(bbox.text)
        self._ann_hbox.show_all()
        self.view.set_selection(bbox.bbox)
        self.view.setzoom_is_fit(False)
        self.view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            self.a_canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            self.a_canvas.set_index_by_bbox(bbox)

    def _create_txt_canvas(self, page, finished_callback=None):
        "Create the text canvas"
        offset = self.view.get_offset()
        self.t_canvas.set_text(
            page=page,
            layer="text_layer",
            edit_callback=self._edit_ocr_text,
            idle=True,
            finished_callback=finished_callback,
        )
        self.t_canvas.set_scale(self.view.get_zoom())
        self.t_canvas.set_offset(offset.x, offset.y)
        self.t_canvas.show()

    def _create_ann_canvas(self, page, finished_callback=None):
        "Create the annotation canvas"
        offset = self.view.get_offset()
        self.a_canvas.set_text(
            page=page,
            layer="annotations",
            edit_callback=self._edit_annotation,
            idle=True,
            finished_callback=finished_callback,
        )
        self.a_canvas.set_scale(self.view.get_zoom())
        self.a_canvas.set_offset(offset.x, offset.y)
        self.a_canvas.show()

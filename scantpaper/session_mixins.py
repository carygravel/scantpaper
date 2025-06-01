"provide methods around session files"

import fcntl
import glob
import logging
import os
import re
import shutil
import tempfile
import gi
import tesserocr
from bboxtree import Bboxtree
from const import (
    EMPTY,
    SPACE,
    ZOOM_CONTEXT_FACTOR,
    DRAGGER_TOOL,
    SELECTOR_TOOL,
    SELECTORDRAGGER_TOOL,
)
from dialog import filter_message, response_stored
from helpers import get_tmp_dir, program_version, exec_command, parse_truetype_fonts
from i18n import _
from simplelist import SimpleList
from text_layer_control import TextLayerControls
from unpaper import Unpaper

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


class SessionMixins:
    "provide methods around session files"

    # pylint: disable=too-many-instance-attributes

    def _create_temp_directory(self):
        "Create a temporary directory for the session"
        tmpdir = get_tmp_dir(self.settings["TMPDIR"], r"gscan2pdf-\w\w\w\w")
        self._find_crashed_sessions(tmpdir)

        # Create temporary directory if necessary
        if self.session is None:
            if tmpdir is not None and tmpdir != EMPTY:
                if not os.path.isdir(tmpdir):
                    os.mkdir(tmpdir)
                try:
                    self.session = tempfile.TemporaryDirectory(
                        prefix="gscan2pdf-", dir=tmpdir
                    )
                except (FileNotFoundError, PermissionError) as e:
                    logger.error("Error creating temporary directory: %s", e)
                    self.session = tempfile.TemporaryDirectory(prefix="gscan2pdf-")
            else:
                self.session = (
                    tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
                        prefix="gscan2pdf-"
                    )
                )

            self._lockfd = self._create_lockfile()
            logger.info("Using %s for temporary files", self.session.name)
            tmpdir = os.path.dirname(self.session.name)
            if "TMPDIR" in self.settings and self.settings["TMPDIR"] != tmpdir:
                logger.warning(
                    _(
                        "Warning: unable to use %s for temporary storage. Defaulting to %s instead."
                    ),
                    self.settings["TMPDIR"],
                    tmpdir,
                )
                self.settings["TMPDIR"] = tmpdir

    def _create_lockfile(self):
        "create a lockfile in the session directory"
        lockfd = open(  # pylint: disable=consider-using-with
            os.path.join(self.session.name, "lockfile"), "w", encoding="utf-8"
        )
        fcntl.lockf(lockfd, fcntl.LOCK_EX)
        return lockfd

    def _find_crashed_sessions(self, tmpdir):
        "Look for crashed sessions"
        if tmpdir is None or tmpdir == EMPTY:
            tmpdir = tempfile.gettempdir()

        logger.info("Checking %s for crashed sessions", tmpdir)
        sessions = glob.glob(os.path.join(tmpdir, "gscan2pdf-????"))
        crashed, selected = [], []

        # Forget those used by running sessions
        for session in sessions:
            try:
                self._create_lockfile()
                crashed.append(session)
            except (OSError, IOError) as e:
                logger.warning("Error opening lockfile %s", str(e))

        # Flag those with no session file
        missing = []
        for i, session in enumerate(crashed):
            if not os.access(os.path.join(session, "session"), os.R_OK):
                missing.append(session)
                del crashed[i]

        if missing:
            self._list_unrestorable_sessions(missing)

        # Allow user to pick a crashed session to restore
        if crashed:
            dialog = Gtk.Dialog(
                title=_("Pick crashed session to restore"),
                transient_for=self,
                modal=True,
            )
            dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            label = Gtk.Label(label=_("Pick crashed session to restore"))
            box = dialog.get_content_area()
            box.add(label)
            columns = {_("Session"): "text"}
            sessionlist = SimpleList(**columns)
            sessionlist.data.append(crashed)
            box.add(sessionlist)
            dialog.show_all()
            if dialog.run() == Gtk.ResponseType.OK:
                selected = sessionlist.get_selected_indices()

            dialog.destroy()
            if selected is not None:
                self.session = crashed[selected]
                self._create_lockfile()
                self._open_session(self.session)

    def _list_unrestorable_sessions(self, missing):
        logger.info("Unrestorable sessions: %s", SPACE.join(missing))
        dialog = Gtk.Dialog(
            title=_("Crashed sessions"),
            transient_for=self,
            modal=True,
        )
        dialog.add_buttons(
            Gtk.STOCK_DELETE,
            Gtk.ResponseType.OK,
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
        )
        text = Gtk.TextView()
        text.set_wrap_mode("word")
        text.get_buffer().set_text(
            _("The following list of sessions cannot be restored.")
            + SPACE
            + _("Please retrieve any images you require from them.")
            + SPACE
            + _("Selected sessions will be deleted.")
        )
        dialog.get_content_area().add(text)
        columns = {_("Session"): "text"}
        sessionlist = SimpleList(**columns)
        sessionlist.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        sessionlist.data.append(missing)
        dialog.get_content_area().add(sessionlist)
        button = dialog.get_action_area().get_children()

        def changed_selection_callback():
            button.set_sensitive(len(sessionlist.get_selected_indices()) > 0)

        sessionlist.get_selection().connect("changed", changed_selection_callback)
        sessionlist.get_selection().select_all()
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            selected = sessionlist.get_selected_indices()
            for i, _v in enumerate(selected):
                selected[i] = missing[i]
            logger.info("Selected for deletion: %s", SPACE.join(selected))
            if selected:
                shutil.rmtree(selected)
        else:
            logger.info("None selected")

        dialog.destroy()

    def _take_snapshot(self):
        "Update undo/redo buffers before doing something"
        self.slist.take_snapshot()

        # Unghost Undo/redo
        self._actions["undo"].set_enabled(True)

        # Check free space in session directory
        df = shutil.disk_usage(self.session.name)
        if df:
            df = df.free / 1024 / 1024
            logger.debug(
                "Free space in %s (Mb): %s (warning at %s)",
                self.session.name,
                df,
                self.settings["available-tmp-warning"],
            )
            if df < self.settings["available-tmp-warning"]:
                text = _("%dMb free in %s.") % (df, self.session.name)
                self._show_message_dialog(
                    parent=self,
                    message_type="warning",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=text,
                )

    def _check_dependencies(self):
        "Check for presence of various packages"

        self._dependencies["tesseract"] = tesserocr.tesseract_version()
        self._dependencies["tesserocr"] = tesserocr.__version__
        if self._dependencies["tesseract"]:
            logger.info(
                "Found tesserocr %s, %s",
                self._dependencies["tesserocr"],
                self._dependencies["tesseract"],
            )
        self._dependencies["unpaper"] = Unpaper().program_version()
        if self._dependencies["unpaper"]:
            logger.info("Found unpaper %s", self._dependencies["unpaper"])

        dependency_rules = [
            [
                "imagemagick",
                "stdout",
                r"Version:\sImageMagick\s([\d.-]+)",
                ["convert", "--version"],
            ],
            [
                "graphicsmagick",
                "stdout",
                r"GraphicsMagick\s([\d.-]+)",
                ["gm", "-version"],
            ],
            ["xdg", "stdout", r"xdg-email\s([^\n]+)", ["xdg-email", "--version"]],
            ["djvu", "stderr", r"DjVuLibre-([\d.]+)", ["cjb2", "--version"]],
            ["libtiff", "both", r"LIBTIFF,\sVersion\s([\d.]+)", ["tiffcp", "-h"]],
            # pdftops and pdfunite are both in poppler-utils, and so the version is
            # the version is the same.
            # Both are needed, though to update %dependencies
            ["pdftops", "stderr", r"pdftops\sversion\s([\d.]+)", ["pdftops", "-v"]],
            ["pdfunite", "stderr", r"pdfunite\sversion\s([\d.]+)", ["pdfunite", "-v"]],
            ["pdf2ps", "stdout", r"([\d.]+)", ["gs", "--version"]],
            ["pdftk", "stdout", r"([\d.]+)", ["pdftk", "--version"]],
            ["xz", "stdout", r"([\d.]+)", ["xz", "--version"]],
        ]

        for name, stream, regex, cmd in dependency_rules:
            self._dependencies[name] = program_version(stream, regex, cmd)
            if self._dependencies[name] and self._dependencies[name] == "-1":
                del self._dependencies[name]

            if (
                not self._dependencies["imagemagick"]
                and self._dependencies["graphicsmagick"]
            ):
                msg = (
                    _("GraphicsMagick is being used in ImageMagick compatibility mode.")
                    + SPACE
                    + _("Whilst this might work, it is not currently supported.")
                    + SPACE
                    + _("Please switch to ImageMagick in case of problems.")
                )
                self._show_message_dialog(
                    parent=self,
                    message_type="warning",
                    buttons=Gtk.ButtonsType.OK,
                    text=msg,
                    store_response=True,
                )
                self._dependencies["imagemagick"] = self._dependencies["graphicsmagick"]

            if self._dependencies[name]:
                logger.info("Found %s %s", name, self._dependencies[name])
                if name == "pdftk":

                    # Don't create PDF  directly with imagemagick, as
                    # some distros configure imagemagick not to write PDFs
                    with tempfile.NamedTemporaryFile(
                        dir=self.session.name, suffix=".jpg"
                    ) as tempimg:
                        exec_command(["convert", "rose:", tempimg.name])
                    with tempfile.NamedTemporaryFile(
                        dir=self.session.name, suffix=".pdf"
                    ) as temppdf:
                        # pdfobj = PDF.Builder( -file = temppdf )
                        # page   = pdfobj.page()
                        # size   = Gscan2pdf.Document.POINTS_PER_INCH
                        # page.mediabox( size, size )
                        # gfx    = page.gfx()
                        # imgobj = pdfobj.image_jpeg(tempimg)
                        # gfx.image( imgobj, 0, 0, size, size )
                        # pdfobj.save()
                        # pdfobj.end()
                        proc = exec_command([name, temppdf.name, "dump_data"])
                    msg = None
                    if re.search(
                        r"Error:[ ]could[ ]not[ ]load[ ]a[ ]required[ ]library",
                        proc.stdout,
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        msg = _(
                            "pdftk is installed, but seems to be missing required dependencies:\n%s"
                        ) % (proc.stdout)

                    # elif not re.search(
                    #     r"NumberOfPages",
                    #     proc.stdout,
                    #     re.MULTILINE | re.DOTALL | re.VERBOSE,
                    # ):
                    #     logger.debug(f"before msg {_}")
                    #     msg = (
                    #         _(
                    #             "pdftk is installed, but cannot access the "
                    #             "directory used for temporary files."
                    #         )
                    #         + _(
                    #             "One reason for this might be that pdftk was installed via snap."
                    #         )
                    #         + _(
                    #             "In this case, removing pdftk, and reinstalling without using "
                    #             "snap would allow gscan2pdf to use pdftk."
                    #         )
                    #         + _(
                    #             "Another workaround would be to select a temporary directory "
                    #             "under your home directory in Edit/Preferences."
                    #         )
                    #     )

                    if msg:
                        del self._dependencies[name]
                        self._show_message_dialog(
                            parent=self,
                            message_type="warning",
                            buttons=Gtk.ButtonsType.OK,
                            text=msg,
                            store_response=True,
                        )

        # OCR engine options
        if self._dependencies["tesseract"]:
            self._ocr_engine.append(
                ["tesseract", _("Tesseract"), _("Process image with Tesseract.")]
            )

        # Build a look-up table of all true-type fonts installed
        proc = exec_command(["fc-list", ":", "family", "style", "file"])
        self._fonts = parse_truetype_fonts(proc.stdout)

    def _finished_process_callback(self, widget, process, button_signal=None):
        "Callback function to handle the completion of a process."
        logger.debug("signal 'finished-process' emitted with data: %s", process)
        if button_signal is not None:
            self._scan_progress.disconnect(button_signal)

        self._scan_progress.hide()
        if process == "scan_pages" and widget.sided == "double":

            def prompt_reverse_sides():
                message, side = None, None
                if widget.side_to_scan == "facing":
                    message = _("Finished scanning facing pages. Scan reverse pages?")
                    side = "reverse"
                else:
                    message = _("Finished scanning reverse pages. Scan facing pages?")
                    side = "facing"

                response = self._ask_question(
                    parent=widget,
                    type="question",
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=message,
                    default_response=Gtk.ResponseType.OK,
                    store_response=True,
                    stored_responses=[Gtk.ResponseType.OK],
                )
                if response == Gtk.ResponseType.OK:
                    widget.side_to_scan = side

            GLib.idle_add(prompt_reverse_sides)

    def _display_callback(self, response):
        "Find the page from the input uuid and display it"
        if response.info and "row" in response.info:
            uuid = response.info["row"][2]
            i = self.slist.find_page_by_uuid(uuid)
            if i is None:
                logger.error("Can't display page with uuid %s: page not found", uuid)
            else:
                self._display_image(self.slist.data[i][2])

    def _display_image(self, pageid):
        "Display the image in the view"
        self._current_page = self.slist.thread.get_page(id=pageid)
        self.view.set_pixbuf(self._current_page.get_pixbuf(), True)
        xresolution, yresolution, _units = self._current_page.resolution
        self.view.set_resolution_ratio(xresolution / yresolution)

        # Get image dimensions to constrain selector spinbuttons on crop dialog
        width, height = self._current_page.get_size()

        # Update the ranges on the crop dialog
        if self._windowc is not None and self._current_page is not None:
            self._windowc.page_width = width
            self._windowc.page_height = height
            self.settings["selection"] = self._windowc.selection
            self.view.set_selection(self.settings["selection"])

        # Delete OCR output if it has become corrupted
        if self._current_page.text_layer is not None:
            bbox = Bboxtree(self._current_page.text_layer)
            if not bbox.valid():
                logger.error(
                    "deleting corrupt text layer: %s", self._current_page.text_layer
                )
                self._current_page.text_layer = None

        if self._current_page.text_layer:
            self._create_txt_canvas(self._current_page)
        else:
            self.t_canvas.clear_text()

        if self._current_page.annotations:
            self._create_ann_canvas(self._current_page)
        else:
            self.a_canvas.clear_text()

    def _error_callback(self, response):
        "Handle errors"
        args = response.request.args
        process = response.request.process
        stage = response.type.name.lower()
        message = response.status
        page = None
        if "page" in args[0]:
            page = self.slist.data[self.slist.find_page_by_uuid(args[0]["page"].uuid)][
                0
            ]

        kwargs = {
            "parent": self,
            "message_type": "error",
            "buttons": Gtk.ButtonsType.CLOSE,
            "process": process,
            "text": message,
            "store-response": True,
            "page": page,
        }

        logger.error(
            "Error running '%s' callback for '%s' process: %s", stage, process, message
        )

        def show_message_dialog_wrapper():
            """Wrap show_message_dialog() in GLib.idle_add() to allow the thread to
            return immediately in order to allow it to work on subsequent pages
            despite errors on previous ones"""
            self._show_message_dialog(**kwargs)

        GLib.idle_add(show_message_dialog_wrapper)
        self.post_process_progress.hide()

    def _ask_question(self, **kwargs):
        "Helper function to display a message dialog, wait for a response, and return it"

        # replace any numbers with metacharacters to compare to filter
        text = filter_message(kwargs["text"])
        if response_stored(text, self.settings["message"]):
            logger.debug(
                f"Skipped MessageDialog with '{kwargs['text']}', "
                + f"automatically replying '{self.settings['message'][text]['response']}'"
            )
            return self.settings["message"][text]["response"]

        cb = None
        dialog = Gtk.MessageDialog(
            parent=kwargs["parent"],
            modal=True,
            destroy_with_parent=True,
            message_type=kwargs["type"],
            buttons=kwargs["buttons"],
            text=kwargs["text"],
        )
        logger.debug("Displayed MessageDialog with '%s'", kwargs["text"])
        if "store-response" in kwargs:
            cb = Gtk.CheckButton.new_with_label(_("Don't show this message again"))
            dialog.get_message_area().add(cb)

        if "default-response" in kwargs:
            dialog.set_default_response(kwargs["default-response"])

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if "store-response" in kwargs and cb.get_active():
            flag = True
            if kwargs["stored-responses"]:
                flag = False
                for i in kwargs["stored-responses"]:
                    if i == response:
                        flag = True
                        break

            if flag:
                self.settings["message"][text]["response"] = response

        logger.debug("Replied '%s'", response)
        return response

    def _add_text_view_layers(self):
        # split panes for detail view/text layer canvas and text layer dialog
        self._ocr_text_hbox = TextLayerControls()
        edit_hbox = self.builder.get_object("edit_hbox")
        edit_hbox.pack_start(self._ocr_text_hbox, True, True, 0)
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
        self._ann_hbox = TextLayerControls()
        edit_hbox.pack_start(self._ann_hbox, True, True, 0)
        ann_textview = Gtk.TextView()
        ann_textview.set_tooltip_text(_("Annotations"))
        self._ann_hbox._textbuffer = ann_textview.get_buffer()
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

    def _text_zoom_changed_callback(self, _widget, zoom):
        self.view.handler_block(self.view.zoom_changed_signal)
        self.view.set_zoom(zoom)
        self.view.handler_unblock(self.view.zoom_changed_signal)

    def _text_offset_changed_callback(self, _widget, x, y):
        self.view.handler_block(self.view.offset_changed_signal)
        self.view.set_offset(x, y)
        self.view.handler_unblock(self.view.offset_changed_signal)

    def _ann_zoom_changed_callback(self, _widget, zoom):
        self.view.handler_block(self.view.zoom_changed_signal)
        self.view.set_zoom(zoom)
        self.view.handler_unblock(self.view.zoom_changed_signal)

    def _ann_offset_changed_callback(self, _widget, x, y):
        self.view.handler_block(self.view.offset_changed_signal)
        self.view.set_offset(x, y)
        self.view.handler_unblock(self.view.offset_changed_signal)

    def _ocr_text_button_clicked(self, _widget):
        self._take_snapshot()
        text = self._ocr_text_hbox._textbuffer.get_text(
            self._ocr_text_hbox._textbuffer.get_start_iter(),
            self._ocr_text_hbox._textbuffer.get_end_iter(),
            False,
        )
        logger.info("Corrected '%s'->'%s'", self._current_ocr_bbox.text, text)
        self._current_ocr_bbox.update_box(text, self.view.get_selection())
        self._current_page.import_hocr(self.t_canvas.hocr())
        self._edit_ocr_text(self._current_ocr_bbox)

    def _ocr_text_copy(self, _widget):
        self._current_ocr_bbox = self.t_canvas.add_box(
            text=self._ocr_text_hbox._textbuffer.get_text(
                self._ocr_text_hbox._textbuffer.get_start_iter(),
                self._ocr_text_hbox._textbuffer.get_end_iter(),
                False,
            ),
            bbox=self.view.get_selection(),
        )
        self._current_page.import_hocr(self.t_canvas.hocr())
        self._edit_ocr_text(self._current_ocr_bbox)

    def _ocr_text_add(self, _widget):
        self._take_snapshot()
        text = self._ocr_text_hbox._textbuffer.get_text(
            self._ocr_text_hbox._textbuffer.get_start_iter(),
            self._ocr_text_hbox._textbuffer.get_end_iter(),
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
        text = self._ann_hbox._textbuffer.get_text(
            self._ann_hbox._textbuffer.get_start_iter(),
            self._ann_hbox._textbuffer.get_end_iter(),
            False,
        )
        logger.info("Corrected '%s'->'%s'", self._current_ann_bbox.text, text)
        self._current_ann_bbox.update_box(text, self.view.get_selection())
        self._current_page.import_annotations(self.a_canvas.hocr())
        self._edit_annotation(self._current_ann_bbox)

    def _ann_text_new(self, _widget):
        text = self._ann_hbox._textbuffer.get_text(
            self._ann_hbox._textbuffer.get_start_iter(),
            self._ann_hbox._textbuffer.get_end_iter(),
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
            logger.debug("edit_ocr_text returning as no bbox")
            return

        self._current_ocr_bbox = bbox
        self._ocr_text_hbox._textbuffer.set_text(bbox.text)
        self._ocr_text_hbox.show_all()
        self.view.set_selection(bbox.bbox)
        self.view.setzoom_is_fit(False)
        self.view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            self.t_canvas.pointer_ungrab(widget, ev.time)

        if bbox:
            self.t_canvas.set_index_by_bbox(bbox)

    def _edit_annotation(self, widget, _target=None, ev=None, bbox=None):
        "Edit annotation"
        if not ev:
            bbox = widget

        self._current_ann_bbox = bbox
        self._ann_hbox._textbuffer.set_text(bbox.text)
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

    def zoom_100(self, _action, _param):
        "Sets the zoom level of the view to 100%."
        self.view.set_zoom(1.0)

    def zoom_to_fit(self, _action, _param):
        "Adjusts the view to fit the content within the visible area."
        self.view.zoom_to_fit()

    def zoom_in(self, _action, _param):
        "Zooms in the current view"
        self.view.zoom_in()

    def zoom_out(self, _action, _param):
        "Zooms out the current view"
        self.view.zoom_out()

    # It's a shame that we have to define these here, but I can't see a way
    # to connect the actions in a context menu in app.ui otherwise
    def _on_dragger(self, _widget):
        "Handles the event when the dragger tool is selected."
        # builder calls this the first time before the window is defined
        self._change_image_tool_cb(
            self._actions["tooltype"], GLib.Variant("s", DRAGGER_TOOL)
        )

    def _on_selector(self, _widget):
        "Handles the event when the selector tool is selected."
        # builder calls this the first time before the window is defined
        self._change_image_tool_cb(
            self._actions["tooltype"], GLib.Variant("s", SELECTOR_TOOL)
        )

    def _on_selectordragger(self, _widget):
        "Handles the event when the selector dragger tool is selected."
        # builder calls this the first time before the window is defined
        self._change_image_tool_cb(
            self._actions["tooltype"], GLib.Variant("s", SELECTORDRAGGER_TOOL)
        )

    def _on_zoom_100(self, _widget):
        "Zooms the current page to 100%"
        self.zoom_100(None, None)

    def _on_zoom_to_fit(self, _widget):
        "Zooms the current page so that it fits the viewing pane."
        self.zoom_to_fit(None, None)

    def _on_zoom_in(self, _widget):
        "Zooms in the current page."
        self.zoom_in(None, None)

    def _on_zoom_out(self, _widget):
        "Zooms out the current page."
        self.zoom_out(None, None)

    def _on_rotate_90(self, _widget):
        "Rotate the selected pages by 90 degrees."
        self.rotate_90(None, None)

    def _on_rotate_180(self, _widget):
        "Rotate the selected pages by 180 degrees."
        self.rotate_180(None, None)

    def _on_rotate_270(self, _widget):
        "Rotate the selected pages by 270 degrees."
        self.rotate_270(None, None)

    def _on_save(self, _widget):
        "Displays the save dialog."
        self.save_dialog(None, None)

    def _on_email(self, _widget):
        "displays the email dialog."
        self.email(None, None)

    def _on_print(self, _widget):
        "displays the print dialog."
        self.print_dialog(None, None)

    def _on_renumber(self, _widget):
        "Displays the renumber dialog."
        self.renumber_dialog(None, None)

    def _on_select_all(self, _widget):
        "selects all pages."
        self.select_all(None, None)

    def _on_select_odd(self, _widget):
        "selects the pages with odd numbers."
        self.select_odd_even(0)

    def _on_select_even(self, _widget):
        "selects the pages with even numbers."
        self.select_odd_even(1)

    def _on_invert_selection(self, _widget):
        "Inverts the current selection."
        self.select_invert(None, None)

    def _on_crop(self, _widget):
        "Displays the crop dialog."
        self.crop_selection(None, None)

    def _on_cut(self, _widget):
        "cuts the selected pages to the clipboard."
        self.cut_selection(None, None)

    def _on_copy(self, _widget):
        "copies the selected pages to the clipboard."
        self.copy_selection(None, None)

    def _on_paste(self, _widget):
        "pastes the copied pages."
        self.paste_selection(None, None)

    def _on_delete(self, _widget):
        "deletes the selected pages."
        self.delete_selection(None, None)

    def _on_clear_ocr(self, _widget):
        "Clears the OCR (Optical Character Recognition) data."
        self.clear_ocr(None, None)

    def _on_properties(self, _widget):
        "displays the properties dialog."
        self.properties(None, None)

    def _on_quit(self, _action, _param):
        "Handles the quit action."
        self.get_application().quit()

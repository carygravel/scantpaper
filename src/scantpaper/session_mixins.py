"""provide methods around session files."""

from __future__ import annotations

import fcntl
import inspect
import logging
import tempfile
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, cast

import gi
import tesserocr

from scantpaper import config
from scantpaper.bboxtree import Bboxtree
from scantpaper.const import (
    EMPTY,
    SPACE,
)
from scantpaper.dialog import filter_message, response_stored
from scantpaper.helpers import get_tmp_dir, program_version
from scantpaper.i18n import _
from scantpaper.layer import LayerEditor
from scantpaper.simplelist import SimpleList
from scantpaper.unpaper import Unpaper

if TYPE_CHECKING:
    from gi.repository import Gio

    from scantpaper.basethread import Response
    from scantpaper.dialog.sane import SaneScanDialog
    from scantpaper.page import Page

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    GLib,
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)


class SessionMixins:
    """provide methods around session files."""

    def _create_temp_directory(self) -> None:
        """Create a temporary directory for the session."""
        tmpdir = get_tmp_dir(self.settings["TMPDIR"], r"scantpaper-\w\w\w\w\w\w\w\w")
        if tmpdir is None or tmpdir == EMPTY:
            self.session = tempfile.TemporaryDirectory(prefix="scantpaper-")
        else:
            if not Path(tmpdir).is_dir():
                Path(tmpdir).mkdir()
            try:
                self.session = tempfile.TemporaryDirectory(
                    prefix="scantpaper-", dir=tmpdir
                )
            except (FileNotFoundError, PermissionError):
                logger.exception("Error creating temporary directory")
                # Keep as fallback: handle stored on self for session lifetime
                self.session = tempfile.TemporaryDirectory(prefix="scantpaper-")

        self._lockfd = self._create_lockfile()
        logger.info("Using %s for temporary files", self.session.name)
        tmpdir = str(Path(self.session.name).parent)
        if "TMPDIR" in self.settings:
            if (
                self.settings["TMPDIR"] is not None
                and self.settings["TMPDIR"] != tmpdir
            ):
                logger.warning(
                    _(
                        "Warning: unable to use %(configured)s for temporary "
                        "storage. Defaulting to %(default)s instead."
                    ),
                    {
                        "configured": self.settings["TMPDIR"],
                        "default": tmpdir,
                    },
                )
            self.settings["TMPDIR"] = tmpdir

    def _create_lockfile(self, session: str | None = None) -> object:
        """Create a lockfile in the session directory."""
        if session is None:
            session = self.session.name
        # SIM115: cross-scope file handle used intentionally
        lockfile = Path(session) / "lockfile"
        lockfd = lockfile.open("w", encoding="utf-8")
        fcntl.lockf(lockfd, fcntl.LOCK_EX)
        return lockfd

    def _find_crashed_sessions(self) -> None:
        """Look for crashed sessions."""
        tmpdir = get_tmp_dir(self.settings["TMPDIR"], r"scantpaper-\w\w\w\w\w\w\w\w")
        if tmpdir is None or tmpdir == EMPTY:
            tmpdir = tempfile.gettempdir()

        logger.info("Checking %s for crashed sessions", tmpdir)
        dbs = sorted(Path(tmpdir).glob("scantpaper-????????.sdb"))
        crashed, selected = [], []

        # Forget those used by running sessions
        for db in dbs:
            session = str(Path(tmpdir) / PurePath(db).stem)
            if session == self.session.name:
                continue
            if not Path(session).is_dir():
                crashed.append(str(db))
                continue
            try:
                self._create_lockfile(session)
                crashed.append(str(db))
            except OSError as e:
                logger.warning("Error opening lockfile %s", str(e))

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
            for db in crashed:
                sessionlist.data.append([db])
            box.add(sessionlist)
            dialog.show_all()
            if dialog.run() == Gtk.ResponseType.OK:
                selected = sessionlist.get_selected_indices()

            dialog.destroy()
            if selected:
                self._open_session(crashed[selected[0]])

    def _check_dependencies(self) -> None:
        """Check for presence of various packages."""
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

        self._dependencies["imagemagick"] = None
        self._dependencies["graphicsmagick"] = None
        dependency_rules = [
            [
                "imagemagick",
                "stdout",
                r"Version:\sImageMagick\s([\d.-]+)",
                [config.CONVERT_COMMAND, "--version"],
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
            ["qpdf", "stdout", r"([\d.]+)", ["qpdf", "--version"]],
        ]

        for name, stream, regex, cmd in dependency_rules:
            name = cast("str", name)
            stream = cast("str", stream)
            regex = cast("str", regex)
            cmd = cast("list[str]", cmd)
            self._dependencies[name] = program_version(stream, regex, cmd)
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

        # OCR engine options
        if self._dependencies["tesseract"]:
            self._ocr_engine.append(
                ["tesseract", _("Tesseract"), _("Process image with Tesseract.")]
            )

    def _finished_process_callback(
        self, widget: SaneScanDialog, process: str, button_signal: int | None = None
    ) -> None:
        """Handle the completion of a process."""
        logger.debug("signal 'finished-process' emitted with data: %s", process)
        if button_signal is not None:
            self._scan_progress.disconnect(button_signal)

        self._scan_progress.hide()
        if process == "scan_pages" and widget.sided == "double":

            def prompt_reverse_sides() -> None:
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

    def _display_callback(self, response: Response) -> None:
        """Find the page from the input uuid and display it."""
        if isinstance(response.info, dict) and "row" in response.info:
            uuid = response.info["row"][2]
            i = self.slist.find_page_by_uuid(uuid)
            if i is None:
                logger.error("Can't display page with uuid %s: page not found", uuid)
            else:
                self._display_image(self.slist.data[i][2])

    def _display_image(self, pageid: str) -> None:
        """Display the image in the view."""
        # Find the index for this pageid to get the thumbnail
        i = self.slist.find_page_by_uuid(pageid)
        if i is None:
            logger.error("Cannot display page with id %s: page not found", pageid)
            return

        # Immediate: show the thumbnail pixbuf from self.data[i][1]
        thumbnail_pixbuf = self.slist.data[i][1]
        if thumbnail_pixbuf is not None:
            self.view.set_pixbuf(thumbnail_pixbuf, zoom_to_fit=True)

        # Deferred: send "get_page" async with callback for full-res. During a
        # bulk import this is suppressed (thumbnails only) and a single
        # full-resolution load is triggered when the import finishes.
        if getattr(self, "_suppress_full_display", False):
            return

        def on_page_error(response: Response) -> None:
            logger.error("Error loading page %s: %s", pageid, response.status)

        self.slist.thread.send(
            "get_page",
            {"id": pageid},
            finished_callback=self._on_page_loaded,
            error_callback=on_page_error,
        )

    def _on_page_loaded(self, response: Response) -> None:
        """Display a fully loaded page."""
        self._current_page = response.info
        self.view.set_pixbuf(self._current_page.get_pixbuf(), zoom_to_fit=True)
        xresolution, yresolution, _units = self._current_page.get_resolution()
        self.view.set_resolution_ratio(xresolution / yresolution)

        # Re-apply the selection now that the full-resolution image is
        # displayed, so it is clamped to the real page size rather than the
        # transient thumbnail. The crop dialog manages the selection itself
        # (below), so skip it when that dialog owns the selection.
        if self._windowc is None and self.settings.get("selection") is not None:
            self.view.set_selection(self.settings["selection"])

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
            self._text_editor.create(
                cast("Page", self._current_page), self.view.get_offset()
            )
        else:
            self._text_editor.clear()

        if self._current_page.annotations:
            self._ann_editor.create(
                cast("Page", self._current_page), self.view.get_offset()
            )
        else:
            self._ann_editor.clear()

    def _error_callback(self, response: Response) -> None:
        """Handle errors."""
        args = response.request.args
        process = response.request.process
        stage = response.type.name.lower()
        message = response.status

        if trace := inspect.trace():
            trace.reverse()
            for info in trace:
                if "scantpaper" in info.filename:
                    logger.error("Filename: '%s' line: %s", info.filename, info.lineno)
                    break

        page = None
        if args and isinstance(args[0], dict) and "page" in args[0]:
            idx = self.slist.find_page_by_uuid(args[0]["page"])
            if idx is not None:
                page = self.slist.data[idx][0]

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

        def show_message_dialog_wrapper() -> None:
            """Wrap show_message_dialog() in GLib.idle_add() to let the thread continue.

            This allows the thread to return immediately and keep working on
            subsequent pages despite errors on previous ones.
            """
            self._show_message_dialog(**kwargs)

        GLib.idle_add(show_message_dialog_wrapper)
        self.post_process_progress.hide()

    def _ask_question(self, **kwargs: object) -> object:
        """Display a message dialog, wait for a response, and return it."""
        # replace any numbers with metacharacters to compare to filter
        text = filter_message(cast("str", kwargs["text"]))
        if response_stored(text, self.settings["message"]):
            logger.debug(
                "Skipped MessageDialog with '%s', automatically replying '%s'",
                kwargs["text"],
                self.settings["message"][text]["response"],
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
                for i in cast("list[object]", kwargs["stored-responses"]):
                    if i == response:
                        flag = True
                        break

            if flag:
                if text not in self.settings["message"]:
                    self.settings["message"][text] = {}
                self.settings["message"][text]["response"] = response

        logger.debug("Replied '%s'", response)
        return response

    def _add_text_view_layers(self) -> None:
        """Create the text and annotation editors and their control bars."""
        view = self.view

        def get_page() -> Page | None:
            return cast("Page | None", getattr(self, "_current_page", None))

        self._text_editor = LayerEditor(
            page_attr="text_layer",
            view=view,
            thread=self.slist.thread,
            get_page=get_page,
            features=("sort", "nav", "copy"),
        )
        self._ann_editor = LayerEditor(
            page_attr="annotations",
            view=view,
            thread=self.slist.thread,
            get_page=get_page,
        )

        # Keep canvas aliases so existing mixins (clear_text, layout) still work.
        self.t_canvas = self._text_editor.canvas
        self.a_canvas = self._ann_editor.canvas

        for canvas in (self.t_canvas, self.a_canvas):
            self.view.bind_property(
                "zoom",
                canvas,
                "zoom",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )
            self.view.bind_property(
                "offset",
                canvas,
                "offset",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )
            self.view.bind_property(
                "selection",
                canvas,
                "selection",
                GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE,
            )

        edit_hbox = self.builder.get_object("edit_hbox")
        edit_hbox.pack_start(
            self._text_editor.controls, expand=True, fill=True, padding=0
        )
        edit_hbox.pack_start(
            self._ann_editor.controls, expand=True, fill=True, padding=0
        )
        self._pack_viewer_tools()

    def _edit_mode_callback(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        """Show/hide the edit tools."""
        action.set_state(parameter)
        if parameter.get_string() == "text":
            self._text_editor.set_active(active=True)
            self._ann_editor.set_active(active=False)
            return
        self._text_editor.set_active(active=False)
        self._ann_editor.set_active(active=True)

    def zoom_100(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        """Set the zoom level of the view to 100%."""
        self.view.set_zoom(1.0)

    def zoom_to_fit(
        self, _action: Gio.SimpleAction, _param: GLib.Variant | None
    ) -> None:
        """Adjust the view to fit the content within the visible area."""
        self.view.zoom_to_fit()

    def zoom_in(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        """Zoom in the current view."""
        self.view.zoom_in()

    def zoom_out(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        """Zoom out the current view."""
        self.view.zoom_out()

    def _on_zoom_100(self, _widget: Gtk.Widget) -> None:
        """Zoom the current page to 100%."""
        self.zoom_100(None, None)

    def _on_zoom_to_fit(self, _widget: Gtk.Widget) -> None:
        """Zoom the current page so that it fits the viewing pane."""
        self.zoom_to_fit(None, None)

    def _on_zoom_in(self, _widget: Gtk.Widget) -> None:
        """Zoom in the current page."""
        self.zoom_in(None, None)

    def _on_zoom_out(self, _widget: Gtk.Widget) -> None:
        """Zoom out the current page."""
        self.zoom_out(None, None)

    def _on_rotate_90(self, _widget: Gtk.Widget) -> None:
        """Rotate the selected pages by 90 degrees."""
        self.rotate_90(None, None)

    def _on_rotate_180(self, _widget: Gtk.Widget) -> None:
        """Rotate the selected pages by 180 degrees."""
        self.rotate_180(None, None)

    def _on_rotate_270(self, _widget: Gtk.Widget) -> None:
        """Rotate the selected pages by 270 degrees."""
        self.rotate_270(None, None)

    def _on_save(self, _widget: Gtk.Widget) -> None:
        """Display the save dialog."""
        self.save_dialog(None, None)

    def _on_email(self, _widget: Gtk.Widget) -> None:
        """Display the email dialog."""
        self.email(None, None)

    def _on_print(self, _widget: Gtk.Widget) -> None:
        """Display the print dialog."""
        self.print_dialog(None, None)

    def _on_select_all(self, _widget: Gtk.Widget) -> None:
        """Select all pages."""
        self.select_all(None, None)

    def _on_select_odd(self, _widget: Gtk.Widget) -> None:
        """Select the pages with odd numbers."""
        self.select_odd_even(0)

    def _on_select_even(self, _widget: Gtk.Widget) -> None:
        """Select the pages with even numbers."""
        self.select_odd_even(1)

    def _on_invert_selection(self, _widget: Gtk.Widget) -> None:
        """Inverts the current selection."""
        self.select_invert(None, None)

    def _on_crop(self, _widget: Gtk.Widget) -> None:
        """Display the crop dialog."""
        self.crop_selection(None, None)

    def _on_cut(self, _widget: Gtk.Widget) -> None:
        """Cut the selected pages to the clipboard."""
        self.cut_selection(None, None)

    def _on_copy(self, _widget: Gtk.Widget) -> None:
        """Copy the selected pages to the clipboard."""
        self.copy_selection(None, None)

    def _on_paste(self, _widget: Gtk.Widget) -> None:
        """Pastes the copied pages."""
        self.paste_selection(None, None)

    def _on_delete(self, _widget: Gtk.Widget) -> None:
        """Delete the selected pages."""
        self.delete_selection(None, None)

    def _on_clear_ocr(self, _widget: Gtk.Widget) -> None:
        """Clear the OCR (Optical Character Recognition) data."""
        self.clear_ocr(None, None)

    def _on_properties(self, _widget: Gtk.Widget) -> None:
        """Display the properties dialog."""
        self.properties(None, None)

    def _on_quit(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        """Handle the quit action."""
        self.get_application().quit()

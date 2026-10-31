"""provide methods around session files."""

from __future__ import annotations

import contextlib
import fcntl
import inspect
import logging
import tempfile
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.bboxtree import Bboxtree
from scantpaper.const import (
    EMPTY,
    SPACE,
)
from scantpaper.dependencies import DEPS
from scantpaper.dialog import (
    filter_message,
    pad_action_area,
    pad_content_area,
    response_stored,
)
from scantpaper.helpers import get_tmp_dir, remove_session_snapshot, run_dialog
from scantpaper.i18n import _, ngettext
from scantpaper.layer import LayerEditor
from scantpaper.simplelist import SimpleList

if TYPE_CHECKING:
    from typing import TextIO

    from gi.repository import Gio

    from scantpaper.basethread import Response
    from scantpaper.dialog.sane import SaneScanDialog
    from scantpaper.page import Page

gi.require_version("Gtk", "4.0")
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

    def _try_lock_snapshot(self, db: Path) -> TextIO | None:
        """Reserve a crashed snapshot without waiting for another instance."""
        db = Path(db)
        session = db.with_suffix("") if db.suffix == ".sdb" else db.with_name(db.stem)
        lock_path = session / "lockfile" if session.is_dir() else Path(f"{db}.lock")
        try:
            lockfile = lock_path.open("w", encoding="utf-8")
        except OSError as err:
            logger.warning("Error opening lockfile %s: %s", lock_path, err)
            return None
        try:
            fcntl.lockf(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lockfile.close()
            return None
        return lockfile

    def _release_crashed_session_locks(self) -> None:
        """Release reservations held by the crashed-session picker."""
        for lockfile in getattr(self, "_crashed_session_locks", []):
            with contextlib.suppress(OSError):
                lockfile.close()
        self._crashed_session_locks = []

    def _find_crashed_sessions(self) -> list[str]:
        """Return crashed snapshots that are not in use."""
        self._release_crashed_session_locks()
        tmpdir = get_tmp_dir(self.settings["TMPDIR"], r"scantpaper-\w\w\w\w\w\w\w\w")
        if tmpdir is None or tmpdir == EMPTY:
            tmpdir = tempfile.gettempdir()

        logger.info("Checking %s for crashed sessions", tmpdir)
        dbs = sorted(Path(tmpdir).glob("scantpaper-????????.sdb"))
        crashed: list[str] = []
        locks: list[TextIO] = []
        current = getattr(getattr(self, "session", None), "name", None)

        for db in dbs:
            session = str(Path(tmpdir) / PurePath(db).stem)
            if session == current:
                continue
            lockfile = self._try_lock_snapshot(db)
            if lockfile is None:
                continue
            locks.append(lockfile)
            crashed.append(str(db))

        self._crashed_session_locks = locks
        return crashed

    def _show_crashed_sessions(self, *, report_empty: bool = False) -> None:
        """List crashed snapshots and let the user restore or discard them."""
        crashed = self._find_crashed_sessions()
        if not crashed:
            if report_empty:
                self._show_message_dialog(
                    parent=self,
                    message_type="info",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=_("No crashed sessions found."),
                    store_response=True,
                )
            return

        dialog = Gtk.Dialog(
            title=_("Crashed sessions"),
            transient_for=self,
            modal=True,
        )
        dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("_Discard"), Gtk.ResponseType.REJECT)
        dialog.add_button(_("_Restore"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        pad_action_area(dialog)
        label = Gtk.Label(label=_("Restore or discard a crashed session"))
        box = dialog.get_content_area()
        pad_content_area(box)
        box.append(label)
        columns = {_("Session"): "text"}
        sessionlist = SimpleList(**columns)
        sessionlist.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        for db in crashed:
            sessionlist.data.append([db])
        box.append(sessionlist)

        keep_locks = False
        try:
            response = run_dialog(dialog)
            selected = sessionlist.get_selected_indices()
            if response == Gtk.ResponseType.OK and selected:
                keep_locks = True
                self._restore_crashed_session(crashed[selected[0]])
            elif response == Gtk.ResponseType.REJECT and selected:
                self._discard_crashed_sessions([crashed[i] for i in selected])
        finally:
            dialog.destroy()
            if not keep_locks:
                self._release_crashed_session_locks()

    def _restore_crashed_session(self, db: str) -> None:
        """Restore a snapshot and release its reservation when finished."""
        if not self._pages_saved(
            _(
                "Some pages have not been saved.\nDo you really want to restore a crashed session?"
            )
        ):
            self._release_crashed_session_locks()
            return

        progress = getattr(self, "post_process_progress", None)
        if progress is not None:
            progress.pulse()

        def finished_callback(_response: object) -> None:
            if progress is not None:
                progress.finish(None)
            self._release_crashed_session_locks()

        def error_callback(_parent: object, _msg: str, status: str) -> None:
            if progress is not None:
                progress.finish(None)
            self._release_crashed_session_locks()
            self._show_message_dialog(
                parent=self,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=status,
                store_response=True,
            )

        try:
            self.slist.restore_session(
                db=db,
                error_callback=error_callback,
                finished_callback=finished_callback,
            )
        except Exception as err:
            logger.exception("Error restoring crashed session %s", db)
            error_callback(None, _("Restore file"), str(err))

    @staticmethod
    def _remove_crashed_snapshot(db: str) -> str | None:
        """Remove one snapshot and return an error description on failure."""
        try:
            remove_session_snapshot(db)
        except OSError as err:
            logger.exception("Error discarding crashed session %s", db)
            return f"{db}: {err}"
        return None

    def _discard_crashed_sessions(self, dbs: list[str]) -> None:
        """Remove selected snapshots after confirmation."""
        count = len(dbs)
        message = ngettext(
            "Discard this %(count)d crashed session?",
            "Discard these %(count)d crashed sessions?",
            count,
        ) % {"count": count}
        response = self._ask_question(
            parent=self,
            type="question",
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=message,
            default_response=Gtk.ResponseType.CANCEL,
        )
        if response != Gtk.ResponseType.OK:
            return

        failures = [
            failure
            for db in dbs
            if (failure := self._remove_crashed_snapshot(db)) is not None
        ]
        if failures:
            self._show_message_dialog(
                parent=self,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=_("Unable to discard some crashed sessions."),
                store_response=True,
            )

    def _check_dependencies(self) -> None:
        """Check for presence of various packages."""
        for dep in DEPS:
            result = dep.probe()
            self._dependencies[dep.name] = result.version
            if bool(result.version):
                logger.info("Found %s %s", dep.name, result.version)
            if dep.name == "imagemagick" and result.using_fallback:
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

        # OCR engine options
        if self._dependencies["tesseract"]:
            self._ocr_engine.append(
                ["tesseract", _("Tesseract"), _("Process image with Tesseract.")]
            )

    def _finished_process_callback(self, widget: SaneScanDialog, process: str) -> None:
        """Handle the completion of a process."""
        logger.debug("signal 'finished-process' emitted with data: %s", process)
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
            # The page no longer exists in the document: drop it from the list
            # so it is not repeatedly reported as missing, and show a valid
            # page instead of the stale thumbnail.
            if self.slist.remove_page_by_uuid(pageid):
                self._redisplay_after_page_removed(i)

        self.slist.thread.send(
            "get_page",
            {"id": pageid},
            finished_callback=self._on_page_loaded,
            error_callback=on_page_error,
        )

    def _redisplay_after_page_removed(self, removed_index: int) -> None:
        """Show a valid page (or clear the view) after a stale page is removed."""
        if not self.slist.data:
            self.view.set_pixbuf(None)
            return
        idx = min(removed_index, len(self.slist.data) - 1)
        self._display_image(self.slist.data[idx][2])

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

        # Seeding the extent after the branch gives both editors the page
        # size even when there is no layer to parse it from, so a selection
        # can be drawn before the first OCR run (and for empty sentinels,
        # whose parse yields no extent).
        self._text_editor.set_extent(width, height, self.view.get_offset())
        self._ann_editor.set_extent(width, height, self.view.get_offset())

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
            transient_for=kwargs["parent"],
            modal=True,
            destroy_with_parent=True,
            message_type=kwargs["type"],
            buttons=kwargs["buttons"],
            text=kwargs["text"],
        )
        logger.debug("Displayed MessageDialog with '%s'", kwargs["text"])
        if "store-response" in kwargs:
            cb = Gtk.CheckButton.new_with_label(_("Don't show this message again"))
            dialog.get_message_area().append(cb)

        if "default-response" in kwargs:
            dialog.set_default_response(kwargs["default-response"])

        response = run_dialog(dialog)
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
            features=("sort", "nav", "copy", "rotate"),
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
                "resolution_ratio",
                canvas,
                "resolution_ratio",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )
            self.view.bind_property(
                "selection",
                canvas,
                "selection",
                GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE,
            )

        edit_hbox = self.builder.get_object("edit_hbox")
        edit_hbox.append(self._text_editor.controls)
        self._text_editor.controls.set_hexpand(True)
        edit_hbox.append(self._ann_editor.controls)
        self._ann_editor.controls.set_hexpand(True)
        self._pack_viewer_tools()

    def _edit_mode_callback(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        """Show the requested layer's editor."""
        action.set_state(parameter)
        self._set_active_layer(parameter.get_string())

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

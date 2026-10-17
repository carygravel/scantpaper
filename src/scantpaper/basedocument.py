"""Base document methods."""

from __future__ import annotations

import logging
import os
import pathlib
import queue
import signal
import tempfile
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.docthread import INSERT_AT_START, DocThread
from scantpaper.helpers import _weak_callback, slurp
from scantpaper.i18n import _
from scantpaper.simplelist import SimpleList

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.basethread import Response

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)


class BaseDocument(SimpleList):
    """a Document is a simple list of pages, backed by SQLite."""

    jobs_completed = 0
    jobs_total = 0

    def __init__(self, **kwargs: object) -> None:
        """Initialise BaseDocument."""
        columns = {"#": "int", _("Thumbnails"): "pixbuf", "Page ID": "hint"}
        super().__init__(**columns)
        self.thread = DocThread(**kwargs)
        self.thread.register_callback("display", "after", "data")
        self.thread.register_callback("updated_page", "after", "data")
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_headers_visible(False)
        self.dir: str | pathlib.Path | None = None
        self._context = {}
        self._suppress_delete = False
        for key, val in kwargs.items():
            setattr(self, key, val)
        if getattr(self, "dir", None) is None:
            self.dir = self.thread.dir
        if isinstance(self.dir, str):
            self.dir = pathlib.Path(self.dir)

        # GTK4 drag-and-drop (replaces the GTK3 Gtk.TargetEntry /
        # drag_source_set / drag_dest_set API). A Gtk.DragSource starts an
        # internal row drag; one Gtk.DropTarget handles our own row drops and
        # another handles external file drops (GTK converts text/uri-list
        # into a Gdk.FileList automatically).
        #
        # Note: Gtk.TreeView.set_reorderable() is deliberately NOT enabled; it
        # would install its own drag source/drop target that reorders the
        # model directly, bypassing the worker reorder used here.
        self._internal_drag: bool = False
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-end", self._on_drag_end)
        self.add_controller(drag_source)

        files_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        files_target.connect("drop", self._on_drop_files)
        self.add_controller(files_target)
        self.files_drop_target = files_target

        rows_target = Gtk.DropTarget.new(
            GObject.TYPE_STRING, Gdk.DragAction.COPY | Gdk.DragAction.MOVE
        )
        rows_target.connect("accept", self._on_rows_accept)
        rows_target.connect("drop", self._on_drop_rows)
        self.add_controller(rows_target)
        self.rows_drop_target = rows_target

        # Set the page number to be editable
        self.set_column_editable(0, editable=True)
        self.row_changed_signal = self.get_model().connect(
            "row-changed", _weak_callback(self, "_on_row_changed")
        )
        self.selection_changed_signal = self.get_selection().connect(
            "changed", _weak_callback(self, "_on_selection_changed")
        )

        # selection changed signal is not being blocked correctly, so add an extra flag
        self._block_signals = False

    def _on_row_changed(
        self, _self: Gtk.TreeModel, _path: Gtk.TreePath, _iter: Gtk.TreeIter
    ) -> None:
        """Set up the callback when the page number has been edited."""
        # Note uuids for selected pages
        selection = self.get_selected_indices()
        uuids = [self.data[i][2] for i in selection]

        self.get_model().handler_block(self.row_changed_signal)

        # Move the edited page to the position given by its number
        edited = None
        for i, row in enumerate(self.data):
            if row[0] != i + 1:
                edited = i
                break
        if edited is not None:
            new_position = max(
                1, min(int(cast("int", self.data[edited][0])), len(self.data))
            )
            if new_position - 1 != edited:
                model = self.get_model()
                row = list(model[edited])
                del self.data[edited]
                self.data.insert(new_position - 1, row)

        # Page numbers are always consecutive 1..n
        self.renumber()
        self.get_model().handler_unblock(self.row_changed_signal)

        # Select the renumbered pages via uuid
        selection = []
        for i in uuids:
            selection.append(self.find_page_by_uuid(i))
        self.select(selection)

    def _on_selection_changed(self, _selection: Gtk.TreeSelection) -> None:
        if self._block_signals:
            return
        self.thread.send("set_selection", self.get_selected_indices())

    def set_paper_sizes(self, paper_sizes: dict[str, object] | None = None) -> None:
        """Set the paper sizes in the manager and worker threads."""
        self.thread.send("set_paper_sizes", paper_sizes)

    def cancel(
        self,
        cancel_callback: Callable[..., object],
        process_callback: Callable[[int], object] | None = None,
    ) -> None:
        """Kill all running processes."""
        with self.thread.lock:
            # Empty the response queue first so the cancelled notifications
            # queued below are not swallowed by the drain
            logger.info("Emptying process queue")
            try:
                while self.thread.responses.get(False):
                    pass
            except queue.Empty:
                pass

            # Cancel queued requests so their requesters are notified
            self.thread.drain_cancelled_requests()

            # Then send the thread a cancel signal
            # to stop it going beyond the next break point
            self.thread.cancel = True

            # Kill all running processes in the thread
            for pidfile in list(self.thread.running_pids):
                pid = slurp(pidfile)
                try:
                    pid = int(pid)
                except (TypeError, ValueError):
                    continue
                if pid <= 1:
                    del self.thread.running_pids[pidfile]
                    continue
                if process_callback is not None:
                    process_callback(pid)

                logger.info("Killing PID %s", pid)

                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    logger.info("PID %s already dead", pid)
                finally:
                    del self.thread.running_pids[pidfile]

        # Add a cancel request to ensure the reply is not blocked
        logger.info("Requesting cancel")
        self.thread.send("cancel", finished_callback=cancel_callback)

    def create_pidfile(self, options: dict[str, object]) -> object | None:
        """Create file in which to store the PID."""
        options = defaultdict(None, options)
        try:
            # SIM115: the pidfile handle escapes to the thread's running_pids
            # registry so that cancel() can later read the spawn pid from it.
            pidfile = tempfile.TemporaryFile(  # noqa: SIM115
                dir=self.dir, suffix=".pid", mode="w+t"
            )
        except (OSError, PermissionError):
            logger.exception("Caught error writing to %s", self.dir)
            if "error_callback" in options:
                cast("Callable[..., object]", options["error_callback"])(
                    options.get("page"),
                    "create PID file",
                    f"Error: unable to write to {self.dir}.",
                )
            return None
        if getattr(self.thread, "running_pids", None) is not None:
            with self.thread.lock:
                self.thread.running_pids[pidfile] = pidfile
        return pidfile

    def data_callback(
        self,
        response: Response,
        options: dict[str, object],
        post_process: Callable[..., object] | None = None,
    ) -> None:
        """Add a page from a worker response, then log any errors."""
        info = response.info
        if isinstance(info, dict) and "type" in info and info["type"] == "page":
            self.add_page(*info["row"], **info)
            if post_process:
                post_process(info["row"][2], options)
        elif (
            isinstance(info, dict)
            and info.get("type") == "user-message"
            and "message_callback" in options
        ):
            cast("Callable[..., object]", options["message_callback"])(response)
        elif "logger_callback" in options:
            cast("Callable[..., object]", options["logger_callback"])(response)

    def find_page_by_uuid(self, uid: object) -> int | None:
        """Return page index given uuid."""
        if uid is None:
            logger.error("find_page_by_uuid() called with None")
            return None

        for i, row in enumerate(self.data):
            if uid == row[2]:
                return i
        return None

    def remove_page_by_uuid(self, uid: object) -> bool:
        """Remove a stale page from the list by its id.

        Used to reconcile the page list when a referenced page no longer
        exists in the document (e.g. it was dropped from the current undo
        snapshot), so it is not repeatedly reported as missing. Returns True
        if the page was present and removed.
        """
        i = self.find_page_by_uuid(uid)
        if i is None:
            return False
        logger.info("Removing stale page %s from the page list", uid)
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)
        del self.data[i]
        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)
        self.renumber()
        return True

    def _find_page_by_ref(self, uid: object) -> int:
        i = self.find_page_by_uuid(uid)
        if i is None:
            logger.error("Requested page %s does not exist.", uid)
            msg = f"Requested page {uid} does not exist."
            raise ValueError(msg)
        return i

    def add_page(
        self, number: int, thumb: object, page_id: int, **kwargs: object
    ) -> int:
        """Add a new page to the document."""
        ref = kwargs.get("insert-after", kwargs.get("replace"))
        i = None
        if ref is not None:
            i = -1 if ref == INSERT_AT_START else self._find_page_by_ref(ref)

        # Block the row-changed signal whilst adding the scan (row).
        if self.row_changed_signal:
            self.get_model().handler_block(self.row_changed_signal)

        # Add to the page list
        if i is None:
            self.data.append([number, thumb, page_id])
            new_index = len(self.data) - 1
            logger.info(
                "Added page id %s at page number %s",
                page_id,
                new_index + 1,
            )

        elif "replace" in kwargs:
            old_id = self.data[i][2]
            self.data[i] = [number, thumb, page_id]
            new_index = i
            logger.info(
                "Replaced page id %s at page number %s with page id %s",
                old_id,
                i + 1,
                page_id,
            )
        else:
            self.data.insert(i + 1, [number, thumb, page_id])
            new_index = i + 1
            logger.info(
                "Inserted %s at page %s",
                page_id,
                new_index + 1,
            )

        # Page numbers are always consecutive 1..n. A pure append whose number
        # already equals its position needs no renumbering; only middle inserts,
        # replaces, and out-of-order appends require the global rewrite.
        self._renumber_after_add(i, number)

        # Block selection_changed_signal
        # to prevent its firing changing pagerange to all
        if self.selection_changed_signal:
            self.get_selection().handler_block(self.selection_changed_signal)

        self.get_selection().unselect_all()

        if self.selection_changed_signal:
            self.get_selection().handler_unblock(self.selection_changed_signal)

        if self.row_changed_signal:
            self.get_model().handler_unblock(self.row_changed_signal)

        self.select([new_index])
        return new_index

    def _renumber_after_add(self, i: int | None, number: int) -> None:
        """Renumber after adding a page, unless it is an in-order append."""
        if i is not None or number != len(self.data):
            self.renumber()

    def cut_selection(self, **kwargs: object) -> list[list[object]] | None:
        """Cut the selection."""
        data = self.copy_selection()
        self.delete_selection_extra(**kwargs)
        return data

    def copy_selection(self) -> list[list[object]] | None:
        """Copy the selection."""
        selection = self.get_selected_indices()
        logger.debug("copy_selection %s", selection)
        if selection == []:
            return None
        data = [
            [self.data[index][0], self.data[index][1], self.data[index][2]]
            for index in selection
        ]
        logger.info("Copied %s pages", len(data))
        return data

    def paste_selection(self, **kwargs: object) -> None:
        """Paste the selection."""
        # Block row-changed signal so that the list can be updated before the sort
        # takes over.
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        if kwargs.get("dest") is None:
            self._send_clone_pages(kwargs, len(self.data), "extend")
        else:
            dest = int(cast("int", kwargs["dest"]))
            if kwargs["how"] in (
                Gtk.TreeViewDropPosition.AFTER,
                Gtk.TreeViewDropPosition.INTO_OR_AFTER,
            ):
                dest += 1
            self._send_clone_pages(kwargs, dest, "insert")

    def _send_clone_pages(
        self, kwargs: dict[str, object], dest: int, action: str
    ) -> None:
        """Clone pages into this document, extending or inserting."""

        def _data_callback(response: Response) -> None:
            logger.debug("%s _data_callback(%s)", action, response)
            info = response.info
            if isinstance(info, dict) and "type" in info and info["type"] == "page":
                new_pages = info["new_pages"]
                if action == "extend":
                    self.data.extend(new_pages)
                else:
                    for row in new_pages:
                        self.data.insert(dest, row)
                self._post_paste_logic(dest, kwargs)

        self.thread.send(
            "clone_pages",
            {
                "page_ids": [
                    row[2] for row in cast("list[list[object]]", kwargs["data"])
                ],
                "dest": dest,
            },
            data_callback=_data_callback,
        )

    def _post_paste_logic(self, dest: int, kwargs: dict[str, object]) -> None:
        """Renumber, select and finalise the page list after a paste."""
        # Renumber the newly pasted rows positionally
        self.renumber()
        self.get_model().emit(
            "row-changed", Gtk.TreePath(), self.get_model().get_iter_first()
        )

        # Select the new pages
        if kwargs.get("select_new_pages"):
            selection: list[int | None] = list(
                range(dest, dest + len(cast("list[object]", kwargs["data"])))
            )

            self.get_selection().unselect_all()
            self.select(selection)

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

        logger.info(
            "Pasted %s pages at position %s",
            len(cast("list[object]", kwargs["data"])),
            dest,
        )
        if "finished_callback" in kwargs:
            cast("Callable[..., object]", kwargs["finished_callback"])()

    def delete_selection(
        self,
        _self: object | None = None,
        context: object | None = None,
        **kwargs: object,
    ) -> None:
        """Delete the selected pages."""
        # A drop during a reorder must not delete the just-moved pages, so
        # deletion is suppressed for the duration of the drag. NOTE: the flag
        # is deliberately NOT cleared here: it is cleared by _on_drag_end once
        # the whole drag is over, because the reorder may still be in flight.
        if getattr(self, "_suppress_delete", False):
            return

        # Historical guard against the same drop being reported twice (GTK3
        # emitted drag-data-delete more than once per drop). Kept because
        # callers may still pass a context; there must be a less hacky way of
        # solving this. FIXME
        if context is not None:
            if context in self._context:
                self._context = {}
                return

            self._context[context] = 1

        def _data_callback(response: Response) -> None:
            info = response.info
            if isinstance(info, dict) and "type" in info and info["type"] == "page":
                # Reverse the rows in order not to invalid the iters
                if paths:
                    for path in reversed(paths):
                        itr = model.get_iter(path)
                        model.remove(itr)
                self.renumber()

            if "finished_callback" in kwargs:
                cast("Callable[..., object]", kwargs["finished_callback"])()

        model, paths = self.get_selection().get_selected_rows()
        page_ids = [model.get_value(model.get_iter(path), 2) for path in paths]
        send_kwargs = kwargs.copy()
        if "finished_callback" in send_kwargs:
            del send_kwargs["finished_callback"]
        self.thread.send(
            "delete_pages",
            {"page_ids": page_ids},
            data_callback=_data_callback,
            **send_kwargs,
        )

    def delete_all_pages(self, **kwargs: object) -> None:
        """Delete all pages."""

        def _data_callback(response: Response) -> None:
            info = response.info
            if isinstance(info, dict) and "type" in info and info["type"] == "page":
                # Block slist signals whilst updating
                self.get_model().handler_block(self.row_changed_signal)
                self.get_selection().handler_block(self.selection_changed_signal)
                self._block_signals = True
                self.data = []
                self._block_signals = False

                # Unblock slist signals now finished
                self.get_selection().handler_unblock(self.selection_changed_signal)
                self.get_model().handler_unblock(self.row_changed_signal)

                self.renumber()

            if "finished_callback" in kwargs:
                cast("Callable[..., object]", kwargs["finished_callback"])()

        page_ids = [row[2] for row in self.data]
        send_kwargs = kwargs.copy()
        if "finished_callback" in send_kwargs:
            del send_kwargs["finished_callback"]
        self.thread.send(
            "delete_pages",
            {"page_ids": page_ids},
            data_callback=_data_callback,
            **send_kwargs,
        )

    def _reorder_data(
        self, page_ids: list[int], new_pages: list[tuple[int, object, int]]
    ) -> None:
        """Reorder self.data to match the worker's new ordering after a drag."""
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        rows = [list(row) for row in self.data]
        moved = {row[2]: row for row in rows if row[2] in page_ids}
        self.data = [row for row in rows if row[2] not in moved]
        for pos, _thumb, pid in new_pages:
            self.data.insert(pos, moved[pid])

        # Page numbers are always consecutive 1..n
        self.renumber()

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

        self.get_selection().unselect_all()
        self.select([i for i, row in enumerate(self.data) if row[2] in moved])

    def reorder_pages(
        self, page_ids: list[int], dest: int, how: Gtk.TreeViewDropPosition
    ) -> None:
        """Reorder the given pages to the given position by drag-and-drop."""

        def _data_callback(response: Response) -> None:
            info = response.info
            if isinstance(info, dict) and "type" in info and info["type"] == "page":
                self._reorder_data(page_ids, info["new_pages"])

        # A drop during a reorder must not delete the just-moved pages, so
        # deletion is suppressed for the duration of the drag. NOTE: the flag
        # is deliberately NOT cleared here, in _data_callback or in
        # delete_selection: the worker reorder response (which updates self.data)
        # can be delivered on the main thread before the drag has fully ended.
        # Clearing the flag on any of those paths would let a stray deletion
        # remove the just-moved page from the database while self.data still
        # holds it, making a subsequent save fail with "Page id ... not found".
        # Instead delete_selection just returns (leaving the flag set) for the
        # duration of the drag, and _on_drag_end clears it once the drag is over.
        self._suppress_delete = True
        self.thread.send(
            "reorder_pages",
            {"page_ids": page_ids, "dest": dest, "how": how},
            data_callback=_data_callback,
        )

    def _on_drag_prepare(
        self, _source: Gtk.DragSource, _x: float, _y: float
    ) -> Gdk.ContentProvider | None:
        """Start an internal row drag when at least one page is selected."""
        if not self.get_selected_indices():
            return None
        self._internal_drag = True
        return Gdk.ContentProvider.new_for_value("scantpaper-rows")

    def _on_rows_accept(self, _target: Gtk.DropTarget, _drop: Gdk.Drop) -> bool:
        """Accept only our own row drags, not external text drops."""
        return bool(self._internal_drag)

    def _on_drop_rows(
        self, _target: Gtk.DropTarget, _value: str, x: float, y: float
    ) -> bool:
        """Reorder the dragged pages at the drop position."""
        rows = self.get_selected_indices()
        if not rows:
            return False

        row = self.get_dest_row_at_pos(int(x), int(y))
        path, how = None, None
        if row:
            path, how = row
            if path is not None:
                path = path.to_string()

        dest = len(self.data)
        if path is not None:
            dest = int(path)
            if how in (
                Gtk.TreeViewDropPosition.AFTER,
                Gtk.TreeViewDropPosition.INTO_OR_AFTER,
            ):
                dest += 1

        page_ids = [cast("int", self.data[i][2]) for i in rows]
        self.reorder_pages(page_ids, dest, how)
        return True

    def _on_drop_files(
        self, _target: Gtk.DropTarget, value: Gdk.FileList, _x: float, _y: float
    ) -> bool:
        """Import the files that were dropped onto the thumbnail list."""
        paths = [gio_file.get_uri() for gio_file in value.get_files()]
        self.import_files(paths=paths)
        return True

    def _on_drag_end(
        self, _source: Gtk.DragSource, _drag: Gdk.Drag, _delete_data: object
    ) -> None:
        """Clear the drag state and any leftover reorder suppression.

        The signal passes whether the drop was a move (delete_data), which is
        ignored: reordering never deletes the dragged pages.
        """
        self._internal_drag = False
        self._suppress_delete = False

    def delete_selection_extra(self, **kwargs: object) -> None:
        """Delete the current selection."""
        page = self.get_selected_indices()
        npages = len(page)
        ids = (str(self.data[x][2]) for x in page)
        logger.info("Deleting page ids %s", " ".join(ids))
        if self.selection_changed_signal is not None:
            self.get_selection().handler_block(self.selection_changed_signal)

        def _after_delete() -> None:
            # Select nearest page to last current page
            if self.data:
                old_selection = page[0]

                # Select just the first one
                new_sel = [page[0]]
                new_sel[0] = min(new_sel[0], len(self.data) - 1)

                self.select(new_sel)

                # If the index hasn't changed, the signal won't have emitted, so do it
                # manually. Even if the index has changed, if it has the focus, the
                # signal is still not fired (is this a bug in gtk+-3?), so do it here.
                if old_selection == new_sel[0] or self.has_focus():
                    self.get_selection().emit("changed")

            # No pages left, and having blocked the selection_changed_signal,
            # we've got to clear the image
            else:
                self.get_selection().emit("changed")

            logger.info("Deleted %s pages", npages)

            if "finished_callback" in kwargs:
                cast("Callable[..., object]", kwargs["finished_callback"])()

        self.delete_selection(finished_callback=_after_delete)

        if self.selection_changed_signal is not None:
            self.get_selection().handler_unblock(self.selection_changed_signal)

    def save_session(self, filename: str) -> None:
        """Write the session db to a file."""
        self.thread.save_as(filename)
        self.thread.mark_all_pages_saved()
        logger.info("Saved document as %s", filename)

    def _remove_temp_session_db(self) -> None:
        """Remove the temporary scratch database and its sidecars."""
        base = str(self.dir) + ".sdb"
        for suffix in ("", "-wal", "-shm"):
            pathlib.Path(base + suffix).unlink(missing_ok=True)

    @staticmethod
    def _finish_session_open(finished_callback: object) -> None:
        """Signal completion to an import flow that opened this session."""
        if finished_callback:
            cast("Callable[[Response | None], None]", finished_callback)(None)

    def open_session(self, **kwargs: object) -> None:
        """Open session file."""
        if "db" not in kwargs:
            if kwargs["error_callback"]:
                cast("Callable[..., object]", kwargs["error_callback"])(
                    None, "Open file", "Error: session file not defined"
                )
            return

        db = pathlib.Path(cast("str", kwargs["db"]))
        if not db.is_file():
            if kwargs["error_callback"]:
                cast("Callable[..., object]", kwargs["error_callback"])(
                    None, "Open file", f"Error: Unable to read {db}"
                )
            return

        self.thread.close()
        self._remove_temp_session_db()

        # Block the row-changed signal for the entire async sequence
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        error_callback = kwargs.get("error_callback")
        finished_callback = kwargs.get("finished_callback")

        def on_open(_response: Response) -> None:
            self.thread.send(
                "page_number_table",
                finished_callback=on_table,
                error_callback=on_error,
            )

        def on_table(response: Response) -> None:
            self._unblock_row_changed()
            self.data = response.info
            self.renumber()
            logger.info("Opened document %s", db)
            logger.info("Found %i pages", len(self.data))
            self.select(0)
            self._finish_session_open(finished_callback)

        def on_error(response: Response) -> None:
            self._unblock_row_changed()
            if error_callback:
                cast("Callable[..., object]", error_callback)(
                    None, "Open file", response.status
                )

        self.thread.send(
            "open",
            db,
            finished_callback=on_open,
            error_callback=on_error,
        )

    def _unblock_row_changed(self) -> None:
        """Re-enable the row-changed signal if it was blocked."""
        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

    def renumber(self) -> None:
        """Renumber pages so that page numbers are consecutive 1..n."""
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        for i, row in enumerate(self.data):
            row[0] = i + 1

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

    def get_page_index(
        self, page_range: str, error_callback: Callable[..., object]
    ) -> list[int]:
        """Return array index of pages depending on which radiobutton is active."""
        index = []
        if page_range == "all":
            if self.data:
                return list(range(len(self.data)))
            error_callback(None, "Get page", _("No pages to process"))
        elif page_range == "selected":
            index = self.get_selected_indices()
            if len(index) == 0:
                error_callback(None, "Get page", _("No pages selected"))
        return index

    def _note_callbacks(self, kwargs: dict[str, object]) -> None:
        """Create the mark_saved callback if necessary."""
        # File in which to store the process ID so that it can be killed if necessary
        kwargs["pidfile"] = self.create_pidfile(kwargs)
        kwargs["dir"] = self.dir


def _save_method_generator(method_name: str) -> Callable[..., None]:
    def _generic_method(
        self: BaseDocument, _method_name: str, **kwargs: object
    ) -> None:
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        method = getattr(self.thread, _method_name)
        method(**kwargs)

    return lambda self, **kwargs: _generic_method(self, method_name, **kwargs)


def _modify_method_generator(method_name: str) -> Callable[..., None]:
    def _generic_method(
        self: BaseDocument, _method_name: str, **kwargs: object
    ) -> None:
        kwargs["data_callback"] = partial(self.data_callback, options=kwargs)
        self._note_callbacks(kwargs)
        method = getattr(self.thread, _method_name)
        method(**kwargs)

    return lambda self, **kwargs: _generic_method(self, method_name, **kwargs)


for method_name_ in [
    "save_pdf",
    "save_djvu",
    "save_tiff",
    "save_image",
    "save_text",
    "save_hocr",
]:
    setattr(BaseDocument, method_name_, _save_method_generator(method_name_))


for method_name_ in [
    "rotate",
    "analyse",
    "threshold",
    "brightness_contrast",
    "negate",
    "unsharp",
    "crop",
    "tesseract",
    "user_defined",
]:
    setattr(BaseDocument, method_name_, _modify_method_generator(method_name_))

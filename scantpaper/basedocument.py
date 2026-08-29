"Base document methods"

import logging
import os
import pathlib
import queue
import re
import shutil
import signal
import tempfile
import weakref
from collections import defaultdict
from functools import partial

import gi
from docthread import INSERT_AT_START, DocThread
from helpers import _weak_callback, slurp
from i18n import _
from simplelist import SimpleList

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # pylint: disable=wrong-import-position

ID_PAGE = 1
ID_URI = 0

logger = logging.getLogger(__name__)


class BaseDocument(SimpleList):
    "a Document is a simple list of pages, backed by SQLite"

    jobs_completed = 0
    jobs_total = 0

    def __init__(self, **kwargs):
        columns = {"#": "int", _("Thumbnails"): "pixbuf", "Page ID": "hint"}
        super().__init__(**columns)
        self.thread = DocThread(**kwargs)
        self.thread.register_callback("display", "after", "data")
        self.thread.register_callback("updated_page", "after", "data")
        self._finalizer = weakref.finalize(
            self, self.thread._cleanup_thread, self.thread.requests
        )
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_headers_visible(False)
        self.set_reorderable(True)
        self.dir = None
        self.clipboard = None
        self._context = {}
        for key, val in kwargs.items():
            setattr(self, key, val)
        if not self.dir:
            self.dir = self.thread._dir
        if isinstance(self.dir, str):
            self.dir = pathlib.Path(self.dir)

        dnd_source = Gtk.TargetEntry.new(
            "Glib::Scalar",  # some string representing the drag type
            Gtk.TargetFlags.SAME_WIDGET,
            ID_PAGE,  # some app-defined integer identifier
        )
        self.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [dnd_source],
            Gdk.DragAction.COPY | Gdk.DragAction.MOVE,
        )
        dnd_dest = Gtk.TargetEntry.new(
            "text/uri-list",  # some string representing the drag type
            0,  # flags
            ID_URI,  # some app-defined integer identifier
        )
        self.drag_dest_set(
            Gtk.DestDefaults.DROP
            | Gtk.DestDefaults.MOTION
            | Gtk.DestDefaults.HIGHLIGHT,
            [dnd_source, dnd_dest],
            Gdk.DragAction.COPY | Gdk.DragAction.MOVE,
        )

        def drag_data_get_callback(_tree, _context, sel, _info, _time, _user_data=None):
            # set dummy data which we'll ignore and use selected rows
            sel.set(sel.get_target(), 8, [])  # 8 == string format

        self.connect("drag-data-get", drag_data_get_callback)
        self.connect("drag-data-delete", _weak_callback(self, "delete_selection"))
        self.connect("drag-data-received", drag_data_received_callback)

        def drag_drop_callback(tree, context, _x, _y, when):
            "Callback for dropped signal"
            targets = tree.drag_dest_get_target_list()
            target = tree.drag_dest_find_target(context, targets)
            if target:
                tree.drag_get_data(context, target, when)
                return True

            return False

        self.connect("drag-drop", drag_drop_callback)

        # Set the page number to be editable
        self.set_column_editable(0, True)
        self.row_changed_signal = self.get_model().connect(
            "row-changed", _weak_callback(self, "_on_row_changed")
        )
        self.selection_changed_signal = self.get_selection().connect(
            "changed", _weak_callback(self, "_on_selection_changed")
        )

        # selection changed signal is not being blocked correctly, so add an extra flag
        self._block_signals = False

    def _on_row_changed(self, _self, _path, _iter):
        "Set-up the callback when the page number has been edited."
        # Note uuids for selected pages
        selection = self.get_selected_indices()
        uuids = []
        for i in selection:
            uuids.append(self.data[i][2])

        self.get_model().handler_block(self.row_changed_signal)

        # Move the edited page to the position given by its number
        edited = None
        for i, row in enumerate(self.data):
            if row[0] != i + 1:
                edited = i
                break
        if edited is not None:
            new_position = max(1, min(int(self.data[edited][0]), len(self.data)))
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

    def _on_selection_changed(self, _selection):
        if self._block_signals:
            return
        self.thread.send("set_selection", self.get_selected_indices())

    def set_paper_sizes(self, paper_sizes=None):
        "Set the paper sizes in the manager and worker threads"
        self.thread.send("set_paper_sizes", paper_sizes)

    def cancel(self, cancel_callback, process_callback=None):
        "Kill all running processes"
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

    def create_pidfile(self, options):
        "create file in which to store the PID"
        options = defaultdict(None, options)
        try:
            # SIM115: the pidfile handle escapes to the thread's running_pids
            # registry so that cancel() can later read the spawn pid from it.
            pidfile = tempfile.TemporaryFile(  # noqa: SIM115  # pylint: disable=consider-using-with
                dir=self.dir, suffix=".pid", mode="w+t"
            )
        except (OSError, PermissionError) as err:
            logger.error("Caught error writing to %s: %s", self.dir, err)
            if "error_callback" in options:
                options["error_callback"](
                    options.get("page"),
                    "create PID file",
                    f"Error: unable to write to {self.dir}.",
                )
            return None
        if getattr(self.thread, "running_pids", None) is not None:
            with self.thread.lock:
                self.thread.running_pids[pidfile] = pidfile
        return pidfile

    def data_callback(self, response, options, post_process=None):
        "add a page from a worker response, then log any errors"
        info = response.info
        if info and "type" in info and info["type"] == "page":
            self.add_page(*info["row"], **info)
            if post_process:
                post_process(info["row"][2], options)
        elif "logger_callback" in options:
            options["logger_callback"](response)

    def find_page_by_uuid(self, uid):
        "return page index given uuid"
        if uid is None:
            logger.error("find_page_by_uuid() called with None")
            return None

        for i, row in enumerate(self.data):
            if uid == row[2]:
                return i
        return None

    def _find_page_by_ref(self, uid):
        i = self.find_page_by_uuid(uid)
        if i is None:
            logger.error("Requested page %s does not exist.", uid)
            raise ValueError(f"Requested page {uid} does not exist.")
        return i

    def add_page(self, number, thumb, page_id, **kwargs):
        "Add a new page to the document"
        ref = kwargs.get("insert-after", kwargs.get("replace"))
        i = None
        if ref is not None:
            if ref == INSERT_AT_START:
                i = -1
            else:
                i = self._find_page_by_ref(ref)

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

        else:
            if "replace" in kwargs:
                old_id = self.data[i][2]
                self.data[i] = [number, thumb, page_id]
                new_index = i
                logger.info(
                    "Replaced page id %s at page number %s with page id %s",
                    old_id,
                    i + 1,
                    page_id,
                )
            elif "insert-after" in kwargs:
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

    def _renumber_after_add(self, i, number):
        "Renumber after adding a page, unless it is an in-order append"
        if i is not None or number != len(self.data):
            self.renumber()

    def cut_selection(self, **kwargs):
        "Cut the selection"
        data = self.copy_selection()
        self.delete_selection_extra(**kwargs)
        return data

    def copy_selection(self):
        "Copy the selection"
        selection = self.get_selected_indices()
        logger.debug("copy_selection %s", selection)
        if selection == []:
            return None
        data = []
        for index in selection:
            data.append([self.data[index][0], self.data[index][1], self.data[index][2]])
        logger.info("Copied %s pages", len(data))
        return data

    def paste_selection(self, **kwargs):
        "Paste the selection"

        # Block row-changed signal so that the list can be updated before the sort
        # takes over.
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        def _post_paste_logic(dest):
            # Renumber the newly pasted rows positionally
            self.renumber()
            self.get_model().emit(
                "row-changed", Gtk.TreePath(), self.get_model().get_iter_first()
            )

            # Select the new pages
            if kwargs.get("select_new_pages"):
                selection = list(range(dest, dest + len(kwargs["data"])))

                self.get_selection().unselect_all()
                self.select(selection)

            if self.row_changed_signal is not None:
                self.get_model().handler_unblock(self.row_changed_signal)

            logger.info("Pasted %s pages at position %s", len(kwargs["data"]), dest)
            if "finished_callback" in kwargs:
                kwargs["finished_callback"]()

        dest = None
        if kwargs.get("dest") is None:
            dest = len(self.data)

            def _data_callback(response):
                logger.debug("extend _data_callback(%s)", response)
                info = response.info
                if info and "type" in info and info["type"] == "page":
                    self.data.extend(info["new_pages"])
                    _post_paste_logic(dest)

            self.thread.send(
                "clone_pages",
                {"page_ids": [row[2] for row in kwargs["data"]], "dest": dest},
                data_callback=_data_callback,
            )
        else:
            dest = int(kwargs["dest"])
            if kwargs["how"] in (
                Gtk.TreeViewDropPosition.AFTER,
                Gtk.TreeViewDropPosition.INTO_OR_AFTER,
            ):
                dest += 1

            def _data_callback(response):
                logger.debug("insert _data_callback(%s)", response)
                info = response.info
                if info and "type" in info and info["type"] == "page":
                    for row in info["new_pages"]:
                        self.data.insert(dest, row)
                    _post_paste_logic(dest)

            self.thread.send(
                "clone_pages",
                {"page_ids": [row[2] for row in kwargs["data"]], "dest": dest},
                data_callback=_data_callback,
            )

    def delete_selection(self, _self=None, context=None, **kwargs):
        "Delete the selected pages"

        # The drag-data-delete callback seems to be fired twice. Therefore, create
        # a hash of the context hashes and ignore the second drop. There must be a
        # less hacky way of solving this. FIXME
        if context is not None:
            if context in self._context:
                self._context = {}
                return

            self._context[context] = 1

        def _data_callback(response):
            info = response.info
            if info and "type" in info and info["type"] == "page":
                # Reverse the rows in order not to invalid the iters
                if paths:
                    for path in reversed(paths):
                        itr = model.get_iter(path)
                        model.remove(itr)
                self.renumber()

            if "finished_callback" in kwargs:
                kwargs["finished_callback"]()

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

    def delete_all_pages(self, **kwargs):
        "Delete all pages"

        def _data_callback(response):
            info = response.info
            if info and "type" in info and info["type"] == "page":
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
                kwargs["finished_callback"]()

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

    def delete_selection_extra(self, **kwargs):
        "wrapper for delete_selection()"
        page = self.get_selected_indices()
        npages = len(page)
        ids = (str(self.data[x][2]) for x in page)
        logger.info("Deleting page ids %s", " ".join(ids))
        if self.selection_changed_signal is not None:
            self.get_selection().handler_block(self.selection_changed_signal)

        def _after_delete():
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
                kwargs["finished_callback"]()

        self.delete_selection(finished_callback=_after_delete)

        if self.selection_changed_signal is not None:
            self.get_selection().handler_unblock(self.selection_changed_signal)

    def save_session(self, filename):
        "copy session db to a file"
        self.thread.save_as(filename)
        logger.info("Saved document as %s", filename)

    def open_session(self, **kwargs):
        "open session file"
        if "db" not in kwargs:
            if kwargs["error_callback"]:
                kwargs["error_callback"](
                    None, "Open file", "Error: session file not defined"
                )
            return

        db = pathlib.Path(kwargs["db"])
        self.thread.close()
        try:
            shutil.copy(db, self.dir.name + ".sdb")
        except OSError:
            if kwargs["error_callback"]:
                kwargs["error_callback"](
                    None, "Open file", f"Error: Unable to read {db}"
                )
            return

        # Block the row-changed signal for the entire async sequence
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        error_callback = kwargs.get("error_callback")

        def on_open(_response):
            self.thread.send(
                "page_number_table",
                finished_callback=on_table,
                error_callback=on_error,
            )

        def on_table(response):
            if self.row_changed_signal is not None:
                self.get_model().handler_unblock(self.row_changed_signal)
            self.data = response.info
            self.renumber()
            logger.info("Opened document %s", db)
            logger.info("Found %i pages", len(self.data))
            self.select(0)

        def on_error(response):
            if self.row_changed_signal is not None:
                self.get_model().handler_unblock(self.row_changed_signal)
            if error_callback:
                error_callback(None, "Open file", response.status)

        self.thread.send(
            "open",
            db,
            finished_callback=on_open,
            error_callback=on_error,
        )

    def renumber(self):
        "Renumber pages so that page numbers are consecutive 1..n"
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        for i, row in enumerate(self.data):
            row[0] = i + 1

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

    def get_page_index(self, page_range, error_callback):
        "return array index of pages depending on which radiobutton is active"
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

    def _note_callbacks(self, kwargs):
        "create the mark_saved callback if necessary"
        # File in which to store the process ID so that it can be killed if necessary
        kwargs["pidfile"] = self.create_pidfile(kwargs)
        kwargs["dir"] = self.dir


def _save_method_generator(method_name):
    def _generic_method(self, _method_name, **kwargs):
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        method = getattr(self.thread, _method_name)
        method(**kwargs)

    return lambda self, **kwargs: _generic_method(self, method_name, **kwargs)


def _modify_method_generator(method_name):
    def _generic_method(self, _method_name, **kwargs):
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


def drag_data_received_callback(tree, context, xpos, ypos, data, info, time):
    "callback to receive DnD data"

    # This callback is fired twice, seemingly once for the drop flag,
    # and once for the copy flag,
    # or possible once for the new data and once for the old data.
    # If the drop flag is disabled, the URI
    # drop does not work. If the copy flag is disabled, the drag-with-copy
    # does not work. Therefore if copying, create a hash of the drop times
    # and ignore the second drop.
    # https://stackoverflow.com/questions/48469655/drop-file-in-python-gui-gtk
    if hasattr(tree, "drops") and time in tree.drops:
        tree.drops = {}
        Gtk.drag_finish(context, True, False, time)
        return

    if not hasattr(tree, "drops"):
        tree.drops = {}
    tree.drops[time] = 1

    if info == ID_URI:
        uris = data.get_uris()
        for uri in uris:
            uri = re.sub(
                r"^file://", r"", uri, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
            )

        tree.import_files(paths=uris)
        Gtk.drag_finish(context, True, False, time)

    elif info == ID_PAGE:
        rows = tree.get_selected_indices()
        if not rows:
            return

        row = tree.get_dest_row_at_pos(xpos, ypos)
        path, how = None, None
        if row:
            path, how = row
            if path is not None:
                path = path.to_string()

        data = tree.copy_selection()

        # pasting without updating the selection
        # in order not to defeat the finish() call below.
        tree.paste_selection(data=data, dest=path, how=how)
        Gtk.drag_finish(context, True, False, time)

    else:
        context.abort()

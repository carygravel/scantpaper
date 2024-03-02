"Base document methods"
from collections import defaultdict
import uuid
import re
import os
import logging
import tempfile
import queue
import signal
import tarfile
import gi
from simplelist import SimpleList
from i18n import _
from docthread import DocThread
from bboxtree import Bboxtree
from page import Page

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # pylint: disable=wrong-import-position

THUMBNAIL = 100  # pixels
ID_PAGE = 1
ID_URI = 0
INFINITE = -1

logger = logging.getLogger(__name__)

SimpleList.add_column_type(hstring={"type": object, "attr": "hidden"})


class BaseDocument(SimpleList):
    "a Document is a simple list of pages"
    jobs_completed = 0
    jobs_total = 0
    uuid_object = uuid.uuid1()
    # Default thumbnail sizes
    heightt = THUMBNAIL
    widtht = THUMBNAIL
    selection_changed_signal = None
    paper_sizes = {}

    def _on_row_changed(self, _path, _iter, _data):
        "Set-up the callback when the page number has been edited."
        # Note uuids for selected pages
        selection = self.get_selected_indices()
        uuids = []
        for i in selection:
            uuids.append(self.data[i][2].uuid)

        self.get_model().handler_block(self.row_changed_signal)

        # Sort pages
        self._manual_sort_by_column(0)

        # And make sure there are no duplicates
        self.renumber()
        self.get_model().handler_unblock(self.row_changed_signal)

        # Select the renumbered pages via uuid
        selection = []
        for i in uuids:
            selection.append(self.find_page_by_uuid(i))
        self.select(selection)

    def __init__(self, **options):
        super().__init__(
            {"#": "int", _("Thumbnails"): "pixbuf", "Page Data": "hstring"}
        )
        self.thread = DocThread()
        self.thread.register_callback("mark_saved", "before", "finished")
        self.thread.register_callback("display", "before", "finished")
        self.thread.register_callback("updated_page", "after", "data")
        self.thread.start()
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_headers_visible(False)
        self.set_reorderable(True)
        self.dir = None
        for key, val in options.items():
            setattr(self, key, val)

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

        def drag_data_get_callback(_tree, _context, sel):
            # set dummy data which we'll ignore and use selected rows
            setattr(sel, sel.get_target(), [])

        self.connect("drag-data-get", drag_data_get_callback)
        self.connect("drag-data-delete", self.delete_selection)
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
            "row-changed", self._on_row_changed
        )

        GLib.timeout_add(100, self._page_request_handler)

    def _page_request_handler(self):
        "handle page requests"
        if not self.thread.page_requests.empty():
            uid = self.thread.page_requests.get()

            if uid == "cancel":
                return GLib.SOURCE_CONTINUE

            page = self.find_page_by_uuid(uid)
            self.thread.pages.put(self.data[page][2])
        return GLib.SOURCE_CONTINUE

    def set_paper_sizes(self, paper_sizes=None):
        "Set the paper sizes in the manager and worker threads"
        self.paper_sizes = paper_sizes
        self.thread.send("set_paper_sizes", paper_sizes)

    def cancel(self, cancel_callback, process_callback=None):
        "Kill all running processes"
        with self.thread.lock:  # FIXME: move most of this to basethread.py
            # Empty process queue first to stop any new process from starting
            logger.info("Emptying process queue")
            try:
                while self.thread.requests.get(False):
                    pass
            except queue.Empty:
                pass
            try:
                while self.thread.responses.get(False):
                    pass
            except queue.Empty:
                pass
            try:
                while self.thread.page_requests.get(False):
                    pass
            except queue.Empty:
                pass
            try:
                while self.thread.pages.get(False):
                    pass
            except queue.Empty:
                pass
            self.thread.page_requests.put("cancel")

            # jobs_completed = 0
            # jobs_total = 0

            # Then send the thread a cancel signal
            # to stop it going beyond the next break point
            self.thread.cancel = True

            # Kill all running processes in the thread
            for pidfile in self.thread.running_pids:
                pid = slurp(pidfile)
                if pid != "":
                    if pid == 1:
                        continue
                    if process_callback is not None:
                        process_callback(pid)

                    logger.info("Killing PID %s", pid)

                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    del self.thread.running_pids[pidfile]

        # Add a cancel request to ensure the reply is not blocked
        logger.info("Requesting cancel")
        self.thread.send("cancel", finished_callback=cancel_callback)

    def create_pidfile(self, options):
        "create file in which to store the PID"
        options = defaultdict(None, options)
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.dir, suffix=".pid", delete=False
            ) as pidfile:
                return pidfile.name
        except (PermissionError, IOError) as err:
            logger.error("Caught error writing to %s: %s", self.dir, err)
            if "error_callback" in options:
                options["error_callback"](
                    options.get("page"),
                    "create PID file",
                    f"Error: unable to write to {self.dir}.",
                )
        return None

    def index_for_page(self, num, min_page=None, max_page=None, direction=1):
        "does the given page exist?"
        if len(self.data) < 1:
            return INFINITE
        if min_page is None:
            min_page = 0

        if max_page is None:
            max_page = num - 1

        start = min_page
        end = max_page + 1
        step = 1
        if direction < 0:
            step = -step
            start = max_page
            if start > len(self.data) - 1:
                start = len(self.data) - 1
            end = min_page - 1

        i = start
        while (i <= end and i < len(self.data)) if step > 0 else i > end:
            if self.data[i][0] == num:
                return i

            i += step

        return INFINITE

    def pages_possible(self, start, step):
        "Check how many pages could be scanned"
        i = len(self.data) - 1

        # Empty document and negative step
        if i < 0 and step < 0:
            num = -start / step
            return num if num == int(num) else int(num) + 1

        # Empty document, or start page after end of document, allow infinite pages
        if i < 0 or (step > 0 and self.data[i][0] < start):
            return INFINITE

        # scan in appropriate direction, looking for position for last page
        num = 0
        max_page_number = self.data[i][0]
        while True:
            # fallen off top of index
            if step > 0 and start + num * step > max_page_number:
                return INFINITE

            # fallen off bottom of index
            if step < 0 and start + num * step < 1:
                return num

            # Found page
            i = self.index_for_page(start + num * step, 0, start - 1, step)
            if i > INFINITE:
                return num

            num += 1

    def find_page_by_uuid(self, uid):
        "return page index given uuid"
        if uid is None:
            logger.error("find_page_by_uuid() called with None")
            return None

        for i, row in enumerate(self.data):
            if str(uid) == str(row[2].uuid):
                return i
        return None

    def _find_page_by_ref(self, ref):
        if ref:
            for key in ["replace", "insert-after"]:
                if key in ref and ref[key]:
                    uid = ref[key]
                    i = self.find_page_by_uuid(uid)
                    if i is None:
                        logger.error("Requested page %s does not exist.", uid)
                        return None
                    return i
        return None

    def add_page(self, new_page, ref):
        "Add a new page to the document"
        pagenum = None

        # FIXME: This is really hacky to allow import_scan() to specify the page number
        if not isinstance(ref, dict):
            pagenum = ref
            ref = None

        i = self._find_page_by_ref(ref)

        # Block the row-changed signal whilst adding the scan (row) and sorting it.
        if self.row_changed_signal:
            self.get_model().handler_block(self.row_changed_signal)

        xresolution, yresolution, units = new_page.get_resolution(self.paper_sizes)
        thumb = new_page.get_pixbuf_at_scale(self.heightt, self.widtht)

        # Add to the page list
        if i is None:
            if pagenum is None:
                pagenum = len(self.data) + 1
            self.data.append([pagenum, thumb, new_page])
            logger.info(
                "Added %s (%s) at page %s with resolution %s,%s",
                new_page.filename,
                new_page.uuid,
                pagenum,
                xresolution,
                yresolution,
            )

        else:
            if "replace" in ref:
                pagenum = self.data[i][0]
                logger.info(
                    "Replaced %s (%s) at page %s with %s (%s), resolution %s,%s",
                    self.data[i][2].filename,
                    self.data[i][2].uuid,
                    pagenum,
                    new_page.filename,
                    new_page.uuid,
                    xresolution,
                    yresolution,
                )
                self.data[i][1] = thumb
                self.data[i][2] = new_page

            elif "insert-after" in ref:
                pagenum = self.data[i][0] + 1
                self.data.insert(i + 1, [pagenum, thumb, new_page])
                logger.info(
                    "Inserted %s (%s) at page %s with resolution %s,%s,%s",
                    new_page.filename,
                    new_page.uuid,
                    pagenum,
                    xresolution,
                    yresolution,
                    units,
                )

        # Block selection_changed_signal
        # to prevent its firing changing pagerange to all
        if self.selection_changed_signal:
            self.get_selection().handler_block(self.selection_changed_signal)

        self.get_selection().unselect_all()
        self._manual_sort_by_column(0)

        if self.selection_changed_signal:
            self.get_selection().handler_unblock(self.selection_changed_signal)

        if self.row_changed_signal:
            self.get_model().handler_unblock(self.row_changed_signal)

        # Due to the sort, must search for new page
        page_selection = [0]

        # page_selection[0] < len(self.data) - 1 needed to prevent infinite loop in case of
        # error importing.
        while (
            page_selection[0] < len(self.data) - 1
            and self.data[page_selection[0]][0] != pagenum
        ):
            page_selection[0] += 1

        self.select(page_selection)
        # if "display" in callback[process_uuid]:
        #     callback[process_uuid]["display"](self.data[i][2])

        return page_selection[0]

    def _remove_corrupted_pages(self):
        "remove corrupt pages"
        i = 0
        while i < len(self.data):
            if self.data[i][2] is None:
                del self.data[i]

            else:
                i += 1

    def _manual_sort_by_column(self, sortcol):
        """Helpers:

        Manual one-time sorting of the simplelist's data"""
        self._remove_corrupted_pages()

        # The sort function depends on the column type
        #     sortfuncs = {
        #     object : compare_text_col,
        #     str : compare_text_col,
        #     int    : compare_numeric_col,
        #     float : compare_numeric_col,
        # }

        # Remember, this relies on the fact that simplelist keeps model
        # and view column indices aligned.
        # sortfunc = sortfuncs[ self.get_model().get_column_type(sortcol) ]

        # Deep copy the tied data so we can sort it.
        # Otherwise, very bad things happen.
        data = [list(x) for x in self.data.model]
        data = sorted(data, key=lambda row: row[sortcol])
        self.data = data

    def cut_selection(self):
        "Cut the selection"
        data = self.copy_selection(False)
        self._delete_selection_extra()
        return data

    def copy_selection(self, clone):
        "Copy the selection"
        selection = self.get_selected_indices()
        if selection == []:
            return None
        data = []
        for index in selection:
            page = self.data[index]
            data.append([page[0], page[1], page[2].clone(clone)])

        logger.info("Copied %s%s pages", "and cloned " if clone else "", len(data))
        return data

    def paste_selection(self, data, path, how, select_new_pages=False):
        "Paste the selection"

        # Block row-changed signal so that the list can be updated before the sort
        # takes over.
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        dest = None
        if path is not None:
            if how in ("after", "into-or-after"):
                path += 1
            self.data.insert(path, data)
            dest = path

        else:
            dest = len(self.data)
            self.data.append(data)

        # Renumber the newly pasted rows
        start = None
        if dest == 0:
            start = 1

        else:
            start = self.data[dest - 1][0] + 1

        for i in range(dest, dest + len(data) - 2):
            self.data[i][0] = start
            start += 1

        # Update the start spinbutton if necessary
        self.renumber()
        self.get_model().emit(
            "row-changed", Gtk.TreePath(), self.get_model().get_iter_first()
        )

        # Select the new pages
        if select_new_pages:
            selection = []
            for _ in range(dest, dest + len(data)):
                selection.append(_)

            self.get_selection().unselect_all()
            self.select(selection)

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

        # self.save_session()
        logger.info("Pasted %s pages at position %s", len(data), dest)

    def delete_selection(self, _context=None):
        "Delete the selected pages"

        # The drag-data-delete callback seems to be fired twice. Therefore, create
        # a hash of the context hashes and ignore the second drop. There must be a
        # less hacky way of solving this. FIXME
        # if context is not None:
        #     if context in self.context:
        #         del self.context
        #         return

        #     self.context[context] = 1

        model, paths = self.get_selection().get_selected_rows()

        # Reverse the rows in order not to invalid the iters
        if paths:
            for path in reversed(paths):
                itr = model.get_iter(path)
                model.remove(itr)

    def _delete_selection_extra(self):
        "wrapper for delete_selection()"
        page = self.get_selected_indices()
        npages = len(page)
        uuids = map(lambda x: str(self.data[x][2].uuid), page)
        logger.info("Deleting %s", " ".join(uuids))
        if self.selection_changed_signal is not None:
            self.get_selection().handler_block(self.selection_changed_signal)

        self.delete_selection()
        if self.selection_changed_signal is not None:
            self.get_selection().handler_unblock(self.selection_changed_signal)

        # Select nearest page to last current page
        if self.data and page:
            old_selection = page[0]

            # Select just the first one
            page = [page[0]]
            if page[0] > len(self.data) - 1:
                page[0] = len(self.data) - 1

            self.select(page)

            # If the index hasn't changed, the signal won't have emitted, so do it
            # manually. Even if the index has changed, if it has the focus, the
            # signal is still not fired (is this a bug in gtk+-3?), so do it here.
            if old_selection == page[0] or self.has_focus():
                self.get_selection().emit("changed")

        elif self.data:
            self.get_selection().unselect_all()

        # No pages left, and having blocked the selection_changed_signal,
        # we've got to clear the image
        else:
            self.get_selection().emit("changed")

        # self.save_session()
        logger.info("Deleted %s pages", npages)

    def scans_saved(self):
        "Check that all pages have been saved"
        for row in self:
            if not row[2].saved:
                return False
        return True

    def _to_png(self, kwargs):
        "convert the given page to png"
        self._note_callbacks(kwargs)
        self.thread.to_png(**kwargs)

    def save_session(self, filename=None, version=None):
        """Dump $self to a file.
        If a filename is given, zip it up as a session file
        Pass version to allow us to mock different session version and to be able to
        test opening old sessions."""
        self._remove_corrupted_pages()
        session, filenamelist = {}, []
        for row in self.data:
            if row[0] not in session:
                session[row[0]] = {}
            session[row[0]]["filename"] = row[2].filename
            filenamelist.append(row[2].filename)
            for key in row[2].keys():
                if key != "filename":
                    session[row[0]][key] = row[2][key]

        filenamelist.append(os.path.join(self.dir, "session"))
        selection = self.get_selected_indices()
        session["selection"] = selection
        if version is not None:
            session["version"] = version
        # store(session, os.path.join(self.dir, "session"))
        if filename is not None:
            with tarfile.TarFile(filename, "w") as tar:
                for file in filenamelist:
                    tar.add(file)
            for row in self.data:
                row[2].saved = True

    def open_session_file(self, options):
        "open session file"
        if "info" not in options:
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", "Error: session file not supplied."
                )

            return

        with tarfile.open(options["info"], True) as tar:
            filenamelist = tar.list_files()
            sessionfile = [x for x in filenamelist if re.search(r"\/session$", x)]
            sesdir = os.path.join(self.dir, os.path.dirname(sessionfile[0]))
            for filename in filenamelist:
                tar.extract_file(
                    filename, os.path.join(sesdir, os.path.basename(filename))
                )

        self.open_session(dir=sesdir, delete=True, **options)
        if options["finished_callback"]:
            options["finished_callback"]()

    def open_session(self, options):
        "open session file"
        if "dir" not in options:
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", "Error: session folder not defined"
                )

            return

        sessionfile = os.path.join(options["dir"], "session")
        if not os.access(sessionfile, os.R_OK):
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", f"Error: Unable to read {sessionfile}"
                )

            return

        # sessionref = retrieve(sessionfile)
        sessionref = sessionfile  # until we've figured out how this is going to work

        session = sessionref

        # hocr -> bboxtree
        if "version" not in sessionref:
            logger.info("Restoring pre-2.8.1 session file.")
            for key in sessionref.keys():
                if isinstance(sessionref[key], dict) and "hocr" in sessionref[key]:
                    tree = Bboxtree()
                    if re.search(
                        r"<body>[\s\S]*<\/body>",
                        sessionref[key]["hocr"],
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        tree.from_hocr(sessionref[key]["hocr"])

                    # else:
                    #     tree.from_text(sessionref[key]["hocr"])

                    sessionref[key]["text_layer"] = tree.json()
                    del sessionref[key]["hocr"]

        else:
            logger.info(
                "Restoring v%s->%s session file.", sessionref, session["version"]
            )

        # Block the row-changed signal whilst adding the scan (row) and sorting it.
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        selection = session["selection"]
        del session["selection"]
        if "version" in session:
            del session["version"]
        for pagenum in sorted(session.keys()):
            # don't reuse session directory

            session[pagenum]["dir"] = self.dir
            session[pagenum]["delete"] = options["delete"]

            # correct the path now that it is relative to the current session dir

            if options["dir"] != self.dir:
                session[pagenum]["filename"] = os.path.join(
                    options["dir"], os.path.basename(session[pagenum]["filename"])
                )

            # Populate the SimpleList
            page = Page(session[pagenum])
            thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
            self.data.append([pagenum, thumb, page])

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

        self.select(selection)

    def renumber(self, start=1, step=1, selection="all"):
        "Renumber pages"
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        if start is not None:
            if step is None:
                step = 1
            if selection is None:
                selection = "all"
            selection = []
            if selection == "selected":
                selection = self.get_selected_indices()

            else:
                selection = range(len(self.data))

            for _ in selection:
                logger.info("Renumbering page %s->%s", self.data[_][0], start)
                self.data[_][0] = start
                start += step

        # If $start and $step are undefined, just make sure that the numbering is
        # ascending.

        else:
            for i in range(1, len(self.data)):
                if self.data[i][0] <= self.data[i - 1][0]:
                    new = self.data[i - 1][0] + 1
                    logger.info("Renumbering page %s->%s", self.data[i][0], new)
                    self.data[i][0] = new

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

    def valid_renumber(self, start, step, selection):
        "Check if $start and $step give duplicate page numbers"
        logger.debug(
            "Checking renumber validity of: start %s, step %s, selection %s",
            start,
            step,
            selection,
        )
        if step == 0 or start < 1:
            return False

        # if we are renumbering all pages, just make sure the numbers stay positive
        if selection == "all":
            if step < 0:
                return (start + (len(self.data) - 1) * step) > 0
            return True

        # Get list of pages not in selection
        selected_pages = self.get_selected_indices()
        all_pages = list(range(len(self.data)))

        # Convert the indices to sets of page numbers
        selected_pages = self._index2page_number(selected_pages)
        all_pages = self._index2page_number(all_pages)
        selected_pages = set(selected_pages)
        all_pages = set(all_pages)
        not_selected_pages = all_pages - selected_pages
        logger.debug("Page numbers not selected: %s", not_selected_pages)

        # Create a set from the current settings
        current = {start + step * i for i in range(len(selected_pages))}
        logger.debug("Current setting would create page numbers: %s", current)

        # Are any of the new page numbers the same as those not selected?
        if len(current.intersection(not_selected_pages)):
            return False
        return True

    def _index2page_number(self, index):
        "helper function to return an array of page numbers given an array of page indices"
        return [self.data[i][0] for i in index]

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

    def set_dir(self, dirname):
        "Set session dir"
        self.dir = dirname

    def _note_callbacks(self, kwargs):
        "create the mark_saved callback if necessary"
        # File in which to store the process ID so that it can be killed if necessary
        kwargs["pidfile"] = self.create_pidfile(kwargs)
        kwargs["dir"] = self.dir
        if "mark_saved" in kwargs and kwargs["mark_saved"]:

            def mark_saved_callback(_data):
                # list_of_pages is frozen,
                # so find the original pages from their uuids
                for page in kwargs["list_of_pages"]:
                    page.saved = True

            kwargs["mark_saved_callback"] = mark_saved_callback


def drag_data_received_callback(
    tree, context, xpos, ypos, data, info, time
):  # pylint: disable=too-many-arguments
    "callback to receive DnD data"
    delete = bool(context.get_actions == "move")

    # This callback is fired twice, seemingly once for the drop flag,
    # and once for the copy flag. If the drop flag is disabled, the URI
    # drop does not work. If the copy flag is disabled, the drag-with-copy
    # does not work. Therefore if copying, create a hash of the drop times
    # and ignore the second drop.

    if not delete:
        if time in tree["drops"]:
            del tree["drops"]
            Gtk.drag_finish(context, True, delete, time)
            return

        tree["drops"][time] = 1

    if info == ID_URI:
        uris = data.get_uris()
        for uri in uris:
            uri = re.sub(
                r"^file://", r"", uri, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
            )

        tree.import_files(paths=uris)
        Gtk.drag_finish(context, True, False, time)

    elif info == ID_PAGE:
        path, how = tree.get_dest_row_at_pos(xpos, ypos)
        if path is not None:
            path = path.to_string()
        rows = tree.get_selected_indices()
        if not rows:
            return
        selection = tree.copy_selection(not delete)

        # pasting without updating the selection
        # in order not to defeat the finish() call below.

        tree.paste_selection(selection, path, how)
        Gtk.drag_finish(context, True, delete, time)

    else:
        context.abort()


def slurp(file):
    "slurp file"
    with open(file, "r", encoding="utf-8") as fhd:
        return fhd.read()

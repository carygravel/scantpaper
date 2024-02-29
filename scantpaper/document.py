"main document IO methods"
from collections import defaultdict
import datetime
import struct
import re
import os
import queue
import tempfile
import uuid
import logging
import signal
import tarfile
from const import POINTS_PER_INCH, ANNOTATION_COLOR
from bboxtree import Bboxtree, unescape_utf8
from docthread import DocThread
from i18n import _
import gi
from simplelist import SimpleList
from page import Page
import netpbm

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)

VERSION = "1"
EMPTY = ""
SPACE = " "
PERCENT = "%"
STRING_FORMAT = 8
_POLL_INTERVAL = 100  # ms
THUMBNAIL = 100  # pixels
_100PERCENT = 100
YEAR = 5
BOX_TOLERANCE = 5
BITS_PER_BYTE = 8
ALL_PENDING_ZOMBIE_PROCESSES = -1
INFINITE = -1
NOT_FOUND = -1
SIGNAL_MASK = 127
MONTHS_PER_YEAR = 12
DAYS_PER_MONTH = 31
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60
ID_URI = 0
ID_PAGE = 1
STRFTIME_YEAR_OFFSET = -1900
STRFTIME_MONTH_OFFSET = -1
MIN_YEAR_FOR_DATECALC = 1970
LAST_ELEMENT = -1
LEFT = 0
TOP = 1
RIGHT = 2
BOTTOM = 3


EXPORT_OK = []

ISODATE_REGEX = r"(\d{4})-(\d\d)-(\d\d)"
TIME_REGEX = r"(\d\d):(\d\d):(\d\d)"
TZ_REGEX = r"([+-]\d\d):(\d\d)"

SimpleList.add_column_type(hstring={"type": object, "attr": "hidden"})


class Document(SimpleList):
    "a Document is a simple list of pages"
    jobs_completed = 0
    jobs_total = 0
    uuid_object = uuid.uuid1()
    # Default thumbnail sizes
    heightt = THUMBNAIL
    widtht = THUMBNAIL
    selection_changed_signal = None
    paper_sizes = {}

    def on_row_changed(self, _path, _iter, _data):
        "Set-up the callback when the page number has been edited."
        # Note uuids for selected pages
        selection = self.get_selected_indices()
        uuids = []
        for i in selection:
            uuids.append(self.data[i][2].uuid)

        self.get_model().handler_block(self.row_changed_signal)

        # Sort pages
        self.manual_sort_by_column(0)

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
            "row-changed", self.on_row_changed
        )

        GLib.timeout_add(100, self.page_request_handler)

    def page_request_handler(self):
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
                if pid != EMPTY:
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

    def import_files(self, **options):
        """To avoid race condtions importing multiple files,
        run get_file_info on all files first before checking for errors and importing"""
        info = []
        options["passwords"] = []
        for i in range(len(options["paths"])):
            self._get_file_info_finished_callback1(i, info, options)

    def _get_file_info_finished_callback1(self, i, infolist, options):
        options = defaultdict(None, options)
        path = options["paths"][i]

        # File in which to store the process ID
        # so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        # uid = _note_callbacks(options)

        def _select_next_finished_callback(response):
            if (
                "encrypted" in response.info
                and response.info["encrypted"]
                and "password_callback" in options
            ):
                options["passwords"].append(options["password_callback"](path))
                if (options["passwords"][i] is not None) and options["passwords"][
                    i
                ] != EMPTY:
                    self._get_file_info_finished_callback1(i, infolist, options)
                return

            infolist.append(response.info)
            if i == len(options["paths"]) - 1:
                self._get_file_info_finished_callback2(infolist, options)

        self.thread.get_file_info(
            path,
            # "pidfile": f"{pidfile}",
            # # "uuid": uid,
            options["passwords"][i] if i < len(options["passwords"]) else None,
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            running_callback=options.get("running_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=_select_next_finished_callback,
        )

    def _get_file_info_finished_callback2_multiple_files(self, info, options):
        for i in info:
            if i["format"] == "session file":
                logger.error(
                    "Cannot open a session file at the same time as another file."
                )
                if options["error_callback"]:
                    options["error_callback"](
                        None,
                        "Open file",
                        _(
                            "Error: cannot open a session file at the same "
                            "time as another file."
                        ),
                    )

                return

            if i["pages"] > 1:
                logger.error(
                    "Cannot import a multipage file at the same time as another file."
                )
                if options["error_callback"]:
                    options["error_callback"](
                        None,
                        "Open file",
                        _(
                            "Error: importing a multipage file at the same "
                            "time as another file."
                        ),
                    )

                return

        finished_callback = options["finished_callback"]
        del options["paths"]
        del options["finished_callback"]
        for i, item in enumerate(info):
            if "metadata_callback" in options:
                options["metadata_callback"](_extract_metadata(item))

            if i == len(info) - 1:
                options["finished_callback"] = finished_callback

            self.import_file(info=item, first_page=1, last_page=1, **options)

    def _get_file_info_finished_callback2(self, info, options):
        if len(info) > 1:
            self._get_file_info_finished_callback2_multiple_files(info, options)

        elif info[0]["format"] == "session file":
            self.open_session_file(info=info[0]["path"], **options)

        else:
            if options.get("metadata_callback"):
                options["metadata_callback"](_extract_metadata(info[0]))

            first_page = 1
            last_page = info[0]["pages"]
            if options.get("pagerange_callback") and last_page > 1:
                first_page, last_page = options["pagerange_callback"](info[0])
                if (first_page is None) or (last_page is None):
                    return

            password = options["passwords"][0] if options.get("passwords") else None
            for key in ["paths", "passwords", "password_callback"]:
                if key in options:
                    del options[key]
            self.import_file(
                info=info[0],
                password=password,
                first_page=first_page,
                last_page=last_page,
                **options,
            )

    def import_file(self, password=None, **options):
        "import file"
        # File in which to store the process ID
        # so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        dirname = EMPTY
        if self.dir is not None:
            dirname = self.dir

        def _import_file_data_callback(response):
            try:
                self.add_page(response.info, None)
            except AttributeError:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        def _import_file_finished_callback(response):
            if "finished_callback" in options:
                options["finished_callback"](response)

        self.thread.import_file(
            info=options["info"],
            password=password,
            first=options["first_page"],
            last=options["last_page"],
            dir=dirname,
            pidfile=pidfile,
            data_callback=_import_file_data_callback,
            finished_callback=_import_file_finished_callback,
        )

    def _post_process_scan(self, page, options):
        options = defaultdict(None, options)

        # tesseract can't extract resolution from pnm, so convert to png
        if (
            (page is not None)
            and re.search(
                r"Portable[ ](any|pix|gray|bit)map",
                page.format,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            and "to_png" in options
            and options["to_png"]
        ):

            def to_png_finished_callback(_response):
                finished_page = self.find_page_by_uuid(page.uuid)
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.to_png(
                page=page.uuid,
                finished_callback=to_png_finished_callback,
                **options,
            )

        if "rotate" in options and options["rotate"]:

            def rotate_finished_callback(_response):
                finished_page = self.find_page_by_uuid(page.uuid)
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            rotate_options = options
            rotate_options["angle"] = options["rotate"]
            rotate_options["page"] = page.uuid
            rotate_options["finished_callback"] = rotate_finished_callback
            del rotate_options["rotate"]
            self.rotate(**rotate_options)
            return

        if "unpaper" in options and options["unpaper"]:

            def updated_page_callback(response):
                if isinstance(response.info, dict) and response.info["type"] == "page":
                    del options["unpaper"]
                    finished_page = self.find_page_by_uuid(page.uuid)
                    if finished_page is None:
                        self._post_process_scan(
                            None, options
                        )  # to fire finished_callback
                        return
                    self._post_process_scan(self.data[finished_page][2], options)

            unpaper_options = options
            unpaper_options["options"] = {
                "command": options["unpaper"].get_cmdline(),
                "direction": options["unpaper"].get_option("direction"),
            }
            unpaper_options["page"] = page.uuid
            unpaper_options["updated_page_callback"] = updated_page_callback
            del unpaper_options["finished_callback"]
            self.unpaper(**unpaper_options)
            return

        if "udt" in options and options["udt"]:

            def udt_finished_callback(_response):
                del options["udt"]
                finished_page = self.find_page_by_uuid(page.uuid)
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.user_defined(
                page=page.uuid,
                command=options["udt"],
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=udt_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )
            return

        if "ocr" in options and options["ocr"]:

            def ocr_finished_callback(_response):
                del options["ocr"]
                self._post_process_scan(None, options)  # to fire finished_callback

            self.ocr_pages(
                pages=[page.uuid],
                threshold=options.get("threshold"),
                engine=options["engine"],
                language=options["language"],
                queued_callback=options.get("queued_callback"),
                started_callback=options.get("started_callback"),
                finished_callback=ocr_finished_callback,
                error_callback=options.get("error_callback"),
                display_callback=options.get("display_callback"),
            )
            return

        if "finished_callback" in options and options["finished_callback"]:
            options["finished_callback"](None)

    def import_scan(self, **options):
        """Take new scan, pad it if necessary, display it,
        and set off any post-processing chains"""

        # TODO: pass size and options as data, rather than via scope
        # opening inside with didn't work in initial tests for unknown reasons
        fhd = open(  # pylint: disable=consider-using-with
            options["filename"], mode="r", encoding="utf-8"
        )

        # Read without blocking
        size = 0

        def file_changed_callback(_fileno, condition, *data):
            nonlocal size, fhd

            if condition & GLib.IOCondition.IN:
                width, height = None, None
                if size == 0:
                    size, width, height = netpbm.file_size_from_header(
                        options["filename"]
                    )
                    logger.info("Header suggests %s", size)
                    if size == 0:
                        return GLib.SOURCE_CONTINUE
                    fhd.close()

                filesize = os.path.getsize(options["filename"])
                logger.info("Expecting %s, found %s", size, filesize)
                if size > filesize:
                    pad = size - filesize
                    with open(options["filename"], mode="ab") as fhd:
                        data = [1] * (pad * BITS_PER_BYTE + 1)
                        fhd.write(struct.pack(f"{len(data)}b", *data))
                    logger.info("Padded %s bytes", pad)

                page = Page(
                    filename=options["filename"],
                    resolution=(
                        options["resolution"],
                        options["resolution"],
                        "PixelsPerInch",
                    ),
                    width=width,
                    height=height,
                    format="Portable anymap",
                    delete=options["delete"] if "delete" in options else False,
                    dir=options["dir"],
                )
                index = self.add_page(page, options["page"])
                if index == NOT_FOUND and options["error_callback"]:
                    options["error_callback"](
                        None, "Import scan", _("Unable to load image")
                    )

                else:
                    if "display_callback" in options:
                        options["display_callback"](None)

                    self._post_process_scan(page, options)

                return GLib.SOURCE_REMOVE

            return GLib.SOURCE_CONTINUE

        GLib.io_add_watch(
            fhd,
            GLib.PRIORITY_DEFAULT,
            GLib.IOCondition.IN | GLib.IOCondition.HUP,
            file_changed_callback,
        )

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
        self.manual_sort_by_column(0)

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

    def remove_corrupted_pages(self):
        "remove corrupt pages"
        i = 0
        while i < len(self.data):
            if self.data[i][2] is None:
                del self.data[i]

            else:
                i += 1

    def manual_sort_by_column(self, sortcol):
        """Helpers:

        Manual one-time sorting of the simplelist's data"""
        self.remove_corrupted_pages()

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
        self.delete_selection_extra()
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

        logger.info("Copied %s%s pages", "and cloned " if clone else EMPTY, len(data))
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

    def delete_selection_extra(self):
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

    def save_pdf(self, **options):
        "save the given pages as PDF"
        options = defaultdict(None, options)

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        self.thread.save_pdf(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            metadata=options.get("metadata"),
            options=options.get("options"),
            dir=self.dir,
            pidfile=pidfile,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def save_djvu(self, **options):
        "save the given pages as DjVu"
        options = defaultdict(None, options)

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        self.thread.save_djvu(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            metadata=options.get("metadata"),
            options=options.get("options"),
            dir=self.dir,
            pidfile=pidfile,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def save_tiff(self, **options):
        "save the given pages as TIFF"
        options = defaultdict(None, options)

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        self.thread.save_tiff(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options.get("options"),
            dir=self.dir,
            pidfile=pidfile,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def rotate(self, **options):
        "rotate given page"
        options = defaultdict(None, options)
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        self.thread.rotate(
            angle=options["angle"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def save_image(self, **options):
        "save the given pages as image files"
        options = defaultdict(None, options)

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        self.thread.save_image(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options.get("options"),
            pidfile=pidfile,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def scans_saved(self):
        "Check that all pages have been saved"
        for row in self:
            if not row[2].saved:
                return False
        return True

    def save_text(self, **options):
        "save a text file from the given pages"
        options = defaultdict(None, options)
        self.thread.save_text(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options.get("options"),
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def save_hocr(self, **options):
        "save an hocr file from the given pages"
        options = defaultdict(None, options)
        self.thread.save_hocr(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options.get("options"),
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            mark_saved_callback=options.get("mark_saved_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def analyse(self, **options):
        "analyse given page"
        options = defaultdict(None, options)
        self.thread.analyse(
            list_of_pages=options["list_of_pages"],
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def threshold(self, **options):
        "threshold given page"
        options = defaultdict(None, options)
        self.thread.threshold(
            threshold=options["threshold"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def brightness_contrast(self, **options):
        "adjust brightness & contrast of given page"
        options = defaultdict(None, options)
        self.thread.brightness_contrast(
            brightness=options["brightness"],
            contrast=options["contrast"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def negate(self, **options):
        "negate given page"
        options = defaultdict(None, options)
        self.thread.negate(
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def unsharp(self, **options):
        "run unsharp mask on given page"
        options = defaultdict(None, options)
        self.thread.unsharp(
            radius=options["radius"],
            percent=options["percent"],
            threshold=options["threshold"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def crop(self, **options):
        "crop page"
        options = defaultdict(None, options)
        self.thread.crop(
            x=options["x"],
            y=options["y"],
            w=options["w"],
            h=options["h"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def split_page(self, **options):
        """split the given page either vertically or horizontally, creating an
        additional page"""
        options = defaultdict(None, options)

        # FIXME: duplicate to _import_file_data_callback()
        def _split_page_data_callback(response):
            if response.info["type"] == "page":
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        self.thread.split_page(
            direction=options["direction"],
            position=options["position"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            data_callback=_split_page_data_callback,
            finished_callback=options.get("finished_callback"),
        )

    def to_png(self, options):
        "convert the given page to png"
        self.thread.to_png(
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
        )

    def tesseract(self, **options):
        "run tesseract on the given page"
        options = defaultdict(None, options)
        self.thread.tesseract(
            language=options["language"],
            page=options["page"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def ocr_pages(self, **options):
        "Wrapper for the various ocr engines"
        for page in options["pages"]:
            options["page"] = page
            if options["engine"] == "tesseract":
                self.tesseract(**options)

    def unpaper(self, **options):
        "run unpaper on the given page"
        options = defaultdict(None, options)

        # FIXME: duplicate to _import_file_data_callback()
        def _unpaper_data_callback(response):
            if isinstance(response.info, dict) and "page" in response.info:
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        self.thread.unpaper(
            page=options["page"],
            options=options["options"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            display_callback=options.get("display_callback"),
            error_callback=options.get("error_callback"),
            data_callback=_unpaper_data_callback,
            updated_page_callback=options.get("updated_page_callback"),
            finished_callback=options.get("finished_callback"),
        )

    def user_defined(self, **options):
        "run a user-defined command on a page"
        options = defaultdict(None, options)
        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return

        # FIXME: duplicate to _import_file_data_callback()
        def _user_defined_data_callback(response):
            if response.info["type"] == "page":
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        self.thread.user_defined(
            page=options["page"],
            command=options["command"],
            dir=self.dir,
            uuid=_note_callbacks(options),
            pidfile=pidfile,
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            error_callback=options.get("error_callback"),
            data_callback=_user_defined_data_callback,
            finished_callback=options.get("finished_callback"),
        )

    def save_session(self, filename=None, version=None):
        """Dump $self to a file.
        If a filename is given, zip it up as a session file
        Pass version to allow us to mock different session version and to be able to
        test opening old sessions."""
        self.remove_corrupted_pages()
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
        selected_pages = self.index2page_number(selected_pages)
        all_pages = self.index2page_number(all_pages)
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

    def index2page_number(self, index):
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


def _extract_metadata(info):
    metadata = {}
    for key in info.keys():
        if (
            re.search(
                r"(author|title|subject|keywords|tz)",
                key,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            and info[key] != "NONE"
        ):
            metadata[key] = unescape_utf8(info[key])

    if "datetime" in info:
        if info["format"] == "Portable Document Format":
            regex = re.search(
                r"^(.{19})((?:[+-]\d+)|Z)?$",
                info["datetime"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                try:
                    dtm = datetime.datetime.strptime(
                        regex.group(1), "%Y-%m-%dT%H:%M:%S"
                    )
                    tzn = regex.group(2)
                    metadata["datetime"] = [
                        dtm.year,
                        dtm.month,
                        dtm.day,
                        dtm.hour,
                        dtm.minute,
                        dtm.second,
                    ]
                    if (tzn is None) or tzn == "Z":
                        tzn = 0

                    metadata["tz"] = [None, None, None, int(tzn), 0, None, None]
                except ValueError:
                    pass

        elif info["format"] == "DJVU":
            regex = re.search(
                rf"^{ISODATE_REGEX}\s{TIME_REGEX}{TZ_REGEX}",
                info["datetime"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                metadata["datetime"] = [int(regex.group(x)) for x in range(1, 7)]
                metadata["tz"] = [
                    None,
                    None,
                    None,
                    int(regex.group(7)),
                    int(regex.group(8)),
                    None,
                    None,
                ]

    return metadata


def drag_data_received_callback(tree, context, xpos, ypos, data, info, time):
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


def expand_metadata_pattern(**kwargs):
    "expand metadata template"

    # Expand author, title and extension
    for key in ["author", "title", "subject", "keywords", "extension"]:
        if key not in kwargs:
            kwargs[key] = ""
        regex = r"%D" + key[0]
        kwargs["template"] = re.sub(
            regex, kwargs[key], kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )

    # Expand convert %Dx code to %x, convert using strftime and replace
    regex = re.search(
        r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
    )
    while regex:
        code = regex.group(1)
        template = f"{PERCENT}{code}"
        result = kwargs["docdate"].strftime(template)
        kwargs["template"] = re.sub(
            rf"%D{code}",
            result,
            kwargs["template"],
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        regex = re.search(
            r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
        )

    # Expand basic strftime codes
    kwargs["template"] = kwargs["today_and_now"].strftime(kwargs["template"])

    # avoid leading and trailing whitespace in expanded filename template
    kwargs["template"] = kwargs["template"].strip()
    if "convert_whitespace" in kwargs and kwargs["convert_whitespace"]:
        kwargs["template"] = re.sub(
            r"\s", r"_", kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )
    return kwargs["template"]


def collate_metadata(settings, today_and_now, timezone):
    "collect metadata from settings dictionary"
    metadata = {}
    for key in ["author", "title", "subject", "keywords"]:
        if key in settings:
            metadata[key] = settings[key]

    today_and_now = datetime.datetime(*today_and_now)
    offset = datetime.timedelta(
        days=settings["datetime offset"][0],
        hours=settings["datetime offset"][1],
        minutes=settings["datetime offset"][2],
        seconds=settings["datetime offset"][3],
    )
    today_plus_offset = today_and_now + offset
    metadata["datetime"] = [
        today_plus_offset.year,
        today_plus_offset.month,
        today_plus_offset.day,
        today_plus_offset.hour,
        today_plus_offset.minute,
        today_plus_offset.second,
    ]
    if "use_time" not in settings:
        # Set time to zero
        time = [0, 0, 0]
        del metadata["datetime"][
            len(metadata["datetime"]) - len(time) : len(metadata["datetime"])
        ]
        metadata["datetime"] += time

    if "use_timezone" in settings:
        metadata["tz"] = add_delta_timezone(timezone, settings["timezone offset"])

    return metadata


def add_delta_timezone(timezone, timezone_offset):
    "apply timezone delta"
    return [timezone[i] + timezone_offset[i] for i in range(len(timezone))]


def delta_timezone(tz1, tz2):
    "calculate delta between two timezones - mostly to spot differences between DST"
    return [tz2[i] - tz1[i] for i in range(len(tz1))]


def px2pt(pixels, resolution):
    """helper function to return length in points given a number of pixels
    and the resolution"""
    return pixels / resolution * POINTS_PER_INCH


def _bbox2markup(xresolution, yresolution, height, bbox):
    for i in (0, 2):
        bbox[i] = px2pt(bbox[i], xresolution)
        bbox[i + 1] = height - px2pt(bbox[i + 1], yresolution)

    return [
        bbox[LEFT],
        bbox[BOTTOM],
        bbox[RIGHT],
        bbox[BOTTOM],
        bbox[LEFT],
        bbox[TOP],
        bbox[RIGHT],
        bbox[TOP],
    ]


def _note_callbacks(options):
    "create the mark_saved callback if necessary"
    if "mark_saved" in options and options["mark_saved"]:

        def mark_saved_callback(_data):
            # list_of_pages is frozen,
            # so find the original pages from their uuids
            for page in options["list_of_pages"]:
                page.saved = True

        options["mark_saved_callback"] = mark_saved_callback


# https://py-pdf.github.io/fpdf2/Annotations.html
def _add_annotations_to_pdf(page, gs_page):
    """Box is the same size as the page. We don't know the text position.
    Start at the top of the page (PDF coordinate system starts
    at the bottom left of the page)"""
    xresolution, yresolution, _units = gs_page.get_resolution()
    height = px2pt(gs_page.height, yresolution)
    for box in Bboxtree(gs_page.annotations).get_bbox_iter():
        if box["type"] == "page" or "text" not in box or box["text"] == EMPTY:
            continue

        rgb = []
        for i in range(3):
            rgb.append(hex(ANNOTATION_COLOR[i : i + 2]) / 255)

        annot = page.annotation()
        annot.markup(
            box["text"],
            _bbox2markup(xresolution, yresolution, height, len(box["bbox"])),
            "Highlight",
            color=rgb,
            opacity=0.5,
        )

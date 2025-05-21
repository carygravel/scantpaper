"main document IO methods"

from collections import defaultdict
import datetime
import re
import logging
import sys
import os
from i18n import _
from basedocument import BaseDocument
from page import Page
from bboxtree import unescape_utf8

logger = logging.getLogger(__name__)

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
STRFTIME_YEAR_OFFSET = -1900
STRFTIME_MONTH_OFFSET = -1
MIN_YEAR_FOR_DATECALC = 1970
LAST_ELEMENT = -1


class Document(BaseDocument):
    "More methods"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._undo_buffer = []
        self._undo_selection = []
        self._redo_buffer = []
        self._redo_selection = []

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

    def import_file(self, **kwargs):
        "import file"
        print(f"import_file({kwargs})")
        # File in which to store the process ID
        # so that it can be killed if necessary
        kwargs["pidfile"] = self.create_pidfile(kwargs)
        if kwargs["pidfile"] is None:
            return
        kwargs["dir"] = EMPTY
        if self.dir is not None:
            kwargs["dir"] = self.dir
        kwargs["first"] = kwargs.pop("first_page")
        kwargs["last"] = kwargs.pop("last_page")

        def _import_file_data_callback(response):
            try:
                self.add_page(*response.info["row"])
            except AttributeError:
                if "logger_callback" in kwargs:
                    kwargs["logger_callback"](response)

        kwargs["data_callback"] = _import_file_data_callback
        self.thread.import_file(**kwargs)

    def _post_process_rotate(self, page_id, options):
        print(f"_post_process_rotate {page_id}")

        def updated_page_callback(response):
            print(f"updated_page_callback {response, response.request}")
            info = response.info
            print(f"info {info}")
            if info and "type" in info and info["type"] == "page":
                args = list(info["row"])
                for key in [
                    "replace",
                    "insert-after",
                ]:
                    if key in info:
                        args.append(info[key])
                print(f"before add_page {args}")
                self.add_page(*args)
                page_id = args[2]
                print(f"page_id {page_id}")
                del options["rotate"]
                self._post_process_scan(page_id, options)

        rotate_options = options.copy()
        rotate_options["angle"] = options["rotate"]
        rotate_options["page"] = page_id
        rotate_options["updated_page_callback"] = updated_page_callback
        del rotate_options["finished_callback"]
        self.rotate(**rotate_options)  # pylint: disable=no-member

    def _post_process_unpaper(self, page_id, options):
        print(f"_post_process_unpaper {page_id}")

        def updated_page_callback(response):
            print(f"unpaper updated_page_callback {response, response.request}")
            info = response.info
            print(f"info {info}")
            if info and "type" in info and info["type"] == "page":
                args = list(info["row"])
                for key in [
                    "replace",
                    "insert-after",
                ]:
                    if key in info:
                        args.append(info[key])
                print(f"before add_page {args}")
                self.add_page(*args)
                page_id = args[2]
                print(f"page_id {page_id}")
                del options["unpaper"]
                self._post_process_scan(page_id, options)

        unpaper_options = options.copy()
        unpaper_options["options"] = {
            "command": options["unpaper"].get_cmdline(),
            "direction": options["unpaper"].get_option("direction"),
        }
        unpaper_options["page"] = page_id
        unpaper_options["updated_page_callback"] = updated_page_callback
        del unpaper_options["finished_callback"]
        self.unpaper(**unpaper_options)

    def _post_process_udt(self, page_id, options):
        print(f"_post_process_udt {page_id}")

        def updated_page_callback(response):
            info = response.info
            print(f"info {info}")
            if info and "type" in info and info["type"] == "page":
                args = list(info["row"])
                for key in [
                    "replace",
                    "insert-after",
                ]:
                    if key in info:
                        args.append(info[key])
                print(f"before add_page {args}")
                self.add_page(*args)
                page_id = args[2]
                print(f"page_id {page_id}")
                del options["udt"]
                self._post_process_scan(page_id, options)

        udt_options = options.copy()
        udt_options["page"] = page_id
        udt_options["command"] = options["udt"]
        udt_options["updated_page_callback"] = updated_page_callback
        self.user_defined(**udt_options)

    def _post_process_ocr(self, page_id, options):
        print(f"_post_process_ocr {page_id}")

        def ocr_finished_callback(_response):
            del options["ocr"]
            self._post_process_scan(None, options)  # to fire finished_callback

        self.ocr_pages(
            pages=[page_id],
            threshold=options.get("threshold"),
            engine=options["engine"],
            language=options["language"],
            queued_callback=options.get("queued_callback"),
            started_callback=options.get("started_callback"),
            finished_callback=ocr_finished_callback,
            error_callback=options.get("error_callback"),
            display_callback=options.get("display_callback"),
        )

    def _post_process_scan(self, page_id, options):
        options = defaultdict(None, options)

        if "rotate" in options and options["rotate"]:
            self._post_process_rotate(page_id, options)
            return

        if "unpaper" in options and options["unpaper"]:
            self._post_process_unpaper(page_id, options)
            return

        if "udt" in options and options["udt"]:
            self._post_process_udt(page_id, options)
            return

        if "ocr" in options and options["ocr"]:
            self._post_process_ocr(page_id, options)
            return

        if "finished_callback" in options and options["finished_callback"]:
            options["finished_callback"](None)

    def import_scan(self, **kwargs):
        "Take new scan, display it, and set off any post-processing chains"

        page_kwargs = {
            "resolution": kwargs["resolution"],
            "format": "Portable anymap",
            "dir": kwargs["dir"],
        }
        for key in ["image_object", "filename"]:
            if key in kwargs:
                page_kwargs[key] = kwargs[key]

        # FIXME: duplicate to _import_file_data_callback(), apart from the
        # post-processing chain
        def _import_scan_data_callback(response):
            print(f"_import_page_data_callback {response, response.info}")
            if response.info["type"] == "page":
                args = list(response.info["row"])
                for key in [
                    "replace",
                    "insert-after",
                ]:
                    if key in response.info:
                        args.append(response.info[key])
                print(f"before add_page {args}")
                self.add_page(*args)
                page_id = args[2]
                print(f"page_id {page_id}")
                self._post_process_scan(page_id, kwargs)

        import_scan_kwargs = kwargs.copy()
        import_scan_kwargs["data_callback"] = _import_scan_data_callback
        if "finished_callback" in import_scan_kwargs:
            del import_scan_kwargs["finished_callback"]
        self.thread.import_page(**import_scan_kwargs)

    def split_page(self, **kwargs):
        """split the given page either vertically or horizontally, creating an
        additional page"""

        # FIXME: duplicate to _import_file_data_callback()
        def _split_page_data_callback(response):
            if response.info["type"] == "page":
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in kwargs:
                    kwargs["logger_callback"](response)

        self._note_callbacks(kwargs)
        kwargs["data_callback"] = _split_page_data_callback
        self.thread.split_page(**kwargs)

    def ocr_pages(self, **kwargs):
        "Wrapper for the various ocr engines"
        for page in kwargs["pages"]:
            kwargs["page"] = page
            if kwargs["engine"] == "tesseract":
                self.tesseract(**kwargs)  # pylint: disable=no-member

    def unpaper(self, **kwargs):
        "run unpaper on the given page"

        # FIXME: duplicate to _import_file_data_callback()
        def _unpaper_data_callback(response):
            if isinstance(response.info, dict) and "page" in response.info:
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in kwargs:
                    kwargs["logger_callback"](response)

        self._note_callbacks(kwargs)
        kwargs["data_callback"] = _unpaper_data_callback
        self.thread.unpaper(**kwargs)

    def user_defined(self, **kwargs):
        "run a user-defined command on a page"

        # FIXME: duplicate to _import_file_data_callback()
        def _user_defined_data_callback(response):
            print(f"_user_defined_data_callback {response, response.info}")
            if response.info["type"] == "page":
                args = list(response.info["row"])
                for key in [
                    "replace",
                    "insert-after",
                ]:
                    if key in response.info:
                        args.append(response.info[key])
                print(f"before add_page {args}")
                self.add_page(*args)
                print(f"after add_page")
            else:
                if "logger_callback" in kwargs:
                    kwargs["logger_callback"](response)

        self._note_callbacks(kwargs)
        kwargs["data_callback"] = _user_defined_data_callback
        self.thread.user_defined(**kwargs)

    def take_snapshot(self):
        "take a snapshot of the document"

        old_undo_files = list(map(lambda x: x[2].uuid, self._undo_buffer))

        # Deep copy the tied data. Otherwise, very bad things happen.
        self._undo_buffer = self.data.copy()
        self._undo_selection = self.get_selected_indices()
        logger.debug("Undo buffer %s", self._undo_buffer)
        logger.debug("Undo selection %s", self._undo_selection)

        # Clean up files that fall off the undo buffer
        undo_files = {}
        for i in self._undo_buffer:
            undo_files[i[2].uuid] = True

        delete_files = []
        for file in old_undo_files:
            if not undo_files[file]:
                delete_files.append(file)

        if delete_files:
            logger.info("Cleaning up delete_files")
            os.remove(delete_files)

    def undo(self):
        "undo the last action"
        self._redo_buffer = self.clone_data()
        self._redo_selection = self.get_selected_indices()
        logger.debug("undo_buffer: %s", self._undo_buffer)
        logger.debug("undo_selection: %s", self._undo_selection)
        logger.debug("redo_buffer: %s", self._redo_buffer)
        logger.debug("redo_selection: %s", self._redo_selection)

        # Block slist signals whilst updating
        self.get_model().handler_block(self.row_changed_signal)
        self.get_selection().handler_block(self.selection_changed_signal)
        self.data = self._undo_buffer

        # Unblock slist signals now finished
        self.get_selection().handler_unblock(self.selection_changed_signal)
        self.get_model().handler_unblock(self.row_changed_signal)

        # Reselect the pages to display the detail view
        self.select(self._undo_selection)

    def unundo(self):
        "redo the last action"
        self._undo_buffer = self.clone_data()
        self._undo_selection = self.get_selected_indices()
        logger.debug("undo_buffer: %s", self._undo_buffer)
        logger.debug("undo_selection: %s", self._undo_selection)
        logger.debug("redo_buffer: %s", self._redo_buffer)
        logger.debug("redo_selection: %s", self._redo_selection)

        # Block slist signals whilst updating
        self.get_model().handler_block(self.row_changed_signal)
        self.get_selection().handler_block(self.selection_changed_signal)
        self.data = self._redo_buffer

        # Unblock slist signals now finished
        self.get_selection().handler_unblock(self.selection_changed_signal)
        self.get_model().handler_unblock(self.row_changed_signal)

        # Reselect the pages to display the detail view
        self.select(self._redo_selection)

    def indices2pages(self, list_of_indices):
        "Helper function to convert an array of indices into an array of uuids"
        return map(lambda x: str(self.data[x][2].uuid), list_of_indices)

    def mark_pages(self, pages):
        "marked page list as saved"
        self.get_model().handler_block(self.row_changed_signal)
        for p in pages:
            i = self.find_page_by_uuid(p)
            if i is not None:
                self.data[i][2].saved = True
        self.get_model().handler_unblock(self.row_changed_signal)

    def get_selected_properties(self):
        "Helper function for properties()"
        page = self.get_selected_indices()
        xresolution = None
        yresolution = None
        if len(page) > 0:
            i = page.pop(0)
            xresolution, yresolution, _units = self.data[i][2].resolution
            logger.debug(
                "Page %s has resolutions %s,%s",
                self.data[i][0],
                xresolution,
                yresolution,
            )

        for i in page:
            if self.data[i][2].resolution[0] != xresolution:
                xresolution = None
                break

        for i in page:
            if self.data[i][2].resolution[0] != yresolution:
                yresolution = None
                break

        # round the value to a sensible number of significant figures
        return xresolution, yresolution


def _extract_metadata(info):
    metadata = {}
    for key in info.keys():
        if (
            re.search(
                r"(author|title|subject|keywords)",
                key,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            and info[key] != "NONE"
        ):
            metadata[key] = unescape_utf8(info[key])

    if "datetime" in info:
        if info["format"] in ["Portable Document Format", "DJVU"]:

            # before python 3.11, fromisoformat() did not understand Z==UTC, or TZs without minutes
            if sys.version_info < (3, 11):
                if info["datetime"][-1] == "Z":
                    info["datetime"] = info["datetime"][:-1] + "+00:00"
                elif re.search(
                    r"^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d$", info["datetime"]
                ):
                    info["datetime"] += ":00"
            try:
                metadata["datetime"] = datetime.datetime.fromisoformat(info["datetime"])
            except ValueError:
                pass

    return metadata

"main document IO methods"
from collections import defaultdict
import datetime
import struct
import re
import os
import logging
from i18n import _
from basedocument import BaseDocument
from page import Page
import netpbm
from bboxtree import unescape_utf8
from gi.repository import GLib

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
STRFTIME_YEAR_OFFSET = -1900
STRFTIME_MONTH_OFFSET = -1
MIN_YEAR_FOR_DATECALC = 1970
LAST_ELEMENT = -1


EXPORT_OK = []

ISODATE_REGEX = r"(\d{4})-(\d\d)-(\d\d)"
TIME_REGEX = r"(\d\d):(\d\d):(\d\d)"
TZ_REGEX = r"([+-]\d\d):(\d\d)"


class Document(BaseDocument):
    "Import methods"

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

            self._to_png(
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

    def save_pdf(self, **kwargs):
        "save the given pages as PDF"
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        self.thread.save_pdf(**kwargs)

    def save_djvu(self, **kwargs):
        "save the given pages as DjVu"
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        self.thread.save_djvu(**kwargs)

    def save_tiff(self, **kwargs):
        "save the given pages as TIFF"
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        self.thread.save_tiff(**kwargs)

    def rotate(self, **kwargs):
        "rotate given page"
        self._note_callbacks(kwargs)
        self.thread.rotate(**kwargs)

    def save_image(self, **kwargs):
        "save the given pages as image files"
        kwargs["mark_saved"] = True
        self._note_callbacks(kwargs)
        self.thread.save_image(**kwargs)

    def save_text(self, **kwargs):
        "save a text file from the given pages"
        self._note_callbacks(kwargs)
        self.thread.save_text(**kwargs)

    def save_hocr(self, **kwargs):
        "save an hocr file from the given pages"
        self._note_callbacks(kwargs)
        self.thread.save_hocr(**kwargs)

    def analyse(self, **kwargs):
        "analyse given page"
        self._note_callbacks(kwargs)
        self.thread.analyse(**kwargs)

    def threshold(self, **kwargs):
        "threshold given page"
        self._note_callbacks(kwargs)
        self.thread.threshold(**kwargs)

    def brightness_contrast(self, **kwargs):
        "adjust brightness & contrast of given page"
        self._note_callbacks(kwargs)
        self.thread.brightness_contrast(**kwargs)

    def negate(self, **kwargs):
        "negate given page"
        self._note_callbacks(kwargs)
        self.thread.negate(**kwargs)

    def unsharp(self, **kwargs):
        "run unsharp mask on given page"
        self._note_callbacks(kwargs)
        self.thread.unsharp(**kwargs)

    def crop(self, **kwargs):
        "crop page"
        self._note_callbacks(kwargs)
        self.thread.crop(**kwargs)

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

    def tesseract(self, **kwargs):
        "run tesseract on the given page"
        self._note_callbacks(kwargs)
        self.thread.tesseract(**kwargs)

    def ocr_pages(self, **kwargs):
        "Wrapper for the various ocr engines"
        for page in kwargs["pages"]:
            kwargs["page"] = page
            if kwargs["engine"] == "tesseract":
                self.tesseract(**kwargs)

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
            if response.info["type"] == "page":
                self.add_page(response.info["page"], response.info["info"])
            else:
                if "logger_callback" in kwargs:
                    kwargs["logger_callback"](response)

        self._note_callbacks(kwargs)
        kwargs["data_callback"] = _user_defined_data_callback
        self.thread.user_defined(**kwargs)


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

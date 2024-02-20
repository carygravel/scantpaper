"main document IO methods"
from collections import defaultdict
import shutil
import subprocess
import glob
import pathlib
import datetime
import struct
import re
import os
import threading
import queue
import gettext  # For translations
import tempfile
import uuid
import logging
from pathlib import Path
import signal
import tarfile
import img2pdf
import ocrmypdf
from PIL import ImageStat, Image, ImageEnhance, ImageOps, ImageFilter
from basethread import BaseThread
from const import POINTS_PER_INCH, ANNOTATION_COLOR
from bboxtree import Bboxtree, unescape_utf8
from i18n import _
import gi
from simplelist import SimpleList
from page import Page
import netpbm
import tesserocr

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # pylint: disable=wrong-import-position

img2pdf.default_dpi = 72.0

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
PROCESS_FAILED = -1
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
_90_DEGREES = 90
_270_DEGREES = 270
LEFT = 0
TOP = 1
RIGHT = 2
BOTTOM = 3


EXPORT_OK = []

ISODATE_REGEX = r"(\d{4})-(\d\d)-(\d\d)"
TIME_REGEX = r"(\d\d):(\d\d):(\d\d)"
TZ_REGEX = r"([+-]\d\d):(\d\d)"
PNG = r"Portable[ ]Network[ ]Graphics"
JPG = r"JPEG"
GIF = r"CompuServe[ ]graphics[ ]interchange[ ]format"

image_format = {
    "pnm": "Portable anymap",
    "ppm": "Portable pixmap format (color)",
    "pgm": "Portable graymap format (gray scale)",
    "pbm": "Portable bitmap format (black and white)",
}

SimpleList.add_column_type(hstring={"type": object, "attr": "hidden"})


class DocThread(BaseThread):
    "subclass basethread for document"

    cancel = False
    paper_sizes = {}

    def __init__(self):
        BaseThread.__init__(self)
        self.lock = threading.Lock()
        self.page_requests = queue.Queue()
        self.pages = queue.Queue()
        self.running_pids = []

    def input_handler(self, request):
        "handle page requests"
        if not request.args:
            return request.args

        args = list(request.args)

        if "page" in args[0]:
            self.page_requests.put(args[0]["page"])
            page_request = self.pages.get()  # blocking get requested page
            if page_request == "cancel":
                return
            args[0]["page"] = page_request

        elif "list_of_pages" in args[0]:
            for i, page in enumerate(args[0]["list_of_pages"]):
                self.page_requests.put(page)
                page_request = self.pages.get()  # blocking get requested page
                if page_request == "cancel":
                    return

                args[0]["list_of_pages"][i] = page_request
        request.args = tuple(args)
        return request.args

    def do_get_file_info(self, request):
        "get file info"
        path, password = request.args
        info = {}
        if not pathlib.Path(path).exists():
            raise FileNotFoundError(_("File %s not found") % (path,))

        logger.info("Getting info for %s", path)
        _returncode, fformat, _stderr = exec_command(["file", "-Lb", path])
        fformat = fformat.rstrip()
        logger.info("Format: '%s'", fformat)
        if fformat in ["very short file (no magic)", "empty"]:
            raise RuntimeError(_("Error importing zero-length file %s.") % (path,))

        elif re.search(r"gzip[ ]compressed[ ]data", fformat):
            info["path"] = path
            info["format"] = "session file"
            return info

        elif re.search(r"DjVu", fformat):
            # Dig out the number of pages
            _exit_code, stdout, stderr = exec_command(["djvudump", path])
            if re.search(
                r"command[ ]not[ ]found", stderr, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                raise RuntimeError(
                    _("Please install djvulibre-bin in order to open DjVu files.")
                )

            logger.info(stdout)
            if self.cancel:
                return
            pages = 1
            regex = re.search(
                r"\s(\d+)\s+page", stdout, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                pages = int(regex.group(1))

            # Dig out the size and resolution of each page
            width, height, ppi = [], [], []
            info["format"] = "DJVU"
            regex = re.findall(
                r"DjVu\s(\d+)x(\d+).+?\s+(\d+)\s+dpi",
                stdout,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            for _w, _h, _p in regex:
                width.append(int(_w))
                height.append(int(_h))
                ppi.append(int(_p))
                logger.info(
                    "Page %s is %sx%s, %s ppi", len(ppi), width[-1], height[-1], ppi[-1]
                )

            if pages != len(ppi):
                raise RuntimeError(
                    _("Unknown DjVu file structure. Please contact the author.")
                )

            info["width"] = width
            info["height"] = height
            info["ppi"] = ppi
            info["pages"] = pages
            info["path"] = path
            # Dig out the metadata
            _exit_code, stdout, _stderr = exec_command(
                ["djvused", path, "-e", "print-meta"]
            )
            logger.info(stdout)
            if self.cancel:
                return

            # extract the metadata from the file
            _add_metadata_to_info(info, stdout, r'\s+"([^"]+)')
            return info

        elif re.search(r"PDF[ ]document", fformat):
            fformat = "Portable Document Format"
            args = ["pdfinfo", "-isodates", path]
            if password is not None:
                args.insert(2, "-upw")
                args.insert(3, password)

            process = subprocess.run(args, capture_output=True, text=True)
            if self.cancel:
                return
            if process.returncode != 0:
                logger.info("stdout: %s", process.stdout)
                logger.info("stderr: %s", process.stderr)
                if (process.stderr is not None) and re.search(
                    r"Incorrect[ ]password",
                    process.stderr,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    info["encrypted"] = True
                else:
                    request.error(process.stderr)
                    return

            else:
                info["pages"] = 1
                regex = re.search(
                    r"Pages:\s+(\d+)",
                    process.stdout,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                if regex:
                    info["pages"] = int(regex.group(1))

                logger.info("%s pages", info["pages"])
                floatr = r"\d+(?:[.]\d*)?"
                regex = re.search(
                    rf"Page\ssize:\s+({floatr})\s+x\s+({floatr})\s+(\w+)",
                    process.stdout,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                if regex:
                    info["page_size"] = [
                        float(regex.group(1)),
                        float(regex.group(2)),
                        regex.group(3),
                    ]
                    logger.info(
                        "Page size: %s x %s %s",
                        regex.group(1),
                        regex.group(2),
                        regex.group(3),
                    )

                # extract the metadata from the file
                _add_metadata_to_info(info, process.stdout, r":\s+([^\n]+)")

        elif re.search(r"^TIFF[ ]image[ ]data", fformat):
            fformat = "Tagged Image File Format"
            _exit_code, stdout, _stderr = exec_command(["tiffinfo", path])
            if self.cancel:
                return
            logger.info(info)

            # Count number of pages
            info["pages"] = len(
                re.findall(
                    r"TIFF[ ]Directory[ ]at[ ]offset",
                    stdout,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
            )
            logger.info("%s pages", info["pages"])

            # Dig out the size of each page
            width, height = [], []
            regex = re.findall(
                r"Image\sWidth:\s(\d+)\sImage\sLength:\s(\d+)",
                stdout,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            for _w, _h in regex:
                width.append(int(_w))
                height.append(int(_h))
                request.data(f"Page {len(width)} is {width[-1]}x{height[-1]}")

            info["width"] = width
            info["height"] = height

        else:
            # Get file type
            image = Image.open(path)

            if self.cancel:
                return
            fformat = image.format

            logger.info("Format %s", fformat)
            info["width"] = [image.width]
            info["height"] = [image.height]
            dpi = image.info.get("dpi")
            if dpi is None:
                info["xresolution"], info["yresolution"] = (
                    img2pdf.default_dpi,
                    img2pdf.default_dpi,
                )
            else:
                xresolution, yresolution = dpi
            info["pages"] = 1

        info["format"] = fformat
        info["path"] = path
        return info

    def do_import_file(self, request):
        "import file in thread"
        args = request.args[0]
        if args["info"]["format"] == "DJVU":
            # Extract images from DjVu
            if args["last"] >= args["first"] and args["first"] > 0:
                for i in range(args["first"], args["last"] + 1):
                    self.progress = (i - 1) / (args["last"] - args["first"] + 1)
                    # self.message = _("Importing page %i of %i") % (
                    #     i,
                    #     args["last"] - args["first"] + 1,
                    # )
                    tif, txt, ann, error = None, None, None, None
                    try:
                        tif = tempfile.NamedTemporaryFile(
                            dir=args["dir"], suffix=".tif", delete=False
                        )
                        subprocess.run(
                            [
                                "ddjvu",
                                "-format=tiff",
                                f"-page={i}",
                                args["info"]["path"],
                                tif.name,
                            ],
                            check=True,
                        )
                        txt = subprocess.check_output(
                            [
                                "djvused",
                                args["info"]["path"],
                                "-e",
                                f"select {i}; print-txt",
                            ],
                            text=True,
                        )
                        ann = subprocess.check_output(
                            [
                                "djvused",
                                args["info"]["path"],
                                "-e",
                                f"select {i}; print-ant",
                            ],
                            text=True,
                        )

                    except Exception as err:
                        if tif is not None:
                            logger.error("Caught error creating %s: %s", tif, err)
                            self._thread_throw_error(
                                args["uuid"],
                                args["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {tif}.",
                            )

                        else:
                            logger.error(
                                "Caught error writing to %s: %s", args.dir, err
                            )
                            self._thread_throw_error(
                                args["uuid"],
                                args["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {args.dir}.",
                            )

                        error = True

                    if self.cancel or error:
                        return
                    page = Page(
                        filename=tif.name,
                        dir=args["dir"],
                        delete=True,
                        format="Tagged Image File Format",
                        resolution=(
                            args["info"]["ppi"][i - 1],
                            args["info"]["ppi"][i - 1],
                            "PixelsPerInch",
                        ),
                        width=args["info"]["width"][i - 1],
                        height=args["info"]["height"][i - 1],
                    )
                    try:
                        page.import_djvu_txt(txt)
                    except Exception as err:
                        request.data(
                            None, f"Caught error parsing DjVU text layer: {err}"
                        )

                    try:
                        page.import_djvu_ann(ann)

                    except Exception as err:
                        logger.error(
                            "Caught error parsing DjVU annotation layer: %s", err
                        )
                        self._thread_throw_error(
                            args["uuid"],
                            args["page"]["uuid"],
                            "Open file",
                            "Error: parsing DjVU annotation layer",
                        )

                    request.data(page)

        elif args["info"]["format"] == "Portable Document Format":
            self._thread_import_pdf(request)

        elif args["info"]["format"] == "Tagged Image File Format":
            # Only one page, so skip tiffcp in case it gives us problems
            if args["last"] == 1:
                #                self.progress = 1
                #                self.message = _("Importing page %i of %i") % (1, 1)
                page = Page(
                    filename=args["info"]["path"],
                    dir=args["dir"],
                    delete=False,
                    format=args["info"]["format"],
                    width=args["info"]["width"][0],
                    height=args["info"]["height"][0],
                )
                request.data(page)

            # Split the tiff into its pages and import them individually
            elif args["last"] >= args["first"] and args["first"] > 0:
                for i in range(args["first"] - 1, args["last"] - 1 + 1):
                    self.progress = i / (args["last"] - args["first"] + 1)
                    self.message = _("Importing page %i of %i") % (
                        i,
                        args["last"] - args["first"] + 1,
                    )
                    (tif, error) = (None, None)
                    try:
                        tif = tempfile.NamedTemporaryFile(
                            dir=args["dir"], suffix=".tif", delete=False
                        )
                    except Exception as err:
                        logger.error("Caught error creating %s: %s", tif, err)
                        self._thread_throw_error(
                            args["uuid"],
                            args["page"]["uuid"],
                            "Open file",
                            f"Error: unable to write to {tif}.",
                        )
                    try:
                        subprocess.run(
                            ["tiffcp", f"{args['info']['path']},{i}", tif.name],
                            check=True,
                        )
                    except Exception as err:
                        logger.error(
                            "Caught error extracting page %s from %s: %s",
                            i,
                            args["info"]["path"],
                            err,
                        )
                        self._thread_throw_error(
                            args["uuid"],
                            args["page"]["uuid"],
                            "Open file",
                            f"Caught error extracting page {i} from {args['info']['path']}: {err}",
                        )

                    if self.cancel:
                        return
                    page = Page(
                        filename=tif.name,
                        dir=args["dir"],
                        delete=True,
                        format=args["info"]["format"],
                        width=args["info"]["width"][i - 1],
                        height=args["info"]["height"][i - 1],
                    )
                    request.data(page)

        elif re.search(rf"(?:{PNG}|{JPG}|{GIF})", args["info"]["format"]):
            try:
                page = Page(
                    filename=args["info"]["path"],
                    dir=args["dir"],
                    format=args["info"]["format"],
                    width=args["info"]["width"][0],
                    height=args["info"]["height"][0],
                    resolution=(
                        args["info"]["xresolution"],
                        args["info"]["yresolution"],
                        "PixelsPerInch",
                    ),
                )
                request.data(page)
            except Exception as err:
                logger.error("Caught error writing to %s: %s", args["dir"], err)
                self._thread_throw_error(
                    args["uuid"],
                    args["page"]["uuid"],
                    "Open file",
                    f"Error: unable to write to {args}{dir}.",
                )

        else:
            page = Page(
                filename=args["info"]["path"],
                dir=args["dir"],
                format=args["info"]["format"],
                width=args["info"]["width"][0],
                height=args["info"]["height"][0],
            )
            request.data(page.to_png(self.paper_sizes))

    def get_file_info(self, path, password, **kwargs):
        "get file info"
        return self.send("get_file_info", path, password, **kwargs)

    def import_file(self, **kwargs):
        "import file"
        callbacks = _note_callbacks2(kwargs)
        return self.send("import_file", kwargs, **callbacks)

    def save_pdf(self, **kwargs):
        "save pdf"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_pdf", kwargs, **callbacks)

    def do_save_pdf(self, request):
        "save PDF in thread"
        options = request.args[0]
        _ = gettext.gettext
        pagenr = 0
        pdf, error, message = None, None, None

        self.message = _("Setting up PDF")
        outdir = Path(options["dir"])
        filename = options["path"]
        if _need_temp_pdf(options["options"]):
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=".pdf", delete=False
            ).name

        metadata = {}
        if "metadata" in options and "ps" not in options:
            metadata = prepare_output_metadata("PDF", options["metadata"])

        with open(outdir / "origin_pre.pdf", "wb") as fhd:
            filenames = []
            sizes = []
            for page in options["list_of_pages"]:
                filenames.append(_write_image_object(page, options))
                sizes += list(page.matching_paper_sizes(self.paper_sizes).keys())
            sizes = list(set(sizes))  # make the keys unique
            if sizes:
                size = self.paper_sizes[sizes[0]]
                metadata["layout_fun"] = img2pdf.get_layout_fun(
                    (img2pdf.mm_to_pt(size["x"]), img2pdf.mm_to_pt(size["y"]))
                )
            fhd.write(img2pdf.convert(filenames, **metadata))
        ocrmypdf.api._pdf_to_hocr(
            outdir / "origin_pre.pdf",
            outdir,
            language="eng",
            skip_text=True,
        )
        for pagedata in options["list_of_pages"]:
            pagenr += 1
            if pagedata.text_layer:
                with open(outdir / f"{pagenr:-06}__ocr_hocr.hocr", "w") as pfh:
                    pfh.write(pagedata.export_hocr())
        #     self.progress = pagenr / (len(options["list_of_pages"]) + 1)
        #     self.message = _("Saving page %i of %i") % (pagenr, len(options["list_of_pages"]))
        #     # if status or _self["cancel"]:
        #     #     return

        ocrmypdf.api._hocr_to_ocr_pdf(outdir, filename, optimize=0)

        if (
            options is not None
            and "options" in options
            and options["options"] is not None
            and ("prepend" in options["options"] or "append" in options["options"])
        ):
            if self._append_pdf(filename, options):
                return

        if (
            options is not None
            and "options" in options
            and options["options"] is not None
            and "user-password" in options["options"]
        ):
            if self._encrypt_pdf(filename, options):
                return

        self._set_timestamp(options)
        if (
            options is not None
            and "options" in options
            and options["options"] is not None
            and "ps" in options["options"]
        ):
            self.message = _("Converting to PS")
            cmd = [options["options"]["pstool"], filename, options["options"]["ps"]]
            status, _stdout, error = exec_command(cmd, options["pidfile"])
            if status or error:
                logger.info(error)
                self._thread_throw_error(
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error converting PDF to PS: %s") % (error),
                )
                return

            _post_save_hook(options["options"]["ps"], options["options"])

        else:
            _post_save_hook(filename, options["options"])

    # https://py-pdf.github.io/fpdf2/Annotations.html
    def _add_annotations_to_pdf(self, page, gs_page):
        """Box is the same size as the page. We don't know the text position.
        Start at the top of the page (PDF coordinate system starts
        at the bottom left of the page)"""
        xresolution, yresolution, units = gs_page.get_resolution()
        height = px2pt(gs_page.height, yresolution)
        for box in Bboxtree(gs_page.annotations).get_bbox_iter():
            if box["type"] == "page" or "text" not in box or box["text"] == EMPTY:
                continue

            rgb = []
            for i in range(3):
                rgb.append(hex(ANNOTATION_COLOR[i : i + 2, 2]) / int("0xff", 0))

            annot = page.annotation()
            annot.markup(
                box["text"],
                _bbox2markup(xresolution, yresolution, height, len(box["bbox"])),
                "Highlight",
                color=rgb,
                opacity=0.5,
            )

    def _append_pdf(self, filename, options):
        if "prepend" in options["options"]:
            file1 = filename
            file2 = options["options"]["prepend"] + ".bak"
            bak = file2
            out = options["options"]["prepend"]
            message = _("Error prepending PDF: %s")
            logger.info("Prepending PDF")

        else:
            file2 = filename
            file1 = options["options"]["append"] + ".bak"
            bak = file1
            out = options["options"]["append"]
            message = _("Error appending PDF: %s")
            logger.info("Appending PDF")

        try:
            os.rename(out, bak)
        except ValueError:
            self._thread_throw_error(
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error creating backup of PDF"),
            )
            return

        (status, _stdout, error) = exec_command(
            ["pdfunite", file1, file2, out], options["pidfile"]
        )
        if status:
            logger.info(error)
            self._thread_throw_error(
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                message % (error),
            )
            return status

    def save_djvu(self, **kwargs):
        "save DjvU"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_djvu", kwargs, **callbacks)

    def do_save_djvu(self, request):
        "save DjvU in thread"
        args = request.args[0]
        page = 0
        filelist = []
        for pagedata in args["list_of_pages"]:
            page += 1
            self.progress = page / (len(args["list_of_pages"]) - 1 + 2)
            self.message = _("Writing page %i of %i") % (
                page,
                len(args["list_of_pages"]) - 1 + 1,
            )
            (djvu, error) = (None, None)
            try:
                djvu = tempfile.NamedTemporaryFile(dir=args["dir"], suffix=".djvu")

            except Exception as err:
                logger.error("Caught error writing DjVu: %s", err)
                self._thread_throw_error(
                    args["uuid"],
                    args["page"]["uuid"],
                    "Save file",
                    f"Caught error writing DjVu: {_}.",
                )
                error = True

            if error:
                return
            compression, filename, resolution = self._convert_image_for_djvu(
                pagedata, page, args
            )

            # Create the djvu
            status, _stdout, _stderr = exec_command(
                [compression, "-dpi", str(int(resolution)), filename, djvu.name],
                args["pidfile"],
            )
            size = os.path.getsize(djvu.name)
            if self.cancel:
                return
            if status != 0 or size == 0:
                logger.error(
                    "Error writing image for page %s of DjVu (process "
                    "returned %s, image size %s)",
                    page,
                    status,
                    size,
                )
                self._thread_throw_error(
                    args["uuid"],
                    args["page"]["uuid"],
                    "Save file",
                    _("Error writing DjVu"),
                )
                return

            filelist.append(djvu.name)
            self._add_txt_to_djvu(djvu, args["dir"], pagedata, args["uuid"])
            self._add_ann_to_djvu(djvu, args["dir"], pagedata, args["uuid"])

        self.progress = 1
        self.message = _("Merging DjVu")
        status, out, err = exec_command(
            ["djvm", "-c", args["path"], *filelist], args["pidfile"]
        )
        if self.cancel:
            return
        if status:
            logger.error("Error merging DjVu")
            self._thread_throw_error(
                args["uuid"],
                args["page"]["uuid"],
                "Save file",
                _("Error merging DjVu"),
            )

        self._add_metadata_to_djvu(args)
        self._set_timestamp(args)
        _post_save_hook(args["path"], args["options"])

    def _convert_image_for_djvu(self, pagedata, page, options):
        filename = pagedata.filename

        # Check the image depth to decide what sort of compression to use
        image = Image.open(filename)
        # if f"{e}":
        #     logger.error(e)
        #     self._thread_throw_error(
        #         options["uuid"],
        #         options["page"]["uuid"],
        #         "Save file",
        #         f"Error reading {filename}: {e}.",
        #     )
        #     return

        mode = image.mode
        compression, resolution, upsample = None, None, None

        # c44 and cjb2 do not support different resolutions in the x and y
        # directions, so resample
        xresolution, yresolution, units = pagedata.get_resolution()
        width, height = pagedata.width, pagedata.height
        if xresolution != yresolution:
            resolution = max(xresolution, yresolution)
            width *= resolution / xresolution
            height *= resolution / yresolution
            logger.info("Upsampling to %sx%s", resolution, resolution)
            image = image.resize((int(width), int(height)), resample=Image.BOX)
            upsample = True

        else:
            resolution = xresolution

        # c44 can only use pnm and jpg
        fformat = None
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            fformat = regex.group(1)

        if mode != "1":
            compression = "c44"
            if (
                not re.search(
                    r"(?:pnm|jpg)", fformat, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                or upsample
            ):
                pnm = tempfile.NamedTemporaryFile(
                    dir=options["dir"], suffix=".pnm", delete=False
                )
                image.save(pnm.name)
                # if f"{e}":
                #     logger.error(e)
                #     _thread_throw_error(
                #         self,
                #         options["uuid"],
                #         options["page"]["uuid"],
                #         "Save file",
                #         f"Error writing {pnm}: {e}.",
                #     )
                #     return

                filename = pnm.name

        # cjb2 can only use pnm and tif
        else:
            compression = "cjb2"
            if (
                not re.search(
                    r"(?:pnm|tif)", fformat, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                or (fformat == "pnm" and mode != "PseudoClass")
                or upsample
            ):
                pbm = tempfile.TemporaryFile(dir=options["dir"], suffix=".pbm")
                err = image.Write(filename=pbm)
                if f"{err}":
                    logger.error(err)
                    self._thread_throw_error(
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        f"Error writing {pbm}: {err}.",
                    )
                    return

                filename = pbm

        return compression, filename, resolution

    def _add_txt_to_djvu(self, djvu, dirname, pagedata, uid):
        if pagedata.text_layer is not None:
            txt = pagedata.export_djvu_txt()
            if txt == EMPTY:
                return
            logger.debug(txt)

            # Write djvusedtxtfile
            with tempfile.NamedTemporaryFile(
                mode="w", dir=dirname, suffix=".txt", delete=False
            ) as fhd:
                djvusedtxtfile = fhd.name
                fhd.write(txt)

            # Run djvusedtxtfile
            cmd = [
                "djvused",
                djvu.name,
                "-e",
                f"select 1; set-txt {djvusedtxtfile}",
                "-s",
            ]
            logger.info(cmd)
            try:
                subprocess.run(cmd, check=True)
            except ValueError:
                logger.error(
                    "Error adding text layer to DjVu page %s", pagedata["page_number"]
                )
                self._thread_throw_error(
                    uid,
                    pagedata["uuid"],
                    "Save file",
                    _("Error adding text layer to DjVu"),
                )

    def _add_ann_to_djvu(self, djvu, dirname, pagedata, uid):
        """FIXME - refactor this together with _add_txt_to_djvu"""
        if pagedata.annotations is not None:
            ann = pagedata.export_djvu_ann()
            if ann == EMPTY:
                return
            logger.debug(ann)

            # Write djvusedtxtfile
            with tempfile.NamedTemporaryFile(
                mode="w", dir=dirname, suffix=".txt", delete=False
            ) as fhd:
                djvusedtxtfile = fhd.name
                fhd.write(ann)

            # Run djvusedtxtfile
            cmd = [
                "djvused",
                djvu.name,
                "-e",
                f"select 1; set-ant {djvusedtxtfile}",
                "-s",
            ]
            logger.info(cmd)
            try:
                subprocess.run(cmd, check=True)
            except ValueError:
                logger.error(
                    "Error adding annotations to DjVu page %s",
                    pagedata["page_number"],
                )
                self._thread_throw_error(
                    uid,
                    pagedata["uuid"],
                    "Save file",
                    _("Error adding annotations to DjVu"),
                )

    def _add_metadata_to_djvu(self, options):
        if "metadata" in options and options["metadata"] is not None:
            metadata = prepare_output_metadata("DjVu", options["metadata"])

            # Write djvusedmetafile
            with tempfile.NamedTemporaryFile(
                mode="w", dir=options["dir"], suffix=".txt", delete=False
            ) as fhd:
                djvusedmetafile = fhd.name
                fhd.write("(metadata\n")

                # Write the metadata
                for key in metadata.keys():
                    val = metadata[key]

                    # backslash-escape any double quotes and bashslashes
                    val = re.sub(
                        r"\\", r"\\\\", val, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
                    )
                    val = re.sub(
                        r"\"", r"\\\"", val, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
                    )
                    fhd.write(f'{key} "{val}"\n')

                fhd.write(")\n")

            # Write djvusedmetafile
            cmd = [
                "djvused",
                "-e",
                f'"set-meta" {djvusedmetafile}',
                options["path"],
                "-s",
            ]
            subprocess.run(cmd, check=True)
            if self.cancel:
                return
            # if status:
            #     logger.error("Error adding metadata info to DjVu file")
            #     self._thread_throw_error(
            #         options["uuid"],
            #         options["page"]["uuid"],
            #         "Save file",
            #         _("Error adding metadata to DjVu"),
            #     )

    def _thread_import_pdf(self, request):
        args = request.args[0]
        warning_flag, xresolution, yresolution = None, None, None

        # Extract images from PDF
        if args["last"] >= args["first"] and args["first"] > 0:
            for i in range(args["first"], args["last"] + 1):
                cmd = [
                    "pdfimages",
                    "-f",
                    str(i),
                    "-l",
                    str(i),
                    "-list",
                    args["info"]["path"],
                ]
                if args["password"] is not None:
                    cmd.insert(1, "-upw")
                    cmd.insert(2, args["password"])

                out = subprocess.check_output(cmd, text=True)
                for line in re.split(r"\n", out):
                    xresolution, yresolution = line[70:75], line[76:81]
                    if re.search(
                        r"\d", xresolution, re.MULTILINE | re.DOTALL | re.VERBOSE
                    ):
                        xresolution, yresolution = float(xresolution), float(
                            yresolution
                        )
                        break

                cmd = [
                    "pdfimages",
                    "-f",
                    str(i),
                    "-l",
                    str(i),
                    args["info"]["path"],
                    "x",
                ]
                if args["password"] is not None:
                    cmd.insert(1, "-upw")
                    cmd.insert(2, args["password"])

                try:
                    subprocess.run(cmd, check=True)
                except:
                    self._thread_throw_error(
                        args["uuid"],
                        args["page"]["uuid"],
                        "Open file",
                        _("Error extracting images from PDF"),
                    )
                if self.cancel:
                    return

                html = tempfile.NamedTemporaryFile(dir=args["dir"], suffix=".html")
                cmd = [
                    "pdftotext",
                    "-bbox",
                    "-f",
                    str(i),
                    "-l",
                    str(i),
                    args["info"]["path"],
                    html.name,
                ]
                if args["password"] is not None:
                    cmd.insert(1, "-upw")
                    cmd.insert(2, args["password"])

                spo = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if self.cancel:
                    return
                if spo.returncode != 0:
                    self._thread_throw_error(
                        args["uuid"],
                        args["page"]["uuid"],
                        "Open file",
                        _("Error extracting text layer from PDF"),
                    )

                # Import each image
                images = glob.glob("x-??*.???")
                if len(images) != 1:
                    warning_flag = True
                for fname in images:
                    regex = re.search(
                        r"([^.]+)$", fname, re.MULTILINE | re.DOTALL | re.VERBOSE
                    )
                    if regex:
                        ext = regex.group(1)
                    try:
                        page = Page(
                            filename=fname,
                            dir=args["dir"],
                            delete=True,
                            format=image_format[ext],
                            resolution=(xresolution, yresolution, "PixelsPerInch"),
                        )
                        with open(html.name, "r") as fhd:
                            page.import_pdftotext(fhd.read())
                        request.data(page.to_png(self.paper_sizes))
                    except Exception as err:
                        logger.error("Caught error importing PDF: %s", err)
                        self._thread_throw_error(
                            args["uuid"],
                            args["page"]["uuid"],
                            "Open file",
                            _("Error importing PDF"),
                        )

            if warning_flag:
                request.data(
                    None,
                    #                    request.uuid,
                    #                    args["page"]["uuid"],
                    #                    "Open file",
                    _(
                        "Warning: gscan2pdf expects one image per page, but "
                        "this was not satisfied. It is probable that the PDF "
                        "has not been correctly imported. If you wish to add "
                        "scans to an existing PDF, use the prepend/append to "
                        "PDF options in the Save dialogue."
                    ),
                )

    def _set_timestamp(self, options):
        if (
            options is None
            or "options" not in options
            or options["options"] is None
            or "set_timestamp" not in options["options"]
            or not options["options"]["set_timestamp"]
            or "ps" in options["options"]
        ):
            return

        metadata = options["metadata"]
        adatetime = metadata["datetime"]
        adatetime = datetime.datetime(*adatetime)
        if "tz" in metadata:
            tzn = metadata["tz"]
            tzn = [0 if x is None else x for x in tzn]
            tzn = datetime.timedelta(
                days=tzn[2], hours=tzn[3], minutes=tzn[4], seconds=tzn[5]
            )
            adatetime -= tzn

        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        adatetime = (adatetime - epoch).total_seconds()
        if adatetime < 0:
            raise ValueError("Unable to set file timestamp for dates prior to 1970")
        os.utime(options["path"], (adatetime, adatetime))

    def _encrypt_pdf(self, filename, options):
        cmd = ["pdftk", filename, "output", options["path"]]
        if "user-password" in options["options"]:
            cmd += ["user_pw", options["options"]["user-password"]]

        spo = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if spo.returncode != 0:
            logger.info(spo.stderr)
            self._thread_throw_error(
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error encrypting PDF: %s") % (spo.stderr),
            )
            return spo.returncode

    def save_tiff(self, **kwargs):
        "save TIFF"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_tiff", kwargs, **callbacks)

    def do_save_tiff(self, request):
        "save TIFF in thread"
        options = request.args[0]

        page = 0
        filelist = []
        for pagedata in options["list_of_pages"]:
            page += 1
            self.progress = (page - 1) / (len(options["list_of_pages"]) + 1)
            # self.message = _("Converting image %i of %i to TIFF") % (
            #     page,
            #     len(options["list_of_pages"]) - 1 + 1,
            # )
            filename = pagedata.filename
            if not re.search(
                r"[.]tif", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            ) or (
                "compression" in options["options"]
                and options["options"]["compression"] == "jpeg"
            ):
                (tif, error) = (None, None)
                try:
                    tif = tempfile.NamedTemporaryFile(
                        dir=options["dir"], suffix=".tif", delete=False
                    )
                except Exception as err:
                    logger.error("Error writing TIFF: %s", err)
                    self._thread_throw_error(
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        f"Error writing TIFF: {_}.",
                    )
                    error = True

                if error:
                    return
                xresolution, yresolution, units = pagedata.resolution

                # Convert to tiff

                depth = []
                if "compression" in options["options"]:
                    if options["options"]["compression"] == "jpeg":
                        depth = ["-depth", "8"]

                    elif re.search(
                        r"g[34]",
                        options["options"]["compression"],
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        depth = ["-threshold", "40%", "-depth", "1"]

                cmd = [
                    "convert",
                    filename,
                    "-units",
                    "PixelsPerInch",
                    "-density",
                    f"{xresolution}x{yresolution}",
                    *depth,
                    tif.name,
                ]
                subprocess.run(cmd, check=True)
                if self.cancel:
                    return
                # if status:
                #     logger.error("Error writing TIFF")
                #     self._thread_throw_error(
                #         options["uuid"],
                #         options["page"]["uuid"],
                #         "Save file",
                #         _("Error writing TIFF"),
                #     )
                #     return

                filename = tif.name

            filelist.append(filename)

        compression = []
        if "compression" in options["options"]:
            compression = ["-c", options["options"]["compression"]]
            if options["options"]["compression"] == "jpeg":
                compression[1] += f":{options['options']['quality']}"
                compression.append(["-r", "16"])

        # Create the tiff
        self.progress = 1
        # self.message = _("Concatenating TIFFs")
        cmd = ["tiffcp", *compression, *filelist, options["path"]]
        subprocess.run(cmd, check=True)
        if self.cancel:
            return
        # if status or error != EMPTY:
        #     logger.info(error)
        #     self._thread_throw_error(
        #         options["uuid"],
        #         options["page"]["uuid"],
        #         "Save file",
        #         _("Error compressing image: %s") % (error),
        #     )
        #     return

        if "ps" in options["options"]:
            # self.message = _("Converting to PS")
            cmd = ["tiff2ps", "-3", options["path"], "-O", options["options"]["ps"]]
            status, _stdout, error = exec_command(cmd, options["pidfile"])
            if status or error:
                logger.info(error)
                self._thread_throw_error(
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error converting TIFF to PS: %s") % (error),
                )
                return

            _post_save_hook(options["options"]["ps"], options["options"])

        else:
            _post_save_hook(options["path"], options["options"])

    def save_image(self, **kwargs):
        "save pages as image files"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_image", kwargs, **callbacks)

    def do_save_image(self, request):
        "save pages as image files in thread"
        options = request.args[0]

        if len(options["list_of_pages"]) == 1:
            status, _stdout, _stderr = exec_command(
                [
                    "convert",
                    options["list_of_pages"][0].filename,
                    "-density",
                    str(options["list_of_pages"][0].resolution[0])
                    + f'x{options["list_of_pages"][0].resolution[1]}',
                    options["path"],
                ],
                options["pidfile"],
            )
            # if _self["cancel"]:
            #     return
            if status:
                self._thread_throw_error(
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error saving image"),
                )

            _post_save_hook(options["list_of_pages"][0].filename, options["options"])

        else:
            current_filename = None
            i = 1
            for _ in options["list_of_pages"]:
                current_filename = options["path"] % (i)
                i += 1
                status = exec_command(
                    [
                        "convert",
                        _["filename"],
                        "-density",
                        _["xresolution"] + "x" + _["yresolution"],
                        current_filename,
                    ],
                    options["pidfile"],
                )
                if _self["cancel"]:
                    return
                if status:
                    self._thread_throw_error(
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        _("Error saving image"),
                    )

                _post_save_hook(_["filename"], options["options"])

    def save_text(self, **kwargs):
        "save text file"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_text", kwargs, **callbacks)

    def do_save_text(self, request):
        "save text file in thread"
        options = request.args[0]

        string = EMPTY
        for page in options["list_of_pages"]:
            string += page.export_text()
            if self.cancel:
                return

        with open(options["path"], "w") as fhd:
            fhd.write(string)

        _post_save_hook(options["path"], options["options"])

    def save_hocr(self, **kwargs):
        "save hocr file"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_hocr", kwargs, **callbacks)

    def do_save_hocr(self, request):
        "save hocr file in thread"
        options = request.args[0]

        with open(options["path"], "w") as fhd:
            written_header = False
            for page in options["list_of_pages"]:
                hocr = page.export_hocr()
                regex = re.search(
                    r"([\s\S]*<body>)([\s\S]*)<\/body>",
                    hocr,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                if hocr is not None and regex:
                    header = regex.group(1)
                    hocr_page = regex.group(2)
                    if not written_header:
                        fhd.write(header)
                        written_header = True

                    fhd.write(hocr_page)
                    if self.cancel:
                        return

            if written_header:
                fhd.write("</body>\n</html>\n")

        _post_save_hook(options["path"], options["options"])

    def rotate(self, **kwargs):
        "rotate page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("rotate", kwargs, **callbacks)

    def do_rotate(self, request):
        "rotate page in thread"
        options = request.args[0]
        angle, page = options["angle"], options["page"]

        if self._page_gone("rotate", options["uuid"], page):
            return
        filename = page.filename
        logger.info("Rotating %s by %s degrees", filename, angle)
        image = page.im_object().rotate(angle, expand=True)

        if self.cancel:
            return
        regex = re.search(r"([.]\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        fnm = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            dir=options["dir"], suffix=suffix, delete=False
        )
        image.save(fnm.name)

        if self.cancel:
            return
        page.filename = fnm.name
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        if angle == _90_DEGREES or angle == _270_DEGREES:
            page.width, page.height = page.height, page.width
            page.resolution = (
                page.resolution[1],
                page.resolution[0],
                page.resolution[2],
            )
        return page

    def do_cancel(self, _request):
        "cancel running tasks"
        self.cancel = False

    def _page_gone(self, process, uid, page):
        if not os.path.isfile(
            page.filename
        ):  # in case file was deleted after process started
            err = f"Page for process {uid} no longer exists. Cannot {process}."
            logger.error(err)
            self._thread_throw_error(uid, page["uuid"], process, err)
            return True
        return False

    def set_paper_sizes(self, paper_sizes):
        "set paper sizes"
        self.paper_sizes = paper_sizes
        return self.send("paper_sizes", paper_sizes)

    def do_set_paper_sizes(self, request):
        "set paper sizes in thread"
        paper_sizes = request.args[0]
        self.paper_sizes = paper_sizes

    def user_defined(self, **kwargs):
        "run user defined command on page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("user_defined", kwargs, **callbacks)

    def do_user_defined(self, request):
        "run user defined command on page in thread"
        options = request.args[0]

        if self._page_gone("user-defined", options["uuid"], options["page"]):
            return

        infile = options["page"].filename
        suffix = None
        regex = re.search(r"([.]\w*)$", infile, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        try:
            out = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=suffix, delete=False
            )
            if re.search("%o", options["command"]):
                options["command"] = re.sub(
                    r"%o",
                    out.name,
                    options["command"],
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                options["command"] = re.sub(
                    r"%i",
                    infile,
                    options["command"],
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )

            else:
                if not shutil.copy2(infile, out.name):
                    self._thread_throw_error(
                        options["uuid"],
                        options["page"]["uuid"],
                        "user-defined",
                        _("Error copying page"),
                    )
                    return

                options["command"] = re.sub(
                    r"%i",
                    out.name,
                    options["command"],
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )

            options["command"] = re.sub(
                r"%r",
                rf"{options['page'].resolution[0]}",
                options["command"],
                flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            # options["command"] = options["command"].split(" ")
            sbp = subprocess.run(
                options["command"],
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )
            if self.cancel:
                return
            logger.info("stdout: %s", sbp.stdout)
            logger.info("stderr: %s", sbp.stderr)

            # don't return in here, just in case we can ignore the error -
            # e.g. theming errors from gimp
            if sbp.stderr != EMPTY:
                request.data(
                    {"type": "message", "info": sbp.stderr}
                    # options["uuid"],
                    # options["page"].uuid,
                    # "user-defined",
                )

            # Get file type
            image = Image.open(out.name)

            # assume the resolution hasn't changed
            new = Page(
                filename=out.name,
                dir=options["dir"],
                delete=True,
                format=image.format,
                resolution=options["page"].resolution,
            )

            # Copy the OCR output
            try:
                new.bboxtree = options["page"].bboxtree
            except AttributeError:
                pass

            # reuse uuid so that the process chain can find it again
            new.uuid = options["page"].uuid
            request.data(
                {
                    "type": "page",
                    "uuid": options["uuid"],
                    "page": new,
                    "info": {"replace": new.uuid},
                }
            )

        except Exception as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            request.error(
                f"Error creating file in {options['dir']}: {err}.",
            )

    def analyse(self, **kwargs):
        "analyse page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("analyse", kwargs, **callbacks)

    def do_analyse(self, request):
        "analyse page in thread"
        options = request.args[0]
        list_of_pages = options["list_of_pages"]

        i = 1
        total = len(list_of_pages)
        for page in list_of_pages:
            self.progress = (i - 1) / total
            self.message = _("Analysing page %i of %i") % (i, total)
            i += 1

            image = page.im_object()

            if self.cancel:
                return
            stat = ImageStat.Stat(image)
            mean, stddev = stat.mean, stat.stddev
            logger.info("std dev: %s mean: %s", stddev, mean)
            if self.cancel:
                return

            # TODO add any other useful image analysis here e.g. is the page mis-oriented?
            #  detect mis-orientation possible algorithm:
            #   blur or low-pass filter the image (so words look like ovals)
            #   look at few vertical narrow slices of the image and get the Standard Deviation
            #   if most of the Std Dev are high, then it might be portrait
            page.mean = mean
            page.std_dev = stddev
            page.analyse_time = datetime.datetime.now()
            request.data(page)

    def threshold(self, **kwargs):
        "threshold page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("threshold", kwargs, **callbacks)

    def do_threshold(self, request):
        "threshold page in thread"
        options = request.args[0]
        threshold, page = (options["threshold"], options["page"])

        if self._page_gone("threshold", options["uuid"], page):
            return
        if self.cancel:
            return
        filename = page.filename
        logger.info("Threshold %s with %s", filename, threshold)
        image = page.im_object()

        # To grayscale
        image = image.convert("L")
        # Threshold
        image = image.point(lambda p: 255 if p > threshold else 0)
        # To mono
        image = image.convert("1")

        if self.cancel:
            return

        fnm = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            dir=options["dir"], suffix=".png", delete=False
        )
        image.save(fnm.name)

        if self.cancel:
            return
        page.filename = fnm.name
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        return page

    def brightness_contrast(self, **kwargs):
        "adjust brightness and contrast"
        callbacks = _note_callbacks2(kwargs)
        return self.send("brightness_contrast", kwargs, **callbacks)

    def do_brightness_contrast(self, request):
        "adjust brightness and contrast in thread"
        options = request.args[0]
        brightness, contrast, page = (
            options["brightness"],
            options["contrast"],
            options["page"],
        )

        if self._page_gone("brightness-contrast", options["uuid"], options["page"]):
            return

        filename = page.filename
        logger.info(
            "Enhance %s with brightness %s, contrast %s", filename, brightness, contrast
        )
        image = page.im_object()
        if self.cancel:
            return

        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)

        if self.cancel:
            return

        image.save(filename)
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        return page

    def negate(self, **kwargs):
        "negate page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("negate", kwargs, **callbacks)

    def do_negate(self, request):
        "negate page in thread"
        options = request.args[0]
        page = options["page"]

        if self._page_gone("negate", options["uuid"], page):
            return

        filename = page.filename
        logger.info("Invert %s", filename)
        image = page.im_object()
        image = ImageOps.invert(image)

        if self.cancel:
            return

        image.save(filename)
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        return page

    def unsharp(self, **kwargs):
        "run unsharp mask"
        callbacks = _note_callbacks2(kwargs)
        return self.send("unsharp", kwargs, **callbacks)

    def do_unsharp(self, request):
        "run unsharp mask in thread"
        options = request.args[0]
        page = options["page"]
        radius = options["radius"]
        percent = options["percent"]
        threshold = options["threshold"]

        if self._page_gone("unsharp", options["uuid"], page):
            return

        filename = page.filename
        logger.info(
            "Unsharp mask %s radius %s percent %s threshold %s",
            filename,
            radius,
            percent,
            threshold,
        )
        image = page.im_object()
        image = image.filter(
            ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
        )

        if self.cancel:
            return

        image.save(filename)
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        return page

    def crop(self, **kwargs):
        "crop page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("crop", kwargs, **callbacks)

    def do_crop(self, request):
        "crop page in thread"
        options = request.args[0]
        page = options["page"]
        left = options["x"]
        top = options["y"]
        width = options["w"]
        height = options["h"]

        if self._page_gone("crop", options["uuid"], options["page"]):
            return

        filename = page.filename
        logger.info("Crop %s x %s y %s w %s h %s", filename, left, top, width, height)
        image = page.im_object()

        image = image.crop((left, top, left + width, top + height))

        if self.cancel:
            return

        page.width = image.width
        page.height = image.height

        if page.text_layer is not None:
            bboxtree = Bboxtree(page.text_layer)
            page.text_layer = bboxtree.crop(left, top, width, height).json()

        image.save(filename)
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        return page

    def split_page(self, **kwargs):
        "split page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("split_page", kwargs, **callbacks)

    def do_split_page(self, request):
        "split page in thread"
        options = request.args[0]
        page = options["page"]

        if self._page_gone("split", options["uuid"], options["page"]):
            return

        filename = page.filename
        filename2 = filename
        image = page.im_object()
        image2 = image.copy()

        # split the image
        if options["direction"] == "v":
            width = options["position"]
            height = image.height
            right = width
            bottom = 0
            width2 = image.width - width
            height2 = height
        else:
            width = image.width
            height = options["position"]
            right = 0
            bottom = height
            width2 = width
            height2 = image.height - height

        image = image.crop((0, 0, width, height))
        image2 = image2.crop((right, bottom, right + width2, bottom + height2))

        if self.cancel:
            return

        # Write them
        suffix = None
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            image.save(filename)

            filename2 = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            image2.save(filename2)

        logger.info(
            "Splitting in direction %s @ %s -> %s + %s",
            options["direction"],
            options["position"],
            filename,
            filename2,
        )
        if self.cancel:
            return
        page.filename = filename.name
        page.width = image.width
        page.height = image.height
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        # split doesn't change the resolution, so we can safely copy it
        new2 = Page(
            filename=filename2.name,
            dir=options["dir"],
            delete=True,
            format=page.format,
            resolution=page.resolution,
            dirty_time=page.dirty_time,
        )
        if page.text_layer:
            bboxtree = Bboxtree(page.text_layer)
            bboxtree2 = Bboxtree(page.text_layer)
            page.text_layer = bboxtree.crop(0, 0, width, height).json()
            new2.text_layer = bboxtree2.crop(right, bottom, width2, height2).json()

        request.data(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": page,
                "info": {"replace": page.uuid},
            }
        )
        request.data(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": new2,
                "info": {"insert-after": page.uuid},
            }
        )

    def tesseract(self, **kwargs):
        "run tesseract"
        callbacks = _note_callbacks2(kwargs)
        return self.send("tesseract", kwargs, **callbacks)

    def do_tesseract(self, request):
        "run tesseract in thread"
        options = request.args[0]
        page, language = (options["page"], options["language"])

        if self._page_gone("tesseract", options["uuid"], options["page"]):
            return

        if self.cancel:
            return

        paths = glob.glob("/usr/share/tesseract-ocr/*/tessdata")
        if not paths:
            request.error(_("tessdata directory not found"))
        with tesserocr.PyTessBaseAPI(lang=language, path=paths[-1]) as api:
            output = "image_out"

            api.SetVariable("tessedit_create_hocr", "T")
            _pp = api.ProcessPages(output, page.filename)

            # Unnecessary filesystem write/read
            path_hocr = Path(output).with_suffix(".hocr")
            hocr = path_hocr.read_text()
            path_hocr.unlink()

            page.import_hocr(hocr)
            page.ocr_flag = True
            page.ocr_time = datetime.datetime.now()

        if self.cancel:
            return

        return page

    def unpaper(self, **kwargs):
        "run unpaper"
        callbacks = _note_callbacks2(kwargs)
        return self.send("unpaper", kwargs, **callbacks)

    def do_unpaper(self, request):
        "run unpaper in thread"
        options = request.args[0]

        if self._page_gone("unpaper", options["uuid"], options["page"]):
            return

        filename = options["page"].filename
        infile = None
        try:
            if not re.search(
                r"[.]pnm$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                image = options["page"].im_object()
                depth = options["page"].get_depth()

                suffix = ".pbm"
                if depth > 1:
                    suffix = ".pnm"

                # Temporary filename for new file
                infile = tempfile.NamedTemporaryFile(
                    dir=options["dir"],
                    suffix=suffix,
                    delete=False,
                ).name

                logger.debug("Converting %s -> %s for unpaper", filename, infile)
                image.save(infile)

            else:
                infile = filename
            options["options"]["command"][-3] = infile

            out = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=".pnm", delete=False
            ).name
            options["options"]["command"][-2] = out

            out2 = EMPTY
            index = options["options"]["command"].index("--output-pages")
            if options["options"]["command"][index + 1] == "2":
                out2 = tempfile.NamedTemporaryFile(
                    dir=options["dir"], suffix=".pnm", delete=False
                ).name
                options["options"]["command"][-1] = out2
            else:
                del options["options"]["command"][-1]

            spo = subprocess.run(
                options["options"]["command"],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(spo.stdout)
            if spo.stderr:
                logger.error(spo.stderr)
                request.data(spo.stderr)
                # self._thread_throw_error(
                #     options["uuid"], options["page"]["uuid"], "unpaper", stderr
                # )
                if not os.path.getsize(out):
                    return

            if self.cancel:
                return
            spo.stdout = re.sub(
                r"Processing[ ]sheet.*[.]pnm\n",
                r"",
                spo.stdout,
                count=1,
                flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if spo.stdout:
                logger.warning(spo.stdout)
                request.data(spo.stdout)
                # self._thread_throw_error(
                #     options["uuid"], options["page"]["uuid"], "unpaper", stdout
                # )
                if not os.path.getsize(out):
                    return

            if (
                options["options"]["command"][index + 1] == "2"
                and "direction" in options["options"]
                and options["options"]["direction"] == "rtl"
            ):
                out, out2 = out2, out

            # unpaper doesn't change the resolution, so we can safely copy it
            new = Page(
                filename=out,
                dir=options["dir"],
                delete=True,
                format="Portable anymap",
                resolution=options["page"].resolution,
                uuid=options["page"].uuid,
                dirty_time=datetime.datetime.now(),  # flag as dirty
            )
            request.data(
                {
                    "type": "page",
                    "uuid": options["uuid"],
                    "page": new,
                    "info": {"replace": options["page"].uuid},
                }
            )
            if out2:
                new2 = Page(
                    filename=out2,
                    dir=options["dir"],
                    delete=True,
                    format="Portable anymap",
                    resolution=options["page"].resolution,
                    dirty_time=datetime.datetime.now(),  # flag as dirty
                )
                request.data(
                    {
                        "type": "page",
                        "uuid": options["uuid"],
                        "page": new2,
                        "info": {"insert-after": new.uuid},
                    }
                )

        except Exception as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            self._thread_throw_error(
                options["uuid"],
                options["page"]["uuid"],
                "unpaper",
                f"Error creating file in {options}{dir}: {err}.",
            )


class Document(SimpleList):
    "a Document is a simple list of pages"
    # easier to extract strings with xgettext
    # To get TRUE and FALSE. 1.210 necessary for Glib::SOURCE_REMOVE and Glib::SOURCE_CONTINUE

    # To create temporary files
    # Split filename into dir, file, ext

    # For session files

    # for gensym
    # For size method for page numbering issues

    # for $PROCESS_ID, $INPUT_RECORD_SEPARATOR
    # $CHILD_ERROR

    # to deal with utf8 in filenames

    jobs_completed = 0
    jobs_total = 0
    uuid_object = uuid.uuid1()
    # Default thumbnail sizes
    heightt = THUMBNAIL
    widtht = THUMBNAIL
    selection_changed_signal = None
    paper_sizes = {}

    def on_row_changed(self, path, _iter, data):
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
        for prop in options.keys():
            setattr(self, prop, options[prop])

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

        def drag_data_get_callback(tree, context, sel):
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
        return self.thread.send("set_paper_sizes", paper_sizes)

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

            jobs_completed = 0
            jobs_total = 0

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
                    del self.running_pids[pidfile]

        # Add a cancel request to ensure the reply is not blocked
        logger.info("Requesting cancel")
        return self.thread.send("cancel", finished_callback=cancel_callback)

    def create_pidfile(self, options):
        "create file in which to store the PID"
        pidfile = None
        try:
            pidfile = tempfile.TemporaryFile(dir=self.dir, suffix=".pid")
        except Exception as err:
            logger.error("Caught error writing to %s: %s", self.dir, err)
            if "error_callback" in options:
                options["error_callback"](
                    options["page"] if "page" in options else None,
                    "create PID file",
                    f"Error: unable to write to {self.dir}.",
                )

        return pidfile

    def import_files(self, **options):
        """To avoid race condtions importing multiple files,
        run get_file_info on all files first before checking for errors and importing"""
        info = []
        options["passwords"] = []
        for i in range(len(options["paths"])):
            self._get_file_info_finished_callback1(i, info, options)

    def _get_file_info_finished_callback1(self, i, infolist, options):
        path = options["paths"][i]

        # File in which to store the process ID
        # so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        # uid = self._note_callbacks(options)

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

        return self.thread.get_file_info(
            path,
            # "pidfile": f"{pidfile}",
            # # "uuid": uid,
            options["passwords"][i] if i < len(options["passwords"]) else None,
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            running_callback=options["running_callback"]
            if "running_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=_select_next_finished_callback,
        )

    def _get_file_info_finished_callback2(self, info, options):
        if len(info) > 1:
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

                elif i["pages"] > 1:
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
            for i in range(len(info)):
                if "metadata_callback" in options:
                    options["metadata_callback"](_extract_metadata(info[i]))

                if i == len(info) - 1:
                    options["finished_callback"] = finished_callback

                self.import_file(info=info[i], first_page=1, last_page=1, **options)

        elif info[0]["format"] == "session file":
            self.open_session_file(info=info[0]["path"], **options)

        else:
            if "metadata_callback" in options and options["metadata_callback"]:
                options["metadata_callback"](_extract_metadata(info[0]))

            first_page = 1
            last_page = info[0]["pages"]
            if (
                "pagerange_callback" in options
                and options["pagerange_callback"]
                and last_page > 1
            ):
                first_page, last_page = options["pagerange_callback"](info[0])
                if (first_page is None) or (last_page is None):
                    return

            password = (
                options["passwords"][0]
                if "passwords" in options and options["passwords"]
                else None
            )
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

    def _note_callbacks(self, options):
        "create the mark_saved callback if necessary"
        if "mark_saved" in options and options["mark_saved"]:

            def mark_saved_callback(_data):
                # list_of_pages is frozen,
                # so find the original pages from their uuids
                for page in options["list_of_pages"]:
                    page.saved = True

            options["mark_saved_callback"] = mark_saved_callback

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
                self.add_page(None, response.info, None)
            except AttributeError:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        def _import_file_finished_callback(response):
            if "finished_callback" in options:
                options["finished_callback"](response)

        uid = self.thread.import_file(
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
        options = defaultdict(None, **options)

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

            def to_png_finished_callback(response):
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
            # self.data[0][2].im_object().save("before_rotate.png")

            def rotate_finished_callback(response):
                # self.data[0][2].im_object().save("after_rotate.png")
                # del options["rotate"]
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

            def udt_finished_callback(response):
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

            def ocr_finished_callback(response):
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

        # Interface to frontend
        fhd = open(options["filename"], mode="r")

        # Read without blocking
        size = 0

        def file_changed_callback(fileno, condition, *data):
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
                    fhd = open(options["filename"], mode="ab")
                    data = [1] * (pad * BITS_PER_BYTE + 1)
                    fhd.write(struct.pack("%db" % (len(data)), *data))
                    fhd.close()
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
                index = self.add_page("none", page, options["page"])
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
        elif i < 0 or (step > 0 and self.data[i][0] < start):
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
            return

        for i, row in enumerate(self.data):
            if str(uid) == str(row[2].uuid):
                return i

    def add_page(self, process_uuid, new_page, ref):
        "Add a new page to the document"
        i, pagenum = None, None

        # FIXME: This is really hacky to allow import_scan() to specify the page number
        if not isinstance(ref, dict):
            pagenum = ref
            ref = None

        if ref is not None:
            for key in ["replace", "insert-after"]:
                if key in ref and ref[key] is not None:
                    uid = ref[key]
                    i = self.find_page_by_uuid(uid)
                    if i is None:
                        logger.error("Requested page %s does not exist.", uid)
                        return NOT_FOUND
                    break

        # Move the temp file from the thread to a temp object that will be
        # automatically cleared up
        # if type(page["filename"]) == "File::Temp":
        #     new = page
        # else:
        #     try:
        #         new = page.thaw()
        #     except:
        #         _throw_error(
        #             process_uuid,
        #             page["uuid"],
        #             EMPTY,
        #             f"Caught error writing to {self}->{dir}: {_}",
        #         )

        #     if new is None:
        #         return

        # Block the row-changed signal whilst adding the scan (row) and sorting it.
        if self.row_changed_signal is not None:
            self.get_model().handler_block(self.row_changed_signal)

        xresolution, yresolution, units = new_page.get_resolution(self.paper_sizes)
        thumb = new_page.get_pixbuf_at_scale(self.heightt, self.widtht)

        # Add to the page list
        if i is None:
            if pagenum is None:
                pagenum = len(self.data) + 1
            self.data.append([pagenum, thumb, new_page])
            model = self.get_model()
            row = model[model.iter_nth_child(None, 0)]
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
        if self.selection_changed_signal is not None:
            self.get_selection().handler_block(self.selection_changed_signal)

        self.get_selection().unselect_all()
        self.manual_sort_by_column(0)
        if self.selection_changed_signal is not None:
            self.get_selection().handler_unblock(self.selection_changed_signal)

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

        # Due to the sort, must search for new page
        page_selection = [0]

        # $page[0] < $#{$self -> {data}} needed to prevent infinite loop in case of
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
            return
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
            if how == "after" or how == "into-or-after":
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

    def delete_selection(self, context=None):
        "Delete the selected pages"

        # The drag-data-delete callback seems to be fired twice. Therefore, create
        # a hash of the context hashes and ignore the second drop. There must be a
        # less hacky way of solving this. FIXME
        if context is not None:
            if context in self.context:
                del self.context
                return

            else:
                self.context[context] = 1

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

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        return self.thread.save_pdf(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            metadata=options["metadata"] if "metadata" in options else None,
            options=options["options"] if "options" in options else None,
            dir=self.dir,
            pidfile=pidfile,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def save_djvu(self, **options):
        "save the given pages as DjVu"

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        return self.thread.save_djvu(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            metadata=options["metadata"] if "metadata" in options else None,
            options=options["options"] if "options" in options else None,
            dir=self.dir,
            pidfile=pidfile,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def save_tiff(self, **options):
        "save the given pages as TIFF"

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        return self.thread.save_tiff(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options["options"] if "options" in options else None,
            dir=self.dir,
            pidfile=pidfile,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def rotate(self, **options):
        "rotate given page"
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        return self.thread.rotate(
            angle=options["angle"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def save_image(self, **options):
        "save the given pages as image files"

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        return self.thread.save_image(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options["options"] if "options" in options else None,
            pidfile=pidfile,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def scans_saved(self):
        "Check that all pages have been saved"
        for row in self:
            if not row[2].saved:
                return False
        return True

    def save_text(self, **options):
        "save a text file from the given pages"
        return self.thread.save_text(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options["options"] if "options" in options else None,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def save_hocr(self, **options):
        "save an hocr file from the given pages"
        return self.thread.save_hocr(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            options=options["options"] if "options" in options else None,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            mark_saved_callback=options["mark_saved_callback"]
            if "mark_saved_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def analyse(self, **options):
        "analyse given page"
        return self.thread.analyse(
            list_of_pages=options["list_of_pages"],
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def threshold(self, **options):
        "threshold given page"
        return self.thread.threshold(
            threshold=options["threshold"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def brightness_contrast(self, **options):
        "adjust brightness & contrast of given page"
        return self.thread.brightness_contrast(
            brightness=options["brightness"],
            contrast=options["contrast"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def negate(self, **options):
        "negate given page"
        return self.thread.negate(
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def unsharp(self, **options):
        "run unsharp mask on given page"
        return self.thread.unsharp(
            radius=options["radius"],
            percent=options["percent"],
            threshold=options["threshold"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def crop(self, **options):
        "crop page"
        return self.thread.crop(
            x=options["x"],
            y=options["y"],
            w=options["w"],
            h=options["h"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def split_page(self, **options):
        """split the given page either vertically or horizontally, creating an
        additional page"""

        # FIXME: duplicate to _import_file_data_callback()
        def _split_page_data_callback(response):
            if response.info["type"] == "page":
                self.add_page(None, response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        return self.thread.split_page(
            direction=options["direction"],
            position=options["position"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            data_callback=_split_page_data_callback,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def to_png(self, options):
        "convert the given page to png"
        return self.thread.to_png(
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
        )

    def tesseract(self, **options):
        "run tesseract on the given page"
        return self.thread.tesseract(
            language=options["language"],
            page=options["page"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            display_callback=options["display_callback"]
            if "display_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def ocr_pages(self, **options):
        "Wrapper for the various ocr engines"
        for page in options["pages"]:
            options["page"] = page
            if options["engine"] == "tesseract":
                self.tesseract(**options)

    def unpaper(self, **options):
        "run unpaper on the given page"
        options = defaultdict(None, **options)

        # FIXME: duplicate to _import_file_data_callback()
        def _unpaper_data_callback(response):
            if isinstance(response.info, dict) and "page" in response.info:
                self.add_page(None, response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        return self.thread.unpaper(
            page=options["page"],
            options=options["options"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
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
        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return

        # FIXME: duplicate to _import_file_data_callback()
        def _user_defined_data_callback(response):
            if response.info["type"] == "page":
                self.add_page(None, response.info["page"], response.info["info"])
            else:
                if "logger_callback" in options:
                    options["logger_callback"](response)

        return self.thread.user_defined(
            page=options["page"],
            command=options["command"],
            dir=self.dir,
            uuid=self._note_callbacks(options),
            pidfile=pidfile,
            queued_callback=options["queued_callback"]
            if "queued_callback" in options
            else None,
            started_callback=options["started_callback"]
            if "started_callback" in options
            else None,
            error_callback=options["error_callback"]
            if "error_callback" in options
            else None,
            data_callback=_user_defined_data_callback,
            finished_callback=options["finished_callback"]
            if "finished_callback" in options
            else None,
        )

    def save_session(self, filename=None, version=None):
        """Dump $self to a file.
        If a filename is given, zip it up as a session file
        Pass version to allow us to mock different session version and to be able to
        test opening old sessions."""
        self.remove_corrupted_pages()
        session, filenamelist = {}, []
        for i in range(len(self.data)):
            if self.data[i][0] not in session:
                session[self.data[i][0]] = {}
            session[self.data[i][0]]["filename"] = self.data[i][2].filename
            filenamelist.append(self.data[i][2].filename)
            for key in self.data[i][2].keys():
                if key != "filename":
                    session[self.data[i][0]][key] = self.data[i][2][key]

        filenamelist.append(os.path.join(self.dir, "session"))
        selection = self.get_selected_indices()
        session["selection"] = selection
        if version is not None:
            session["version"] = version
        # store(session, os.path.join(self.dir, "session"))
        if filename is not None:
            tar = tarfile.TarFile()
            tar.add_files(filenamelist)
            tar.write(filename, True, EMPTY)
            for i in range(len(self.data)):
                self.data[i][2].saved = True

    def open_session_file(self, options):
        "open session file"
        if "info" not in options:
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", "Error: session file not supplied."
                )

            return

        tar = tarfile.open(options["info"], True)
        filenamelist = tar.list_files()
        sessionfile = [x for x in filenamelist if re.search(r"\/session$", x)]
        sesdir = os.path.join(self.dir, os.path.dirname(sessionfile[0]))
        for filename in filenamelist:
            tar.extract_file(filename, os.path.join(sesdir, os.path.basename(filename)))

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

        # hocr -> bboxtree
        if "version" not in sessionref:
            logger.info("Restoring pre-2.8.1 session file.")
            for key in sessionref.keys():
                if type(sessionref[key]) == "HASH" and "hocr" in sessionref[key]:
                    tree = Bboxtree()
                    if re.search(
                        r"<body>[\s\S]*<\/body>",
                        sessionref[key]["hocr"],
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        tree.from_hocr(sessionref[key]["hocr"])

                    else:
                        tree.from_text(sessionref[key]["hocr"])

                    sessionref[key]["text_layer"] = tree.json()
                    del sessionref[key]["hocr"]

        else:
            logger.info(
                "Restoring v%s->%s session file.", sessionref, session["version"]
            )

        session = sessionref

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

            try:
                page = Page(session[pagenum])

                # At some point the main window widget was being stored on the
                # Page object. Restoring this and dumping it via Dumper segfaults.
                # This is tested in t/175_open_session2.t

                if "window" in page:
                    del page["window"]
                thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
                self.data.append([pagenum, thumb, page])

            except:
                if options["error_callback"]:
                    options["error_callback"](
                        None,
                        "Open file",
                        _("Error importing page %d. Ignoring.") % (pagenum),
                    )

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
            else:
                error_callback(None, "Get page", _("No pages to process"))
        elif page_range == "selected":
            index = self.get_selected_indices()
            if len(index) == 0:
                error_callback(None, "Get page", _("No pages selected"))
        return index

    def set_dir(self, dirname):
        "Set session dir"
        self.dir = dirname

    def _thread_throw_error(self, uid, page_uuid, process, message):
        self.return_queue.enqueue(
            {
                "type": "error",
                "uuid": uid,
                "page": page_uuid,
                "process": process,
                "message": message,
            }
        )

    def _write_file(self, fhd, filename, data, uid):
        if not fhd.write(data):
            self._thread_throw_error(
                uid, None, "Save file", _("Can't write to file: %s") % (filename)
            )
            return False

        return True


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

        else:
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
    (text) = None
    if type(file) == "GLOB":
        text = file

    else:
        try:
            fhd = open("<:encoding(UTF8)", file)

        except:
            raise f"Error: cannot open {file}\n"
        text = fhd
        try:
            fhd.close()

        except:
            raise f"Error: cannot close {file}\n"

    return text


def exec_command(cmd, pidfile=None):  # FIXME: no need for this wrapper
    "wrapper for subprocess.run()"
    # remove empty arguments in cmd
    # i = 0
    # while i <= len(cmd)-1 :
    #     if   (i in cmd is None) and cmd[i] == EMPTY :
    #         del(cmd[i])

    #     else :
    #         i+=1

    if logger is not None:
        logger.info(SPACE.join(cmd))

    try:
        sbp = subprocess.run(cmd, capture_output=True, check=True, text=True)
    except FileNotFoundError as err:
        return -1, None, str(err)

    # if pid == 0 :
    #     return PROCESS_FAILED, None,           SPACE.join(  cmd ) + ': command not found'

    # if  logger is not None :
    #     logger.info(f"Spawned PID {pid}")
    # if  pidfile is not None :
    #     try:
    #         fh=open('>',pidfile)

    #     except:
    #         return PROCESS_FAILED
    #     fh.print(pid)
    #     try:
    #         fh.close()

    #     except:
    #         return PROCESS_FAILED

    # slurping these before waitpid, as if the output is larger than 65535,
    # waitpid hangs forever.

    # reader = unescape_utf8( slurp(reader) )
    # err    = unescape_utf8( slurp(err) )

    # Using 0 for flags, rather than WNOHANG to ensure that we wait for the
    # process to finish and not leave a zombie

    # os.waitpid(pid,0)
    # child_exit_status = CHILD_ERROR >> BITS_PER_BYTE
    return sbp.returncode, sbp.stdout, sbp.stderr


def program_version(stream, regex, cmd):
    "run command and parse version string from output"
    return _program_version(stream, regex, exec_command(cmd))


def _program_version(stream, regex, output):
    status, out, err = output
    if out is None:
        out = ""
    if err is None:
        err = ""
    output = None
    if stream == "stdout":
        output = out

    elif stream == "stderr":
        output = err

    elif stream == "both":
        output = out + err

    else:
        logger.error("Unknown stream: '%s'", (stream,))

    regex2 = re.search(regex, output)
    if regex2:
        return regex2.group(1)
    if status == PROCESS_FAILED:
        logger.info(err)
        return PROCESS_FAILED

    logger.info("Unable to parse version string from: '%s'", output)


def text_to_datetime(text, thisyear=None, thismonth=None, thisday=None):
    "convert string to datetime"
    (year, month, day, hour, minute, sec) = (None, None, None, None, None, None)
    regex = re.search(
        r"^(\d+)?-?(\d+)?-?(\d+)?(?:\s(\d+)?:?(\d+)?:?(\d+)?)?$",
        text,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    if (text is not None) and regex:
        if regex.group(1) is not None:
            year = int(regex.group(1))
        if regex.group(2) is not None:
            month = int(regex.group(2))
        if regex.group(3) is not None:
            day = int(regex.group(3))
        if regex.group(4) is not None:
            hour = int(regex.group(4))
        if regex.group(5) is not None:
            minute = int(regex.group(5))
        if regex.group(6) is not None:
            sec = int(regex.group(6))

    if (year is None) or year == 0:
        year = thisyear
    if (month is None) or month < 1 or month > MONTHS_PER_YEAR:
        month = thismonth

    if (day is None) or day < 1 or day > DAYS_PER_MONTH:
        day = thisday

    if (hour is None) or hour > HOURS_PER_DAY - 1:
        hour = 0

    if (minute is None) or minute > MINUTES_PER_HOUR - 1:
        minute = 0

    if (sec is None) or sec > SECONDS_PER_MINUTE - 1:
        sec = 0

    return year, month, day, hour, minute, sec


def expand_metadata_pattern(**kwargs):
    "expand metadata template"
    dhour, dmin, dsec, thour, tmin, tsec = 0, 0, 0, 0, 0, 0
    if len(kwargs["docdate"]) > 3:
        dyear, dmonth, dday, dhour, dmin, dsec = kwargs["docdate"]
    else:
        dyear, dmonth, dday = kwargs["docdate"]
    if len(kwargs["today_and_now"]) > 3:
        tyear, tmonth, tday, thour, tmin, tsec = kwargs["today_and_now"]
    else:
        tyear, tmonth, tday = kwargs["today_and_now"]

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
        result = datetime.datetime(dyear, dmonth, dday, dhour, dmin, dsec).strftime(
            template
        )
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
    kwargs["template"] = datetime.datetime(
        tyear,
        tmonth,
        tday,
        thour,
        tmin,
        tsec,
    ).strftime(kwargs["template"])

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


def prepare_output_metadata(ftype, metadata):
    "format metadata for PDF or DjVu"
    out = {}
    if metadata is not None and ftype in ["PDF", "DjVu"]:
        year, month, day, hour, mns, sec = 0, 0, 0, 0, 0, 0
        if "datetime" in metadata and metadata["datetime"] is not None:
            year, month, day, hour, mns, sec = metadata["datetime"]
        sign, dhr, dmin = "+", 0, 0
        if "tz" in metadata:
            _year, _month, _day, dhr, dmin, _sec, _dst = metadata["tz"]
        if year > 0:
            if ftype == "PDF":
                out["creationdate"] = datetime.datetime(
                    year,
                    month,
                    day,
                    hour,
                    mns,
                    sec,
                    tzinfo=datetime.timezone(
                        datetime.timedelta(hours=dhr, minutes=dmin)
                    ),
                )
            else:
                dateformat = "%4i-%02i-%02i %02i:%02i:%02i%1s%02i:%02i"
                out["creationdate"] = dateformat % (
                    year,
                    month,
                    day,
                    hour,
                    mns,
                    sec,
                    sign,
                    dhr,
                    dmin,
                )
            out["moddate"] = out["creationdate"]
        out["creator"] = f"gscan2pdf v{VERSION}"
        if ftype == "DjVu":
            out["producer"] = "djvulibre"
        for key in ["author", "title", "subject", "keywords"]:
            if key in metadata and metadata[key] != "":
                out[key] = metadata[key]

    return out


def _add_metadata_to_info(info, string, regex):
    kw_lookup = {
        "Title": "title",
        "Subject": "subject",
        "Keywords": "keywords",
        "Author": "author",
        "CreationDate": "datetime",
    }
    for key, value in kw_lookup.items():
        match = re.search(
            rf"{key}{regex}", string, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if match:
            info[value] = match.group(1)


def _need_temp_pdf(options):
    return options and (
        "prepend" in options
        or "append" in options
        or "ps" in options
        or "user-password" in options
    )


def _must_convert_image_for_pdf(compression, fformat, downsample):
    return (
        (compression != "none" and compression != fformat)
        or downsample
        or compression == "jpg"
    )


def _write_image_object(page, options):
    filename = page.filename
    save = False
    image = None
    if (
        options
        and "options" in options
        and options["options"]
        and "downsample" in options["options"]
        and options["options"]["downsample"]
    ):
        if options["options"]["downsample dpi"] < min(
            page.resolution[0], page.resolution[1]
        ):
            save = True
            image = page.im_object()
            width = (
                page.width * options["options"]["downsample dpi"] // page.resolution[0]
            )
            height = (
                page.height * options["options"]["downsample dpi"] // page.resolution[1]
            )
            image = image.resize((width, height))
    if (
        options
        and "options" in options
        and options["options"]
        and "compression" in options["options"]
        and "g" in options["options"]["compression"]
    ):
        save = True
        if image is None:
            image = page.im_object()
        # Grayscale
        image = image.convert("L")
        # Threshold
        threshold = 0.4 * 255
        image = image.point(lambda p: 255 if p > threshold else 0)
        # To mono
        image = image.convert("1")
    if save:
        regex = re.search(r"([.]\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        filename = tempfile.NamedTemporaryFile(
            dir=options["dir"], suffix=regex.group(1)
        ).name
        image.save(filename)
    return filename

    compression = options["options"]["compression"]
    if (
        (
            not re.search(
                r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            and format != "tif"
        )
        or re.search(r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE)
        or options["options"]["downsample"]
    ):
        logger.info("Writing temporary image %s", (filename,))

        # Perlmagick doesn't reliably convert to 1-bit, so using convert

        if re.search(r"g[34]", compression, re.MULTILINE | re.DOTALL | re.VERBOSE):
            cmd = [
                "convert",
                image.Get("filename"),
                "-threshold",
                "40%",
                "-depth",
                "1",
                filename,
            ]
            (status) = exec_command(cmd)
            return "tif"

        # Reset depth because of ImageMagick bug
        # <https://github.com/ImageMagick/ImageMagick/issues/277>
        image.depth = image.depth
        status = image.write(filename.name)
        # if _self["cancel"]:
        #     return
        if status:
            logger.warning(status)
        regex = re.search(
            r"[.](\w*)$", filename.name, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            return regex.group(1)


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


def _post_save_hook(filename, options):
    if options is not None and "post_save_hook" in options:
        args = options["post_save_hook"].split(" ")
        for i, arg in enumerate(args):
            args[i] = re.sub(
                "%i", filename, arg, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
            )
        if (
            "post_save_hook_options" not in options
            or options["post_save_hook_options"] != "fg"
        ):
            args += " &"

        logger.info(args)
        subprocess.run(args, check=True)


def _note_callbacks2(kwargs):
    callbacks = {}
    for callback in [
        "queued",
        "started",
        "running",
        "data",
        "finished",
        "error",
        "mark_saved",
        "display",
        "updated_page",
    ]:
        name = callback + "_callback"
        if name in kwargs:
            callbacks[name] = kwargs[name]
            del kwargs[name]
    return callbacks

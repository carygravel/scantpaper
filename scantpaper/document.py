"main document IO methods"
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
from basethread import BaseThread
from const import POINTS_PER_INCH

# from scanner.options import Options
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib
from simplelist import SimpleList

from page import Page
import netpbm

# import Gscan2pdf.Tesseract
# import Gscan2pdf.Cuneiform

# easier to extract strings with xgettext

_ = gettext.gettext

# import Socket
# import FileHandle
import PythonMagick

# import File.Basename
# from Storable import store,retrieve
# import Archive.Tar
# from IPC.Open3 import open3
# import Symbol
# from intspan import intspan
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# import version

logger = logging.getLogger(__name__)
from gi.repository import Gtk, Gdk

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
JPG = r"Joint[ ]Photographic[ ]Experts[ ]Group[ ]JFIF[ ]format"
GIF = r"CompuServe[ ]graphics[ ]interchange[ ]format"
_self, paper_sizes, callback = None, None, {}

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

    def do_get_file_info(self, path, password=None, **options):
        "get file info"
        _ = gettext.gettext
        info = {}
        if not pathlib.Path(path).exists():
            raise FileNotFoundError(_("File %s not found") % (path,))

        logger.info(f"Getting info for {path}")
        _returncode, fformat, _stderr = exec_command(["file", "-Lb", path])
        fformat = fformat.rstrip()
        logger.info(f"Format: '{fformat}'")
        if fformat in ["very short file (no magic)", "empty"]:
            raise RuntimeError(_("Error importing zero-length file %s.") % (path,))

        elif re.search(r"gzip[ ]compressed[ ]data", fformat):
            info["path"] = path
            info["format"] = "session file"
            return info

        elif re.search(r"DjVu", fformat):
            # Dig out the number of pages
            _, stdout, stderr = exec_command(                ["djvudump", path]            )
            if re.search(
                r"command[ ]not[ ]found", stderr, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                raise RuntimeError(_("Please install djvulibre-bin in order to open DjVu files."))

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
            for w, h, p in regex:
                width.append(int(w))
                height.append(int(h))
                ppi.append(int(p))
                logger.info(
                    f"Page $#ppi is {width}[$#width]x{height}[$#height], {ppi}[$#ppi] ppi"
                )

            if pages != len(ppi):
                raise RuntimeError(_("Unknown DjVu file structure. Please contact the author."))

            info["width"] = width
            info["height"] = height
            info["ppi"] = ppi
            info["pages"] = pages
            info["path"] = path
            # Dig out the metadata
            _, stdout, _stderr = exec_command(                ["djvused", path, "-e", "print-meta"]            )
            logger.info(stdout)
            if self.cancel:
                return

            # extract the metadata from the file
            _add_metadata_to_info(info, stdout, r'\s+"([^"]+)')
            return info

        elif re.search(r"PDF[ ]document", fformat):
            fformat = "Portable Document Format"
            args = ["pdfinfo", "-isodates", path]
            if "password" in options:
                args = [
                    "pdfinfo",
                    "-isodates",
                    "-upw",
                    options["password"],
                    path,
                ]

            _, stdout, stderr = exec_command(args)
            if self.cancel:
                return
            logger.info(f"stdout: {stdout}")
            logger.info(f"stderr: {stderr}")
            if (stderr is not None) and re.search(
                r"Incorrect[ ]password", stderr, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                info["encrypted"] = True

            else:
                info["pages"] = 1
                regex = re.search(
                    r"Pages:\s+(\d+)", stdout, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                if regex:
                    info["pages"] = int(regex.group(1))

                logger.info(f"{info['pages']} pages")
                floatr = r"\d+(?:[.]\d*)?"
                regex = re.search(
                    fr"Page\ssize:\s+({floatr})\s+x\s+({floatr})\s+(\w+)",
                    stdout,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                if regex:
                    info["page_size"] = [
                        float(regex.group(1)),
                        float(regex.group(2)),
                        regex.group(3),
                    ]
                    logger.info(
                        f"Page size: {regex.group(1)} x {regex.group(2)} {regex.group(3)}"
                    )

                # extract the metadata from the file
                _add_metadata_to_info(info, stdout, r":\s+([^\n]+)")

        elif re.search(r"^TIFF[ ]image[ ]data", fformat):
            fformat = "Tagged Image File Format"
            _, stdout, _stderr = exec_command(                ["tiffinfo", path]            )
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
            logger.info(f"{info['pages']} pages")

            # Dig out the size of each page
            width, height = [], []
            regex = re.findall(
                r"Image\sWidth:\s(\d+)\sImage\sLength:\s(\d+)",
                stdout,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            for w, h in regex:
                width.append(int(w))
                height.append(int(h))
                self.log(event="get_file_info", info=f"Page {len(width)} is {width[-1]}x{height[-1]}")

            info["width"] = width
            info["height"] = height

        else:

            # Get file type
            image = PythonMagick.Image(path)

            if self.cancel:
                return
            fformat = image.magick()

            logger.info(f"Format {fformat}")
            info["width"] = [image.size().width()]
            info["height"] = [image.size().height()]
            if image.xResolution() > 0.:
                info["xresolution"] = [image.xResolution()]
            if image.yResolution() > 0.:
                info["yresolution"] = [image.yResolution()]
            info["pages"] = 1

        info["format"] = fformat
        info["path"] = path
        # self.log(event="get_file_info", info=info)
        return            info

    def do_import_file(self, info, *options):
        print(f"do_import_file {info} {options}")
        password, first, last, dirname, pidfile = options
        if info["format"] == "DJVU":

            # Extract images from DjVu
            if last >= options["first"] and options["first"] > 0:
                for i in range(options["first"], last + 1):
                    self.progress = (i - 1) / (last - options["first"] + 1)
                    self.message = _("Importing page %i of %i") % (
                        i,
                        last - options["first"] + 1,
                    )
                    tif, txt, ann, error = None, None, None, None
                    try:
                        tif = tempfile.NamedTemporaryFile(
                            dir=options["dir"], suffix=".tif", delete=False
                        )
                        exec_command(
                            [
                                "ddjvu",
                                "-format=tiff",
                                f"-page={i}",
                                info["path"],
                                tif,
                            ],
                            options["pidfile"],
                        )
                        (_, txt) = exec_command(
                            [
                                "djvused",
                                info["path"],
                                "-e",
                                f"select {i}; print-txt",
                            ],
                            options["pidfile"],
                        )
                        (_, ann) = exec_command(
                            [
                                "djvused",
                                info["path"],
                                "-e",
                                f"select {i}; print-ant",
                            ],
                            options["pidfile"],
                        )

                    except:
                        if tif is not None:
                            logger.error(f"Caught error creating {tif}: {_}")
                            _thread_throw_error(
                                self,
                                options["uuid"],
                                options["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {tif}.",
                            )

                        else:
                            logger.error(f"Caught error writing to {options}{dir}: {_}")
                            _thread_throw_error(
                                self,
                                options["uuid"],
                                options["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {options}{dir}.",
                            )

                        error = True

                    if _self["cancel"] or error:
                        return
                    page = Page(
                        filename=tif,
                        dir=options["dir"],
                        delete=True,
                        format="Tagged Image File Format",
                        xresolution=info["ppi"][i - 1],
                        yresolution=info["ppi"][i - 1],
                        width=info["width"][i - 1],
                        height=info["height"][i - 1],
                    )
                    try:
                        page.import_djvu_txt(txt)

                    except:
                        logger.error(f"Caught error parsing DjVU text layer: {_}")
                        _thread_throw_error(
                            self,
                            options["uuid"],
                            options["page"]["uuid"],
                            "Open file",
                            "Error: parsing DjVU text layer",
                        )

                    try:
                        page.import_djvu_ann(ann)

                    except:
                        logger.error(f"Caught error parsing DjVU annotation layer: {_}")
                        _thread_throw_error(
                            self,
                            options["uuid"],
                            options["page"]["uuid"],
                            "Open file",
                            "Error: parsing DjVU annotation layer",
                        )

                    self.return_queue.enqueue(
                        {"type": "page", "uuid": options["uuid"], "page": page}
                    )

        elif info["format"] == "Portable Document Format":
            _thread_import_pdf(self, options)

        elif info["format"] == "Tagged Image File Format":

            # Only one page, so skip tiffcp in case it gives us problems
            if last == 1:
#                self.progress = 1
#                self.message = _("Importing page %i of %i") % (1, 1)
                return Page(
                    filename=info["path"],
                    dir=dirname,
                    delete=False,
                    format=info["format"],
                    width=info["width"][0],
                    height=info["height"][0],
                )
            # Split the tiff into its pages and import them individually
            elif last >= options["first"] and options["first"] > 0:
                for i in range(options["first"] - 1, last - 1 + 1):
                    self.progress = i / (last - options["first"] + 1)
                    self.message = _("Importing page %i of %i") % (
                        i,
                        last - options["first"] + 1,
                    )
                    (tif, error) = (None, None)
                    try:
                        tif = tempfile.NamedTemporaryFile(
                            dir=options["dir"], suffix=".tif", delete=False
                        )
                        (status, out, err) = exec_command(
                            ["tiffcp", f"{options}{info}{path},{i}", tif],
                            options["pidfile"],
                        )
                        if (err is not None) and err != EMPTY:
                            logger.error(
                                f"Caught error extracting page {i} from {options}{info}{path}: {err}"
                            )
                            _thread_throw_error(
                                self,
                                options["uuid"],
                                options["page"]["uuid"],
                                "Open file",
                                f"Caught error extracting page {i} from {options}{info}{path}: {err}",
                            )

                    except:
                        if tif is not None:
                            logger.error(f"Caught error creating {tif}: {_}")
                            _thread_throw_error(
                                self,
                                options["uuid"],
                                options["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {tif}.",
                            )

                        else:
                            logger.error(f"Caught error writing to {options}{dir}: {_}")
                            _thread_throw_error(
                                self,
                                options["uuid"],
                                options["page"]["uuid"],
                                "Open file",
                                f"Error: unable to write to {options}{dir}.",
                            )

                        error = True

                    if _self["cancel"] or error:
                        return
                    page = Page(
                        filename=tif,
                        dir=options["dir"],
                        delete=True,
                        format=info["format"],
                        width=info["width"][i - 1],
                        height=info["height"][i - 1],
                    )
                    self.return_queue.enqueue(
                        {"type": "page", "uuid": options["uuid"], "page": page.freeze()}
                    )

        elif re.search(fr"(?:{PNG}|{JPG}|{GIF})", info["format"]):
            try:
                page = Page(
                    filename=info["path"],
                    dir=dirname,
                    format=info["format"],
                    width=info["width"],
                    height=info["height"],
                    xresolution=info["xresolution"],
                    yresolution=info["yresolution"],
                )
                self.return_queue.enqueue(
                    {"type": "page", "uuid": options["uuid"], "page": page.freeze()}
                )

            except:
                logger.error(f"Caught error writing to {options}{dir}: {_}")
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Open file",
                    f"Error: unable to write to {options}{dir}.",
                )

        else:
            return Page(
                filename=info["path"],
                dir=dirname,
                format=info["format"],
                width=info["width"][0],
                height=info["height"][0],
            )

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "import-file",
                "uuid": options["uuid"],
            }
        )

    def get_file_info(self, path, **kwargs):
        "get file info"
        return self.send("get_file_info", path, **kwargs)

    def import_file(self, password=None, first=1, last=1, **kwargs):
        "import file"
        info = kwargs["info"]
        del kwargs["info"]
        dirname = kwargs["dir"] if "dir" in kwargs else None
        del kwargs["dir"]
        pidfile = kwargs["pidfile"] if "pidfile" in kwargs else None
        del kwargs["pidfile"]
        return self.send("import_file", info, password, first, last, dirname, pidfile, **kwargs)

    def save_pdf(self, **kwargs):
        "save pdf"
        return self.send("save_pdf", kwargs)

    def do_save_pdf(self, *options):
        options = options[0]
        print(f"in do_save_pdf with {options}")
        _ = gettext.gettext
        pagenr = 0
        cache, pdf, error, message = None, None, None, None

        # Create PDF with PDF::Builder
        self.message = _("Setting up PDF")
        filename = options["path"]
        if _need_temp_pdf(options):
            filename = tempfile.TemporaryFile(dir=options["dir"], suffix=".pdf")

        pdf = canvas.Canvas(filename)

        if error:
            return 1
        if "metadata" in options and "ps" not in options["options"]:
            metadata = prepare_output_metadata("PDF", options["metadata"])
            if "Author" in metadata:
                pdf.setAuthor(metadata["Author"])
            if "Title" in metadata:
                pdf.setTitle(metadata["Title"])
            if "Subject" in metadata:
                pdf.setSubject(metadata["Subject"])
            if "Keywords" in metadata:
                pdf.setKeywords(metadata["Keywords"])
            pdf.setCreator(f"scantpaper v{VERSION}")

        #cache["core"] = pdf.corefont("Times-Roman")
        pdf.setFont('Times-Roman', 12)
        if "font" in options["options"]:
            message = _("Unable to find font '%s'. Defaulting to core font.") % (
                options["options"]["font"]
            )
            if os.path.isfile(options["options"]["font"]):
                try:
                    cache["ttf"] = pdf.ttfont(options["options"]["font"], unicodemap=1)
                    logger.info(f"Using {options}{options}{font} for non-ASCII text")

                except:
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        message,
                    )

            else:
                _thread_throw_error(
                    self, options["uuid"], options["page"]["uuid"], "Save file", message
                )

        for pagedata in options["list_of_pages"]:
            pagenr += 1
            self.progress = pagenr / (len(options["list_of_pages"]) + 1)
            self.message = _("Saving page %i of %i") % (
                pagenr,
                len(options["list_of_pages"]) - 1 + 1,
            )
            status = self._add_page_to_pdf(pdf, pagedata, cache, options)
            # if status or _self["cancel"]:
            #     return

        self.message = _("Closing PDF")
        logger.info("Closing PDF")
        pdf.save()
        if "prepend" in options["options"] or "append" in options["options"]:
            if _append_pdf(self, filename, options):
                return

        if "user-password" in options["options"]:
            if _encrypt_pdf(self, filename, options):
                return

        self._set_timestamp(options)
        if "ps" in options["options"]:
            self.message = _("Converting to PS")
            cmd = [options["options"]["pstool"], filename, options["options"]["ps"]]
            (status, _, error) = exec_command(cmd, options["pidfile"])
            if status or error:
                logger.info(error)
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error converting PDF to PS: %s") % (error),
                )
                return

            _post_save_hook(options["options"]["ps"], options["options"])

        else:
            _post_save_hook(filename, options["options"])

    def _add_page_to_pdf(self, pdf, pagedata, cache, options):
        print(f"_add_page_to_pdf {pdf}, {pagedata}, {cache}, {options}")
        filename = pagedata.filename
        image = PythonMagick.Image(filename)

        # Get the size and resolution. Resolution is pixels per inch, width
        # and height are in pixels.
        width, height = pagedata.get_size()
        xres, yres, units = pagedata.get_resolution()
        w = width / xres * POINTS_PER_INCH
        h = height / yres * POINTS_PER_INCH

        pdf.setPageSize((w,h))

        # Automatic mode
        ctype = None
        if (
            "compression" not in options["options"]
            or options["options"]["compression"] == "auto"
        ):
            pagedata.depth = image.depth()
            logger.info(f"Depth of {filename} is {pagedata.depth}")
            if pagedata.depth == 1:
                pagedata.compression = "png"

            else:
                ctype = image.format()
                print(f"format {ctype}")
                logger.info(f"Type of {filename} is {ctype}")
                if re.search(r"TrueColor", ctype, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    pagedata.compression = "jpg"

                else:
                    pagedata.compression = "png"

            logger.info(f"Selecting {pagedata.compression} compression")

        else:
            pagedata.compression = options["options"]["compression"]

        filename, fmt, output_xresolution, output_yresolution = self._convert_image_for_pdf(
            pagedata, image, options
        )

#        pdf.drawString(1 * cm, 29.7 * cm - 1 * cm, "Hello")
        if (
            "text_position" in options["options"]
            and options["options"]["text_position"] == "right"
        ):
            logger.info("Embedding OCR output right of image")
            logger.info("Defining page at ", w * 2, f" pt x {h} pt")

        else:
            logger.info("Embedding OCR output behind image")
            logger.info(f"Defining page at {w} pt x {h} pt")

        if pagedata.text_layer is not None:
            logger.info("Embedding text layer behind image")
            self._add_text_to_pdf(pdf, pagedata, cache, options)

        # Add scan
        print(f"before drawImage {filename}")
        pdf.drawImage(filename, 0, 0)

        if pagedata.annotations is not None:
            logger.info("Adding annotations")
            _add_annotations_to_pdf(self, page, pagedata)

        logger.info(f"Added {filename} at {output_xresolution}x{output_yresolution} PPI")

    def _convert_image_for_pdf(self, pagedata, image, options):
        """Convert file if necessary"""

        # The output resolution is normally the same as the input
        # resolution.
        output_xresolution, output_yresolution, units = pagedata.get_resolution()
        return pagedata.filename, None, output_xresolution, output_yresolution

        filename = pagedata.filename
        compression = pagedata.compression
        fmt = None
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            fmt = regex.group(1)

        if _must_convert_image_for_pdf(
            compression, fmt, options["options"]["downsample"] if "downsample" in options["options"] else None
        ):
            if (
                not re.search(
                    r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                and fmt != "tif"
            ):
                ofn = filename
                filename = tempfile.TemporaryFile(dir=options["dir"], suffix=".tif")
                logger.info(f"Converting {ofn} to {filename}")

            elif re.search(
                r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                ofn = filename
                filename = tempfile.TemporaryFile(
                    dir=options["dir"], suffix=f".{compression}"
                )
                msg = f"Converting {ofn} to {filename}"
                if "quality" in options["options"] and compression == "jpg":
                    msg += f" with quality={options}{options}{quality}"

                logger.info(msg)

            if "downsample" in options["options"]:
                output_xresolution = options["options"]["downsample dpi"]
                output_yresolution = options["options"]["downsample dpi"]
                w_pixels = (
                    pagedata["width"] * output_xresolution / pagedata["xresolution"]
                )
                h_pixels = (
                    pagedata["height"] * output_yresolution / pagedata["yresolution"]
                )
                logger.info(f"Resizing {filename} to {w_pixels} x {h_pixels}")
                status = image.Sample(width=w_pixels, height=h_pixels)
                if f"{status}":
                    logger.warn(status)

            if "quality" in options["options"] and compression == "jpg":
                status = image.Set(quality=options["options"]["quality"])
                if f"{status}":
                    logger.warn(status)

            fmt = _write_image_object(
                image, filename, fmt, pagedata, options["options"]["downsample"] if "downsample" in options["options"] else None
            )
            if not re.search(
                r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                filename2 = tempfile.TemporaryFile(dir=options["dir"], suffix=".tif")
                error = tempfile.TemporaryFile(dir=options["dir"], suffix=".txt")
                (status, _, error) = exec_command(
                    ["tiffcp", "-r", "-1", "-c", compression, filename, filename2],
                    options["pidfile"],
                )
                if _self["cancel"]:
                    return
                if status:
                    logger.info(error)
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        _("Error compressing image: %s") % (error),
                    )
                    return

                filename = filename2

        return filename.name, fmt, output_xresolution, output_yresolution

    def _add_text_to_pdf(self, pdf_page, gs_page, cache, options):
        """Add OCR as text behind the scan"""
        xresolution = gs_page["xresolution"]
        yresolution = gs_page["yresolution"]
        w = gs_page["width"] / gs_page["xresolution"]
        h = gs_page["height"] / gs_page["yresolution"]
        font = None
        offset = 0
        if (
            "text_position" in options["options"]
            and options["options"]["text_position"] == "right"
        ):
            offset = w * POINTS_PER_INCH

        text = pdf_page.text()
        iter = Bboxtree(gs_page["text_layer"]).get_bbox_iter()
        for box in iter:
            (x1, y1, x2, y2) = box["bbox"]
            txt = box["text"]
            if txt is None:
                continue
            regex = re.search(
                r"([[:^ascii:]]+)", txt, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                if not font_can_char(cache["core"], regex.group(1)):
                    if "ttf" not in cache:
                        message = _(
                            "Core font '%s' cannot encode character '%s', and no TTF font defined."
                        ) % (cache["core"].fontname(), regex.group(1))
                        logger.error(encode("UTF-8", message))
                        _thread_throw_error(
                            self,
                            options["uuid"],
                            options["page"]["uuid"],
                            "Save file",
                            message,
                        )

                    elif font_can_char(cache["ttf"], regex.group(1)):
                        logger.debug(encode("UTF-8", f"Using TTF for '{1}' in '{txt}'"))
                        font = cache["ttf"]

                    else:
                        message = _(
                            "Neither '%s' nor '%s' can encode character '%s' in '%s'"
                        ) % (
                            cache["core"].fontname(),
                            cache["ttf"].fontname(),
                            regex.group(1),
                            txt,
                        )
                        logger.error(encode("UTF-8", message))
                        _thread_throw_error(
                            self,
                            options["uuid"],
                            options["page"]["uuid"],
                            "Save file",
                            message,
                        )

            if font is None:
                font = cache["core"]
            if x1 == 0 and y1 == 0 and (x2 is None):
                (x2, y2) = (w * xresolution, h * yresolution)

            if (
                abs(h * yresolution - y2 + y1) > BOX_TOLERANCE
                and abs(w * xresolution - x2 + x1) > BOX_TOLERANCE
            ):

                # Box is smaller than the page. We know the text position.
                # Set the text position.
                # Translate x1 and y1 to inches and then to points. Invert the
                # y coordinate (since the PDF coordinates are bottom to top
                # instead of top to bottom) and subtract $size, since the text
                # will end up above the given point instead of below.

                size = px2pt(y2 - y1, yresolution)
                text.font(font, size)
                text.translate(
                    offset + px2pt(x1, xresolution),
                    (h - (y1 / yresolution)) * POINTS_PER_INCH - size,
                )
                text.text(txt, utf8=1)

            else:
                size = 1
                text.font(font, size)
                _wrap_text_to_page(txt, size, text, h, w)

    def _set_timestamp(self, options):

        if (
            "set_timestamp" not in options["options"]
            or not options["options"]["set_timestamp"]
            or "ps" in options["options"]
        ):
            return

        adatetime = options["metadata"]["datetime"]
        adatetime = datetime.datetime(*adatetime)
        if "tz" in options["metadata"]:
            tz = options["metadata"]["tz"]
            tz = [0 if x is None else x for x in tz]
            tz = datetime.timedelta(
                days=tz[2], hours=tz[3], minutes=tz[4], seconds=tz[5]
            )
            adatetime -= tz

        try:
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
            adatetime = (adatetime - epoch).total_seconds()
            os.utime(options["path"], (adatetime, adatetime))

        except:
            logger.error("Unable to set file timestamp for dates prior to 1970")
            _thread_throw_error(
                self,
                options["uuid"],
                None,
                "Set timestamp",
                _("Unable to set file timestamp for dates prior to 1970"),
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

    def setup(_class, logger=None):
        _self = {}
        Page.set_logger(logger)
        _self["requests"] = Thread.Queue()
        _self["return"] = Thread.Queue()
        _self["pages"] = Thread.Queue()
        _self["progress"] = queue.Queue()
        _self["message"] = queue.Queue()
        _self["process_name"] = queue.Queue()
        _self["cancel"] = queue.Queue()
        _self["cancel"] = False
        _self["thread"] = threading.Thread(target=_thread_main, args=(_self,))

    def on_row_changed(self, path, iter, data):
        "Set-up the callback when the page number has been edited."
        # Note uuids for selected pages
        selection = self.get_selected_indices()
        uuids = []
        for i in selection:
            uuids.append(self.data[i][2]["uuid"])

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
        self.thread.start()
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_headers_visible(False)
        self.set_reorderable(True)
        for prop in options.keys():
            setattr(self, prop, options[prop])

        # Glib.Timeout.add( _POLL_INTERVAL, check_return_queue, self )
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

        def drag_drop_callback(tree, context, x, y, when):
            """# Callback for dropped signal."""
            targets = tree.drag_dest_get_target_list()
            if target in tree.drag_dest_find_target(context, targets):
                tree.drag_get_data(context, target, when)
                return True

            return False

        self.connect("drag-drop", drag_drop_callback)

        # Set the page number to be editable
        self.set_column_editable(0, True)
        self.row_changed_signal = self.get_model().connect(
            "row-changed", self.on_row_changed
        )

    def set_paper_sizes(_class, paper_sizes=None):
        """Set the paper sizes in the manager and worker threads"""
        _enqueue_request("paper_sizes", {"paper_sizes": paper_sizes})

    def cancel(self, cancel_callback, process_callback):
        """Kill all running processes"""
        lock(_self["requests"])  # unlocks automatically when out of scope
        lock(_self["pages"])  # unlocks automatically when out of scope

        # Empty process queue first to stop any new process from starting
        logger.info("Emptying process queue")
        while _self["requests"].pending():
            _self["requests"].dequeue()

        jobs_completed = 0
        jobs_total = 0

        # Empty pages queue
        while _self["pages"].pending():
            _self["pages"].dequeue()

        # Then send the thread a cancel signal
        # to stop it going beyond the next break point
        _self["cancel"] = True

        # Kill all running processes in the thread
        for pidfile in self.running_pids.keys():
            pid = slurp(pidfile)
            SIG["CHLD"] = "IGNORE"
            if pid != EMPTY:
                if pid == 1:
                    continue
                if process_callback is not None:
                    process_callback(pid)

                logger.info(f"Killing PID {pid}")

                os.killpg(os.getpgid(pid), signal.SIGKILL)
                del self.running_pids[pidfile]

        uuid = str(uuid_object())
        callback[uuid]["cancelled"] = cancel_callback

        # Add a cancel request to ensure the reply is not blocked
        logger.info("Requesting cancel")
        sentinel = _enqueue_request("cancel", {"uuid": uuid})

        # Send a dummy page to the pages queue in case the thread is waiting there
        _self["pages"].enqueue({"page": "cancel"})
        return self._monitor_process(sentinel=sentinel, uuid=uuid)

    def create_pidfile(self, options):
        pidfile = None
        try:
            pidfile = tempfile.TemporaryFile(dir=self.dir, suffix=".pid")
        except Exception as e:
            logger.error(f"Caught error writing to {self.dir}: {e}")
            if "error_callback" in options:
                options["error_callback"](
                    options["page"],
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
            if "encrypted" in response.info and response.info["encrypted"] and "password_callback" in options:
                options["passwords"][i] = options["password_callback"](path)
                if (options["passwords"][i] is not None) and options["passwords"][
                    i
                ] != EMPTY:
                    self._get_file_info_finished_callback1(i, infolist, options)
                return

            infolist.append( response.info)
            if i == len(options["paths"]) - 1:
                self._get_file_info_finished_callback2(infolist, options)

        return self.thread.get_file_info(
            path,
            # "pidfile": f"{pidfile}",
            # # "uuid": uid,
            # "password": options["passwords"][i] if i < len(options["passwords"]) else None,
            started_callback=options["started_callback"] if "started_callback" in options else None,
            running_callback=options["running_callback"] if "running_callback" in options else None,
            finished_callback=_select_next_finished_callback,
        )

    def _get_file_info_finished_callback2(self, info, options):
        if len(info) > 1:
            for i in info:
                if i is None:
                    continue

                if i["format"] == "session file":
                    logger.error(
                        "Cannot open a session file at the same time as another file."
                    )
                    if options["error_callback"]:
                        options["error_callback"](
                            None,
                            "Open file",
                            _(
                                "Error: cannot open a session file at the same time as another file."
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
                                "Error: importing a multipage file at the same time as another file."
                            ),
                        )

                    return

            main_uuid = options["uuid"]
            finished_callback = options["finished_callback"]
            del options["paths"]
            del options["finished_callback"]
            for i in range(len(info)):
                if options["metadata_callback"]:
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
            if "pagerange_callback" in options and options["pagerange_callback"] and last_page > 1:
                first_page, last_page = options["pagerange_callback"](info[0])
                if (first_page is None) or (last_page is None):
                    return

            password = options["passwords"][0] if "passwords" in options and options["passwords"] else None
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
        """Because the finished, error and cancelled callbacks are triggered by the
        return queue, note them here for the return queue to use."""
        uid = uuid.uuid1()
        callback[uid] = {}
        for cb in ["queued_callback", "started_callback", "running_callback", "finished_callback", "error_callback", "cancelled_callback", "display_callback"]:
            if cb in options:
                callback[uid][cb[:-9]] = options[cb]
        if "mark_saved" in options and options["mark_saved"]:

            def mark_saved_callback():

                # list_of_pages is frozen,
                # so find the original pages from their uuids
                for _ in options["list_of_pages"]:
                    page = self.find_page_by_uuid(_)
                    self.data[page][2]["saved"] = True

            callback[uid]["mark_saved"] = mark_saved_callback

        return uid

    def import_file(self, password=None, first=1, last=1, **options):
        # File in which to store the process ID
        # so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        dirname = EMPTY
        if self.dir is not None:
            dirname = self.dir
        # uuid = self._note_callbacks(options)

        def _import_file_finished_callback(result):
            self.add_page(None, result.info, None)
            if "finished_callback" in options:
                options["finished_callback"]()

        uid = self.thread.import_file(
            info= options["info"],
            password= password,
            first= first,
            last= last,
            dir= dirname,
            pidfile= pidfile,
            # uuid= uuid,
            finished_callback = _import_file_finished_callback,
        )

    def _post_process_scan(self, page, options):

        # tesseract can't extract resolution from pnm, so convert to png
        if (
            (page is not None)
            and re.search(
                r"Portable[ ](any|pix|gray|bit)map",
                page.format,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            and "to_png" in options and options["to_png"]
        ):

            def to_png_finished_callback():
                finished_page = self.find_page_by_uuid(page["uuid"])
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.to_png(
                page=page["uuid"],
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=to_png_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )

        if "rotate" in options and options["rotate"]:

            def rotate_finished_callback():
                del options["rotate"]
                finished_page = self.find_page_by_uuid(page["uuid"])
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.rotate(
                angle=options["rotate"],
                page=page["uuid"],
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=rotate_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )

        if "unpaper" in options and options["unpaper"]:

            def unpaper_finished_callback():
                del options["unpaper"]
                finished_page = self.find_page_by_uuid(page["uuid"])
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.unpaper(
                page=page["uuid"],
                options={
                    "command": options["unpaper"].get_cmdline(),
                    "direction": options["unpaper"].get_option("direction"),
                },
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=unpaper_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )
            return

        if "udt" in options and options["udt"]:

            def udt_finished_callback():
                del options["udt"]
                finished_page = self.find_page_by_uuid(page["uuid"])
                if finished_page is None:
                    self._post_process_scan(None, options)  # to fire finished_callback
                    return

                self._post_process_scan(self.data[finished_page][2], options)

            self.user_defined(
                page=page["uuid"],
                command=options["udt"],
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=udt_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )
            return

        if "ocr" in options and options["ocr"]:

            def ocr_finished_callback():
                del options["ocr"]
                self._post_process_scan(None, options)  # to fire finished_callback

            self.ocr_pages(
                [page["uuid"]],
                threshold=options["threshold"],
                engine=options["engine"],
                language=options["language"],
                queued_callback=options["queued_callback"],
                started_callback=options["started_callback"],
                finished_callback=ocr_finished_callback,
                error_callback=options["error_callback"],
                display_callback=options["display_callback"],
            )
            return

        if "finished_callback" in options and options["finished_callback"]:
            options["finished_callback"]()

    def import_scan(self, **options):
        """Take new scan, pad it if necessary, display it,
        and set off any post-processing chains"""

        # Interface to frontend
        fh = open(options["filename"], mode="r")  ## no critic (RequireBriefOpen)

        # Read without blocking
        size = 0

        def file_changed_callback(fileno, condition, *data):
            nonlocal size, fh

            if condition & GLib.IOCondition.IN:
                width, height = None, None
                if size == 0:
                    size, width, height = netpbm.file_size_from_header(
                        options["filename"]
                    )
                    logger.info(f"Header suggests {size}")
                    if size == 0:
                        return GLib.SOURCE_CONTINUE
                    fh.close()

                filesize = os.path.getsize(options["filename"])
                logger.info(f"Expecting {size}, found {filesize}")
                if size > filesize:
                    pad = size - filesize
                    fh = open(options["filename"], mode="ab")
                    data = [1] * (pad * BITS_PER_BYTE + 1)
                    fh.write(struct.pack("%db" % (len(data)), *data))
                    fh.close()
                    logger.info(f"Padded {pad} bytes")

                page = Page(
                    filename=options["filename"],
                    xresolution=options["xresolution"] if "xresolution" in options else None,
                    yresolution=options["yresolution"] if "yresolution" in options else None,
                    width=width,
                    height=height,
                    format="Portable anymap",
                    delete=options["delete"] if "delete" in options else False,
                    dir=options["dir"].name,
                )
                index = self.add_page("none", page, options["page"])
                if index == NOT_FOUND and options["error_callback"]:
                    options["error_callback"](
                        None, "Import scan", _("Unable to load image")
                    )

                else:
                    if "display_callback" in options:
                        options["display_callback"]()

                    self._post_process_scan(page, options)

                return GLib.SOURCE_REMOVE

            return GLib.SOURCE_CONTINUE

        GLib.io_add_watch(fh, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN | GLib.IOCondition.HUP, file_changed_callback)

    def check_return_queue(self):

        lock(_self["return"])  # unlocks automatically when out of scope
        for data in _self.return_queue.dequeue_nb():
            if "type" not in data:
                logger.error(f"Bad data bundle {data} in return queue.")
                continue

            # if we have pressed the cancel button, ignore everything in the returns
            # queue until it flags cancelled.

            if _self["cancel"]:
                if data["type"] == "cancelled":
                    _self["cancel"] = False
                    if "cancelled" in callback[data["uuid"]]:
                        callback[data["uuid"]]["cancelled"](data["info"])
                        del callback[data["uuid"]]

                else:
                    continue

            if "uuid" not in data:
                logger.error("Bad uuid in return queue.")
                continue

            if data["type"] == "file-info":
                if "info" not in data:
                    logger.error("Bad file info in return queue.")
                    continue

                if "finished" in callback[data["uuid"]]:
                    callback[data["uuid"]]["finished"](data["info"])
                    del callback[data["uuid"]]

            elif data["type"] == "page request":
                i = self.find_page_by_uuid(data["uuid"])
                if i is not None:
                    _self["pages"].enqueue(
                        {
                            # sharing File::Temp objects causes problems,
                            # so freeze
                            "page": self.data[i][2].freeze(),
                        }
                    )

                else:
                    logger.error(f"No page with UUID {data}->{uuid}")
                    _self["pages"].enqueue({"page": "cancel"})

                return Glib.SOURCE_CONTINUE

            elif data["type"] == "page":
                if "page" in data:
                    del data["page"]["saved"]  # Remove saved tag
                    self.add_page(data["uuid"], data["page"], data["info"])

                else:
                    logger.error("Bad page in return queue.")

            elif data["type"] == "error":
                _throw_error(
                    data["uuid"], data["page"], data["process"], data["message"]
                )

            elif data["type"] == "finished":
                if "started" in callback[data["uuid"]]:
                    callback[data["uuid"]]["started"](
                        None,
                        _self["process_name"],
                        jobs_completed,
                        jobs_total,
                        data["message"],
                        _self["progress"],
                    )
                    del callback[data["uuid"]]["started"]

                if "mark_saved" in callback[data["uuid"]]:
                    callback[data["uuid"]]["mark_saved"]()
                    del callback[data["uuid"]]["mark_saved"]

                if "finished" in callback[data["uuid"]]:
                    callback[data["uuid"]]["finished"](data["message"])
                    del callback[data["uuid"]]

                if _self["requests"].pending() == 0:
                    jobs_completed = 0
                    jobs_total = 0

                else:
                    jobs_completed += 1

        return Glib.SOURCE_CONTINUE

    def index_for_page(self, n, min, max, direction):
        "does the given page exist?"
        if len(self.data) - 1 < 0:
            return INFINITE
        if min is None:
            min = 0

        if max is None:
            max = n - 1

        s = min
        e = max + 1
        step = 1
        if direction < 0:
            step = -step
            s = max
            if s > len(self.data) - 1:
                s = len(self.data) - 1
            e = min - 1

        i = s
        while (i <= e and i < len(self.data)) if step > 0 else i > e:
            if self.data[i][0] == n:
                return i

            i += step

        return INFINITE

    def pages_possible(self, start, step):
        "Check how many pages could be scanned"
        i = len(self.data) - 1

        # Empty document and negative step
        if i < 0 and step < 0:
            n = -start / step
            return n if n == int(n) else int(n) + 1

        # Empty document, or start page after end of document, allow infinite pages
        elif i < 0 or (step > 0 and self.data[i][0] < start):
            return INFINITE

        # scan in appropriate direction, looking for position for last page
        n = 0
        max_page_number = self.data[i][0]
        while True:

            # fallen off top of index
            if step > 0 and start + n * step > max_page_number:
                return INFINITE

            # fallen off bottom of index
            if step < 0 and start + n * step < 1:
                return n

            # Found page
            i = self.index_for_page(start + n * step, 0, start - 1, step)
            if i > INFINITE:
                return n

            n += 1

    def find_page_by_uuid(self, uuid):

        if uuid is None:
            logger.error(longmess("find_page_by_uuid() called with undef"))
            return

        i = 0
        while i <= len(self.data) - 1 and (
            "uuid" not in self.data[i][2] or self.data[i][2]["uuid"] != uuid
        ):
            i += 1

        if i <= len(self.data) - 1:
            return i
        return

    def add_page(self, process_uuid, new_page, ref):
        """Add a new page to the document"""
        i, pagenum = None, None

        # FIXME: This is really hacky to allow import_scan() to specify the page number
        if not isinstance(ref, dict):
            pagenum = ref
            ref = None

        if ref is not None:
            for uid in (ref["replace"], ref["insert-after"]):
                if uid is not None:
                    i = self.find_page_by_uuid(uid)
                    if i is None:
                        logger.error(f"Requested page {uid} does not exist.")
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

        xresolution, yresolution, units = new_page.get_resolution(paper_sizes)
        thumb = new_page.get_pixbuf_at_scale(self.heightt, self.widtht)

        # Add to the page list
        if i is None:
            if pagenum is None:
                pagenum = len(self.data) + 1
            self.data.append([pagenum, thumb, new_page])
            model = self.get_model()
            row = model[model.iter_nth_child(None, 0)]
            logger.info(
                f"Added {new_page.filename} ({new_page.uuid}) at page {pagenum} with resolution {xresolution},{yresolution}"
            )

        else:
            if "replace" in ref:
                pagenum = self.data[i][0]
                logger.info(
                    f"Replaced {self}->{data}[{i}][2]->{filename} ({self}->{data}[{i}][2]->{uid}) at page {pagenum} with {new_page}->{filename} ({new_page}->{uid}), resolution {xresolution},{yresolution}"
                )
                self.data[i][1] = thumb
                self.data[i][2] = new_page

            elif "insert-after" in ref:
                pagenum = self.data[i][0] + 1
                del self.data[i + 1]
                self.data.insert(i + 1, [pagenum, thumb, new_page])
                logger.info(
                    f"Inserted {new_page}->{filename} ({new_page}->{uid}) at page {pagenum} with resolution {xresolution},{yresolution},{units}"
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
        while page_selection[0] < len(self.data) - 1 and self.data[page_selection[0]][0] != pagenum:
            page_selection[0] += 1

        self.select(page_selection)
        # if "display" in callback[process_uuid]:
        #     callback[process_uuid]["display"](self.data[i][2])

        return page_selection[0]

    def remove_corrupted_pages(self):

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
        """Cut the selection"""
        data = self.copy_selection(False)
        self.delete_selection_extra()
        return data

    def copy_selection(self, clone):
        """Copy the selection"""
        selection = self.get_selected_indices()
        if selection == []:
            return
        data = []
        for index in selection:
            page = self.data[index]
            data.append([page[0], page[1], page[2].clone(clone)])

        logger.info(
            "Copied ", "and cloned " if clone else EMPTY, len(data) - 1 + 1, " pages"
        )
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

        for i in range(dest, dest + len(data)-2):
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
        logger.info("Pasted ", len(data), f" pages at position {dest}")

    def delete_selection(self, context=None):
        """Delete the selected scans"""

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
                iter = model.get_iter(path)
                model.remove(iter)

    def delete_selection_extra(self):
        page = self.get_selected_indices()
        npages = len(page)
        uuids = map(lambda x: str(self.data[x][2].uuid), page)
        logger.info("Deleting ", " ".join(uuids))
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
        logger.info(f"Deleted {npages} pages")

    def save_pdf(self, **options):

        # File in which to store the process ID so that it can be killed if necessary
        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        uuid = self._note_callbacks(options)
        return self.thread.save_pdf(
            path=options["path"],
            list_of_pages=options["list_of_pages"],
            metadata=options["metadata"] if "metadata" in options else None,
            options=options["options"],
            dir=self.dir,
            pidfile=pidfile,
            uuid=uuid,
            started_callback = options["started_callback"],
            finished_callback = options["finished_callback"],
        )

    def save_djvu(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "save-djvu",
            {
                "path": options["path"],
                "list_of_pages": options["list_of_pages"],
                "metadata": options["metadata"],
                "options": options["options"],
                "dir": self.dir,
                "pidfile": pidfile,
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def save_tiff(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "save-tiff",
            {
                "path": options["path"],
                "list_of_pages": options["list_of_pages"],
                "options": options["options"],
                "dir": f"{self}->{dir}",
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def rotate(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "rotate",
            {
                "angle": options["angle"],
                "page": options["page"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def save_image(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        options["mark_saved"] = True
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "save-image",
            {
                "path": options["path"],
                "list_of_pages": options["list_of_pages"],
                "options": options["options"],
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def scans_saved(self):
        "Check that all pages have been saved"
        print(f"scans_saved {self.data}")
        for row in self:
            print(f"row {row}")
            if not row[2].saved:
                return False
        return True

    def save_text(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "save-text",
            {
                "path": options["path"],
                "list_of_pages": options["list_of_pages"],
                "options": options["options"],
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def save_hocr(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "save-hocr",
            {
                "path": options["path"],
                "list_of_pages": options["list_of_pages"],
                "options": options["options"],
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def analyse(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "analyse", {"list_of_pages": options["list_of_pages"], "uuid": uuid}
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def threshold(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "threshold",
            {
                "threshold": options["threshold"],
                "page": options["page"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def brightness_contrast(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "brightness-contrast",
            {
                "page": options["page"],
                "brightness": options["brightness"],
                "contrast": options["contrast"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def negate(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "negate", {"page": options["page"], "dir": f"{self}->{dir}", "uuid": uuid}
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def unsharp(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "unsharp",
            {
                "page": options["page"],
                "radius": options["radius"],
                "sigma": options["sigma"],
                "gain": options["gain"],
                "threshold": options["threshold"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def crop(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "crop",
            {
                "page": options["page"],
                "x": options["x"],
                "y": options["y"],
                "w": options["w"],
                "h": options["h"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def split_page(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "split",
            {
                "page": options["page"],
                "direction": options["direction"],
                "position": options["position"],
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def to_png(self, options):

        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "to-png", {"page": options["page"], "dir": f"{self}->{dir}", "uuid": uuid}
        )
        return self._monitor_process(
            sentinel=sentinel,
            uuid=uuid,
        )

    def tesseract(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "tesseract",
            {
                "page": options["page"],
                "language": options["language"],
                "threshold": options["threshold"],
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def cuneiform(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "cuneiform",
            {
                "page": options["page"],
                "language": options["language"],
                "threshold": options["threshold"],
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def gocr(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "gocr",
            {
                "page": options["page"],
                "threshold": options["threshold"],
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def ocr_pages(self, pages, options):
        """Wrapper for the various ocr engines"""
        for page in pages:
            options["page"] = page
            if options["engine"] == "gocr":
                self.gocr(options)

            elif options["engine"] == "tesseract":
                self.tesseract(options)

            else:  # cuneiform
                self.cuneiform(options)

    def unpaper(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "unpaper",
            {
                "page": options["page"],
                "options": options["options"],
                "pidfile": f"{pidfile}",
                "dir": f"{self}->{dir}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
        )

    def user_defined(self, options):

        # File in which to store the process ID so that it can be killed if necessary

        pidfile = self.create_pidfile(options)
        if pidfile is None:
            return
        uuid = self._note_callbacks(options)
        sentinel = _enqueue_request(
            "user-defined",
            {
                "page": options["page"],
                "command": options["command"],
                "dir": f"{self}->{dir}",
                "pidfile": f"{pidfile}",
                "uuid": uuid,
            },
        )
        return self._monitor_process(
            sentinel=sentinel,
            pidfile=pidfile,
            uuid=uuid,
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

        filenamelist.append(File.Spec.catfile(self.dir, "session"))
        selection = self.get_selected_indices()
        session["selection"] = selection
        if version is not None:
            session["version"] = version
        store(session, File.Spec.catfile(self.dir, "session"))
        if filename is not None:
            tar = Archive.Tar()
            tar.add_files(filenamelist)
            tar.write(filename, True, EMPTY)
            for i in range(len(self.data)):
                self.data[i][2]["saved"] = True

    def open_session_file(self, options):

        if "info" not in options:
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", "Error: session file not supplied."
                )

            return

        tar = Archive.Tar(options["info"], True)
        filenamelist = tar.list_files()
        sessionfile = [x for x in filenamelist if re.search(r"\/session$", x)]
        sesdir = File.Spec.catfile(self.dir, dirname(sessionfile[0]))
        for _ in filenamelist:
            tar.extract_file(_, File.Spec.catfile(sesdir, basename(_)))

        self.open_session(dir=sesdir, delete=True, **options)
        if options["finished_callback"]:
            options["finished_callback"]()

    def open_session(self, options):

        if "dir" not in options:
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", "Error: session folder not defined"
                )

            return

        sessionfile = File.Spec.catfile(options["dir"], "session")
        if not os.access(sessionfile, os.R_OK):
            if options["error_callback"]:
                options["error_callback"](
                    None, "Open file", f"Error: Unable to read {sessionfile}"
                )

            return

        sessionref = retrieve(sessionfile)

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
            logger.info(f"Restoring v{sessionref}->{version} session file.")

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
                session[pagenum]["filename"] = File.Spec.catfile(
                    options["dir"], basename(session[pagenum]["filename"])
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
                logger.info(f"Renumbering page {self.data[_][0]}->{start}")
                self.data[_][0] = start
                start += step

        # If $start and $step are undefined, just make sure that the numbering is
        # ascending.

        else:
            for _ in range(1, len(self.data)):
                if self.data[_][0] <= self.data[_ - 1][0]:
                    new = self.data[_ - 1][0] + 1
                    logger.info(f"Renumbering page {self}->{data}[{_}][0]->{new}")
                    self.data[_][0] = new

        if self.row_changed_signal is not None:
            self.get_model().handler_unblock(self.row_changed_signal)

    def valid_renumber(self, start, step, selection):
        "Check if $start and $step give duplicate page numbers"
        logger.debug(
            f"Checking renumber validity of: start {start}, step {step}, selection {selection}"
        )
        if step == 0 or start < 1:
            return False

        # if we are renumbering all pages, just make sure the numbers stay positive
        if selection == "all":
            if step < 0:
                return (start + (len(self.data) - 1) * step) > 0
            return True

        # Get list of pages not in selection
        selected = self.get_selected_indices()
        all = list(range(len(self.data)))

        # Convert the indices to sets of page numbers
        selected = self.index2page_number(selected)
        all = self.index2page_number(all)
        selected = set(selected)
        all = set(all)
        not_selected = all - selected
        logger.debug(f"Page numbers not selected: {not_selected}")

        # Create a set from the current settings
        current = {start + step * i for i in range(len(selected))}
        logger.debug(f"Current setting would create page numbers: {current}")

        # Are any of the new page numbers the same as those not selected?
        if len(current.intersection(not_selected)):
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

    def set_dir(self, dir):
        """Have to roll my own slurp sub to support utf8







        wrapper for _program_version below



        Check exec_command output for version number
        Don't call exec_command directly to allow us to test output we can't reproduce.



        Check that a command exists



        Compute a timestamp







        Normally, it would be more sensible to put this in main::, but in order to
        run unit tests on the sub, it has been moved here.



        calculate delta between two timezones - mostly to spot differences between
        DST.



        apply timezone delta



        delta timezone to current. Putting here to be able to test it for dates before 1970.





        Set session dir"""
        self.dir = dir

    def _monitor_process(self, options):

        if "pidfile" in options:
            self.running_pids[f"{options}{pidfile}"] = f"{options}{pidfile}"

        if callback[options["uuid"]]["queued"]:
            callback[options["uuid"]]["queued"](
                process_name=_self["process_name"],
                jobs_completed=jobs_completed,
                jobs_total=jobs_total,
            )

        def anonymous_13():
            if options["sentinel"] == 2:
                self._monitor_process_finished_callback(options)
                return Glib.SOURCE_REMOVE

            elif options["sentinel"] == 1:
                self._monitor_process_running_callback(options)
                return Glib.SOURCE_CONTINUE

            return Glib.SOURCE_CONTINUE

        Glib.Timeout.add(_POLL_INTERVAL, anonymous_13)
        return options["pidfile"]

    def _monitor_process_running_callback(self, options):

        if _self["cancel"]:
            return
        if callback[options["uuid"]]["started"]:
            callback[options["uuid"]]["started"](
                1,
                _self["process_name"],
                jobs_completed,
                jobs_total,
                _self["message"],
                _self["progress"],
            )
            del callback[options["uuid"]]["started"]

        if callback[options["uuid"]]["running"]:
            callback[options["uuid"]]["running"](
                process=_self["process_name"],
                jobs_completed=jobs_completed,
                jobs_total=jobs_total,
                message=_self["message"],
                progress=_self["progress"],
            )

    def _monitor_process_finished_callback(self, options):

        if _self["cancel"]:
            return
        if callback[options["uuid"]]["started"]:
            callback[options["uuid"]]["started"](
                None,
                _self["process_name"],
                jobs_completed,
                jobs_total,
                _self["message"],
                _self["progress"],
            )
            del callback[options["uuid"]]["started"]

        if _self["status"]:
            if callback[options["uuid"]]["error"]:
                callback[options["uuid"]]["error"](_self["message"])

            return

        self.check_return_queue()
        if "pidfile" in options:
            del self.running_pids[f"{options}->{pidfile}"]

    def _thread_main(self):

        for request in self["requests"].dequeue():
            self.process_name = request["action"]

            # Signal the sentinel that the request was started.

            request["sentinel"] += 1

            # Ask for page data given UUID

            if "page" in request:
                self.return_queue.enqueue(
                    {"type": "page request", "uuid": request["page"]}
                )
                page_request = self.pages.dequeue()
                if page_request["page"] == "cancel":
                    continue
                request["page"] = page_request["page"]

            elif "list_of_pages" in request:
                cancel = False
                for i in range(len(request["list_of_pages"]) - 1 + 1):
                    self.return_queue.enqueue(
                        {"type": "page request", "uuid": request["list_of_pages"][i]}
                    )
                    page_request = self.pages.dequeue()
                    if page_request["page"] == "cancel":
                        cancel = True
                        break

                    request["list_of_pages"][i] = page_request["page"]

                if cancel:
                    continue

            if request["action"] == "analyse":
                _thread_analyse(self, request["list_of_pages"], request["uuid"])

            elif request["action"] == "brightness-contrast":
                _thread_brightness_contrast(
                    self,
                    page=request["page"],
                    brightness=request["brightness"],
                    contrast=request["contrast"],
                    dir=request["dir"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "cancel":
                lock(_self["pages"])  # unlocks automatically when out of scope

                # Empty pages queue

                while _self["pages"].pending():
                    _self["pages"].dequeue()

                self.return_queue.enqueue(
                    {"type": "cancelled", "uuid": request["uuid"]}
                )

            elif request["action"] == "crop":
                _thread_crop(
                    self,
                    page=request["page"],
                    x=request["x"],
                    y=request["y"],
                    w=request["w"],
                    h=request["h"],
                    dir=request["dir"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "split":
                _thread_split(
                    self,
                    page=request["page"],
                    direction=request["direction"],
                    position=request["position"],
                    dir=request["dir"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "cuneiform":
                _thread_cuneiform(
                    self,
                    page=request["page"],
                    language=request["language"],
                    threshold=request["threshold"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "get-file-info":
                _thread_get_file_info(
                    self,
                    filename=request["path"],
                    password=request["password"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "gocr":
                _thread_gocr(
                    self,
                    request["page"],
                    request["threshold"],
                    request["pidfile"],
                    request["uuid"],
                )

            elif request["action"] == "import-file":
                _thread_import_file(
                    self,
                    info=request["info"],
                    password=request["password"],
                    first_page=request["first"],
                    last_page=request["last"],
                    dir=request["dir"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "negate":
                _thread_negate(self, request["page"], request["dir"], request["uuid"])

            elif request["action"] == "paper_sizes":
                _thread_paper_sizes(self, request["paper_sizes"])

            elif request["action"] == "quit":
                break

            elif request["action"] == "rotate":
                _thread_rotate(
                    self,
                    request["angle"],
                    request["page"],
                    request["dir"],
                    request["uuid"],
                )

            elif request["action"] == "save-djvu":
                _thread_save_djvu(
                    self,
                    path=request["path"],
                    list_of_pages=request["list_of_pages"],
                    metadata=request["metadata"],
                    options=request["options"],
                    dir=request["dir"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "save-hocr":
                _thread_save_hocr(
                    self,
                    request["path"],
                    request["list_of_pages"],
                    request["options"],
                    request["uuid"],
                )

            elif request["action"] == "save-image":
                _thread_save_image(
                    self,
                    path=request["path"],
                    list_of_pages=request["list_of_pages"],
                    pidfile=request["pidfile"],
                    options=request["options"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "save-pdf":
                _thread_save_pdf(
                    self,
                    path=request["path"],
                    list_of_pages=request["list_of_pages"],
                    metadata=request["metadata"],
                    options=request["options"],
                    dir=request["dir"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "save-text":
                _thread_save_text(
                    self,
                    request["path"],
                    request["list_of_pages"],
                    request["options"],
                    request["uuid"],
                )

            elif request["action"] == "save-tiff":
                _thread_save_tiff(
                    self,
                    path=request["path"],
                    list_of_pages=request["list_of_pages"],
                    options=request["options"],
                    dir=request["dir"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "tesseract":
                _thread_tesseract(
                    self,
                    page=request["page"],
                    language=request["language"],
                    threshold=request["threshold"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "threshold":
                _thread_threshold(
                    self,
                    request["threshold"],
                    request["page"],
                    request["dir"],
                    request["uuid"],
                )

            elif request["action"] == "to-png":
                _thread_to_png(self, request["page"], request["dir"], request["uuid"])

            elif request["action"] == "unpaper":
                _thread_unpaper(
                    self,
                    page=request["page"],
                    options=request["options"],
                    pidfile=request["pidfile"],
                    dir=request["dir"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "unsharp":
                _thread_unsharp(
                    self,
                    page=request["page"],
                    radius=request["radius"],
                    sigma=request["sigma"],
                    gain=request["gain"],
                    threshold=request["threshold"],
                    dir=request["dir"],
                    uuid=request["uuid"],
                )

            elif request["action"] == "user-defined":
                _thread_user_defined(
                    self,
                    page=request["page"],
                    command=request["command"],
                    dir=request["dir"],
                    pidfile=request["pidfile"],
                    uuid=request["uuid"],
                )

            else:
                logger.info("Ignoring unknown request " + request["action"])
                continue

            # Signal the sentinel that the request was completed.

            request["sentinel"] += 1
            self.process_name = None

    def _thread_throw_error(self, uuid, page_uuid, process, message):

        self.return_queue.enqueue(
            {
                "type": "error",
                "uuid": uuid,
                "page": page_uuid,
                "process": process,
                "message": message,
            }
        )


    def _thread_import_pdf(self, options):

        (warning_flag, xresolution, yresolution) = (None, None, None)

        # Extract images from PDF

        if options["last"] >= options["first"] and options["first"] > 0:
            pdfobj = PDF.Builder.open(options["info"]["path"])
            for i in range(options["first"], options["last"] + 1):
                args = ["pdfimages", "-f", i, "-l", i, "-list", options["info"]["path"]]
                if "password" in options:
                    del (args[1], options["password"])
                    args.insert(1, "-upw")

                (status, out, err) = exec_command(args, options["pidfile"])
                for _ in re.split(r"\n", out):
                    (xresolution, yresolution) = struct.unpack("x69A6xA6", _)
                    if re.search(
                        r"\d", xresolution, re.MULTILINE | re.DOTALL | re.VERBOSE
                    ):
                        break

                args = ["pdfimages", "-f", i, "-l", i, options["info"]["path"], "x"]
                if "password" in options:
                    del (args[1], options["password"])
                    args.insert(1, "-upw")

                (status, out, err) = exec_command(args, options["pidfile"])
                if _self["cancel"]:
                    return
                if status:
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Open file",
                        _("Error extracting images from PDF"),
                    )

                html = tempfile.TemporaryFile(dir=options["dir"], suffix=".html")
                args = [
                    "pdftotext",
                    "-bbox",
                    "-f",
                    i,
                    "-l",
                    i,
                    options["info"]["path"],
                    html,
                ]
                if "password" in options:
                    del (args[1], options["password"])
                    args.insert(1, "-upw")

                (status, out, err) = exec_command(args, options["pidfile"])
                if _self["cancel"]:
                    return
                if status:
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Open file",
                        _("Error extracting text layer from PDF"),
                    )

                pageobj = pdfobj.openpage(i)

                # Import each image

                images = glob.glob("x-??*.???")
                if len(images) != 1:
                    warning_flag = True
                for _ in images:
                    (ext) = re.search(
                        r"([^.]+)$", _, re.MULTILINE | re.DOTALL | re.VERBOSE
                    )
                    try:
                        page = Page(
                            filename=_,
                            dir=options["dir"],
                            delete=True,
                            format=image_format[ext],
                            xresolution=xresolution,
                            yresolution=yresolution,
                        )
                        page.import_pdftotext(slurp(html))
                        self.return_queue.enqueue(
                            {
                                "type": "page",
                                "uuid": options["uuid"],
                                "page": page.to_png(paper_sizes).freeze(),
                            }
                        )

                    except:
                        logger.error(f"Caught error importing PDF: {_}")
                        _thread_throw_error(
                            self,
                            options["uuid"],
                            options["page"]["uuid"],
                            "Open file",
                            _("Error importing PDF"),
                        )

            if warning_flag:
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Open file",
                    _(
                        """Warning: gscan2pdf expects one image per page, but this was not satisfied. It is probable that the PDF has not been correctly imported.

If you wish to add scans to an existing PDF, use the prepend/append to PDF options in the Save dialogue.
"""
                    ),
                )

    def _append_pdf(self, filename, options):

        (bak, file1, file2, out, message) = (None, None, None, None, None)
        if "prepend" in options["options"]:
            file1 = filename
            file2 = f"{options}{options}{prepend}.bak"
            bak = file2
            out = options["options"]["prepend"]
            message = _("Error prepending PDF: %s")
            logger.info("Prepending PDF")

        else:
            file2 = filename
            file1 = f"{options}{options}{append}.bak"
            bak = file1
            out = options["options"]["append"]
            message = _("Error appending PDF: %s")
            logger.info("Appending PDF")

        if not os.rename(out, bak):
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error creating backup of PDF"),
            )
            return

        (status, _, error) = exec_command(
            ["pdfunite", file1, file2, out], options["pidfile"]
        )
        if status:
            logger.info(error)
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                message % (error),
            )
            return status

    def _encrypt_pdf(self, filename, options):

        cmd = ["pdftk", filename, "output", options["path"]]
        if "user-password" in options["options"]:
            cmd.append("user_pw", options["options"]["user-password"])

        (status, _, error) = exec_command(cmd, options["pidfile"])
        if status or error:
            logger.info(error)
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error encrypting PDF: %s") % (error),
            )
            return status

    def _add_annotations_to_pdf(self, page, gs_page):
        """Box is the same size as the page. We don't know the text position.
        Start at the top of the page (PDF coordinate system starts
        at the bottom left of the page)"""
        xresolution = gs_page["xresolution"]
        yresolution = gs_page["yresolution"]
        h = px2pt(gs_page["height"], yresolution)
        iter = Bboxtree(gs_page["annotations"]).get_bbox_iter()
        for box in iter:
            if box["type"] == "page" or "text" not in box or box["text"] == EMPTY:
                continue

            rgb = []
            for i in range(2 + 1):
                rgb.append(hex(ANNOTATION_COLOR[i : i + 2, 2]) / int("0xff", 0))

            annot = page.annotation()
            annot.markup(
                box["text"],
                _bbox2markup(xresolution, yresolution, h, len(box["bbox"])),
                "Highlight",
                color=rgb,
                opacity=0.5,
            )

    def _thread_save_djvu(self, options):

        page = 0
        filelist = []
        for pagedata in options["list_of_pages"]:
            page += 1
            self.progress = page / (len(options["list_of_pages"]) - 1 + 2)
            self.message = _("Writing page %i of %i") % (
                page,
                len(options["list_of_pages"]) - 1 + 1,
            )
            (djvu, error) = (None, None)
            try:
                djvu = tempfile.TemporaryFile(dir=options["dir"], suffix=".djvu")

            except:
                logger.error(f"Caught error writing DjVu: {_}")
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    f"Caught error writing DjVu: {_}.",
                )
                error = True

            if error:
                return
            (compression, filename, resolution) = _convert_image_for_djvu(
                self, pagedata, page, options
            )

            # Create the djvu

            (status) = exec_command(
                [compression, "-dpi", int(resolution), filename, djvu],
                options["pidfile"],
            )
            size = os.path.getsize(
                f"{djvu}"
            )  # quotes needed to prevent -s clobbering File::Temp object
            if _self["cancel"]:
                return
            if status != 0 or not size:
                logger.error(
                    f"Error writing image for page {page} of DjVu (process returned {status}, image size {size})"
                )
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error writing DjVu"),
                )
                return

            filelist.append(djvu)
            _add_txt_to_djvu(self, djvu, options["dir"], pagedata, options["uuid"])
            _add_ann_to_djvu(self, djvu, options["dir"], pagedata, options["uuid"])

        self.progress = 1
        self.message = _("Merging DjVu")
        (status, out, err) = exec_command(
            ["djvm", "-c", options["path"], filelist], options["pidfile"]
        )
        if _self["cancel"]:
            return
        if status:
            logger.error("Error merging DjVu")
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error merging DjVu"),
            )

        _add_metadata_to_djvu(self, options)
        _set_timestamp(self, options)
        _post_save_hook(options["path"], options["options"])
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "save-djvu",
                "uuid": options["uuid"],
            }
        )

    def _convert_image_for_djvu(self, pagedata, page, options):

        filename = pagedata["filename"]

        # Check the image depth to decide what sort of compression to use

        image = PythonMagick.Image()
        e = image.Read(filename)
        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                f"Error reading {filename}: {e}.",
            )
            return

        depth = image.Get("depth")
        _class = image.Get("class")
        (compression, resolution, upsample) = (None, None, None)

        # Get the size

        pagedata["w"] = image.Get("width")
        pagedata["h"] = image.Get("height")
        pagedata["pidfile"] = options["pidfile"]
        pagedata["page_number"] = page

        # c44 and cjb2 do not support different resolutions in the x and y
        # directions, so resample

        if pagedata["xresolution"] != pagedata["yresolution"]:
            resolution = (
                pagedata["xresolution"]
                if pagedata["xresolution"] > pagedata["yresolution"]
                else pagedata["yresolution"]
            )
            pagedata["w"] *= resolution / pagedata["xresolution"]
            pagedata["h"] *= resolution / pagedata["yresolution"]
            logger.info(f"Upsampling to {resolution}" + f"x{resolution}")
            image.Sample(width=pagedata["w"], height=pagedata["h"])
            upsample = True

        else:
            resolution = pagedata["xresolution"]

        # c44 can only use pnm and jpg

        format = None
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            format = regex.group(1)

        if depth > 1:
            compression = "c44"
            if (
                not re.search(
                    r"(?:pnm|jpg)", format, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                or upsample
            ):
                pnm = tempfile.TemporaryFile(dir=options["dir"], suffix=".pnm")
                e = image.Write(filename=pnm)
                if f"{e}":
                    logger.error(e)
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        f"Error writing {pnm}: {e}.",
                    )
                    return

                filename = pnm

        # cjb2 can only use pnm and tif

        else:
            compression = "cjb2"
            if (
                not re.search(
                    r"(?:pnm|tif)", format, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                or (format == "pnm" and _class != "PseudoClass")
                or upsample
            ):
                pbm = tempfile.TemporaryFile(dir=options["dir"], suffix=".pbm")
                e = image.Write(filename=pbm)
                if f"{e}":
                    logger.error(e)
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        f"Error writing {pbm}: {e}.",
                    )
                    return

                filename = pbm

        return compression, filename, resolution

    def _write_file(self, fh, filename, data, uuid):

        if not fh.write(data):
            _thread_throw_error(
                self, uuid, None, "Save file", _("Can't write to file: %s") % (filename)
            )
            return False

        return True

    def _add_txt_to_djvu(self, djvu, dir, pagedata, uuid):

        if "text_layer" in pagedata:
            txt = pagedata.export_djvu_txt()
            if txt == EMPTY:
                return

            # Write djvusedtxtfile

            djvusedtxtfile = tempfile.TemporaryFile(dir=dir, suffix=".txt")
            logger.debug(txt)
            try:
                fh = open(">:encoding(UTF8)", djvusedtxtfile)

            except:
                raise (_("Can't open file: %s") % (djvusedtxtfile))
            try:
                _write_file(self, fh, djvusedtxtfile, txt, uuid)
            except:
                return
            try:
                fh.close()

            except:
                raise (_("Can't close file: %s") % (djvusedtxtfile))

            # Run djvusedtxtfile

            cmd = [
                "djvused",
                djvu,
                "-e",
                f"select 1; set-txt {djvusedtxtfile}",
                "-s",
            ]
            (status) = exec_command(cmd, pagedata["pidfile"])
            if _self["cancel"]:
                return
            if status:
                logger.error(
                    f"Error adding text layer to DjVu page {pagedata}->{page_number}"
                )
                _thread_throw_error(
                    self,
                    uuid,
                    pagedata["uuid"],
                    "Save file",
                    _("Error adding text layer to DjVu"),
                )

    def _add_ann_to_djvu(self, djvu, dir, pagedata, uuid):
        """FIXME - refactor this together with _add_txt_to_djvu"""
        if "annotations" in pagedata:
            ann = pagedata.export_djvu_ann()
            if ann == EMPTY:
                return

            # Write djvusedtxtfile

            djvusedtxtfile = tempfile.TemporaryFile(dir=dir, suffix=".txt")
            logger.debug(ann)
            try:
                fh = open(">:encoding(UTF8)", djvusedtxtfile)

            except:
                raise (_("Can't open file: %s") % (djvusedtxtfile))
            try:
                _write_file(self, fh, djvusedtxtfile, ann, uuid)
            except:
                return
            try:
                fh.close()

            except:
                raise (_("Can't close file: %s") % (djvusedtxtfile))

            # Run djvusedtxtfile

            cmd = [
                "djvused",
                djvu,
                "-e",
                f"select 1; set-ant {djvusedtxtfile}",
                "-s",
            ]
            (status) = exec_command(cmd, pagedata["pidfile"])
            if _self["cancel"]:
                return
            if status:
                logger.error(
                    f"Error adding annotations to DjVu page {pagedata}->{page_number}"
                )
                _thread_throw_error(
                    self,
                    uuid,
                    pagedata["uuid"],
                    "Save file",
                    _("Error adding annotations to DjVu"),
                )

    def _add_metadata_to_djvu(self, options):

        if options["metadata"] and options["metadata"]:

            # Open djvusedmetafile

            djvusedmetafile = tempfile.TemporaryFile(dir=options["dir"], suffix=".txt")
            try:
                fh = open(
                    ">:encoding(UTF8)", djvusedmetafile
                )  ## no critic (RequireBriefOpen)

            except:
                raise (_("Can't open file: %s") % (djvusedmetafile))
            try:
                _write_file(self, fh, djvusedmetafile, "(metadata\n", options["uuid"])
            except:
                return

            # Write the metadata

            metadata = prepare_output_metadata("DjVu", options["metadata"])
            for key in metadata.keys():
                val = metadata[key]

                # backslash-escape any double quotes and bashslashes

                val = re.sub(
                    r"\\", r"\\\\", val, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                val = re.sub(
                    r"\"", r"\\\"", val, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                try:
                    _write_file(
                        self, fh, djvusedmetafile, f'{key} "{val}"\n', options["uuid"]
                    )
                except:
                    return

            try:
                _write_file(self, fh, djvusedmetafile, ")", options["uuid"])
            except:
                return
            try:
                fh.close()

            except:
                raise (_("Can't close file: %s") % (djvusedmetafile))

            # Write djvusedmetafile

            cmd = [
                "djvused",
                options["path"],
                "-e",
                f"set-meta {djvusedmetafile}",
                "-s",
            ]
            (status) = exec_command(cmd, options["pidfile"])
            if _self["cancel"]:
                return
            if status:
                logger.error("Error adding metadata info to DjVu file")
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error adding metadata to DjVu"),
                )

    def _thread_save_tiff(self, options):

        page = 0
        filelist = []
        for pagedata in options["list_of_pages"]:
            page += 1
            self.progress = (page - 1) / (len(options["list_of_pages"]) - 1 + 2)
            self.message = _("Converting image %i of %i to TIFF") % (
                page,
                len(options["list_of_pages"]) - 1 + 1,
            )
            filename = pagedata["filename"]
            if not re.search(
                r"[.]tif", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            ) or (
                "compression" in options["options"]
                and options["options"]["compression"] == "jpeg"
            ):
                (tif, error) = (None, None)
                try:
                    tif = tempfile.TemporaryFile(dir=options["dir"], suffix=".tif")

                except:
                    logger.error(f"Error writing TIFF: {_}")
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        f"Error writing TIFF: {_}.",
                    )
                    error = True

                if error:
                    return
                xresolution = pagedata["xresolution"]
                yresolution = pagedata["yresolution"]

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
                    xresolution + "x" + yresolution,
                    depth,
                    tif,
                ]
                (status) = exec_command(cmd, options["pidfile"])
                if _self["cancel"]:
                    return
                if status:
                    logger.error("Error writing TIFF")
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        _("Error writing TIFF"),
                    )
                    return

                filename = tif

            filelist.append(filename)

        compression = []
        if "compression" in options["options"]:
            compression = ["-c", f"{options}{options}{compression}"]
            if options["options"]["compression"] == "jpeg":
                compression[1] += f":{options}{options}{quality}"
                compression.append(["-r", "16"])

        # Create the tiff
        self.progress = 1
        self.message = _("Concatenating TIFFs")
        cmd = ["tiffcp", compression, filelist, options["path"]]
        (status, _, error) = exec_command(cmd, options["pidfile"])
        if _self["cancel"]:
            return
        if status or error != EMPTY:
            logger.info(error)
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Save file",
                _("Error compressing image: %s") % (error),
            )
            return

        if "ps" in options["options"]:
            self.message = _("Converting to PS")
            cmd = ["tiff2ps", "-3", options["path"], "-O", options["options"]["ps"]]
            (status, _, error) = exec_command(cmd, options["pidfile"])
            if status or error:
                logger.info(error)
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error converting TIFF to PS: %s") % (error),
                )
                return

            _post_save_hook(options["options"]["ps"], options["options"])

        else:
            _post_save_hook(options["path"], options["options"])

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "save-tiff",
                "uuid": options["uuid"],
            }
        )

    def _thread_no_filename(self, process, uuid, page):

        if "filename" not in page:  # in case file was deleted after process started
            e = f"Page for process {uuid} no longer exists. Cannot {process}."
            logger.error(e)
            _thread_throw_error(self, uuid, page["uuid"], process, e)
            return True

    def _thread_rotate(self, angle, page, dir, uuid):

        if _thread_no_filename(self, "rotate", uuid, page):
            return
        filename = page["filename"]
        logger.info(f"Rotating {filename} by {angle} degrees")

        # Rotate with imagemagick

        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)

        # workaround for those versions of imagemagick that produce 16bit output
        # with rotate

        depth = image.Get("depth")
        e = image.Rotate(angle)
        if f"{e}":
            logger.error(e)
            _thread_throw_error(self, uuid, page["uuid"], "Rotate", e)
            return

        if _self["cancel"]:
            return
        (suffix, error) = (None, None)
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        try:
            filename = tempfile.NamedTemporaryFile(
                dir=dir, suffix=f".{suffix}", delete=False
            )
            e = image.Write(filename=filename, depth=depth)

        except:
            logger.error(f"Error rotating: {_}")
            _thread_throw_error(self, uuid, page["uuid"], "Rotate", _)
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)
        page["filename"] = filename.filename()
        page["dirty_time"] = timestamp()  # flag as dirty
        if angle == _90_DEGREES or angle == _270_DEGREES:
            (page["width"], page["height"]) = (page["height"], page["width"])
            (page["xresolution"], page["yresolution"]) = (
                page["yresolution"],
                page["xresolution"],
            )

        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": uuid,
                "page": page,
                "info": {"replace": page["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "rotate",
                "uuid": uuid,
            }
        )

    def _thread_save_image(self, options):

        if options["list_of_pages"] == 1:
            status = exec_command(
                [
                    "convert",
                    options["list_of_pages"][0]["filename"],
                    "-density",
                    options["list_of_pages"][0]["xresolution"]
                    + "x"
                    + options["list_of_pages"][0]["yresolution"],
                    options["path"],
                ],
                options["pidfile"],
            )
            if _self["cancel"]:
                return
            if status:
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "Save file",
                    _("Error saving image"),
                )

            _post_save_hook(options["list_of_pages"][0]["filename"], options["options"])

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
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "Save file",
                        _("Error saving image"),
                    )

                _post_save_hook(_["filename"], options["options"])

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "save-image",
                "uuid": options["uuid"],
            }
        )

    def _thread_save_text(self, path, list_of_pages, options, uuid):

        fh = None
        string = EMPTY
        for page in list_of_pages:
            string += page.export_text()
            if _self["cancel"]:
                return

        try:
            fh = open(">", path)
        except:
            _thread_throw_error(
                self, uuid, None, "Save file", _("Can't open file: %s") % (path)
            )
            return

        try:
            _write_file(self, fh, path, string, uuid)
        except:
            return
        if not fh.close():
            _thread_throw_error(
                self, uuid, None, "Save file", _("Can't close file: %s") % (path)
            )

        _post_save_hook(path, options)
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "save-text",
                "uuid": uuid,
            }
        )

    def _thread_save_hocr(self, path, list_of_pages, options, uuid):

        fh = None
        try:
            fh = open(">", path)
        except:
            _thread_throw_error(
                self, uuid, None, "Save file", _("Can't open file: %s") % (path)
            )
            return

        written_header = False
        for _ in list_of_pages:
            hocr = _.export_hocr()
            regex = re.search(
                r"([\s\S]*<body>)([\s\S]*)<\/body>",
                hocr,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if (hocr is not None) and regex:
                header = regex.group(1)
                hocr_page = regex.group(2)
                if not written_header:
                    try:
                        _write_file(self, fh, path, header, uuid)
                    except:
                        return
                    written_header = True

                try:
                    _write_file(self, fh, path, hocr_page, uuid)
                except:
                    return
                if _self["cancel"]:
                    return

        if written_header:
            try:
                _write_file(self, fh, path, "</body>\n</html>\n", uuid)
            except:
                return

        try:
            fh.close()
        except:
            _thread_throw_error(
                self, uuid, None, "Save file", _("Can't close file: %s") % (path)
            )

        _post_save_hook(path, options)
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "save-hocr",
                "uuid": uuid,
            }
        )

    def _thread_analyse(self, list_of_pages, uuid):

        i = 1
        total = list_of_pages
        for page in list_of_pages:
            self.progress = (i - 1) / total
            self.message = _("Analysing page %i of %i") % (i, total)
            i += 1

            # Identify with imagemagick

            image = PythonMagick.Image()
            e = image.Read(page["filename"])
            if f"{e}":
                logger.error(e)
                _thread_throw_error(
                    self,
                    uuid,
                    page["uuid"],
                    "Analyse",
                    f"Error reading {page}->{filename}: {e}.",
                )
                return

            if _self["cancel"]:
                return
            (depth, min, max, mean, stddev) = image.Statistics()
            if depth is None:
                logger.warn("image->Statistics() failed")

            logger.info(f"std dev: {stddev} mean: {mean}")
            if _self["cancel"]:
                return
            maxq = (1 << depth) - 1
            mean = mean / maxq if maxq else 0
            if re.search(r"^[-]nan$", stddev, re.MULTILINE | re.DOTALL | re.VERBOSE):
                stddev = 0

            # my $quantum_depth = $image->QuantumDepth;
            # warn "image->QuantumDepth failed" unless defined $quantum_depth;
            # TODO add any other useful image analysis here e.g. is the page mis-oriented?
            #  detect mis-orientation possible algorithm:
            #   blur or low-pass filter the image (so words look like ovals)
            #   look at few vertical narrow slices of the image and get the Standard Deviation
            #   if most of the Std Dev are high, then it might be portrait
            # TODO may need to send quantumdepth

            page["mean"] = mean
            page["std_dev"] = stddev
            page["analyse_time"] = timestamp()
            self.return_queue.enqueue(
                {
                    "type": "page",
                    "uuid": uuid,
                    "page": page,
                    "info": {"replace": page["uuid"]},
                }
            )

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "analyse",
                "uuid": uuid,
            }
        )

    def _thread_threshold(self, threshold, page, dir, uuid):

        if _thread_no_filename(self, "threshold", uuid, page):
            return
        filename = page["filename"]
        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)

        # Using imagemagick, as Perlmagick has performance problems.
        # See https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=968918

        out = None
        try:
            out = tempfile.NamedTemporaryFile(dir=dir, suffix=".pbm", delete=False)

        except:
            logger.error(_)
            _thread_throw_error(self, uuid, page["uuid"], "Threshold", _)
            return

        cmd = [
            "convert",
            filename,
            "+dither",
            "-threshold",
            f"{threshold}%",
            out,
        ]
        (status, stdout, stderr) = exec_command(cmd)
        if status != 0:
            logger.error(stderr)
            _thread_throw_error(self, uuid, page["uuid"], "Threshold", stderr)
            return

        if _self["cancel"]:
            return
        page["filename"] = out.filename()
        page["dirty_time"] = timestamp()  # flag as dirty
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": uuid,
                "page": page,
                "info": {"replace": page["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "theshold",
                "uuid": uuid,
            }
        )

    def _thread_brightness_contrast(self, options):

        if _thread_no_filename(
            self, "brightness-contrast", options["uuid"], options["page"]
        ):
            return

        filename = options["page"]["filename"]
        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)
        depth = image.Get("depth")

        # BrightnessContrast the image

        image.BrightnessContrast(
            brightness=2 * options["brightness"] - _100PERCENT,
            contrast=2 * options["contrast"] - _100PERCENT,
        )
        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "Brightness-contrast", e
            )
            return

        if _self["cancel"]:
            return

        # Write it

        error = None
        try:
            suffix = None
            regex = re.search(
                r"([.]\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=suffix, delete=False
            )
            e = image.Write(depth=depth, filename=filename)
            if f"{e}":
                logger.warn(e)

        except:
            logger.error(f"Error changing brightness / contrast: {_}")
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "Brightness-contrast", _
            )
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        logger.info(
            f"Wrote {filename} with brightness / contrast changed to {options}{brightness} / {options}{contrast}"
        )
        options["page"]["filename"] = filename.filename()
        options["page"]["dirty_time"] = timestamp()  # flag as dirty
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "brightness-contrast",
                "uuid": options["uuid"],
            }
        )

    def _thread_negate(self, page, dir, uuid):

        if _thread_no_filename(self, "negate", uuid, page):
            return
        filename = page["filename"]
        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)
        depth = image.Get("depth")

        # Negate the image

        e = image.Negate(channel="RGB")
        if f"{e}":
            logger.error(e)
            _thread_throw_error(self, uuid, page["uuid"], "Negate", e)
            return

        if _self["cancel"]:
            return

        # Write it

        error = None
        try:
            suffix = None
            regex = re.search(
                r"([.]\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(dir=dir, suffix=suffix, delete=False)
            e = image.Write(depth=depth, filename=filename)
            if f"{e}":
                logger.warn(e)

        except:
            logger.error(f"Error negating: {_}")
            _thread_throw_error(self, uuid, page["uuid"], "Negate", _)
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        logger.info(f"Negating to {filename}")
        page["filename"] = filename.filename()
        page["dirty_time"] = timestamp()  # flag as dirty
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": uuid,
                "page": page,
                "info": {"replace": page["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "negate",
                "uuid": uuid,
            }
        )

    def _thread_unsharp(self, options):

        if _thread_no_filename(self, "unsharp", options["uuid"], options["page"]):
            return

        filename = options["page"]["filename"]
        version = None
        image = PythonMagick.Image()
        regex = re.search(
            r"ImageMagick\s([\d.]+)",
            image.Get("version"),
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        if regex:
            version = regex.group(1)

        logger.debug(f"Image::Magick->version {version}")
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)

        # Unsharp the image

        if version.parse(f"v{version}") >= version.parse("v7.0.0"):
            e = image.UnsharpMask(
                radius=options["radius"],
                sigma=options["sigma"],
                gain=options["gain"],
                threshold=options["threshold"],
            )

        else:
            e = image.UnsharpMask(
                radius=options["radius"],
                sigma=options["sigma"],
                amount=options["gain"],
                threshold=options["threshold"],
            )

        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "Unsharp", e
            )
            return

        if _self["cancel"]:
            return

        # Write it

        error = None
        try:
            suffix = None
            regex = re.search(
                r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            e = image.Write(filename=filename)
            if f"{e}":
                logger.warn(e)

        except:
            logger.error(f"Error writing image with unsharp mask: {_}")
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "Unsharp",
                f"Error writing image with unsharp mask: {_}.",
            )
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        logger.info(
            f"Wrote {filename} with unsharp mask: radius={options}{radius}, sigma={options}{sigma}, gain={options}{gain}, threshold={options}{threshold}"
        )
        options["page"]["filename"] = filename.filename()
        options["page"]["dirty_time"] = timestamp()  # flag as dirty
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "unsharp",
                "uuid": options["uuid"],
            }
        )

    def _thread_crop(self, options):

        if _thread_no_filename(self, "crop", options["uuid"], options["page"]):
            return

        filename = options["page"]["filename"]
        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)

        # Crop the image

        e = image.Crop(
            width=options["w"], height=options["h"], x=options["x"], y=options["y"]
        )
        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "crop", e
            )
            return

        image.Set(page="0x0+0+0")
        if _self["cancel"]:
            return

        # Write it

        error = None
        try:
            suffix = None
            regex = re.search(
                r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            e = image.Write(filename=filename)
            if f"{e}":
                logger.warn(e)

        except:
            logger.error(f"Error cropping: {_}")
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "crop", _
            )
            error = True

        if error:
            return
        logger.info(
            f"Cropping {options}{w} x {options}{h} + {options}{x} + {options}{y} to {filename}"
        )
        if _self["cancel"]:
            return
        options["page"]["filename"] = filename.filename()
        options["page"]["width"] = options["w"]
        options["page"]["height"] = options["h"]
        options["page"]["dirty_time"] = timestamp()  # flag as dirty
        if options["page"]["text_layer"]:
            bboxtree = Bboxtree(options["page"]["text_layer"])
            options["page"]["text_layer"] = bboxtree.crop(
                options["x"], options["y"], options["w"], options["h"]
            ).json()

        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "crop",
                "uuid": options["uuid"],
            }
        )

    def _thread_split(self, options):

        if _thread_no_filename(self, "split", options["uuid"], options["page"]):
            return

        filename = options["page"]["filename"]
        filename2 = filename
        image = PythonMagick.Image()
        e = image.Read(filename)
        if _self["cancel"]:
            return
        if f"{e}":
            logger.warn(e)
        image2 = image.Clone()

        # split the image

        (w, h, x2, y2, w2, h2) = (None, None, None, None, None, None)
        if options["direction"] == "v":
            w = options["position"]
            h = image.Get("height")
            x2 = w
            y2 = 0
            w2 = image.Get("width") - w
            h2 = h

        else:
            w = image.Get("width")
            h = options["position"]
            x2 = 0
            y2 = h
            w2 = w
            h2 = image.Get("height") - h

        e = image.Crop(w + f"x{h}+0+0")
        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "crop", e
            )
            return

        image.Set(page="0x0+0+0")
        e = image2.Crop(w2 + f"x{h2}+{x2}+{y2}")
        if f"{e}":
            logger.error(e)
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "crop", e
            )
            return

        image2.Set(page="0x0+0+0")
        if _self["cancel"]:
            return

        # Write it

        error = None
        try:
            suffix = None
            regex = re.search(
                r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            if regex:
                suffix = regex.group(1)
            filename = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            e = image.Write(filename=filename)
            if f"{e}":
                logger.warn(e)
            filename2 = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            )
            e = image2.Write(filename=filename2)
            if f"{e}":
                logger.warn(e)

        except:
            logger.error(f"Error cropping: {_}")
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "crop", _
            )
            error = True

        if error:
            return
        logger.info(
            f"Splitting in direction {options}{direction} @ {options}{position} -> {filename} + {filename2}"
        )
        if _self["cancel"]:
            return
        options["page"]["filename"] = filename.filename()
        options["page"]["width"] = image.Get("width")
        options["page"]["height"] = image.Get("height")
        options["page"]["dirty_time"] = timestamp()  # flag as dirty
        new2 = Page(
            filename=filename2,
            dir=options["dir"],
            delete=True,
            format=image2.Get("format"),
        )
        if options["page"]["text_layer"]:
            bboxtree = Bboxtree(options["page"]["text_layer"])
            bboxtree2 = Bboxtree(options["page"]["text_layer"])
            options["page"]["text_layer"] = bboxtree.crop(0, 0, w, h).json()
            new2["text_layer"] = bboxtree2.crop(x2, y2, w2, h2).json()

        # crop doesn't change the resolution, so we can safely copy it

        if "xresolution" in options["page"]:
            new2["xresolution"] = options["page"]["xresolution"]
            new2["yresolution"] = options["page"]["yresolution"]

        new2["dirty_time"] = timestamp()  # flag as dirty
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": new2.freeze(),
                "info": {"insert-after": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "crop",
                "uuid": options["uuid"],
            }
        )

    def _thread_to_png(self, page, dir, uuid):

        if _thread_no_filename(self, "to_png", uuid, page):
            return
        (new, error) = (None, None)
        try:
            new = page.to_png(paper_sizes)
            new["uuid"] = page["uuid"]

        except:
            logger.error(f"Error converting to png: {_}")
            _thread_throw_error(self, uuid, page["uuid"], "to-PNG", _)
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        logger.info(f"Converted {page}->{filename} to {new}->{filename}")
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": uuid,
                "page": new.freeze(),
                "info": {"replace": page["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "to-png",
                "uuid": uuid,
            }
        )

    def _thread_tesseract(self, options):

        if _thread_no_filename(self, "tesseract", options["uuid"], options["page"]):
            return

        (error, stdout, stderr) = (None, None, None)
        try:
            (stdout, stderr) = Tesseract.hocr(
                file=options["page"]["filename"],
                language=options["language"],
                logger=logger,
                threshold=options["threshold"],
                dpi=options["page"]["xresolution"],
                pidfile=options["pidfile"],
            )
            options["page"].import_hocr(stdout)

        except:
            logger.error(f"Error processing with tesseract: {_}")
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "tesseract", _
            )
            error = True

        if error:
            return
        if _self["cancel"]:
            return
        if (stderr is not None) and stderr != EMPTY:
            _thread_throw_error(
                self, options["uuid"], options["page"]["uuid"], "tesseract", stderr
            )

        options["page"]["ocr_flag"] = 1  # FlagOCR
        options["page"][
            "ocr_time"
        ] = timestamp()  # remember when we ran OCR on this page
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "tesseract",
                "uuid": options["uuid"],
            }
        )

    def _thread_cuneiform(self, options):

        if _thread_no_filename(self, "cuneiform", options["uuid"], options["page"]):
            return

        options["page"].import_hocr(
            Cuneiform.hocr(
                file=options["page"]["filename"],
                language=options["language"],
                logger=logger,
                pidfile=options["pidfile"],
                threshold=options["threshold"],
            )
        )
        if _self["cancel"]:
            return
        options["page"]["ocr_flag"] = 1  # FlagOCR
        options["page"][
            "ocr_time"
        ] = timestamp()  # remember when we ran OCR on this page
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": options["uuid"],
                "page": options["page"],
                "info": {"replace": options["page"]["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "cuneiform",
                "uuid": options["uuid"],
            }
        )

    def _thread_gocr(self, page, threshold, pidfile, uuid):

        if _thread_no_filename(self, "gocr", uuid, page):
            return
        pnm = None
        if not re.search(
            r"[.]pnm$", page["filename"], re.MULTILINE | re.DOTALL | re.VERBOSE
        ):

            # Temporary filename for new file

            pnm = tempfile.TemporaryFile(suffix=".pnm")
            cmd = []
            if (threshold is not None) and threshold:
                logger.info(f"thresholding at {threshold} to {pnm}")
                cmd = [
                    "convert",
                    page["filename"],
                    "+dither",
                    "-threshold",
                    f"{threshold}%",
                    "-depth",
                    1,
                    pnm,
                ]

            else:
                logger.info(f"writing temporary image {pnm}")
                cmd = [
                    "convert",
                    page["filename"],
                    pnm,
                ]

            (status, stdout, stderr) = exec_command(cmd)
            if status != 0:
                logger.error(stderr)
                _thread_throw_error(self, uuid, page["uuid"], "Threshold", stderr)
                return

            if _self["cancel"]:
                return

        else:
            pnm = page["filename"]

        # Temporary filename for output

        txt = tempfile.TemporaryFile(suffix=".txt")

        # Using temporary txt file, as perl munges charset encoding
        # if text is passed by stdin/stdout

        exec_command(["gocr", pnm, "-o", txt], pidfile)
        (stdout, _) = slurp(txt)
        page.import_text(stdout)
        if _self["cancel"]:
            return
        page["ocr_flag"] = 1  # FlagOCR
        page["ocr_time"] = timestamp()  # remember when we ran OCR on this page
        self.return_queue.enqueue(
            {
                "type": "page",
                "uuid": uuid,
                "page": page,
                "info": {"replace": page["uuid"]},
            }
        )
        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "gocr",
                "uuid": uuid,
            }
        )

    def _thread_unpaper(self, options):

        if _thread_no_filename(self, "unpaper", options["uuid"], options["page"]):
            return

        filename = options["page"]["filename"]
        infile = None
        try:
            if not re.search(
                r"[.]pnm$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE
            ):
                image = PythonMagick.Image()
                e = image.Read(filename)
                if f"{e}":
                    logger.error(e)
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "unpaper",
                        f"Error reading {filename}: {e}.",
                    )
                    return

                depth = image.Get("depth")

                # Unfortunately, -depth doesn't seem to work here,
                # so forcing depth=1 using pbm extension.

                suffix = ".pbm"
                if depth > 1:
                    suffix = ".pnm"

                # Temporary filename for new file

                infile = tempfile.TemporaryFile(
                    dir=options["dir"],
                    suffix=suffix,
                )

                # FIXME: need to -compress Zip from perlmagick
                # "convert -compress Zip $self->{data}[$pagenum][2]{filename} $infile;";

                logger.debug(f"Converting {filename} -> {infile} for unpaper")
                image.Write(filename=infile)

            else:
                infile = filename

            out = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=".pnm", delete=False
            )
            out2 = EMPTY
            if re.search(
                r"--output-pages[ ]2[ ]",
                options["options"]["command"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                out2 = tempfile.NamedTemporaryFile(
                    dir=options["dir"], suffix=".pnm", delete=False
                )

            # --overwrite needed because $out exists with 0 size

            cmd = split(SPACE, f"{options}{options}{command}" % (infile, out, out2))
            (_, stdout, stderr) = exec_command(cmd, options["pidfile"])
            logger.info(stdout)
            if stderr:
                logger.error(stderr)
                _thread_throw_error(
                    self, options["uuid"], options["page"]["uuid"], "unpaper", stderr
                )
                if not os.path.getsize(out):
                    return

            if _self["cancel"]:
                return
            stdout = re.sub(
                r"Processing[ ]sheet.*[.]pnm\n",
                r"",
                stdout,
                count=1,
                flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if stdout:
                logger.warn(stdout)
                _thread_throw_error(
                    self, options["uuid"], options["page"]["uuid"], "unpaper", stdout
                )
                if not os.path.getsize(out):
                    return

            if (
                re.search(
                    r"--output-pages[ ]2[ ]",
                    options["options"]["command"],
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                and "direction" in options["options"]
                and options["options"]["direction"] == "rtl"
            ):
                (out, out2) = (out2, out)

            new = Page(
                filename=out,
                dir=options["dir"],
                delete=True,
                format="Portable anymap",
            )

            # unpaper doesn't change the resolution, so we can safely copy it

            if "xresolution" in options["page"]:
                new["xresolution"] = options["page"]["xresolution"]
                new["yresolution"] = options["page"]["yresolution"]

            # reuse uuid so that the process chain can find it again

            new["uuid"] = options["page"]["uuid"]
            new["dirty_time"] = timestamp()  # flag as dirty
            self.return_queue.enqueue(
                {
                    "type": "page",
                    "uuid": options["uuid"],
                    "page": new.freeze(),
                    "info": {"replace": options["page"]["uuid"]},
                }
            )
            if out2 != EMPTY:
                new2 = Page(
                    filename=out2,
                    dir=options["dir"],
                    delete=True,
                    format="Portable anymap",
                )

                # unpaper doesn't change the resolution, so we can safely copy it

                if "xresolution" in options["page"]:
                    new2["xresolution"] = options["page"]["xresolution"]
                    new2["yresolution"] = options["page"]["yresolution"]

                new2["dirty_time"] = timestamp()  # flag as dirty
                self.return_queue.enqueue(
                    {
                        "type": "page",
                        "uuid": options["uuid"],
                        "page": new2.freeze(),
                        "info": {"insert-after": new["uuid"]},
                    }
                )

        except:
            logger.error(f"Error creating file in {options}{dir}: {_}")
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "unpaper",
                f"Error creating file in {options}{dir}: {_}.",
            )

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "unpaper",
                "uuid": options["uuid"],
            }
        )

    def _thread_user_defined(self, options):

        if _thread_no_filename(self, "user-defined", options["uuid"], options["page"]):
            return

        infile = options["page"]["filename"]
        suffix = None
        regex = re.search(r"([.]\w*)$", infile, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        try:
            out = tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=suffix, delete=False
            )
            options["command"] = re.sub(
                r"%o",
                out,
                options["command"],
                flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if options["command"]:
                options["command"] = re.sub(
                    r"%i",
                    infile,
                    options["command"],
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )

            else:
                if not shutil.copy2(infile, out):
                    _thread_throw_error(
                        self,
                        options["uuid"],
                        options["page"]["uuid"],
                        "user-defined",
                        _("Error copying page"),
                    )
                    return

                options["command"] = re.sub(
                    r"%i",
                    out,
                    options["command"],
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )

            options["command"] = re.sub(
                r"%r",
                fr"{options}{{page}}{xresolution}",
                options["command"],
                flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            (_, info, error) = exec_command([options["command"]], options["pidfile"])
            if _self["cancel"]:
                return
            logger.info(f"stdout: {info}")
            logger.info(f"stderr: {error}")

            # don't return in here, just in case we can ignore the error -
            # e.g. theming errors from gimp

            if error != EMPTY:
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "user-defined",
                    error,
                )

            # Get file type

            image = PythonMagick.Image()
            e = image.Read(out)
            if f"{e}":
                logger.error(e)
                _thread_throw_error(
                    self,
                    options["uuid"],
                    options["page"]["uuid"],
                    "user-defined",
                    f"Error reading {out}: {e}.",
                )
                return

            new = Page(
                filename=out,
                dir=options["dir"],
                delete=True,
                format=image.Get("format"),
            )

            # No way to tell what resolution a pnm is,
            # so assume it hasn't changed

            if re.search(
                r"Portable\s(:?any|bit|gray|pix)map",
                new["format"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                new["xresolution"] = options["page"]["xresolution"]
                new["yresolution"] = options["page"]["yresolution"]

            # Copy the OCR output

            new["bboxtree"] = options["page"]["bboxtree"]

            # reuse uuid so that the process chain can find it again

            new["uuid"] = options["page"]["uuid"]
            self.return_queue.enqueue(
                {
                    "type": "page",
                    "uuid": options["uuid"],
                    "page": new.freeze(),
                    "info": {"replace": options["page"]["uuid"]},
                }
            )

        except:
            logger.error(f"Error creating file in {options}{dir}: {_}")
            _thread_throw_error(
                self,
                options["uuid"],
                options["page"]["uuid"],
                "user-defined",
                f"Error creating file in {options}{dir}: {_}.",
            )

        self.return_queue.enqueue(
            {
                "type": "finished",
                "process": "user-defined",
                "uuid": options["uuid"],
            }
        )

    def _thread_paper_sizes():
        pass


# Build a look-up table of all true-type fonts installed


# If user selects session dir as tmp dir, return parent dir



# define hidden string column for page data


def quit():
    _enqueue_request("quit")
    _self["thread"].join()
    _self["thread"] = None


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
            metadata[key] = info[key]

    if info["datetime"]:
        if info["format"] == "Portable Document Format":
            regex = re.search(
                r"^(.{19})((?:[+-]\d+)|Z)?$",
                info["datetime"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                try:
                    t = datetime.datetime.strptime(regex.group(1), "%Y-%m-%dT%H:%M:%S")
                    tz = regex.group(2)
                    metadata["datetime"] = [
                        t.year,
                        t.month,
                        t.day,
                        t.hour,
                        t.minute,
                        t.second,
                    ]
                    if (tz is None) or tz == "Z":
                        tz = 0

                    metadata["tz"] = [None, None, None, int(tz), 0, None, None]
                except ValueError:
                    pass

        elif info["format"] == "DJVU":
            regex = re.search(
                fr"^{ISODATE_REGEX}\s{TIME_REGEX}{TZ_REGEX}",
                info["datetime"],
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                metadata["datetime"] = [
                    int(
                        regex.group(1),
                        int(
                            regex.group(2),
                            int(
                                regex.group(3),
                                int(
                                    regex.group(4),
                                    int(regex.group(5), int(regex.group(6))),
                                ),
                            ),
                        ),
                    )
                ]
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


def _throw_error(uuid, page_uuid, process, message):

    if (uuid is not None) and "started" in callback[uuid]:
        callback[uuid]["started"](
            None, process, jobs_completed, jobs_total, message, None
        )
        del callback[uuid]["started"]

    if "error" in callback[uuid]:
        message = re.sub(
            r"\s+$", r"", message, count=1, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
        )  # strip trailing whitespace
        callback[uuid]["error"](page_uuid, process, message)
        del callback[uuid]["error"]


def compare_numeric_col():  ## no critic (RequireArgUnpacking, RequireFinalReturn)
    return -1 if _[0] < _[1] else 0 if _[0] == _[1] else 1


def compare_text_col():  ## no critic (RequireArgUnpacking, RequireFinalReturn)
    return -1 if _[0] < _[1] else 0 if _[0] == _[1] else 1


def drag_data_received_callback(
    tree, context, x, y, data, info, time
):  ## no critic (ProhibitManyArgs)

    delete = bool(
        context.get_actions == "move"
    )  ## no critic (ProhibitMismatchedOperators)

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
        for _ in uris:
            _ = re.sub(r"^file://", r"", _, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)

        tree.import_files(paths=uris)
        Gtk.drag_finish(context, True, False, time)

    elif info == ID_PAGE:
        (path, how) = tree.get_dest_row_at_pos(x, y)
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


INPUT_RECORD_SEPARATOR = None


def slurp(file):

    (text) = None
    if type(file) == "GLOB":
        text = file

    else:
        try:
            fh = open("<:encoding(UTF8)", file)

        except:
            raise f"Error: cannot open {file}\n"
        text = fh
        try:
            fh.close()

        except:
            raise f"Error: cannot close {file}\n"

    return text


def unescape_utf8(text):

    if text is not None:

        def anonymous_12(match):
            return chr(oct(match[1])) if (match[1] is not None) else match[2]

        text = re.sub(
            r"\\(?:([0-7]{1,3})|(.))",
            anonymous_12,
            text,
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )

    return decode("UTF-8", text)


def exec_command(cmd, pidfile=None):

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
    except FileNotFoundError as e:
        return -1, None, str(e)

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
        logger.error(f"Unknown stream: '{stream}'")

    regex2 = re.search(regex, output)
    if regex2:
        return regex2.group(1)
    if status == PROCESS_FAILED:
        logger.info(err)
        return PROCESS_FAILED

    logger.info(f"Unable to parse version string from: '{output}'")


def check_command(cmd):

    (_, exe) = exec_command(["which", cmd])
    return (exe is not None) and exe != EMPTY


def timestamp():
    time = localtime

    # return a time which can be string-wise compared

    return "%04d%02d%02d%02d%02d%02d" % (reversed(time[range(YEAR + 1)]))


def text_to_datetime(text, thisyear=None, thismonth=None, thisday=None):

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
            fr"%D{code}",
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
    return [timezone[i] + timezone_offset[i] for i in range(len(timezone))]


def delta_timezone(tz1, tz2):
    return [tz2[i] - tz1[i] for i in range(len(tz1))]


def delta_timezone_to_current(adatetime):
    if adatetime[0] < MIN_YEAR_FOR_DATECALC:
        return [0, 0, 0, 0, 0, 0, 0]

    current = datetime.datetime.now().astimezone().utcoffset()
    current = [
        0,
        0,
        0,
        current.days,
        current.seconds // 3600,
        (current.seconds // 60) % 60,
        current.seconds % 60,
    ]
    adatetime = datetime.datetime(*adatetime).astimezone().utcoffset()
    adatetime = [
        0,
        0,
        0,
        adatetime.days,
        adatetime.seconds // 3600,
        (adatetime.seconds // 60) % 60,
        adatetime.seconds % 60,
    ]
    return delta_timezone(current, adatetime)


def prepare_output_metadata(ftype, metadata):

    h = {}
    if metadata is not None and ftype in ["PDF", "DjVu"]:
        dateformat = (
            "D:%4i%02i%02i%02i%02i%02i%1s%02i'%02i'"
            if ftype == "PDF"
            else "%4i-%02i-%02i %02i:%02i:%02i%1s%02i:%02i"
        )
        print(f"metadata {metadata}")
        year, month, day, hour, mns, sec = metadata["datetime"] if "datetime" in metadata and metadata["datetime"] is not None else 0, 0, 0, 0, 0, 0
        sign, dh, dm = "+", 0, 0
        if "tz" in metadata:
            (_, _, _, dh, dm, _, _) = metadata["tz"]
            if dh * MINUTES_PER_HOUR + dm < 0:
                sign = "-"
            dh = abs(dh)
            dm = abs(dm)

        h["CreationDate"] = dateformat % (
            year,
            month,
            day,
            hour,
            mns,
            sec,
            sign,
            dh,
            dm,
        )
        h["ModDate"] = h["CreationDate"]
        h["Creator"] = f"gscan2pdf v{VERSION}"
        if ftype == "DjVu":
            h["Producer"] = "djvulibre"
        for key in ["author", "title", "subject", "keywords"]:
            if key in metadata and metadata[key] != "":
                h[key.capitalize()] = metadata[key]

    return h


def _enqueue_request(action, data):

    sentinel: shared = 0
    _self["requests"].enqueue({"action": action, "sentinel": sentinel, "data": data})
    jobs_total += 1
    return sentinel


def _add_metadata_to_info(info, string, regex):

    kw_lookup = {
        "Title": "title",
        "Subject": "subject",
        "Keywords": "keywords",
        "Author": "author",
        "CreationDate": "datetime",
    }
    for (key, value) in kw_lookup.items():
        regex = re.search(
            fr"{key}{regex}", string, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            info[value] = regex.group(1)


def font_can_char(font, char):
    "return if the given PDF::Builder font can encode the given character"
    return font.glyphByUni(ord(char)) != ".notdef"


def _need_temp_pdf(options):

    return (
        "prepend" in options["options"]
        or "append" in options["options"]
        or "ps" in options["options"]
        or "user-password" in options["options"]
    )


def _must_convert_image_for_pdf(compression, format, downsample):

    return (
        (compression != "none" and compression != format)
        or downsample
        or compression == "jpg"
    )


def _write_image_object(image, filename, format, pagedata, downsample):

    compression = pagedata.compression
    if (
        not re.search(r"(?:jpg|png)", compression, re.MULTILINE | re.DOTALL | re.VERBOSE)
        and format != "tif"
    ):
        logger.info(f"Writing temporary image {filename}")

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

        image.Set("depth", image.Get("depth"))
        status = image.Write(filename=filename)
        if _self["cancel"]:
            return
        if f"{status}":
            logger.warn(status)
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            format = regex.group(1)

    return format


def px2pt(px, resolution):

    return px / resolution * POINTS_PER_INCH


def _wrap_text_to_page(txt, size, text_box, h, w):

    y = h * POINTS_PER_INCH - size
    for line in re.split(r"\n", txt):
        x = 0

        # Add a word at a time in order to linewrap

        for word in split(SPACE, line):
            if len(word) * size + x > w * POINTS_PER_INCH:
                x = 0
                y -= size

            text_box.translate(x, y)
            if x > 0:
                word = SPACE + word
            x += text_box.text(word, utf8=1)

        y -= size


def _bbox2markup(xresolution, yresolution, h, bbox):

    for i in (0, 2):
        bbox[i] = px2pt(bbox[i], xresolution)
        bbox[i + 1] = h - px2pt(bbox[i + 1], yresolution)

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

    if "post_save_hook" in options:
        command = options["post_save_hook"]
        if isinstance(command, list):
            for i, e in enumerate(command):
                command[i] = re.sub("%i", filename, e, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)
        elif isinstance(command, str):
            command = re.sub("%i", filename, command, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)
        if (
            "post_save_hook_options" not in options
            or options["post_save_hook_options"] != "fg"
        ):
            command += " &"

        logger.info(command)
        subprocess.run(command)


def parse_truetype_fonts(fclist):

    fonts = {"by_file": {}, "by_family": {}}
    for line in re.split(r"\n", fclist):
        if re.search(r"ttf:[ ]", line, re.MULTILINE | re.DOTALL | re.VERBOSE):
            fields = re.split(r":", line)
            if len(fields) > 2:
                ffile, family, style = fields
                style = style.rstrip()
                family = re.sub(
                    r"^[ ]",
                    r"",
                    family,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                family = re.sub(
                    r",.*$",
                    r"",
                    family,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                style = re.sub(
                    r"^style=",
                    r"",
                    style,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                style = re.sub(
                    r",.*$",
                    r"",
                    style,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                fonts["by_file"][ffile] = (family, style)
                if family not in fonts["by_family"]:
                    fonts["by_family"][family] = {}
                fonts["by_family"][family][style] = ffile

    return fonts


def get_tmp_dir(directory, pattern):

    if directory is None:
        return None
    while re.search(pattern, directory, re.MULTILINE | re.DOTALL | re.VERBOSE):
        directory = os.path.dirname(directory)

    return directory

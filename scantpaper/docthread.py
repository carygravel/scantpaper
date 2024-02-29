"Threading model for the Document class"

from collections import defaultdict
import threading
import queue
import pathlib
import logging
import re
import os
import subprocess
import datetime
import glob
import tempfile
import shutil
from PIL import ImageStat, Image, ImageEnhance, ImageOps, ImageFilter
import img2pdf
import ocrmypdf
from basethread import BaseThread
from i18n import _
from helpers import exec_command
from page import Page
from bboxtree import Bboxtree
import tesserocr

img2pdf.default_dpi = 72.0

logger = logging.getLogger(__name__)

VERSION = "1"
PNG = r"Portable[ ]Network[ ]Graphics"
JPG = r"JPEG"
GIF = r"CompuServe[ ]graphics[ ]interchange[ ]format"

image_format = {
    "pnm": "Portable anymap",
    "ppm": "Portable pixmap format (color)",
    "pgm": "Portable graymap format (gray scale)",
    "pbm": "Portable bitmap format (black and white)",
}


class CancelledError(RuntimeError):
    "Raised when a job is cancelled"


class DocThread(BaseThread):
    "subclass basethread for document"

    def __init__(self):
        BaseThread.__init__(self)
        self.lock = threading.Lock()
        self.page_requests = queue.Queue()
        self.pages = queue.Queue()
        self.running_pids = []
        self.message = None
        self.progress = None
        self.cancel = False
        self.paper_sizes = {}

    def input_handler(self, request):
        "handle page requests"
        if not request.args:
            return request.args

        args = list(request.args)

        if "page" in args[0]:
            self.page_requests.put(args[0]["page"])
            page_request = self.pages.get()  # blocking get requested page
            if page_request == "cancel":
                return None
            args[0]["page"] = page_request

        elif "list_of_pages" in args[0]:
            for i, page in enumerate(args[0]["list_of_pages"]):
                self.page_requests.put(page)
                page_request = self.pages.get()  # blocking get requested page
                if page_request == "cancel":
                    return None

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
        proc = exec_command(["file", "-Lb", path])
        proc.stdout = proc.stdout.rstrip()
        logger.info("Format: '%s'", proc.stdout)
        if proc.stdout in ["very short file (no magic)", "empty"]:
            raise RuntimeError(_("Error importing zero-length file %s.") % (path,))

        if re.search(r"gzip[ ]compressed[ ]data", proc.stdout):
            info["path"] = path
            info["format"] = "session file"

        elif re.search(r"DjVu", proc.stdout):
            self._get_djvu_info(info, path)

        elif re.search(r"PDF[ ]document", proc.stdout):
            self._get_pdf_info(info, path, password, request)

        elif re.search(r"^TIFF[ ]image[ ]data", proc.stdout):
            self._get_tif_info(info, path, request)

        else:
            # Get file type
            image = Image.open(path)

            if self.cancel:
                raise CancelledError()
            info["format"] = image.format

            logger.info("Format %s", info["format"])
            info["width"] = [image.width]
            info["height"] = [image.height]
            dpi = image.info.get("dpi")
            if dpi is None:
                info["xresolution"], info["yresolution"] = (
                    img2pdf.default_dpi,
                    img2pdf.default_dpi,
                )
            info["pages"] = 1

        info["path"] = path
        return info

    def _get_djvu_info(self, info, path):
        "get DjVu info"
        # Dig out the number of pages
        proc = exec_command(["djvudump", path])
        if re.search(
            r"command[ ]not[ ]found", proc.stderr, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            raise RuntimeError(
                _("Please install djvulibre-bin in order to open DjVu files.")
            )

        logger.info(proc.stdout)
        if self.cancel:
            raise CancelledError()
        pages = 1
        regex = re.search(
            r"\s(\d+)\s+page", proc.stdout, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            pages = int(regex.group(1))

        # Dig out the size and resolution of each page
        width, height, ppi = [], [], []
        info["format"] = "DJVU"
        regex = re.findall(
            r"DjVu\s(\d+)x(\d+).+?\s+(\d+)\s+dpi",
            proc.stdout,
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
        proc = exec_command(["djvused", path, "-e", "print-meta"])
        logger.info(proc.stdout)
        if self.cancel:
            raise CancelledError()

        # extract the metadata from the file
        _add_metadata_to_info(info, proc.stdout, r'\s+"([^"]+)')

    def _get_pdf_info(self, info, path, password, request):
        "get PDF info"
        info["format"] = "Portable Document Format"
        args = ["pdfinfo", "-isodates", path]
        if password is not None:
            args.insert(2, "-upw")
            args.insert(3, password)

        try:
            process = subprocess.run(args, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as err:
            logger.info("stdout: %s", err.stdout)
            logger.info("stderr: %s", err.stderr)
            if (err.stderr is not None) and re.search(
                r"Incorrect[ ]password",
                err.stderr,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                info["encrypted"] = True
                return
            request.error(err.stderr)
            return

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

        if self.cancel:
            raise CancelledError()

        # extract the metadata from the file
        _add_metadata_to_info(info, process.stdout, r":\s+([^\n]+)")

    def _get_tif_info(self, info, path, request):
        "get TIFF info"
        info["format"] = "Tagged Image File Format"
        proc = exec_command(["tiffinfo", path])
        if self.cancel:
            raise CancelledError()
        logger.info(info)

        # Count number of pages
        info["pages"] = len(
            re.findall(
                r"TIFF[ ]Directory[ ]at[ ]offset",
                proc.stdout,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
        )
        logger.info("%s pages", info["pages"])

        # Dig out the size of each page
        width, height = [], []
        regex = re.findall(
            r"Image\sWidth:\s(\d+)\sImage\sLength:\s(\d+)",
            proc.stdout,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        for _w, _h in regex:
            width.append(int(_w))
            height.append(int(_h))
            request.data(f"Page {len(width)} is {width[-1]}x{height[-1]}")

        info["width"] = width
        info["height"] = height

    def do_import_file(self, request):
        "import file in thread"
        args = request.args[0]
        if args["info"]["format"] == "DJVU":
            self._do_import_djvu(request)

        elif args["info"]["format"] == "Portable Document Format":
            self._do_import_pdf(request)

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
                    tif = None
                    with tempfile.NamedTemporaryFile(
                        dir=args["dir"], suffix=".tif", delete=False
                    ) as tif:
                        subprocess.run(
                            ["tiffcp", f"{args['info']['path']},{i}", tif.name],
                            check=True,
                        )
                        if self.cancel:
                            raise CancelledError()
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
            except (PermissionError, IOError) as err:
                logger.error("Caught error writing to %s: %s", args["dir"], err)
                request.error(f"Error: unable to write to {args['dir']}.")

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
        options = defaultdict(None, request.args[0])

        self.message = _("Setting up PDF")
        outdir = pathlib.Path(options["dir"])
        filename = options["path"]
        if _need_temp_pdf(options["options"]):
            with tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=".pdf", delete=False
            ) as temp:
                filename = temp.name

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
        for pagenr, pagedata in enumerate(options["list_of_pages"]):
            if pagedata.text_layer:
                with open(
                    outdir / f"{pagenr:-06}__ocr_hocr.hocr", "w", encoding="utf-8"
                ) as fhd:
                    fhd.write(pagedata.export_hocr())
            self.progress = pagenr / (len(options["list_of_pages"]) + 1)
            self.message = _("Saving page %i of %i") % (
                pagenr,
                len(options["list_of_pages"]),
            )
            if self.cancel:
                raise CancelledError()

        ocrmypdf.api._hocr_to_ocr_pdf(outdir, filename, optimize=0)

        _append_pdf(filename, options, request)

        if options["options"] and options["options"].get("user-password"):
            if _encrypt_pdf(filename, options, request):
                return

        _set_timestamp(options)
        if options["options"] and options["options"].get("ps"):
            self.message = _("Converting to PS")
            proc = exec_command(
                [options["options"]["pstool"], filename, options["options"]["ps"]],
                options["pidfile"],
            )
            if proc.returncode or proc.stderr:
                logger.info(proc.stderr)
                request.error(_("Error converting PDF to PS: %s") % (proc.stderr))
                return

            _post_save_hook(options["options"]["ps"], options["options"])

        else:
            _post_save_hook(filename, options["options"])

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
            with tempfile.NamedTemporaryFile(
                dir=args["dir"], suffix=".djvu", delete=False
            ) as djvu:

                # logger.error("Caught error writing DjVu: %s", err)
                # self._thread_throw_error(
                #     args["uuid"],
                #     args["page"]["uuid"],
                #     "Save file",
                #     f"Caught error writing DjVu: {_}.",
                # )
                # error = True

                # if error:
                #     return
                compression, filename, resolution = _convert_image_for_djvu(
                    pagedata, args, request
                )

                # Create the djvu
                proc = exec_command(
                    [compression, "-dpi", str(int(resolution)), filename, djvu.name],
                    args["pidfile"],
                )
                size = os.path.getsize(djvu.name)
                if self.cancel:
                    raise CancelledError()
                if proc.returncode != 0 or size == 0:
                    logger.error(
                        "Error writing image for page %s of DjVu (process "
                        "returned %s, image size %s)",
                        page,
                        proc.returncode,
                        size,
                    )
                    request.error(_("Error writing DjVu"))
                    return

                filelist.append(djvu.name)
                _add_txt_to_djvu(djvu, args["dir"], pagedata, request)
                _add_ann_to_djvu(djvu, args["dir"], pagedata, request)

        self.progress = 1
        self.message = _("Merging DjVu")
        proc = exec_command(["djvm", "-c", args["path"], *filelist], args["pidfile"])
        if self.cancel:
            raise CancelledError()
        if proc.returncode:
            logger.error("Error merging DjVu")
            request.error(_("Error merging DjVu"))

        self._add_metadata_to_djvu(args)
        _set_timestamp(args)
        _post_save_hook(args["path"], args["options"])

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
                for key, val in metadata.items():

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
                raise CancelledError()
            # if status:
            #     logger.error("Error adding metadata info to DjVu file")
            #     self._thread_throw_error(
            #         options["uuid"],
            #         options["page"]["uuid"],
            #         "Save file",
            #         _("Error adding metadata to DjVu"),
            #     )

    def _do_import_djvu(self, request):
        args = request.args[0]
        # Extract images from DjVu
        if args["last"] >= args["first"] and args["first"] > 0:
            for i in range(args["first"], args["last"] + 1):
                self.progress = (i - 1) / (args["last"] - args["first"] + 1)
                self.message = _("Importing page %i of %i") % (
                    i,
                    args["last"] - args["first"] + 1,
                )
                with tempfile.NamedTemporaryFile(
                    dir=args["dir"], suffix=".tif", delete=False
                ) as tif:
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
                    if self.cancel:
                        raise CancelledError()
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
                    except (PermissionError, IOError, ValueError) as err:
                        request.data(
                            None, f"Caught error parsing DjVU text layer: {err}"
                        )

                    try:
                        page.import_djvu_ann(ann)

                    except (PermissionError, IOError) as err:
                        logger.error(
                            "Caught error parsing DjVU annotation layer: %s", err
                        )
                        request.error("Error: parsing DjVU annotation layer")

                    request.data(page)

    def _do_import_pdf(self, request):
        args = request.args[0]

        # Extract images from PDF
        warning_flag, xresolution, yresolution = False, None, None
        for i in range(args["first"], args["last"] + 1):
            out = subprocess.check_output(
                _pdf_cmd_with_password(
                    [
                        "pdfimages",
                        "-f",
                        str(i),
                        "-l",
                        str(i),
                        "-list",
                        args["info"]["path"],
                    ],
                    args["password"],
                ),
                text=True,
            )
            for line in re.split(r"\n", out):
                xresolution, yresolution = line[70:75], line[76:81]
                if re.search(r"\d", xresolution, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    xresolution, yresolution = float(xresolution), float(yresolution)
                    break

            try:
                subprocess.run(
                    _pdf_cmd_with_password(
                        [
                            "pdfimages",
                            "-f",
                            str(i),
                            "-l",
                            str(i),
                            args["info"]["path"],
                            "x",
                        ],
                        args["password"],
                    ),
                    check=True,
                )
            except subprocess.CalledProcessError:
                request.error(_("Error extracting images from PDF"))
            if self.cancel:
                raise CancelledError()

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
                    page.import_pdftotext(self._extract_text_from_pdf(request, i))
                    request.data(page.to_png(self.paper_sizes))
                except (PermissionError, IOError) as err:
                    logger.error("Caught error importing PDF: %s", err)
                    request.error(_("Error importing PDF"))

        if warning_flag:
            request.data(
                None,
                _(
                    "Warning: gscan2pdf expects one image per page, but "
                    "this was not satisfied. It is probable that the PDF "
                    "has not been correctly imported. If you wish to add "
                    "scans to an existing PDF, use the prepend/append to "
                    "PDF options in the Save dialogue."
                ),
            )

    def _extract_text_from_pdf(self, request, i):
        args = request.args[0]
        with tempfile.NamedTemporaryFile(
            mode="w+t", dir=args["dir"], suffix=".html"
        ) as html:
            spo = subprocess.run(
                _pdf_cmd_with_password(
                    [
                        "pdftotext",
                        "-bbox",
                        "-f",
                        str(i),
                        "-l",
                        str(i),
                        args["info"]["path"],
                        html.name,
                    ],
                    args["password"],
                ),
                check=True,
                capture_output=True,
                text=True,
            )
            if self.cancel:
                raise CancelledError()
            if spo.returncode != 0:
                request.error(_("Error extracting text layer from PDF"))
            return html.read()

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
                with tempfile.NamedTemporaryFile(
                    dir=options["dir"], suffix=".tif", delete=False
                ) as tif:
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
                        units,
                        "-density",
                        f"{xresolution}x{yresolution}",
                        *depth,
                        tif.name,
                    ]
                    subprocess.run(cmd, check=True)
                    if self.cancel:
                        raise CancelledError()
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
            raise CancelledError()
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
            proc = exec_command(cmd, options["pidfile"])
            if proc.returncode or proc.stderr:
                logger.info(proc.stderr)
                request.error(_("Error converting TIFF to PS: %s") % (proc.stderr))
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
            proc = exec_command(
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
            if self.cancel:
                raise CancelledError()
            if proc.returncode:
                request.error(_("Error saving image"))

            _post_save_hook(options["list_of_pages"][0].filename, options["options"])

        else:
            current_filename = None
            i = 1
            for page in options["list_of_pages"]:
                current_filename = options["path"] % (i)
                i += 1
                proc = exec_command(
                    [
                        "convert",
                        page.filename,
                        "-density",
                        page.xresolution + "x" + page.yresolution,
                        current_filename,
                    ],
                    options["pidfile"],
                )
                if self.cancel:
                    raise CancelledError()
                if proc.returncode:
                    request.error(_("Error saving image"))

                _post_save_hook(page.filename, options["options"])

    def save_text(self, **kwargs):
        "save text file"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_text", kwargs, **callbacks)

    def do_save_text(self, request):
        "save text file in thread"
        options = request.args[0]

        string = ""
        for page in options["list_of_pages"]:
            string += page.export_text()
            if self.cancel:
                raise CancelledError()

        with open(options["path"], "w", encoding="utf-8") as fhd:
            fhd.write(string)

        _post_save_hook(options["path"], options["options"])

    def save_hocr(self, **kwargs):
        "save hocr file"
        callbacks = _note_callbacks2(kwargs)
        return self.send("save_hocr", kwargs, **callbacks)

    def do_save_hocr(self, request):
        "save hocr file in thread"
        options = request.args[0]

        with open(options["path"], "w", encoding="utf-8") as fhd:
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
                        raise CancelledError()

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

        if _page_gone("rotate", options["uuid"], page, request):
            return None
        filename = page.filename
        logger.info("Rotating %s by %s degrees", filename, angle)
        image = page.im_object().rotate(angle, expand=True)

        if self.cancel:
            raise CancelledError()
        regex = re.search(r"([.]\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        fnm = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            dir=options["dir"], suffix=suffix, delete=False
        )
        image.save(fnm.name)

        if self.cancel:
            raise CancelledError()
        page.filename = fnm.name
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        if angle in (90, 270):
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

    def set_paper_sizes(self, paper_sizes):
        "set paper sizes"
        self.paper_sizes = paper_sizes
        return self.send("paper_sizes", paper_sizes)

    def do_set_paper_sizes(self, request):
        "set paper sizes in thread"
        paper_sizes = request.args[0]
        self.paper_sizes = paper_sizes

    def to_png(self, **kwargs):
        "convert to PNG"
        callbacks = _note_callbacks2(kwargs)
        return self.send("to_png", kwargs, **callbacks)

    def do_to_png(self, request):
        "convert to PNG in thread"
        page = request.args[0]
        return page.to_png(self.paper_sizes)

    def user_defined(self, **kwargs):
        "run user defined command on page"
        callbacks = _note_callbacks2(kwargs)
        return self.send("user_defined", kwargs, **callbacks)

    def do_user_defined(self, request):
        "run user defined command on page in thread"
        options = request.args[0]

        if _page_gone("user-defined", options["uuid"], options["page"], request):
            return

        infile = options["page"].filename
        suffix = None
        regex = re.search(r"([.]\w*)$", infile, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)

        try:
            with tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=suffix, delete=False
            ) as out:
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
                        request.error(_("Error copying page"))
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
                    raise CancelledError()
                logger.info("stdout: %s", sbp.stdout)
                logger.info("stderr: %s", sbp.stderr)

                # don't return in here, just in case we can ignore the error -
                # e.g. theming errors from gimp
                if sbp.stderr != "":
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

        except (PermissionError, IOError) as err:
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
                raise CancelledError()
            stat = ImageStat.Stat(image)
            mean, stddev = stat.mean, stat.stddev
            logger.info("std dev: %s mean: %s", stddev, mean)
            if self.cancel:
                raise CancelledError()

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

        if _page_gone("threshold", options["uuid"], page, request):
            return None
        if self.cancel:
            raise CancelledError()
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
            raise CancelledError()

        fnm = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            dir=options["dir"], suffix=".png", delete=False
        )
        image.save(fnm.name)

        if self.cancel:
            raise CancelledError()
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

        if _page_gone("brightness-contrast", options["uuid"], options["page"], request):
            return None

        filename = page.filename
        logger.info(
            "Enhance %s with brightness %s, contrast %s", filename, brightness, contrast
        )
        image = page.im_object()
        if self.cancel:
            raise CancelledError()

        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)

        if self.cancel:
            raise CancelledError()

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

        if _page_gone("negate", options["uuid"], page, request):
            return None

        filename = page.filename
        logger.info("Invert %s", filename)
        image = page.im_object()
        image = ImageOps.invert(image)

        if self.cancel:
            raise CancelledError()

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

        if _page_gone("unsharp", options["uuid"], page, request):
            return None

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
            raise CancelledError()

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

        if _page_gone("crop", options["uuid"], options["page"], request):
            return None

        filename = page.filename
        logger.info("Crop %s x %s y %s w %s h %s", filename, left, top, width, height)
        image = page.im_object()

        image = image.crop((left, top, left + width, top + height))

        if self.cancel:
            raise CancelledError()

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

        if _page_gone("split", options["uuid"], options["page"], request):
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
            raise CancelledError()

        # Write them
        suffix = None
        regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if regex:
            suffix = regex.group(1)
            with tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            ) as filename, tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=f".{suffix}", delete=False
            ) as filename2:
                image.save(filename)
                image2.save(filename2)

            logger.info(
                "Splitting in direction %s @ %s -> %s + %s",
                options["direction"],
                options["position"],
                filename,
                filename2,
            )
            if self.cancel:
                raise CancelledError()
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

        if _page_gone("tesseract", options["uuid"], options["page"], request):
            return None

        if self.cancel:
            raise CancelledError()

        paths = glob.glob("/usr/share/tesseract-ocr/*/tessdata")
        if not paths:
            request.error(_("tessdata directory not found"))
        with tesserocr.PyTessBaseAPI(lang=language, path=paths[-1]) as api:
            output = "image_out"

            api.SetVariable("tessedit_create_hocr", "T")
            _pp = api.ProcessPages(output, page.filename)

            # Unnecessary filesystem write/read
            path_hocr = pathlib.Path(output).with_suffix(".hocr")
            hocr = path_hocr.read_text(encoding="utf-8")
            path_hocr.unlink()

            page.import_hocr(hocr)
            page.ocr_flag = True
            page.ocr_time = datetime.datetime.now()

        if self.cancel:
            raise CancelledError()

        return page

    def unpaper(self, **kwargs):
        "run unpaper"
        callbacks = _note_callbacks2(kwargs)
        return self.send("unpaper", kwargs, **callbacks)

    def _run_unpaper_cmd(self, request):
        options = request.args[0]
        with tempfile.NamedTemporaryFile(
            dir=options["dir"], suffix=".pnm", delete=False
        ) as out, tempfile.NamedTemporaryFile(
            dir=options["dir"], suffix=".pnm", delete=False
        ) as out2:
            options["options"]["command"][-2] = out.name

            index = options["options"]["command"].index("--output-pages")
            if options["options"]["command"][index + 1] == "2":
                options["options"]["command"][-1] = out2.name
            else:
                del options["options"]["command"][-1]
                out2 = None

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
                if not os.path.getsize(out.name):
                    raise subprocess.CalledProcessError

            if self.cancel:
                raise CancelledError()
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
                if not os.path.getsize(out.name):
                    raise subprocess.CalledProcessError

            if (
                options["options"]["command"][index + 1] == "2"
                and options["options"].get("direction") == "rtl"
            ):
                out, out2 = out2, out
            return out, out2

    def do_unpaper(self, request):
        "run unpaper in thread"
        options = request.args[0]

        if _page_gone("unpaper", options["uuid"], options["page"], request):
            return

        try:
            if re.search(
                r"[.]pnm$",
                options["page"].filename,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                infile = options["page"].filename
            else:
                image = options["page"].im_object()
                depth = options["page"].get_depth()

                suffix = ".pbm"
                if depth > 1:
                    suffix = ".pnm"

                # Temporary filename for new file
                with tempfile.NamedTemporaryFile(
                    dir=options["dir"], suffix=suffix, delete=False
                ) as temp:
                    infile = temp.name
                    logger.debug(
                        "Converting %s -> %s for unpaper",
                        options["page"].filename,
                        infile,
                    )
                    image.save(infile)

            options["options"]["command"][-3] = infile

            out, out2 = self._run_unpaper_cmd(request)

            # unpaper doesn't change the resolution, so we can safely copy it
            new = Page(
                filename=out.name,
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
                    filename=out2.name,
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

        except (PermissionError, IOError) as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            request.error(f"Error creating file in {options['dir']}: {err}.")


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


def prepare_output_metadata(ftype, metadata):
    "format metadata for PDF or DjVu"
    out = {}
    if metadata and ftype in ["PDF", "DjVu"]:
        if ftype == "PDF":
            out["creationdate"] = metadata["datetime"]
        else:
            out["creationdate"] = metadata["datetime"].isoformat()
        out["moddate"] = out["creationdate"]
        out["creator"] = f"gscan2pdf v{VERSION}"
        if ftype == "DjVu":
            out["producer"] = "djvulibre"
        for key in ["author", "title", "subject", "keywords"]:
            if key in metadata and metadata[key] != "":
                out[key] = metadata[key]

    return out


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
        with tempfile.NamedTemporaryFile(
            dir=options["dir"], suffix=regex.group(1), delete=False
        ) as tmp:
            filename = tmp.name
            image.save(filename)
    return filename


def _append_pdf(filename, options, request):
    if options is None or "options" not in options or options["options"] is None:
        return None
    if "prepend" in options["options"]:
        file1 = filename
        file2 = options["options"]["prepend"] + ".bak"
        bak = file2
        out = options["options"]["prepend"]
        message = _("Error prepending PDF: %s")
        logger.info("Prepending PDF")

    elif "append" in options["options"]:
        file2 = filename
        file1 = options["options"]["append"] + ".bak"
        bak = file1
        out = options["options"]["append"]
        message = _("Error appending PDF: %s")
        logger.info("Appending PDF")

    else:
        return None

    try:
        os.rename(out, bak)
    except ValueError:
        request.error(_("Error creating backup of PDF"))
        return None

    proc = exec_command(["pdfunite", file1, file2, out], options["pidfile"])
    if proc.returncode:
        logger.info(proc.stderr)
        request.error(message % (proc.stderr))
    return proc.returncode


def _set_timestamp(options):
    if (
        not options["options"]
        or options["options"].get("set_timestamp") is None
        or options["options"].get("ps")
    ):
        return

    metadata = options["metadata"]
    adatetime = metadata["datetime"]
    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    adatetime = (adatetime - epoch).total_seconds()
    if adatetime < 0:
        raise ValueError("Unable to set file timestamp for dates prior to 1970")
    os.utime(options["path"], (adatetime, adatetime))


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


def _pdf_cmd_with_password(cmd, password):
    if password is not None:
        cmd.insert(1, "-upw")
        cmd.insert(2, password)
    return cmd


def _convert_image_for_djvu(pagedata, options, request):
    filename = pagedata.filename

    # Check the image depth to decide what sort of compression to use
    compression = None

    # c44 and cjb2 do not support different resolutions in the x and y
    # directions, so resample
    resolution, image = pagedata.equalize_resolution()
    if image:
        upsample = True
    else:
        upsample = False
        image = Image.open(filename)

    # c44 can only use pnm and jpg
    fformat = None
    regex = re.search(r"[.](\w*)$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE)
    if regex:
        fformat = regex.group(1)

    mode = image.mode
    if mode != "1":
        compression = "c44"
        if (
            not re.search(
                r"(?:pnm|jpg)", fformat, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            or upsample
        ):
            with tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=".pnm", delete=False
            ) as pnm:
                image.save(pnm.name)
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
            with tempfile.TemporaryFile(dir=options["dir"], suffix=".pbm") as pbm:
                err = image.save(pbm.name)
                if f"{err}":
                    logger.error(err)
                    request.error(f"Error writing {pbm}: {err}.")
                    return None

                filename = pbm.name

    return compression, filename, resolution


def _add_txt_to_djvu(djvu, dirname, pagedata, request):
    if pagedata.text_layer is not None:
        txt = pagedata.export_djvu_txt()
        if txt == "":
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
            request.error(_("Error adding text layer to DjVu"))


def _add_ann_to_djvu(djvu, dirname, pagedata, request):
    """FIXME - refactor this together with _add_txt_to_djvu"""
    if pagedata.annotations is not None:
        ann = pagedata.export_djvu_ann()
        if ann == "":
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
            request.error(_("Error adding annotations to DjVu"))


def _page_gone(process, uid, page, request):
    if not os.path.isfile(
        page.filename
    ):  # in case file was deleted after process started
        err = f"Page for process {uid} no longer exists. Cannot {process}."
        logger.error(err)
        request.error(err)
        return True
    return False


def _encrypt_pdf(filename, options, request):
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
        request.error(_("Error encrypting PDF: %s") % (spo.stderr))
    return spo.returncode

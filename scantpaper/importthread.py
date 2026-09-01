"Threading model for the Document class"

import logging
import pathlib
import re
import subprocess
import tempfile
import threading

from basethread import BaseThread
from helpers import exec_command, exec_command_run
from i18n import _
from page import Page
from PIL import Image

logger = logging.getLogger(__name__)

image_format = {
    "pnm": "Portable anymap",
    "ppm": "Portable pixmap format (color)",
    "pgm": "Portable graymap format (gray scale)",
    "pbm": "Portable bitmap format (black and white)",
}


class CancelledError(RuntimeError):
    "Raised when a job is cancelled"


class Importhread(BaseThread):
    "subclass basethread for document"

    def __init__(self):
        BaseThread.__init__(self)
        self.lock = threading.Lock()
        self.running_pids = {}
        self.message = None
        self.progress = None
        self.cancel = False
        self.paper_sizes = {}

    def _request_pidfile(self, request):
        "locate the pidfile attached to a request for this thread"
        pidfile = getattr(request, "pidfile", None)
        if pidfile is not None:
            return pidfile
        for args in request.args:
            if isinstance(args, dict) and "pidfile" in args:
                return args["pidfile"]
        return None

    def _request_completed(self, request):
        "deregister the request's pidfile now that its handler has finished"
        pidfile = self._request_pidfile(request)
        if pidfile is not None:
            with self.lock:
                self.running_pids.pop(pidfile, None)

    def do_cancel(self, _request):
        "cancel running tasks"
        self.cancel = False

    def check_cancelled(self):
        "check if operation was cancelled"
        if self.cancel:
            raise CancelledError

    def do_get_file_info(self, request):
        "get file info"
        path, password = request.args
        pidfile = getattr(request, "pidfile", None)
        info = {}
        if not pathlib.Path(path).exists():
            raise FileNotFoundError(_("File %s not found") % (path,))

        logger.info("Getting info for %s", path)
        proc = exec_command(["file", "-Lb", path], pidfile)
        if proc.stdout is None:
            raise RuntimeError(
                _("Error getting file info for %s: %s") % (path, proc.stderr)
            )
        proc.stdout = proc.stdout.rstrip()
        logger.info("Format: '%s'", proc.stdout)
        if proc.stdout in ["very short file (no magic)", "empty"]:
            raise RuntimeError(_("Error importing zero-length file %s.") % (path,))

        if re.search(r"SQLite[ ]3.x[ ]database", proc.stdout):
            info["path"] = path
            info["format"] = "session file"

        elif re.search(r"DjVu", proc.stdout):
            self._get_djvu_info(info, path, pidfile)

        elif re.search(r"PDF[ ]document", proc.stdout):
            self._get_pdf_info(info, path, password, request, pidfile)

        elif re.search(r"^TIFF[ ]image[ ]data", proc.stdout):
            self._get_tif_info(info, path, request, pidfile)

        else:
            # Get file type
            image = Image.open(path)

            self.check_cancelled()
            info["format"] = image.format

            logger.info("Format %s", info["format"])
            info["width"] = [image.width]
            info["height"] = [image.height]
            info["pages"] = 1

        info["path"] = path
        return info

    def _get_djvu_info(self, info, path, pidfile=None):
        "get DjVu info"
        # Dig out the number of pages
        proc = exec_command(["djvudump", path], pidfile)
        if proc.stdout is None:
            raise RuntimeError(
                _("Please install djvulibre-bin in order to open DjVu files: %s")
                % (proc.stderr,)
            )

        logger.info(proc.stdout)
        self.check_cancelled()
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
        proc = exec_command(["djvused", path, "-e", "print-meta"], pidfile)
        if proc.stdout is None:
            raise RuntimeError(
                _("Please install djvulibre-bin in order to open DjVu files: %s")
                % (proc.stderr,)
            )

        logger.info(proc.stdout)
        self.check_cancelled()

        # extract the metadata from the file
        _add_metadata_to_info(info, proc.stdout, r'\s+"([^"]+)')

    def _get_pdf_info(self, info, path, password, request, pidfile=None):
        "get PDF info"
        info["format"] = "Portable Document Format"
        args = ["pdfinfo", "-isodates", path]
        if password is not None:
            args.insert(2, "-upw")
            args.insert(3, password)

        try:
            process = exec_command_run(
                args, pidfile, capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as err:
            logger.info("stdout: %s", err.stdout)
            logger.info("stderr: %s", err.stderr)
            if err.stderr is not None and re.search(
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

        self.check_cancelled()

        # extract the metadata from the file
        _add_metadata_to_info(info, process.stdout, r":\s+([^\n]+)")

    def _get_tif_info(self, info, path, request, pidfile=None):
        "get TIFF info"
        info["format"] = "Tagged Image File Format"
        proc = exec_command(["tiffinfo", path], pidfile)
        if proc.stdout is None:
            raise RuntimeError(
                _("Please install libtiff-tools in order to open TIFF files: %s")
                % (proc.stderr,)
            )

        self.check_cancelled()
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
                page = Page(
                    filename=args["info"]["path"],
                    dir=args["dir"],
                    format=args["info"]["format"],
                    width=args["info"]["width"][0],
                    height=args["info"]["height"][0],
                )
                request.data(
                    {
                        "type": "page",
                        "row": self.add_page(page),
                    }
                )

            # Split the tiff into its pages and import them individually
            elif args["last"] >= args["first"] and args["first"] > 0:
                for i in range(args["first"] - 1, args["last"] - 1 + 1):
                    self.progress = i / (args["last"] - args["first"] + 1)
                    self.message = _("Importing page %i of %i") % (
                        i,
                        args["last"] - args["first"] + 1,
                    )
                    with tempfile.NamedTemporaryFile(
                        dir=args["dir"], suffix=".tif"
                    ) as tif:
                        exec_command_run(
                            ["tiffcp", f"{args['info']['path']},{i}", tif.name],
                            args.get("pidfile"),
                            check=True,
                        )
                        self.check_cancelled()
                        page = Page(
                            filename=tif.name,
                            dir=args["dir"],
                            format=args["info"]["format"],
                            width=args["info"]["width"][i - 1],
                            height=args["info"]["height"][i - 1],
                        )
                        request.data(
                            {
                                "type": "page",
                                "row": self.add_page(page),
                            }
                        )

        else:
            page = Page(
                filename=args["info"]["path"],
                dir=args["dir"],
                format=args["info"]["format"],
                width=args["info"]["width"][0],
                height=args["info"]["height"][0],
            )
            page.get_resolution(self.paper_sizes)
            request.data(
                {
                    "type": "page",
                    "row": self.add_page(page),
                }
            )

    def get_file_info(self, path, password, **kwargs):
        "get file info"
        return self.send("get_file_info", path, password, **kwargs)

    def import_file(self, **kwargs):
        "import file"
        callbacks = _note_callbacks(kwargs)
        return self.send("import_file", kwargs, **callbacks)

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
                with tempfile.NamedTemporaryFile(dir=args["dir"], suffix=".tif") as tif:
                    exec_command_run(
                        [
                            "ddjvu",
                            "-format=tiff",
                            f"-page={i}",
                            args["info"]["path"],
                            tif.name,
                        ],
                        args.get("pidfile"),
                        check=True,
                    )
                    txt = exec_command_run(
                        [
                            "djvused",
                            args["info"]["path"],
                            "-e",
                            f"select {i}; print-txt",
                        ],
                        args.get("pidfile"),
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout
                    ann = exec_command_run(
                        [
                            "djvused",
                            args["info"]["path"],
                            "-e",
                            f"select {i}; print-ant",
                        ],
                        args.get("pidfile"),
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout
                    self.check_cancelled()
                    page = Page(
                        filename=tif.name,
                        dir=args["dir"],
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
                    except (OSError, PermissionError, ValueError) as err:
                        request.data(
                            None, f"Caught error parsing DjVU text layer: {err}"
                        )

                    try:
                        page.import_djvu_ann(ann)
                    except (OSError, PermissionError):
                        logger.exception("Caught error parsing DjVU annotation layer")
                        request.error("Error: parsing DjVU annotation layer")

                    request.data(
                        {
                            "type": "page",
                            "row": self.add_page(page),
                        }
                    )

    def _do_import_pdf(self, request):
        args = request.args[0]

        # Extract images from PDF
        warning_flag = False
        for i in range(args["first"], args["last"] + 1):
            # Remove any extraction files left over from a previous page
            for fname in pathlib.Path().glob("x-*"):
                pathlib.Path(fname).unlink()

            out = exec_command_run(
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
                args.get("pidfile"),
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            entries = _parse_pdfimages_list(out)

            try:
                exec_command_run(
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
                    args.get("pidfile"),
                    check=True,
                )
            except subprocess.CalledProcessError:
                request.error(_("Error extracting images from PDF"))
                return
            self.check_cancelled()

            images_and_resolution, warning = _correlate_pdf_images(entries)
            warning_flag = warning_flag or warning
            self._import_pdf_images(request, i, images_and_resolution)

        if warning_flag:
            request.error(
                None,
                _(
                    "Warning: scantpaper expects one image per page, but "
                    "this was not satisfied. It is probable that the PDF "
                    "has not been correctly imported. If you wish to add "
                    "scans to an existing PDF, use the prepend/append to "
                    "PDF options in the Save dialogue."
                ),
            )

    def _import_pdf_images(self, request, i, images_and_resolution):
        "import the images extracted from a PDF page"
        for fname, xresolution, yresolution, mask_fname in images_and_resolution:
            if mask_fname is not None:
                _composite_over_white(fname, mask_fname)
                pathlib.Path(mask_fname).unlink()
            regex = re.search(r"([^.]+)$", fname, re.MULTILINE | re.DOTALL | re.VERBOSE)
            if regex:
                ext = regex.group(1)
                try:
                    page = Page(
                        filename=fname,
                        dir=request.args[0]["dir"],
                        format=image_format[ext],
                        resolution=(xresolution, yresolution, "PixelsPerInch"),
                    )
                    page.import_pdftotext(self._extract_text_from_pdf(request, i))
                    request.data(
                        {
                            "type": "page",
                            "row": self.add_page(page),
                        }
                    )
                    pathlib.Path(fname).unlink()
                except (OSError, PermissionError):
                    logger.exception("Caught error importing PDF")
                    request.error(_("Error importing PDF"))

    def _extract_text_from_pdf(self, request, i):
        args = request.args[0]
        with tempfile.NamedTemporaryFile(
            mode="w+t", dir=args["dir"], suffix=".html"
        ) as html:
            spo = exec_command_run(
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
                args.get("pidfile"),
                capture_output=True,
                text=True,
            )
            self.check_cancelled()
            if spo.returncode != 0:
                request.error(_("Error extracting text layer from PDF"))
            return html.read()


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


def _pdf_cmd_with_password(cmd, password):
    if password is not None:
        cmd.insert(1, "-upw")
        cmd.insert(2, password)
    return cmd


def _parse_pdfimages_list(out):
    "parse pdfimages -list output into a list of image entries"
    entries = []
    for line in out.splitlines():
        tokens = line.split()
        if len(tokens) < 14:
            continue
        try:
            page = int(tokens[0])
            num = int(tokens[1])
        except ValueError:
            continue
        entries.append(
            {
                "page": page,
                "num": num,
                "type": tokens[2],
                "x_ppi": float(tokens[-4]),
                "y_ppi": float(tokens[-3]),
            }
        )
    return entries


def _composite_over_white(image_path, mask_path):
    "composite the image over a white background using its soft mask, in place"
    try:
        image = Image.open(image_path)
        mask = Image.open(mask_path)
        if image.size != mask.size:
            return False
        background = Image.new("RGB", image.size, "white")
        result = Image.composite(image.convert("RGB"), background, mask.convert("L"))
        if image.mode not in ("RGB", "RGBA"):
            result = result.convert("L")
        result.save(image_path)
    except (OSError, ValueError):
        return False
    return True


def _correlate_pdf_images(entries):
    "correlate extracted files with pdfimages -list entries by index"
    images = sorted(str(x) for x in pathlib.Path().glob("x-??*.???"))
    if len(images) != len(entries):
        # Unexpected structure: import every file and warn
        xresolution, yresolution = None, None
        if entries:
            xresolution = entries[0]["x_ppi"]
            yresolution = entries[0]["y_ppi"]
        return [(fname, xresolution, yresolution, None) for fname in images], True
    images_and_resolution = []
    paired_masks = set()
    for i, (fname, entry) in enumerate(zip(images, entries, strict=False)):
        if entry["type"] == "image":
            mask_fname = None
            if i + 1 < len(entries) and entries[i + 1]["type"] == "smask":
                mask_fname = images[i + 1]
                paired_masks.add(images[i + 1])
            images_and_resolution.append(
                (fname, entry["x_ppi"], entry["y_ppi"], mask_fname)
            )
    for fname, entry in zip(images, entries, strict=False):
        if entry["type"] != "image" and fname not in paired_masks:
            pathlib.Path(fname).unlink()
    return images_and_resolution, len(images_and_resolution) != 1


def _note_callbacks(kwargs):
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
            callbacks[name] = kwargs.pop(name)
    return callbacks

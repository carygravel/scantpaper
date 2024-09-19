"Threading model for the Document class"

from collections import defaultdict
import pathlib
import re
import logging
import subprocess
import datetime
import os
import tempfile
import shutil
from PIL import Image
import img2pdf
import ocrmypdf
from const import VERSION, POINTS_PER_INCH, ANNOTATION_COLOR
from importthread import Importhread, CancelledError, _note_callbacks
from i18n import _
from helpers import exec_command
from bboxtree import Bboxtree
from page import Page

logger = logging.getLogger(__name__)

img2pdf.default_dpi = 72.0

LEFT = 0
TOP = 1
RIGHT = 2
BOTTOM = 3


class SaveThread(Importhread):
    "subclass basethread for document"

    def save_pdf(self, **kwargs):
        "save pdf"
        callbacks = _note_callbacks(kwargs)
        return self.send("save_pdf", kwargs, **callbacks)

    def do_save_pdf(self, request):
        "save PDF in thread"
        options = defaultdict(None, request.args[0])

        self.message = _("Setting up PDF")
        outdir = pathlib.Path(options["dir"])
        filename = options["path"]
        if _need_temp_pdf(options.get("options")):
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

        if options.get("options") and options["options"].get("user-password"):
            if _encrypt_pdf(filename, options, request):
                return

        _set_timestamp(options)
        if options.get("options") and options["options"].get("ps"):
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
            _post_save_hook(filename, options.get("options"))

    def save_djvu(self, **kwargs):
        "save DjvU"
        callbacks = _note_callbacks(kwargs)
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

    def save_tiff(self, **kwargs):
        "save TIFF"
        callbacks = _note_callbacks(kwargs)
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
        callbacks = _note_callbacks(kwargs)
        return self.send("save_image", kwargs, **callbacks)

    def do_save_image(self, request):
        "save pages as image files in thread"
        options = defaultdict(None, request.args[0])

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
        callbacks = _note_callbacks(kwargs)
        return self.send("save_text", kwargs, **callbacks)

    def do_save_text(self, request):
        "save text file in thread"
        options = defaultdict(None, request.args[0])

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
        callbacks = _note_callbacks(kwargs)
        return self.send("save_hocr", kwargs, **callbacks)

    def do_save_hocr(self, request):
        "save hocr file in thread"
        options = defaultdict(None, request.args[0])

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

    def to_png(self, **kwargs):
        "convert to PNG"
        callbacks = _note_callbacks(kwargs)
        return self.send("to_png", kwargs, **callbacks)

    def do_to_png(self, request):
        "convert to PNG in thread"
        page = request.args[0]["page"]
        new = page.to_png(self.paper_sizes)
        new.uuid = page.uuid
        request.data(
            {
                "type": "page",
                "page": new,
                "info": {"replace": new.uuid},
            }
        )

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
        callbacks = _note_callbacks(kwargs)
        return self.send("user_defined", kwargs, **callbacks)

    def do_user_defined(self, request):
        "run user defined command on page in thread"
        options = request.args[0]

        if _page_gone("user-defined", options["page"], request):
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
                        "page": new,
                        "info": {"replace": new.uuid},
                    }
                )

        except (PermissionError, IOError) as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            request.error(
                f"Error creating file in {options['dir']}: {err}.",
            )


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
        not options.get("options")
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


# https://py-pdf.github.io/fpdf2/Annotations.html
def _add_annotations_to_pdf(page, gs_page):
    """Box is the same size as the page. We don't know the text position.
    Start at the top of the page (PDF coordinate system starts
    at the bottom left of the page)"""
    xresolution, yresolution, _units = gs_page.get_resolution()
    height = px2pt(gs_page.height, yresolution)
    for box in Bboxtree(gs_page.annotations).each_bbox():
        if box["type"] == "page" or "text" not in box or box["text"] == "":
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


def _page_gone(process, page, request):
    if not os.path.isfile(
        page.filename
    ):  # in case file was deleted after process started
        err = f"Page for process {request.uuid} no longer exists. Cannot {process}."
        logger.error(err)
        request.error(err)
        return True
    return False

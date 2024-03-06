"Threading model for the Document class"

import pathlib
import logging
import re
import os
import subprocess
import datetime
import glob
import tempfile
from PIL import ImageStat, ImageEnhance, ImageOps, ImageFilter
from importthread import CancelledError, _note_callbacks
from savethread import SaveThread, _page_gone
from i18n import _
from page import Page
from bboxtree import Bboxtree
import tesserocr

logger = logging.getLogger(__name__)


class DocThread(SaveThread):
    "subclass basethread for document"

    def rotate(self, **kwargs):
        "rotate page"
        callbacks = _note_callbacks(kwargs)
        return self.send("rotate", kwargs, **callbacks)

    def do_rotate(self, request):
        "rotate page in thread"
        options = request.args[0]
        angle, page = options["angle"], options["page"]

        if _page_gone("rotate", page, request):
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

    def analyse(self, **kwargs):
        "analyse page"
        callbacks = _note_callbacks(kwargs)
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
        callbacks = _note_callbacks(kwargs)
        return self.send("threshold", kwargs, **callbacks)

    def do_threshold(self, request):
        "threshold page in thread"
        options = request.args[0]
        threshold, page = (options["threshold"], options["page"])

        if _page_gone("threshold", page, request):
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
        callbacks = _note_callbacks(kwargs)
        return self.send("brightness_contrast", kwargs, **callbacks)

    def do_brightness_contrast(self, request):
        "adjust brightness and contrast in thread"
        options = request.args[0]
        brightness, contrast, page = (
            options["brightness"],
            options["contrast"],
            options["page"],
        )

        if _page_gone("brightness-contrast", options["page"], request):
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
        callbacks = _note_callbacks(kwargs)
        return self.send("negate", kwargs, **callbacks)

    def do_negate(self, request):
        "negate page in thread"
        options = request.args[0]
        page = options["page"]

        if _page_gone("negate", page, request):
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
        callbacks = _note_callbacks(kwargs)
        return self.send("unsharp", kwargs, **callbacks)

    def do_unsharp(self, request):
        "run unsharp mask in thread"
        options = request.args[0]
        page = options["page"]
        radius = options["radius"]
        percent = options["percent"]
        threshold = options["threshold"]

        if _page_gone("unsharp", page, request):
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
        callbacks = _note_callbacks(kwargs)
        return self.send("crop", kwargs, **callbacks)

    def do_crop(self, request):
        "crop page in thread"
        options = request.args[0]
        page = options["page"]
        left = options["x"]
        top = options["y"]
        width = options["w"]
        height = options["h"]

        if _page_gone("crop", options["page"], request):
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
        callbacks = _note_callbacks(kwargs)
        return self.send("split_page", kwargs, **callbacks)

    def do_split_page(self, request):
        "split page in thread"
        options = request.args[0]
        page = options["page"]

        if _page_gone("split", options["page"], request):
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
                "page": page,
                "info": {"replace": page.uuid},
            }
        )
        request.data(
            {
                "type": "page",
                "page": new2,
                "info": {"insert-after": page.uuid},
            }
        )

    def tesseract(self, **kwargs):
        "run tesseract"
        callbacks = _note_callbacks(kwargs)
        return self.send("tesseract", kwargs, **callbacks)

    def do_tesseract(self, request):
        "run tesseract in thread"
        options = request.args[0]
        page, language = (options["page"], options["language"])

        if _page_gone("tesseract", options["page"], request):
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
        callbacks = _note_callbacks(kwargs)
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

        if _page_gone("unpaper", options["page"], request):
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
                        "page": new2,
                        "info": {"insert-after": new.uuid},
                    }
                )

        except (PermissionError, IOError) as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            request.error(f"Error creating file in {options['dir']}: {err}.")

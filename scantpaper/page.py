"Class of data and methods for handling page objects"

import io
import locale
import re
import subprocess
import tempfile
import uuid
import logging
from PIL import Image
from const import POINTS_PER_INCH, MM_PER_INCH, CM_PER_INCH
from bboxtree import Bboxtree
from helpers import exec_command
import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib  # pylint: disable=wrong-import-position


PAGE_TOLERANCE = 0.02
MODE2DEPTH = {
    "1": 1,
    "L": 8,
    "P": 8,
    "RGB": 24,
    "RGBA": 32,
    "CMYK": 32,
    "YCbCr": 24,
    "LAB": 24,
    "HSV": 24,
    "I": 32,
    "F": 32,
}
logger = logging.getLogger(__name__)


class Page:
    "Class of data and methods for handling page objects"

    width = None
    height = None
    size = (None, None, None)
    resolution = None
    text_layer = None
    annotations = None
    dir = None
    saved = False
    _depth = None
    std_dev = None
    mean = None
    image_id = None

    def __init__(self, **kwargs):
        if ("image_object" not in kwargs and "filename" not in kwargs) or (
            "image_object" in kwargs and "filename" in kwargs
        ):
            raise ValueError(
                "Error: please supply either a filename or an image object"
            )
        if "image_object" in kwargs and not isinstance(
            kwargs["image_object"], Image.Image
        ):
            raise TypeError(
                f"Error: image_object is type {type(kwargs['image_object'])} not Image"
            )

        if "filename" in kwargs:
            self.image_object = Image.open(kwargs["filename"])

        # set this before setting attributes from kwargs in order to reuse uuid
        # if necessary. Therefore, the uuid tracks the page through import,
        # threshold, rotate, unpaper, etc. steps but still allows the page
        # number to change.
        self.uuid = uuid.uuid1()

        for key, value in kwargs.items():
            setattr(self, key, value)

        if self.resolution and not isinstance(self.resolution, tuple):
            self.resolution = (self.resolution, self.resolution, "PixelsPerInch")

        logger.info(
            "New page size %s, format %s, (%s)",
            len(self.image_object.tobytes()),
            self.image_object.mode,
            self.uuid,
        )

    def to_bytes(self):
        "return the image as bytes, e.g. suitable for storing as a blob in SQLite"
        img_byte_arr = io.BytesIO()
        self.image_object.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()

    @classmethod
    def from_bytes(cls, blob, **kwargs):
        "create a page from bytes"
        page = Page(image_object=Image.open(io.BytesIO(blob)))
        page.get_size()
        for key in [
            "id",
            "image_id",
            "resolution",
            "mean",
            "std_dev",
            "saved",
            "text_layer",
            "annotations",
        ]:
            if key in kwargs and kwargs[key] is not None:
                setattr(page, key, kwargs[key])
        return page

    def import_hocr(self, hocr):
        "import hocr"
        bboxtree = Bboxtree()
        bboxtree.from_hocr(hocr)
        self.text_layer = bboxtree.json()

    def export_hocr(self):
        "export hocr"
        return Bboxtree(self.text_layer).to_hocr()

    def import_djvu_txt(self, djvu):
        "import djvu text"
        tree = Bboxtree()
        tree.from_djvu_txt(djvu)
        self.text_layer = tree.json()

    def export_djvu_txt(self):
        "export djvu text"
        if self.text_layer is None:
            return None
        return Bboxtree(self.text_layer).to_djvu_txt()

    def export_text(self):
        "export simple text"
        if self.text_layer is None:
            return ""
        return Bboxtree(self.text_layer).to_text()

    def import_pdftotext(self, html):
        "import text layer from PDF"
        tree = Bboxtree()
        res = self.get_resolution()
        tree.from_pdftotext(html, (res[0], res[1]), self.get_size())
        self.text_layer = tree.json()

    def import_annotations(self, hocr):
        "import annotation layer from hocr"
        bboxtree = Bboxtree()
        bboxtree.from_hocr(hocr)
        self.annotations = bboxtree.json()

    def import_djvu_ann(self, ann):
        "import annotation layer from djvu"
        imagew, imageh = self.get_size()
        tree = Bboxtree()
        tree.from_djvu_ann(ann, imagew, imageh)
        self.annotations = tree.json()

    def export_djvu_ann(self):
        "export annotation for djvu"
        if self.annotations is None:
            return None
        return Bboxtree(self.annotations).to_djvu_ann()

    def get_size(self):
        "get the image size"
        if self.width is None or self.height is None:
            self.width = self.image_object.width
            self.height = self.image_object.height

        return self.width, self.height

    def get_resolution(self, paper_sizes=None):
        "get the resolution"
        if isinstance(self.resolution, (int, float)) or (
            isinstance(self.resolution, tuple) and self.resolution[0] is not None
        ):
            return self.resolution

        locale.setlocale(locale.LC_NUMERIC, "C")
        if self.size != (None, None, None):
            width, height = self.get_size()
            logger.debug("PDF size %sx%s %s", self.size[0], self.size[1], self.size[2])
            logger.debug("image size %s %s", width, height)
            if self.size[2] != "pts":
                raise ValueError(f"Error: unknown units '{self.size[2]}'")

            self.resolution = (
                width / self.size[0] * POINTS_PER_INCH,
                height / self.size[1] * POINTS_PER_INCH,
                "PixelsPerInch",
            )
            logger.debug("resolution %s %s", self.resolution[0], self.resolution[1])
            return self.resolution

        units = "PixelsPerInch"
        if self.image_object.format is not None and re.search(
            r"^P.M$", self.image_object.format, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            # Return the first match based on the format
            for value in self.matching_paper_sizes(paper_sizes).values():
                xresolution = value
                yresolution = value
                self.resolution = (xresolution, yresolution, units)
                return self.resolution

            # Default to 72
            self.resolution = (POINTS_PER_INCH, POINTS_PER_INCH, units)
            return self.resolution

        xresolution, yresolution = 72, 72
        for key in ["dpi", "aspect", "jfif_density"]:
            # for some reason PIL reports TIFFs e.g. in test 11271 as resolution==1
            if key in self.image_object.info and self.image_object.info[key][0] > 1:
                xresolution, yresolution = self.image_object.info[key]
            if not isinstance(xresolution, float):
                xresolution, yresolution = float(xresolution), float(yresolution)

        if (
            "jfif_unit" in self.image_object.info
            and self.image_object.info["jfif_unit"] == 2
        ):
            units = "PixelsPerCentimeter"
            xresolution *= CM_PER_INCH
            yresolution *= CM_PER_INCH

        # if no units for resolution, rewrite the resolution, which forces units
        # tested by test_1114_save_pdf_different_resolutions.py
        # if (
        #     xresolution != yresolution
        #     and "density_unit" not in image.info
        #     and "jfif_unit" not in image.info
        # ):
        #     image.save(self.filename, dpi=(xresolution, yresolution))

        self.resolution = (xresolution, yresolution, units)
        return self.resolution

    def matching_paper_sizes(self, paper_sizes):
        """Given paper width and height (mm), and hash of paper sizes,
        returns hash of matching resolutions (pixels per inch)"""
        matching = {}
        if paper_sizes is None:
            return matching
        width, height = self.get_size()
        ratio = height / width
        if ratio < 1:
            ratio = 1 / ratio
        for key in paper_sizes.keys():
            if (
                paper_sizes[key]["x"] > 0
                and abs(ratio - paper_sizes[key]["y"] / paper_sizes[key]["x"])
                < PAGE_TOLERANCE
            ):
                matching[key] = (
                    (height if (height > width) else width)
                    / paper_sizes[key]["y"]
                    * MM_PER_INCH
                )

        return matching

    def get_pixbuf(self):
        "return a pixbuf of the image"
        if self.image_object is None:
            logger.warning("Cannot get pixbuf from None")
            return None
        # TODO: This doesn't work, probably because I didn't test it with an RGB image,
        # but would be a better solution
        # width, height = self.image_object.size
        # return GdkPixbuf.Pixbuf.new_from_bytes(
        #     GLib.Bytes.new(self.image_object.tobytes()),
        #     GdkPixbuf.Colorspace.RGB,
        #     False,
        #     8,
        #     width,
        #     height,
        #     width * 3,
        # )
        with tempfile.NamedTemporaryFile(dir=self.dir, suffix=".png") as filename:
            self.image_object.save(filename.name)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename.name)
            except (GLib.Error, TypeError) as exc:
                logger.warning("Caught error getting pixbuf: %s", exc)
        return pixbuf

    def get_pixbuf_at_scale(self, max_width, max_height):
        """logic taken from at_scale_size_prepared_cb() in
        https://gitlab.gnome.org/GNOME/gdk-pixbuf/blob/2.40.0/gdk-pixbuf/gdk-pixbuf-io.c

        Returns the pixbuf scaled to fit in the given box"""
        if self.image_object is None:
            logger.warning("Cannot get pixbuf from None")
            return None
        xresolution, yresolution, _units = self.get_resolution()
        width, height = self.get_size()
        width, height = _prepare_scale(
            width, height, xresolution / yresolution, max_width, max_height
        )
        pixbuf = None
        with tempfile.NamedTemporaryFile(dir=self.dir, suffix=".png") as filename:
            self.image_object.save(filename.name)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filename.name, width, height, False
                )
            except (GLib.Error, TypeError) as exc:
                logger.warning("Caught error getting pixbuf: %s", exc)
        return pixbuf

    def get_depth(self):
        "return image depth based on mode provided by PIL"
        if self._depth is None:
            self._depth = MODE2DEPTH[self.image_object.mode]
        return self._depth

    def _equalize_resolution(self):
        "c44 and cjb2 do not support different resolutions in the x and y directions, so resample"
        xresolution, yresolution, units = self.get_resolution()
        width, height = self.width, self.height
        if xresolution != yresolution:
            resolution = max(xresolution, yresolution)
            width *= resolution / xresolution
            height *= resolution / yresolution
            logger.info("Upsampling to %sx%s %s", resolution, resolution, units)
            return resolution, self.image_object.resize(
                (int(width), int(height)), resample=Image.BOX
            )
        return xresolution, self.image_object

    def write_image_for_pdf(self, filename, options):
        "write the image as a PNG file"
        image = self.image_object
        if (
            options
            and "options" in options
            and options["options"]
            and "downsample" in options["options"]
            and options["options"]["downsample"]
        ):
            if options["options"]["downsample dpi"] < min(
                self.resolution[0], self.resolution[1]
            ):
                width = int(
                    self.width
                    * options["options"]["downsample dpi"]
                    // self.resolution[0]
                )
                height = int(
                    self.height
                    * options["options"]["downsample dpi"]
                    // self.resolution[1]
                )
                image = image.resize((width, height))
        if (
            options
            and "options" in options
            and options["options"]
            and "compression" in options["options"]
            and options["options"]["compression"][0] == "g"  # g3 or g4
        ):
            # Grayscale
            image = image.convert("L")
            # Threshold
            threshold = 0.4 * 255
            image = image.point(lambda p: 255 if p > threshold else 0)
            # To mono
            image = image.convert("1")

        xresolution, yresolution, _units = self.get_resolution()
        image.save(filename, dpi=(xresolution, yresolution))

    def write_image_for_djvu(self, filename, options):
        "Save the image as a DjVu file."
        # Check the image depth to decide what sort of compression to use

        # c44 and cjb2 do not support different resolutions in the x and y
        # directions, so resample
        resolution, image = self._equalize_resolution()

        # cjb2 can only use pnm and tif
        if image.mode == "1":
            compression = "cjb2"
            suffix = ".pbm"

        # c44 can only use pnm and jpg
        else:
            compression = "c44"
            suffix = ".pnm"

        with tempfile.NamedTemporaryFile(
            dir=options.get("dir"), suffix=suffix
        ) as tempimage:
            image.save(tempimage.name)
            exec_command(
                [
                    compression,
                    "-dpi",
                    str(int(resolution)),
                    tempimage.name,
                    filename,
                ],
                options["pidfile"],
            )
            self._add_txt_to_djvu(filename, options.get("dir"))
            self._add_ann_to_djvu(filename, options.get("dir"))

    def _add_txt_to_djvu(self, djvu, dirname):
        if self.text_layer is not None:
            txt = self.export_djvu_txt()
            if txt == "":
                return
            logger.debug(txt)

            # Write djvusedtxtfile
            with tempfile.NamedTemporaryFile(
                mode="wt", dir=dirname, suffix=".txt"
            ) as fhd:
                fhd.write(txt)
                fhd.flush()

                # Run djvusedtxtfile
                cmd = [
                    "djvused",
                    djvu,
                    "-e",
                    f"select 1; set-txt {fhd.name}",
                    "-s",
                ]
                logger.info(cmd)
                subprocess.run(cmd, check=True)

    def _add_ann_to_djvu(self, djvu, dirname):
        """FIXME - refactor this together with _add_txt_to_djvu"""
        if self.annotations is not None:
            ann = self.export_djvu_ann()
            if ann == "":
                return
            logger.debug(ann)

            # Write djvusedtxtfile
            with tempfile.NamedTemporaryFile(
                mode="w", dir=dirname, suffix=".txt"
            ) as fhd:
                fhd.write(ann)
                fhd.flush()

                # Run djvusedtxtfile
                cmd = [
                    "djvused",
                    djvu,
                    "-e",
                    f"select 1; set-ant {fhd.name}",
                    "-s",
                ]
                logger.info(cmd)
                subprocess.run(cmd, check=True)

    def write_image_for_tiff(self, filename, options):
        "Save the image as a TIFF file."
        with tempfile.NamedTemporaryFile(
            dir=options.get("dir"), suffix=".tif"
        ) as infile:
            self.image_object.save(infile.name)
            xresolution, yresolution, units = self.resolution

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
                infile.name,
                "-units",
                units,
                "-density",
                f"{xresolution}x{yresolution}",
                *depth,
                filename,
            ]
            subprocess.run(cmd, check=True)


def _prepare_scale(image_width, image_height, res_ratio, max_width, max_height):
    if image_width <= 0 or image_height <= 0 or max_width <= 0 or max_height <= 0:
        return None, None

    image_width = image_width / res_ratio
    if image_height * max_width > image_width * max_height:
        image_width = image_width * max_height / image_height
        image_height = max_height

    else:
        image_height = image_height * max_width / image_width
        image_width = max_width

    return image_width, image_height

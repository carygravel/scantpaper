"Class of data and methods for handling page objects"
import locale
import re
import shutil
import os
import tempfile
import uuid
import logging
import gettext
import copy
from PIL import Image
from const import POINTS_PER_INCH, MM_PER_INCH, CM_PER_INCH
from bboxtree import Bboxtree
import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib  # pylint: disable=wrong-import-position


PAGE_TOLERANCE = 0.02
VERSION = "2.13.2"
logger = logging.getLogger(__name__)
# easier to extract strings with xgettext
_ = gettext.gettext


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

    def __init__(self, **kwargs):
        if "filename" not in kwargs:
            raise ValueError("Error: filename not supplied")
        if not os.path.isfile(kwargs["filename"]):
            raise FileNotFoundError("Error: filename not found")
        if "format" not in kwargs:
            raise ValueError("Error: format not supplied")

        logger.info(
            "New page filename %s, format %s", kwargs["filename"], kwargs["format"]
        )
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.uuid = uuid.uuid1()

        # copy or move image to session directory
        suffix = {
            "Portable Network Graphics": ".png",
            "Joint Photographic Experts Group JFIF format": ".jpg",
            "Tagged Image File Format": ".tif",
            "Portable anymap": ".pnm",
            "Portable pixmap format (color)": ".ppm",
            "Portable graymap format (gray scale)": ".pgm",
            "Portable bitmap format (black and white)": ".pbm",
            "PBM": ".pbm",
            "PPM": ".ppm",
            "PNG": ".png",
            "JPEG": ".jpg",
            "CompuServe graphics interchange format": ".gif",
        }
        self.filename = (
            tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
                dir=kwargs["dir"],
                suffix=suffix[kwargs["format"]],
                delete=False,
            ).name
        )
        if "delete" in kwargs and kwargs["delete"]:
            shutil.move(kwargs["filename"], self.filename)
        else:
            shutil.copy2(kwargs["filename"], self.filename)

        logger.info("New page written as %s (%s)", self.filename, self.uuid)

    def clone(self, copy_image=False):
        "clone the page"
        new = copy.deepcopy(self)
        new.uuid = uuid.uuid1()
        if copy_image:
            _filename, suffix = os.path.splitext(self.filename)
            new.filename = (
                tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
                    dir=self.dir, suffix=suffix
                ).name
            )
            logger.info(
                "Cloning %s (%s) -> %s (%s)",
                self.filename,
                self.uuid,
                new.filename,
                new.uuid,
            )
            shutil.copy2(self.filename, new.filename)
        return new

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
            return None
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

    def to_png(self, page_sizes=None):
        "Convert the image format to PNG"
        png = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            dir=self.dir, suffix=".png", delete=False
        ).name
        image = self.im_object()
        image.save(png)
        new = Page(
            filename=png,
            format="Portable Network Graphics",
            dir=self.dir,
            resolution=self.get_resolution(page_sizes),
            width=self.width,
            height=self.height,
        )
        if self.text_layer is not None:
            new.text_layer = self.text_layer

        return new

    def get_size(self):
        "get the image size"
        if self.width is None or self.height is None:
            image = self.im_object()
            self.width = image.width
            self.height = image.height

        return self.width, self.height

    def get_resolution(self, paper_sizes=None):
        "get the resolution"
        if self.resolution is not None:
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

        image = self.im_object()
        image_format = image.format
        units = "PixelsPerInch"
        if re.search(r"^P.M$", image_format, re.MULTILINE | re.DOTALL | re.VERBOSE):
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
            if key in image.info and image.info[key][0] > 0:
                xresolution, yresolution = image.info[key]

        if "jfif_unit" in image.info and image.info["jfif_unit"] == 2:
            units = "PixelsPerCentimeter"
            xresolution *= CM_PER_INCH
            yresolution *= CM_PER_INCH

        # if no units for resolution, rewrite the resolution, which forces units
        # tested by test_1114_save_pdf_different_resolutions.py
        if (
            xresolution != yresolution
            and "density_unit" not in image.info
            and "jfif_unit" not in image.info
        ):
            image.save(self.filename, dpi=(xresolution, yresolution))

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

    def im_object(self):
        "returns PIL object"
        return Image.open(self.filename)

    def get_pixbuf_at_scale(self, max_width, max_height):
        """logic taken from at_scale_size_prepared_cb() in
        https://gitlab.gnome.org/GNOME/gdk-pixbuf/blob/2.40.0/gdk-pixbuf/gdk-pixbuf-io.c

        Returns the pixbuf scaled to fit in the given box"""
        xresolution, yresolution, _units = self.get_resolution()
        width, height = self.get_size()
        width, height = _prepare_scale(
            width, height, xresolution / yresolution, max_width, max_height
        )
        pixbuf = None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.filename, width, height, False
            )
        except (GLib.Error, TypeError) as exc:
            logger.warning("Caught error getting pixbuf: %s", exc)
        return pixbuf


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

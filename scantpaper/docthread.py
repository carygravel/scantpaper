"Threading model for the Document class"

import pathlib
import json
import logging
import re
import os
import subprocess
import datetime
import glob
import tempfile
import sqlite3
from PIL import ImageStat, ImageEnhance, ImageOps, ImageFilter
from importthread import CancelledError, _note_callbacks
from savethread import SaveThread
from i18n import _
from page import Page
from bboxtree import Bboxtree
import tesserocr
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)

THUMBNAIL = 100  # pixels


class DocThread(SaveThread):
    "subclass basethread for document"

    heightt = THUMBNAIL
    widtht = THUMBNAIL
    _action_id = 0
    _db = None
    _dir = None
    number_undo_steps = 1

    def __init__(self, *args, **kwargs):
        for key in ["dir", "db"]:
            if key in kwargs:
                setattr(self, "_" + key, kwargs.pop(key))
        super().__init__(*args, **kwargs)
        if self._db:
            self._db = pathlib.Path(self._db)
        if self._dir:
            self._dir = pathlib.Path(self._dir)
        else:
            if self._db:
                self._dir = self._db.parent
            else:
                self._dir = pathlib.Path(tempfile.gettempdir())
        if self._db is None:
            self._db = self._dir / "document.db"

        self._con = sqlite3.connect(self._db, check_same_thread=False)
        self._cur = self._con.cursor()
        self._cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='page';"
        )
        if not self._cur.fetchone():
            self._cur.execute(
                """CREATE TABLE page(
                    id INTEGER PRIMARY KEY,
                    image BLOB,
                    thumb BLOB,
                    x_res FLOAT,
                    y_res FLOAT,
                    std_dev TEXT,
                    mean TEXT,
                    saved BOOL,
                    text TEXT,
                    annotations TEXT)"""
            )
            # TODO: the number table is just a buffer of part of undo_buffer and can be factored out
            self._cur.execute(
                """CREATE TABLE number(
                    row_id INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    page_id INTEGER NOT NULL,
                    FOREIGN KEY (page_id) REFERENCES page(id),
                    PRIMARY KEY (row_id))"""
            )
            self._cur.execute(
                """CREATE TABLE undo_buffer(
                    action_id INTEGER NOT NULL,
                    row_id INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    page_id INTEGER NOT NULL,
                    FOREIGN KEY (page_id) REFERENCES page(id),
                    PRIMARY KEY (action_id, row_id))"""
            )

    def open(self, db):
        "open a saved database"
        self._db = db
        self._con = sqlite3.connect(self._db, check_same_thread=False)
        self._cur = self._con.cursor()
        self._cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='page';"
        )
        if not self._cur.fetchone():
            raise TypeError(f"File '{self._db}' is not a gsscan2pdf document")

    def _insert_page(self, page):
        "insert a page to the database"

        x_res, y_res = None, None
        if page.resolution:
            x_res, y_res = page.resolution[0], page.resolution[1]
        thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
        self._cur.execute(
            """INSERT INTO page (
                id, image, thumb, x_res, y_res, mean, std_dev, saved, text, annotations)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                page.to_bytes(),
                self._pixbuf_to_bytes(thumb),
                x_res,
                y_res,
                None if page.mean is None else json.dumps(page.mean),
                None if page.std_dev is None else json.dumps(page.std_dev),
                page.saved,
                page.text_layer,
                page.annotations,
            ),
        )
        self._con.commit()
        return thumb

    def add_page(self, page, number=None):
        "add a page to the database"

        if number is None:
            self._cur.execute("SELECT MAX(page_number) FROM number")
            number = self._cur.fetchone()[0]
            if number is None:
                number = 1
            else:
                number += 1

        if self.find_row_id_by_page_number(number):
            raise ValueError(f"Page {number} already exists")

        thumb = self._insert_page(page)
        page_id = self._cur.lastrowid
        self._cur.execute("SELECT MAX(row_id) FROM number")
        max_row_id = self._cur.fetchone()[0]
        if max_row_id is None:
            max_row_id = -1
        self._cur.execute(
            """INSERT INTO number (row_id, page_number, page_id)
               VALUES (?, ?, ?)""",
            (
                max_row_id + 1,
                number,
                page_id,
            ),
        )
        self._con.commit()
        return number, thumb, page_id

    def replace_page(self, page, number):
        "replace a page in the database"

        i = self.find_row_id_by_page_number(number)
        if i is None:
            raise ValueError(f"Page {number} does not exist")

        thumb = self._insert_page(page)
        page_id = self._cur.lastrowid
        self._cur.execute(
            """UPDATE number SET page_number = ?, page_id = ?
               WHERE row_id = ?""",
            (
                number,
                page_id,
                i,
            ),
        )
        self._con.commit()
        return number, thumb, page_id

    def delete_page(self, **kwargs):
        "delete a page from the database"

        row_id = None
        if "number" in kwargs:
            row_id = self.find_row_id_by_page_number(kwargs["number"])
            if row_id is None:
                raise ValueError(f"Page {kwargs['number']} does not exist")
        elif "row_id" in kwargs:
            row_id = kwargs["row_id"]
        if row_id is None:
            raise ValueError("Specify either row_id or number")

        self._cur.execute("DELETE FROM number WHERE row_id = ?", (row_id,))
        self._con.commit()

    def find_row_id_by_page_number(self, number):
        "find a row id by its page number"
        self._cur.execute("SELECT row_id FROM number WHERE page_number = ?", (number,))
        row = self._cur.fetchone()
        if row:
            return row[0]
        return None

    def find_page_number_by_page_id(self, page_id):
        "find a page id by its page number"
        self._cur.execute(
            "SELECT page_number FROM number WHERE page_id = ?", (page_id,)
        )
        row = self._cur.fetchone()
        if row:
            return row[0]
        return None

    def page_number_table(self):
        "get data for page number/thumb table"
        self._cur.execute(
            """SELECT page_number, thumb, page_id
               FROM number, page WHERE page_id = page.id ORDER BY page_number"""
        )
        rows = []
        for row in self._cur.fetchall():
            rows.append([row[0], self._bytes_to_pixbuf(row[1]), row[2]])
        return rows

    def get_page(self, **kwargs):
        "get a page from the database"
        if "number" in kwargs:
            self._cur.execute(
                """SELECT image, x_res, y_res, mean, std_dev, text, annotations, id
                   FROM page, number WHERE id = page_id AND page_number = ?""",
                (kwargs["number"],),
            )
        elif "id" in kwargs:
            self._cur.execute(
                """SELECT image, x_res, y_res, mean, std_dev, text, annotations, page_number
                   FROM page, number WHERE id = page_id AND page_id = ?""",
                (kwargs["id"],),
            )
        else:
            raise ValueError("Please specify either page number or page id")
        row = self._cur.fetchone()
        if row is None:
            if "number" in kwargs:
                raise ValueError(f"Page number {kwargs['number']} not found")
            raise ValueError(f"Page id {kwargs['id']} not found")
        return Page.from_bytes(
            row[0],
            id=row[7] if "number" in kwargs else kwargs["id"],
            resolution=(row[1], row[2], "PixelsPerInch"),
            mean=None if row[3] is None else json.loads(row[3], strict=False),
            std_dev=None if row[4] is None else json.loads(row[4], strict=False),
            text_layer=row[5],
            annotations=row[6],
        )

    def clone_page(self, pageid, number):
        "clone a page in the database"
        self._cur.execute(
            """SELECT image, thumb, x_res, y_res, mean, std_dev, text, annotations
               FROM page, number WHERE id = page_id AND page_id = ?""",
            (pageid,),
        )
        row = self._cur.fetchone()
        self._cur.execute(
            """INSERT INTO page (
                id, image, thumb, x_res, y_res, mean, std_dev, text, annotations)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*row,),
        )
        self._con.commit()
        new_page_id = self._cur.lastrowid
        self._cur.execute("SELECT MAX(row_id) FROM number")
        max_row_id = self._cur.fetchone()[0]
        if max_row_id is None:
            max_row_id = -1
        self._cur.execute(
            """INSERT INTO number (row_id, page_number, page_id)
               VALUES (?, ?, ?)""",
            (
                max_row_id + 1,
                number,
                new_page_id,
            ),
        )
        self._con.commit()
        return new_page_id

    def _take_snapshot(self):
        "take a snapshot of the current state of the document"

        # in case the user has undone one or more actions, before taking a
        # snapshot, remove the redo steps
        self._cur.execute(
            "DELETE FROM undo_buffer WHERE action_id > ?", (self._action_id,)
        )
        self._action_id += 1

        # copy page numbers and order to buffer
        self._cur.execute(
            """INSERT INTO undo_buffer (action_id, row_id, page_number, page_id)
                SELECT ?, row_id, page_number, page_id
                FROM number""",
            (self._action_id,),
        )

        # delete those outside the undo limit
        self._cur.execute(
            "DELETE FROM undo_buffer WHERE action_id < ?",
            (self._action_id - self.number_undo_steps,),
        )
        self._con.commit()

    def _get_snapshot(self, action_id):
        "fetch the snapshot of the document with the given action id"
        self._cur.execute(
            """SELECT page_number, thumb, page_id
                FROM undo_buffer, page
                WHERE action_id = ? and page_id = id
                ORDER BY page_number""",
            (action_id,),
        )
        rows = []
        for row in self._cur.fetchall():
            row = list(row)
            row[1] = self._bytes_to_pixbuf(row[1])
            rows.append(row)
        return rows

    def _get_snapshots(self):
        "fetch the snapshot of the document with the given action id"
        self._cur.execute(
            """SELECT action_id, page_number, page_id
                FROM undo_buffer
                ORDER BY action_id, page_number"""
        )
        return self._cur.fetchall()

    def _pixbuf_to_bytes(self, pixbuf):
        "given a pixbuf, return the equivalent bytes, in order to store them as a blob"
        with tempfile.NamedTemporaryFile(dir=self._dir, suffix=".png") as temp:
            pixbuf.savev(temp.name, "png")
            return temp.read()

    def _bytes_to_pixbuf(self, blob):
        "given a stream of bytes, return the equivalent pixbuf"
        with tempfile.NamedTemporaryFile(dir=self._dir, suffix=".png") as temp:
            temp.write(blob)
            temp.flush()
            return GdkPixbuf.Pixbuf.new_from_file(temp.name)

    def can_undo(self):
        "checks whether undo is possible"
        self._cur.execute("SELECT min(action_id) FROM undo_buffer")
        min_action_id = self._cur.fetchone()[0]
        return min_action_id is not None and min_action_id < self._action_id

    def can_redo(self):
        "checks whether redo is possible"
        self._cur.execute("SELECT max(action_id) FROM undo_buffer")
        max_action_id = self._cur.fetchone()[0]
        return max_action_id is not None and max_action_id > self._action_id

    def _restore_snapshot(self):
        "restore the state of the last snapshot"
        # clear page number table and copy from buffer
        self._cur.execute("DELETE FROM number")
        self._cur.execute(
            """INSERT INTO number (row_id, page_number, page_id)
                SELECT row_id, page_number, page_id
                FROM undo_buffer
                WHERE action_id = ?""",
            (self._action_id,),
        )

    def undo(self):
        "restore the state of the last snapshot"
        if not self.can_undo():
            raise StopIteration("No more undo steps possible")
        self._action_id -= 1
        self._restore_snapshot()

    def redo(self):
        "restore the state of the last snapshot"
        if not self.can_redo():
            raise StopIteration("No more redo steps possible")
        self._action_id += 1
        self._restore_snapshot()

    def set_saved(self, page_id, saved=True):
        "mark given page as saved"
        if not isinstance(page_id, list):
            page_id = [page_id]
        self._cur.execute(
            f"UPDATE page SET saved = ? WHERE id IN ({", ".join(["?"]*len(page_id))})",
            (
                saved,
                *page_id,
            ),
        )
        self._con.commit()

    def pages_saved(self):
        "Check that all pages have been saved"
        self._cur.execute(
            """SELECT COUNT(id)
                FROM number, page
                WHERE saved = 0 and page_id = id"""
        )
        return self._cur.fetchone()[0] == 0

    def get_thumb(self, page_id):
        "gets the thumbnail for the given page_id"
        self._cur.execute("SELECT thumb FROM page WHERE id = ?", (page_id,))
        return self._bytes_to_pixbuf(self._cur.fetchone()[0])

    def get_text(self, page_id):
        "gets the text layer for the given page"
        self._cur.execute("SELECT text FROM page WHERE id = ?", (page_id,))
        return self._cur.fetchone()[0]

    def set_text(self, page_id, text):
        "sets the text layer for the given page"
        self._cur.execute(
            "UPDATE page SET text = ? WHERE id = ?",
            (
                text,
                page_id,
            ),
        )
        self._con.commit()

    def get_annotations(self, page_id):
        "gets the annotations layer for the given page"
        self._cur.execute("SELECT annotations FROM page WHERE id = ?", (page_id,))
        return self._cur.fetchone()[0]

    def set_annotations(self, page_id, annotations):
        "sets the annotations layer for the given page"
        self._cur.execute(
            "UPDATE page SET annotations = ? WHERE id = ?",
            (
                annotations,
                page_id,
            ),
        )
        self._con.commit()

    def get_resolution(self, page_id):
        "gets the resolution for the given page"
        self._cur.execute("SELECT x_res, y_res FROM page WHERE id = ?", (page_id,))
        return self._cur.fetchone()

    def set_resolution(self, page_id, x_res, y_res):
        "sets the resolution for the given page"
        self._cur.execute(
            "UPDATE page SET x_res = ?, y_res = ? WHERE id = ?",
            (
                x_res,
                y_res,
                page_id,
            ),
        )
        self._con.commit()

    def get_mean_std_dev(self, page_id):
        "gets the mean and std_dev for the given page"
        self._cur.execute("SELECT mean, std_dev FROM page WHERE id = ?", (page_id,))
        mean, std_dev = self._cur.fetchone()
        mean = json.loads(mean, strict=False)
        std_dev = json.loads(std_dev, strict=False)
        return mean, std_dev

    def set_mean_std_dev(self, page_id, mean, std_dev):
        "sets the mean and std_dev for the given page"
        self._cur.execute(
            "UPDATE page SET mean = ?, std_dev = ? WHERE id = ?",
            (
                json.dumps(mean),
                json.dumps(std_dev),
                page_id,
            ),
        )
        self._con.commit()

    def rotate(self, **kwargs):
        "rotate page"
        callbacks = _note_callbacks(kwargs)
        return self.send("rotate", kwargs, **callbacks)

    def do_rotate(self, request):
        "rotate page in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])
        logger.info("Rotating %s by %s degrees", page.id, options["angle"])
        page.image_object = page.image_object.rotate(options["angle"], expand=True)

        if self.cancel:
            raise CancelledError()

        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        if options["angle"] in (90, 270):
            page.width, page.height = page.height, page.width
            page.resolution = (
                page.resolution[1],
                page.resolution[0],
                page.resolution[2],
            )
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

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
        for page_id in list_of_pages:
            page = self.get_page(id=page_id)
            self.progress = (i - 1) / total
            self.message = _("Analysing page %i of %i") % (i, total)
            i += 1

            if self.cancel:
                raise CancelledError()
            stat = ImageStat.Stat(page.image_object)
            # ImageStat seems to have a bug here. Working around it.
            if stat.count == [0]:
                page.mean = [0.0]
                page.std_dev = [0.0]
            else:
                page.mean = stat.mean
                page.std_dev = stat.stddev
            logger.info("std dev: %s mean: %s", page.std_dev, page.mean)
            if self.cancel:
                raise CancelledError()

            # TODO add any other useful image analysis here e.g. is the page mis-oriented?
            #  detect mis-orientation possible algorithm:
            #   blur or low-pass filter the image (so words look like ovals)
            #   look at few vertical narrow slices of the image and get the Standard Deviation
            #   if most of the Std Dev are high, then it might be portrait
            page.analyse_time = datetime.datetime.now()
            request.data(
                {
                    "type": "page",
                    "row": self.replace_page(
                        page, self.find_page_number_by_page_id(page.id)
                    ),
                    "replace": page.id,
                }
            )

    def threshold(self, **kwargs):
        "threshold page"
        callbacks = _note_callbacks(kwargs)
        return self.send("threshold", kwargs, **callbacks)

    def do_threshold(self, request):
        "threshold page in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])

        if self.cancel:
            raise CancelledError()
        logger.info("Threshold %s with %s", page.id, options["threshold"])

        # To grayscale
        page.image_object = page.image_object.convert("L")
        # Threshold
        page.image_object = page.image_object.point(
            lambda p: 255 if p > options["threshold"] else 0
        )
        # To mono
        page.image_object = page.image_object.convert("1")

        if self.cancel:
            raise CancelledError()

        if self.cancel:
            raise CancelledError()
        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

    def brightness_contrast(self, **kwargs):
        "adjust brightness and contrast"
        callbacks = _note_callbacks(kwargs)
        return self.send("brightness_contrast", kwargs, **callbacks)

    def do_brightness_contrast(self, request):
        "adjust brightness and contrast in thread"
        options = request.args[0]
        brightness, contrast = options["brightness"], options["contrast"]
        page = self.get_page(id=options["page"])
        logger.info(
            "Enhance %s with brightness %s, contrast %s",
            page.id,
            brightness,
            contrast,
        )
        if self.cancel:
            raise CancelledError()

        page.image_object = ImageEnhance.Brightness(page.image_object).enhance(
            brightness
        )
        page.image_object = ImageEnhance.Contrast(page.image_object).enhance(contrast)

        if self.cancel:
            raise CancelledError()

        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

    def negate(self, **kwargs):
        "negate page"
        callbacks = _note_callbacks(kwargs)
        return self.send("negate", kwargs, **callbacks)

    def do_negate(self, request):
        "negate page in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])

        logger.info("Invert %s", page.id)
        page.image_object = ImageOps.invert(page.image_object)

        if self.cancel:
            raise CancelledError()

        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

    def unsharp(self, **kwargs):
        "run unsharp mask"
        callbacks = _note_callbacks(kwargs)
        return self.send("unsharp", kwargs, **callbacks)

    def do_unsharp(self, request):
        "run unsharp mask in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])
        radius = options["radius"]
        percent = options["percent"]
        threshold = options["threshold"]

        logger.info(
            "Unsharp mask %s radius %s percent %s threshold %s",
            page.id,
            radius,
            percent,
            threshold,
        )
        page.image_object = page.image_object.filter(
            ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
        )

        if self.cancel:
            raise CancelledError()

        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

    def crop(self, **kwargs):
        "crop page"
        callbacks = _note_callbacks(kwargs)
        return self.send("crop", kwargs, **callbacks)

    def do_crop(self, request):
        "crop page in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])
        left = options["x"]
        top = options["y"]
        width = options["w"]
        height = options["h"]

        logger.info("Crop %s x %s y %s w %s h %s", page.id, left, top, width, height)

        page.image_object = page.image_object.crop(
            (left, top, left + width, top + height)
        )

        if self.cancel:
            raise CancelledError()

        page.width = page.image_object.width
        page.height = page.image_object.height

        if page.text_layer is not None:
            bboxtree = Bboxtree(page.text_layer)
            page.text_layer = bboxtree.crop(left, top, width, height).json()

        page.dirty_time = datetime.datetime.now()  # flag as dirty
        page.saved = False
        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

    def split_page(self, **kwargs):
        "split page"
        callbacks = _note_callbacks(kwargs)
        return self.send("split_page", kwargs, **callbacks)

    def do_split_page(self, request):
        "split page in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])
        image = page.image_object
        image2 = image.copy()

        logger.info(
            "Splitting in direction %s @ %s -> %s + %s",
            options["direction"],
            options["position"],
            page.id,
            page.id,
        )
        # split the image
        boxes = _calculate_crop_tuples(options, image)
        page.image_object = image.crop(boxes[0])
        image2 = image2.crop(boxes[1])

        if self.cancel:
            raise CancelledError()

        # Write them
        page.width = page.image_object.width
        page.height = page.image_object.height
        page.dirty_time = datetime.datetime.now()  # flag as dirty

        # split doesn't change the resolution, so we can safely copy it
        new2 = Page(
            image_object=image2,
            dir=options["dir"],
            delete=True,
            resolution=page.resolution,
            dirty_time=page.dirty_time,
        )
        if page.text_layer:
            bboxtree = Bboxtree(page.text_layer)
            bboxtree2 = Bboxtree(page.text_layer)
            page.text_layer = bboxtree.crop(*boxes[0]).json()
            new2.text_layer = bboxtree2.crop(*boxes[2]).json()

        # have to insert the extra page first, because after the replacing the
        # input page, it won't exist any more.
        number = self.find_page_number_by_page_id(page.id)
        request.data(
            {
                "type": "page",
                "row": self.add_page(new2, number + 1),
                "insert-after": page.id,
            }
        )
        request.data(
            {
                "type": "page",
                "row": self.replace_page(page, number),
                "replace": page.id,
            }
        )

    def tesseract(self, **kwargs):
        "run tesseract"
        callbacks = _note_callbacks(kwargs)
        return self.send("tesseract", kwargs, **callbacks)

    def do_tesseract(self, request):
        "run tesseract in thread"
        options = request.args[0]
        page = self.get_page(id=options["page"])
        if options["language"] is None:
            raise ValueError(_("No tesseract language specified"))

        if self.cancel:
            raise CancelledError()

        paths = glob.glob("/usr/share/tesseract-ocr/*/tessdata")
        if not paths:
            request.error(_("tessdata directory not found"))
        with tesserocr.PyTessBaseAPI(lang=options["language"], path=paths[-1]) as api:
            output = "image_out"
            api.SetVariable("tessedit_create_hocr", "T")
            api.SetVariable("hocr_font_info", "T")
            with tempfile.NamedTemporaryFile(dir=options["dir"], suffix=".png") as file:
                page.image_object.save(file.name)
                _pp = api.ProcessPages(output, file.name)

            # Unnecessary filesystem write/read
            path_hocr = pathlib.Path(output).with_suffix(".hocr")
            hocr = path_hocr.read_text(encoding="utf-8")
            path_hocr.unlink()

            page.import_hocr(hocr)
            page.ocr_flag = True
            page.ocr_time = datetime.datetime.now()

        if self.cancel:
            raise CancelledError()

        request.data(
            {
                "type": "page",
                "row": self.replace_page(
                    page, self.find_page_number_by_page_id(page.id)
                ),
                "replace": page.id,
            }
        )

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
        page = self.get_page(id=options["page"])
        try:
            image = page.image_object
            depth = page.get_depth()

            suffix = ".pbm"
            if depth > 1:
                suffix = ".pnm"

            # Temporary filename for new file
            with tempfile.NamedTemporaryFile(
                dir=options["dir"], suffix=suffix, delete=False
            ) as temp:
                infile = temp.name
                logger.debug(
                    "Writing %s -> %s for unpaper",
                    page.id,
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
                resolution=page.resolution,
                dirty_time=datetime.datetime.now(),  # flag as dirty
            )

            # have to send the 2nd page 1st, as the page_id for the 1st will
            # cease to exist after replacing it
            number = self.find_page_number_by_page_id(page.id)
            if out2:
                new2 = Page(
                    filename=out2.name,
                    dir=options["dir"],
                    delete=True,
                    format="Portable anymap",
                    resolution=page.resolution,
                    dirty_time=datetime.datetime.now(),  # flag as dirty
                )
                request.data(
                    {
                        "type": "page",
                        "row": self.add_page(new2, number + 1),
                        "insert-after": page.id,
                    }
                )
            request.data(
                {
                    "type": "page",
                    "row": self.replace_page(new, number),
                    "replace": page.id,
                }
            )

        except (PermissionError, IOError) as err:
            logger.error("Error creating file in %s: %s", options["dir"], err)
            request.error(f"Error creating file in {options['dir']}: {err}.")

    def import_page(self, **kwargs):
        "import page from file or object"
        callbacks = _note_callbacks(kwargs)
        return self.send("import_page", kwargs, **callbacks)

    def do_import_page(self, request):
        "import page from file or object"
        kwargs = request.args[0]
        pagenum = kwargs["page"]
        page = Page(**kwargs)
        xresolution, yresolution, units = page.get_resolution()
        row = self.add_page(page, pagenum)
        page_id = row[0]
        logger.info(
            "Added page id %s at page number %s with resolution %s,%s,%s",
            page_id,
            pagenum,
            xresolution,
            yresolution,
            units,
        )
        request.data(
            {
                "type": "page",
                "row": row,
            }
        )


def _calculate_crop_tuples(options, image):
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

    return (
        (0, 0, width, height),
        (right, bottom, right + width2, bottom + height2),
        (right, bottom, width2, height2),
    )

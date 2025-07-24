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
import threading
from PIL import ImageStat, ImageEnhance, ImageOps, ImageFilter
from const import THUMBNAIL, APPLICATION_ID, USER_VERSION
from importthread import CancelledError, _note_callbacks
from savethread import SaveThread
from i18n import _
from page import Page
from bboxtree import Bboxtree
import tesserocr
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, GdkPixbuf  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


def _loggerise(vars):
    logger_vars = None
    if vars:
        tuple_flag = False
        if isinstance(vars, tuple):
            tuple_flag = True
        logger_vars = list(vars)
        for i, item in enumerate(logger_vars):
            if isinstance(item, (bytes, bytearray)):
                logger_vars[i] = "binary data"
            elif isinstance(item, (tuple, list)):
                logger_vars[i] = _loggerise(logger_vars[i])
        if tuple_flag:
            logger_vars = tuple(logger_vars)
    return logger_vars


class DocThread(SaveThread):
    "subclass basethread for document"

    heightt = THUMBNAIL
    widtht = THUMBNAIL
    _action_id = 0
    _db = None
    _dir = None
    # number_undo_steps = 10

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

        self.db_files = [
            self._db,
            self._dir / pathlib.Path(self._db.name + "-wal"),
            self._dir / pathlib.Path(self._db.name + "-shm"),
        ]
        self._con = {}
        self._cur = {}
        self._write_tid = None
        self.start()
        mlp = GLib.MainLoop()
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        self.send("create", self._db, finished_callback=lambda x: mlp.quit())
        mlp.run()

    def _connect(self):
        tid = threading.get_native_id()
        if tid not in self._con:
            logger.debug("Connecting to database %s in thread %s", self._db, tid)
            self._con[tid] = sqlite3.connect(self._db)
            self._cur[tid] = self._con[tid].cursor()

    def _execute(self, query, params=None):
        "execute a query on the database"
        self._connect()
        tid = threading.get_native_id()
        logger.debug("_execute(%s, %s) in tid %s", query, _loggerise(params), tid)
        if params is None:
            self._cur[tid].execute(query)
        else:
            self._cur[tid].execute(query, params)

    def _executemany(self, query, params=None):
        "execute a query on the database"
        self._connect()
        tid = threading.get_native_id()
        logger.debug("_executemany(%s, %s) in tid %s", query, _loggerise(params), tid)
        if params is None:
            self._cur[tid].executemany(query)
        else:
            self._cur[tid].executemany(query, params)

    def _fetchone(self):
        "fetch one row from the database"
        tid = threading.get_native_id()
        result = self._cur[tid].fetchone()
        logger.debug("_fetchone() in tid %s returned %s", tid, _loggerise(result))
        return result

    def _fetchall(self):
        "fetch one row from the database"
        tid = threading.get_native_id()
        result = self._cur[tid].fetchall()
        logger.debug("fetchall() in tid %s returned %s", tid, _loggerise(result))
        return result

    def _check_write_tid(self):
        tid = threading.get_native_id()
        if self._write_tid:
            if self._write_tid != tid:
                raise RuntimeError(
                    f"Attempted to write to database with tid {tid}, but the "
                    f"database was created with tid {self._write_tid}"
                )
        else:
            self._write_tid = tid

    def do_create(self, request):
        "open a saved database"
        self._check_write_tid()
        self._db = request.args[0]
        if pathlib.Path(self._db).exists() and os.path.getsize(self._db):
            logger.warning(
                "Database %s already exists, not creating it again", self._db
            )
            self.open(self._db)
            return
        self._execute("PRAGMA journal_mode=WAL")
        self._execute(f"PRAGMA application_id={APPLICATION_ID}")
        self._execute(f"PRAGMA user_version={USER_VERSION}")
        self.isolation_level = "IMMEDIATE"
        self._execute(
            """CREATE TABLE image(
                id INTEGER PRIMARY KEY,
                image BLOB,
                thumb BLOB)"""
        )
        self._execute(
            """CREATE TABLE page(
                id INTEGER PRIMARY KEY,
                image_id INTEGER NOT NULL,
                x_res FLOAT,
                y_res FLOAT,
                std_dev TEXT,
                mean TEXT,
                saved BOOL,
                text TEXT,
                annotations TEXT,
                FOREIGN KEY (image_id) REFERENCES image(id))"""
        )
        self._execute(
            """CREATE TABLE page_order(
                action_id INTEGER NOT NULL,
                row_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                page_id INTEGER NOT NULL,
                FOREIGN KEY (page_id) REFERENCES page(id),
                PRIMARY KEY (action_id, row_id))"""
        )
        self._execute(
            """CREATE TABLE selection(
                action_id INTEGER PRIMARY KEY,
                row_ids TEXT NOT NULL)"""
        )

    def open(self, db):
        "open a saved database"
        self._db = db
        self._connect()
        self._execute("PRAGMA application_id")
        application_id = self._fetchone()
        if application_id and application_id[0]:
            print(f"application_id {application_id}")
            if application_id[0] != APPLICATION_ID:
                raise TypeError("%s is not a gscan2pdf session file", self._db)
        self._execute("PRAGMA user_version")
        user_version = self._fetchone()
        if user_version:
            if user_version[0] > USER_VERSION:
                logger.warning(
                    "%s was created by a newer version of gscan2pdf.", self._db
                )
        self._execute("SELECT MAX(action_id) FROM page_order")
        row = self._fetchone()
        if row:
            self._action_id = row[0]

    def _insert_image(self, page, if_different_from=None):
        "insert an image to the database"
        self._check_write_tid()
        bytes_image = page.to_bytes()
        insert = True
        if if_different_from is not None:
            self._execute(
                "SELECT image, thumb FROM image WHERE id = ?",
                (if_different_from,),
            )
            row = self._fetchone()
            if not row:
                raise ValueError(f"Image id {if_different_from} not found")
            if row[0] == bytes_image:
                insert = False
                thumb = self._bytes_to_pixbuf(row[1])
        if insert:
            thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
            self._execute(
                "INSERT INTO image (id, image, thumb) VALUES (NULL, ?, ?)",
                (
                    bytes_image,
                    self._pixbuf_to_bytes(thumb),
                ),
            )
            return self._cur[threading.get_native_id()].lastrowid, thumb
        return if_different_from, thumb

    def _insert_page(self, page, image_id):
        "insert a page to the database"
        self._check_write_tid()
        x_res, y_res = None, None
        if page.resolution:
            x_res, y_res = page.resolution[0], page.resolution[1]
        self._execute(
            """INSERT INTO page (
                id, image_id, x_res, y_res, mean, std_dev, saved, text, annotations)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                image_id,
                x_res,
                y_res,
                None if page.mean is None else json.dumps(page.mean),
                None if page.std_dev is None else json.dumps(page.std_dev),
                page.saved,
                page.text_layer,
                page.annotations,
            ),
        )
        tid = threading.get_native_id()
        self._con[tid].commit()
        return self._cur[tid].lastrowid

    def add_page(self, page, number=None):
        "add a page to the database"
        self._check_write_tid()
        self._take_snapshot()

        if number is None:
            self._execute(
                "SELECT MAX(page_number) FROM page_order WHERE action_id = ?",
                (self._action_id,),
            )
            number = self._fetchone()[0]
            if number is None:
                number = 1
            else:
                number += 1

        if self.find_row_id_by_page_number(number):
            raise ValueError(f"Page {number} already exists")

        image_id, thumb = self._insert_image(page)
        page_id = self._insert_page(page, image_id)
        self._execute(
            "SELECT MAX(row_id) FROM page_order WHERE action_id = ?",
            (self._action_id,),
        )
        max_row_id = self._fetchone()[0]
        if max_row_id is None:
            max_row_id = -1
        self._execute(
            """INSERT INTO page_order (action_id, row_id, page_number, page_id)
               VALUES (?, ?, ?, ?)""",
            (
                self._action_id,
                max_row_id + 1,
                number,
                page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()
        return number, thumb, page_id

    def replace_page(self, page, number):
        "replace a page in the database"
        self._check_write_tid()
        self._take_snapshot()

        i = self.find_row_id_by_page_number(number)
        if i is None:
            raise ValueError(f"Page {number} does not exist")

        image_id, thumb = self._insert_image(page, if_different_from=page.image_id)
        page_id = self._insert_page(page, image_id)
        self._execute(
            """UPDATE page_order SET page_number = ?, page_id = ?
               WHERE row_id = ? AND action_id = ?""",
            (
                number,
                page_id,
                i,
                self._action_id,
            ),
        )
        self._con[threading.get_native_id()].commit()
        return number, thumb, page_id

    def do_delete_pages(self, request):
        "delete a page from the database"
        self._check_write_tid()
        self._take_snapshot()
        kwargs = request.args[0]

        row_ids = []
        if "numbers" in kwargs:
            for number in kwargs["numbers"]:
                row_id = self.find_row_id_by_page_number(number)
                if row_id is None:
                    raise ValueError(f"Page {kwargs['number']} does not exist")
                row_ids.append(self.find_row_id_by_page_number(number))
        elif "row_ids" in kwargs:
            row_ids = kwargs["row_ids"]
        if not row_ids:
            raise ValueError("Specify either row_id or number")

        self._execute(
            f"""DELETE FROM page_order
                WHERE row_id IN ({", ".join(["?"]*len(row_ids))}) AND action_id = ?""",
            (*row_ids, self._action_id),
        )

        # renumber remaining rows
        self._execute(
            "SELECT row_id, page_id, action_id FROM page_order WHERE action_id = ? ORDER BY row_id",
            (self._action_id,),
        )
        page_order = self._fetchall()
        for i, page in enumerate(page_order):
            page_order[i] = [i, page[1], self._action_id]
        self._executemany(
            "UPDATE page_order SET row_id = ? WHERE page_id = ? AND action_id = ?",
            page_order,
        )
        self._con[threading.get_native_id()].commit()

        request.data(
            {
                "type": "page",
                "remove": row_ids,
            }
        )

    def find_row_id_by_page_number(self, number):
        "find a row id by its page number"
        self._execute(
            "SELECT row_id FROM page_order WHERE page_number = ? AND action_id = ?",
            (number, self._action_id),
        )
        row = self._fetchone()
        if row:
            return row[0]
        return None

    def find_page_number_by_page_id(self, page_id):
        "find a page id by its page number"
        self._execute(
            "SELECT page_number FROM page_order WHERE page_id = ? AND action_id = ?",
            (page_id, self._action_id),
        )
        row = self._fetchone()
        if row:
            return row[0]
        return None

    def page_number_table(self):
        "get data for page number/thumb table"
        self._execute(
            """SELECT page_number, thumb, page_id
               FROM page_order, page, image
               WHERE page_id = page.id AND image_id = image.id AND action_id = ?
               ORDER BY page_number""",
            (self._action_id,),
        )
        rows = []
        for row in self._fetchall():
            rows.append([row[0], self._bytes_to_pixbuf(row[1]), row[2]])
        return rows

    def get_page(self, **kwargs):
        "get a page from the database"
        if "number" in kwargs:
            self._execute(
                """SELECT image, x_res, y_res, mean, std_dev, text, annotations, page.id, image.id
                   FROM page, page_order, image
                   WHERE page.id = page_id
                    AND image_id = image.id
                    AND page_number = ?
                    AND action_id = ?""",
                (kwargs["number"], self._action_id),
            )
        elif "id" in kwargs:
            self._execute(
                """SELECT
                    image, x_res, y_res, mean, std_dev, text, annotations, page_number, image.id
                   FROM page, page_order, image
                   WHERE page.id = page_id
                    AND image_id = image.id
                    AND page_id = ?
                    AND action_id = ?""",
                (kwargs["id"], self._action_id),
            )
        else:
            raise ValueError("Please specify either page number or page id")
        row = self._fetchone()
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
            image_id=row[8],
        )

    def do_clone_pages(self, request):
        "clone pages in the database"
        self._check_write_tid()
        self._take_snapshot()
        kwargs = request.args[0]
        page_ids = kwargs["page_ids"]
        dest = kwargs["dest"]
        self._execute(
            f"""SELECT image_id, x_res, y_res, mean, std_dev, saved, text, annotations FROM page, page_order
                WHERE action_id = ?
                 AND id = page_id
                 AND page_id IN ({", ".join(["?"]*len(page_ids))})""",
            (self._action_id, *page_ids),
        )
        pages = self._fetchall()
        image_ids = [page[0] for page in pages]
        self._execute(
            f"SELECT image, thumb FROM image WHERE id IN ({", ".join(["?"]*len(image_ids))})",
            (*image_ids,),
        )
        images = self._fetchall()
        self._executemany(
            "INSERT INTO image (id, image, thumb) VALUES (NULL, ?, ?)",
            images,
        )
        tid = threading.get_native_id()
        self._execute("SELECT last_insert_rowid()")
        first_image_id = self._fetchone()[0] - len(pages) + 1
        for i, page in enumerate(pages):
            pages[i] = list(pages[i])
            pages[i][0] = first_image_id + i  # new image id
        self._executemany(
            """INSERT INTO page (
                id, image_id, x_res, y_res, mean, std_dev, saved, text, annotations)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
            pages,
        )
        self._execute("SELECT last_insert_rowid()")
        first_page_id = self._fetchone()[0] - len(pages) + 1
        self._execute(
            "SELECT MAX(row_id) FROM page_order WHERE action_id = ?",
            (self._action_id,),
        )
        max_row_id = self._fetchone()[0]

        # if we are not adding the cloned pages to the end, renumber the rows after dest
        if dest <= max_row_id:
            self._execute(
                "SELECT row_id, page_number, page_id, action_id FROM page_order WHERE action_id = ? AND row_id >= ? ORDER BY row_id",
                (self._action_id, dest),
            )
            page_order = self._fetchall()
            for i, page in enumerate(page_order):
                page_order[i] = (
                    page[0] + len(pages),
                    page[1] + len(pages),
                    page[2],
                    self._action_id,
                )
            self._execute(
                "SELECT row_id, page_number, page_id from page_order WHERE action_id = ?",
                (self._action_id,),
            )
            for page in reversed(
                page_order
            ):  # reverse list to prevent numbering conflicts during execution
                self._execute(
                    "UPDATE page_order SET row_id = ?, page_number = ? WHERE page_id = ? AND action_id = ?",
                    page,
                )
            self._execute(
                "SELECT row_id, page_number, page_id from page_order WHERE action_id = ?",
                (self._action_id,),
            )
            self._con[tid].commit()

        new_pages = [
            (self._action_id, dest + i, dest + i + 1, first_page_id + i)
            for i in range(len(pages))
        ]
        self._execute(
            "SELECT row_id, page_number, page_id from page_order WHERE action_id = ?",
            (self._action_id,),
        )
        self._executemany(
            """INSERT INTO page_order (action_id, row_id, page_number, page_id)
               VALUES (?, ?, ?, ?)""",
            new_pages,
        )
        self._con[tid].commit()
        self._execute(
            "SELECT row_id, page_number, page_id from page_order WHERE action_id = ?",
            (self._action_id,),
        )

        self._execute(
            f"""SELECT page_number, thumb, page_id
                          FROM page_order, page, image
                          WHERE action_id = ?
                           AND page_id = page.id
                           AND image_id = image.id
                           AND page_id IN ({", ".join(["?"]*len(new_pages))})""",
            (self._action_id, *[row[3] for row in new_pages]),
        )
        rows = []
        for row in self._fetchall():
            row = list(row)
            row[1] = self._bytes_to_pixbuf(row[1])
            rows.append(row)
        request.data({"type": "page", "new_pages": rows})
        return [dest + i for i in range(len(pages))]

    def _take_snapshot(self):
        "take a snapshot of the current state of the document"
        self._check_write_tid()

        # in case the user has undone one or more actions, before taking a
        # snapshot, remove the redo steps
        self._execute("DELETE FROM page_order WHERE action_id > ?", (self._action_id,))

        # copy page numbers and order to buffer
        self._execute(
            """SELECT row_id, page_number, page_id
                FROM page_order
                WHERE action_id = ?""",
            (self._action_id,),
        )
        snapshot = self._fetchall()
        self._action_id += 1
        snapshot = [(self._action_id, *row) for row in snapshot]
        self._executemany(
            """INSERT INTO page_order (action_id, row_id, page_number, page_id)
               VALUES (?, ?, ?, ?)""",
            snapshot,
        )

        # TODO: implement set number_undo_steps depending on available disk space
        # TODO: after deleting from selection, page_order, also delete rows in
        # page & image that are no longer referenced.
        # delete those outside the undo limit
        # self._execute(
        #     "DELETE FROM page_order WHERE action_id < ?",
        #     (self._action_id - self.number_undo_steps,),
        # )
        self._con[threading.get_native_id()].commit()

    def _get_snapshot(self):
        "fetch the snapshot of the document with the given action id"
        self._execute(
            """SELECT page_number, thumb, page_id
                FROM page_order, page, image
                WHERE action_id = ? AND page_id = page.id AND image_id = image.id
                ORDER BY page_number""",
            (self._action_id,),
        )
        rows = []
        for row in self._fetchall():
            row = list(row)
            row[1] = self._bytes_to_pixbuf(row[1])
            rows.append(row)
        return rows

    def _get_snapshots(self):
        "fetch the snapshot of the document with the given action id"
        self._execute(
            """SELECT action_id, page_number, page_id
                FROM page_order
                ORDER BY action_id, page_number"""
        )
        return self._fetchall()

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
        self._execute("SELECT min(action_id) FROM page_order")
        min_action_id = self._fetchone()[0]
        return min_action_id is not None and min_action_id <= self._action_id

    def can_redo(self):
        "checks whether redo is possible"
        self._execute("SELECT max(action_id) FROM page_order")
        max_action_id = self._fetchone()[0]
        return max_action_id is not None and max_action_id > self._action_id

    def undo(self):
        "restore the state of the last snapshot"
        if not self.can_undo():
            raise StopIteration("No more undo steps possible")

        self._action_id -= 1
        return self._get_snapshot()

    def redo(self):
        "restore the state of the last snapshot"
        if not self.can_redo():
            raise StopIteration("No more redo steps possible")
        self._action_id += 1
        return self._get_snapshot()

    def get_selection(self):
        "get the selected row ids for the current action_id"
        self._execute(
            "SELECT row_ids FROM selection WHERE action_id = ?",
            (self._action_id,),
        )
        row_ids = self._fetchone()
        return json.loads(row_ids[0]) if row_ids else []

    def do_set_selection(self, request):
        "set the selected row ids for the current action_id"
        self._check_write_tid()
        row_ids = json.dumps(request.args[0])
        self._execute(
            """INSERT INTO selection (action_id, row_ids) VALUES (?, ?)
                ON CONFLICT(action_id) DO UPDATE SET row_ids = ?""",
            (self._action_id, row_ids, row_ids),
        )
        self._con[threading.get_native_id()].commit()

    def do_set_saved(self, request):
        "mark given page as saved"
        self._check_write_tid()
        page_id, saved = request.args
        if not isinstance(page_id, list):
            page_id = [page_id]
        self._execute(
            f"UPDATE page SET saved = ? WHERE id IN ({", ".join(["?"]*len(page_id))})",
            (
                saved,
                *page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()

    def pages_saved(self):
        "Check that all pages have been saved"
        self._execute(
            """SELECT COUNT(id)
                FROM page_order, page
                WHERE saved = 0 and page_id = id AND action_id = ?""",
            (self._action_id,),
        )
        return self._fetchone()[0] == 0

    def get_thumb(self, page_id):
        "gets the thumbnail for the given page_id"
        self._execute("SELECT thumb FROM page WHERE id = ?", (page_id,))
        return self._bytes_to_pixbuf(self._fetchone()[0])

    def get_text(self, page_id):
        "gets the text layer for the given page"
        self._execute("SELECT text FROM page WHERE id = ?", (page_id,))
        return self._fetchone()[0]

    def do_set_text(self, request):
        "sets the text layer for the given page"
        self._check_write_tid()
        page_id, text = request.args
        self._execute(
            "UPDATE page SET text = ? WHERE id = ?",
            (
                text,
                page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()

    def get_annotations(self, page_id):
        "gets the annotations layer for the given page"
        self._execute("SELECT annotations FROM page WHERE id = ?", (page_id,))
        return self._fetchone()[0]

    def do_set_annotations(self, request):
        "sets the annotations layer for the given page"
        self._check_write_tid()
        page_id, annotations = request.args
        self._execute(
            "UPDATE page SET annotations = ? WHERE id = ?",
            (
                annotations,
                page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()

    def get_resolution(self, page_id):
        "gets the resolution for the given page"
        self._execute("SELECT x_res, y_res FROM page WHERE id = ?", (page_id,))
        return self._fetchone()

    def do_set_resolution(self, request):
        "sets the resolution for the given page"
        self._check_write_tid()
        page_id, x_res, y_res = request.args
        self._execute(
            "UPDATE page SET x_res = ?, y_res = ? WHERE id = ?",
            (
                x_res,
                y_res,
                page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()

    def get_mean_std_dev(self, page_id):
        "gets the mean and std_dev for the given page"
        self._execute("SELECT mean, std_dev FROM page WHERE id = ?", (page_id,))
        mean, std_dev = self._fetchone()
        mean = json.loads(mean, strict=False)
        std_dev = json.loads(std_dev, strict=False)
        return mean, std_dev

    def do_set_mean_std_dev(self, request):
        "sets the mean and std_dev for the given page"
        self._check_write_tid()
        page_id, mean, std_dev = request.args
        self._execute(
            "UPDATE page SET mean = ?, std_dev = ? WHERE id = ?",
            (
                json.dumps(mean),
                json.dumps(std_dev),
                page_id,
            ),
        )
        self._con[threading.get_native_id()].commit()

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
        if options["angle"] in (-90, 90):
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
            dir=options.get("dir"),
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
        out = tempfile.NamedTemporaryFile(dir=options.get("dir"), suffix=".pnm")
        out2 = None
        options["options"]["command"][-2] = out.name

        index = options["options"]["command"].index("--output-pages")
        if options["options"]["command"][index + 1] == "2":
            out2 = tempfile.NamedTemporaryFile(dir=options.get("dir"), suffix=".pnm")
            options["options"]["command"][-1] = out2.name
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
                dir=options.get("dir"), suffix=suffix
            ) as infile:
                logger.debug(
                    "Writing %s -> %s for unpaper",
                    page.id,
                    infile.name,
                )
                image.save(infile.name)
                options["options"]["command"][-3] = infile.name
                out, out2 = self._run_unpaper_cmd(request)

                # unpaper doesn't change the resolution, so we can safely copy it
                new = Page(
                    filename=out.name,
                    dir=options.get("dir"),
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
                        dir=options.get("dir"),
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

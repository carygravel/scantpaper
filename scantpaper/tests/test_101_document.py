"""Tests for document.py."""

import datetime
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from collections import defaultdict
from unittest.mock import MagicMock, Mock, patch

import config
import gi
import img2pdf
import pytest
from basethread import Request
from const import VERSION
from dialog.scan import Scan
from docthread import DocThread
from document import (
    Document,
    _extract_metadata,
)
from helpers import (
    Proc,
    _program_version,
    collate_metadata,
    exec_command,
    expand_metadata_pattern,
)
from loop_helpers import safe_mainloop
from page import Page
from PIL import Image
from savethread import _bbox2markup, _set_timestamp, prepare_output_metadata

gi.require_version("Gtk", "3.0")

from gi.repository import (  # noqa: E402
    GLib,
    Gtk,
)


def get_page_index_all_callback(_uuid, _process, _message):
    """Callback for get_page_index."""
    assert True, "error in all"


def get_page_index_selected_callback(_uuid, _process, _message):
    """Callback for get_page_index."""
    assert True, "error in selected"


def test_basics(temp_db):
    """Test basics."""
    slist = Document(db=temp_db.name)

    selected = slist.get_page_index("all", get_page_index_all_callback)
    assert selected == [], "no pages"

    slist.get_model().handler_block(slist.row_changed_signal)
    slist.data = [[2, None, None]]

    selected = slist.get_page_index("selected", get_page_index_selected_callback)
    assert selected == [], "none selected"

    slist.select(0)
    get_page_index_selected_callback2 = Mock()
    selected = slist.get_page_index("selected", get_page_index_selected_callback2)
    get_page_index_selected_callback2.assert_not_called()
    assert selected == [0], "selected"

    get_page_index_all_callback2 = Mock()
    selected = slist.get_page_index("all", get_page_index_all_callback2)
    get_page_index_all_callback2.assert_not_called()
    assert selected == [0], "all"

    slist.data = [[1, None, None], [3, None, None], [5, None, None]]

    #########################

    slist.renumber()
    assert (slist.data[0][0], slist.data[1][0], slist.data[2][0]) == (
        1,
        2,
        3,
    ), "renumber makes numbers consecutive"


def test_indexing(temp_db):
    """Test indexing."""
    slist = Document(db=temp_db.name)
    slist.data = [[1, None, None], [6, None, None], [7, None, None], [8, None, None]]
    slist.renumber()
    assert [row[0] for row in slist.data] == [
        1,
        2,
        3,
        4,
    ], "renumber makes numbers consecutive"

    #########################

    slist.data = [
        [1, None, 1],
        [3, None, 2],
        [5, None, 3],
        [7, None, 4],
        [9, None, 5],
        [11, None, 6],
        [13, None, 7],
        [15, None, 8],
        [17, None, 9],
        [19, None, 10],
    ]
    slist.renumber()
    assert [row[0] for row in slist.data] == list(range(1, 11)), (
        "renumber gives consecutive page numbers"
    )
    assert len(slist.data) == 10, "renumber does not create pages"

    #########################

    assert slist.find_page_by_uuid("someuuid") is None, (
        "no warning if a page has no uuid for some reason"
    )

    #########################

    assert list(slist.indices2pages([0, 9])) == [1, 10], "indices2pages"

    #########################

    slist.data = [[1, None, 1], [2, None, 2]]
    slist.select(0)
    slist.data[0][0] = 3
    assert slist.get_selected_indices() == [1], (
        "correctly selected page after manual renumber"
    )


def test_file_dates(temp_txt):
    """Test file dates."""
    options = defaultdict(
        None,
        {
            "path": temp_txt.name,
            "options": {"set_timestamp": True},
            "metadata": {
                "datetime": datetime.datetime(
                    2016,
                    2,
                    10,
                    0,
                    0,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=14)),
                ),
            },
        },
    )
    _set_timestamp(options)
    stb = pathlib.Path(temp_txt.name).stat()
    assert datetime.datetime.fromtimestamp(
        stb.st_mtime, tz=datetime.timezone.utc
    ) == datetime.datetime(2016, 2, 9, 10, 0, 0, tzinfo=datetime.timezone.utc), (
        "timestamp with timezone"
    )


def test_helpers():
    """Test helpers."""
    proc = exec_command([sys.executable, "-c", 'print("a" * 65537)'])
    assert len(proc.stdout) == 65538, "exec_command returns more than 65536 bytes"

    #########################

    assert (
        expand_metadata_pattern(
            template="%Da %Dt %Ds %Dk %DY %Y %Dm %m %Dd %d %H %M %S.%De",
            author="a.n.other",
            title="title",
            subject="subject",
            keywords="keywords",
            docdate=datetime.datetime(
                2016,
                2,
                1,
                tzinfo=datetime.timezone.utc,
            ),
            today_and_now=datetime.datetime(
                1970,
                1,
                12,
                14,
                46,
                39,
                tzinfo=datetime.timezone.utc,
            ),
            extension="png",
        )
        == "a.n.other title subject keywords 2016 1970 02 01 01 12 14 46 39.png"
    ), "expand_metadata_pattern"

    assert (
        expand_metadata_pattern(
            template="%Da %Dt %DY %Y %Dm %m %Dd %d %H %M %S %DH %DM %DS.%De",
            author="a.n.other",
            title="title",
            docdate=datetime.datetime(
                2016,
                2,
                1,
                10,
                11,
                12,
                tzinfo=datetime.timezone.utc,
            ),
            today_and_now=datetime.datetime(
                1970,
                1,
                12,
                14,
                46,
                39,
                tzinfo=datetime.timezone.utc,
            ),
            extension="tif",
        )
        == "a.n.other title 2016 1970 02 01 01 12 14 46 39 10 11 12.tif"
    ), "expand_metadata_pattern with doc time"

    assert (
        expand_metadata_pattern(
            template="%Da %Dt %DY %Y %Dm %m %Dd %d %H %M %S.%De",
            author="a.n.other",
            title="title",
            docdate=datetime.datetime(
                1816,
                2,
                1,
                tzinfo=datetime.timezone.utc,
            ),
            today_and_now=datetime.datetime(
                1970,
                1,
                12,
                14,
                46,
                39,
                tzinfo=datetime.timezone.utc,
            ),
            extension="djvu",
        )
        == "a.n.other title 1816 1970 02 01 01 12 14 46 39.djvu"
    ), "expand_metadata_pattern before 1900"

    assert (
        expand_metadata_pattern(
            template="%Da %Dt %DY %Y %Dm %m %Dd %d %H %M %S.%De",
            convert_whitespace=True,
            author="a.n.other",
            title="title",
            docdate=datetime.datetime(
                2016,
                2,
                1,
                tzinfo=datetime.timezone.utc,
            ),
            today_and_now=datetime.datetime(
                1970,
                1,
                12,
                14,
                46,
                39,
                tzinfo=datetime.timezone.utc,
            ),
            extension="pdf",
        )
        == "a.n.other_title_2016_1970_02_01_01_12_14_46_39.pdf"
    ), "expand_metadata_pattern with underscores"

    #########################

    assert prepare_output_metadata(
        "PDF",
        {
            "datetime": datetime.datetime(
                2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "author": "a.n.other",
            "title": "title",
            "subject": "subject",
            "keywords": "keywords",
        },
    ) == {
        "moddate": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "creator": f"scantpaper v{VERSION}",
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
        "creationdate": datetime.datetime(
            2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc
        ),
    }, "prepare_output_metadata"

    assert prepare_output_metadata(
        "PDF",
        {
            "datetime": datetime.datetime(
                2016, 2, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
            ),
            "author": "a.n.other",
            "title": "title",
            "subject": "subject",
            "keywords": "keywords",
        },
    ) == {
        "moddate": datetime.datetime(
            2016, 2, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        ),
        "creator": f"scantpaper v{VERSION}",
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
        "creationdate": datetime.datetime(
            2016, 2, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        ),
    }, "prepare_output_metadata with tz"

    assert prepare_output_metadata(
        "PDF",
        {
            "datetime": datetime.datetime(
                2016,
                2,
                10,
                19,
                59,
                5,
                tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
            ),
            "author": "a.n.other",
            "title": "title",
            "subject": "subject",
            "keywords": "keywords",
        },
    ) == {
        "moddate": datetime.datetime(
            2016,
            2,
            10,
            19,
            59,
            5,
            tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
        ),
        "creator": f"scantpaper v{VERSION}",
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
        "creationdate": datetime.datetime(
            2016,
            2,
            10,
            19,
            59,
            5,
            tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
        ),
    }, "prepare_output_metadata with time"

    #########################

    settings = {
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
        "datetime offset": datetime.timedelta(days=2, hours=0, minutes=59, seconds=59),
    }
    today_and_now = datetime.datetime(
        2016, 2, 10, 1, 2, 3, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
    )
    assert collate_metadata(settings, today_and_now) == {
        "datetime": datetime.datetime(2016, 2, 12, tzinfo=datetime.timezone.utc),
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
    }, "collate basic metadata"

    settings["use_timezone"] = True
    assert collate_metadata(settings, today_and_now) == {
        "datetime": datetime.datetime(
            2016, 2, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        ),
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
    }, "collate timezone"

    settings["use_time"] = True
    assert collate_metadata(settings, today_and_now) == {
        "datetime": datetime.datetime(
            2016, 2, 12, 2, 2, 2, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        ),
        "author": "a.n.other",
        "title": "title",
        "subject": "subject",
        "keywords": "keywords",
    }, "collate time"

    #########################

    assert _extract_metadata(
        {"format": "Portable Document Format", "datetime": "2016-08-06T02:00:00Z"}
    ) == {
        "datetime": datetime.datetime(
            2016, 8, 6, 2, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=0))
        ),
    }, "_extract_metadata UTC"

    assert _extract_metadata(
        {"format": "Portable Document Format", "datetime": "2016-08-06T02:00:00+02"}
    ) == {
        "datetime": datetime.datetime(
            2016, 8, 6, 2, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        ),
    }, "_extract_metadata UTC+2"

    assert _extract_metadata(
        {"format": "Portable Document Format", "datetime": "2019-01-01T02:00:00+14"}
    ) == {
        "datetime": datetime.datetime(
            2019, 1, 1, 2, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=14))
        ),
    }, "_extract_metadata GMT+14"

    assert not _extract_metadata(
        {"format": "Portable Document Format", "datetime": "non-parsable date"}
    ), "_extract_metadata on error"

    assert not _extract_metadata(
        {"format": "Portable Document Format", "datetime": "non-parsable-string"}
    ), "_extract_metadata on error 2"

    #########################

    assert (
        _program_version(
            "stdout", r"file-(\d+\.\d+)", Proc(0, "file-5.22\nmagic file from", None)
        )
        == "5.22"
    ), "file version"
    assert (
        _program_version(
            "stdout",
            r"Version:\sImageMagick\s([\d.-]+)",
            Proc(0, "Version: ImageMagick 6.9.0-3 Q16", None),
        )
        == "6.9.0-3"
    ), "imagemagick version"
    assert (
        _program_version(
            "stdout",
            r"Version:\\sImageMagick\\s([\\d.-]+)",
            Proc(0, "Version:ImageMagick 6.9.0-3 Q16", None),
        )
        is None
    ), "unable to parse version"
    assert (
        _program_version(
            "stdout",
            r"Version:\\sImageMagick\\s([\\d.-]+)",
            Proc(-1, "", "convert: command not found"),
        )
        is None
    ), "command not found"
    assert (
        _program_version(
            "stdout",
            r"Version:\\sImageMagick\\s([\\d.-]+)",
            Proc(-1, None, "convert: command not found"),
        )
        is None
    ), "catch undefined stdout"

    proc = exec_command(["/command/not/found"])
    assert proc.returncode == -1, "status open3 running unknown command"
    assert proc.stderr == "[Errno 2] No such file or directory: '/command/not/found'", (
        "stderr running unknown command"
    )


def test_bbox2markup():
    """Test _bbox2markup()."""
    assert _bbox2markup(300, 300, 500, [0, 0, 452, 57]) == pytest.approx(
        [0.0, 486.32, 108.48, 486.32, 0.0, 500.0, 108.48, 500.0], abs=0.01
    ), "converted bbox to markup coords"


def test_docthread_basic(temp_db, rose_png, temp_pdf, clean_up_files):
    """Tests for DocThread."""
    with tempfile.NamedTemporaryFile(suffix=".tif") as tif:
        thread = DocThread(db=temp_db.name)
        clean_up_files([tif.name])
        request = Request("get_file_info", (tif.name, None), thread.responses)
        with pytest.raises(FileNotFoundError):
            thread.do_get_file_info(request)

        subprocess.run(["touch", tif.name], check=True)
        request = Request("get_file_info", (tif.name, None), thread.responses)
        with pytest.raises(RuntimeError):
            thread.do_get_file_info(request)

        temp_pdf.write(img2pdf.convert(rose_png))
        temp_pdf.flush()
        request = Request("get_file_info", (temp_pdf.name, None), thread.responses)
        info = thread.do_get_file_info(request)
        del info["datetime"]
        assert info == {
            "format": "Portable Document Format",
            "path": temp_pdf.name,
            "page_size": [70.0, 46.0, "pts"],
            "pages": 1,
        }, "do_get_file_info + pdf"

        info = {
            "format": "Tagged Image File Format",
            "width": [70],
            "height": [46],
            "pages": 1,
        }
        subprocess.run(
            [config.CONVERT_COMMAND, "rose:", tif.name], check=True
        )  # Create test image
        request = Request("get_file_info", (tif.name, None), thread.responses)
        example = thread.do_get_file_info(request)
        del example["path"]
        assert example == info, "do_get_file_info + tiff"

        request = Request("get_file_info", (rose_png, None), thread.responses)
        info = {
            "format": "PNG",
            "path": rose_png,
            "width": [70],
            "height": [46],
            "pages": 1,
        }
        assert thread.do_get_file_info(request) == info, "do_get_file_info + png"

        request = Request(
            "import_file",
            (
                {
                    "info": info,
                    "dir": None,
                },
            ),
            thread.responses,
        )

        # spoof the write thread check
        thread._write_tid = threading.get_native_id()
        thread.do_import_file(request)
        page = thread.get_page(id=1)
        assert isinstance(page, Page), "do_import_file + png"


@pytest.mark.skipif(shutil.which("cjb2") is None, reason="requires cjb2")
def test_docthread_djvu(temp_db, temp_cjb2, temp_djvu, temp_pbm):
    """Tests for djvu DocThread."""
    thread = DocThread(db=temp_db.name)
    subprocess.run([config.CONVERT_COMMAND, "rose:", temp_pbm.name], check=True)
    subprocess.run(["cjb2", temp_pbm.name, temp_cjb2.name], check=True)
    subprocess.run(
        ["djvm", "-c", temp_djvu.name, temp_cjb2.name, temp_cjb2.name], check=True
    )
    request = Request("get_file_info", (temp_djvu.name, None), thread.responses)
    assert thread.do_get_file_info(request) == {
        "format": "DJVU",
        "path": temp_djvu.name,
        "width": [70, 70],
        "height": [46, 46],
        "ppi": [300, 300],
        "pages": 2,
    }, "do_get_file_info + djvu"


def test_db(temp_db):
    """Test database access."""
    thread = DocThread(db=temp_db.name)

    with pytest.raises(StopIteration):
        thread.do_undo(Request("undo", (), thread.responses))

    with pytest.raises(StopIteration):
        thread.do_redo(Request("redo", (), thread.responses))

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    thread.add_page(Page(image_object=Image.new("RGB", (210, 297))))
    page = thread.get_page(id=1)
    assert page.id == 1, "add page"

    thread = DocThread(db=temp_db.name)
    page = thread.get_page(id=1)
    assert page.id == 1, "load from db"

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    thread.add_page(Page(image_object=Image.new("RGB", (210, 297))))
    request = Request("delete_pages", ({"row_ids": [0]},), thread.responses)
    thread.do_delete_pages(request)
    assert thread.page_number_table()[0][0] == 0, "deleted page"

    page = thread.get_page(id=2)
    assert isinstance(page, Page), "get_page by id"

    result = thread.do_undo(Request("undo", (), thread.responses))
    assert result["snapshot"][0][0] == 1, "undo"

    result = thread.do_redo(Request("redo", (), thread.responses))
    assert result["snapshot"][0][0] == 1, "redo"

    thread.do_set_saved(Request("set_saved", (1, True), thread.responses))
    assert not thread.pages_saved(), "not all pages saved"

    thread.do_set_saved(Request("set_saved", (2, True), thread.responses))
    assert thread.pages_saved(), "all pages saved"

    thread.do_set_text(Request("set_text", (2, "text"), thread.responses))
    assert thread.get_text(2) == "text", "g/set_text()"

    thread.do_set_annotations(Request("set_annotations", (2, "ann"), thread.responses))
    assert thread.get_annotations(2) == "ann", "g/set_annotations()"

    thread.do_set_resolution(
        Request("set_resolution", (2, 299.9, 199.9), thread.responses)
    )
    assert thread.get_resolution(2) == (299.9, 199.9), "g/set_resolution()"

    thread.do_set_mean_std_dev(
        Request("set_mean_std_dev", (2, 2.5, 3.4), thread.responses)
    )
    assert thread.get_mean_std_dev(2) == (2.5, 3.4), "g/set_mean_std_dev()"

    thread.do_set_mean_std_dev(
        Request("set_mean_std_dev", (2, [2.5], [3.4]), thread.responses)
    )
    assert thread.get_mean_std_dev(2) == (
        [2.5],
        [3.4],
    ), "g/set_mean_std_dev() as list"

    request = Request("clone_pages", ({"page_ids": [2], "dest": 1},), thread.responses)
    assert thread.do_clone_pages(request) == [1], "row_ids of cloned pages"
    assert thread.get_text(3) == "text", "text in cloned page"
    assert len(thread.page_number_table()) == 2, "cloned page in page number table"

    request = Request("clone_pages", ({"page_ids": [2], "dest": 0},), thread.responses)
    assert thread.do_clone_pages(request) == [0], "row_ids of inserted pages"
    assert len(thread.page_number_table()) == 3, "inserted page in page number table"

    request = Request("set_selection", ([2],), thread.responses)
    thread.do_set_selection(request)
    assert thread.get_selection() == [2], "g/set_selection"


def test_undo_redo_snapshot_page_numbers(temp_db):
    """Undo and redo snapshots carry 1-based page numbers."""
    thread = DocThread(db=temp_db.name)

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    for _ in range(3):
        thread.add_page(Page(image_object=Image.new("RGB", (70, 46))))

    page_ids = [row[2] for row in thread.page_number_table()]
    request = Request("delete_pages", ({"page_ids": [page_ids[0]]},), thread.responses)
    thread.do_delete_pages(request)

    result = thread.do_undo(Request("undo", (), thread.responses))
    assert [row[0] for row in result["snapshot"]] == [1, 2, 3], "undo"

    result = thread.do_redo(Request("redo", (), thread.responses))
    assert [row[0] for row in result["snapshot"]] == [1, 2], "redo"


def test_do_quit_closes_database_connection(temp_db):
    """Test that do_quit closes the worker thread's database connection."""
    thread = DocThread(db=temp_db.name)
    tid = threading.get_native_id()
    thread._con[tid] = thread._con.get(tid) or sqlite3.connect(temp_db.name)
    assert tid in thread._con, "connection present"

    request = Request("quit", (), thread.responses)
    thread.do_quit(request)

    assert tid not in thread._con, "connection closed after quit"


def test_reorder_pages(temp_db):
    """Reorder pages via do_reorder_pages."""
    thread = DocThread(db=temp_db.name)

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    for _ in range(5):
        thread.add_page(Page(image_object=Image.new("RGB", (70, 46))))

    ids = [row[2] for row in thread.page_number_table()]

    # image row count should be unchanged by a reorder
    thread._execute("SELECT COUNT(*) FROM image")
    image_count_before = thread._fetchone()[0]

    # move the first page to the end (after the last page)
    request = Request(
        "reorder_pages",
        ({"page_ids": [ids[0]], "dest": 5},),
        thread.responses,
    )
    thread.do_reorder_pages(request)

    after = [row[2] for row in thread.page_number_table()]
    assert after == [*ids[1:], ids[0]], "first page moved to the end"

    thread._execute("SELECT COUNT(*) FROM image")
    image_count_after = thread._fetchone()[0]
    assert image_count_after == image_count_before, "no image duplication on reorder"

    # a single undo restores the original order
    result = thread.do_undo(Request("undo", (), thread.responses))
    assert [row[2] for row in result["snapshot"]] == ids, "single undo restores order"


def test_reorder_pages_block(temp_db):
    """Reorder a block of pages preserving relative order."""
    thread = DocThread(db=temp_db.name)

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    for _ in range(5):
        thread.add_page(Page(image_object=Image.new("RGB", (70, 46))))

    ids = [row[2] for row in thread.page_number_table()]

    # move the middle two pages to the end as a block
    request = Request(
        "reorder_pages",
        ({"page_ids": [ids[1], ids[2]], "dest": 5},),
        thread.responses,
    )
    thread.do_reorder_pages(request)

    after = [row[2] for row in thread.page_number_table()]
    assert after == [ids[0], ids[3], ids[4], ids[1], ids[2]], "block preserved order"


def test_reorder_pages_consecutive_numbering(temp_db):
    """Reorder keeps page numbers consecutive."""
    thread = DocThread(db=temp_db.name)

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    for _ in range(4):
        thread.add_page(Page(image_object=Image.new("RGB", (70, 46))))

    ids = [row[2] for row in thread.page_number_table()]

    # move the last page to the front
    request = Request(
        "reorder_pages",
        ({"page_ids": [ids[3]], "dest": 0},),
        thread.responses,
    )
    thread.do_reorder_pages(request)

    assert [row[0] for row in thread.page_number_table()] == [
        0,
        1,
        2,
        3,
    ], "row ids consecutive after reorder"


def test_reorder_pages_unknown_id(temp_db):
    """Reorder with an id no longer present returns the current order unchanged."""
    thread = DocThread(db=temp_db.name)

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    for _ in range(4):
        thread.add_page(Page(image_object=Image.new("RGB", (70, 46))))

    ids = [row[2] for row in thread.page_number_table()]
    before = [row[2] for row in thread.page_number_table()]

    # the frontend asks to reorder an id that is gone from the database
    request = Request(
        "reorder_pages",
        ({"page_ids": [999999], "dest": 0},),
        thread.responses,
    )
    thread.do_reorder_pages(request)

    after = [row[2] for row in thread.page_number_table()]
    assert after == before, "order unchanged when all ids are unknown"
    assert after == ids, "ordering matches the pre-reorder page order"


def test_document(rose_tif):
    """Tests for Document()."""
    with tempfile.TemporaryDirectory() as tempdir:
        slist = Document(dir=tempdir)
        ran_callback = False
        dialog = Scan(title="title", transient_for=Gtk.Window(), document=slist)

        def finished_callback(_result):
            nonlocal ran_callback
            clipboard = slist.copy_selection()

            def step2():
                nonlocal clipboard
                assert slist.data[0][2] != slist.data[1][2], "different uuid"
                assert slist.data[1][0] == 2, "new page is number 2"
                assert slist.get_selected_indices() == [1], "pasted page selected"
                dialog.page_number_start = 3
                clipboard = slist.cut_selection(finished_callback=step3)
                assert len(clipboard) == 1, "cut 1 page to clipboard"

            def step3():
                assert len(slist.data) == 1, "1 page left in list"
                assert slist.get_selected_indices() == [0], (
                    "selection changed to previous page"
                )
                slist.paste_selection(
                    data=[clipboard[0]],
                    dest=0,
                    how=Gtk.TreeViewDropPosition.BEFORE,
                    finished_callback=step4,
                )  # paste page before 1

            def step4():
                assert len(slist.data) == 2, "2 pages now in list"
                assert slist.data[0][0] == 1, "cut page renumbered to page 1"
                assert slist.get_selected_indices() == [1], (
                    "pasted page not selected, as parameter not TRUE"
                )
                assert dialog.page_number_start == 3, "page-number-start after paste"
                slist.select([0, 1])
                assert slist.get_selected_indices() == [0, 1], "selected all pages"

                slist.delete_selection(finished_callback=step5)

            def step5():
                assert len(slist.data) == 0, "deleted all pages"

                def after_undo():
                    assert len(slist.data) == 2, "undo delete"

                    def after_redo():
                        assert len(slist.data) == 0, "redo delete"

                        nonlocal ran_callback
                        ran_callback = True
                        mlp.quit()

                    slist.unundo(finished_callback=after_redo)

                slist.undo(finished_callback=after_undo)

            slist.paste_selection(
                data=[clipboard[0]],
                dest=0,
                how=Gtk.TreeViewDropPosition.AFTER,
                select_new_pages=True,
                finished_callback=step2,
            )  # copy-paste page 1->2

        slist.import_files(paths=[rose_tif], finished_callback=finished_callback)
        mlp = safe_mainloop(5000)
        mlp.run()
        assert ran_callback, "ran finished callback"


def test_delete_all_pages_undo_redo(rose_tif):
    """Tests for Document.delete_all_pages() with undo/redo."""
    with tempfile.TemporaryDirectory() as tempdir:
        slist = Document(dir=tempdir)
        ran_callback = False

        def after_import(_result):
            nonlocal ran_callback
            assert len(slist.data) == 1, "imported 1 page"

            def after_clear():
                assert len(slist.data) == 0, "all pages cleared"
                assert slist.thread.can_undo(), "clear is undoable"
                assert not slist.thread.can_redo(), "nothing to redo after clear"

                def after_undo():
                    assert len(slist.data) == 1, "undo restores cleared pages"
                    assert slist.thread.can_redo(), "redo available after undo"

                    def after_redo():
                        nonlocal ran_callback
                        assert len(slist.data) == 0, "redo clears pages again"
                        assert not slist.thread.can_redo(), "redo exhausted"
                        ran_callback = True
                        mlp.quit()

                    slist.unundo(finished_callback=after_redo)

                slist.undo(finished_callback=after_undo)

            slist.delete_all_pages(finished_callback=after_clear)

        slist.import_files(paths=[rose_tif], finished_callback=after_import)
        mlp = safe_mainloop(5000)
        mlp.run()
        assert ran_callback, "ran finished callback"


def test_issue_74_new_file_then_scan_edit_undo(rose_tif):
    """Issue #74 regression: undo after New File must not resurrect old pages."""
    with tempfile.TemporaryDirectory() as tempdir:
        slist = Document(dir=tempdir)
        ran_callback = False

        def step2():
            nonlocal ran_callback
            # page B has been scanned; edit it (as the crop tool would)
            b_id = slist.data[0][2]
            edited = Page(image_object=Image.new("RGB", (70, 46), color="blue"))
            slist.thread._write_tid = threading.get_native_id()
            slist.thread.replace_page(edited, b_id)

            def after_undo():
                nonlocal ran_callback
                assert len(slist.data) == 1, "only page B remains after undo"
                assert slist.data[0][2] == b_id, "page A was not resurrected"
                ran_callback = True
                mlp.quit()

            slist.undo(finished_callback=after_undo)

        def after_import_b(_result):
            assert len(slist.data) == 1, "1 page after New File + scan"
            GLib.idle_add(step2)

        def after_clear():
            slist.import_files(paths=[rose_tif], finished_callback=after_import_b)

        def after_import_a(_result):
            assert len(slist.data) == 1, "imported page A"
            slist.delete_all_pages(finished_callback=after_clear)

        slist.import_files(paths=[rose_tif], finished_callback=after_import_a)
        mlp = safe_mainloop(10000)
        mlp.run()
        assert ran_callback, "ran finished callback"


def test_import_files_encrypted():
    """Test import_files with encryption."""
    with patch("basedocument.DocThread") as mockdocthread:
        mockdocthread.return_value._dir = "/tmp"
        doc = Document()
        doc.thread = mockdocthread.return_value

        # Setup mocks
        doc.create_pidfile = MagicMock()

        paths = ["encrypted.pdf"]

        # Scenario:
        # 1. get_file_info called (no password)
        # 2. callback called with encrypted=True
        # 3. password_callback called
        # 4. get_file_info called (with password)

        def get_file_info_side_effect(path, password, **kwargs):
            finished_callback = kwargs["finished_callback"]
            response = MagicMock()
            response.info = {"encrypted": True, "path": path}
            if password == "secret":
                response.info["encrypted"] = False
                response.info["pages"] = 1
                response.info["format"] = "PDF"

            finished_callback(response)

        doc.thread.get_file_info.side_effect = get_file_info_side_effect

        password_callback = MagicMock(return_value="secret")

        doc.import_files(paths=paths, password_callback=password_callback)

        assert password_callback.called
        assert doc.thread.get_file_info.call_count == 2
        # verify second call had password
        args, _ = doc.thread.get_file_info.call_args
        assert args[1] == "secret"


def test_import_files_multiple_errors():
    """Test import_files with multiple files and errors."""
    with patch("basedocument.DocThread") as mockdocthread:
        mockdocthread.return_value._dir = "/tmp"
        doc = Document()
        doc.thread = mockdocthread.return_value
        doc.create_pidfile = MagicMock()

        error_callback = MagicMock()

        # Case 1: Session file mixed
        paths = ["file1", "session.db"]

        def get_file_info_side_effect(path, _password, **kwargs):
            finished_callback = kwargs["finished_callback"]
            response = MagicMock()
            if path == "file1":
                response.info = {"format": "PDF", "pages": 1, "path": path}
            else:
                response.info = {"format": "session file", "pages": 1, "path": path}
            finished_callback(response)

        doc.thread.get_file_info.side_effect = get_file_info_side_effect

        doc.import_files(paths=paths, error_callback=error_callback)

        # Should verify error_callback called
        assert error_callback.called
        args, _ = error_callback.call_args
        assert "session file" in args[2]

        # Case 2: Multipage file mixed
        error_callback.reset_mock()
        doc.thread.get_file_info.reset_mock()
        paths = ["file1", "multipage.pdf"]

        def get_file_info_side_effect_2(path, _password, **kwargs):
            finished_callback = kwargs["finished_callback"]
            response = MagicMock()
            if path == "file1":
                response.info = {"format": "PDF", "pages": 1, "path": path}
            else:
                response.info = {"format": "PDF", "pages": 5, "path": path}
            finished_callback(response)

        doc.thread.get_file_info.side_effect = get_file_info_side_effect_2
        doc.import_files(paths=paths, error_callback=error_callback)

        assert error_callback.called
        args, _ = error_callback.call_args
        assert "multipage file" in args[2]


def test_post_process_chain():
    """Test post process chain."""
    with patch("basedocument.DocThread") as mockdocthread:
        mockdocthread.return_value._dir = "/tmp"
        doc = Document()
        doc.thread = mockdocthread.return_value
        doc.create_pidfile = MagicMock()
        doc.add_page = MagicMock()

        # Methods to mock on doc to verify chain
        doc.rotate = MagicMock()
        doc.unpaper = MagicMock()
        doc.user_defined = MagicMock()
        doc.ocr_pages = MagicMock()

        # 1. Rotate
        # Setup import_scan to trigger callback
        def import_page_side_effect(**kwargs):
            data_callback = kwargs["data_callback"]
            response = MagicMock()
            response.info = {"type": "page", "row": [1, None, "uuid1"]}
            data_callback(response)

        doc.thread.import_page.side_effect = import_page_side_effect

        # Setup rotate to trigger updated_page_callback
        def rotate_side_effect(**kwargs):
            callback = kwargs["updated_page_callback"]
            response = MagicMock()
            response.info = {"type": "page", "row": [1, None, "uuid1"]}
            callback(response)

        doc.rotate.side_effect = rotate_side_effect

        doc.import_scan(resolution=300, rotate=90, finished_callback=MagicMock())

        assert doc.rotate.called
        assert doc.rotate.call_args[1]["angle"] == 90

        # 2. Unpaper
        doc.rotate.reset_mock()
        # Setup unpaper mock object
        mock_unpaper_obj = MagicMock()
        mock_unpaper_obj.get_cmdline.return_value = "unpaper_cmd"
        mock_unpaper_obj.get_option.return_value = "direction"

        def unpaper_side_effect(**kwargs):
            callback = kwargs["updated_page_callback"]
            response = MagicMock()
            response.info = {"type": "page", "row": [1, None, "uuid1"]}
            callback(response)

        doc.unpaper.side_effect = unpaper_side_effect

        doc.import_scan(
            resolution=300, unpaper=mock_unpaper_obj, finished_callback=MagicMock()
        )
        assert doc.unpaper.called

        # 3. UDT
        doc.unpaper.reset_mock()

        def udt_side_effect(**kwargs):
            callback = kwargs["updated_page_callback"]
            response = MagicMock()
            response.info = {"type": "page", "row": [1, None, "uuid1"]}
            callback(response)

        doc.user_defined.side_effect = udt_side_effect

        doc.import_scan(resolution=300, udt="command", finished_callback=MagicMock())
        assert doc.user_defined.called

        # 4. OCR
        doc.user_defined.reset_mock()

        def ocr_side_effect(**kwargs):
            callback = kwargs["finished_callback"]
            callback(None)

        doc.ocr_pages.side_effect = ocr_side_effect

        finished_callback = MagicMock()
        doc.import_scan(
            resolution=300,
            ocr=True,
            engine="tesseract",
            language="eng",
            finished_callback=finished_callback,
        )
        assert doc.ocr_pages.called
        assert finished_callback.called


def test_split_page():
    """Test split_page."""
    with patch("basedocument.DocThread") as mockdocthread:
        mockdocthread.return_value._dir = "/tmp"
        doc = Document()
        doc.thread = mockdocthread.return_value
        doc.add_page = MagicMock()

        def split_page_side_effect(**kwargs):
            data_callback = kwargs["data_callback"]
            response = MagicMock()
            response.info = {"type": "page", "row": [1, None, "uuid1"]}
            data_callback(response)

        doc.thread.split_page.side_effect = split_page_side_effect

        doc.split_page(page=1)
        assert doc.thread.split_page.called
        assert doc.add_page.called


def test_get_selected_properties(temp_db):
    """Test get_selected_properties with multiple pages."""
    slist = Document(db=temp_db.name)

    # spoof the write thread check
    slist.thread._write_tid = threading.get_native_id()

    # Add two pages with same resolution
    img1 = Image.new("RGB", (100, 100))
    p1 = Page(image_object=img1, resolution=(300, 300, "PixelsPerInch"))
    slist.thread.add_page(p1)

    img2 = Image.new("RGB", (100, 100))
    p2 = Page(image_object=img2, resolution=(300, 300, "PixelsPerInch"))
    slist.thread.add_page(p2)

    # Update slist.data
    slist.data = slist.thread.page_number_table()

    # Select both pages
    slist.get_selection().unselect_all()
    slist.select([0, 1])

    # This should call the loops in get_selected_properties
    xres, yres = slist.get_selected_properties()
    assert xres == 300
    assert yres == 300

    # Add a third page with different resolution
    img3 = Image.new("RGB", (100, 100))
    p3 = Page(image_object=img3, resolution=(150, 150, "PixelsPerInch"))
    slist.thread.add_page(p3)
    slist.data = slist.thread.page_number_table()

    # Select first and third pages (different resolutions)
    slist.get_selection().unselect_all()
    slist.select([0, 2])
    xres, yres = slist.get_selected_properties()
    assert xres is None
    assert yres is None

    # Select first and second pages (same resolution) again to be sure
    slist.get_selection().unselect_all()
    slist.select([0, 1])
    xres, yres = slist.get_selected_properties()
    assert xres == 300
    assert yres == 300

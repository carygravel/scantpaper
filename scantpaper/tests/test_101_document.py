"Tests for document.py"

from collections import defaultdict
import datetime
import os
import re
import subprocess
import tempfile
import threading
from PIL import Image
import gi
import pytest
from page import Page
from const import VERSION
from document import (
    Document,
    _extract_metadata,
)
from docthread import DocThread
from dialog.scan import Scan
from basethread import Request
from savethread import prepare_output_metadata, _set_timestamp, _bbox2markup
from helpers import (
    exec_command,
    _program_version,
    Proc,
    expand_metadata_pattern,
    collate_metadata,
    parse_truetype_fonts,
)

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position


def get_page_index_all_callback(_uuid, _process, _message):
    "callback for get_page_index"
    assert True, "error in all"


def get_page_index_selected_callback(_uuid, _process, _message):
    "callback for get_page_index"
    assert True, "error in selected"


def get_page_index_selected_callback2(_uuid, _process, _message):
    "callback for get_page_index"
    assert False, "no error in selected"


def get_page_index_all_callback2(_uuid, _process, _message):
    "callback for get_page_index"
    assert False, "no error in all"


def test_basics(clean_up_files):
    "test basics"
    slist = Document()
    assert (
        slist.pages_possible(1, 1) == -1
    ), "pages_possible infinite forwards in empty document"
    assert (
        slist.pages_possible(2, -1) == 2
    ), "pages_possible finite backwards in empty document"
    assert (
        slist.pages_possible(1, -2) == 1
    ), "pages_possible finite backwards in empty document #2"

    selected = slist.get_page_index("all", get_page_index_all_callback)
    assert selected == [], "no pages"

    slist.get_model().handler_block(slist.row_changed_signal)
    slist.data = [[2, None, None]]

    selected = slist.get_page_index("selected", get_page_index_selected_callback)
    assert selected == [], "none selected"

    slist.select(0)
    selected = slist.get_page_index("selected", get_page_index_selected_callback2)
    assert selected == [0], "selected"

    selected = slist.get_page_index("all", get_page_index_all_callback2)
    assert selected == [0], "all"
    assert slist.pages_possible(2, 1) == 0, "pages_possible 0 due to existing page"
    assert (
        slist.pages_possible(1, 1) == 1
    ), "pages_possible finite forwards in non-empty document"
    assert (
        slist.pages_possible(1, -1) == 1
    ), "pages_possible finite backwards in non-empty document"

    slist.data[0][0] = 1
    assert (
        slist.pages_possible(2, 1) == -1
    ), "pages_possible infinite forwards in non-empty document"

    slist.data = [[1, None, None], [2, None, None], [3, None, None]]
    assert (
        slist.pages_possible(2, -2) == 0
    ), "pages_possible several existing pages and negative step"

    slist.data = [[1, None, None], [3, None, None], [5, None, None]]
    assert (
        slist.pages_possible(2, 1) == 1
    ), "pages_possible finite forwards starting in middle of range"
    assert (
        slist.pages_possible(2, -1) == 1
    ), "pages_possible finite backwards starting in middle of range"
    assert (
        slist.pages_possible(6, -2) == 3
    ), "pages_possible finite backwards starting at end of range"
    assert (
        slist.pages_possible(2, 2) == -1
    ), "pages_possible infinite forwards starting in middle of range"

    #########################

    assert slist.valid_renumber(1, 1, "all"), "valid_renumber all step 1"
    assert slist.valid_renumber(3, -1, "all"), "valid_renumber all start 3 step -1"
    assert (
        slist.valid_renumber(2, -1, "all") is False
    ), "valid_renumber all start 2 step -1"

    slist.select(0)
    assert slist.valid_renumber(1, 1, "selected"), "valid_renumber selected ok"
    assert (
        slist.valid_renumber(3, 1, "selected") is False
    ), "valid_renumber selected nok"

    #########################

    slist.renumber(1, 1, "all")
    assert (slist.data[0][0], slist.data[1][0], slist.data[2][0]) == (
        1,
        2,
        3,
    ), "renumber start 1 step 1"

    #########################

    clean_up_files(slist.thread.db_files)


def test_indexing(clean_up_files):
    "test indexing"

    slist = Document()
    slist.data = [[1, None, None], [6, None, None], [7, None, None], [8, None, None]]
    assert (
        slist.pages_possible(2, 1) == 4
    ), "pages_possible finite forwards starting in middle of range2"

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
    assert (
        slist.index_for_page(12, 0, 11, 1) == -1
    ), "index_for_page correctly returns no index"
    assert len(slist.data) - 1 == 9, "index_for_page does not inadvertanty create pages"

    #########################

    assert (
        slist.find_page_by_uuid("someuuid") is None
    ), "no warning if a page has no uuid for some reason"

    #########################

    assert list(slist.indices2pages([0, 9])) == [1, 10], "indices2pages"

    #########################

    slist.data = [[1, None, 1], [2, None, 2]]
    slist.select(0)
    slist.get_model().handler_unblock(slist.row_changed_signal)
    slist.data[0][0] = 3
    assert slist.get_selected_indices() == [
        1
    ], "correctly selected page after manual renumber"

    clean_up_files(slist.thread.db_files)


def test_file_dates(clean_up_files):
    "test file dates"
    filename = "test.txt"
    subprocess.run(["touch", filename], check=True)
    options = defaultdict(
        None,
        {
            "path": filename,
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
    _set_timestamp(options)  # pylint: disable=protected-access
    stb = os.stat(filename)
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 9, 10, 0, 0
    ), "timestamp with timezone"

    clean_up_files([filename])


def test_helpers():
    "test helpers"
    proc = exec_command(["fc-list", ":", "family", "style", "file"])
    assert (
        re.search(r"\w+", proc.stdout) is not None
    ), "exec_command produces some output from fc-list"

    proc = exec_command(["perl", "-e", 'print "a" x 65537'])
    assert len(proc.stdout) == 65537, "exec_command returns more than 65537 bytes"

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
        "creator": f"gscan2pdf v{VERSION}",
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
        "creator": f"gscan2pdf v{VERSION}",
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
        "creator": f"gscan2pdf v{VERSION}",
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
            r"Version:\sImageMagick\s([\d.-]+)",
            Proc(0, "Version:ImageMagick 6.9.0-3 Q16", None),
        )
        is None
    ), "unable to parse version"
    assert (
        _program_version(
            "stdout",
            r"Version:\sImageMagick\s([\d.-]+)",
            Proc(-1, "", "convert: command not found"),
        )
        == -1
    ), "command not found"
    assert (
        _program_version(
            "stdout",
            r"Version:\sImageMagick\s([\d.-]+)",
            Proc(-1, None, "convert: command not found"),
        )
        == -1
    ), "catch undefined stdout"

    proc = exec_command(["/command/not/found"])
    assert proc.returncode == -1, "status open3 running unknown command"
    assert (
        proc.stderr == "[Errno 2] No such file or directory: '/command/not/found'"
    ), "stderr running unknown command"


def test_parse_truetype_fonts():
    "test parse_truetype_fonts()"
    fclist = """/usr/share/fonts/Cairo-Light.ttf: Cairo,Cairo Light:style=Light,Regular
/usr/share/fonts/FaustinaVFBeta-Italic.ttf: Faustina VF Beta
"""
    assert parse_truetype_fonts(fclist) == {
        "by_family": {"Cairo": {"Light": "/usr/share/fonts/Cairo-Light.ttf"}},
        "by_file": {"/usr/share/fonts/Cairo-Light.ttf": ("Cairo", "Light")},
    }, "parse_truetype_fonts() only returns fonts for which we have a style"


def test_bbox2markup():
    "test _bbox2markup()"
    assert _bbox2markup(300, 300, 500, [0, 0, 452, 57]) == pytest.approx(
        [0.0, 486.32, 108.48, 486.32, 0.0, 500.0, 108.48, 500.0], abs=0.01
    ), "converted bbox to markup coords"


def test_docthread(temp_db, temp_pbm, temp_png, temp_pdf, clean_up_files):
    "tests for DocThread"

    with tempfile.NamedTemporaryFile(suffix=".tif") as tif:
        thread = DocThread(db=temp_db.name)
        clean_up_files([tif.name])
        with pytest.raises(FileNotFoundError):
            request = Request("get_file_info", (tif.name, None), thread.responses)
            thread.do_get_file_info(request)

        with pytest.raises(RuntimeError):
            subprocess.run(["touch", tif.name], check=True)
            request = Request("get_file_info", (tif.name, None), thread.responses)
            thread.do_get_file_info(request)

        cjb2 = "test.cjb2"
        djvu = "test.djvu"
        subprocess.run(["convert", "rose:", tif.name], check=True)  # Create test image
        subprocess.run(
            ["convert", "rose:", temp_pbm.name], check=True
        )  # Create test image
        subprocess.run(["cjb2", temp_pbm.name, cjb2], check=True)
        subprocess.run(["djvm", "-c", djvu, cjb2, cjb2], check=True)
        request = Request("get_file_info", (djvu, None), thread.responses)
        assert thread.do_get_file_info(request) == {
            "format": "DJVU",
            "path": "test.djvu",
            "width": [70, 70],
            "height": [46, 46],
            "ppi": [300, 300],
            "pages": 2,
        }, "do_get_file_info + djvu"

        subprocess.run(["tiff2pdf", "-o", temp_pdf.name, tif.name], check=True)
        request = Request("get_file_info", (temp_pdf.name, None), thread.responses)
        info = thread.do_get_file_info(request)
        del info["datetime"]
        assert info == {
            "format": "Portable Document Format",
            "path": temp_pdf.name,
            "page_size": [16.8, 11.04, "pts"],
            "pages": 1,
        }, "do_get_file_info + pdf"

        info = {
            "format": "Tagged Image File Format",
            "width": [70],
            "height": [46],
            "pages": 1,
        }
        request = Request("get_file_info", (tif.name, None), thread.responses)
        example = thread.do_get_file_info(request)
        del example["path"]
        assert example == info, "do_get_file_info + tiff"

        subprocess.run(
            ["convert", "rose:", temp_png.name], check=True
        )  # Create test image
        request = Request("get_file_info", (temp_png.name, None), thread.responses)
        info = {
            "format": "PNG",
            "path": temp_png.name,
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

        def get_file_info_callback(response):
            assert (
                response.request.process == "get_file_info"
            ), "get_file_info_finished_callback"
            del response.info["path"]
            assert response.info == info, "get_file_info"

        thread.get_file_info(tif.name, None, finished_callback=get_file_info_callback)
        for _ in range(4):
            thread.monitor(block=True)

        clean_up_files(
            thread.db_files
            + [
                cjb2,
                djvu,
            ]
        )


def test_db(temp_db, clean_up_files):
    "test database access"
    thread = DocThread(db=temp_db.name)

    with pytest.raises(StopIteration):
        thread.undo()

    with pytest.raises(StopIteration):
        thread.redo()

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    thread.add_page(Page(image_object=Image.new("RGB", (210, 297))), 1)
    page = thread.get_page(number=1)
    assert page.id == 1, "add page"

    thread = DocThread(db=temp_db.name)
    page = thread.get_page(number=1)
    assert page.id == 1, "load from db"

    # spoof the write thread check
    thread._write_tid = threading.get_native_id()
    thread.add_page(Page(image_object=Image.new("RGB", (210, 297))), 2)
    request = Request("delete_pages", ({"numbers": [1]},), thread.responses)
    thread.do_delete_pages(request)
    assert thread.page_number_table()[0][0] == 2, "deleted page"

    page = thread.get_page(number=2)
    assert isinstance(page, Page), "get_page by number"

    page = thread.get_page(id=2)
    assert isinstance(page, Page), "get_page by id"

    thread.undo()
    assert thread.page_number_table()[0][0] == 1, "undo"

    thread.redo()
    assert thread.page_number_table()[0][0] == 2, "redo"

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

    clean_up_files(thread.db_files)


def test_document(clean_up_files):
    "tests for Document()"
    tiff = "test.tif"
    subprocess.run(["convert", "rose:", tiff], check=True)  # Create test image

    with tempfile.TemporaryDirectory() as tempdir:
        slist = Document(dir=tempdir)
        ran_callback = False
        dialog = Scan(title="title", transient_for=Gtk.Window(), document=slist)

        def finished_callback(_result):
            nonlocal ran_callback
            ran_callback = True
            clipboard = slist.copy_selection()
            slist.paste_selection(
                data=clipboard[0], dest=0, how="after", select_new_pages=True
            )  # copy-paste page 1->2
            assert slist.data[0][2] != slist.data[1][2], "different uuid"
            assert slist.data[1][0] == 2, "new page is number 2"
            assert slist.get_selected_indices() == [1], "pasted page selected"
            dialog.page_number_start = 3
            clipboard = slist.cut_selection()
            assert len(clipboard) == 1, "cut 1 page to clipboard"
            assert len(slist.data) == 1, "1 page left in list"
            assert slist.get_selected_indices() == [
                0
            ], "selection changed to previous page"
            # TODO = "Don't know how to trigger update of page-number-start from Document"
            # assert dialog.page_number_start== 2,               'page-number-start after cut'
            slist.paste_selection(
                data=clipboard[0], dest=0, how="before"
            )  # paste page before 1
            assert len(slist.data) == 2, "2 pages now in list"
            assert slist.data[0][2] == clipboard[0][2], "cut page pasted at page 1"
            assert slist.data[0][0] == 1, "cut page renumbered to page 1"
            assert slist.get_selected_indices() == [
                1
            ], "pasted page not selected, as parameter not TRUE"
            assert dialog.page_number_start == 3, "page-number-start after paste"
            slist.select([0, 1])
            assert slist.get_selected_indices() == [0, 1], "selected all pages"

            slist.delete_selection()
            assert len(slist.data) == 0, "deleted all pages"

            slist.undo()
            assert len(slist.data) == 2, "undo delete"

            slist.unundo()
            assert len(slist.data) == 0, "redo delete"

            # TODO/FIXME: test drag-and-drop callbacks for move
            # TODO/FIXME: test drag-and-drop callbacks for copy

        slist.import_files(paths=[tiff], finished_callback=finished_callback)
        mlp = GLib.MainLoop()
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()
        assert ran_callback, "ran finished callback"

        clean_up_files(slist.thread.db_files + [tiff])


def test_import_scan(
    temp_pnm,
    clean_up_files,
):  # FIXME: not sure we need this anymore, now we are passed Image objects around
    "test Document.import_scan()"
    pytest.skip("Skip until we are sure we need this")

    slist = Document()

    # build a cropped (i.e. too little data compared with header) pnm
    # to test padding code
    subprocess.run(["convert", "rose:", "test.ppm"], check=True)
    old = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.ppm"]
    )

    # To avoid piping one into the other. See
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    with subprocess.Popen(("convert", "rose:", "-"), stdout=subprocess.PIPE) as rose:
        output = subprocess.check_output(("head", "-c", "-1K"), stdin=rose.stdout)
        rose.wait()
        temp_pnm.write(output)

    asserts = 0
    mlp = GLib.MainLoop()

    def _finished_callback(_response):
        subprocess.run(["convert", slist.data[0][2].filename, "test2.ppm"], check=True)
        assert (
            subprocess.check_output(
                ["identify", "-format", "%m %G %g %z-bit %r", "test2.ppm"]
            )
            == old
        ), "padded pnm imported correctly (as PNG)"
        nonlocal asserts
        asserts += 1
        assert os.path.getsize("test2.ppm") == os.path.getsize(
            "test.ppm"
        ), "padded pnm correct size"
        asserts += 1
        mlp.quit()

    slist.import_scan(
        filename=temp_pnm.name,
        page=1,
        delete=True,
        resolution=70,
        finished_callback=_finished_callback,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 2, "all tests run"

    #########################

    clean_up_files(slist.thread.db_files + ["test.ppm", "test2.ppm"])

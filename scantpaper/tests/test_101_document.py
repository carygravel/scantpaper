"Tests for document.py"
from collections import defaultdict
import re
import os
import datetime
import subprocess
import tempfile
import pytest
from page import Page
from const import VERSION
from document import (
    Document,
    _extract_metadata,
)
from savethread import prepare_output_metadata, _set_timestamp, _bbox2markup
from helpers import (
    exec_command,
    _program_version,
    Proc,
    expand_metadata_pattern,
    collate_metadata,
    parse_truetype_fonts,
)


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


def test_basics():
    "test basics"
    # Gscan2pdf.Translation.set_domain('gscan2pdf')

    # logger = Log.Log4perl.get_logger
    # Gscan2pdf.Document.setup(logger)

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
    assert slist.data == [
        [1, None, None],
        [2, None, None],
        [3, None, None],
    ], "renumber start 1 step 1"

    #########################


def test_indexing():
    "test indexing"

    slist = Document()
    slist.data = [[1, None, None], [6, None, None], [7, None, None], [8, None, None]]
    assert (
        slist.pages_possible(2, 1) == 4
    ), "pages_possible finite forwards starting in middle of range2"

    #########################

    png = "test.png"
    subprocess.run(["convert", "rose:", png], check=True)  # Create test image
    tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    page = Page(filename=png, format="Portable Network Graphics", dir=tempdir.name)
    slist.data = [
        [1, None, page],
        [3, None, page.clone()],
        [5, None, page.clone()],
        [7, None, page.clone()],
        [9, None, page.clone()],
        [11, None, page.clone()],
        [13, None, page.clone()],
        [15, None, page.clone()],
        [17, None, page.clone()],
        [19, None, page.clone()],
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

    slist.data = [[1, None, page], [2, None, page.clone()]]
    slist.select(0)
    slist.get_model().handler_unblock(slist.row_changed_signal)
    slist.data[0][0] = 3
    assert slist.get_selected_indices() == [
        1
    ], "correctly selected page after manual renumber"
    os.remove(png)


def test_file_dates():
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
    os.remove(filename)


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
        "timezone offset": datetime.timedelta(hours=0),
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
        "datetime": [2016, 8, 6, 2, 0, 0],
        "tz": [None, None, None, 0, 0, None, None],
    }, "_extract_metadata"

    assert _extract_metadata(
        {"format": "Portable Document Format", "datetime": "2016-08-06T02:00:00+02"}
    ) == {
        "datetime": [2016, 8, 6, 2, 0, 0],
        "tz": [None, None, None, 2, 0, None, None],
    }, "_extract_metadata"

    assert _extract_metadata(
        {"format": "Portable Document Format", "datetime": "2019-01-01T02:00:00+14"}
    ) == {
        "datetime": [2019, 1, 1, 2, 0, 0],
        "tz": [None, None, None, 14, 0, None, None],
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
    fclist = """/usr/local/share/fonts/Cairo-ExtraLight.ttf: Cairo,Cairo ExtraLight:style=ExtraLight,Regular
/usr/local/share/fonts/FaustinaVFBeta-Italic.ttf: Faustina VF Beta
"""
    assert parse_truetype_fonts(fclist) == {
        "by_family": {
            "Cairo": {"ExtraLight": "/usr/local/share/fonts/Cairo-ExtraLight.ttf"}
        },
        "by_file": {
            "/usr/local/share/fonts/Cairo-ExtraLight.ttf": ("Cairo", "ExtraLight")
        },
    }, "parse_truetype_fonts() only returns fonts for which we have a style"


def test_bbox2markup():
    "test _bbox2markup()"
    assert _bbox2markup(300, 300, 500, [0, 0, 452, 57]) == pytest.approx(
        [0.0, 486.32, 108.48, 486.32, 0.0, 500.0, 108.48, 500.0], abs=0.01
    ), "converted bbox to markup coords"

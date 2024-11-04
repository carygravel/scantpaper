"test dialog.save"

from datetime import date, datetime
from unittest.mock import Mock
from dialog.save import Save
from helpers import exec_command, parse_truetype_fonts
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_basic():
    "basic tests"
    dialog = Save(
        title="title",
        transient_for=Gtk.Window(),
        meta_datetime=date(2017, 1, 1),
        select_datetime=True,
        meta_title="title",
        meta_title_suggestions=["title-suggestion"],
        meta_author="author",
        meta_author_suggestions=["author-suggestion"],
        meta_subject="subject",
        meta_subject_suggestions=["subject-suggestion"],
        meta_keywords="keywords",
        meta_keywords_suggestions=["keyword-suggestion"],
    )
    assert isinstance(dialog, Save)

    assert dialog.meta_datetime == date(  # pylint: disable=comparison-with-callable
        2017, 1, 1
    ), "date"
    assert dialog.meta_author == "author", "author"
    assert dialog.meta_title == "title", "title"
    assert dialog.meta_subject == "subject", "subject"
    assert dialog.meta_keywords == "keywords", "keywords"

    dialog._meta_author_widget.set_text("author2")
    assert dialog.meta_author == "author2", "author from Entry()"


def test_datetime():
    "test datetime"
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
        select_datetime=True,
    )
    assert dialog.meta_datetime == datetime(  # pylint: disable=comparison-with-callable
        2017, 1, 1, 23, 59, 5
    ), "date and time"


def test_now(mocker):
    "test not setting datetime"
    now = datetime(2018, 1, 1, 0, 0, 0)
    mocker.patch("dialog.save.datetime.datetime", Mock(now=Mock(return_value=now)))
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
    )
    assert (
        dialog.meta_datetime == now  # pylint: disable=comparison-with-callable
    ), "now"


def test_fonts():
    "test font functionality"
    # Build a look-up table of all true-type fonts installed
    proc = exec_command(["fc-list", ":", "family", "style", "file"])
    fonts = parse_truetype_fonts(proc.stdout)

    dialog = Save(
        transient_for=Gtk.Window(),
        image_types=[
            ["pdf", "gif", "jpg", "png", "pnm", "ps", "tif", "txt", "hocr", "session"]
        ],
        ps_backends=[["libtiff", "pdf2ps", "pdftops"]],
        available_fonts=fonts,
        pdf_font="/does/not/exist",
    )
    dialog.add_image_type()
    assert dialog.ps_backend == "pdftops", "default ps backend"
    assert dialog.pdf_font != "/does/not/exist", "correct non-existant font"

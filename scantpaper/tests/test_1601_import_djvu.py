"Test importing DjVu"

import os
from pathlib import Path
import re
import subprocess
import tempfile
import shutil
import datetime
import pytest
from gi.repository import GLib
from document import Document
from bboxtree import VERSION
from page import Page


def test_import_djvu(clean_up_files):
    "Test importing DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)
    text = """(page 0 0 2236 3185
  (column 157 3011 1725 3105
    (para 157 3014 1725 3101
      (line 157 3014 1725 3101
        (word 157 3030 241 3095 "Füß—")
        (word 533 3033 645 3099 "LA")
        (word 695 3014 1188 3099 "MARQUISE")
        (word 1229 3034 1365 3098 "DE")
        (word 1409 3031 1725 3101 "GANGE")))))
"""
    with open("text.txt", "w", encoding="utf-8") as fhd:
        fhd.write(text)
    text = """(maparea "" "()" (rect 157 3030 84 65) (hilite #cccf00) (xor))
"""
    with open("ann.txt", "w", encoding="utf-8") as fhd:
        fhd.write(text)
    subprocess.run(
        [
            "djvused",
            "test.djvu",
            "-e",
            "select 1; set-txt text.txt; set-ant ann.txt",
            "-s",
        ],
        check=True,
    )
    text = """Author	"Authör"
Keywords	"Keywörds"
Title	"Titleß"
Subject	"Sübject"
CreationDate	"2018-12-31 13:00:00+01:00"
"""
    with open("text.txt", "w", encoding="utf-8") as fhd:
        fhd.write(text)
    subprocess.run(
        ["djvused", "test.djvu", "-e", "set-meta text.txt", "-s"], check=True
    )

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def started_cb(response):
        nonlocal asserts
        assert response.request.process in ["get_file_info", "import_file"]
        asserts += 1

    def metadata_cb(response):
        assert response["datetime"] == datetime.datetime(
            2018, 12, 31, 13, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))
        ), "datetime"
        assert response["author"] == "Authör", "author"
        assert response["subject"] == "Sübject", "subject"
        assert response["keywords"] == "Keywörds", "keywords"
        assert response["title"] == "Titleß", "title"
        nonlocal asserts
        asserts += 1

    slist.import_files(
        paths=["test.djvu"],
        started_callback=started_cb,
        metadata_callback=metadata_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 3, "callbacks all run"

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "DjVu imported correctly"
    expected = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 2236 3185'>
   <div class='ocr_carea' title='bbox 157 80 1725 174'>
    <p class='ocr_par' title='bbox 157 84 1725 171'>
     <span class='ocr_line' title='bbox 157 84 1725 171'>
      <span class='ocr_word' title='bbox 157 90 241 155'>Füß—</span>
      <span class='ocr_word' title='bbox 533 86 645 152'>LA</span>
      <span class='ocr_word' title='bbox 695 86 1188 171'>MARQUISE</span>
      <span class='ocr_word' title='bbox 1229 87 1365 151'>DE</span>
      <span class='ocr_word' title='bbox 1409 84 1725 154'>GANGE</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    assert page.export_hocr() == expected, "text layer"
    expected = """(maparea "" "()" (rect 157 3030 84 65) (hilite #cccf00) (xor))
"""
    assert page.export_djvu_ann() == expected, "annotation layer"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.jpg",
            "test.djvu",
            "text.txt",
            "ann.txt",
        ]
    )


def test_import_djvu_with_error(clean_up_files):
    "Test importing DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def queued_cb(response):
        nonlocal asserts
        assert response.request.process == "get_file_info", "queued_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o500)  # no write access

    def error_cb(_page, _process, message):
        nonlocal asserts
        assert re.search(r"^Error", message), "error_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o700)  # no write access

    slist.import_files(
        paths=["test.djvu"],
        queued_callback=queued_cb,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "all callbacks run"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.jpg", "test.djvu"]
    )


def mock_import_djvu_txt(self, _text):
    "mock import_djvu_txt method to test error handling"
    raise ValueError("Error parsing djvu text")


def test_import_djvu_with_error2(monkeypatch, clean_up_files):
    "Test importing DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)

    # apply the monkeypatch for Page.import_djvu_txt to mock_import_djvu_txt
    monkeypatch.setattr(Page, "import_djvu_txt", mock_import_djvu_txt)

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def logger_cb(response):
        nonlocal asserts
        assert re.search(r"error", response.status), "error_cb"
        asserts += 1

    slist.import_files(
        paths=["test.djvu"],
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "DjVu imported otherwise correctly"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.jpg", "test.djvu"]
    )


def test_import_multipage_djvu(clean_up_files):
    "Test importing multipage DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)
    subprocess.run(["djvm", "-c", "test2.djvu", "test.djvu", "test.djvu"], check=True)

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def started_cb(response):
        nonlocal asserts
        assert response.request.process in ["get_file_info", "import_file"]
        asserts += 1

    def error_cb(response):
        assert False, "error thrown importing multipage djvu"

    slist.import_files(
        paths=["test2.djvu"],
        started_callback=started_cb,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "callbacks all run"
    assert len(slist.data) == 2, "imported 2 pages"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.jpg",
            "test.djvu",
            "test2.djvu",
        ]
    )

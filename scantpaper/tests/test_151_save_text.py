"Test saving text"

import subprocess
import tempfile
from gi.repository import GLib
from document import Document
from bboxtree import VERSION


def test_save_text(import_in_mainloop, clean_up_files):
    "Test saving text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].text_layer = (
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "The quick brown fox", "depth": 3}]'
    )

    mlp = GLib.MainLoop()
    slist.save_text(
        path="test.txt",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "post_save_hook": "cp %i test2.txt",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", "test.txt"], text=True) == "The quick brown fox"
    ), "saved ASCII"
    assert (
        subprocess.check_output(["cat", "test2.txt"], text=True)
        == "The quick brown fox"
    ), "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.txt", "test2.txt"])


def test_save_no_text(import_in_mainloop, clean_up_files):
    "Test saving text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_text(
        path="test.txt",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "post_save_hook": "cp %i test2.txt",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(["cat", "test.txt"], text=True) == "", "saved ASCII"
    assert (
        subprocess.check_output(["cat", "test2.txt"], text=True) == ""
    ), "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.txt", "test2.txt"])


def test_save_utf8(import_in_mainloop, clean_up_files):
    "Test writing text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].text_layer = (
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
        '"пени способствовала сохранению", "depth": 3}]'
    )

    mlp = GLib.MainLoop()
    slist.save_text(
        path="test.txt",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", "test.txt"], text=True)
        == "пени способствовала сохранению"
    ), "saved ASCII"

    #########################

    clean_up_files(["test.pnm", "test.txt"])


def test_save_hocr_as_text(import_in_mainloop, clean_up_files):
    "Test saving HOCR as text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocr_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocr_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocr_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocr_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)

    mlp = GLib.MainLoop()
    slist.save_text(
        path="test.txt",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", "test.txt"], text=True) == "The quick brown fox"
    ), "saved hOCR"

    #########################

    clean_up_files(["test.pnm", "test.txt"])

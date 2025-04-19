"Test saving a djvu"

import os
import re
import subprocess
import tempfile
import shutil
import codecs
import pytest
from gi.repository import GLib
from document import Document


def test_save_djvu(import_in_mainloop, clean_up_files):
    "Test saving a djvu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.djvu") == 1054, "DjVu created with expected size"
    assert slist.scans_saved() == 1, "pages tagged as saved"

    capture = subprocess.check_output(["identify", "test2.png"], text=True)
    assert re.search(
        r"test2.png PNG 70x46 70x46\+0\+0 8-bit sRGB", capture
    ), "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.djvu", "test2.png"])


def test_save_djvu_text_layer(import_in_mainloop, clean_up_files):
    "Test saving a djvu with text layer"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

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
    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvutxt", "test.djvu"], text=True)
    assert re.search(r"The quick brown fox", capture), "DjVu with expected text"

    #########################

    clean_up_files(["test.pnm", "test.djvu"])


def test_save_djvu_with_hocr(import_in_mainloop, clean_up_files):
    "Test saving a djvu with text layer from HOCR"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    hocr = """<!DOCTYPE html
 PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN
 http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
  <meta content="ocr_line ocr_page" name="ocr-capabilities"/>
  <meta content="en" name="ocr-langs"/>
  <meta content="Latn" name="ocr-scripts"/>
  <meta content="" name="ocr-microformats"/>
  <title>OCR Output</title>
 </head>
 <body>
  <div class="ocr_page" title="bbox 0 0 70 46>
   <p class="ocr_par">
    <span class="ocr_line" title="bbox 10 10 60 11">The quick — brown fox·</span>
   </p>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)
    slist.data[0][2].import_annotations(hocr)
    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvutxt", "test.djvu"], text=True)
    assert re.search(r"The quick — brown fox", capture), "DjVu with expected text"

    capture = subprocess.check_output(
        ["djvused", "test.djvu", "-e", "select 1; print-ant"]
    )
    assert re.search(
        r"The quick — brown fox", codecs.escape_decode(capture)[0].decode("utf-8")
    ), "DjVu with expected annotation"

    #########################

    clean_up_files(["test.pnm", "test.djvu"])


def test_cancel_save_djvu(import_in_mainloop, clean_up_files):
    "Test cancel saving a DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

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

    def finished_callback(_response):
        assert False, "Finished callback"

    mlp = GLib.MainLoop()
    called = False

    def cancelled_callback(_response):
        nonlocal called
        called = True
        mlp.quit()

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=finished_callback,
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "Cancelled callback"

    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", "test.jpg"], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    clean_up_files(["test.pnm", "test.djvu", "test.jpg"])


def test_save_djvu_with_error(import_in_mainloop, clean_up_files):
    "Test saving a djvu and triggering an error"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()
    asserts = 0

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    # inject error before save_djvu
    os.chmod(dirname.name, 0o500)  # no write access

    def error_callback1(_page, _process, _message):
        "no write access"
        assert True, "caught error injected before save_djvu"
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        error_callback=error_callback1,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def error_callback2(_page, _process, _message):
        assert True, "save_djvu caught error injected in queue"
        os.chmod(dirname.name, 0o700)  # allow write access
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2]],
        error_callback=error_callback2,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "ran all callbacks"

    #########################

    clean_up_files(["test.pnm", "test.djvu"])


def test_save_djvu_with_float_resolution(import_in_mainloop, clean_up_files):
    "Test saving a djvu with resolution as float"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])
    slist.data[0][2].resolution = 299.72, 299.72, "ppi"

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.djvu") == 1054, "DjVu created with expected size"

    #########################

    clean_up_files(["test.png", "test.djvu"])


def test_save_djvu_different_resolutions(import_in_mainloop, clean_up_files):
    "Test saving a djvu with different resolutions"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "-density", "100x200", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvudump", "test.djvu"], text=True)
    assert re.search(
        r"DjVu 140x46, v24, 200 dpi, gamma=2.2", capture
    ), "created djvu with expect size and resolution"

    #########################

    clean_up_files(["test.png", "test.djvu"])

"Test saving a djvu"

import codecs
import datetime
import os
import re
import shutil
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


def test_save_djvu1(
    import_in_mainloop, rose_pnm, temp_png, temp_db, temp_djvu, clean_up_files
):
    "Test saving a djvu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "convert %i " + temp_png.name,
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize(temp_djvu.name) == 1054, "DjVu created with expected size"
    assert slist.thread.pages_saved(), "pages tagged as saved"

    capture = subprocess.check_output(["identify", temp_png.name], text=True)
    assert re.search(
        rf"{temp_png.name} PNG 70x46 70x46\+0\+0 8-bit sRGB", capture
    ), "ran post-save hook"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_text_layer(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_djvu,
    clean_up_files,
):
    "Test saving a djvu with text layer"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "The quick brown fox", "depth": 3}]',
    )
    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvutxt", temp_djvu.name], text=True)
    assert re.search(r"The quick brown fox", capture), "DjVu with expected text"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_with_hocr(
    import_in_mainloop,
    set_text_in_mainloop,
    set_annotations_in_mainloop,
    rose_pnm,
    temp_db,
    temp_djvu,
    clean_up_files,
):
    "Test saving a djvu with text layer from HOCR"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

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
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)
    page.import_annotations(hocr)
    set_annotations_in_mainloop(slist, 1, page.annotations)
    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvutxt", temp_djvu.name], text=True)
    assert re.search(r"The quick — brown fox", capture), "DjVu with expected text"

    capture = subprocess.check_output(
        ["djvused", temp_djvu.name, "-e", "select 1; print-ant"]
    )
    assert re.search(
        r"The quick — brown fox", codecs.escape_decode(capture)[0].decode("utf-8")
    ), "DjVu with expected annotation"

    #########################

    clean_up_files(slist.thread.db_files)


def test_cancel_save_djvu(
    rose_pnm,
    temp_db,
    temp_jpg,
    import_in_mainloop,
    set_text_in_mainloop,
    temp_djvu,
    clean_up_files,
):
    "Test cancel saving a DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "The quick brown fox", "depth": 3}]',
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
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=finished_callback,
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "Cancelled callback"

    slist.save_image(
        path=temp_jpg.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", temp_jpg.name], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_with_error(rose_pnm, temp_djvu, import_in_mainloop, clean_up_files):
    "Test saving a djvu and triggering an error"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    with tempfile.TemporaryDirectory() as dirname:
        slist = Document(dir=dirname)
        asserts = 0

        import_in_mainloop(slist, [rose_pnm.name])

        # inject error before save_djvu
        os.chmod(dirname, 0o500)  # no write access

        def error_callback1(_page, _process, _message):
            "no write access"
            assert True, "caught error injected before save_djvu"
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = GLib.MainLoop()
        slist.save_djvu(
            path=temp_djvu.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback1,
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        def error_callback2(_page, _process, _message):
            assert True, "save_djvu caught error injected in queue"
            os.chmod(dirname, 0o700)  # allow write access
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = GLib.MainLoop()
        slist.save_djvu(
            path=temp_djvu.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback2,
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert asserts == 2, "ran all callbacks"

        #########################

        clean_up_files(slist.thread.db_files)


def test_save_djvu_with_float_resolution(
    temp_png,
    temp_db,
    temp_djvu,
    import_in_mainloop,
    set_resolution_in_mainloop,
    clean_up_files,
):
    "Test saving a djvu with resolution as float"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", temp_png.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])
    set_resolution_in_mainloop(slist, 1, 299.72, 299.72)

    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize(temp_djvu.name) == 1054, "DjVu created with expected size"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_different_resolutions(
    temp_png, temp_db, temp_djvu, import_in_mainloop, clean_up_files
):
    "Test saving a djvu with different resolutions"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(
        ["convert", "rose:", "-density", "100x200", temp_png.name], check=True
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvudump", temp_djvu.name], text=True)
    assert re.search(
        r"DjVu 140x46, v24, 200 dpi, gamma=2.2", capture
    ), "created djvu with expect size and resolution"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_with_metadata(
    rose_pnm, temp_db, temp_djvu, import_in_mainloop, clean_up_files
):
    "Test saving a djvu with metadata"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    metadata = {
        "datetime": datetime.datetime(2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }
    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    info = subprocess.check_output(
        ["djvused", temp_djvu.name, "-e", "print-meta"], text=True
    )
    assert re.search(r"metadata title", info) is not None, "metadata title in DjVu"
    assert re.search(r"2016-02-10", info) is not None, "metadata ModDate in DjVu"

    stb = os.stat(temp_djvu.name)
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_djvu_with_old_metadata(
    rose_pnm, temp_db, temp_djvu, import_in_mainloop, clean_up_files
):
    "Test saving a djvu with old metadata"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    called = False

    def error_callback(_result):
        nonlocal called
        called = True

    metadata = {
        "datetime": datetime.datetime(1966, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }
    slist.save_djvu(
        path=temp_djvu.name,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
        error_callback=error_callback,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "caught errors setting timestamp"

    info = subprocess.check_output(
        ["djvused", temp_djvu.name, "-e", "print-meta"], text=True
    )
    assert re.search(r"metadata title", info) is not None, "metadata title in DjVu"
    assert re.search(r"1966-02-10", info) is not None, "metadata ModDate in DjVu"

    #########################

    clean_up_files(slist.thread.db_files)

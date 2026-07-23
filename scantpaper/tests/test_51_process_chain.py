"Test process chain"

import subprocess
import shutil
import re
from unittest.mock import MagicMock
import pytest
from gi.repository import GLib
import config
from document import Document
from unpaper import Unpaper
from loop_helpers import safe_mainloop


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_process_chain(temp_db, temp_pnm, clean_up_files, get_page_sync):
    "Test process chain"

    unpaper = Unpaper()
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "-density",
            "300",
            "label:The quick brown fox",
            "-alpha",
            "Off",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-rotate",
            "-90",
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = safe_mainloop(2000)
    slist.import_scan(
        filename=temp_pnm.name,
        page=1,
        rotate=-90,
        unpaper=unpaper,
        ocr=True,
        resolution=300,
        delete=True,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert (
        asserts == 4
    ), "display callback called for import, rotate, unpaper, tesseract"
    page = get_page_sync(slist.thread, number=1)
    assert page.resolution[0] == 300, "Resolution of imported image"

    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_process_chain2(temp_db, temp_pnm, clean_up_files, get_page_sync):
    "Test process chain"

    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "xc:white",
            "-size",
            "210x297",
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)

    mlp = safe_mainloop(2000)
    slist.import_scan(
        filename=temp_pnm.name,
        page=1,
        udt=f"{config.CONVERT_COMMAND} %i -negate %o",
        resolution=300,
        delete=True,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop()
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert page.mean == [0.0], "User-defined with %i and %o"

    #########################

    clean_up_files(slist.thread.db_files)


# FIXME: there is no reason why this can't be made to work on a recent CI. It works locally
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
@pytest.mark.xfail(
    reason="Pillow FreeType glyph metrics broken on CI (getbbox x_min=-19M)"
)
def test_tesseract_in_process_chain_pil(temp_db, rotated_qbfox_pnm, clean_up_files, get_page_sync):
    "Test tesseract in process chain using Pillow-generated image"

    slist = Document(db=temp_db.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        asserts += 1

    mlp = safe_mainloop(5000)
    slist.import_scan(
        filename=rotated_qbfox_pnm,
        page=1,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=True,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 3, "display callback called for import, rotate, tesseract"
    page = get_page_sync(slist.thread, number=1)
    assert page.resolution[0] == 300, "Resolution of imported image"

    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_tesseract_in_process_chain(temp_db, rotated_qbfox_pnm_im, clean_up_files, get_page_sync):
    "Test tesseract in process chain using ImageMagick-generated image"

    slist = Document(db=temp_db.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        asserts += 1

    mlp = safe_mainloop(5000)
    slist.import_scan(
        filename=rotated_qbfox_pnm_im.name,
        page=1,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=True,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 3, "display callback called for import, rotate, tesseract"
    page = get_page_sync(slist.thread, number=1)
    assert page.resolution[0] == 300, "Resolution of imported image"

    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain1(temp_db, rotated_qbfox_pnm, clean_up_files):
    "Test error handling in process chain"

    slist = Document(db=temp_db.name)

    asserts = 0
    mlp = safe_mainloop()

    def started_callback(_response):
        slist.select(0)
        slist.delete_selection()

    def error_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    slist.import_scan(
        filename=rotated_qbfox_pnm,
        page=2,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=False,
        engine="tesseract",
        language="eng",
        started_callback=started_callback,
        error_callback=error_callback,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 1, "Caught error trying to process deleted page"

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain2(temp_db, rotated_qbfox_pnm, clean_up_files):
    "Test error handling in process chain"

    slist = Document(db=temp_db.name)
    mlp = safe_mainloop(5000)
    error_callback = MagicMock()
    slist.import_scan(
        filename=rotated_qbfox_pnm,
        page=2,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=False,
        engine="tesseract",
        language="eng",
        error_callback=error_callback,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    error_callback.assert_not_called()

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain3(temp_db, rotated_qbfox_pnm, clean_up_files):
    "Test error handling in process chain"

    slist = Document(db=temp_db.name)

    asserts = 0
    mlp = safe_mainloop()

    def started_callback(_response):
        slist.select(0)
        slist.delete_selection()

    def finished_or_error_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    options = {
        "filename": rotated_qbfox_pnm,
        "rotate": -90,
        "ocr": True,
        "resolution": 300,
        "delete": False,
        "engine": "tesseract",
        "language": "eng",
        "error_callback": finished_or_error_callback,
        "finished_callback": finished_or_error_callback,
    }
    slist.import_scan(page=1, **options)
    slist.import_scan(page=2, started_callback=started_callback, **options)
    mlp.run()

    assert asserts > 0, "Didn't hang waiting for deleted page"

    clean_up_files(slist.thread.db_files)

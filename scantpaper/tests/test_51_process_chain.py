"Test process chain"

from pathlib import Path
import subprocess
import tempfile
import shutil
import re
import pytest
from gi.repository import GLib
from document import Document
from unpaper import Unpaper


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_process_chain(clean_up_files):
    "Test process chain"

    unpaper = Unpaper()
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            "-rotate",
            "-90",
            "test.pnm",
        ],
        check=True,
    )
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.import_scan(
        filename="test.pnm",
        page=1,
        rotate=-90,
        unpaper=unpaper,
        ocr=True,
        resolution=300,
        delete=True,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        asserts == 4
    ), "display callback called for import, rotate, unpaper, tesseract"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 300, "Resolution of imported image"

    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", "test.pnm"])


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_process_chain2(clean_up_files):
    "Test process chain"

    subprocess.run(
        [
            "convert",
            "-size",
            "210x297",
            "xc:white",
            "white.pnm",
        ],
        check=True,
    )
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()
    slist.import_scan(
        filename="white.pnm",
        page=1,
        udt="convert %i -negate %o",
        resolution=300,
        delete=True,
        dir=dirname.name,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = slist.thread.get_page(number=1)
    assert page.mean == [0.0], "User-defined with %i and %o"

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", "white.pnm"])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_tesseract_in_process_chain(rotated_qbfox_image, clean_up_files):
    "Test tesseract in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        asserts += 1

    mlp = GLib.MainLoop()
    slist.import_scan(
        filename=rotated_qbfox_image,
        page=1,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=True,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 3, "display callback called for import, rotate, tesseract"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 300, "Resolution of imported image"

    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", rotated_qbfox_image])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain1(rotated_qbfox_image, clean_up_files):
    "Test error handling in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0
    mlp = GLib.MainLoop()

    def started_callback(_response):
        slist.select(0)
        slist.delete_selection()

    def error_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    slist.import_scan(
        filename=rotated_qbfox_image,
        page=2,
        to_png=True,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=False,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        started_callback=started_callback,
        error_callback=error_callback,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "Caught error trying to process deleted page"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", rotated_qbfox_image])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain2(rotated_qbfox_image, clean_up_files):
    "Test error handling in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0
    mlp = GLib.MainLoop()

    def error_callback2(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    slist.import_scan(
        filename=rotated_qbfox_image,
        page=2,
        to_png=True,
        rotate=-90,
        ocr=True,
        resolution=300,
        delete=False,
        dir=dirname.name,
        engine="tesseract",
        language="eng",
        error_callback=error_callback2,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 0, "No error thrown"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", rotated_qbfox_image])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_error_in_process_chain3(rotated_qbfox_image, clean_up_files):
    "Test error handling in process chain"

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

    slist = Document()
    slist.set_dir(dirname.name)

    asserts = 0
    mlp = GLib.MainLoop()

    def started_callback(_response):
        slist.select(0)
        slist.delete_selection()

    def error_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    def finished_callback(_response):
        nonlocal asserts
        asserts += 1
        mlp.quit()

    options = {
        "filename": rotated_qbfox_image,
        "to_png": True,
        "rotate": -90,
        "ocr": True,
        "resolution": 300,
        "delete": False,
        "dir": dirname.name,
        "engine": "tesseract",
        "language": "eng",
        "error_callback": error_callback,
        "finished_callback": finished_callback,
    }
    slist.import_scan(page=1, **options)
    slist.import_scan(page=2, started_callback=started_callback, **options)
    GLib.timeout_add(5000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts > 0, "Didn't hang waiting for deleted page"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db", rotated_qbfox_image])

"Test user-defined tools"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_udt(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }

    subprocess.run(["convert", "-size", "210x297", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, ["white.pnm"])

    assert slist.data[0][2].resolution[0] == 25.4, "Resolution of imported image"

    slist.data[0][2].bboxtree = (
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]'
    )

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="convert %i -negate %o",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].mean == [0.0], "User-defined with %i and %o"
    assert slist.data[0][2].resolution[0] == 25.4, "Resolution of converted image"
    assert re.search("ACCOUNT", slist.data[0][2].bboxtree), "OCR output still there"
    assert not slist.scans_saved(), "modification removed saved tag"

    #########################

    clean_up_files(["white.pnm"])


def test_udt_in_place(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    subprocess.run(["convert", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["white.pnm"])

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="convert %i -negate %i",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].mean == [0.0], "User-defined with %i"

    #########################

    clean_up_files(["white.pnm"])


def test_udt_page_size(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }

    subprocess.run(["convert", "-size", "210x297", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, ["white.pnm"])

    assert slist.data[0][2].resolution[0] == 25.4, "Resolution of imported image"

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="convert %i tmp.pbm;mv tmp.pbm %i",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    new = subprocess.check_output(
        ["pdfinfo", "test.pdf"],
        text=True,
    )
    assert re.search("A4", new), "PDF is A4"

    #########################

    clean_up_files(["white.pnm", "test.pdf"])


def test_udt_resolution(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    subprocess.run(["convert", "-size", "210x297", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["white.pnm"])
    slist.data[0][2].resolution = (10, 10, "PixelsPerInch")

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="convert %i tmp.ppm;mv tmp.ppm %i",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert slist.data[0][2].resolution == (
        10,
        10,
        "PixelsPerInch",
    ), "Resolution of converted image taken from input"

    #########################

    clean_up_files(["white.pnm"])


def test_udt_error(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    subprocess.run(["convert", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["white.pnm"])

    asserts = 0

    def logger_cb(response):
        nonlocal asserts
        assert re.search(r"error", response.info["info"]), "error_cb"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="echo error > /dev/stderr;convert %i -negate %i",
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    assert slist.data[0][2].mean == [0.0], "User-defined after error"

    #########################

    clean_up_files(["white.pnm"])

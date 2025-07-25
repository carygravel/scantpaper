"Test unpaper"

import re
import subprocess
import tempfile
import shutil
import pytest
from document import Document
from unpaper import Unpaper
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_version():
    "Test unpaper version"
    unpaper = Unpaper()
    assert unpaper.program_version() is not None, "version"


def test_1():
    "Test unpaper dialog"
    unpaper = Unpaper()

    assert unpaper.get_option("direction") == "ltr", "default direction"

    vbox = Gtk.VBox()
    unpaper.add_options(vbox)
    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "single",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "Basic functionality > 0.3"

    unpaper = Unpaper({"layout": "double"})
    unpaper.add_options(vbox)
    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "double",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "Defaults"

    assert unpaper.get_option("direction") == "ltr", "get_option"

    assert unpaper.get_options() == {
        "no-blackfilter": False,
        "output-pages": 1,
        "no-deskew": False,
        "no-border-scan": False,
        "no-noisefilter": False,
        "no-blurfilter": False,
        "white-threshold": 0.9,
        "layout": "double",
        "no-mask-scan": False,
        "no-mask-center": False,
        "no-grayfilter": False,
        "no-border-align": False,
        "black-threshold": 0.33,
        "deskew-scan-direction": "left,right",
        "border-margin": "0.0,0.0",
        "direction": "ltr",
    }, "get_options"

    #########################

    unpaper = Unpaper(
        {
            "white-threshold": "0.8",
            "black-threshold": "0.35",
        },
    )

    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.35",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "single",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.8",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "no GUI"

    #########################

    unpaper = Unpaper({"layout": "double"})
    unpaper.add_options(vbox)
    unpaper.set_options({"output-pages": 2})

    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "double",
        "--output-pages",
        "2",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "output-pages = 2"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper(temp_pnm, import_in_mainloop, temp_db, clean_up_files):
    "Test unpaper"

    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }
    subprocess.run(
        [
            "convert",
            "-size",
            "210x297",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pnm.name])

    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of processed image"

    #########################

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper2(
    temp_pnm, temp_db, import_in_mainloop, set_resolution_in_mainloop, clean_up_files
):
    "Test unpaper"

    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }
    subprocess.run(
        [
            "convert",
            "-size",
            "255x350",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pnm.name])

    page = slist.thread.get_page(id=1)
    assert page.resolution[0] == 72, "non-standard size pnm imports with 72 PPI"

    set_resolution_in_mainloop(slist, 1, 300, 300)
    page = slist.thread.get_page(id=1)
    assert (
        page.resolution[0] == 300
    ), "simulated having imported non-standard pnm with 300 PPI"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 300, "Resolution of processed image"

    #########################

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper3(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test unpaper"

    unpaper = Unpaper({"output-pages": 2, "layout": "double"})
    subprocess.run(
        [
            "convert",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            "1.pnm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The slower lazy dog",
            "2.pnm",
        ],
        check=True,
    )
    subprocess.run(["convert", "-size", "100x100", "xc:black", "black.pnm"], check=True)
    subprocess.run(
        ["convert", "1.pnm", "black.pnm", "2.pnm", "+append", temp_pnm.name], check=True
    )
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 72, "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 72, "Resolution of 1st page"
    page = slist.thread.get_page(number=2)
    assert page.resolution[0] == 72, "Resolution of 2nd page"

    #########################

    clean_up_files(slist.thread.db_files + ["1.pnm", "black.pnm", "2.pnm"])


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper_rtl(temp_db, import_in_mainloop, clean_up_files):
    "Test unpaper"

    unpaper = Unpaper({"output-pages": 2, "layout": "double", "direction": "rtl"})
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            "1.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The slower lazy dog",
            "2.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "-size",
            "100x100",
            "xc:black",
            "black.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "1.pbm",
            "black.pbm",
            "2.pbm",
            "+append",
            "test.pbm",
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["test.pbm"])

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={
            "command": unpaper.get_cmdline(),
            "direction": unpaper.get_option("direction"),
        },
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "all callbacks run"

    level = []
    for i in [0, 1]:
        with tempfile.NamedTemporaryFile(suffix=".pnm") as filename:
            page = slist.thread.get_page(number=i + 1)
            page.image_object.save(filename.name)
            out = subprocess.check_output(
                [
                    "convert",
                    filename.name,
                    "-depth",
                    "1",
                    "-resize",
                    "1x1",
                    "txt:-",
                ],
                text=True,
            )
        regex = re.search(r"gray\((\d{2,3}(\.\d+)?)%?\)", out)
        assert regex, f"valid PNM created for page {i+1}"
        level.append(regex.group(1))
    assert len(level) == 2 and level[1] > level[0], "rtl"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test.pbm",
            "1.pbm",
            "2.pbm",
            "black.pbm",
        ]
    )

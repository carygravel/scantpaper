"Test unpaper"

import os
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document
from unpaper import Unpaper


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_1(import_in_mainloop):
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
        ["convert", "1.pnm", "black.pnm", "2.pnm", "+append", "test.pnm"], check=True
    )
    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    assert slist.data[0][2].resolution[0] == 72, "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
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
    assert slist.data[0][2].resolution[0] == 72, "Resolution of 1st page"
    assert slist.data[1][2].resolution[0] == 72, "Resolution of 2nd page"

    #########################

    for fname in ["test.pnm", "1.pnm", "black.pnm", "2.pnm"]:
        if os.path.isfile(fname):
            os.remove(fname)

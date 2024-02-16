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
            "test.pnm",
        ],
        check=True,
    )
    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, ["test.pnm"])

    assert (
        slist.data[0][2].resolution[0] == 25.74208754208754
    ), "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2].uuid,
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    assert (
        slist.data[0][2].resolution[0] == 25.74208754208754
    ), "Resolution of process image"

    #########################

    for fname in ["test.pnm"]:
        if os.path.isfile(fname):
            os.remove(fname)

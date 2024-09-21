"Test process chain"

import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skipif(
    shutil.which("unpaper") is None or shutil.which("tesseract") is None,
    reason="requires unpaper and tesseract",
)
def test_1(clean_up_files):
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
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert slist.data[0][2].mean == [0.0, 0.0, 0.0], "User-defined with %i and %o"

    #########################

    clean_up_files(["white.pnm"])

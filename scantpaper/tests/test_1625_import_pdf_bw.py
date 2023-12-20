"Test importing PDF"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1():
    "Test importing PDF"

    options = [
        "convert",
        "+matte",
        "-depth",
        "1",
        "-colorspace",
        "Gray",
        "-type",
        "Bilevel",
        "-family",
        "DejaVu Sans",
        "-pointsize",
        "12",
        "-density",
        "300",
        "label:The quick brown fox",
    ]
    subprocess.run(options + ["test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "test.pdf", "test.tif"], check=True)
    subprocess.run(options + ["test.png"], check=True)
    old = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.png"], text=True
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.pdf"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    new = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", slist.data[0][2].filename],
        text=True,
    )
    assert old == new, "BW PDF imported correctly"

    #########################

    for fname in ["test.tif", "test.png", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

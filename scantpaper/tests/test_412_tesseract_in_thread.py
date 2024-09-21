"Test importing PDF"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test importing PDF"

    args = [
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
        "test.png",
    ]
    subprocess.run(args, check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.tesseract(
        page=slist.data[0][2].uuid,
        language="eng",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    hocr = slist.data[0][2].export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'

    #########################

    clean_up_files(["test.png"])

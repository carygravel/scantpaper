"Test writing PDF with downsampled image"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing PDF with downsampled image"

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
            "test.png",
        ],
        check=True,
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test2.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "downsample": True,
            "downsample dpi": 150,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.pdf") > os.path.getsize(
        "test2.pdf"
    ), "downsampled PDF smaller than original"

    subprocess.run(["pdfimages", "test2.pdf", "x"], check=True)
    example = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "x-000.pbm"], text=True
    )
    assert re.search(
        r"PBM 2\d\dx[23]\d 2\d\dx[23]\d[+]0[+]0 1-bit DirectClass Gray", example
    ), "downsampled"

    #########################

    clean_up_files(["test.png", "test.pdf", "test2.pdf", "x-000.pbm"])

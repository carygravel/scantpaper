"Test importing PDF"

import os
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1():
    "Test importing PDF"

    if shutil.which("pdftk") is None:
        pytest.skip("Please install pdftk to enable test")

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "input.pdf", "test.tif"], check=True)
    subprocess.run(
        [
            "pdftk",
            "input.pdf",
            "output",
            "output.pdf",
            "encrypt_128bit",
            "user_pw",
            "s3cr3t",
        ],
        check=True,
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def password_cb(path):
        nonlocal asserts
        assert path == "output.pdf"
        asserts += 1
        return "s3cr3t"

    slist.import_files(
        paths=["output.pdf"],
        password_callback=password_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "callbacks all run"
    assert len(slist.data) == 1, "imported 1 page"

    #########################

    for fname in ["test.tif", "input.pdf", "output.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

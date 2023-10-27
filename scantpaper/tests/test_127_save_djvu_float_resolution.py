"Test saving a djvu with resolution as float"

import os
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test saving a djvu with resolution as float"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])
    slist.data[0][2].resolution = 299.72, 299.72, "ppi"

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.djvu") == 1054, "DjVu created with expected size"
    assert slist.scans_saved() == 1, "pages tagged as saved"

    #########################

    for fname in ["test.png", "test.djvu"]:
        if os.path.isfile(fname):
            os.remove(fname)

"Test saving a djvu"

import os
import re
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test saving a djvu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2].uuid],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("test.djvu") == 1054, "DjVu created with expected size"
    assert slist.scans_saved() == 1, "pages tagged as saved"

    capture = subprocess.check_output(["identify", "test2.png"], text=True)
    assert re.search(
        r"test2.png PNG 70x46 70x46\+0\+0 8-bit sRGB", capture
    ), "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.djvu", "test2.png"])

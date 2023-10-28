"Test saving a djvu with resolution as float"

import os
import subprocess
import tempfile
import shutil
import re
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test saving a djvu with resolution as float"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "-density", "100x200", "test.png"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["djvudump", "test.djvu"], text=True)
    assert re.search(
        r"DjVu 140x46, v24, 200 dpi, gamma=2.2", capture
    ), "created djvu with expect size and resolution"

    #########################

    for fname in ["test.png", "test.djvu"]:
        if os.path.isfile(fname):
            os.remove(fname)

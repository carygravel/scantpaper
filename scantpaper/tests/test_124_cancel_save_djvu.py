"Test saving a djvu with text layer"

import os
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test saving a djvu with text layer"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].import_text("The quick brown fox")

    def finished_callback(_response):
        assert False, "Finished callback"

    mlp = GLib.MainLoop()
    called = False

    def cancelled_callback(_response):
        nonlocal called
        called = True
        mlp.quit()

    slist.save_djvu(
        path="test.djvu",
        list_of_pages=[slist.data[0][2]],
        finished_callback=finished_callback,
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "Cancelled callback"

    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", "test.jpg"], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    for fname in ["test.pnm", "test.djvu", "test.jpg"]:
        if os.path.isfile(fname):
            os.remove(fname)

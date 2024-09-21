"Test importing DjVu"

import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document


def test_1(clean_up_files):
    "Test importing DjVu"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)
    subprocess.run(["c44", "test.jpg", "test.djvu"], check=True)
    subprocess.run(["djvm", "-c", "test2.djvu", "test.djvu", "test.djvu"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def started_cb(response):
        nonlocal asserts
        assert response.request.process == "get_file_info"
        asserts += 1

    def error_cb(response):
        assert False, "error thrown importing multipage djvu"

    slist.import_files(
        paths=["test2.djvu"],
        started_callback=started_cb,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "callbacks all run"
    assert len(slist.data) == 2, "imported 2 pages"

    #########################

    clean_up_files(["test.jpg", "test.djvu", "test2.djvu"])

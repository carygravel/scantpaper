"Test importing TIFF"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    # inject error during import file
    os.chmod(dirname.name, 0o500)  # allow access

    def error_cb(_page, _process, message):
        nonlocal asserts
        assert re.search(r"^Error", message), "error_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o700)  # allow write access

    slist.import_files(
        paths=["test.tif"],
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def queued_cb(response):
        nonlocal asserts
        assert response.request.process == "get_file_info", "queued_cb"
        asserts += 1

        # inject error during import file
        os.chmod(dirname.name, 0o500)  # no write access

    slist.import_files(
        paths=["test.tif"],
        queued_callback=queued_cb,
        error_callback=error_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 3, "all callbacks run"

    #########################

    clean_up_files(["test.tif"])

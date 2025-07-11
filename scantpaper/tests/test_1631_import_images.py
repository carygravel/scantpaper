"Test importing PPM"

from pathlib import Path
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_import_ppm(temp_db, clean_up_files):
    "Test importing PPM"

    subprocess.run(["convert", "rose:", "test.ppm"], check=True)

    slist = Document(db=temp_db)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.ppm"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    page = slist.thread.get_page(id=1)
    assert page.image_object.mode == "RGB", "PPM imported correctly"

    #########################

    clean_up_files(slist.thread.db_files + ["test.ppm"])


def test_import_corrupt_png(clean_up_files):
    "Test importing PNG"

    subprocess.run(["touch", "test.png"], check=True)

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def error_cb(response):
        nonlocal asserts
        assert (
            response.status == "Error importing zero-length file test.png."
        ), "caught errors importing file"
        asserts += 1
        mlp.quit()

    def finished_cb(response):
        assert False, "caught errors importing file"
        mlp.quit()

    slist.import_files(
        paths=["test.png"],
        error_callback=error_cb,
        finished_callback=finished_cb,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"

    #########################

    clean_up_files(slist.thread.db_files + ["test.png"])

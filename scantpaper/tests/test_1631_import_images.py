"Test importing PPM"

import subprocess
from unittest.mock import MagicMock
from gi.repository import GLib
import config
from document import Document
from loop_helpers import safe_mainloop


def test_import_ppm(temp_db, temp_ppm, get_page_sync):
    "Test importing PPM"

    subprocess.run([config.CONVERT_COMMAND, "rose:", temp_ppm.name], check=True)

    slist = Document(db=temp_db.name)

    mlp = safe_mainloop(2000)

    slist.import_files(
        paths=[temp_ppm.name],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.image_object.mode == "RGB", "PPM imported correctly"


def test_import_corrupt_png(temp_png, temp_db):
    "Test importing PNG"

    slist = Document(db=temp_db.name)

    mlp = safe_mainloop(2000)

    asserts = 0

    def error_cb(response):
        nonlocal asserts
        assert (
            response.status == f"Error importing zero-length file {temp_png.name}."
        ), "caught errors importing file"
        asserts += 1
        mlp.quit()

    finished_cb = MagicMock()

    slist.import_files(
        paths=[temp_png.name],
        error_callback=error_cb,
        finished_callback=finished_cb,
    )
    mlp.run()

    assert asserts == 1, "all callbacks run"
    finished_cb.assert_not_called(), "no finished callback called"

"Test writing basic PDF"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1():
    "Test writing basic PDF"

    # Create test image
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    asserts = 0
    # FIXME: add support from completed, total vars
    #    def import_files_started_cb( thread, process, completed, total ):
    def import_files_started_cb(response):
        nonlocal asserts
        # FIXME: add support for completed/total
        # assert completed== 0, 'completed counter starts at 0'
        # assert total==     2, 'total counter starts at 2'
        assert response.request.process == "get_file_info"
        asserts += 1

    def import_files_finished_cb():
        nonlocal asserts
        assert not slist.scans_saved(), "pages not tagged as saved"
        asserts += 1
        mlp.quit()

    slist.import_files(
        paths=["test.pnm"],
        started_callback=import_files_started_cb,
        finished_callback=import_files_finished_cb,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    # FIXME: add support from completed, total vars
    #    def save_pdf_started_cb( result, completed, total ):
    def save_pdf_started_cb(result):
        nonlocal asserts
        assert result.request.process == "save_pdf", "save_pdf"
        # FIXME: add support for completed/total
        # assert completed== 0, 'completed counter re-initialised'
        # assert total==     1, 'total counter re-initialised'
        asserts += 1

    def save_pdf_finished_cb(result):
        nonlocal asserts
        capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
        assert (
            re.search(r"Page size:\s+70 x 46 pts", capture) is not None
        ), "valid PDF created"
        assert slist.scans_saved(), "pages tagged as saved"
        asserts += 1
        mlp.quit()

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": ["pdftoppm", "%i", "test"],
            "post_save_hook_options": "fg",
        },
        started_callback=save_pdf_started_cb,
        finished_callback=save_pdf_finished_cb,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 4, "ran all callbacks"

    capture = subprocess.check_output(["identify", "test-1.ppm"], text=True)
    assert re.search(
        r"test-1.ppm PPM 146x96 146x96\+0\+0 8-bit sRGB", capture
    ), "ran post-save hook on pdf"

    #########################

    for fname in ["test.pnm", "test.pdf", "test-1.ppm"]:
        if os.path.isfile(fname):
            os.remove(fname)

import os
import re
import subprocess
import gi
from gi.repository import GLib
import logging
import tempfile
from document import Document


def test_1():

    # Create test image
    subprocess.run(["convert","rose:","test.pnm"])

    slist = Document()

    # dir for temporary files
    dir = tempfile.TemporaryDirectory()
    slist.set_dir(dir.name)

    asserts = 0
#    def import_files_started_cb( thread, process, completed, total ):
    def import_files_started_cb( response ):
        print(f"in import_files_started_cb {response}")
        nonlocal asserts
        # assert completed== 0, 'completed counter starts at 0'
        # assert total==     2, 'total counter starts at 2'
        assert response.process == "get_file_info"
        asserts += 1


    def import_files_finished_cb():
        print(f"in import_files_finished_cb")
        nonlocal asserts
        assert not slist.scans_saved(), 'pages not tagged as saved'
        asserts += 1
        mlp.quit()


    slist.import_files(
        paths            = [    'test.pnm'],
        started_callback = import_files_started_cb ,
        finished_callback = import_files_finished_cb ,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def save_pdf_started_cb( thread, process, completed, total ):
        print(f"in save_pdf_started_cb")
        nonlocal asserts
        assert completed== 0, 'completed counter re-initialised'
        assert total==     1, 'total counter re-initialised'
        asserts += 1


    def save_pdf_finished_cb():
        print(f"in save_pdf_finished_cb")
        nonlocal asserts
        capture = subprocess.check_output(["pdfinfo","test.pdf"])
        assert re.search(r"Page size:\s+70 x 46 pts",capture) is not None,             'valid PDF created'
        assert slist.scans_saved()== 1, 'pages tagged as saved'
        asserts += 1
        mlp.quit()


    slist.save_pdf(
        path             = 'test.pdf',
        list_of_pages    = [  slist.data[0][2] ],
        options = {
            "post_save_hook"         : ['pdftoppm', '%i', 'test'],
            "post_save_hook_options" : 'fg',
        },
        started_callback = save_pdf_started_cb ,
        finished_callback = save_pdf_finished_cb ,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["identify","test-1.ppm"], text=True)
    assert re.search(r"test-1.ppm PPM 146x96 146x96\+0\+0 8-bit sRGB",capture),     'ran post-save hook on pdf'
    assert asserts == 4, "ran all callbacks"

#########################

    for fname in ['test.pnm','test.pdf','test-1.ppm']:
        if os.path.isfile(fname):
            os.remove(fname)

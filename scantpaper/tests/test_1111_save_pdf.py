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

# use a new main loop to avoid nesting, which was preventing the counters
# resetting in some environments
#    def import_files_started_cb( thread, process, completed, total ):
    def import_files_started_cb( response ):
        print(f"import_files_started_cb {response}")
        
        # assert completed== 0, 'completed counter starts at 0'
        # assert total==     2, 'total counter starts at 2'
        assert response.process == "get_file_info"


    def import_files_finished_cb():
        assert not slist.scans_saved(), 'pages not tagged as saved'
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
        
        assert completed== 0, 'completed counter re-initialised'
        assert total==     1, 'total counter re-initialised'


    def save_pdf_finished_cb():
        capture = subprocess.check_output(["pdfinfo","test.pdf"])
        assert re.search(r"Page size:\s+70 x 46 pts",capture) is not None,             'valid PDF created'
        assert slist.scans_saved()== 1, 'pages tagged as saved'
        mlp.quit()


    slist.save_pdf(
    path             = 'test.pdf',
    list_of_pages    = [
    slist.data[0][2]["uuid"] ],
    started_callback = save_pdf_started_cb ,
    options = {
        "post_save_hook"         : 'pdftoppm %i test',
        "post_save_hook_options" : 'fg',
    },
    finished_callback = save_pdf_finished_cb 
)
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["identify","test-1.ppm"])
    assert re.search(r"test-1.ppm PPM 146x96 146x96\+0\+0 8-bit sRGB",capture) is not None,     'ran post-save hook on pdf'

#########################

    os.remove('test.pnm','test.pdf','test-1.ppm')   

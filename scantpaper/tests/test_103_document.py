import glob
import os
import subprocess
import tempfile
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from document import Document
import logging


def test_1():

    # Gscan2pdf.Translation.set_domain('gscan2pdf')
    # logger = Log.Log4perl.get_logger
    # Gscan2pdf.Document.setup(logger)

    slist = Document()

    # dir for temporary files
    tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(tempdir)

    # build a cropped (i.e. too little data compared with header) pnm
    # to test padding code
    subprocess.run(["convert","rose:","test.ppm"])
    old = subprocess.run( ["identify","-format", '%m %G %g %z-bit %r', 'test.ppm'], check=True, capture_output=True )

    # To avoid piping one into the other. See
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    # subprocess.run(['convert', 'rose:', '-', '|', "head", "-c", "-1K", ">", 'test.pnm'], shell=True)
    rose = subprocess.Popen(('convert', 'rose:', '-'), stdout=subprocess.PIPE)
    output = subprocess.check_output(("head", "-c", "-1K"), stdin=rose.stdout)
    rose.wait()
    with open("test.pnm", "wb") as image_file:
        image_file.write(output)

    asserts = 0
    def _finished_callback():
        assert False
        subprocess.run([ 'convert', str(slist.data[0][2].filename), 'test2.ppm' ])
        assert subprocess.capture( ["identify","-format"], '%m %G %g %z-bit %r', 'test2.ppm' )==             old,             'padded pnm imported correctly (as PNG)'
        asserts+=1
        assert os.path.getsize('test2.ppm') == os.path.getsize('test.ppm') , 'padded pnm correct size'
        asserts+=1
        ml.quit()

    slist.import_scan(
    filename          = 'test.pnm',
    page              = 1,
    delete            = 1,
    dir               = tempdir,
    finished_callback = _finished_callback 
)
    ml = GLib.MainLoop()
    GLib.timeout_add(2000, ml.quit) # to prevent it hanging
    ml.run()
    assert asserts == 2, "all tests run"

#########################

    for fn in ['test.ppm','test2.ppm','test.pnm']+glob.glob(f"{dir}/*"):
        if os.path.isfile(fn):
            os.remove(fn)    
    os.rmdir(tempdir.name) 
    # Gscan2pdf.Document.quit()


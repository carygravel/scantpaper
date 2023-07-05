"test Document.import_scan()"

import glob
import os
import subprocess
import tempfile
from document import Document
from gi.repository import GLib


def test_import_scan():
    "test Document.import_scan()"

    slist = Document()

    # dir for temporary files
    tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(tempdir)

    # build a cropped (i.e. too little data compared with header) pnm
    # to test padding code
    subprocess.run(["convert", "rose:", "test.ppm"], check=True)
    old = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.ppm"]
    )

    # To avoid piping one into the other. See
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    with subprocess.Popen(("convert", "rose:", "-"), stdout=subprocess.PIPE) as rose:
        # rose = subprocess.Popen(("convert", "rose:", "-"), stdout=subprocess.PIPE)
        output = subprocess.check_output(("head", "-c", "-1K"), stdin=rose.stdout)
        rose.wait()
        with open("test.pnm", "wb") as image_file:
            image_file.write(output)

    asserts = 0

    def _finished_callback():
        subprocess.run(
            ["convert", str(slist.data[0][2].filename), "test2.ppm"], check=True
        )
        assert (
            subprocess.check_output(
                ["identify", "-format", "%m %G %g %z-bit %r", "test2.ppm"]
            )
            == old
        ), "padded pnm imported correctly (as PNG)"
        nonlocal asserts
        asserts += 1
        assert os.path.getsize("test2.ppm") == os.path.getsize(
            "test.ppm"
        ), "padded pnm correct size"
        asserts += 1
        mlp.quit()

    slist.import_scan(
        filename="test.pnm",
        page=1,
        delete=1,
        dir=tempdir,
        finished_callback=_finished_callback,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert asserts == 2, "all tests run"

    #########################

    for fname in ["test.ppm", "test2.ppm", "test.pnm"] + glob.glob(f"{dir}/*"):
        if os.path.isfile(fname):
            os.remove(fname)

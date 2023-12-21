"Test importing PPM"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1():
    "Test importing PPM"

    subprocess.run(["convert", "rose:", "test.ppm"], check=True)
    subprocess.run(["convert", "rose:", "test.png"], check=True)
    old = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.png"], text=True
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["test.ppm"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    new = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", slist.data[0][2].filename],
        text=True,
    )
    assert new == old, "PPM imported correctly"
    assert (
        os.path.dirname(slist.data[0][2].filename) == dirname.name
    ), "using session directory"

    #########################

    for fname in ["test.ppm", "test.png"]:
        if os.path.isfile(fname):
            os.remove(fname)

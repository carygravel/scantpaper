"Test rotating"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test rotating"

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.jpg"])
    slist.data[0][2].saved = True

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.rotate(
        angle=90,
        page=slist.data[0][2].uuid,
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    new = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", slist.data[0][2].filename],
        text=True,
    )
    assert new == "JPEG 46x70 46x70+0+0 8-bit DirectClass sRGB ", "valid JPG created"
    assert (
        os.path.dirname(slist.data[0][2].filename) == dirname.name
    ), "using session directory"
    assert not slist.scans_saved(), "modification removed saved tag"

    #########################

    clean_up_files(["test.jpg"])

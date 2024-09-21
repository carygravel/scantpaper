"Test writing TIFF and triggering an error"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing TIFF and triggering an error"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()
    asserts = 0

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    # inject error before save_djvu
    os.chmod(dirname.name, 0o500)  # no write access

    def error_callback1(_page, _process, _message):
        "no write access"
        assert True, "caught error injected before save_tiff"
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2].uuid],
        error_callback=error_callback1,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    def error_callback2(_page, _process, _message):
        assert True, "save_djvu caught error injected in queue"
        os.chmod(dirname.name, 0o700)  # allow write access
        nonlocal asserts
        asserts += 1
        mlp.quit()

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        error_callback=error_callback2,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "ran all callbacks"

    #########################

    clean_up_files(["test.pnm", "test.tif", "test2.png"])

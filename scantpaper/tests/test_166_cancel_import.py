"Test importing TIFF"

import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test importing TIFF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    old = subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", "test.tif"], text=True
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def finished_cb(response):
        assert False, "TIFF not imported"
        mlp.quit()

    def cancelled_cb(response):
        nonlocal asserts
        assert len(slist.data) == 0, "TIFF not imported"
        asserts += 1
        mlp.quit()

    slist.import_files(
        paths=["test.tif"],
        finished_callback=finished_cb,
    )
    slist.cancel(cancelled_cb)

    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"

    import_in_mainloop(slist, ["test.tif"])
    assert (
        slist.data[0][2].image_object.mode == "RGB"
    ), "TIFF imported correctly after cancelling previous import"

    #########################

    clean_up_files(["test.tif"])

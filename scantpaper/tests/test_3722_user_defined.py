"Test user-defined tools"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    subprocess.run(["convert", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["white.pnm"])

    asserts = 0

    def logger_cb(response):
        nonlocal asserts
        assert re.search(r"error", response.info["info"]), "error_cb"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="echo error > /dev/stderr;convert %i -negate %i",
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.analyse(
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    assert slist.data[0][2].mean == [0.0], "User-defined after error"

    #########################

    clean_up_files(["white.pnm"])

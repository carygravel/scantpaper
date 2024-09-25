"Test convert to PNG"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test convert to PNG"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])
    slist.data[0][2].saved = True
    slist.data[0][2].bboxtree = (
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]'
    )

    mlp = GLib.MainLoop()
    slist.to_png(
        page=slist.data[0][2].uuid,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(
        ["identify", slist.data[0][2].filename], text=True
    )
    assert (
        re.search(r".png PNG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid TIFF created"

    assert re.search("ACCOUNT", slist.data[0][2].bboxtree), "OCR output still there"
    assert (
        os.path.dirname(slist.data[0][2].filename) == dirname.name
    ), "using session directory"
    assert slist.scans_saved(), "modification did not affect saved tag"

    #########################

    clean_up_files(["test.pnm"])

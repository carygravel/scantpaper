"Test threshold"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test threshold"

    subprocess.run(["convert", "rose:", "test.jpg"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.jpg"])
    slist.data[0][2].saved = True
    slist.data[0][2].bboxtree = (
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]'
    )

    mlp = GLib.MainLoop()
    slist.threshold(
        threshold=80,
        page=slist.data[0][2].uuid,
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

    assert len(slist.data[0][2].mean) == 1, "depth == 1"
    assert re.search("ACCOUNT", slist.data[0][2].bboxtree), "OCR output still there"
    assert (
        os.path.dirname(slist.data[0][2].filename) == dirname.name
    ), "using session directory"
    assert not slist.scans_saved(), "modification removed saved tag"

    #########################

    clean_up_files(["test.jpg"])

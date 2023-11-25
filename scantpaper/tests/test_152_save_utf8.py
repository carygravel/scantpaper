"Test writing text"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].text_layer = (
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
        '"пени способствовала сохранению", "depth": 3}]'
    )

    mlp = GLib.MainLoop()
    slist.save_text(
        path="test.txt",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", "test.txt"], text=True)
        == "пени способствовала сохранению"
    ), "saved ASCII"

    #########################

    for fname in ["test.pnm", "test.txt"]:
        if os.path.isfile(fname):
            os.remove(fname)

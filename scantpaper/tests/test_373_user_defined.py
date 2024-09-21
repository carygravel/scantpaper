"Test user-defined tools"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test user-defined tools"

    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }

    subprocess.run(["convert", "-size", "210x297", "xc:white", "white.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, ["white.pnm"])

    assert slist.data[0][2].resolution[0] == 25.4, "Resolution of imported image"

    mlp = GLib.MainLoop()
    slist.user_defined(
        page=slist.data[0][2].uuid,
        command="convert %i tmp.pbm;mv tmp.pbm %i",
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    new = subprocess.check_output(
        ["pdfinfo", "test.pdf"],
        text=True,
    )
    assert re.search("A4", new), "PDF is A4"

    #########################

    clean_up_files(["white.pnm", "test.pdf"])

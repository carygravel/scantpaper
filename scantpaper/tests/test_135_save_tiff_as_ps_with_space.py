"Test writing TIFF and postscript"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing TIFF and postscript"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm", "test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2], slist.data[1][2]],
        options={
            "ps": "te st.ps",
            "post_save_hook": "ps2pdf %i test.pdf",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["file", "te st.ps"], text=True)
    assert (
        example
        == "te st.ps: PostScript document text conforming DSC level 3.0, type EPS, Level 3\n"
    ), "valid postscript created"

    example = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(
            r"tiff2ps",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    for fname in ["test.pnm", "test.tif", "te st.ps", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

"Test writing multipage PDF as Postscript"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm", "test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid, slist.data[1][2].uuid],
        # metadata and timestamp should be ignored: debian #962151
        metadata={},
        options={
            "ps": "te st.ps",
            "pstool": "pdftops",
            "post_save_hook": "cp %i test2.ps",
            "post_save_hook_options": "fg",
            "set_timestamp": True,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("te st.ps") > 15500, "non-empty postscript created"
    assert os.path.getsize("test2.ps") > 15500, "ran post-save hook"

    #########################

    clean_up_files(["test.pnm", "test.pdf", "test2.ps", "te st.ps"])

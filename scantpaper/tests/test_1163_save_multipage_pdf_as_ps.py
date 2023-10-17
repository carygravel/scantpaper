"Test writing multipage PDF as Postscript"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm", "test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2], slist.data[1][2]],
        # metadata and timestamp should be ignored: debian #962151
        metadata={},
        options={
            "ps": "te st.ps",
            "pstool": "pdf2ps",
            "post_save_hook": "cp %i test2.ps",
            "post_save_hook_options": "fg",
            "set_timestamp": True,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert os.path.getsize("te st.ps") > 194000, "non-empty postscript created"
    assert os.path.getsize("test2.ps") > 194000, "ran post-save hook"

    #########################

    for fname in ["test.pnm", "test.pdf", "test2.ps", "te st.ps"]:
        if os.path.isfile(fname):
            os.remove(fname)

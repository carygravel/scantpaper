"test saving an encrypted PDF"

import os
import subprocess
import shutil
import tempfile
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "test saving an encrypted PDF"
    if shutil.which("pdftk") is None:
        pytest.skip("pdftk not found")
        return

    # Create test image
    subprocess.run(["convert", "rose:", "test.jpg"], check=True)

    slist = Document()

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.jpg"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        options={"user-password": "123"},
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(["pdfinfo", "test.pdf"])

    for fname in ["test.jpg", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

"Test writing PDF with old metadata"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing PDF with old metadata"

    pnm = "test.pnm"
    pdf = "test.pdf"
    subprocess.run(["convert", "rose:", pnm], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, [pnm])

    metadata = {"datetime": [1966, 2, 10, 0, 0, 0], "title": "metadata title"}

    called = False

    def error_callback(_result):
        nonlocal called
        called = True

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=pdf,
        list_of_pages=[slist.data[0][2].uuid],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
        error_callback=error_callback,
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "caught errors setting timestamp"

    info = subprocess.check_output(["pdfinfo", "-isodates", pdf], text=True)
    assert (
        re.search(r"1966-02-10T00:00:00Z", info) is not None
    ), "metadata ModDate in PDF"

    #########################

    for fname in [pnm, pdf]:
        if os.path.isfile(fname):
            os.remove(fname)

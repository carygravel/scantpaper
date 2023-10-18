"Test writing PDF with metadata"

import re
import os
import subprocess
import tempfile
import datetime
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing PDF with metadata"

    pnm = "test.pnm"
    pdf = "test.pdf"
    subprocess.run(["convert", "rose:", pnm], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, [pnm])

    metadata = {
        "datetime": [2016, 2, 10, 0, 0, 0],
        "title": "metadata title",
        "subject": "",
    }
    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=pdf,
        list_of_pages=[slist.data[0][2]],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    info = subprocess.check_output(["pdfinfo", "-isodates", pdf], text=True)
    assert re.search(r"metadata title", info) is not None, "metadata title in PDF"

    assert re.search(r"NONE", info) is None, "don't add blank metadata"

    # FIXME: If whichever library we end up has no support for has no support
    # for setting /CreationDate and /ModDate, we can directly modify
    # the PDF:
    # https://stackoverflow.com/questions/52358853/reportlab-metadata-creationdate-and-modificationdate
    # assert re.search(r"2016-02-10T00:00:00Z",info) is not None     ,'metadata ModDate in PDF'
    stb = os.stat(pdf)
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    for fname in [pnm, pdf]:
        if os.path.isfile(fname):
            os.remove(fname)
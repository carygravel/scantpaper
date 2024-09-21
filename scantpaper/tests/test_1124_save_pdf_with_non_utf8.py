"Test writing PDF with non-utf8 in text layer"

import re
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_1(import_in_mainloop, clean_up_files):
    "Test writing PDF with non-utf8 in text layer"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.data[0][2].text_layer = (
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "P�e", "depth": 3}]'
    )
    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    out = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(r"P■e■", out) is not None, "PDF with expected text"

    #########################

    clean_up_files(["test.pnm", "test.pdf"])

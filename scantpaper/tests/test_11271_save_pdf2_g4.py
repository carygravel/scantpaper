"Test writing PDF with group 4 compression"

import os
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skip(
    reason="until we move to fpdf or OCRmyPDF, or solve "
    "https://stackoverflow.com/questions/77202653/"
    "embed-1bpp-image-in-pdf-using-python-and-reportlab"
)
def test_1(import_in_mainloop):
    "Test writing PDF with group 4 compression"

    subprocess.run(
        [
            "convert",
            "rose:",
            "-define",
            "tiff:rows-per-strip=1",
            "-compress",
            "group4",
            "test.tif",
        ],
        check=True,
    )

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    subprocess.run(
        [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=pnggray",
            "-g70x46",
            "-dPDFFitPage",
            "-dUseCropBox",
            "-sOutputFile=test.png",
            "test.pdf",
        ],
        check=True,
    )
    example = subprocess.check_output(
        ["convert", "test.png", "-depth", "1", "-alpha", "off", "txt:-"], text=True
    )
    expected = subprocess.check_output(
        ["convert", "test.tif", "-depth", "1", "-alpha", "off", "txt:-"], text=True
    )
    assert example == expected, "valid G4 PDF created from multi-strip TIFF"

    #########################

    for fname in ["test.tif", "test.png", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

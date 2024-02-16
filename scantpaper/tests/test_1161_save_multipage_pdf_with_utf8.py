"Test writing multipage PDF with utf8"

import re
import os
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_1(import_in_mainloop):
    "Test writing multipage PDF with utf8"

    num = 3  # number of pages
    files = []
    for i in range(num):
        filename = f"{i+1}.pnm"
        subprocess.run(["convert", "rose:", filename], check=True)
        files.append(filename)

    # To avoid piping one into the other. See
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    options = {}
    with subprocess.Popen(
        ("fc-list", ":lang=ru", "file"), stdout=subprocess.PIPE
    ) as fcl:
        with subprocess.Popen(
            ("grep", "ttf"), stdin=fcl.stdout, stdout=subprocess.PIPE
        ) as grep:
            options["font"] = subprocess.check_output(
                ("head", "-n", "1"), stdin=grep.stdout, text=True
            )
            fcl.wait()
            grep.wait()
            options["font"] = options["font"].rstrip()
            options["font"] = re.sub(r":\s*$", r"", options["font"], count=1)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, files)

    pages = []
    for i in range(num):
        slist.data[0][2].text_layer = (
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
            '"пени способствовала сохранению", "depth": 3}]'
        )
        pages.append(slist.data[i][2].uuid)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=pages,
        options={"options": options},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        len(
            re.findall(
                "TrueType", subprocess.check_output(["pdffonts", "test.pdf"], text=True)
            )
        )
        == 1
    ), "font embedded once in multipage PDF"

    #########################

    for fname in ["test.pdf"] + [f"{i+1}.pnm" for i in range(num)]:
        if os.path.isfile(fname):
            os.remove(fname)

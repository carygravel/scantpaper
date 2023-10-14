"Test writing multipage PDF with utf8"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


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
        slist.data[i][2].import_text("пени способствовала сохранению")
        pages.append(slist.data[i][2])

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

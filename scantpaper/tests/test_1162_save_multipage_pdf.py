"Test writing multipage PDF with utf8"

import datetime
import os
from pathlib import Path
import re
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


def test_save_multipage_pdf(import_in_mainloop, clean_up_files):
    "Test writing multipage PDF"

    num = 3  # number of pages
    files = []
    for i in range(1, num + 1):
        filename = f"{i}.pnm"
        subprocess.run(["convert", "rose:", filename], check=True)
        files.append(filename)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, files)

    pages = []
    for i in range(1, num + 1):
        slist.set_text(
            i,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": "hello world", "depth": 3}]',
        )
        pages.append(i)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=pages,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        len(subprocess.check_output(["pdffonts", "test.pdf"], text=True).splitlines())
        < 3
    ), "no fonts embedded in multipage PDF"

    #########################

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pdf"]
        + [f"{i}.pnm" for i in range(1, num + 1)]
    )


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_multipage_pdf_with_utf8(import_in_mainloop, clean_up_files):
    "Test writing multipage PDF with utf8"

    num = 3  # number of pages
    files = []
    for i in range(1, num + 1):
        filename = f"{i}.pnm"
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
    for i in range(1, num + 1):
        slist.set_text(
            i,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
            '"пени способствовала сохранению", "depth": 3}]',
        )
        pages.append(i)

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

    clean_up_files(
        [Path(tempfile.gettempdir()) / "document.db", "test.pdf"]
        + [f"{i}.pnm" for i in range(1, num + 1)]
    )


def test_save_multipage_pdf_as_ps(import_in_mainloop, clean_up_files):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm", "test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[1, 2],
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

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.pdf",
            "test2.ps",
            "te st.ps",
        ]
    )


def test_save_multipage_pdf_as_ps2(import_in_mainloop, clean_up_files):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm", "test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[1, 2],
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

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.pdf",
            "test2.ps",
            "te st.ps",
        ]
    )


def test_prepend_pdf(import_in_mainloop, clean_up_files):
    "Test prepending a page to a PDF"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "test.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[1],
        options={
            "prepend": "test.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("test.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.tif",
            "test.pdf",
            "test.pdf.bak",
        ]
    )


def test_append_pdf(import_in_mainloop, clean_up_files):
    "Test appending a page to a PDF"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "test.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[1],
        options={
            "append": "test.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF appended"
    assert os.path.isfile("test.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.tif",
            "test.pdf",
            "test.pdf.bak",
        ]
    )


def test_prepend_with_space(import_in_mainloop, clean_up_files):
    "Test prepending a page to a PDF with a space"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "te st.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="te st.pdf",
        list_of_pages=[1],
        options={
            "prepend": "te st.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "te st.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("te st.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.tif",
            "te st.pdf",
            "te st.pdf.bak",
        ]
    )


def test_prepend_with_inverted_comma(import_in_mainloop, clean_up_files):
    "Test prepending a page to a PDF"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "te'st.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="te'st.pdf",
        list_of_pages=[1],
        options={
            "prepend": "te'st.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "te'st.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("te'st.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.tif",
            "te'st.pdf",
            "te'st.pdf.bak",
        ]
    )


def test_append_pdf_with_timestamp(import_in_mainloop, clean_up_files):
    "Test appending a page to a PDF with a timestamp"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "test.pdf", "test.tif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[1],
        metadata={
            "datetime": datetime.datetime(
                2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "title": "metadata title",
        },
        options={
            "append": "test.pdf",
            "set_timestamp": True,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture), "PDF appended"
    assert os.path.isfile("test.pdf.bak"), "Backed up original"
    stb = os.stat("test.pdf")
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    clean_up_files(
        [
            Path(tempfile.gettempdir()) / "document.db",
            "test.pnm",
            "test.tif",
            "test.pdf",
            "test.pdf.bak",
        ]
    )

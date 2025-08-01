"Test writing multipage PDF with utf8"

import datetime
import os
import re
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document


def test_save_multipage_pdf(
    import_in_mainloop, set_text_in_mainloop, temp_db, temp_pdf, clean_up_files
):
    "Test writing multipage PDF"

    num = 3  # number of pages
    files = []
    for i in range(1, num + 1):
        filename = f"{i}.pnm"
        subprocess.run(["convert", "rose:", filename], check=True)
        files.append(filename)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, files)

    pages = []
    for i in range(1, num + 1):
        set_text_in_mainloop(
            slist,
            1,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": "hello world", "depth": 3}]',
        )
        pages.append(i)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=pages,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        len(
            subprocess.check_output(["pdffonts", temp_pdf.name], text=True).splitlines()
        )
        < 3
    ), "no fonts embedded in multipage PDF"

    #########################

    clean_up_files(slist.thread.db_files + [f"{i}.pnm" for i in range(1, num + 1)])


@pytest.mark.skip(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_multipage_pdf_with_utf8(
    import_in_mainloop, set_text_in_mainloop, temp_pdf, clean_up_files
):
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

    import_in_mainloop(slist, files)

    pages = []
    for i in range(1, num + 1):
        set_text_in_mainloop(
            slist,
            1,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
            '"пени способствовала сохранению", "depth": 3}]',
        )
        pages.append(i)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=pages,
        options={"options": options},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        len(
            re.findall(
                "TrueType",
                subprocess.check_output(["pdffonts", temp_pdf.name], text=True),
            )
        )
        == 1
    ), "font embedded once in multipage PDF"

    #########################

    clean_up_files(slist.thread.db_files + [f"{i}.pnm" for i in range(1, num + 1)])


def test_save_multipage_pdf_as_ps(
    temp_pnm, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name, temp_pnm.name])

    with tempfile.NamedTemporaryFile(
        suffix=".ps", prefix=" "
    ) as temp_ps, tempfile.NamedTemporaryFile(suffix=".ps") as temp_ps2:
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[1, 2],
            # metadata and timestamp should be ignored: debian #962151
            metadata={},
            options={
                "ps": temp_ps.name,
                "pstool": "pdf2ps",
                "post_save_hook": f"cp %i {temp_ps2.name}",
                "post_save_hook_options": "fg",
                "set_timestamp": True,
            },
            finished_callback=lambda response: mlp.quit(),
        )
        mlp = GLib.MainLoop()
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert os.path.getsize(temp_ps.name) > 194000, "non-empty postscript created"
        assert os.path.getsize(temp_ps2.name) > 194000, "ran post-save hook"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_multipage_pdf_as_ps2(
    temp_pnm, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test writing multipage PDF as Postscript"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name, temp_pnm.name])

    with tempfile.NamedTemporaryFile(
        suffix=".ps", prefix=" "
    ) as temp_ps, tempfile.NamedTemporaryFile(suffix=".ps") as temp_ps2:
        slist.save_pdf(
            path=temp_pdf.name,
            list_of_pages=[1, 2],
            # metadata and timestamp should be ignored: debian #962151
            metadata={},
            options={
                "ps": temp_ps.name,
                "pstool": "pdftops",
                "post_save_hook": f"cp %i {temp_ps2.name}",
                "post_save_hook_options": "fg",
                "set_timestamp": True,
            },
            finished_callback=lambda response: mlp.quit(),
        )
        mlp = GLib.MainLoop()
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert os.path.getsize(temp_ps.name) > 15500, "non-empty postscript created"
        assert os.path.getsize(temp_ps2.name) > 15500, "ran post-save hook"

    #########################

    clean_up_files(slist.thread.db_files)


def test_prepend_pdf(
    temp_pnm, temp_tif, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)
    subprocess.run(["convert", "rose:", temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, temp_tif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[1],
        options={
            "prepend": temp_pdf.name,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"

    #########################

    clean_up_files(slist.thread.db_files + [f"{temp_pdf.name}.bak"])


def test_append_pdf(
    temp_pnm, temp_tif, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test appending a page to a PDF"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)
    subprocess.run(["convert", "rose:", temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, temp_tif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[1],
        options={
            "append": temp_pdf.name,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF appended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"

    #########################

    clean_up_files(slist.thread.db_files + [f"{temp_pdf.name}.bak"])


def test_prepend_with_space(
    temp_pnm, temp_tif, temp_db, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF with a space"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)
    subprocess.run(["convert", "rose:", temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", "te st.pdf", temp_tif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

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

    clean_up_files(slist.thread.db_files + ["te st.pdf", "te st.pdf.bak"])


def test_prepend_with_inverted_comma(
    temp_pnm, temp_tif, temp_db, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)
    subprocess.run(["convert", "rose:", temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", "te'st.pdf", temp_tif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

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

    clean_up_files(slist.thread.db_files + ["te'st.pdf", "te'st.pdf.bak"])


def test_append_pdf_with_timestamp(
    temp_pnm, temp_tif, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test appending a page to a PDF with a timestamp"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)
    subprocess.run(["convert", "rose:", temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, temp_tif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[1],
        metadata={
            "datetime": datetime.datetime(
                2016, 2, 10, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "title": "metadata title",
        },
        options={
            "append": temp_pdf.name,
            "set_timestamp": True,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture), "PDF appended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"
    stb = os.stat(temp_pdf.name)
    assert datetime.datetime.utcfromtimestamp(stb.st_mtime) == datetime.datetime(
        2016, 2, 10, 0, 0, 0
    ), "timestamp"

    #########################

    clean_up_files(slist.thread.db_files + [f"{temp_pdf.name}.bak"])

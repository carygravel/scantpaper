"Test writing multipage PDF with utf8"

import datetime
import os
import re
import subprocess
import tempfile
import pytest
from gi.repository import GLib
import img2pdf
from document import Document
from loop_helpers import safe_mainloop


def test_save_multipage_pdf(
    rose_pnm,
    import_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    temp_pdf,
):
    "Test writing multipage PDF"

    num = 3  # number of pages
    files = [rose_pnm for i in range(num)]
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, files)

    pages = []
    for i in range(num):
        set_text_in_mainloop(
            slist,
            1,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": "hello world", "depth": 3}]',
        )
        pages.append(i + 1)

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=pages,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    capture = subprocess.check_output(["pdffonts", temp_pdf.name], text=True)
    # not all combinations of ocrmypdf, qpdf & ghostsript embed GlyphLessFont
    fonts = 1 if re.search(r"GlyphLessFont", capture) else 0
    assert (
        len(capture.splitlines()) == fonts + 2
    ), "no other fonts embedded in multipage PDF"


@pytest.mark.xfail(reason="OCRmyPDF doesn't yet support non-latin characters")
def test_save_multipage_pdf_with_utf8(
    rose_pnm, import_in_mainloop, set_text_in_mainloop, temp_pdf, clean_up_files
):
    "Test writing multipage PDF with utf8"
    num = 3  # number of pages
    files = [rose_pnm for i in range(num)]
    slist = Document()

    import_in_mainloop(slist, files)

    pages = []
    for i in range(num):
        set_text_in_mainloop(
            slist,
            1,
            '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
            '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
            '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
            '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
            '"пени способствовала сохранению", "depth": 3}]',
        )
        pages.append(i + 1)

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=pages,
        finished_callback=lambda response: mlp.quit(),
    )
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

    clean_up_files(slist.thread.db_files)


def test_save_multipage_pdf_as_ps(rose_pnm, temp_db, temp_pdf, import_in_mainloop):
    "Test writing multipage PDF as Postscript"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm, rose_pnm])

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
                "set_timestamp": True,
            },
            finished_callback=lambda response: mlp.quit(),
        )
        mlp = safe_mainloop(5000)
        mlp.run()

        assert os.path.getsize(temp_ps.name) > 194000, "non-empty postscript created"
        assert os.path.getsize(temp_ps2.name) > 194000, "ran post-save hook"


def test_save_multipage_pdf_as_ps2(rose_pnm, temp_db, temp_pdf, import_in_mainloop):
    "Test writing multipage PDF as Postscript"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm, rose_pnm])

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
                "set_timestamp": True,
            },
            finished_callback=lambda response: mlp.quit(),
        )
        mlp = safe_mainloop(5000)
        mlp.run()

        assert os.path.getsize(temp_ps.name) > 14000, "non-empty postscript created"
        assert os.path.getsize(temp_ps2.name) > 14000, "ran post-save hook"


def test_prepend_pdf(
    rose_pnm, rose_png, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF"
    temp_pdf.write(img2pdf.convert(rose_png))
    temp_pdf.flush()

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[1],
        options={
            "prepend": temp_pdf.name,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"

    #########################

    clean_up_files([f"{temp_pdf.name}.bak"])


def test_append_pdf(
    rose_pnm, rose_png, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test appending a page to a PDF"
    temp_pdf.write(img2pdf.convert(rose_png))
    temp_pdf.flush()

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[1],
        options={
            "append": temp_pdf.name,
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF appended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"

    #########################

    clean_up_files([f"{temp_pdf.name}.bak"])


def test_prepend_with_space(
    rose_pnm, rose_png, temp_db, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF with a space"
    with open("te st.pdf", "wb") as temp_pdf:
        temp_pdf.write(img2pdf.convert(rose_png))
        temp_pdf.flush()

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    slist.save_pdf(
        path="te st.pdf",
        list_of_pages=[1],
        options={
            "prepend": "te st.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "te st.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("te st.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(["te st.pdf", "te st.pdf.bak"])


def test_prepend_with_inverted_comma(
    rose_pnm, rose_png, temp_db, import_in_mainloop, clean_up_files
):
    "Test prepending a page to a PDF"
    with open("te'st.pdf", "wb") as temp_pdf:
        temp_pdf.write(img2pdf.convert(rose_png))
        temp_pdf.flush()

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    slist.save_pdf(
        path="te'st.pdf",
        list_of_pages=[1],
        options={
            "prepend": "te'st.pdf",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = safe_mainloop(5000)
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", "te'st.pdf"], text=True)
    assert re.search(r"Pages:\s+2", capture) is not None, "PDF prepended"
    assert os.path.isfile("te'st.pdf.bak"), "Backed up original"

    #########################

    clean_up_files(["te'st.pdf", "te'st.pdf.bak"])


def test_append_pdf_with_timestamp(
    rose_pnm, rose_png, temp_db, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test appending a page to a PDF with a timestamp"
    temp_pdf.write(img2pdf.convert(rose_png))
    temp_pdf.flush()

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

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
    mlp = safe_mainloop(5000)
    mlp.run()

    capture = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
    assert re.search(r"Pages:\s+2", capture), "PDF appended"
    assert os.path.isfile(f"{temp_pdf.name}.bak"), "Backed up original"
    stb = os.stat(temp_pdf.name)
    assert datetime.datetime.fromtimestamp(
        stb.st_mtime, tz=datetime.timezone.utc
    ) == datetime.datetime(
        2016, 2, 10, 0, 0, 0, tzinfo=datetime.timezone.utc
    ), "timestamp"

    #########################

    clean_up_files([f"{temp_pdf.name}.bak"])

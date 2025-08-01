"Test importing PDF"

import datetime
import os
import re
import subprocess
import shutil
import tempfile
import pytest
from gi.repository import GLib
from document import Document


def test_import_multipage_pdf(rose_tif, temp_pdf, temp_db, clean_up_files):
    "Test importing PDF"
    subprocess.run(["tiffcp", rose_tif.name, rose_tif.name, "test2.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, "test2.tif"], check=True)

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=[temp_pdf.name],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert len(slist.data) == 2, "imported 2 pages"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test2.tif",
        ]
    )


def test_import_multipage_pdf_with_not_enough_images(temp_db, temp_pdf, clean_up_files):
    "Test importing PDF"

    if shutil.which("pdfunite") is None:
        pytest.skip("Please install pdfunite (poppler utils) to enable test")

    subprocess.run(["convert", "rose:", "page1.tif"], check=True)
    subprocess.run(["tiff2pdf", "-o", "page1.pdf", "page1.tif"], check=True)
    content = b"""%PDF-1.4
1 0 obj
  << /Type /Catalog
      /Outlines 2 0 R
      /Pages 3 0 R
  >>
endobj

2 0 obj
  << /Type /Outlines
      /Count 0
  >>
endobj

3 0 obj
  << /Type /Pages
      /Kids [ 4 0 R ]
      /Count 1
  >>
endobj

4 0 obj
  << /Type /Page
      /Parent 3 0 R
      /MediaBox [ 0 0 612 792 ]
      /Contents 7 0 R
      /Resources 5 0 R
  >>
endobj

5 0 obj
  << /Font <</F1 6 0 R >> >>
endobj

6 0 obj
  << /Type /Font
      /Subtype /Type1
      /Name /F1
      /BaseFont /Courier
  >>
endobj

7 0 obj
  << /Length 62 >>
stream
  BT
    /F1 24 Tf
    100 100 Td
    ( Hello World ) Tj
  ET
endstream
endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000091 00000 n 
0000000148 00000 n 
0000000224 00000 n 
0000000359 00000 n 
0000000404 00000 n 
0000000505 00000 n 
trailer
<</Size 8/Root 1 0 R>> 
startxref
618
%%EOF
"""
    with open("page2.pdf", "wb") as fhd:
        fhd.write(content)
    subprocess.run(["pdfunite", "page1.pdf", "page2.pdf", temp_pdf.name], check=True)

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def logger_cb(response):
        nonlocal asserts
        assert re.search(
            r"one image per page", response.status
        ), "one image per page warning"
        asserts += 1

    slist.import_files(
        paths=[temp_pdf.name],
        logger_callback=logger_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    assert len(slist.data) == 1, "imported 1 pages"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "page1.tif",
            "page1.pdf",
            "page2.pdf",
        ]
    )


def test_import_pdf_bw(temp_tif, temp_png, temp_pdf, clean_up_files, temp_db):
    "Test importing PDF"

    options = [
        "convert",
        "+matte",
        "-depth",
        "1",
        "-colorspace",
        "Gray",
        "-type",
        "Bilevel",
        "-family",
        "DejaVu Sans",
        "-pointsize",
        "12",
        "-density",
        "300",
        "label:The quick brown fox",
    ]
    subprocess.run(options + [temp_tif.name], check=True)
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, temp_tif.name], check=True)
    subprocess.run(options + [temp_png.name], check=True)
    subprocess.check_output(
        ["identify", "-format", "%m %G %g %z-bit %r", temp_png.name], text=True
    )

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=[temp_pdf.name],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        slist.thread.get_page(id=1).image_object.mode == "1"
    ), "BW PDF imported correctly"

    #########################

    clean_up_files(slist.thread.db_files)


def test_import_pdf_with_error(rose_tif, temp_pdf, clean_up_files):
    "Test importing PDF"
    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, rose_tif.name], check=True)

    with tempfile.TemporaryDirectory() as dirname:
        slist = Document(dir=dirname)

        mlp = GLib.MainLoop()

        asserts = 0

        def queued_cb(response):
            nonlocal asserts
            assert response.request.process == "get_file_info", "queued_cb"
            asserts += 1

            # inject error during import file
            os.chmod(dirname, 0o500)  # no write access

        def error_cb(_page, _process, message):
            nonlocal asserts
            assert re.search(r"^Error", message), "error_cb"
            asserts += 1

            # inject error during import file
            os.chmod(dirname, 0o700)  # allow write access

        slist.import_files(
            paths=[temp_pdf.name],
            queued_callback=queued_cb,
            error_callback=error_cb,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert asserts == 2, "all callbacks run"

        #########################

        clean_up_files(slist.thread.db_files)


def test_import_encrypted_pdf(rose_tif, temp_db, temp_pdf, clean_up_files):
    "Test importing PDF"

    if shutil.which("pdftk") is None:
        pytest.skip("Please install pdftk to enable test")

    subprocess.run(["tiff2pdf", "-o", temp_pdf.name, rose_tif.name], check=True)
    subprocess.run(
        [
            "pdftk",
            temp_pdf.name,
            "output",
            "output.pdf",
            "encrypt_128bit",
            "user_pw",
            "s3cr3t",
        ],
        check=True,
    )

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    asserts = 0

    def password_cb(path):
        nonlocal asserts
        assert path == "output.pdf"
        asserts += 1
        return "s3cr3t"

    slist.import_files(
        paths=["output.pdf"],
        password_callback=password_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "callbacks all run"
    assert len(slist.data) == 1, "imported 1 page"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "output.pdf",
        ]
    )


def test_import_pdf_with_metadata(rose_tif, temp_pdf, clean_up_files):
    "Test importing PDF"
    cmd = [
        "tiff2pdf",
        "-o",
        temp_pdf.name,
        "-e",
        "20181231120000",
        "-a",
        "Authör",
        "-t",
        "Title",
        "-s",
        "Sübject",
        "-k",
        "Keywörds",
        rose_tif.name,
    ]
    cmd = [x.encode("latin") for x in cmd]  # tiff2pdf expects latin, not utf8
    subprocess.run(cmd, check=True)

    slist = Document()

    mlp = GLib.MainLoop()

    asserts = 0

    def metadata_cb(response):
        assert response["datetime"] == datetime.datetime(
            2018, 12, 31, 12, 0, tzinfo=datetime.timezone.utc
        ), "datetime"
        assert response["author"] == "Authör", "author"
        assert response["subject"] == "Sübject", "subject"
        assert response["keywords"] == "Keywörds", "keywords"
        assert response["title"] == "Title", "title"
        nonlocal asserts
        asserts += 1

    slist.import_files(
        paths=[temp_pdf.name],
        metadata_callback=metadata_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "callbacks all run"

    #########################

    clean_up_files(slist.thread.db_files)


def test_import_pdf_with_2000_pages(rose_tif, temp_db, clean_up_files):
    "Test importing PDF"
    pytest.skip("Skip until this works interactively")
    if shutil.which("pdfunite") is None:
        pytest.skip("Please install pdfunite (poppler utils) to enable test")

    # Create test image
    subprocess.run(["tiff2pdf", "-o", "page1.pdf", rose_tif.name], check=True)
    subprocess.run(
        [
            "pdfunite",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "page1.pdf",
            "10.pdf",
        ],
        check=True,
    )
    subprocess.run(
        [
            "pdfunite",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "10.pdf",
            "100.pdf",
        ],
        check=True,
    )
    subprocess.run(
        [
            "pdfunite",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "100.pdf",
            "1000.pdf",
        ],
        check=True,
    )
    subprocess.run(["pdfunite", "1000.pdf", "1000.pdf", "2000.pdf"], check=True)

    slist = Document(db=temp_db.name)

    mlp = GLib.MainLoop()

    slist.import_files(
        paths=["2000.pdf"],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(40000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert len(slist.data) == 2000, "imported 2000 images"

    #########################

    clean_up_files(
        slist.thread.db_files
        + ["page1.pdf", "10.pdf", "100.pdf", "1000.pdf", "2000.pdf"]
    )

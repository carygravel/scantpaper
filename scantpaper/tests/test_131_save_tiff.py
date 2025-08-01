"Test writing TIFF"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_save_tiff(
    rose_pnm, temp_db, temp_tif, temp_png, import_in_mainloop, clean_up_files
):
    "Test writing TIFF"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path=temp_tif.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": f"convert %i {temp_png.name}",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", temp_tif.name], text=True)
    assert (
        re.search(
            rf"{temp_tif.name} TIFF 70x46 70x46\+0\+0 8-bit sRGB [.\d]+K?B", example
        )
        is not None
    ), "valid TIFF created"

    example = subprocess.check_output(["identify", temp_png.name], text=True)
    assert (
        re.search(
            rf"{temp_png.name} PNG 70x46 70x46\+0\+0 8-bit sRGB \d+\.?\d*K?B 0\.\d+u 0:00\.\d+\b",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    clean_up_files(slist.thread.db_files)


def test_cancel_save_tiff(
    rose_pnm, temp_db, temp_tif, temp_jpg, import_in_mainloop, clean_up_files
):
    "Test cancel saving a TIFF"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    mlp = GLib.MainLoop()
    called = False

    def cancelled_callback(_response):
        nonlocal called
        called = True
        mlp.quit()

    slist.save_tiff(
        path=temp_tif.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "Cancelled callback"

    slist.save_image(
        path=temp_jpg.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", temp_jpg.name], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_tiff_with_error(rose_pnm, temp_tif, import_in_mainloop, clean_up_files):
    "Test writing TIFF and triggering an error"
    with tempfile.TemporaryDirectory() as dirname:
        slist = Document(dir=dirname)
        asserts = 0

        import_in_mainloop(slist, [rose_pnm.name])

        # inject error before save_djvu
        os.chmod(dirname, 0o500)  # no write access

        def error_callback1(_page, _process, _message):
            "no write access"
            assert True, "caught error injected before save_tiff"
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = GLib.MainLoop()
        slist.save_tiff(
            path=temp_tif.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback1,
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        def error_callback2(_page, _process, _message):
            assert True, "save_djvu caught error injected in queue"
            os.chmod(dirname, 0o700)  # allow write access
            nonlocal asserts
            asserts += 1
            mlp.quit()

        mlp = GLib.MainLoop()
        slist.save_tiff(
            path=temp_tif.name,
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback2,
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert asserts == 2, "ran all callbacks"

        #########################

        clean_up_files(slist.thread.db_files)


def test_save_tiff_with_alpha(
    temp_png, temp_db, temp_tif, import_in_mainloop, clean_up_files
):
    "Test writing TIFF with alpha layer"

    subprocess.run(
        [
            "convert",
            "-fill",
            "lightblue",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "label:The quick brown fox",
            temp_png.name,
        ],
        check=True,
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path=temp_tif.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "lzw",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", temp_tif.name], text=True)
    assert (
        re.search(
            rf"{temp_tif.name} TIFF \d\d\dx\d\d \d\d\dx\d\d\+0\+0 8-bit sRGB", example
        )
        is not None
    ), "valid TIFF created"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_tiff_as_ps(
    rose_pnm, temp_db, temp_tif, temp_pdf, import_in_mainloop, clean_up_files
):
    "Test writing TIFF and postscript"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name, rose_pnm.name])

    with tempfile.NamedTemporaryFile(suffix=".ps", prefix=" ") as temp_ps:
        mlp = GLib.MainLoop()
        slist.save_tiff(
            path=temp_tif.name,
            list_of_pages=[slist.data[0][2], slist.data[1][2]],
            options={
                "ps": temp_ps.name,
                "post_save_hook": f"ps2pdf %i {temp_pdf.name}",
                "post_save_hook_options": "fg",
            },
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        example = subprocess.check_output(["file", temp_ps.name], text=True)
        assert (
            example
            == temp_ps.name
            + ": PostScript document text conforming DSC level 3.0, type EPS, Level 3\n"
        ), "valid postscript created"

        example = subprocess.check_output(["pdfinfo", temp_pdf.name], text=True)
        assert re.search(r"tiff2ps", example) is not None, "ran post-save hook"

        #########################

        clean_up_files(slist.thread.db_files)


def test_save_tiff_g4(temp_png, temp_db, temp_tif, import_in_mainloop, clean_up_files):
    "Test writing TIFF with group 4 compression"

    subprocess.run(["convert", "rose:", temp_png.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path=temp_tif.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", temp_tif.name], text=True)
    assert (
        re.search(
            rf"{temp_tif.name} TIFF 70x46 70x46\+0\+0 1-bit Bilevel Gray", example
        )
        is not None
    ), "valid TIFF created"

    #########################

    clean_up_files(slist.thread.db_files)

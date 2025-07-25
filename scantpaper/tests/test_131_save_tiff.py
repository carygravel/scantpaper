"Test writing TIFF"

import os
import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_save_tiff(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test writing TIFF"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF 70x46 70x46\+0\+0 8-bit sRGB [.\d]+K?B", example)
        is not None
    ), "valid TIFF created"

    example = subprocess.check_output(["identify", "test2.png"], text=True)
    assert (
        re.search(
            r"test2\.png PNG 70x46 70x46\+0\+0 8-bit sRGB \d+\.?\d*K?B 0\.\d+u 0:00\.\d+\b",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test.tif",
            "test2.png",
        ]
    )


def test_cancel_save_tiff(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test cancel saving a TIFF"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    mlp = GLib.MainLoop()
    called = False

    def cancelled_callback(_response):
        nonlocal called
        called = True
        mlp.quit()

    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    slist.cancel(cancelled_callback)
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "Cancelled callback"

    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert subprocess.check_output(
        ["identify", "test.jpg"], text=True
    ), "can create a valid JPG after cancelling save PDF process"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test.tif",
            "test.jpg",
        ]
    )


def test_save_tiff_with_error(temp_pnm, import_in_mainloop, clean_up_files):
    "Test writing TIFF and triggering an error"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    with tempfile.TemporaryDirectory() as dirname:
        slist = Document(dir=dirname)
        asserts = 0

        import_in_mainloop(slist, [temp_pnm.name])

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
            path="test.tif",
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
            path="test.tif",
            list_of_pages=[slist.data[0][2]],
            error_callback=error_callback2,
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert asserts == 2, "ran all callbacks"

        #########################

        clean_up_files(
            slist.thread.db_files
            + [
                "test.tif",
                "test2.png",
            ]
        )


def test_save_tiff_with_alpha(temp_png, temp_db, import_in_mainloop, clean_up_files):
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
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "lzw",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF \d\d\dx\d\d \d\d\dx\d\d\+0\+0 8-bit sRGB", example)
        is not None
    ), "valid TIFF created"

    #########################

    clean_up_files(slist.thread.db_files + ["test.tif"])


def test_save_tiff_as_ps(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test writing TIFF and postscript"

    subprocess.run(["convert", "rose:", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name, temp_pnm.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2], slist.data[1][2]],
        options={
            "ps": "te st.ps",
            "post_save_hook": "ps2pdf %i test.pdf",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["file", "te st.ps"], text=True)
    assert (
        example
        == "te st.ps: PostScript document text conforming DSC level 3.0, type EPS, Level 3\n"
    ), "valid postscript created"

    example = subprocess.check_output(["pdfinfo", "test.pdf"], text=True)
    assert (
        re.search(
            r"tiff2ps",
            example,
        )
        is not None
    ), "ran post-save hook"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test.tif",
            "te st.ps",
            "test.pdf",
        ]
    )


def test_save_tiff_g4(temp_png, temp_db, import_in_mainloop, clean_up_files):
    "Test writing TIFF with group 4 compression"

    subprocess.run(["convert", "rose:", temp_png.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    mlp = GLib.MainLoop()
    slist.save_tiff(
        path="test.tif",
        list_of_pages=[slist.data[0][2]],
        options={
            "compression": "g4",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.tif"], text=True)
    assert (
        re.search(r"test.tif TIFF 70x46 70x46\+0\+0 1-bit Bilevel Gray", example)
        is not None
    ), "valid TIFF created"

    #########################

    clean_up_files(
        slist.thread.db_files
        + [
            "test.tif",
            "test2.png",
        ]
    )

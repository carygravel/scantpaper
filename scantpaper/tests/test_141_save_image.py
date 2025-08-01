"Test writing image"

import re
import os
import subprocess
from gi.repository import GLib
from document import Document


def test_save_image(
    rose_pnm, temp_db, temp_jpg, temp_png, import_in_mainloop, clean_up_files
):
    "Test writing image"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    mlp = GLib.MainLoop()
    slist.save_image(
        path=temp_jpg.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": f"convert %i {temp_png.name}",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", temp_jpg.name], text=True)
    assert (
        re.search(rf"{temp_jpg.name} JPEG 70x46 70x46\+0\+0 8-bit sRGB", example)
        is not None
    ), "valid JPG created"

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


def test_save_image_with_quote(rose_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test writing image"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    os.mkdir("te'st")

    mlp = GLib.MainLoop()
    slist.save_image(
        path="te'st/test.jpg",
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "te'st/test.jpg"], text=True)
    assert (
        re.search(r"test.jpg JPEG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

    #########################

    clean_up_files(slist.thread.db_files + ["te'st/test.jpg"])
    os.rmdir("te'st")


def test_save_image_with_ampersand(
    rose_pnm, temp_db, import_in_mainloop, clean_up_files
):
    "Test writing image"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    path = "sed & awk.png"

    mlp = GLib.MainLoop()
    slist.save_image(
        path=path,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", path], text=True)
    assert (
        re.search(rf"{path} PNG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

    #########################

    clean_up_files(slist.thread.db_files + [path])

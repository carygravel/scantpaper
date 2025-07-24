"Test writing image"

import re
import os
import subprocess
from gi.repository import GLib
from document import Document


def test_save_image(temp_db, import_in_mainloop, clean_up_files):
    "Test writing image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["test.pnm"])

    mlp = GLib.MainLoop()
    slist.save_image(
        path="test.jpg",
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": "convert %i test2.png",
            "post_save_hook_options": "fg",
        },
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["identify", "test.jpg"], text=True)
    assert (
        re.search(r"test.jpg JPEG 70x46 70x46\+0\+0 8-bit sRGB", example) is not None
    ), "valid JPG created"

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
            "test.pnm",
            "test.jpg",
            "test2.png",
        ]
    )


def test_save_image_with_quote(temp_db, import_in_mainloop, clean_up_files):
    "Test writing image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["test.pnm"])

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

    clean_up_files(slist.thread.db_files + ["test.pnm", "te'st/test.jpg"])
    os.rmdir("te'st")


def test_save_image_with_ampersand(temp_db, import_in_mainloop, clean_up_files):
    "Test writing image"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["test.pnm"])

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

    clean_up_files(slist.thread.db_files + ["test.pnm", path])

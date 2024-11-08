"Test importing PDF"

import subprocess
import tempfile
import datetime
from gi.repository import GLib
from document import Document


def test_1(clean_up_files):
    "Test importing PDF"

    subprocess.run(["convert", "rose:", "test.tif"], check=True)
    cmd = [
        "tiff2pdf",
        "-o",
        "test.pdf",
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
        "test.tif",
    ]
    cmd = [x.encode("latin") for x in cmd]  # tiff2pdf expects latin, not utf8
    subprocess.run(cmd, check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

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
        paths=["test.pdf"],
        metadata_callback=metadata_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "callbacks all run"

    #########################

    clean_up_files(["test.tif", "test2.tif", "test2.pdf"])

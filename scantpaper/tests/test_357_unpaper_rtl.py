"Test unpaper"

import re
import subprocess
import tempfile
import shutil
import pytest
from gi.repository import GLib
from document import Document
from unpaper import Unpaper


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_1(import_in_mainloop, clean_up_files):
    "Test unpaper"

    unpaper = Unpaper({"output-pages": 2, "layout": "double", "direction": "rtl"})
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The quick brown fox",
            "1.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-border",
            "2x2",
            "-bordercolor",
            "black",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-density",
            "300",
            "label:The slower lazy dog",
            "2.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "-size",
            "100x100",
            "xc:black",
            "black.pbm",
        ],
        check=True,
    )
    subprocess.run(
        [
            "convert",
            "1.pbm",
            "black.pbm",
            "2.pbm",
            "+append",
            "test.pbm",
        ],
        check=True,
    )
    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pbm"])

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2].uuid,
        options={
            "command": unpaper.get_cmdline(),
            "direction": unpaper.get_option("direction"),
        },
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"

    level = []
    for i in [0, 1]:
        with tempfile.NamedTemporaryFile(suffix=".pnm") as filename:
            slist.data[i][2].image_object.save(filename.name)
            out = subprocess.check_output(
                [
                    "convert",
                    filename.name,
                    "-depth",
                    "1",
                    "-resize",
                    "1x1",
                    "txt:-",
                ],
                text=True,
            )
        regex = re.search(r"gray\((\d{2,3}(\.\d+)?)%?\)", out)
        assert regex, f"valid PNM created for page {i+1}"
        level.append(regex.group(1))
    assert len(level) == 2 and level[1] > level[0], "rtl"

    #########################

    clean_up_files(["test.pbm", "1.pbm", "2.pbm", "black.pbm"])

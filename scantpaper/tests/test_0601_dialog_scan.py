"test scan dialog"

import os
import glob
import subprocess
import tempfile
import gi
from document import Document
from dialog.scan import Scan

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position


def test_1():
    "test basic functionality of scan dialog"

    window = Gtk.Window()

    dialog = Scan(
        title="title",
        transient_for=window,
    )
    assert isinstance(dialog, Scan), "Created dialog"

    dialog.sided = "double"
    dialog.side_to_scan = "reverse"

    # After having scanned some double-sided pages on a simplex scanner,
    # selecting single-sided again should also select facing page.
    dialog.sided = "single"
    assert dialog.side_to_scan == "facing", "selecting single sided also selects facing"

    dialog.checkx.set_active(True)
    dialog.page_number_increment = 3
    dialog.checkx.set_active(False)
    assert (
        dialog.page_number_increment == 2
    ), "turning off extended page numbering resets increment"

    assert dialog.allow_batch_flatbed == 0, "default allow-batch-flatbed"
    dialog.allow_batch_flatbed = True
    dialog.num_pages = 2
    assert dialog.num_pages == 2, "num-pages"
    assert dialog.framen.is_sensitive(), "num-page gui not ghosted"
    dialog.allow_batch_flatbed = False
    assert (
        dialog.num_pages == 2
    ), "with no source, num-pages not affected by allow-batch-flatbed"
    assert dialog.framen.is_sensitive(), "with no source, num-page gui not ghosted"


def test_2(clean_up_files):
    "test interaction of scan dialog and document"

    window = Gtk.Window()

    dialog = Scan(
        title="title",
        transient_for=window,
    )
    slist = Document()
    dialog = Scan(
        title="title",
        transient_for=window,
        document=slist,
    )
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    with tempfile.TemporaryDirectory() as tempdir:
        options = {
            "filename": "test.pnm",
            "resolution": (72, 72, "PixelsPerInch"),
            "page": 1,
            "dir": tempdir,
        }
        slist.import_scan(**options)
        options["page"] = 2
        slist.import_scan(**options)
        options["page"] = 4
        slist.import_scan(**options)
        options["page"] = 5

        asserts = 0
        mlp = GLib.MainLoop()

        def finished_callback(_response):
            nonlocal asserts
            assert (
                dialog.page_number_start == 3
            ), "adding pages should update page-number-start"
            assert dialog.num_pages == 1, "adding pages should update num-pages"
            asserts += 1
            mlp.quit()

        options["finished_callback"] = finished_callback
        slist.import_scan(**options)
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()
        assert asserts == 1, "ran finished callback"

        # v2.6.3 had the bug where scanning 10 pages on single-sided, followed by
        # 10 pages double-sided reverse resulted in the reverse pages being numbered:
        # 11, 9, 7, 5, 3, 1, -1, -3, -5, -7
        dialog.allow_batch_flatbed = True
        slist.data = [[1, None, None], [3, None, None], [5, None, None]]
        dialog.page_number_start = 6
        dialog.num_pages = 0
        dialog.side_to_scan = "reverse"
        assert (
            dialog.num_pages == 3
        ), "selecting reverse should automatically limit the number of pages to scan"
        assert (
            dialog.max_pages == 3
        ), "selecting reverse should automatically limit the max number of pages to scan"

        clean_up_files(["test.pnm"] + glob.glob(f"{tempdir}/*"))
        os.rmdir(tempdir)

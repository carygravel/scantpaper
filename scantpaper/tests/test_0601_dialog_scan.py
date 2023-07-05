import os
import subprocess
import gi

# import Gscan2pdf.Document
from dialog.scan import Scan

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import logging
import pytest


@pytest.mark.skip(reason="This can't work until Document() is finished")
def test_1():

    window = Gtk.Window()

    # Gscan2pdf.Translation.set_domain('gscan2pdf')

    # logger = Log.Log4perl.get_logger

    dialog = Scan(
        title="title",
        transient_for=window,
        # logger        = logger
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
    assert dialog["framen"].is_sensitive(), "num-page gui not ghosted"
    dialog.allow_batch_flatbed = False
    assert (
        dialog.num_pages == 2
    ), "with no source, num-pages not affected by allow-batch-flatbed"
    assert dialog["framen"].is_sensitive(), "with no source, num-page gui not ghosted"

    Gscan2pdf.Document.setup(logger)
    slist = Gscan2pdf.Document()
    dialog = Gscan2pdf.Dialog.Scan(
        title="title",
        transient_for=window,
        document=slist,
        logger=logger,
    )
    subprocess.run(["convert", "rose:", "test.pnm"])
    dir = tempfile.newdir()
    options = {
        "filename": "test.pnm",
        "xresolution": 72,
        "yresolution": 72,
        "page": 1,
        "dir": dir,
    }
    slist.import_scan(options)
    options["page"] = 2
    slist.import_scan(options)
    options["page"] = 4
    slist.import_scan(options)
    options["page"] = 5

    def anonymous_01():
        assert (
            dialog.page_number_start == 3
        ), "adding pages should update page-number-start"
        assert dialog.num_pages == 1, "adding pages should update num-pages"
        Gtk.main_quit()

    options["finished_callback"] = anonymous_01
    slist.import_scan(options)
    Gtk.main() # FIXME: implement GLib.MainLoop() as per test 103

    # v2.6.3 had the bug where scanning 10 pages on single-sided, followed by
    # 10 pages double-sided reverse resulted in the reverse pages being numbered:
    # 11, 9, 7, 5, 3, 1, -1, -3, -5, -7

    dialog.allow_batch_flatbed = True
    slist["data"] = [[1, None, None], [3, None, None], [5, None, None]]
    dialog.page_number_start = 6
    dialog.num_pages = 0
    dialog.side_to_scan = "reverse"
    assert (
        dialog.num_pages == 3
    ), "selecting reverse should automatically limit the number of pages to scan"
    assert (
        dialog.max_pages == 3
    ), "selecting reverse should automatically limit the max number of pages to scan"

    os.remove("test.pnm")
    os.rmdir(dir)
    Gscan2pdf.Document.quit()

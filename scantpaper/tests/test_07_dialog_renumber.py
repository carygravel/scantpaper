"test Renumber class"

import subprocess
import tempfile
import gi
from document import Document
from dialog.renumber import Renumber

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1(mainloop_with_timeout, temp_db, clean_up_files):
    "basic tests for Renumber class"
    slist = Document(db=temp_db)
    dialog = Renumber(document=slist, transient_for=Gtk.Window())
    assert isinstance(dialog, Renumber)
    assert dialog.start == 1, "default start for empty document"
    assert dialog.increment == 1, "default step for empty document"

    clean_up_files(slist.thread.db_files)

    #########################

    slist = Document()
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    with tempfile.TemporaryDirectory() as tempdir:
        kwargs = {
            "filename": "test.pnm",
            "resolution": 72,
            "page": 1,
            "dir": tempdir,
        }
        slist.import_scan(**kwargs)
        kwargs["page"] = 2
        loop1 = mainloop_with_timeout()
        kwargs["finished_callback"] = lambda response: loop1.quit()
        slist.import_scan(**kwargs)
        loop1.run()
        slist.select(1)
        assert slist.get_selected_indices() == [1], "selected"
        dialog.range = "selected"
        dialog.document = slist
        assert dialog.start == 2, "start for document with start clash"
        assert dialog.increment == 1, "step for document with start clash"

        #########################

        slist.data[1][0] = 3
        kwargs["page"] = 5
        del kwargs["finished_callback"]
        slist.import_scan(**kwargs)
        kwargs["page"] = 7
        loop2 = mainloop_with_timeout()
        kwargs["finished_callback"] = lambda response: loop2.quit()
        slist.import_scan(**kwargs)
        loop2.run()
        slist.select([2, 3])
        selected = slist.get_selected_indices()
        assert selected == [2, 3], "selected"
        dialog.range = "selected"
        assert dialog.start == 4, "start for document with start and step clash"
        assert dialog.increment == 1, "step for document with start and step clash"

        #########################

        dialog.increment = 0
        assert dialog.start == 4, "start for document with negative step"
        assert dialog.increment == -2, "step for document with negative step"

        asserted = False

        def before_renumber_cb(*args):
            nonlocal asserted
            asserted = True

        dialog.connect("before-renumber", before_renumber_cb)
        dialog.renumber()
        assert asserted, "before-renumber signal fired on renumber"

    #########################

    clean_up_files(slist.thread.db_files + ["test.pnm"])

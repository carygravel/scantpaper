"tests for DocThread()/Document()"

import os
import subprocess
import tempfile
import gi
import pytest
from document import DocThread, Document
from dialog.scan import Scan
from basethread import Request

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position


def test_docthread():
    "tests for DocThread"
    # Gscan2pdf.Translation.set_domain('gscan2pdf')
    # logger = Log.Log4perl.get_logger
    # Gscan2pdf.Document.setup(logger)

    thread = DocThread()
    thread.start()

    with pytest.raises(FileNotFoundError):
        request = Request("get_file_info", ("test2.tif", None), thread.responses)
        thread.do_get_file_info(request)

    tiff = "test.tif"
    subprocess.run(["touch", tiff], check=True)
    with pytest.raises(RuntimeError):
        request = Request("get_file_info", (tiff, None), thread.responses)
        thread.do_get_file_info(request)

    subprocess.run(["convert", "rose:", tiff], check=True)  # Create test image
    tgz = "test.tgz"
    subprocess.run(["tar", "cfz", tgz, tiff], check=True)  # Create test tarball
    request = Request("get_file_info", (tgz, None), thread.responses)
    assert thread.do_get_file_info(request) == {
        "format": "session file",
        "path": "test.tgz",
    }, "do_get_file_info + tgz"

    pbm = "test.pbm"
    cjb2 = "test.cjb2"
    djvu = "test.djvu"
    subprocess.run(["convert", "rose:", pbm], check=True)  # Create test image
    subprocess.run(["cjb2", pbm, cjb2], check=True)
    subprocess.run(["djvm", "-c", djvu, cjb2, cjb2], check=True)
    request = Request("get_file_info", (djvu, None), thread.responses)
    assert thread.do_get_file_info(request) == {
        "format": "DJVU",
        "path": "test.djvu",
        "width": [70, 70],
        "height": [46, 46],
        "ppi": [300, 300],
        "pages": 2,
    }, "do_get_file_info + djvu"

    pdf = "test.pdf"
    subprocess.run(["tiff2pdf", "-o", pdf, tiff], check=True)
    request = Request("get_file_info", (pdf, None), thread.responses)
    info = thread.do_get_file_info(request)
    del info["datetime"]
    assert info == {
        "format": "Portable Document Format",
        "path": "test.pdf",
        "page_size": [16.8, 11.04, "pts"],
        "pages": 1,
    }, "do_get_file_info + pdf"

    info = {
        "format": "Tagged Image File Format",
        "width": [70],
        "height": [46],
        "pages": 1,
        "path": "test.tif",
    }
    request = Request("get_file_info", (tiff, None), thread.responses)
    assert thread.do_get_file_info(request) == info, "do_get_file_info + tiff"
    # do_import_file() no longer returns a page object, as it can return
    # multiple pages, which are passed via the log queue
    # request = Request(
    #     "import_file",
    #     ({"info": info, "first": 1, "last": 1, "dir": None},),
    #     thread.responses,
    # )
    # assert isinstance(thread.do_import_file(request), Page), "do_import_file + tiff"

    png = "test.png"
    subprocess.run(["convert", "rose:", png], check=True)  # Create test image
    request = Request("get_file_info", (png, None), thread.responses)
    assert thread.do_get_file_info(request) == {
        "format": "PNG",
        "path": png,
        "width": [70],
        "height": [46],
        "pages": 1,
        "xresolution": 72.0,
        "yresolution": 72.0,
    }, "do_get_file_info + png"

    def get_file_info_callback(response):
        assert (
            response.request.process == "get_file_info"
        ), "get_file_info_finished_callback"
        assert response.info == info, "get_file_info"

    thread.get_file_info(tiff, None, finished_callback=get_file_info_callback)
    for _ in range(4):
        thread.monitor(block=True)

    for fname in [cjb2, djvu, pbm, pdf, png, tgz, tiff]:
        os.remove(fname)


def test_document():
    "tests for Document()"
    tiff = "test.tif"
    subprocess.run(["convert", "rose:", tiff], check=True)  # Create test image

    slist = Document()
    window = Gtk.Window()
    dialog = Scan(
        title="title",
        transient_for=window,
        document=slist,
        # logger        = logger,
    )  # dir for temporary files
    tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(tempdir.name)

    ran_callback = False

    def finished_callback(_result):
        nonlocal ran_callback
        ran_callback = True
        clipboard = slist.copy_selection(True)
        slist.paste_selection(clipboard[0], 0, "after", True)  # copy-paste page 1->2
        assert (
            f"{slist.data[0][2].filename}" != f"{slist.data[1][2].filename}"
        ), "different filename"
        assert (
            f"{slist.data[0][2].uuid}" != f"{slist.data[1][2].uuid}"
        ), "different uuid"
        assert slist.data[1][0] == 2, "new page is number 2"
        assert slist.get_selected_indices() == [1], "pasted page selected"
        dialog.page_number_start = 3
        clipboard = slist.cut_selection()
        assert len(clipboard) == 1, "cut 1 page to clipboard"
        assert len(slist.data) == 1, "1 page left in list"
        assert slist.get_selected_indices() == [0], "selection changed to previous page"
        # TODO = "Don't know how to trigger update of page-number-start from Document"
        # assert dialog.page_number_start== 2,               'page-number-start after cut'
        slist.paste_selection(clipboard[0], 0, "before")  # paste page before 1
        assert len(slist.data) == 2, "2 pages now in list"
        assert f"{slist.data[0][2].uuid}" == str(
            clipboard[0][2].uuid
        ), "cut page pasted at page 1"
        assert slist.data[0][0] == 1, "cut page renumbered to page 1"
        assert slist.get_selected_indices() == [
            1
        ], "pasted page not selected, as parameter not TRUE"
        assert dialog.page_number_start == 3, "page-number-start after paste"
        slist.select([0, 1])
        assert slist.get_selected_indices() == [0, 1], "selected all pages"
        slist.delete_selection()
        assert len(slist.data) == 0, "deleted all pages"

        # TODO/FIXME: test drag-and-drop callbacks for move
        # TODO/FIXME: test drag-and-drop callbacks for copy

    slist.import_files(paths=[tiff], finished_callback=finished_callback)
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert ran_callback, "ran finished callback"
    os.remove(tiff)

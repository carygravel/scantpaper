"Some helper functions to reduce boilerplate"

from types import SimpleNamespace
import tempfile
import subprocess
import os
import pytest
from config import CONVERT_COMMAND
from dialog.sane import SaneScanDialog
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position


def pytest_configure(config):
    "globals"
    config.timeout = 10000


@pytest.fixture
def sane_scan_dialog():
    "return a SaneScanDialog instance"
    return SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )


@pytest.fixture
def import_in_mainloop():
    "import paths in a blocking mainloop"

    def anonymous(slist, paths):
        mlp = GLib.MainLoop()
        slist.import_files(
            paths=paths,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def set_saved_in_mainloop():
    "set_saved in a blocking mainloop"

    def anonymous(slist, page_id, saved=True):
        mlp = GLib.MainLoop()
        slist.thread.send(
            "set_saved", page_id, saved, finished_callback=lambda response: mlp.quit()
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def set_text_in_mainloop():
    "set_text in a blocking mainloop"

    def anonymous(slist, page_id, text):
        mlp = GLib.MainLoop()
        slist.thread.send(
            "set_text", page_id, text, finished_callback=lambda response: mlp.quit()
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def set_annotations_in_mainloop():
    "set_annotations in a blocking mainloop"

    def anonymous(slist, page_id, annotations):
        mlp = GLib.MainLoop()
        slist.thread.send(
            "set_annotations",
            page_id,
            annotations,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def set_resolution_in_mainloop():
    "set_resolution in a blocking mainloop"

    def anonymous(slist, page_id, xres, yres):
        mlp = GLib.MainLoop()
        slist.thread.send(
            "set_resolution",
            page_id,
            xres,
            yres,
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous


@pytest.fixture
def mainloop_with_timeout(request):
    "start a mainloop with a timeout"

    def anonymous():
        loop = GLib.MainLoop()
        GLib.timeout_add(request.config.timeout, loop.quit)  # to prevent it hanging
        return loop

    return anonymous


@pytest.fixture
def set_device_wait_reload(mainloop_with_timeout):
    "set the device and wait for the options to load"

    def anonymous(dialog, device):
        loop = mainloop_with_timeout()
        signal = None

        def reloaded_scan_options_cb(_arg):
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
        dialog.device_list = [
            SimpleNamespace(name=device, vendor="", model="", label=""),
        ]
        dialog.device = device
        loop.run()

    return anonymous


@pytest.fixture
def set_option_in_mainloop(mainloop_with_timeout):
    "set the given option, and wait for it to finish"

    def anonymous(dialog, name, value):
        loop = mainloop_with_timeout()
        callback_ran = False

        def callback(_arg1, _arg2, _arg3, _arg4):
            nonlocal loop
            nonlocal signal
            nonlocal callback_ran
            callback_ran = True
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("changed-scan-option", callback)
        options = dialog.available_scan_options
        dialog.set_option(options.by_name(name), value)
        loop.run()
        return callback_ran

    return anonymous


@pytest.fixture
def set_paper_in_mainloop(mainloop_with_timeout):
    "set the given paper, and wait for it to finish"

    def anonymous(dialog, paper):
        loop = mainloop_with_timeout()
        callback_ran = False

        def changed_paper(_widget, _paper):
            nonlocal loop
            nonlocal signal
            nonlocal callback_ran
            callback_ran = True
            dialog.disconnect(signal)
            loop.quit()

        signal = dialog.connect("changed-paper", changed_paper)
        dialog.paper = paper
        loop.run()
        return callback_ran

    return anonymous


# pylint: disable=line-too-long
HOCR_HEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name='ocr-system' content='tesseract'>
</head>
"""
# pylint: enable=line-too-long


@pytest.fixture
def temp_db():
    "return a temporary db"
    return tempfile.NamedTemporaryFile(suffix=".db")


@pytest.fixture
def temp_cjb2():
    "return a temporary cjb2"
    return tempfile.NamedTemporaryFile(suffix=".cjb2")


@pytest.fixture
def temp_djvu():
    "return a temporary djvu"
    return tempfile.NamedTemporaryFile(suffix=".djvu")


@pytest.fixture
def temp_gif():
    "return a temporary gif"
    return tempfile.NamedTemporaryFile(suffix=".gif")


@pytest.fixture
def temp_jpg():
    "return a temporary jpg"
    return tempfile.NamedTemporaryFile(suffix=".jpg")


@pytest.fixture
def temp_pbm():
    "return a temporary pbm"
    return tempfile.NamedTemporaryFile(suffix=".pbm")


@pytest.fixture
def temp_pnm():
    "return a temporary pnm"
    return tempfile.NamedTemporaryFile(suffix=".pnm")


@pytest.fixture
def temp_ppm():
    "return a temporary ppm"
    return tempfile.NamedTemporaryFile(suffix=".ppm")


@pytest.fixture
def temp_png():
    "return a temporary png"
    return tempfile.NamedTemporaryFile(suffix=".png")


@pytest.fixture
def temp_pdf():
    "return a temporary pdf"
    return tempfile.NamedTemporaryFile(suffix=".pdf")


@pytest.fixture
def temp_tif():
    "return a temporary tif file"
    return tempfile.NamedTemporaryFile(suffix=".tif")


@pytest.fixture
def temp_txt():
    "return a temporary txt file"
    return tempfile.NamedTemporaryFile(suffix=".txt", mode="wt")


@pytest.fixture
def rotated_qbfox_pnm(temp_pnm):
    "return an image with quick brown fox text"
    subprocess.run(
        [
            CONVERT_COMMAND,
            "-density",
            "300",
            "label:The quick brown fox",
            "-alpha",
            "Off",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-rotate",
            "-90",
            temp_pnm.name,
        ],
        check=True,
    )
    return temp_pnm


@pytest.fixture
def rose_jpg(temp_jpg):
    "return a jpg file with a rose image"
    subprocess.run([CONVERT_COMMAND, "rose:", temp_jpg.name], check=True)
    return temp_jpg


@pytest.fixture
def rose_png(temp_png):
    "return a png file with a rose image"
    subprocess.run([CONVERT_COMMAND, "rose:", temp_png.name], check=True)
    return temp_png


@pytest.fixture
def rose_pnm(temp_pnm):
    "return a pnm file with a rose image"
    subprocess.run([CONVERT_COMMAND, "rose:", temp_pnm.name], check=True)
    return temp_pnm


@pytest.fixture
def rose_tif(temp_tif):
    "return a tif file with a rose image"
    subprocess.run([CONVERT_COMMAND, "rose:", temp_tif.name], check=True)
    return temp_tif


@pytest.fixture
def clean_up_files():
    "clean up given files"

    def anonymous(files):
        for fname in files:
            if os.path.isfile(fname) or os.path.islink(fname):
                os.remove(fname)

    return anonymous


@pytest.fixture
def datadir(request):
    """Return the directory for test data"""
    return os.path.join(request.fspath.dirname, "")

"Some helper functions to reduce boilerplate"

import os
import tempfile
from types import SimpleNamespace

import gi
import pytest
from dialog.sane import SaneScanDialog
from PIL import Image, ImageDraw, ImageFont

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position


from loop_helpers import _MainLoopWrapper, safe_mainloop  # noqa: F401


def pytest_configure(config):
    "globals"
    config.timeout = 10000


@pytest.fixture
def sane_scan_dialog():
    "return a SaneScanDialog instance"
    dialog = SaneScanDialog(
        title="title",
        transient_for=Gtk.Window(),
    )
    yield dialog
    if hasattr(dialog, "thread") and dialog.thread.is_alive():
        dialog.thread.quit()
        dialog.thread.join(timeout=1)
    dialog.destroy()


@pytest.fixture
def import_in_mainloop():
    "import paths in a blocking mainloop"

    def anonymous(slist, paths):
        mlp = safe_mainloop()
        slist.import_files(
            paths=paths,
            finished_callback=lambda response: mlp.quit(),
        )
        mlp.run()

    return anonymous


@pytest.fixture
def set_saved_in_mainloop():
    "set_saved in a blocking mainloop"

    def anonymous(slist, page_id, saved=True):
        mlp = safe_mainloop()
        slist.thread.send(
            "set_saved", page_id, saved, finished_callback=lambda response: mlp.quit()
        )
        mlp.run()

    return anonymous


@pytest.fixture
def set_text_in_mainloop():
    "set_text in a blocking mainloop"

    def anonymous(slist, page_id, text):
        mlp = safe_mainloop()
        slist.thread.send(
            "set_text", page_id, text, finished_callback=lambda response: mlp.quit()
        )
        mlp.run()

    return anonymous


@pytest.fixture
def set_annotations_in_mainloop():
    "set_annotations in a blocking mainloop"

    def anonymous(slist, page_id, annotations):
        mlp = safe_mainloop()
        slist.thread.send(
            "set_annotations",
            page_id,
            annotations,
            finished_callback=lambda response: mlp.quit(),
        )
        mlp.run()

    return anonymous


@pytest.fixture
def set_resolution_in_mainloop():
    "set_resolution in a blocking mainloop"

    def anonymous(slist, page_id, xres, yres):
        mlp = safe_mainloop()
        slist.thread.send(
            "set_resolution",
            page_id,
            xres,
            yres,
            finished_callback=lambda response: mlp.quit(),
        )
        mlp.run()

    return anonymous


@pytest.fixture
def mainloop_with_timeout(request):
    "start a mainloop with a timeout"

    def anonymous():
        loop = GLib.MainLoop()
        wrapper = _MainLoopWrapper(loop)
        GLib.timeout_add(request.config.timeout, wrapper._on_timeout)
        return wrapper

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


def _create_rose_image():
    "Create a 70x46 RGB image resembling the ImageMagick rose: sample"
    img = Image.new("RGB", (70, 46))
    pixels = img.load()
    for y in range(46):
        for x in range(70):
            r = int(255 * (1 - ((x - 35) ** 2 + (y - 23) ** 2) / 2000))
            g = int(128 * (1 - ((x - 20) ** 2 + (y - 15) ** 2) / 1500))
            b = int(180 * (1 - ((x - 50) ** 2 + (y - 30) ** 2) / 1800))
            pixels[x, y] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )
    return img


def _create_qbfox_image():
    "Create a rotated 1-bit grayscale image with 'The quick brown fox' text"
    font_size = 50  # 12pt at 300 DPI ≈ 50px
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
        )
    text = "The quick brown fox"
    tmp = Image.new("L", (1200, 80), 255)
    draw = ImageDraw.Draw(tmp)
    draw.text((10, 10), text, fill=0, font=font)
    bbox = tmp.getbbox()
    if bbox:
        tmp = tmp.crop(bbox)
    return tmp.rotate(90, expand=True).convert("1")


@pytest.fixture(scope="session")
def rose_pnm():
    "return a session-scoped pnm file with a rose image"
    tmp = tempfile.NamedTemporaryFile(suffix=".pnm", delete=False)
    _create_rose_image().save(tmp.name, "PPM")
    yield tmp
    os.unlink(tmp.name)


@pytest.fixture(scope="session")
def rose_png():
    "return a session-scoped png file with a rose image"
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    _create_rose_image().save(tmp.name, "PNG")
    yield tmp
    os.unlink(tmp.name)


@pytest.fixture(scope="session")
def rose_jpg():
    "return a session-scoped jpg file with a rose image"
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    _create_rose_image().save(tmp.name, "JPEG")
    yield tmp
    os.unlink(tmp.name)


@pytest.fixture(scope="session")
def rose_tif():
    "return a session-scoped tif file with a rose image"
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    _create_rose_image().save(tmp.name, "TIFF")
    yield tmp
    os.unlink(tmp.name)


@pytest.fixture(scope="session")
def rotated_qbfox_pnm():
    "return a session-scoped image with quick brown fox text"
    tmp = tempfile.NamedTemporaryFile(suffix=".pnm", delete=False)
    _create_qbfox_image().save(tmp.name)
    yield tmp
    os.unlink(tmp.name)


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

"Some helper functions to reduce boilerplate"

# pylint: disable=redefined-outer-name, protected-access  # tests access private members and pytest fixtures

import contextlib
import logging
import os
import subprocess
import tempfile
from types import SimpleNamespace

import config
import gi
import pytest
from dialog.sane import SaneScanDialog
from frontend import enums
from frontend.image_sane import decode_info
from loop_helpers import _MainLoopWrapper, safe_mainloop
from PIL import Image, ImageDraw, ImageFont
from scanner.options import Option

gi.require_version("Gtk", "3.0")

from gi.repository import (  # pylint: disable=wrong-import-position  # noqa: E402
    GLib,
    Gtk,
)

Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)


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
def sane_scan_mocks():
    "raw_options and mocked SaneThread do_* methods for scan-dialog tests"
    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            index=1,
            name="brightness",
            title="Brightness",
            desc="Controls the brightness of the acquired image.",
            type=1,
            unit=0,
            size=1,
            cap=13,
            constraint=(-100, 100, 1),
        ),
        Option(
            index=2,
            name="contrast",
            title="Contrast",
            desc="Controls the contrast of the acquired image.",
            type=1,
            unit=0,
            size=1,
            cap=13,
            constraint=(-100, 100, 1),
        ),
        Option(
            index=3,
            name="resolution",
            title="Scan resolution",
            desc="Sets the resolution of the scanned image.",
            type=1,
            unit=4,
            size=1,
            cap=5,
            constraint=[600],
        ),
        Option(
            index=4,
            name="x-resolution",
            title="X-resolution",
            desc="Sets the horizontal resolution of the scanned image.",
            type=1,
            unit=4,
            size=1,
            cap=69,
            constraint=[150, 225, 300, 600, 900, 1200],
        ),
        Option(
            index=5,
            name="y-resolution",
            title="Y-resolution",
            desc="Sets the vertical resolution of the scanned image.",
            type=1,
            unit=4,
            size=1,
            cap=69,
            constraint=[150, 225, 300, 600, 900, 1200, 1800, 2400],
        ),
        Option(
            index=6,
            name="",
            title="Geometry",
            desc="",
            type=5,
            unit=0,
            size=1,
            cap=64,
            constraint=None,
        ),
        Option(
            index=7,
            name="scan-area",
            title="Scan area",
            desc="Select an area to scan based on well-known media sizes.",
            type=3,
            unit=0,
            size=1,
            cap=5,
            constraint=[
                "Maximum",
                "A4",
                "A5 Landscape",
                "A5 Portrait",
                "B5",
                "Letter",
                "Executive",
                "CD",
            ],
        ),
        Option(
            size=1,
            type=2,
            index=8,
            desc="Top-left x position of scan area.",
            name="tl-x",
            constraint=(0, 215.899993896484, 0),
            title="Top-left x",
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            index=9,
            type=2,
            size=1,
            title="Top-left y",
            cap=5,
            unit=3,
            name="tl-y",
            constraint=(0, 297.179992675781, 0),
        ),
        Option(
            constraint=(0, 215.899993896484, 0),
            name="br-x",
            unit=3,
            cap=5,
            title="Bottom-right x",
            type=2,
            size=1,
            desc="Bottom-right x position of scan area.",
            index=10,
        ),
        Option(
            type=2,
            size=1,
            desc="Bottom-right y position of scan area.",
            index=11,
            constraint=(0, 297.179992675781, 0),
            name="br-y",
            cap=5,
            unit=3,
            title="Bottom-right y",
        ),
        Option(
            index=12,
            name="source",
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            type=3,
            unit=0,
            size=1,
            cap=5,
            constraint=["Flatbed", "Automatic Document Feeder"],
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(self, _request):
        "mocked_do_get_options"
        self.device_handle = SimpleNamespace(
            brightness=0,
            contrast=0,
            resolution=600,
            x_resolution=300,
            y_resolution=300,
            scan_area="Maximum",
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
            source="Flatbed",
        )
        return raw_options

    def mocked_do_set_option(self, _request):
        "mocked_do_set_option"
        info = 0
        key, value = _request.args
        if key == "source" and value == "Automatic Document Feeder":
            raw_options[10] = raw_options[10]._replace(
                constraint=(0, 215.899993896484, 0)
            )
            self.device_handle.br_x = 215.899993896484
            raw_options[11] = raw_options[11]._replace(
                constraint=(0, 355.599990844727, 0)
            )
            self.device_handle.br_y = 355.599990844727
            info = enums.INFO_RELOAD_OPTIONS
        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    def mocked_do_scan_page(self, _request):
        "mocked_do_scan_page page"
        if self.device_handle is None:
            msg = "must open device before starting scan"
            raise ValueError(msg)
        return Image.new("1", (100, 100))

    def patch_all(mocker):
        "patch the SaneThread do_* methods used by scan-dialog tests"
        mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
        mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
        mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)
        mocker.patch("dialog.sane.SaneThread.do_scan_page", mocked_do_scan_page)

    return SimpleNamespace(
        raw_options=raw_options,
        mocked_do_open_device=mocked_do_open_device,
        mocked_do_get_options=mocked_do_get_options,
        mocked_do_set_option=mocked_do_set_option,
        mocked_do_scan_page=mocked_do_scan_page,
        patch_all=patch_all,
    )


@pytest.fixture
def inexact_scan_mocks():
    "raw_options and mocked SaneThread do_* methods for the test_inexact family"
    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            cap=5,
            constraint=["ADF", "Document Table"],
            desc="Document Source",
            index=1,
            size=1,
            name="source",
            title="Document Source",
            type=3,
            unit=0,
        ),
        Option(
            cap=5,
            constraint=(50, 1200, 0),
            desc="Resolution",
            index=4,
            size=1,
            name="resolution",
            title="Resolution",
            type=1,
            unit=4,
        ),
        Option(
            cap=5,
            constraint=(0, 356.0, 0),
            desc="Bottom Right X",
            index=11,
            size=1,
            name="br-x",
            title="Bottom Right X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 356.0, 0),
            desc="Bottom Right Y",
            index=12,
            size=1,
            name="br-y",
            title="Bottom Right Y",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 215.899993896484, 0),
            desc="Top Left X",
            index=13,
            size=1,
            name="tl-x",
            title="Top Left X",
            type=2,
            unit=3,
        ),
        Option(
            cap=5,
            constraint=(0, 297.179992675781, 0),
            desc="Top Left Y",
            index=14,
            size=1,
            name="tl-y",
            title="Top Left Y",
            type=2,
            unit=3,
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            source="Document Table",
            resolution=75,
            tl_x=0,
            tl_y=0,
            br_x=215.899993896484,
            br_y=297.179992675781,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        return raw_options

    def mocked_do_set_option(self, _request):
        """A fujitsu:fi-4220C2dj was ignoring paper change requests because setting
        initial geometry set INFO_INEXACT"""
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break

        info = 0
        if key in ["br-x", "br-y", "tl-x", "tl-y"]:
            info = enums.INFO_RELOAD_PARAMS + enums.INFO_INEXACT
            value -= 0.5
            logger.info(
                "sane_set_option %s (%s) to %s returned info %s (%s)",
                opt.index,
                opt.name,
                value,
                info,
                decode_info(info),
            )

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    def patch_all(mocker):
        "patch the SaneThread do_* methods used by the test_inexact family"
        mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
        mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)
        mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    return SimpleNamespace(
        raw_options=raw_options,
        mocked_do_open_device=mocked_do_open_device,
        mocked_do_get_options=mocked_do_get_options,
        mocked_do_set_option=mocked_do_set_option,
        patch_all=patch_all,
    )


@pytest.fixture
def infinite_reloads_scan_mocks():
    "raw_options and open/get mocks for the test_infinite_reloads family"
    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
    ]

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    def patch_open_and_get(mocker):
        "patch the SaneThread do_open_device/do_get_options methods"
        mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)
        mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    return SimpleNamespace(
        raw_options=raw_options,
        mocked_do_open_device=mocked_do_open_device,
        mocked_do_get_options=mocked_do_get_options,
        patch_open_and_get=patch_open_and_get,
    )


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
def get_page_sync():
    "get a page synchronously via async send()"

    def anonymous(thread, **kwargs):
        result = [None]
        error = [None]
        mlp = safe_mainloop()

        def on_finished(response):
            result[0] = response.info
            mlp.quit()

        def on_error(response):
            error[0] = response.status
            mlp.quit()

        thread.send(
            "get_page",
            kwargs,
            finished_callback=on_finished,
            error_callback=on_error,
        )
        mlp.run()

        if error[0] is not None:
            raise ValueError(error[0])

        return result[0]

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
    # SIM115 — cross-scope file handle used intentionally
    f = tempfile.NamedTemporaryFile(  # noqa: SIM115  # pylint: disable=consider-using-with
        suffix=".db", delete=False
    )
    f.close()
    yield SimpleNamespace(name=f.name)
    for suffix in ("", "-wal", "-shm"):
        with contextlib.suppress(FileNotFoundError):
            os.remove(f.name + suffix)


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
    "Create a rotated grayscale image with 'The quick brown fox' text"
    font_size = 72
    font = None
    font_source = None
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]:
        try:
            font = ImageFont.truetype(path, font_size)
            font_source = path
            break
        except OSError:
            continue
    if font is None:
        result = subprocess.run(
            ["fc-match", "--format=%{file}", "sans:style=Regular"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            font = ImageFont.truetype(result.stdout.strip(), font_size)
            font_source = f"fc-match:{result.stdout.strip()}"
    if font is None:
        try:
            font = ImageFont.load_default(size=font_size)
            font_source = "PIL load_default(size=72)"
        except TypeError:
            font = ImageFont.load_default()
            font_source = "PIL load_default() bitmap"
    print(f"[conftest] _create_qbfox_image: font_source={font_source}", flush=True)
    print(
        f"[conftest] _create_qbfox_image: Pillow version={Image.__version__}",
        flush=True,
    )
    print(f"[conftest] _create_qbfox_image: font={font}", flush=True)
    text = "The quick brown fox"
    print(
        f"[conftest] _create_qbfox_image: font.getbbox(text)={font.getbbox(text)}",
        flush=True,
    )
    print(
        f"[conftest] _create_qbfox_image: font.getmetrics()={font.getmetrics()}",
        flush=True,
    )
    canvas = Image.new("L", (2400, 600), 255)
    draw = ImageDraw.Draw(canvas)
    draw.text((100, 200), text, fill=0, font=font)
    canvas.save("/tmp/qbfox_before_crop.png")
    # get_flattened_data was added in Pillow 12.1.0; fall back to getdata for older versions
    _get_data = getattr(canvas, "get_flattened_data", canvas.getdata)
    pixels = list(_get_data())
    print(
        f"[conftest] _create_qbfox_image: pixel min={min(pixels)} max={max(pixels)} "
        f"non_white={sum(1 for p in pixels if p != 255)}",
        flush=True,
    )
    mask = canvas.point(lambda x: 0 if x == 255 else 255)
    bbox = mask.getbbox()
    print(f"[conftest] _create_qbfox_image: text_bbox={bbox}", flush=True)
    if bbox:
        pad = 40
        canvas = canvas.crop(
            (
                max(bbox[0] - pad, 0),
                max(bbox[1] - pad, 0),
                min(bbox[2] + pad, canvas.width),
                min(bbox[3] + pad, canvas.height),
            )
        )
    w, h = canvas.size
    min_w, min_h = 400, 100
    if w < min_w or h < min_h:
        scale = max(min_w / w, min_h / h)
        canvas = canvas.resize(
            (int(w * scale), int(h * scale)), Image.Resampling.LANCZOS
        )
    return canvas.rotate(90, expand=True)


@pytest.fixture(scope="session")
def rose_pnm():
    "return a session-scoped pnm file with a rose image"
    path = tempfile.mktemp(suffix=".pnm")
    _create_rose_image().save(path, "PPM")
    yield path
    os.unlink(path)


@pytest.fixture(scope="session")
def rose_png():
    "return a session-scoped png file with a rose image"
    path = tempfile.mktemp(suffix=".png")
    _create_rose_image().save(path, "PNG")
    yield path
    os.unlink(path)


@pytest.fixture(scope="session")
def rose_jpg():
    "return a session-scoped jpg file with a rose image"
    path = tempfile.mktemp(suffix=".jpg")
    _create_rose_image().save(path, "JPEG")
    yield path
    os.unlink(path)


@pytest.fixture(scope="session")
def rose_tif():
    "return a session-scoped tif file with a rose image"
    path = tempfile.mktemp(suffix=".tif")
    _create_rose_image().save(path, "TIFF")
    yield path
    os.unlink(path)


@pytest.fixture(scope="session")
def rotated_qbfox_pnm():
    "return a session-scoped image with quick brown fox text"
    path = tempfile.mktemp(suffix=".pnm")
    _create_qbfox_image().save(path)
    yield path
    os.unlink(path)


@pytest.fixture
def rotated_qbfox_pnm_im(temp_pnm):
    "return an ImageMagick-generated image with quick brown fox text"
    subprocess.run(
        [
            config.CONVERT_COMMAND,
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

"""Test unpaper."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import gi
import pytest
from PIL import Image, ImageDraw

from scantpaper import config
from scantpaper.const import A4_HEIGHT_MM, A4_WIDTH_MM, POINTS_PER_INCH
from scantpaper.document import Document
from scantpaper.loop_helpers import safe_mainloop
from scantpaper.unpaper import Unpaper

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.basethread import Response

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def test_unpaper_program_version(mocker: pytest.MockerFixture) -> None:
    """Test Unpaper.program_version caching and retrieval."""
    unpaper = Unpaper()
    assert unpaper._version is None
    mocker.patch("scantpaper.unpaper.program_version", return_value="6.2")
    assert unpaper.program_version() == "6.2"
    assert unpaper._version == "6.2"
    # Subsequent call should use cached version
    assert unpaper.program_version() == "6.2"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_version() -> None:
    """Test unpaper version."""
    unpaper = Unpaper()
    assert unpaper.program_version() is not None, "version"


def test_1() -> None:
    """Test unpaper dialog."""
    unpaper = Unpaper()

    assert unpaper.get_option("direction") == "ltr", "default direction"

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)
    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "single",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "Basic functionality > 0.3"

    unpaper = Unpaper({"layout": "double"})
    unpaper.add_options(vbox)
    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "double",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "Defaults"

    assert unpaper.get_option("direction") == "ltr", "get_option"

    assert unpaper.get_options() == {
        "no-blackfilter": False,
        "output-pages": 1,
        "no-deskew": False,
        "no-border-scan": False,
        "no-noisefilter": False,
        "no-blurfilter": False,
        "white-threshold": 0.9,
        "layout": "double",
        "no-mask-scan": False,
        "no-mask-center": False,
        "no-grayfilter": False,
        "no-border-align": False,
        "black-threshold": 0.33,
        "deskew-scan-direction": "left,right",
        "border-margin": "0.0,0.0",
        "direction": "ltr",
    }, "get_options"

    #########################

    unpaper = Unpaper(
        {
            "white-threshold": "0.8",
            "black-threshold": "0.35",
        },
    )

    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.35",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "single",
        "--output-pages",
        "1",
        "--white-threshold",
        "0.8",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "no GUI"

    #########################

    unpaper = Unpaper({"layout": "double"})
    unpaper.add_options(vbox)
    unpaper.set_options({"output-pages": 2})

    assert unpaper.get_cmdline() == [
        "unpaper",
        "--black-threshold",
        "0.33",
        "--border-margin",
        "0.0,0.0",
        "--deskew-scan-direction",
        "left,right",
        "--layout",
        "double",
        "--output-pages",
        "2",
        "--white-threshold",
        "0.9",
        "--overwrite",
        "%s",
        "%s",
        "%s",
    ], "output-pages = 2"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper(
    temp_pbm: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    temp_db: object,
    get_page_sync: Callable[..., object],
) -> None:
    """Test unpaper."""
    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "-size",
            "210x297",
            "-depth",
            "1",
            "label:The quick brown fox",
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
            temp_pbm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pbm.name])

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of imported image"

    asserts = 0

    def display_cb(response: Response) -> None:
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = safe_mainloop(2000)
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of processed image"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper2(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_resolution_in_mainloop: Callable[[object, str, float, float], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test unpaper."""
    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "label:The quick brown fox",
            "-size",
            "255x350",
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
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pnm.name])

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == POINTS_PER_INCH, (
        "non-standard size pnm imports with 72 PPI"
    )

    set_resolution_in_mainloop(slist, 1, 300, 300)
    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == 300, (
        "simulated having imported non-standard pnm with 300 PPI"
    )

    asserts = 0

    def display_cb(response: Response) -> None:
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = safe_mainloop(2000)
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == 300, "Resolution of processed image"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper3(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test unpaper."""
    unpaper = Unpaper({"output-pages": 2, "layout": "double"})
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "label:The quick brown fox",
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
            "1.pnm",
        ],
        check=True,
    )
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "label:The slower lazy dog",
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
            "2.pnm",
        ],
        check=True,
    )
    subprocess.run(
        [config.CONVERT_COMMAND, "xc:black", "-size", "100x100", "black.pnm"],
        check=True,
    )
    subprocess.run(
        [
            config.CONVERT_COMMAND,
            "1.pnm",
            "black.pnm",
            "2.pnm",
            "+append",
            temp_pnm.name,
        ],
        check=True,
    )
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == POINTS_PER_INCH, "Resolution of imported image"

    asserts = 0

    def display_cb(response: Response) -> None:
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = safe_mainloop(2000)
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 2, "all callbacks run"
    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == POINTS_PER_INCH, "Resolution of 1st page"
    page = get_page_sync(slist.thread, id=2)
    assert page.resolution[0] == POINTS_PER_INCH, "Resolution of 2nd page"

    #########################

    clean_up_files(["1.pnm", "black.pnm", "2.pnm"])


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper_rtl(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test unpaper."""
    unpaper = Unpaper({"output-pages": 2, "layout": "double", "direction": "rtl"})

    # Image dimensions
    height = 200
    strip_width = 5
    width = 200 * 2 + strip_width
    x1 = [0, height + strip_width]
    x2 = [height, width]
    in_level = [(0, 255, 0), (255, 0, 0)]

    # Create image
    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)

    # Draw left (green) & right (red) strips
    for i in [0, 1]:
        draw.rectangle(
            [x1[i], 0, x2[i], height],
            fill=in_level[i],
        )

    img.save(temp_pnm.name)
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    asserts = 0

    def display_cb(response: Response) -> None:
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = safe_mainloop(2000)
    slist.unpaper(
        page=slist.data[0][2],
        options={
            "command": unpaper.get_cmdline(),
            "direction": unpaper.get_option("direction"),
        },
        display_callback=display_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 2, "all callbacks run"

    out_level = []
    for i in [0, 1]:
        page = get_page_sync(slist.thread, id=i + 1)
        out_level.append(page.image_object.getpixel((100, 100)))

    def close(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
        """Return whether two RGB pixels differ by no more than 8 in any channel."""
        return all(abs(c1 - c2) <= 8 for c1, c2 in zip(a, b, strict=False))

    assert len(in_level) == 2, "rtl"
    assert len(out_level) == 2, "rtl"
    assert close(in_level[0], out_level[1]), "rtl"
    assert close(in_level[1], out_level[0]), "rtl"


def test_unpaper_ui_fractional_thresholds() -> None:
    """White/black threshold spins show locale fractions and reject bad input."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    white = unpaper.options["white-threshold"]["widget"]
    black = unpaper.options["black-threshold"]["widget"]

    assert isinstance(white, Gtk.SpinButton)
    assert isinstance(black, Gtk.SpinButton)
    assert white.get_numeric() is False
    assert black.get_numeric() is False
    assert white.get_value() == 0.9
    assert white.get_text() == "0.9"
    assert black.get_value() == 0.33
    assert black.get_text() == "0.33"

    white.get_buffer().set_text("0.8", -1)
    white.emit("focus-out-event", None)
    assert white.get_value() == 0.8
    assert white.get_text() == "0.8"

    white.get_buffer().set_text("0,8", -1)
    white.emit("focus-out-event", None)
    assert white.get_value() == 0.8
    assert white.get_text() == "0.8"

    white.get_buffer().set_text("abc", -1)
    white.emit("activate")
    assert white.get_value() == 0.8
    assert white.get_text() == "0.8"


def test_unpaper_ui_toggles() -> None:
    """Test UI interaction and toggles in Unpaper."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    options = unpaper.options

    # test dsbutton toggled (no-deskew)
    dsbutton = options["no-deskew"]["widget"]
    dframe = options["deskew-scan-direction"]["widget"]

    dsbutton.set_active(True)
    assert not dframe.get_sensitive()
    dsbutton.set_active(False)
    assert dframe.get_sensitive()

    # test deskew_scan_direction_button_cb (at least one active)
    checkbuttons = []

    def find_checkbuttons(widget: Gtk.Widget) -> None:
        if isinstance(widget, Gtk.CheckButton):
            checkbuttons.append(widget)
        elif hasattr(widget, "get_children"):
            for child in widget.get_children():
                find_checkbuttons(child)

    find_checkbuttons(dframe)

    for b in checkbuttons:
        b.set_active(False)
    # The last one should have been forced back to active
    assert any(b.get_active() for b in checkbuttons)

    # test no-border-scan toggle
    bsbutton = options["no-border-scan"]["widget"]
    babutton = options["no-border-align"]["widget"]
    bframe = options["border-align"]["widget"]

    bsbutton.set_active(True)
    assert not bframe.get_sensitive()
    assert not babutton.get_sensitive()
    bsbutton.set_active(False)
    assert babutton.get_sensitive()

    # test no-border-align toggle
    babutton.set_active(True)
    assert not bframe.get_sensitive()
    babutton.set_active(False)
    assert bframe.get_sensitive()


def test_unpaper_ui_border_margins() -> None:
    """Test border margin sensitivity based on alignment."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    options = unpaper.options
    bframe = options["border-align"]["widget"]
    bmframe = options["border-margin"]["widget"]

    checkbuttons = []

    def find_checkbuttons(widget: Gtk.Widget) -> None:
        if isinstance(widget, Gtk.CheckButton):
            checkbuttons.append(widget)
        elif hasattr(widget, "get_children"):
            for child in widget.get_children():
                find_checkbuttons(child)

    find_checkbuttons(bframe)

    # Deactivate all border align buttons
    for b in checkbuttons:
        b.set_active(False)

    assert not bmframe.get_sensitive()

    # Activate one
    checkbuttons[0].set_active(True)
    assert bmframe.get_sensitive()


def test_unpaper_mask_scan_sync() -> None:
    """Test no-mask-scan affecting no-mask-center sensitivity."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    options = unpaper.options
    msbutton = options["no-mask-scan"]["widget"]
    mcbutton = options["no-mask-center"]["widget"]

    msbutton.set_active(True)
    assert not mcbutton.get_sensitive()
    msbutton.set_active(False)
    assert mcbutton.get_sensitive()


def test_combobox_tooltip() -> None:
    """Test ComboBox tooltip change on selection."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    combobl = unpaper.options["layout"]["widget"]
    # Select 'double' (index 1)
    combobl.set_active(1)
    combobl.emit("changed")

    # test combobox_get_option returning None
    combobl.set_active(-1)
    assert unpaper._combobox_get_option("layout") is None


def test_combobox_tooltip_explicit() -> None:
    """Test ComboBox tooltip change on selection with explicit assertions."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    combobl = unpaper.options["layout"]["widget"]

    # Initially it might be 'single' or empty depending on how it's initialized
    # Select 'double' (index 1)
    combobl.set_active(1)
    combobl.emit("changed")
    assert combobl.get_tooltip_text()[:10] == "Two pages "

    # Select 'single' (index 0)
    combobl.set_active(0)
    combobl.emit("changed")
    assert combobl.get_tooltip_text()[:10] == "One page p"


def test_set_options_mixed_types() -> None:
    """Test set_options with various types including group ones."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)
    unpaper.set_options(
        {
            "layout": "double",
            "deskew-scan-direction": "top,bottom",
            "border-margin": "5,10",
        }
    )
    assert unpaper.get_option("layout") == "double"
    assert unpaper.get_option("deskew-scan-direction") == "bottom,top"  # sorted
    assert unpaper.get_option("border-margin") == "10.0,5.0"


def test_get_cmdline_branches() -> None:
    """Test get_cmdline branches."""
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)
    unpaper.set_options(
        {
            "no-deskew": True,
            "black-threshold": 0.5,
            "white-threshold": 0.8,
            "layout": "double",
            "output-pages": 2,
        }
    )
    cmd = unpaper.get_cmdline()
    assert "--no-deskew" in cmd
    assert "--black-threshold" in cmd
    assert "0.5" in cmd
    assert "--white-threshold" in cmd
    assert "0.8" in cmd
    assert "--output-pages" in cmd
    assert "2" in cmd

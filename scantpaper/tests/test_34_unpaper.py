"Test unpaper"

import subprocess
import shutil
import unittest.mock
import pytest
import config
from document import Document
from unpaper import Unpaper, _program_version, program_version
from PIL import Image, ImageDraw
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # pylint: disable=wrong-import-position


def test_program_version_helper():
    "Test _program_version standalone helper"

    class MockOutput:
        "Mock output class"

        def __init__(self, stdout, stderr):
            self.stdout = stdout
            self.stderr = stderr

    mock_output = MockOutput(stdout="unpaper 6.1", stderr="error output")

    # stdout stream
    assert _program_version("stdout", r"([\d.]+)", mock_output) == "6.1"
    # stderr stream
    assert _program_version("stderr", r"error ([\w]+)", mock_output) == "output"
    # both stream
    assert _program_version("both", r"unpaper ([\d.]+)", mock_output) == "6.1"
    # unknown stream (should return None and log error)
    with pytest.raises(TypeError):
        _program_version("unknown", r".*", mock_output)


def test_program_version_file_not_found():
    "Test program_version when file not found"
    with unittest.mock.patch("subprocess.run", side_effect=FileNotFoundError):
        assert program_version("stdout", r".*", ["non-existent"]) is None


def test_unpaper_program_version_lazy(mocker):
    "Test Unpaper.program_version lazy loading"
    unpaper = Unpaper()
    assert unpaper._version is None
    mocker.patch("unpaper.program_version", return_value="6.2")
    assert unpaper.program_version() == "6.2"
    assert unpaper._version == "6.2"
    # Subsequent call should use cached version
    assert unpaper.program_version() == "6.2"


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_version():
    "Test unpaper version"
    unpaper = Unpaper()
    assert unpaper.program_version() is not None, "version"


def test_1():
    "Test unpaper dialog"
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
def test_unpaper(temp_pbm, import_in_mainloop, temp_db, clean_up_files):
    "Test unpaper"

    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
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

    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 25.74208754208754, "Resolution of processed image"

    #########################

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper2(
    temp_pnm, temp_db, import_in_mainloop, set_resolution_in_mainloop, clean_up_files
):
    "Test unpaper"

    unpaper = Unpaper()
    paper_sizes = {
        "A4": {"x": 210, "y": 297, "l": 0, "t": 0},
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

    page = slist.thread.get_page(id=1)
    assert page.resolution[0] == 72, "non-standard size pnm imports with 72 PPI"

    set_resolution_in_mainloop(slist, 1, 300, 300)
    page = slist.thread.get_page(id=1)
    assert (
        page.resolution[0] == 300
    ), "simulated having imported non-standard pnm with 300 PPI"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 300, "Resolution of processed image"

    #########################

    clean_up_files(slist.thread.db_files)


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper3(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test unpaper"

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

    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 72, "Resolution of imported image"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={"command": unpaper.get_cmdline()},
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "all callbacks run"
    page = slist.thread.get_page(number=1)
    assert page.resolution[0] == 72, "Resolution of 1st page"
    page = slist.thread.get_page(number=2)
    assert page.resolution[0] == 72, "Resolution of 2nd page"

    #########################

    clean_up_files(slist.thread.db_files + ["1.pnm", "black.pnm", "2.pnm"])


@pytest.mark.skipif(shutil.which("unpaper") is None, reason="requires unpaper")
def test_unpaper_rtl(temp_pnm, temp_db, import_in_mainloop, clean_up_files):
    "Test unpaper"

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

    def display_cb(response):
        nonlocal asserts
        if response.info and "row" in response.info:
            assert True, "Triggered display callback"
            asserts += 1

    mlp = GLib.MainLoop()
    slist.unpaper(
        page=slist.data[0][2],
        options={
            "command": unpaper.get_cmdline(),
            "direction": unpaper.get_option("direction"),
        },
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert asserts == 2, "all callbacks run"

    out_level = []
    for i in [0, 1]:
        page = slist.thread.get_page(number=i + 1)
        out_level.append(page.image_object.getpixel((100, 100)))
    assert (
        len(in_level) == 2
        and len(out_level) == 2
        and in_level[0] == out_level[1]
        and in_level[1] == out_level[0]
    ), "rtl"

    #########################

    clean_up_files(slist.thread.db_files)


def test_unpaper_ui_toggles():
    "Test UI interaction and toggles in Unpaper"
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

    def find_checkbuttons(widget):
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


def test_unpaper_ui_border_margins():
    "Test border margin sensitivity based on alignment"
    unpaper = Unpaper()
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    unpaper.add_options(vbox)

    options = unpaper.options
    bframe = options["border-align"]["widget"]
    bmframe = options["border-margin"]["widget"]

    checkbuttons = []

    def find_checkbuttons(widget):
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


def test_unpaper_mask_scan_sync():
    "Test no-mask-scan affecting no-mask-center sensitivity"
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


def test_combobox_tooltip():
    "Test ComboBox tooltip change on selection"
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


def test_set_options_mixed_types():
    "Test set_options with various types including group ones"
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


def test_get_cmdline_branches():
    "Test get_cmdline branches"
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

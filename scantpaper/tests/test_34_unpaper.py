"Test unpaper dialog"

from unpaper import Unpaper
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1():
    "Test unpaper dialog"
    unpaper = Unpaper()
    assert unpaper.program_version() is not None, "version"

    assert unpaper.get_option("direction") == "ltr", "default direction"

    vbox = Gtk.VBox()
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

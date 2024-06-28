"options from fujitsu backend"
from scanner.options import Options, Option
import pytest
from frontend import enums


def test_1():
    "options from fujitsu backend"

    filename = "scantpaper/tests/scanners/fujitsu"
    try:
        with open(filename, "r", encoding="utf-8") as fhd:
            output = fhd.read()
    except IOError:
        pytest.skip("source tree not found")
        return
    options = Options(output)
    that = [
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
            title="Scan Mode",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="source",
            title="Source",
            index=2,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=["ADF Front", "ADF Back", "ADF Duplex"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="mode",
            title="Mode",
            index=3,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            constraint=["Gray", "Color"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="resolution",
            title="Resolution",
            index=4,
            desc="Sets the horizontal resolution of the scanned image.",
            constraint=(100, 600, 1),
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="y-resolution",
            title="Y resolution",
            index=5,
            desc="Sets the vertical resolution of the scanned image.",
            constraint=(50, 600, 1),
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=6,
            title="Geometry",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="tl-x",
            title="Top-left x",
            index=7,
            desc="Top-left x position of scan area.",
            constraint=(0.0, 224.846, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=8,
            desc="Top-left y position of scan area.",
            constraint=(0.0, 863.489, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=9,
            constraint=(0.0, 224.846, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=10,
            constraint=(0.0, 863.489, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="pagewidth",
            title="Pagewidth",
            index=11,
            desc="Must be set properly to align scanning window",
            constraint=(0.0, 224.846, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="pageheight",
            title="Pageheight",
            index=12,
            desc="Must be set properly to eject pages",
            constraint=(0.0, 863.489, 0.0211639),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=13,
            title="Enhancement",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="rif",
            title="Rif",
            index=14,
            desc="Reverse image format",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=15,
            title="Advanced",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="dropoutcolor",
            title="Dropoutcolor",
            index=16,
            desc="One-pass scanners use only one color during gray or binary "
            "scanning, useful for colored paper or ink",
            constraint=["Default", "Red", "Green", "Blue"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="sleeptimer",
            title="Sleeptimer",
            index=17,
            desc="Time in minutes until the internal power supply switches to sleep mode",
            constraint=(0, 60, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=18,
            title="Sensors and Buttons",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
    ]
    assert options.array == that, "fujitsu"
    assert options.num_options() == 19, "number of options"
    assert options.by_index(2).name == "source", "by_index"
    assert options.by_name("source").name == "source", "by_name"
    assert options.by_title("Source").name == "source", "by_title"
    assert options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": 0},
        0,
    ), "supports_paper"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": -10},
        0,
    ), "paper crosses top border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": 600},
        0,
    ), "paper crosses bottom border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": -10, "t": 0},
        0,
    ), "paper crosses left border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 20, "t": 0},
        0,
    ), "paper crosses right border"
    assert not options.supports_paper(
        {"x": 225, "y": 297, "l": 0, "t": 0},
        0,
    ), "paper too wide"
    assert not options.supports_paper(
        {"x": 210, "y": 870, "l": 0, "t": 0},
        0,
    ), "paper too tall"
    options.delete_by_index(2)
    assert options.by_index(2) is None, "delete_by_index"
    assert options.by_name("source") is None, "delete_by_index got hash too"
    options.delete_by_name("mode")
    assert options.by_name("mode") is None, "delete_by_name"
    assert options.by_index(3) is None, "delete_by_name got array too"
    output = """Options specific to device `fujitsu:libusb:002:004':
  Geometry:
    -l 0..224.846mm (in quants of 0.0211639) [0]
        Top-left x position of scan area.
    -t 0..863.489mm (in quants of 0.0211639) [0]
        Top-left y position of scan area.
    -x 0..204.846mm (in quants of 0.0211639) [215.872]
        Width of scan-area.
    -y 0..263.489mm (in quants of 0.0211639) [279.364]
        Height of scan-area.
    --page-width 0..224.846mm (in quants of 0.0211639) [215.872]
        Must be set properly to align scanning window
    --page-height 0..863.489mm (in quants of 0.0211639) [279.364]
        Must be set properly to eject pages
"""
    options = Options(output)
    assert options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": 0},
        0,
    ), "page-width supports_paper"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": -10},
        0,
    ), "page-width paper crosses top border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 0, "t": 600},
        0,
    ), "page-width paper crosses bottom border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": -10, "t": 0},
        0,
    ), "page-width paper crosses left border"
    assert not options.supports_paper(
        {"x": 210, "y": 297, "l": 20, "t": 0},
        0,
    ), "page-width paper crosses right border"
    assert not options.supports_paper(
        {"x": 225, "y": 297, "l": 0, "t": 0},
        0,
    ), "page-width paper too wide"
    assert not options.supports_paper(
        {"x": 210, "y": 870, "l": 0, "t": 0},
        0,
    ), "page-width paper too tall"
    assert options.device == "fujitsu:libusb:002:004", "device name"

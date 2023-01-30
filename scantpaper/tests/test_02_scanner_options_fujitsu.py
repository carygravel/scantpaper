"options from fujitsu backend"
from scanner.options import Options
import pytest


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
        {
            "index": 0,
        },
        {
            "index": 1,
            "title": "Scan Mode",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "source",
            "title": "Source",
            "index": 2,
            "desc": "Selects the scan source (such as a document-feeder).",
            "val": "ADF Front",
            "constraint": ["ADF Front", "ADF Back", "ADF Duplex"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "mode",
            "title": "Mode",
            "index": 3,
            "desc": "Selects the scan mode (e.g., lineart, monochrome, or color).",
            "val": "Gray",
            "constraint": ["Gray", "Color"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "resolution",
            "title": "Resolution",
            "index": 4,
            "desc": "Sets the horizontal resolution of the scanned image.",
            "val": 600,
            "constraint": {
                "min": 100,
                "max": 600,
                "quant": 1,
            },
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "y-resolution",
            "title": "Y resolution",
            "index": 5,
            "desc": "Sets the vertical resolution of the scanned image.",
            "val": 600,
            "constraint": {
                "min": 50,
                "max": 600,
                "quant": 1,
            },
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 6,
            "title": "Geometry",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "tl-x",
            "title": "Top-left x",
            "index": 7,
            "desc": "Top-left x position of scan area.",
            "val": 0.0,
            "constraint": {
                "min": 0.0,
                "max": 224.846,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "tl-y",
            "title": "Top-left y",
            "index": 8,
            "desc": "Top-left y position of scan area.",
            "val": 0.0,
            "constraint": {
                "min": 0.0,
                "max": 863.489,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-x",
            "title": "Bottom-right x",
            "desc": "Bottom-right x position of scan area.",
            "index": 9,
            "val": 215.872,
            "constraint": {
                "min": 0.0,
                "max": 224.846,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-y",
            "title": "Bottom-right y",
            "desc": "Bottom-right y position of scan area.",
            "index": 10,
            "val": 279.364,
            "constraint": {
                "min": 0.0,
                "max": 863.489,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "pagewidth",
            "title": "Pagewidth",
            "index": 11,
            "desc": "Must be set properly to align scanning window",
            "val": 215.872,
            "constraint": {
                "min": 0.0,
                "max": 224.846,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "pageheight",
            "title": "Pageheight",
            "index": 12,
            "desc": "Must be set properly to eject pages",
            "val": 279.364,
            "constraint": {
                "min": 0.0,
                "max": 863.489,
                "quant": 0.0211639,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 13,
            "title": "Enhancement",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "rif",
            "title": "Rif",
            "index": 14,
            "desc": "Reverse image format",
            "val": False,
            "unit": "UNIT_NONE",
            "type": "TYPE_BOOL",
            "constraint_type": "CONSTRAINT_NONE",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 15,
            "title": "Advanced",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "dropoutcolor",
            "title": "Dropoutcolor",
            "index": 16,
            "desc": "One-pass scanners use only one color during gray or binary "
            "scanning, useful for colored paper or ink",
            "val": "Default",
            "constraint": ["Default", "Red", "Green", "Blue"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "sleeptimer",
            "title": "Sleeptimer",
            "index": 17,
            "desc": "Time in minutes until the internal power supply switches to sleep mode",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 60,
                "quant": 1,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 18,
            "title": "Sensors and Buttons",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
    ]
    assert options.array == that, "fujitsu"
    assert options.num_options() == 19, "number of options"
    assert options.by_index(2)["name"] == "source", "by_index"
    assert options.by_name("source")["name"] == "source", "by_name"
    assert options.by_title("Source")["name"] == "source", "by_title"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 1
    ), "supports_paper"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": -10,
            },
            0,
        )
        == 0
    ), "paper crosses top border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 600,
            },
            0,
        )
        == 0
    ), "paper crosses bottom border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": -10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses left border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 20,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses right border"
    assert (
        options.supports_paper(
            {
                "x": 225,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper too wide"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 870,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
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
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 1
    ), "page-width supports_paper"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": -10,
            },
            0,
        )
        == 0
    ), "page-width paper crosses top border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 600,
            },
            0,
        )
        == 0
    ), "page-width paper crosses bottom border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": -10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper crosses left border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 20,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper crosses right border"
    assert (
        options.supports_paper(
            {
                "x": 225,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper too wide"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 870,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper too tall"
    assert options.device == "fujitsu:libusb:002:004", "device name"

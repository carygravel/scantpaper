"options from canoscan_FB_630P backend"
from scanner.options import Options
import pytest


def test_1():
    "options from canoscan_FB_630P backend"
    filename = "scantpaper/tests/scanners/canoscan_FB_630P"
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
            "name": "resolution",
            "title": "Resolution",
            "index": 1,
            "desc": "Sets the resolution of the scanned image.",
            "val": 75,
            "constraint": [75, 150, 300, 600],
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_WORD_LIST",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "mode",
            "title": "Mode",
            "index": 2,
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
            "name": "depth",
            "title": "Depth",
            "index": 3,
            "desc": 'Number of bits per sample, typical values are 1 for "line-art" '
            "and 8 for multibit scans.",
            "val": 8,
            "constraint": [8, 12],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_WORD_LIST",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "tl-x",
            "title": "Top-left x",
            "index": 4,
            "desc": "Top-left x position of scan area.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 215,
                "quant": 1869504867,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "tl-y",
            "title": "Top-left y",
            "index": 5,
            "desc": "Top-left y position of scan area.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 296,
                "quant": 1852795252,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-x",
            "title": "Bottom-right x",
            "desc": "Bottom-right x position of scan area.",
            "index": 6,
            "val": 100,
            "constraint": {
                "min": 3,
                "max": 216,
                "quant": 16,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-y",
            "title": "Bottom-right y",
            "desc": "Bottom-right y position of scan area.",
            "index": 7,
            "val": 100,
            "constraint": {
                "min": 1,
                "max": 297,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "quality-cal",
            "title": "Quality cal",
            "val": "",
            "index": 8,
            "desc": "Do a quality white-calibration",
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_NONE",
            "type": "TYPE_BUTTON",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 0,
        },
    ]
    assert options.array == that, "canoscan_FB_630P"
    assert options.device == "canon_pp:parport0", "device name"

"options from officejet_5500 backend"
from scanner.options import Options
import pytest


def test_1():
    "options from officejet_5500 backend"
    filename = "scantpaper/tests/scanners/officejet_5500"
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
            "title": "Scan mode",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "mode",
            "title": "Mode",
            "index": 2,
            "desc": "Selects the scan mode (e.g., lineart, monochrome, or color).",
            "val": "Color",
            "constraint": ["Lineart", "Grayscale", "Color"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "resolution",
            "title": "Resolution",
            "index": 3,
            "desc": "Sets the resolution of the scanned image.",
            "val": 75,
            "constraint": {
                "min": 75,
                "max": 600,
            },
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 4,
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
            "name": "contrast",
            "title": "Contrast",
            "index": 5,
            "desc": "Controls the contrast of the acquired image.",
            "constraint": {
                "min": 0,
                "max": 100,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 1,
        },
        {
            "name": "compression",
            "title": "Compression",
            "index": 6,
            "desc": "Selects the scanner compression method for faster scans, "
            "possibly at the expense of image quality.",
            "val": "JPEG",
            "constraint": ["None", "JPEG"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "jpeg-compression-factor",
            "title": "JPEG compression factor",
            "index": 7,
            "desc": "Sets the scanner JPEG compression factor.  Larger numbers "
            "mean better compression, and smaller numbers mean better image quality.",
            "val": 10,
            "constraint": {
                "min": 0,
                "max": 100,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "batch-scan",
            "title": "Batch scan",
            "index": 8,
            "desc": 'Guarantees that a "no documents" condition will be returned '
            "after the last scanned page, to prevent endless flatbed scans after "
            "a batch scan. For some models, option changes in the middle of a "
            "batch scan don't take effect until after the last page.",
            "val": False,
            "unit": "UNIT_NONE",
            "type": "TYPE_BOOL",
            "constraint_type": "CONSTRAINT_NONE",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "source",
            "title": "Source",
            "index": 9,
            "desc": "Selects the desired scan source for models with both flatbed "
            'and automatic document feeder (ADF) capabilities.  The "Auto" setting '
            "means that the ADF will be used if it's loaded, and the flatbed (if "
            "present) will be used otherwise.",
            "val": "Auto",
            "constraint": ["Auto", "Flatbed", "ADF"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "duplex",
            "title": "Duplex",
            "index": 10,
            "desc": "Enables scanning on both sides of the page for models with "
            'duplex-capable document feeders.  For pages printed in "book"-style '
            "duplex mode, one side will be scanned upside-down.  This feature is experimental.",
            "unit": "UNIT_NONE",
            "type": "TYPE_BOOL",
            "constraint_type": "CONSTRAINT_NONE",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 1,
        },
        {
            "index": 11,
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
            "name": "length-measurement",
            "title": "Length measurement",
            "index": 12,
            "desc": "Selects how the scanned image length is measured and reported, "
            "which is impossible to know in advance for scrollfed scans.",
            "val": "Padded",
            "constraint": ["Unknown", "Approximate", "Padded"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "tl-x",
            "title": "Top-left x",
            "index": 13,
            "desc": "Top-left x position of scan area.",
            "val": 0.0,
            "constraint": {
                "min": 0.0,
                "max": 215.9,
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
            "index": 14,
            "desc": "Top-left y position of scan area.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 381,
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
            "index": 15,
            "val": 215.9,
            "constraint": {
                "min": 0.0,
                "max": 215.9,
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
            "index": 16,
            "val": 381,
            "constraint": {
                "min": 0,
                "max": 381,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
    ]
    assert options.array == that, "officejet_5500"
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
                "t": 90,
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
                "l": 10,
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
    assert (
        options.device == "hpaio:/usb/officejet_5500_series?serial=MY42QF209H96"
    ), "device name"

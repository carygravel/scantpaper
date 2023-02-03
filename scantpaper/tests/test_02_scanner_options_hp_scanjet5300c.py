"options from hp_scanjet5300c backend"
from scanner.options import Options
import pytest


def test_1():
    "options from hp_scanjet5300c backend"
    filename = "scantpaper/tests/scanners/hp_scanjet5300c"
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
            "constraint": [
                "Lineart",
                "Dithered",
                "Gray",
                "12bit Gray",
                "Color",
                "12bit Color",
            ],
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
            "val": 150,
            "constraint": {
                "min": 100,
                "max": 1200,
                "quant": 5,
            },
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "speed",
            "title": "Speed",
            "index": 4,
            "desc": "Determines the speed at which the scan proceeds.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 4,
                "quant": 1,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "preview",
            "title": "Preview",
            "index": 5,
            "desc": "Request a preview-quality scan.",
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
            "index": 6,
            "desc": "Selects the scan source (such as a document-feeder).",
            "val": "Normal",
            "constraint": ["Normal", "ADF"],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 7,
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
            "index": 8,
            "desc": "Top-left x position of scan area.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 216,
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
            "index": 9,
            "desc": "Top-left y position of scan area.",
            "val": 0,
            "constraint": {
                "min": 0,
                "max": 296,
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
            "index": 10,
            "val": 216,
            "constraint": {
                "min": 0,
                "max": 216,
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
            "index": 11,
            "val": 296,
            "constraint": {
                "min": 0,
                "max": 296,
            },
            "unit": "UNIT_MM",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "index": 12,
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
            "name": "brightness",
            "title": "Brightness",
            "index": 13,
            "desc": "Controls the brightness of the acquired image.",
            "val": 0,
            "constraint": {
                "min": -100,
                "max": 100,
                "quant": 1,
            },
            "unit": "UNIT_PERCENT",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "contrast",
            "title": "Contrast",
            "index": 14,
            "desc": "Controls the contrast of the acquired image.",
            "val": 0,
            "constraint": {
                "min": -100,
                "max": 100,
                "quant": 1,
            },
            "unit": "UNIT_PERCENT",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "quality-scan",
            "title": "Quality scan",
            "index": 15,
            "desc": "Turn on quality scanning (slower but better).",
            "val": True,
            "unit": "UNIT_NONE",
            "type": "TYPE_BOOL",
            "constraint_type": "CONSTRAINT_NONE",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "quality-cal",
            "title": "Quality cal",
            "index": 16,
            "desc": "Do a quality white-calibration",
            "val": True,
            "unit": "UNIT_NONE",
            "type": "TYPE_BOOL",
            "constraint_type": "CONSTRAINT_NONE",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "gamma-table",
            "title": "Gamma table",
            "index": 17,
            "desc": "Gamma-correction table.  In color mode this option equally "
            "affects the red, green, and blue channels simultaneously (i.e., it "
            "is an intensity gamma table).",
            "constraint": {
                "min": 0,
                "max": 255,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 255,
        },
        {
            "name": "red-gamma-table",
            "title": "Red gamma table",
            "index": 18,
            "desc": "Gamma-correction table for the red band.",
            "constraint": {
                "min": 0,
                "max": 255,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 255,
        },
        {
            "name": "green-gamma-table",
            "title": "Green gamma table",
            "index": 19,
            "desc": "Gamma-correction table for the green band.",
            "constraint": {
                "min": 0,
                "max": 255,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 255,
        },
        {
            "name": "blue-gamma-table",
            "title": "Blue gamma table",
            "index": 20,
            "desc": "Gamma-correction table for the blue band.",
            "constraint": {
                "min": 0,
                "max": 255,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 255,
        },
        {
            "name": "frame",
            "title": "Frame",
            "index": 21,
            "desc": "Selects the number of the frame to scan",
            "constraint": {
                "min": 0,
                "max": 0,
            },
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 1,
        },
        {
            "name": "power-save-time",
            "title": "Power save time",
            "index": 22,
            "desc": "Allows control of the scanner's power save timer, dimming "
            "or turning off the light.",
            "val": 65535,
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_NONE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "nvram-values",
            "title": "Nvram values",
            "index": 23,
            "desc": "Allows access obtaining the scanner's NVRAM values as pretty printed text.",
            "val": """Vendor: HP      \nModel: ScanJet 5300C   \nFirmware: 4.00
Serial: 3119ME
Manufacturing date: 0-0-0
First scan date: 65535-0-0
Flatbed scans: 65547
Pad scans: -65536
ADF simplex scans: 136183808""",
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_NONE",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
    ]
    assert options.array == that, "hp_scanjet5300c"
    assert options.device == "avision:libusb:001:005", "device name"

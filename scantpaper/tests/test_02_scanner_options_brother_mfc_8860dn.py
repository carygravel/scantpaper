"options from Brother_MFC-8860DN backend"
from scanner.options import Options
import pytest


def test_1():
    "options from Brother_MFC-8860DN backend"
    filename = "scantpaper/tests/scanners/Brother_MFC-8860DN"
    try:
        with open(filename, "r", encoding="utf-8") as fhd:
            output = fhd.read()
    except IOError:
        pytest.skip("source tree not found")
        return
    options = Options(output)
    that = [
        {"index": 0,},
        {
            "title": "Mode",
            "index": 1,
            "type": "TYPE_GROUP",
            "cap": "",
            "max_values": 0,
            "name": "",
            "unit": "UNIT_NONE",
            "desc": "",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "name": "mode",
            "title": "Mode",
            "index": 2,
            "desc": "Select the scan mode",
            "val": "24bit Color",
            "constraint": [
                "Black & White",
                "Gray[Error Diffusion]",
                "True Gray",
                "24bit Color",
                "24bit Color[Fast]",
            ],
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "unit": "UNIT_NONE",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "resolution",
            "title": "Resolution",
            "index": 3,
            "desc": "Sets the resolution of the scanned image.",
            "val": 200,
            "constraint": [100, 150, 200, 300, 400, 600, 1200, 2400, 4800, 9600,],
            "unit": "UNIT_DPI",
            "constraint_type": "CONSTRAINT_WORD_LIST",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "source",
            "title": "Source",
            "index": 4,
            "desc": "Selects the scan source (such as a document-feeder).",
            "val": "Automatic Document Feeder",
            "constraint": [
                "FlatBed",
                "Automatic Document Feeder",
                "Automatic Document Feeder(Duplex)",
            ],
            "unit": "UNIT_NONE",
            "constraint_type": "CONSTRAINT_STRING_LIST",
            "type": "TYPE_STRING",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "brightness",
            "title": "Brightness",
            "index": 5,
            "desc": "Controls the brightness of the acquired image.",
            "constraint": {"min": -50, "max": 50, "quant": 1,},
            "unit": "UNIT_PERCENT",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
            "max_values": 1,
        },
        {
            "name": "contrast",
            "title": "Contrast",
            "index": 6,
            "desc": "Controls the contrast of the acquired image.",
            "constraint": {"min": -50, "max": 50, "quant": 1,},
            "unit": "UNIT_PERCENT",
            "constraint_type": "CONSTRAINT_RANGE",
            "type": "TYPE_INT",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT" + "CAP_INACTIVE",
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
            "val": 0.0,
            "constraint": {"min": 0.0, "max": 215.9, "quant": 0.0999908,},
            "constraint_type": "CONSTRAINT_RANGE",
            "unit": "UNIT_MM",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "tl-y",
            "title": "Top-left y",
            "index": 9,
            "desc": "Top-left y position of scan area.",
            "val": 0.0,
            "constraint": {"min": 0.0, "max": 355.6, "quant": 0.0999908,},
            "constraint_type": "CONSTRAINT_RANGE",
            "unit": "UNIT_MM",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-x",
            "title": "Bottom-right x",
            "desc": "Bottom-right x position of scan area.",
            "index": 10,
            "val": 215.88,
            "constraint": {"min": 0.0, "max": 215.9, "quant": 0.0999908,},
            "constraint_type": "CONSTRAINT_RANGE",
            "unit": "UNIT_MM",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
        {
            "name": "br-y",
            "title": "Bottom-right y",
            "desc": "Bottom-right y position of scan area.",
            "index": 11,
            "val": 355.567,
            "constraint": {"min": 0.0, "max": 355.6, "quant": 0.0999908,},
            "constraint_type": "CONSTRAINT_RANGE",
            "unit": "UNIT_MM",
            "type": "TYPE_FIXED",
            "cap": "CAP_SOFT_DETECT" + "CAP_SOFT_SELECT",
            "max_values": 1,
        },
    ]
    assert options.array == that, "Brother_MFC-8860DN"
    assert options.device == "brother2:net1;dev0", "device name"
    assert options.can_duplex() is True, "can duplex"

"options from brother backend"
from scanner.options import Options, Option
import pytest
from frontend import enums


def test_1():
    "options from brother backend"
    filename = "scantpaper/tests/scanners/brother"
    try:
        with open(filename, "r", encoding="utf-8") as fhd:
            output = fhd.read()
    except IOError:
        pytest.skip("source tree not found")
        return
    options = Options(output)
    that = [
        # (index, name, title, desc, type, unit, size, cap, constraint)
        Option(
            0,
            "",
            "Number of options",
            "Read-only option that specifies how many options a specific device supports.",
            1,
            0,
            4,
            4,
            None,
        ),
        Option(1, "", "Mode", "", enums.TYPE_GROUP, enums.UNIT_NONE, 0, 0, None),
        Option(
            2,
            "mode",
            "Mode",
            "Select the scan mode",
            enums.TYPE_STRING,
            enums.UNIT_NONE,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            [
                "Black & White",
                "Gray[Error Diffusion]",
                "True Gray",
                "24bit Color",
                "24bit Color[Fast]",
            ],
        ),
        Option(
            3,
            "resolution",
            "Resolution",
            "Sets the resolution of the scanned image.",
            enums.TYPE_INT,
            enums.UNIT_DPI,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            [100, 150, 200, 300, 400, 600, 1200, 2400, 4800, 9600],
        ),
        Option(
            4,
            "source",
            "Source",
            "Selects the scan source (such as a document-feeder).",
            enums.TYPE_STRING,
            enums.UNIT_NONE,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            ["FlatBed", "Automatic Document Feeder"],
        ),
        Option(
            5,
            "brightness",
            "Brightness",
            "Controls the brightness of the acquired image.",
            enums.TYPE_INT,
            enums.UNIT_PERCENT,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            (-50, 50, 1),
        ),
        Option(
            6,
            "contrast",
            "Contrast",
            "Controls the contrast of the acquired image.",
            enums.TYPE_INT,
            enums.UNIT_PERCENT,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            (-50, 50, 1),
        ),
        Option(
            7,
            "",
            "Geometry",
            "",
            enums.TYPE_GROUP,
            enums.UNIT_NONE,
            0,
            0,
            None,
        ),
        Option(
            8,
            "tl-x",
            "Top-left x",
            "Top-left x position of scan area.",
            enums.TYPE_FIXED,
            enums.UNIT_MM,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            (0.0, 210.0, 0.0999908),
        ),
        Option(
            9,
            "tl-y",
            "Top-left y",
            "Top-left y position of scan area.",
            enums.TYPE_FIXED,
            enums.UNIT_MM,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            (0.0, 297.0, 0.0999908),
        ),
        Option(
            10,
            "br-x",
            "Bottom-right x",
            "Bottom-right x position of scan area.",
            enums.TYPE_FIXED,
            enums.UNIT_MM,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            (0.0, 210.0, 0.0999908),
        ),
        Option(
            11,
            "br-y",
            "Bottom-right y",
            "Bottom-right y position of scan area.",
            enums.TYPE_FIXED,
            enums.UNIT_MM,
            1,
            enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            (0.0, 297.0, 0.0999908),
        ),
    ]
    assert options.array == that, "brother"
    assert options.device == "brother2:net1;dev0", "device name"

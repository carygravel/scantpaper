"options from brother backend"
from scanner.options import Options, Option
import pytest
import sane


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
        Option(
            1, "", "Mode", "", sane._sane.TYPE_GROUP, sane._sane.UNIT_NONE, 0, 0, None
        ),
        Option(
            2,
            "mode",
            "Mode",
            "Select the scan mode",
            sane._sane.TYPE_STRING,
            sane._sane.UNIT_NONE,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
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
            sane._sane.TYPE_INT,
            sane._sane.UNIT_DPI,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            [100, 150, 200, 300, 400, 600, 1200, 2400, 4800, 9600],
        ),
        Option(
            4,
            "source",
            "Source",
            "Selects the scan source (such as a document-feeder).",
            sane._sane.TYPE_STRING,
            sane._sane.UNIT_NONE,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            ["FlatBed", "Automatic Document Feeder"],
        ),
        Option(
            5,
            "brightness",
            "Brightness",
            "Controls the brightness of the acquired image.",
            sane._sane.TYPE_INT,
            sane._sane.UNIT_PERCENT,
            1,
            sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            (-50, 50, 1),
        ),
        Option(
            6,
            "contrast",
            "Contrast",
            "Controls the contrast of the acquired image.",
            sane._sane.TYPE_INT,
            sane._sane.UNIT_PERCENT,
            1,
            sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            (-50, 50, 1),
        ),
        Option(
            7,
            "",
            "Geometry",
            "",
            sane._sane.TYPE_GROUP,
            sane._sane.UNIT_NONE,
            0,
            0,
            None,
        ),
        Option(
            8,
            "tl-x",
            "Top-left x",
            "Top-left x position of scan area.",
            sane._sane.TYPE_FIXED,
            sane._sane.UNIT_MM,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            (0.0, 210.0, 0.0999908),
        ),
        Option(
            9,
            "tl-y",
            "Top-left y",
            "Top-left y position of scan area.",
            sane._sane.TYPE_FIXED,
            sane._sane.UNIT_MM,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            (0.0, 297.0, 0.0999908),
        ),
        Option(
            10,
            "br-x",
            "Bottom-right x",
            "Bottom-right x position of scan area.",
            sane._sane.TYPE_FIXED,
            sane._sane.UNIT_MM,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            (0.0, 210.0, 0.0999908),
        ),
        Option(
            11,
            "br-y",
            "Bottom-right y",
            "Bottom-right y position of scan area.",
            sane._sane.TYPE_FIXED,
            sane._sane.UNIT_MM,
            1,
            sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            (0.0, 297.0, 0.0999908),
        ),
    ]
    assert options.array == that, "brother"
    assert options.device == "brother2:net1;dev0", "device name"

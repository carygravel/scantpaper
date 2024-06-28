"options from Brother_MFC-8860DN backend"
from scanner.options import Options, Option
import pytest
from frontend import enums


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
            title="Mode",
            index=1,
            type=enums.TYPE_GROUP,
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            constraint=None,
        ),
        Option(
            name="mode",
            title="Mode",
            index=2,
            desc="Select the scan mode",
            constraint=[
                "Black & White",
                "Gray[Error Diffusion]",
                "True Gray",
                "24bit Color",
                "24bit Color[Fast]",
            ],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="resolution",
            title="Resolution",
            index=3,
            desc="Sets the resolution of the scanned image.",
            constraint=[
                100,
                150,
                200,
                300,
                400,
                600,
                1200,
                2400,
                4800,
                9600,
            ],
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="source",
            title="Source",
            index=4,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=[
                "FlatBed",
                "Automatic Document Feeder",
                "Automatic Document Feeder(Duplex)",
            ],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="brightness",
            title="Brightness",
            index=5,
            desc="Controls the brightness of the acquired image.",
            constraint=(-50, 50, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="contrast",
            title="Contrast",
            index=6,
            desc="Controls the contrast of the acquired image.",
            constraint=(-50, 50, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            index=7,
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
            index=8,
            desc="Top-left x position of scan area.",
            constraint=(0.0, 215.9, 0.0999908),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=9,
            desc="Top-left y position of scan area.",
            constraint=(0.0, 355.6, 0.0999908),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=10,
            constraint=(0.0, 215.9, 0.0999908),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=11,
            constraint=(0.0, 355.6, 0.0999908),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
    ]
    assert options.array == that, "Brother_MFC-8860DN"
    assert options.device == "brother2:net1;dev0", "device name"
    assert options.can_duplex(), "can duplex"

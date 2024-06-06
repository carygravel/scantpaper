"options from canoscan_FB_630P backend"
from scanner.options import Options, Option
import pytest
import sane


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
            name="resolution",
            title="Resolution",
            index=1,
            desc="Sets the resolution of the scanned image.",
            constraint=[75, 150, 300, 600],
            unit=sane._sane.UNIT_DPI,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="mode",
            title="Mode",
            index=2,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            constraint=["Gray", "Color"],
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_STRING,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="depth",
            title="Depth",
            index=3,
            desc='Number of bits per sample, typical values are 1 for "line-art" '
            "and 8 for multibit scans.",
            constraint=[8, 12],
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-x",
            title="Top-left x",
            index=4,
            desc="Top-left x position of scan area.",
            constraint=(
                0,
                215,
                1869504867,
            ),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=5,
            desc="Top-left y position of scan area.",
            constraint=(
                0,
                296,
                1852795252,
            ),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=6,
            constraint=(
                3,
                216,
                16,
            ),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=7,
            constraint=(1, 297, 0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="quality-cal",
            title="Quality cal",
            index=8,
            desc="Do a quality white-calibration",
            unit=sane._sane.UNIT_NONE,
            constraint=None,
            type=sane._sane.TYPE_BUTTON,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=0,
        ),
    ]
    assert options.array == that, "canoscan_FB_630P"
    assert options.device == "canon_pp:parport0", "device name"

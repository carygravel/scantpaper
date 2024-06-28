"options from hp_6200 backend"
from scanner.options import Options, Option
import pytest
from frontend import enums


def test_1():
    "options from hp_6200 backend"
    filename = "scantpaper/tests/scanners/hp_6200"
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
            title="Scan mode",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="mode",
            title="Mode",
            index=2,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            constraint=["Lineart", "Grayscale", "Color"],
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
            constraint=(75, 600, 0),
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=4,
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
            name="contrast",
            title="Contrast",
            index=5,
            desc="Controls the contrast of the acquired image.",
            constraint=(0, 100, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="compression",
            title="Compression",
            index=6,
            desc="Selects the scanner compression method for faster scans, "
            "possibly at the expense of image quality.",
            constraint=["None", "JPEG"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="jpeg-compression-factor",
            title="JPEG compression factor",
            index=7,
            desc="Sets the scanner JPEG compression factor.  Larger numbers "
            "mean better compression, and smaller numbers mean better image quality.",
            constraint=(0, 100, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="batch-scan",
            title="Batch scan",
            index=8,
            desc='Guarantees that a "no documents" condition will be returned '
            "after the last scanned page, to prevent endless flatbed scans after a "
            "batch scan. For some models, option changes in the middle of a batch "
            "scan don't take effect until after the last page.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="source",
            title="Source",
            index=9,
            desc="Selects the desired scan source for models with both flatbed "
            'and automatic document feeder (ADF) capabilities.  The "Auto" setting '
            "means that the ADF will be used if it's loaded, and the flatbed (if "
            "present) will be used otherwise.",
            constraint=["Auto", "Flatbed", "ADF"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="duplex",
            title="Duplex",
            index=10,
            desc="Enables scanning on both sides of the page for models with "
            'duplex-capable document feeders.  For pages printed in "book"-style '
            "duplex mode, one side will be scanned upside-down.  This feature is "
            "experimental.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=11,
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
            name="length-measurement",
            title="Length measurement",
            index=12,
            desc="Selects how the scanned image length is measured and reported, "
            "which is impossible to know in advance for scrollfed scans.",
            constraint=["Unknown", "Approximate", "Padded"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-x",
            title="Top-left x",
            index=13,
            desc="Top-left x position of scan area.",
            constraint=(0.0, 215.9, 0.0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=14,
            desc="Top-left y position of scan area.",
            constraint=(0, 381, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=15,
            constraint=(0, 215.9, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=16,
            constraint=(0, 381, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
    ]
    assert options.array == that, "hp_6200"
    assert (
        options.device == "hpaio:/usb/Officejet_6200_series?serial=CN4AKCE1ZY0453"
    ), "device name"
    assert options.can_duplex(), "can duplex"

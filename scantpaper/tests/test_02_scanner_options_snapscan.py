"options from snapscan backend"

from scanner.options import Options, Option
import pytest
from frontend import enums


def test_1():
    "options from snapscan backend"
    filename = "scantpaper/tests/scanners/snapscan"
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
            title="Scan Mode",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="resolution",
            title="Resolution",
            index=2,
            desc="Sets the resolution of the scanned image.",
            constraint=[50, 75, 100, 150, 200, 300, 450, 600],
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="preview",
            title="Preview",
            index=3,
            desc="Request a preview-quality scan.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="mode",
            title="Mode",
            index=4,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            constraint=["Color", "Halftone", "Gray", "Lineart"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="preview-mode",
            title="Preview mode",
            index=5,
            desc="Select the mode for previews. Greyscale previews usually "
            "give the best combination of speed and detail.",
            constraint=["Auto", "Color", "Halftone", "Gray", "Lineart"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="high-quality",
            title="High quality",
            index=6,
            desc="Highest quality but lower speed",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="source",
            title="Source",
            index=7,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=["Flatbed"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT
            + enums.CAP_SOFT_SELECT
            + enums.CAP_INACTIVE
            + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            index=8,
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
            index=9,
            desc="Top-left x position of scan area.",
            constraint=(0, 216, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=10,
            desc="Top-left y position of scan area.",
            constraint=(0, 297, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=11,
            constraint=(0, 216, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=12,
            constraint=(0, 297, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="predef-window",
            title="Predef window",
            index=13,
            desc="Provides standard scanning areas for photographs, printed pages and the like.",
            constraint=["None", "6x4 (inch)", "8x10 (inch)", "8.5x11 (inch)"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=14,
            title="Enhancement",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="depth",
            title="Depth",
            index=15,
            desc='Number of bits per sample, typical values are 1 for "line-art" '
            "and 8 for multibit scans.",
            constraint=[8],
            unit=enums.UNIT_BIT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="quality-cal",
            title="Quality cal",
            index=16,
            desc="Do a quality white-calibration",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="halftoning",
            title="Halftoning",
            index=17,
            desc="Selects whether the acquired image should be halftoned (dithered).",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="halftone-pattern",
            title="Halftone pattern",
            index=18,
            desc="Defines the halftoning (dithering) pattern for scanning halftoned images.",
            constraint=["DispersedDot8x8", "DispersedDot16x16"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="custom-gamma",
            title="Custom gamma",
            index=19,
            desc="Determines whether a builtin or a custom gamma-table should be used.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="analog-gamma-bind",
            title="Analog gamma bind",
            index=20,
            desc="In RGB-mode use same values for each color",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="analog-gamma",
            title="Analog gamma",
            index=21,
            desc="Analog gamma-correction",
            constraint=(0, 4, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="analog-gamma-r",
            title="Analog gamma r",
            index=22,
            desc="Analog gamma-correction for red",
            constraint=(0.0, 4.0, 0.0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="analog-gamma-g",
            title="Analog gamma g",
            index=23,
            desc="Analog gamma-correction for green",
            constraint=(0.0, 4.0, 0.0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="analog-gamma-b",
            title="Analog gamma b",
            index=24,
            desc="Analog gamma-correction for blue",
            constraint=(0.0, 4.0, 0.0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="gamma-table",
            title="Gamma table",
            index=25,
            desc="Gamma-correction table.  In color mode this option equally "
            "affects the red, green, and blue channels simultaneously (i.e., it "
            "is an intensity gamma table).",
            constraint=(0, 65535, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="red-gamma-table",
            title="Red gamma table",
            index=26,
            desc="Gamma-correction table for the red band.",
            constraint=(0, 65535, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="green-gamma-table",
            title="Green gamma table",
            index=27,
            desc="Gamma-correction table for the green band.",
            constraint=(0, 65535, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="blue-gamma-table",
            title="Blue gamma table",
            index=28,
            desc="Gamma-correction table for the blue band.",
            constraint=(0, 65535, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="negative",
            title="Negative",
            index=29,
            desc="Swap black and white",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT
            + enums.CAP_SOFT_SELECT
            + enums.CAP_INACTIVE
            + enums.CAP_AUTOMATIC,
            size=1,
        ),
        Option(
            name="threshold",
            title="Threshold",
            index=30,
            desc="Select minimum-brightness to get a white point",
            constraint=(0, 100, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="brightness",
            title="Brightness",
            index=31,
            desc="Controls the brightness of the acquired image.",
            constraint=(-400, 400, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="contrast",
            title="Contrast",
            index=32,
            desc="Controls the contrast of the acquired image.",
            constraint=(-100, 400, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=33,
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
            name="rgb-lpr",
            title="Rgb lpr",
            index=34,
            desc="Number of scan lines to request in a SCSI read. Changing "
            "this parameter allows you to tune the speed at which data is read "
            "from the scanner during scans. If this is set too low, the scanner "
            "will have to stop periodically in the middle of a scan; if it's set "
            "too high, X-based frontends may stop responding to X events and your "
            "system could bog down.",
            constraint=(1, 50, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="gs-lpr",
            title="Gs lpr",
            index=35,
            desc="Number of scan lines to request in a SCSI read. Changing this "
            "parameter allows you to tune the speed at which data is read from the "
            "scanner during scans. If this is set too low, the scanner will have "
            "to stop periodically in the middle of a scan; if it's set too high, "
            "X-based frontends may stop responding to X events and your system "
            "could bog down.",
            constraint=(1, 50, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
    ]
    assert options.array == that, "snapscan"
    assert options.device == "snapscan:/dev/uscanner0", "device name"

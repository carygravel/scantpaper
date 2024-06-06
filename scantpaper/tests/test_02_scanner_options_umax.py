"options from umax backend"
from scanner.options import Options, Option
import pytest
import sane


def test_1():
    "options from umax backend"
    filename = "scantpaper/tests/scanners/umax"
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
            unit=sane._sane.UNIT_NONE,
            desc="",
            type=sane._sane.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="mode",
            title="Mode",
            index=2,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            constraint=["Lineart", "Gray", "Color"],
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_STRING,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="source",
            title="Source",
            index=3,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=["Flatbed"],
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_STRING,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="resolution",
            title="Resolution",
            index=4,
            desc="Sets the resolution of the scanned image.",
            constraint=(5, 300, 5),
            unit=sane._sane.UNIT_DPI,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="y-resolution",
            title="Y resolution",
            index=5,
            desc="Sets the vertical resolution of the scanned image.",
            constraint=(5, 600, 5),
            unit=sane._sane.UNIT_DPI,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="resolution-bind",
            title="Resolution bind",
            index=6,
            desc="Use same values for X and Y resolution",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="negative",
            title="Negative",
            index=7,
            desc="Swap black and white",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            index=8,
            title="Geometry",
            cap=0,
            size=0,
            name="",
            unit=sane._sane.UNIT_NONE,
            desc="",
            type=sane._sane.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="tl-x",
            title="Top-left x",
            index=9,
            desc="Top-left x position of scan area.",
            constraint=(0.0, 215.9, 0.0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=10,
            desc="Top-left y position of scan area.",
            constraint=(0.0, 297.18, 0.0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=11,
            constraint=(0.0, 215.9, 0.0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=12,
            constraint=(0.0, 297.18, 0.0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=13,
            title="Enhancement",
            cap=0,
            size=0,
            name="",
            unit=sane._sane.UNIT_NONE,
            desc="",
            type=sane._sane.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="depth",
            title="Depth",
            index=14,
            desc='Number of bits per sample, typical values are 1 for "line-art" '
            "and 8 for multibit scans.",
            constraint=[8],
            unit=sane._sane.UNIT_BIT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="quality-cal",
            title="Quality cal",
            index=15,
            desc="Do a quality white-calibration",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="double-res",
            title="Double res",
            index=16,
            desc="Use lens that doubles optical resolution",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="warmup",
            title="Warmup",
            index=17,
            desc="Warmup lamp before scanning",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="rgb-bind",
            title="Rgb bind",
            index=18,
            desc="In RGB-mode use same values for each color",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="brightness",
            title="Brightness",
            index=19,
            desc="Controls the brightness of the acquired image.",
            constraint=(-100, 100, 1),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="contrast",
            title="Contrast",
            index=20,
            desc="Controls the contrast of the acquired image.",
            constraint=(-100, 100, 1),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="threshold",
            title="Threshold",
            index=21,
            desc="Select minimum-brightness to get a white point",
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="highlight",
            title="Highlight",
            index=22,
            desc='Selects what radiance level should be considered "white".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="highlight-r",
            title="Highlight r",
            index=23,
            desc='Selects what red radiance level should be considered "full red".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="highlight-g",
            title="Highlight g",
            index=24,
            desc='Selects what green radiance level should be considered "full green".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="highlight-b",
            title="Highlight b",
            index=25,
            desc='Selects what blue radiance level should be considered "full blue".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="shadow",
            title="Shadow",
            index=26,
            desc='Selects what radiance level should be considered "black".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="shadow-r",
            title="Shadow r",
            index=27,
            desc='Selects what red radiance level should be considered "black".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="shadow-g",
            title="Shadow g",
            index=28,
            desc='Selects what green radiance level should be considered "black".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="shadow-b",
            title="Shadow b",
            index=29,
            desc='Selects what blue radiance level should be considered "black".',
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="analog-gamma",
            title="Analog gamma",
            index=30,
            desc="Analog gamma-correction",
            constraint=(1.0, 2.0, 0.00999451),
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="analog-gamma-r",
            title="Analog gamma r",
            index=31,
            desc="Analog gamma-correction for red",
            constraint=(1.0, 2.0, 0.00999451),
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="analog-gamma-g",
            title="Analog gamma g",
            index=32,
            desc="Analog gamma-correction for green",
            constraint=(1.0, 2.0, 0.00999451),
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="analog-gamma-b",
            title="Analog gamma b",
            index=33,
            desc="Analog gamma-correction for blue",
            constraint=(1.0, 2.0, 0.00999451),
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="custom-gamma",
            title="Custom gamma",
            index=34,
            desc="Determines whether a builtin or a custom gamma-table should be used.",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="gamma-table",
            title="Gamma table",
            index=35,
            constraint=(0, 255, 0),
            desc="Gamma-correction table.  In color mode this option equally "
            "affects the red, green, and blue channels simultaneously (i.e., it "
            "is an intensity gamma table).",
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=255,
        ),
        Option(
            name="red-gamma-table",
            title="Red gamma table",
            index=36,
            constraint=(0, 255, 0),
            desc="Gamma-correction table for the red band.",
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=255,
        ),
        Option(
            name="green-gamma-table",
            title="Green gamma table",
            index=37,
            constraint=(0, 255, 0),
            desc="Gamma-correction table for the green band.",
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=255,
        ),
        Option(
            name="blue-gamma-table",
            title="Blue gamma table",
            index=38,
            constraint=(0, 255, 0),
            desc="Gamma-correction table for the blue band.",
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=255,
        ),
        Option(
            name="halftone-size",
            title="Halftone size",
            index=39,
            desc="Sets the size of the halftoning (dithering) pattern used when "
            "scanning halftoned images.",
            constraint=[2, 4, 6, 8, 12],
            unit=sane._sane.UNIT_PIXEL,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="halftone-pattern",
            title="Halftone pattern",
            index=40,
            desc="Defines the halftoning (dithering) pattern for scanning halftoned images.",
            constraint=(0, 255, 0),
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            index=41,
            title="Advanced",
            cap=0,
            size=0,
            name="",
            unit=sane._sane.UNIT_NONE,
            desc="",
            type=sane._sane.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="cal-exposure-time",
            title="Cal exposure time",
            index=42,
            desc="Define exposure-time for calibration",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cal-exposure-time-r",
            title="Cal exposure time r",
            index=43,
            desc="Define exposure-time for red calibration",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cal-exposure-time-g",
            title="Cal exposure time g",
            index=44,
            desc="Define exposure-time for green calibration",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cal-exposure-time-b",
            title="Cal exposure time b",
            index=45,
            desc="Define exposure-time for blue calibration",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="scan-exposure-time",
            title="Scan exposure time",
            index=46,
            desc="Define exposure-time for scan",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="scan-exposure-time-r",
            title="Scan exposure time r",
            index=47,
            desc="Define exposure-time for red scan",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="scan-exposure-time-g",
            title="Scan exposure time g",
            index=48,
            desc="Define exposure-time for green scan",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="scan-exposure-time-b",
            title="Scan exposure time b",
            index=49,
            desc="Define exposure-time for blue scan",
            constraint=(0, 0, 0),
            unit=sane._sane.UNIT_MICROSECOND,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="disable-pre-focus",
            title="Disable pre focus",
            index=50,
            desc="Do not calibrate focus",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="manual-pre-focus",
            title="Manual pre focus",
            index=51,
            desc="",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="fix-focus-position",
            title="Fix focus position",
            index=52,
            desc="",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="lens-calibration-in-doc-position",
            title="Lens calibration in doc position",
            index=53,
            desc="Calibrate lens focus in document position",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="holder-focus-position-0mm",
            title="Holder focus position 0mm",
            index=54,
            desc="Use 0mm holder focus position instead of 0.6mm",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cal-lamp-density",
            title="Cal lamp density",
            index=55,
            desc="Define lamp density for calibration",
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="scan-lamp-density",
            title="Scan lamp density",
            index=56,
            desc="Define lamp density for scan",
            constraint=(0, 100, 0),
            unit=sane._sane.UNIT_PERCENT,
            type=sane._sane.TYPE_INT,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="select-exposure-time",
            title="Select exposure time",
            index=57,
            desc="Enable selection of exposure-time",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="select-calibration-exposure-time",
            title="Select calibration exposure time",
            index=58,
            desc="Allow different settings for calibration and scan exposure times",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="select-lamp-density",
            title="Select lamp density",
            index=59,
            desc="Enable selection of lamp density",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BOOL,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="lamp-on",
            title="Lamp on",
            index=60,
            desc="Turn on scanner lamp",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BUTTON,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=0,
        ),
        Option(
            name="lamp-off",
            title="Lamp off",
            index=61,
            desc="Turn off scanner lamp",
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            type=sane._sane.TYPE_BUTTON,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=0,
        ),
        Option(
            name="lamp-off-at-exit",
            title="Lamp off at exit",
            index=62,
            desc="Turn off lamp when program exits",
            type=sane._sane.TYPE_BOOL,
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="batch-scan-start",
            title="Batch scan start",
            index=63,
            desc="set for first scan of batch",
            type=sane._sane.TYPE_BOOL,
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="batch-scan-loop",
            title="Batch scan loop",
            index=64,
            desc="set for middle scans of batch",
            type=sane._sane.TYPE_BOOL,
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="batch-scan-end",
            title="Batch scan end",
            index=65,
            desc="set for last scan of batch",
            type=sane._sane.TYPE_BOOL,
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="batch-scan-next-tl-y",
            title="Batch scan next tl y",
            index=66,
            desc="Set top left Y position for next scan",
            constraint=(0.0, 297.18, 0.0),
            unit=sane._sane.UNIT_MM,
            type=sane._sane.TYPE_FIXED,
            cap=sane._sane.CAP_SOFT_DETECT
            + sane._sane.CAP_SOFT_SELECT
            + sane._sane.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="preview",
            title="Preview",
            index=67,
            desc="Request a preview-quality scan.",
            type=sane._sane.TYPE_BOOL,
            constraint=None,
            unit=sane._sane.UNIT_NONE,
            cap=sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT,
            size=1,
        ),
    ]
    assert options.array == that, "umax"
    assert options.device == "umax:/dev/sg2", "device name"

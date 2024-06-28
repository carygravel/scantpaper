"options from Epson_GT-2500 backend"
from scanner.options import Options, Option
import pytest
from frontend import enums


def test_1():
    "options from Epson_GT-2500 backend"
    filename = "scantpaper/tests/scanners/Epson_GT-2500"
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
            name="mode",
            title="Mode",
            index=2,
            desc="Selects the scan mode (e.g., lineart,monochrome, or color).",
            constraint=["Binary", "Gray", "Color"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="depth",
            title="Depth",
            index=3,
            desc='Number of bits per sample, typical values are 1 for "line-art" '
            "and 8 for multibit scans.",
            constraint=[8, 16],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="halftoning",
            title="Halftoning",
            index=4,
            desc="Selects the halftone.",
            constraint=[
                "None",
                "Halftone A (Hard Tone)",
                "Halftone B (Soft Tone)",
                "Halftone C (Net Screen)",
                "Dither A (4x4 Bayer)",
                "Dither B (4x4 Spiral)",
                "Dither C (4x4 Net Screen)",
                "Dither D (8x4 Net Screen)",
                "Text Enhanced Technology",
                "Download pattern A",
                "Download pattern B",
            ],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="dropout",
            title="Dropout",
            index=5,
            desc="Selects the dropout.",
            constraint=["None", "Red", "Green", "Blue"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="brightness",
            title="Brightness",
            index=6,
            desc="Selects the brightness.",
            constraint=(-4, 3, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="sharpness",
            title="Sharpness",
            index=7,
            desc="",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="gamma-correction",
            title="Gamma correction",
            index=8,
            desc="Selects the gamma correction value from a list of pre-defined "
            "devices or the user defined table, which can be downloaded to the scanner",
            constraint=[
                "Default",
                "User defined (Gamma=1.0)",
                "User defined (Gamma=1.8)",
                "High density printing",
                "Low density printing",
                "High contrast printing",
            ],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="color-correction",
            title="Color correction",
            index=9,
            desc="Sets the color correction table for the selected output device.",
            constraint=[
                "No Correction",
                "User defined",
                "Impact-dot printers",
                "Thermal printers",
                "Ink-jet printers",
                "CRT monitors",
            ],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="resolution",
            title="Resolution",
            index=10,
            desc="Sets the resolution of the scanned image.",
            constraint=(50, 2400, 0),
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="threshold",
            title="Threshold",
            index=11,
            desc="Select minimum-brightness to get a white point",
            constraint=(0, 255, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=12,
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
            name="mirror",
            title="Mirror",
            index=13,
            desc="Mirror the image.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="speed",
            title="Speed",
            index=14,
            desc="Determines the speed at which the scan proceeds.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="auto-area-segmentation",
            title="Auto area segmentation",
            index=15,
            desc="",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="short-resolution",
            title="Short resolution",
            index=16,
            desc="Display short resolution list",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="zoom",
            title="Zoom",
            index=17,
            desc="Defines the zoom factor the scanner will use",
            constraint=(50, 200, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="red-gamma-table",
            title="Red gamma table",
            index=18,
            desc="Gamma-correction table for the red band.",
            constraint=(0, 255, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="green-gamma-table",
            title="Green gamma table",
            index=19,
            desc="Gamma-correction table for the green band.",
            constraint=(0, 255, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="blue-gamma-table",
            title="Blue gamma table",
            index=20,
            desc="Gamma-correction table for the blue band.",
            constraint=(0, 255, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
        ),
        Option(
            name="wait-for-button",
            title="Wait for button",
            index=21,
            desc="After sending the scan command, wait until the button on the "
            "scanner is pressed to actually start the scan process.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            desc="Indicates whether a button on the scanner has been pressed "
            "(read-only option).",
            title="Monitor button",
            index=22,
            constraint=None,
            size=1,
            name="monitor-button",
            type=enums.TYPE_BOOL,
            unit=enums.UNIT_NONE,
        ),
        Option(
            index=23,
            title="Color correction coefficients",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="cct-1",
            title="CCT 1",
            index=24,
            desc="Controls red level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-2",
            title="CCT 2",
            index=25,
            desc="Adds to red based on green level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-3",
            title="CCT 3",
            index=26,
            desc="Adds to red based on blue level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-4",
            title="CCT 4",
            index=27,
            desc="Adds to green based on red level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-5",
            title="CCT 5",
            index=28,
            desc="Controls green level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-6",
            title="CCT 6",
            index=29,
            desc="Adds to green based on blue level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-7",
            title="CCT 7",
            index=30,
            desc="Adds to blue based on red level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-8",
            title="CCT 8",
            index=31,
            desc="Adds to blue based on green level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="cct-9",
            title="CCT 9",
            index=32,
            desc="Control blue level",
            constraint=(-2, 2, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            index=33,
            title="Preview",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="preview",
            title="Preview",
            index=34,
            desc="Request a preview-quality scan.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="preview-speed",
            title="Preview speed",
            index=35,
            desc="",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=36,
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
            index=37,
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
            index=38,
            desc="Top-left y position of scan area.",
            constraint=(0.0, 297.18, 0.0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=39,
            constraint=(0.0, 215.9, 0.0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-y",
            title="Bottom-right y",
            desc="Bottom-right y position of scan area.",
            index=40,
            constraint=(0.0, 297.18, 0.0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_FIXED,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="quick-format",
            title="Quick format",
            index=41,
            desc="",
            constraint=["CD", "A5 portrait", "A5 landscape", "Letter", "A4", "Max"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=42,
            title="Optional equipment",
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            desc="",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            name="source",
            title="Source",
            index=43,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=["Flatbed", "Automatic Document Feeder"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="auto-eject",
            title="Auto eject",
            index=44,
            desc="Eject document after scanning",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="film-type",
            title="Film type",
            index=45,
            desc="",
            constraint=["Positive Film", "Negative Film"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="focus-position",
            title="Focus position",
            index=46,
            desc="Sets the focus position to either the glass or 2.5mm above the glass",
            constraint=["Focus on glass", "Focus 2.5mm above glass"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="bay",
            title="Bay",
            index=47,
            desc="Select bay to scan",
            constraint=[1, 2, 3, 4, 5, 6],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="eject",
            title="Eject",
            index=48,
            desc="Eject the sheet in the ADF",
            unit=enums.UNIT_NONE,
            constraint=None,
            type=enums.TYPE_BUTTON,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=0,
        ),
        Option(
            name="adf_mode",
            title="ADF mode",
            index=49,
            desc="Selects the ADF mode (simplex/duplex)",
            constraint=["Simplex", "Duplex"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
    ]
    assert options.array == that, "epson_GT_2500"
    assert options.device == "epkowa:libusb:006:011", "device name"
    assert options.can_duplex(), "can duplex"

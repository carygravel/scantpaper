"options from test backend"

from scanner.options import Options, Option, within_tolerance
import pytest
from frontend import enums


def test_1():
    "options from test backend"

    filename = "scantpaper/tests/scanners/test"
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
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=1,
            desc="",
            title="Scan Mode",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="mode",
            index=2,
            unit=enums.UNIT_NONE,
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            type=enums.TYPE_STRING,
            constraint=["Gray", "Color"],
            title="Mode",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="depth",
            index=3,
            unit=enums.UNIT_NONE,
            desc="Number of bits per sample, "
            'typical values are 1 for "line-art" and 8 for multibit scans.',
            type=enums.TYPE_INT,
            constraint=[1, 8, 16],
            title="Depth",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="hand-scanner",
            index=4,
            unit=enums.UNIT_NONE,
            desc="Simulate a hand-scanner.  Hand-scanners do not know the "
            "image height a priori.  Instead, they return a height of -1.  "
            "Setting this option allows to test whether a frontend can handle "
            "this correctly.  This option also enables a fixed width of 11 cm.",
            title="Hand scanner",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="three-pass",
            unit=enums.UNIT_NONE,
            index=5,
            desc="Simulate a three-pass scanner. In color mode, three frames are transmitted.",
            title="Three pass",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="three-pass-order",
            index=6,
            unit=enums.UNIT_NONE,
            desc="Set the order of frames in three-pass color mode.",
            title="Three pass order",
            type=enums.TYPE_STRING,
            constraint=["RGB", "RBG", "GBR", "GRB", "BRG", "BGR"],
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="resolution",
            index=7,
            unit=enums.UNIT_DPI,
            desc="Sets the resolution of the scanned image.",
            type=enums.TYPE_INT,
            constraint=(1, 1200, 1),
            title="Resolution",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="source",
            index=8,
            unit=enums.UNIT_NONE,
            desc="If Automatic Document Feeder is selected, the feeder will "
            "be 'empty' after 10 scans.",
            type=enums.TYPE_STRING,
            constraint=["Flatbed", "Automatic Document Feeder"],
            title="Source",
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=9,
            desc="",
            title="Special Options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="test-picture",
            index=10,
            unit=enums.UNIT_NONE,
            desc="Select the kind of test picture. Available options: Solid "
            "black: fills the whole scan with black. Solid white: fills the "
            "whole scan with white. Color pattern: draws various color test "
            "patterns depending on the mode. Grid: draws a black/white grid "
            "with a width and height of 10 mm per square.",
            type=enums.TYPE_STRING,
            constraint=["Solid black", "Solid white", "Color pattern", "Grid"],
            title="Test picture",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="invert-endianess",
            unit=enums.UNIT_NONE,
            index=11,
            desc="Exchange upper and lower byte of image data in 16 bit modes. "
            "This option can be used to test the 16 bit modes of frontends, e.g. "
            "if the frontend uses the correct endianness.",
            title="Invert endianess",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="read-limit",
            index=12,
            unit=enums.UNIT_NONE,
            desc="Limit the amount of data transferred with each call to sane_read().",
            title="Read limit",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="read-limit-size",
            index=13,
            unit=enums.UNIT_NONE,
            desc="The (maximum) amount of data transferred with each call to sane_read().",
            title="Read limit size",
            type=enums.TYPE_INT,
            constraint=(1, 65536, 1),
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="read-delay",
            index=14,
            unit=enums.UNIT_NONE,
            desc="Delay the transfer of data to the pipe.",
            title="Read delay",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="read-delay-duration",
            index=15,
            unit=enums.UNIT_MICROSECOND,
            desc="How long to wait after transferring each buffer of data through the pipe.",
            title="Read delay duration",
            type=enums.TYPE_INT,
            constraint=(1000, 200000, 1000),
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="read-return-value",
            index=16,
            unit=enums.UNIT_NONE,
            desc='Select the return-value of sane_read(). "Default" is the '
            "normal handling for scanning. All other status codes are for "
            "testing how the frontend handles them.",
            type=enums.TYPE_STRING,
            constraint=[
                "Default",
                "SANE_STATUS_UNSUPPORTED",
                "SANE_STATUS_CANCELLED",
                "SANE_STATUS_DEVICE_BUSY",
                "SANE_STATUS_INVAL",
                "SANE_STATUS_EOF",
                "SANE_STATUS_JAMMED",
                "SANE_STATUS_NO_DOCS",
                "SANE_STATUS_COVER_OPEN",
                "SANE_STATUS_IO_ERROR",
                "SANE_STATUS_NO_MEM",
                "SANE_STATUS_ACCESS_DENIED",
            ],
            title="Read return value",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="ppl-loss",
            index=17,
            unit=enums.UNIT_PIXEL,
            desc="The number of pixels that are wasted at the end of each line.",
            type=enums.TYPE_INT,
            constraint=(-128, 128, 1),
            title="Ppl loss",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="fuzzy-parameters",
            index=18,
            unit=enums.UNIT_NONE,
            desc="Return fuzzy lines and bytes per line when sane_parameters() "
            "is called before sane_start().",
            title="Fuzzy parameters",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="non-blocking",
            index=19,
            unit=enums.UNIT_NONE,
            desc="Use non-blocking IO for sane_read() if supported by the frontend.",
            title="Non blocking",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="select-fd",
            index=20,
            unit=enums.UNIT_NONE,
            desc="Offer a select filedescriptor for detecting if sane_read() will return data.",
            title="Select fd",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="enable-test-options",
            index=21,
            unit=enums.UNIT_NONE,
            desc="Enable various test options. This is for testing the ability "
            "of frontends to view and modify all the different SANE option types.",
            title="Enable test options",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="read-length-zero",
            index=22,
            unit=enums.UNIT_NONE,
            desc="sane_read() returns data 'x' but length=0 on first call. This "
            "is helpful for testing slow device behavior that returns no data "
            "when background work is in process and zero length with SANE_STATUS_GOOD "
            "although data is NOT filled with 0.",
            title="Read length zero",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=0,
            name="print-options",
            unit=enums.UNIT_NONE,
            index=23,
            desc="Print a list of all options.",
            title="Print options",
            type=enums.TYPE_BUTTON,
            constraint=None,
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=24,
            desc="",
            title="Geometry",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="tl-x",
            index=25,
            unit=enums.UNIT_MM,
            desc="Top-left x position of scan area.",
            type=enums.TYPE_INT,
            constraint=(0, 200, 1),
            title="Top-left x",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="tl-y",
            index=26,
            unit=enums.UNIT_MM,
            desc="Top-left y position of scan area.",
            type=enums.TYPE_INT,
            constraint=(0, 200, 1),
            title="Top-left y",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="br-x",
            index=27,
            unit=enums.UNIT_MM,
            desc="Bottom-right x position of scan area.",
            type=enums.TYPE_INT,
            constraint=(0, 200, 1),
            title="Bottom-right x",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="br-y",
            index=28,
            unit=enums.UNIT_MM,
            desc="Bottom-right y position of scan area.",
            type=enums.TYPE_INT,
            constraint=(0, 200, 1),
            title="Bottom-right y",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="page-width",
            index=29,
            unit=enums.UNIT_MM,
            desc="Specifies the width of the media.  Required for automatic "
            "centering of sheet-fed scans.",
            type=enums.TYPE_INT,
            constraint=(0, 300, 1),
            title="Page width",
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
            name="page-height",
            index=30,
            unit=enums.UNIT_MM,
            desc="Specifies the height of the media.",
            type=enums.TYPE_INT,
            constraint=(0, 300, 1),
            title="Page height",
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=31,
            desc="",
            title="Bool test options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="bool-soft-select-soft-detect",
            unit=enums.UNIT_NONE,
            index=32,
            desc="(1/6) Bool test option that has soft select and soft detect "
            "(and advanced) capabilities. That's just a normal bool option.",
            title="Bool soft select soft detect",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="bool-soft-select-soft-detect-emulated",
            unit=enums.UNIT_NONE,
            index=33,
            desc="(5/6) Bool test option that has soft select, soft detect, "
            "and emulated (and advanced) capabilities.",
            title="Bool soft select soft detect emulated",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT
            + enums.CAP_SOFT_SELECT
            + enums.CAP_INACTIVE
            + enums.CAP_AUTOMATIC,
            size=1,
            name="bool-soft-select-soft-detect-auto",
            unit=enums.UNIT_NONE,
            index=34,
            desc="(6/6) Bool test option that has soft select, soft detect, "
            "and automatic (and advanced) capabilities. This option can be "
            "automatically set by the backend.",
            title="Bool soft select soft detect auto",
            type=enums.TYPE_BOOL,
            constraint=None,
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=35,
            desc="",
            title="Int test options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="int",
            unit=enums.UNIT_NONE,
            index=36,
            desc="(1/6) Int test option with no unit and no constraint set.",
            title="Int",
            type=enums.TYPE_INT,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="int-constraint-range",
            index=37,
            unit=enums.UNIT_PIXEL,
            desc="(2/6) Int test option with unit pixel and constraint range "
            "set. Minimum is 4, maximum 192, and quant is 2.",
            title="Int constraint range",
            type=enums.TYPE_INT,
            constraint=(4, 192, 2),
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="int-constraint-word-list",
            index=38,
            unit=enums.UNIT_BIT,
            desc="(3/6) Int test option with unit bits and constraint word list set.",
            title="Int constraint word list",
            type=enums.TYPE_INT,
            constraint=[-42, -8, 0, 17, 42, 256, 65536, 16777216, 1073741824],
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
            name="int-constraint-array",
            unit=enums.UNIT_NONE,
            index=39,
            desc="(4/6) Int test option with unit mm and using an array without constraints.",
            title="Int constraint array",
            type=enums.TYPE_INT,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
            name="int-constraint-array-constraint-range",
            index=40,
            unit=enums.UNIT_DPI,
            desc="(5/6) Int test option with unit dpi and using an array with "
            "a range constraint. Minimum is 4, maximum 192, and quant is 2.",
            title="Int constraint array constraint range",
            type=enums.TYPE_INT,
            constraint=(4, 192, 2),
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=255,
            name="int-constraint-array-constraint-word-list",
            index=41,
            unit=enums.UNIT_PERCENT,
            desc="(6/6) Int test option with unit percent and using an array "
            "with a word list constraint.",
            title="Int constraint array constraint word list",
            type=enums.TYPE_INT,
            constraint=[-42, -8, 0, 17, 42, 256, 65536, 16777216, 1073741824],
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=42,
            desc="",
            title="Fixed test options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="fixed",
            unit=enums.UNIT_NONE,
            index=43,
            desc="(1/3) Fixed test option with no unit and no constraint set.",
            title="Fixed",
            type=enums.TYPE_FIXED,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="fixed-constraint-range",
            index=44,
            unit=enums.UNIT_MICROSECOND,
            desc="(2/3) Fixed test option with unit microsecond and constraint "
            "range set. Minimum is -42.17, maximum 32767.9999, and quant is 2.0.",
            title="Fixed constraint range",
            type=enums.TYPE_FIXED,
            constraint=(-42.17, 32768.0, 2.0),
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="fixed-constraint-word-list",
            index=45,
            unit=enums.UNIT_NONE,
            desc="(3/3) Fixed test option with no unit and constraint word list set.",
            title="Fixed constraint word list",
            type=enums.TYPE_FIXED,
            constraint=["-32.7", "12.1", "42", "129.5"],
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=46,
            desc="",
            title="String test options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="string",
            unit=enums.UNIT_NONE,
            index=47,
            desc="(1/3) String test option without constraint.",
            title="String",
            type=enums.TYPE_STRING,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="string-constraint-string-list",
            index=48,
            unit=enums.UNIT_NONE,
            desc="(2/3) String test option with string list constraint.",
            title="String constraint string list",
            type=enums.TYPE_STRING,
            constraint=[
                "First entry",
                "Second entry",
                "This is the very long third entry. Maybe the frontend has an "
                "idea how to display it",
            ],
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
            name="string-constraint-long-string-list",
            index=49,
            unit=enums.UNIT_NONE,
            desc="(3/3) String test option with string list constraint. "
            "Contains some more entries...",
            title="String constraint long string list",
            type=enums.TYPE_STRING,
            constraint=[
                "First entry",
                "Second entry",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "12",
                "13",
                "14",
                "15",
                "16",
                "17",
                "18",
                "19",
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "26",
                "27",
                "28",
                "29",
                "30",
                "31",
                "32",
                "33",
                "34",
                "35",
                "36",
                "37",
                "38",
                "39",
                "40",
                "41",
                "42",
                "43",
                "44",
                "45",
                "46",
            ],
        ),
        Option(
            cap=0,
            size=0,
            name="",
            unit=enums.UNIT_NONE,
            index=50,
            desc="",
            title="Button test options",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=0,
            name="button",
            unit=enums.UNIT_NONE,
            index=51,
            desc="(1/1) Button test option. Prints some text...",
            title="Button",
            type=enums.TYPE_BUTTON,
            constraint=None,
        ),
    ]
    assert options.array == that, "array"
    assert options.device == "test:0", "device name"

    assert not within_tolerance(
        options.array[1], "value", "value"
    ), "SANE_CONSTRAINT_NONE"
    assert within_tolerance(
        options.array[2], "Gray", "Gray"
    ), "SANE_CONSTRAINT_STRING_LIST positive"
    assert within_tolerance(
        options.array[3], 8, 8
    ), "SANE_CONSTRAINT_WORD_LIST positive"
    assert within_tolerance(options.array[7], 50, 50), "SANE_CONSTRAINT_RANGE exact"
    assert within_tolerance(options.array[7], 50, 50.1), "SANE_CONSTRAINT_RANGE inexact"
    assert not within_tolerance(
        options.array[2], "Gray", "gray"
    ), "SANE_CONSTRAINT_STRING_LIST negative"
    assert not within_tolerance(
        options.array[3], 8, 7
    ), "SANE_CONSTRAINT_WORD_LIST negative"
    assert not within_tolerance(
        options.array[7], 50, 51.1
    ), "SANE_CONSTRAINT_RANGE negative"
    assert not within_tolerance(options.array[4], False, 1), "SANE_TYPE_BOOL negative"
    assert within_tolerance(options.array[36], 20, 20), "SANE_TYPE_INT positive"
    assert not within_tolerance(options.array[36], 20, 21), "SANE_TYPE_INT negative"
    assert within_tolerance(options.array[43], 20.5, 20.5), "SANE_TYPE_FIXED positive"
    assert not within_tolerance(options.array[43], 20.0, 21), "SANE_TYPE_FIXED negative"
    assert within_tolerance(
        options.array[47], "20.5", "20.5"
    ), "SANE_TYPE_STRING positive"
    assert not within_tolerance(
        options.array[47], "20.5", "21"
    ), "SANE_TYPE_STRING negative"

    option = Option(
        cap=enums.CAP_SOFT_SELECT + enums.CAP_SOFT_DETECT,
        constraint=(297.179992675781, 0.0, 0.0),
        desc="Top Left Y",
        index=14,
        size=1,
        name="tl-y",
        title="Top Left Y",
        type=enums.TYPE_FIXED,
        unit=enums.UNIT_MM,
    )
    assert within_tolerance(
        option, 0.999984741210938, 1, 0.001
    ), "SANE_CONSTRAINT_RANGE inexact with tolerance"

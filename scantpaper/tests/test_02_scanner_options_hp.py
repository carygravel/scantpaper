"options from HP backends"

from pathlib import Path
import pytest
from scanner.options import Options, Option
from frontend import enums


@pytest.mark.skipif(
    not Path("scantpaper/tests/scanners/hp_6200").exists(),
    reason="source tree not found",
)
def test_6200():
    "options from hp_6200 backend"
    output = Path("scantpaper/tests/scanners/hp_6200").read_text(encoding="utf-8")
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


@pytest.mark.skipif(
    not Path("scantpaper/tests/scanners/hp_scanjet5300c").exists(),
    reason="source tree not found",
)
def test_scanjet5300c():
    "options from hp_scanjet5300c backend"
    output = Path("scantpaper/tests/scanners/hp_scanjet5300c").read_text(
        encoding="utf-8"
    )
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
            constraint=[
                "Lineart",
                "Dithered",
                "Gray",
                "12bit Gray",
                "Color",
                "12bit Color",
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
            constraint=(100, 1200, 5),
            unit=enums.UNIT_DPI,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="speed",
            title="Speed",
            index=4,
            desc="Determines the speed at which the scan proceeds.",
            constraint=(0, 4, 1),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="preview",
            title="Preview",
            index=5,
            desc="Request a preview-quality scan.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="source",
            title="Source",
            index=6,
            desc="Selects the scan source (such as a document-feeder).",
            constraint=["Normal", "ADF"],
            unit=enums.UNIT_NONE,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
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
            constraint=(0, 216, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="tl-y",
            title="Top-left y",
            index=9,
            desc="Top-left y position of scan area.",
            constraint=(0, 296, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="br-x",
            title="Bottom-right x",
            desc="Bottom-right x position of scan area.",
            index=10,
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
            index=11,
            constraint=(0, 296, 0),
            unit=enums.UNIT_MM,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            index=12,
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
            name="brightness",
            title="Brightness",
            index=13,
            desc="Controls the brightness of the acquired image.",
            constraint=(-100, 100, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="contrast",
            title="Contrast",
            index=14,
            desc="Controls the contrast of the acquired image.",
            constraint=(-100, 100, 1),
            unit=enums.UNIT_PERCENT,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="quality-scan",
            title="Quality scan",
            index=15,
            desc="Turn on quality scanning (slower but better).",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
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
            name="gamma-table",
            title="Gamma table",
            index=17,
            desc="Gamma-correction table.  In color mode this option equally "
            "affects the red, green, and blue channels simultaneously (i.e., it "
            "is an intensity gamma table).",
            constraint=(0, 255, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=255,
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
            name="frame",
            title="Frame",
            index=21,
            desc="Selects the number of the frame to scan",
            constraint=(0, 0, 0),
            unit=enums.UNIT_NONE,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
            size=1,
        ),
        Option(
            name="power-save-time",
            title="Power save time",
            index=22,
            desc="Allows control of the scanner's power save timer, dimming "
            "or turning off the light.",
            unit=enums.UNIT_NONE,
            constraint=None,
            type=enums.TYPE_INT,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
        Option(
            name="nvram-values",
            title="Nvram values",
            index=23,
            desc="Allows access obtaining the scanner's NVRAM values as pretty printed text.",
            unit=enums.UNIT_NONE,
            constraint=None,
            type=enums.TYPE_STRING,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT,
            size=1,
        ),
    ]
    assert options.array == that, "hp_scanjet5300c"
    assert options.device == "avision:libusb:001:005", "device name"


@pytest.mark.skipif(
    not Path("scantpaper/tests/scanners/officejet_5500").exists(),
    reason="source tree not found",
)
def test_officejet_5500():
    "options from officejet_5500 backend"
    output = Path("scantpaper/tests/scanners/officejet_5500").read_text(
        encoding="utf-8"
    )
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
            "after the last scanned page, to prevent endless flatbed scans after "
            "a batch scan. For some models, option changes in the middle of a "
            "batch scan don't take effect until after the last page.",
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
            "duplex mode, one side will be scanned upside-down.  This feature is experimental.",
            unit=enums.UNIT_NONE,
            type=enums.TYPE_BOOL,
            constraint=None,
            cap=enums.CAP_SOFT_DETECT + enums.CAP_SOFT_SELECT + enums.CAP_INACTIVE,
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
            constraint=(0.0, 215.9, 0),
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
            constraint=(0.0, 215.9, 0),
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
    assert options.array == that, "officejet_5500"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 1
    ), "supports_paper"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": -10,
            },
            0,
        )
        == 0
    ), "paper crosses top border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 90,
            },
            0,
        )
        == 0
    ), "paper crosses bottom border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": -10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses left border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses right border"
    assert (
        options.supports_paper(
            {
                "x": 225,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper too wide"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 870,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper too tall"
    assert (
        options.device == "hpaio:/usb/officejet_5500_series?serial=MY42QF209H96"
    ), "device name"

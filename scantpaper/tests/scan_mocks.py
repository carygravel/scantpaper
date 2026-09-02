"""Shared scan-option definitions for scan-dialog tests"""

from frontend import enums
from scanner.options import Option


def _number_of_options():
    """The read-only option that heads every raw_options list"""
    return Option(
        index=0,
        name="",
        title="Number of options",
        desc="Read-only option that specifies how many options a specific device supports.",
        type=1,
        unit=0,
        size=4,
        cap=4,
        constraint=None,
    )


def _geo(name, constraint, title, desc):
    """Build a 2D-geometry option (tl-x/tl-y/br-x/br-y)"""
    return Option(
        index=0,
        name=name,
        title=title,
        desc=desc,
        type=2,
        unit=3,
        size=1,
        cap=5,
        constraint=constraint,
    )


def _res(
    constraint,
    title="Scan resolution",
    desc="Sets the resolution of the scanned image.",
    size=1,
):
    """Build a resolution option"""
    return Option(
        index=0,
        name="resolution",
        title=title,
        desc=desc,
        type=1,
        unit=4,
        size=size,
        cap=5,
        constraint=constraint,
    )


def _src(
    constraint,
    title="Scan source",
    desc="Selects the scan source (such as a document-feeder).",
):
    """Build a source option"""
    return Option(
        index=0,
        name="source",
        title=title,
        desc=desc,
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=constraint,
    )


# Unique scan option definitions, keyed by descriptive names. Each test builds
# its raw_options by listing the keys it needs; build_scan_options assigns the
# sequential indices.
OPTIONS = {
    # ---- resolution ----
    "resolution-100-200-300-600": _res([100, 200, 300, 600]),
    "resolution-100-200-300-600-size4": _res([100, 200, 300, 600], size=4),
    "resolution-600": _res([600]),
    "resolution-150-200-300-400-600": _res(
        [150, 200, 300, 400, 600],
        desc="Scan resolution",
    ),
    "resolution-50-1200": _res((50, 1200, 0), title="Resolution", desc="Resolution"),
    # ---- source ----
    "source-flatbed-adf": _src(["Flatbed", "ADF"]),
    "source-flatbed-adf-duplex": _src(["Flatbed", "ADF", "Duplex"]),
    "source-flatbed-automatic-document-feeder": _src(
        ["Flatbed", "Automatic Document Feeder"]
    ),
    "source-adf-document-table": _src(
        ["ADF", "Document Table"], title="Document Source", desc="Document Source"
    ),
    # ---- geometry ----
    "tl-x-215899": _geo(
        "tl-x",
        (0, 215.899993896484, 0),
        "Top-left x",
        "Top-left x position of scan area.",
    ),
    "tl-x-215900": _geo(
        "tl-x",
        (0, 215.900009155273, 0),
        "Top-left x",
        "Top-left x position of scan area.",
    ),
    "tl-x-top-left-x": _geo(
        "tl-x", (0, 215.899993896484, 0), "Top Left X", "Top Left X"
    ),
    "tl-y-297179": _geo(
        "tl-y",
        (0, 297.179992675781, 0),
        "Top-left y",
        "Top-left y position of scan area.",
    ),
    "tl-y-297010": _geo(
        "tl-y",
        (0, 297.010681152344, 0),
        "Top-left y",
        "Top-left y position of scan area.",
    ),
    "tl-y-top-left-y": _geo(
        "tl-y", (0, 297.179992675781, 0), "Top Left Y", "Top Left Y"
    ),
    "br-x-215899": _geo(
        "br-x",
        (0, 215.899993896484, 0),
        "Bottom-right x",
        "Bottom-right x position of scan area.",
    ),
    "br-x-215900": _geo(
        "br-x",
        (0, 215.900009155273, 0),
        "Bottom-right x",
        "Bottom-right x position of scan area.",
    ),
    "br-x-bottom-right-x": _geo(
        "br-x", (0, 215.899993896484, 0), "Bottom Right X", "Bottom Right X"
    ),
    "br-x-356": _geo("br-x", (0, 356.0, 0), "Bottom Right X", "Bottom Right X"),
    "br-y-297179": _geo(
        "br-y",
        (0, 297.179992675781, 0),
        "Bottom-right y",
        "Bottom-right y position of scan area.",
    ),
    "br-y-297010": _geo(
        "br-y",
        (0, 297.010681152344, 0),
        "Bottom-right y",
        "Bottom-right y position of scan area.",
    ),
    "br-y-bottom-right-y": _geo(
        "br-y", (0, 297.179992675781, 0), "Bottom Right Y", "Bottom Right Y"
    ),
    "br-y-356": _geo("br-y", (0, 356.0, 0), "Bottom Right Y", "Bottom Right Y"),
    # ---- extras ----
    "swcrop": Option(
        index=0,
        name="swcrop",
        title="Software crop",
        desc="Request driver to remove border from pages digitally.",
        type=0,
        unit=0,
        size=1,
        cap=69,
        constraint=None,
    ),
    "clear-calibration": Option(
        index=0,
        name="clear-calibration",
        title="Clear calibration",
        desc="Clear calibration cache",
        type=4,
        unit=0,
        size=1,
        cap=5,
        constraint=None,
    ),
    "select-detect": Option(
        index=0,
        name=None,
        title=None,
        desc=None,
        constraint=None,
        size=1,
        type=enums.TYPE_BOOL,
        unit=None,
        cap=enums.CAP_SOFT_SELECT + enums.CAP_SOFT_DETECT,
    ),
    "cct-1": Option(
        index=0,
        name="cct-1",
        title="",
        desc="",
        type=2,
        unit=0,
        size=1,
        cap=69,
        constraint=None,
    ),
    # ---- enhancement / processing ----
    "enable-resampling": Option(
        index=0,
        name="enable-resampling",
        title="Enable Resampling",
        desc="This option provides the user with a wider range of supported"
        " resolutions.  Resolutions not supported by the hardware will"
        " be achieved through image processing methods.",
        type=0,
        unit=0,
        size=1,
        cap=100,
        constraint=None,
    ),
    "resolution-bind": Option(
        index=0,
        name="resolution-bind",
        title="Bind X and Y resolutions",
        desc="Bind X and Y resolutions",
        type=0,
        unit=0,
        size=1,
        cap=69,
        constraint=None,
    ),
    "x-resolution-50-1200": Option(
        index=0,
        name="x-resolution",
        title="X Resolution",
        desc="X Resolution",
        type=1,
        unit=4,
        size=1,
        cap=68,
        constraint=(50, 1200, 0),
    ),
    "y-resolution-50-1200": Option(
        index=0,
        name="y-resolution",
        title="Y Resolution",
        desc="Y Resolution",
        type=1,
        unit=4,
        size=1,
        cap=68,
        constraint=(50, 1200, 0),
    ),
    "scan-area-executive-iso": Option(
        index=0,
        name="scan-area",
        title="Scan Area",
        desc="Scan Area",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=[
            "Executive/Portrait",
            "ISO/A4/Portrait",
            "ISO/A5/Portrait",
            "ISO/A5/Landscape",
            "ISO/A6/Portrait",
            "ISO/A6/Landscape",
            "JIS/B5/Portrait",
            "JIS/B6/Portrait",
            "JIS/B6/Landscape",
            "Letter/Portrait",
            "Manual",
            "Maximum",
        ],
    ),
    "mode-image-type": Option(
        index=0,
        name="mode",
        title="Image Type",
        desc="Image Type",
        type=3,
        unit=0,
        size=1,
        cap=13,
        constraint=["Monochrome", "Grayscale", "Color"],
    ),
    "device-03-geometry": Option(
        index=0,
        name="device-03-geometry",
        title="Geometry",
        desc="Scan area and image size related options.",
        type=5,
        unit=0,
        size=0,
        cap=32,
        constraint=None,
    ),
    "device-04-enhancement": Option(
        index=0,
        name="device-04-enhancement",
        title="Enhancement",
        desc="Image modification options.",
        type=5,
        unit=0,
        size=0,
        cap=32,
        constraint=None,
    ),
    "rotate": Option(
        index=0,
        name="rotate",
        title="Rotate",
        desc="Rotate",
        type=3,
        unit=0,
        size=1,
        cap=13,
        constraint=["0 degrees", "90 degrees", "180 degrees", "270 degrees", "Auto"],
    ),
    "blank-threshold": Option(
        index=0,
        name="blank-threshold",
        title="Skip Blank Pages Settings",
        desc="Skip Blank Pages Settings",
        type=2,
        unit=0,
        size=1,
        cap=13,
        constraint=(0, 100, 0),
    ),
    "brightness-0-100": Option(
        index=0,
        name="brightness",
        title="Brightness",
        desc="Change brightness of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 0),
    ),
    "contrast-0-100": Option(
        index=0,
        name="contrast",
        title="Contrast",
        desc="Change contrast of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 0),
    ),
    "threshold": Option(
        index=0,
        name="threshold",
        title="Threshold",
        desc="Threshold",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(0, 255, 0),
    ),
    "device--": Option(
        index=0,
        name="device--",
        title="Other",
        desc="",
        type=5,
        unit=0,
        size=0,
        cap=32,
        constraint=None,
    ),
    "gamma": Option(
        index=0,
        name="gamma",
        title="Gamma",
        desc="Gamma",
        type=3,
        unit=0,
        size=1,
        cap=69,
        constraint=["1.0", "1.8"],
    ),
    "image-count": Option(
        index=0,
        name="image-count",
        title="Image Count",
        desc="Image Count",
        type=1,
        unit=0,
        size=1,
        cap=101,
        constraint=(0, 999, 0),
    ),
    "jpeg-quality": Option(
        index=0,
        name="jpeg-quality",
        title="JPEG Quality",
        desc="JPEG Quality",
        type=1,
        unit=0,
        size=1,
        cap=69,
        constraint=(1, 100, 0),
    ),
    "transfer-format": Option(
        index=0,
        name="transfer-format",
        title="Transfer Format",
        desc="Selecting a compressed format such as JPEG normally results "
        "in faster device side processing.",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=["JPEG", "RAW"],
    ),
    "transfer-size": Option(
        index=0,
        name="transfer-size",
        title="Transfer Size",
        desc="Transfer Size",
        type=1,
        unit=0,
        size=1,
        cap=69,
        constraint=(1, 268435455, 0),
    ),
    # ---- 06182 variants ----
    "tl-y-296925": _geo("tl-y", (0, 296.925994873047, 0), "Top Left Y", "Top Left Y"),
    "br-y-296925": _geo(
        "br-y", (0, 296.925994873047, 0), "Bottom Right Y", "Bottom Right Y"
    ),
    "tl-x-216-user": _geo(
        "tl-x",
        (0, 216, 0),
        "tl-x",
        'Top-left x position of scan area. You should use it in "User defined" mode only!',
    ),
    "br-x-216-user": _geo(
        "br-x",
        (0, 216, 0),
        "br-x",
        'Bottom-right x position of scan area. You should use it in "User defined" mode only!',
    ),
    "tl-y-355-user": _geo(
        "tl-y",
        (0, 355.599990844727, 0),
        "tl-y",
        'Top-left y position of scan area. You should use it in "User defined" mode only!',
    ),
    "br-y-355-user": _geo(
        "br-y",
        (0, 355.599990844727, 0),
        "br-y",
        'Bottom-right y position of scan area. You should use it in "User defined" mode only!',
    ),
    "tl-y-299212": _geo(
        "tl-y",
        (0, 299.212005615234, 0),
        "Top-left y",
        "Top-left y position of scan area.",
    ),
    "br-y-299212": _geo(
        "br-y",
        (0, 299.212005615234, 0),
        "Bottom-right y",
        "Bottom-right y position of scan area.",
    ),
    "resolution-75-100-200-300": _res([75, 100, 200, 300]),
    "mode-scan": Option(
        index=0,
        name="mode",
        title="Scan mode",
        desc="Scan mode",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=["Gray", "Color", "Black & White", "Error Diffusion", "ATEII"],
    ),
    "ScanMode": Option(
        index=0,
        name="ScanMode",
        title="ScanMode",
        desc="scanmode,choose simplex or duplex scan",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=["Simplex", "Duplex"],
    ),
    # ---- sane_scan_mocks variants ----
    "brightness-100-100-1": Option(
        index=0,
        name="brightness",
        title="Brightness",
        desc="Controls the brightness of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 1),
    ),
    "contrast-100-100-1": Option(
        index=0,
        name="contrast",
        title="Contrast",
        desc="Controls the contrast of the acquired image.",
        type=1,
        unit=0,
        size=1,
        cap=13,
        constraint=(-100, 100, 1),
    ),
    "x-resolution-150-225-300-600-900-1200": Option(
        index=0,
        name="x-resolution",
        title="X-resolution",
        desc="Sets the horizontal resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=69,
        constraint=[150, 225, 300, 600, 900, 1200],
    ),
    "y-resolution-150-225-300-600-900-1200-1800-2400": Option(
        index=0,
        name="y-resolution",
        title="Y-resolution",
        desc="Sets the vertical resolution of the scanned image.",
        type=1,
        unit=4,
        size=1,
        cap=69,
        constraint=[150, 225, 300, 600, 900, 1200, 1800, 2400],
    ),
    "geometry": Option(
        index=0,
        name="",
        title="Geometry",
        desc="",
        type=5,
        unit=0,
        size=1,
        cap=64,
        constraint=None,
    ),
    "scan-area-maximum-a4": Option(
        index=0,
        name="scan-area",
        title="Scan area",
        desc="Select an area to scan based on well-known media sizes.",
        type=3,
        unit=0,
        size=1,
        cap=5,
        constraint=[
            "Maximum",
            "A4",
            "A5 Landscape",
            "A5 Portrait",
            "B5",
            "Letter",
            "Executive",
            "CD",
        ],
    ),
}


def build_scan_options(keys):
    """Build a raw_options list from named option keys, auto-assigning indices"""
    opts = [_number_of_options()]
    for i, key in enumerate(keys, start=1):
        opts.append(OPTIONS[key]._replace(index=i))
    return opts

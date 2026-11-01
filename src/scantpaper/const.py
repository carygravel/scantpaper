"""Constants that are used in multiple places."""

from __future__ import annotations

import datetime
import importlib.metadata
import sys
from pathlib import Path
from typing import cast

if sys.version_info >= (3, 11):  # jammy (22.04) still has 3.10
    import tomllib
else:
    import tomli as tomllib

PROG_NAME = "scantpaper"
AUTHOR = "Jeffrey Ratcliffe"
AUTHOR_EMAIL = "jffry@posteo.net"
URL = "https://github.com/carygravel/scantpaper"
BUG_URL = URL + "/issues"
LOCAL_DOCS_URI = f"/usr/share/doc/C/{PROG_NAME}/documentation.html"


def get_version() -> str:
    """Get version from pyproject.toml."""
    tomlfile_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if tomlfile_path.is_file():
        return cast(
            "str", (tomllib.loads(tomlfile_path.read_text())["project"]["version"])
        )
    return importlib.metadata.version(PROG_NAME)


VERSION = get_version()

ASTERISK = "*"
DOT = "."
EMPTY = ""
EMPTY_LIST = -1
NOT_FOUND = -1
HALF = 0.5
# The percent sign is a symbol, not a linguistic element: ISO 31-0/SI defines
# it universally and it is not localised in any locale. It is deliberately not
# wrapped in _(), so it never becomes a msgid that translators must confirm as
# unchanged. The sibling unit labels (mm, ppi, dpi, pel, bit, us, pixels) *are*
# wrapped in _(), because those locales do localise them.
PERCENT = "%"
SPACE = " "
# The focused slice is rendered at this logical em height when the focus level
# is 100%. The level scales it, and FOCUS_MARGIN keeps a border around the
# slice when the fit bound applies.
FOCUS_TEXT_HEIGHT = 64
FOCUS_MARGIN = 0.1
DEFAULT_FOCUS_ZOOM = 1.0
MIN_FOCUS_ZOOM = 0.5
MAX_FOCUS_ZOOM = 2.0
FOCUS_ZOOM_STEP = 0.05
ANNOTATION_COLOR = "cccf00"
# GTK4 removed the Gtk.STYLE_CLASS_* constants; the CSS class names are the
# same strings in the default theme.
STYLE_CLASS_BACKGROUND = "background"
STYLE_CLASS_RUBBERBAND = "rubberband"

BITS_PER_BYTE = 8
CM_PER_INCH = 2.54
MM_PER_CM = 10
MM_PER_INCH = CM_PER_INCH * MM_PER_CM
POINTS_PER_INCH = 72
MAX_DPI = 2400
MIN_BASELINE_COEFFICIENTS = 2

# A grayscale image carrying at most this many distinct intensity levels is
# treated as posterised rather than photographic: page._is_low_colour_depth
# stores and writes it losslessly, because JPEG both loses the levels and
# tends to produce a larger stream for it.
LOW_COLOUR_DEPTH_LEVELS = 16

# Maximum difference, in pixels, between an hOCR page box and the target page
# dimensions. One pixel covers rounding differences between PDF extraction and
# hOCR export without hiding a real crop, rotation, or resample.
HOCR_PAGE_BOX_TOLERANCE = 1

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

# Number of fractional digits shown in ranged scan-option (spin button) size
# fields. Values are rounded to this precision for display, and arrow steps
# stay whole units. This constant is the single knob controlling the precision.
FRACTIONAL_DIGITS = 2

DRAGGER_TOOL = "dragger"
SELECTOR_TOOL = "selector"
SELECTORDRAGGER_TOOL = "selectordragger"

_90_DEGREES = 90
_180_DEGREES = 180
_270_DEGREES = 270
_100_PERCENT = 100

_LOCAL_TZ = datetime.datetime.now().astimezone().tzinfo

HELP_WINDOW_WIDTH = 800
HELP_WINDOW_HEIGHT = 600
HELP_WINDOW_DIVIDER_POS = 200

THUMBNAIL = 100  # pixels
VIEWER_MIN_SIZE = 100  # minimum on-screen size of the image view and canvases

# Dialog content padding, in pixels. GTK3 derived the content-area inset from
# the active theme; GTK4 has no equivalent, and Gtk.Box spacing defaults to 0,
# so both are fixed here. DIALOG_CONTENT_MARGIN insets the content area from
# the window edge; DIALOG_ROW_SPACING separates the blocks appended to the
# content area and the widgets within each row.
DIALOG_CONTENT_MARGIN = 12
DIALOG_ROW_SPACING = 6

# GTK3's GtkDialog took the gap between action buttons from the theme; GTK4's
# action area is a plain GtkBox with spacing 0, so restore a consistent gap
# between adjacent action buttons.
DIALOG_BUTTON_SPACING = 6

APPLICATION_ID = 223562788
USER_VERSION = 3

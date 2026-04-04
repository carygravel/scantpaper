"Constants that are used in multiple places"

import importlib.metadata
from pathlib import Path
import tomllib

PROG_NAME = "scantpaper"
AUTHOR = "Jeffrey Ratcliffe"
AUTHOR_EMAIL = "jffry@posteo.net"
URL = "https://github.com/carygravel/scantpaper"
BUG_URL = URL + "/issues"


def get_version():
    "Get version from pyproject.toml"
    tomlfile_path = Path(__file__).parent.parent / "pyproject.toml"
    if tomlfile_path.is_file():
        return tomllib.loads(tomlfile_path.read_text())["project"]["version"]
    return importlib.metadata.version(PROG_NAME)


VERSION = get_version()

ASTERISK = "*"
DOT = "."
EMPTY = ""
EMPTY_LIST = -1
HALF = 0.5
PERCENT = "%"
SPACE = " "
ZOOM_CONTEXT_FACTOR = 0.5
ANNOTATION_COLOR = "cccf00"

BITS_PER_BYTE = 8
CM_PER_INCH = 2.54
MM_PER_CM = 10
MM_PER_INCH = CM_PER_INCH * MM_PER_CM
POINTS_PER_INCH = 72
MAX_DPI = 2400

DRAGGER_TOOL = "dragger"
SELECTOR_TOOL = "selector"
SELECTORDRAGGER_TOOL = "selectordragger"

_90_DEGREES = 90
_180_DEGREES = 180
_270_DEGREES = 270
_100_PERCENT = 100

HELP_WINDOW_WIDTH = 800
HELP_WINDOW_HEIGHT = 600
HELP_WINDOW_DIVIDER_POS = 200

THUMBNAIL = 100  # pixels
APPLICATION_ID = 2235627884
USER_VERSION = 2

""" inject enums from sane dynamically to avoid linter warnings in each module
    from which they are imported"""
import sane

# Seed enums to avoid no-member warnings from pylint
CAP_ADVANCED = None
CAP_AUTOMATIC = None
CAP_EMULATED = None
CAP_HARD_SELECT = None
CAP_INACTIVE = None
CAP_SOFT_DETECT = None
CAP_SOFT_SELECT = None
CONSTRAINT_NONE = None
CONSTRAINT_RANGE = None
CONSTRAINT_STRING_LIST = None
CONSTRAINT_WORD_LIST = None
FRAME_BLUE = None
FRAME_GRAY = None
FRAME_GREEN = None
FRAME_RED = None
FRAME_RGB = None
INFO_INEXACT = None
INFO_RELOAD_OPTIONS = None
INFO_RELOAD_PARAMS = None
RELOAD_PARAMS = None
SANE_WORD_SIZE = None
TYPE_BOOL = None
TYPE_BUTTON = None
TYPE_FIXED = None
TYPE_GROUP = None
TYPE_INT = None
TYPE_STRING = None
UNIT_BIT = None
UNIT_DPI = None
UNIT_MICROSECOND = None
UNIT_MM = None
UNIT_NONE = None
UNIT_PERCENT = None
UNIT_PIXEL = None


def OPTION_IS_ACTIVE(_opt):  # pylint: disable=invalid-name
    "overwritten by sane._sane.OPTION_IS_ACTIVE"
    return True


def OPTION_IS_SETTABLE(_opt):  # pylint: disable=invalid-name
    "overwritten by sane._sane.OPTION_IS_SETTABLE"
    return True


for symbol in [
    "CAP_ADVANCED",
    "CAP_AUTOMATIC",
    "CAP_EMULATED",
    "CAP_HARD_SELECT",
    "CAP_INACTIVE",
    "CAP_SOFT_DETECT",
    "CAP_SOFT_SELECT",
    "CONSTRAINT_NONE",
    "CONSTRAINT_RANGE",
    "CONSTRAINT_STRING_LIST",
    "CONSTRAINT_WORD_LIST",
    "FRAME_BLUE",
    "FRAME_GRAY",
    "FRAME_GREEN",
    "FRAME_RED",
    "FRAME_RGB",
    "INFO_INEXACT",
    "INFO_RELOAD_OPTIONS",
    "INFO_RELOAD_PARAMS",
    "OPTION_IS_ACTIVE",
    "OPTION_IS_SETTABLE",
    "RELOAD_PARAMS",
    "SANE_WORD_SIZE",
    "TYPE_BOOL",
    "TYPE_BUTTON",
    "TYPE_FIXED",
    "TYPE_GROUP",
    "TYPE_INT",
    "TYPE_STRING",
    "UNIT_BIT",
    "UNIT_DPI",
    "UNIT_MICROSECOND",
    "UNIT_MM",
    "UNIT_NONE",
    "UNIT_PERCENT",
    "UNIT_PIXEL",
]:
    locals()[symbol] = getattr(sane._sane, symbol)  # pylint: disable=protected-access

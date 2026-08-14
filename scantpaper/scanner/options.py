"object and helper methods to manipulate scan options"

import re
from collections import namedtuple

from frontend import enums
from gi.repository import GObject

EMPTY = ""
Option = namedtuple(
    "Option",
    ["index", "name", "title", "desc", "type", "unit", "size", "cap", "constraint"],
)


class Options(GObject.Object):
    """object to manipulate scan options.
    Have to subclass Glib::Object to be able to name it as an object in
    Glib.ParamSpec object in Scantpaper.Dialog.Scan"""

    def __init__(self, options):
        GObject.Object.__init__(self)
        self.hash = {}
        self.geometry = {}
        if options is None:
            raise ValueError("Error: no options supplied")
        if isinstance(options, list):
            for i, option in enumerate(options):
                opt = Option(*option)
                if opt.name is None:
                    opt = opt._replace(cap=0)
                options[i] = opt
            self.array = options
        else:
            raise TypeError("Error: options must be a list")

        # add hash for easy retrieval
        for option in self.array:
            if option.name != EMPTY:
                self.hash[option.name] = option

        # find source option
        self.source = None
        if self.by_name("source") is not None:
            self.source = self.by_name("source")
        else:
            for option in self.array:
                if option.name is not None and re.search(
                    r"source", option.name, re.MULTILINE | re.DOTALL | re.VERBOSE
                ):
                    self.source = option
                    break

        self.parse_geometry()

    def __str__(self):
        return f"Options({self.array})"

    def by_index(self, i):
        "return option by index"
        return self.array[i]

    def by_name(self, name):
        "return option by name"
        return self.hash[name] if name is not None and name in self.hash else None

    def num_options(self):
        "return number of options"
        return len(self.array) - 1 + 1

    def parse_geometry(self):
        """Parse out the geometry from libimage-sane-perl or scanimage option names"""
        for key in ("page-height", "pageheight"):
            if key in self.hash:
                self.geometry["h"] = self.hash[key].constraint[1]
                break

        for key in ("page-width", "pagewidth"):
            if key in self.hash:
                self.geometry["w"] = self.hash[key].constraint[1]
                break

        if "tl-x" in self.hash and "br-x" in self.hash:
            self.geometry["l"] = self.hash["tl-x"].constraint[0]
            self.geometry["x"] = self.hash["br-x"].constraint[1] - self.geometry["l"]

        if "tl-y" in self.hash and "br-y" in self.hash:
            self.geometry["t"] = self.hash["tl-y"].constraint[0]
            self.geometry["y"] = self.hash["br-y"].constraint[1] - self.geometry["t"]

    def supports_paper(self, paper, tolerance):
        "Check the geometry against the paper size"
        if not (
            "l" in self.geometry
            and "x" in self.geometry
            and "t" in self.geometry
            and "y" in self.geometry
            and self.geometry["l"] <= paper["l"] + tolerance
            and self.geometry["t"] <= paper["t"] + tolerance
        ):
            return False

        if "h" in self.geometry and "w" in self.geometry:
            return bool(
                self.geometry["h"] + tolerance >= paper["y"] + paper["t"]
                and self.geometry["w"] + tolerance >= paper["x"] + paper["l"]
            )
        return bool(
            self.geometry["x"] + self.geometry["l"] + tolerance
            >= paper["x"] + paper["l"]
            and self.geometry["y"] + self.geometry["t"] + tolerance
            >= paper["y"] + paper["t"]
        )

    def can_duplex(self):
        """returns TRUE if the current options support duplex, even if not currently
        selected. Alternatively expressed, return FALSE if the scanner is not capable
        of duplex scanner, or if the capability is inactive."""
        for option in self.array:
            if not enums.CAP_INACTIVE & option.cap:
                if option.name is not None and re.search(
                    r"duplex",
                    option.name,
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    return True

                if (
                    isinstance(option.constraint, list)
                    and option.type == enums.TYPE_STRING
                ):
                    for item in option.constraint:
                        if re.search(
                            r"duplex",
                            item,
                            re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                        ):
                            return True

        return False

    def flatbed_selected(self, get_value):
        "returns whether the flatbed is selected"
        source = None
        if self.source is not None:
            try:
                source = get_value(self.source.name)
            except AttributeError:
                pass
        return bool(
            source is None
            or re.search(
                r"(flatbed|Document[ ]Table)",
                source,
                re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            or (
                self.source is not None
                and isinstance(self.source.constraint, list)
                and len(self.source.constraint) == 1
                and re.search(
                    r"flatbed",
                    self.source.constraint[0],
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
            )
        )


def within_tolerance(option, current_value, new_value, tolerance=0):
    "helper function, returning whether new_value is within the tolerance of current_value"
    if isinstance(option.constraint, tuple):
        return bool(
            abs(new_value - current_value) <= option.constraint[2] / 2 + tolerance
        )

    if isinstance(option.constraint, list) or option.type in [
        enums.TYPE_BOOL,
        enums.TYPE_STRING,
    ]:
        return new_value == current_value

    if option.type in [enums.TYPE_INT, enums.TYPE_FIXED]:
        return abs(new_value - current_value) <= tolerance

    return False

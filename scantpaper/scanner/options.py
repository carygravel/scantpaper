"object and helper methods to manipulate scan options"
import re
from collections import defaultdict, namedtuple
from types import SimpleNamespace
from gi.repository import GObject
import sane

EMPTY = ""
EMPTY_ARRAY = -1
MAX_VALUES = 255
UNITS = r"(pel|bit|mm|dpi|%|us)"
UNIT2ENUM = defaultdict(
    dict,
    {
        "pel": sane._sane.UNIT_PIXEL,
        "bit": sane._sane.UNIT_BIT,
        "mm": sane._sane.UNIT_MM,
        "dpi": sane._sane.UNIT_DPI,
        "%": sane._sane.UNIT_PERCENT,
        "us": sane._sane.UNIT_MICROSECOND,
    },
)
Option = namedtuple(
    "Option",
    ["index", "name", "title", "desc", "type", "unit", "size", "cap", "constraint"],
)


class Options(GObject.Object):
    """object to manipulate scan options.
    Have to subclass Glib::Object to be able to name it as an object in
    Glib::ParamSpec->object in Gscan2pdf::Dialog::Scan"""

    def __init__(self, options):
        GObject.Object.__init__(self)
        self.hash = {}
        self.device = None
        self.geometry = {}
        if options is None:
            raise ValueError("Error: no options supplied")
        if isinstance(options, list):
            for i, option in enumerate(options):
                options[i] = Option(*option)
            self.array = options
        else:
            self.array = self._parse_scanimage_output(options)

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
                if re.search(
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

    def by_title(self, title):
        "return option by title"
        for option in self.array:
            if option.title == title:
                return option
        return None

    def num_options(self):
        "return number of options"
        return len(self.array) - 1 + 1

    def delete_by_index(self, i):
        "delete option by index"
        if self.array[i].name != "":
            del self.hash[self.array[i].name]
        self.array[i] = None

    def delete_by_name(self, name):
        "delete option by name"
        self.array[self.hash[name].index] = None
        del self.hash[name]

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

        if "tl-x" in self.hash:
            self.geometry["l"] = self.hash["tl-x"].constraint[0]
            if "br-x" in self.hash:
                self.geometry["x"] = (
                    self.hash["br-x"].constraint[1] - self.geometry["l"]
                )
        elif "l" in self.hash:
            self.geometry["l"] = self.hash["l"].constraint[0]
            if "max" in self.hash["x"].constraint:
                self.geometry["x"] = self.hash["x"].constraint[1]

        if "tl-y" in self.hash:
            self.geometry["t"] = self.hash["tl-y"].constraint[0]
            if "br-y" in self.hash:
                self.geometry["y"] = (
                    self.hash["br-y"].constraint[1] - self.geometry["t"]
                )
        elif "t" in self.hash:
            self.geometry["t"] = self.hash["t"].constraint[0]
            if "max" in self.hash["y"].constraint:
                self.geometry["y"] = self.hash["y"].constraint[1]

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
            if not sane._sane.CAP_INACTIVE & option.cap:
                if re.search(
                    r"duplex",
                    option.name,
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    return True

                if (
                    isinstance(option.constraint, list)
                    and option.type == sane._sane.TYPE_STRING
                ):
                    for item in option.constraint:
                        if re.search(
                            r"duplex",
                            item,
                            re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                        ):
                            return True

        return False

    def flatbed_selected(self, device_handle):
        "returns whether the flatbed is selected"
        val = None
        if self.source is not None:
            name = self.source.name.replace("-", "_")
            if hasattr(device_handle, name):
                val = getattr(device_handle, name)
        return (
            val is not None
            and re.search(
                r"(flatbed|Document[ ]Table)",
                val,
                re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            or (
                isinstance(self.source, list)
                and len(self.source.constraint) == 1
                and re.search(
                    r"flatbed",
                    self.source.constraint[0],
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
            )
        )

    def _parse_scanimage_output(self, output):
        "parse the scanimage/scanadf output into an array and a hash"

        # Remove everything above the options
        regex = re.search(
            r"""
                       Options[ ]specific[ ]to[ ]device[ ] # string
                       `(.+)':\n # device name
                       (.*) # options
                """,
            output,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        if regex:
            self.device = regex.group(1)
            output = regex.group(2)
        else:
            return None

        options = []
        while True:
            option = SimpleNamespace()
            option.unit = sane._sane.UNIT_NONE
            option.constraint_type = "CONSTRAINT_NONE"
            option.constraint = None
            option.val = None
            values = r"(?:(?:[ ]|[[]=[(])([^[].*?)(?:[)]\])?)?"

            # parse group
            regex = re.search(
                r"""
                      \A[ ]{2} # two-character indent
                      ([^\n]*) # the title
                      :\n  # a colon at the end of the line
                      (.*) # the rest of the output
                    """,
                output,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            regex2 = re.search(
                rf"""
                      \A[ ]{{4,}} # four-character indent
                      -+        # at least one dash
                      ([\w\-]+) # the option name
                      {values}      # optionally followed by the possible values
                        # optionally a space,
                        # followed by the current value in square brackets
                      (?:[ ][[](.*?)[]])?
                      [ ]*\n     # the rest of the line
                      (.*) # the rest of the output
                    """,
                output,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                option.title = regex.group(1)
                option.type = sane._sane.TYPE_GROUP
                option.cap = 0
                option.max_values = 0
                option.name = EMPTY
                option.desc = EMPTY

                # Remove everything on the option line and above.
                output = regex.group(2)

            # parse option
            elif regex2:
                output = _parse_option(regex2, option)

            else:
                break

            options.append(
                Option(
                    len(options) + 1,
                    option.name,
                    option.title,
                    option.desc,
                    option.type,
                    option.unit,
                    option.max_values,
                    option.cap,
                    option.constraint,
                )
            )

        if options:
            options.insert(
                0,
                Option(
                    0,
                    "",
                    "Number of options",
                    "Read-only option that specifies how many options a specific device supports.",
                    sane._sane.TYPE_INT,
                    sane._sane.UNIT_NONE,
                    4,
                    4,
                    None,
                ),
            )
        return options


def _parse_option(regex, option):
    # scanimage & scanadf only display options
    # if SANE_CAP_SOFT_DETECT is set
    option.cap = sane._sane.CAP_SOFT_DETECT + sane._sane.CAP_SOFT_SELECT
    option.name = regex.group(1)
    if regex.group(3) is not None:
        if regex.group(3) == "inactive":
            option.cap += sane._sane.CAP_INACTIVE

        else:
            option.val = regex.group(3)

        option.max_values = 1

    else:
        option.type = sane._sane.TYPE_BUTTON
        option.max_values = 0

    # parse the constraint after the current value
    # in order to be able to reset boolean values
    parse_constraint(option, regex.group(2))
    type2value(option)

    # Remove everything on the option line and above.
    output = regex.group(4)
    option.title = option.name
    option.title = re.sub(
        r"[-_]",
        r" ",
        option.title,
        flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
    )  # dashes and underscores to spaces
    option.title = re.sub(
        r"\b(adf|cct|jpeg)\b",
        lambda x: x.group(1).upper(),
        option.title,
        flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
    )  # upper case comment abbreviations
    option.title = re.sub(
        r"(^\w)",
        lambda x: x.group(1).upper(),
        option.title,
        flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
    )  # capitalise at the beginning of the line

    # Parse option description based on an 8-character indent.
    desc = EMPTY
    regex = re.search(
        r"""
            \A[ ]{8,}   # 8-character indent
            ([^\n]*)\n    # text
            (.*) # rest of output
            """,
        output,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    while regex:
        if desc == EMPTY:
            desc = regex.group(1)
        else:
            desc = f"{desc} {regex.group(1)}"

        # Remove everything on the description line and above.
        output = regex.group(2)
        regex = re.search(
            r"""
            \A[ ]{8,}   # 8-character indent
            ([^\n]*)\n    # text
            (.*) # rest of output
            """,
            output,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )

    option.desc = desc
    if option.name == "l":
        option.name = "tl-x"
        option.title = "Top-left x"

    elif option.name == "t":
        option.name = "tl-y"
        option.title = "Top-left y"

    elif option.name == "x":
        option.name = "br-x"
        option.title = "Bottom-right x"
        option.desc = "Bottom-right x position of scan area."

    elif option.name == "y":
        option.name = "br-y"
        option.title = "Bottom-right y"
        option.desc = "Bottom-right y position of scan area."

    return output


def within_tolerance(option, current_value, new_value, tolerance=0):
    "helper function, returning whether new_value is within the tolerance of current_value"
    if isinstance(option.constraint, tuple):
        if len(option.constraint) == 3:
            return bool(
                abs(new_value - current_value) <= option.constraint[2] / 2 + tolerance
            )

    if isinstance(option.constraint, list) or option.type in [
        sane._sane.TYPE_BOOL,
        sane._sane.TYPE_STRING,
    ]:
        return new_value == current_value

    if option.type in [sane._sane.TYPE_INT, sane._sane.TYPE_FIXED]:
        return abs(new_value - current_value) <= tolerance

    return False


def parse_constraint(option, values):
    "parse out range, step and units from the values string"
    option.type = sane._sane.TYPE_INT
    if option.val is not None and re.search(
        r"[.]", option.val, re.MULTILINE | re.DOTALL | re.VERBOSE
    ):
        option.type = sane._sane.TYPE_FIXED

    # if we haven't got a boolean, and there is no constraint, we have a button
    if values is None:
        option.type = sane._sane.TYPE_BUTTON
        option.max_values = 0
        return

    regex = re.search(
        rf"""
            (-?\d+[.]?\d*)          # min value, possibly negative or floating
            [.]{{2}}                # two dots
            (\d+[.]?\d*)            # max value, possible floating
            {UNITS}?                # optional unit
            (,...)?                 # multiple values
        """,
        values,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    regex2 = re.search(
        r"^<(\w+)>(,...)?$", values, re.MULTILINE | re.DOTALL | re.VERBOSE
    )
    if regex:
        parse_range_constraint(option, values, regex)

    elif regex2:
        if regex2.group(1) == "float":
            option.type = sane._sane.TYPE_FIXED

        elif regex2.group(1) == "string":
            option.type = sane._sane.TYPE_STRING

        if regex2.group(2) is not None:
            option.max_values = MAX_VALUES

    else:
        parse_list_constraint(option, values)


def parse_range_constraint(option, values, regex):
    "parse min, max, step"
    mini = regex.group(1)
    maxi = regex.group(2)
    quant = "0"
    option.constraint_type = "CONSTRAINT_RANGE"
    if regex.group(3) is not None:
        option.unit = UNIT2ENUM[regex.group(3)]
    if regex.group(4) is not None:
        option.max_values = MAX_VALUES
    regex = re.search(
        r"""
                       [(]              # opening round bracket
                       in[ ]steps[ ]of[ ] # text
                       (\d+[.]?\d*)     # step
                       [)]              # closing round bracket
                     """,
        values,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    if regex:
        quant = regex.group(1)

    if (
        re.search(
            r"[.]",
            mini,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        or re.search(
            r"[.]",
            maxi,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        or re.search(
            r"[.]",
            quant,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
    ):
        option.type = sane._sane.TYPE_FIXED
        option.constraint = (float(mini), float(maxi), float(quant))
    else:
        option.constraint = (int(mini), int(maxi), int(quant))


def parse_list_constraint(option, values):
    "parse list constraint"
    regex = re.search(r"(.*),...", values, re.MULTILINE | re.DOTALL | re.VERBOSE)
    if regex:
        values = regex.group(1)
        option.max_values = MAX_VALUES

    regex = re.search(rf"(.*){UNITS}$", values, re.MULTILINE | re.DOTALL | re.VERBOSE)
    if regex:
        values = regex.group(1)
        option.unit = UNIT2ENUM[regex.group(2)]

    array = re.split(r"[|]+", values)
    if array:
        if array[0] == "auto":
            option.cap += sane._sane.CAP_AUTOMATIC
            array.pop(0)

        if len(array) == 2 and array[0] == "yes" and array[1] == "no":
            option.type = sane._sane.TYPE_BOOL
            type2value(option)

        else:

            # Can't check before because 'auto' would mess things up
            for i, val in enumerate(array):
                if re.search(r"[A-Za-z]", val, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    option.type = sane._sane.TYPE_STRING

                elif re.search(r"[.]", val, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    option.type = sane._sane.TYPE_FIXED

                if option.type == sane._sane.TYPE_INT:
                    array[i] = int(val)
            option.constraint = array
            option.constraint_type = (
                "CONSTRAINT_STRING_LIST"
                if option.type == sane._sane.TYPE_STRING
                else "CONSTRAINT_WORD_LIST"
            )


def type2value(option):
    "typify the value of the option"
    if option.val is not None:
        if option.type == sane._sane.TYPE_INT:
            option.val = int(option.val)
        elif option.type == sane._sane.TYPE_FIXED:
            option.val = float(option.val)
        elif option.type == sane._sane.TYPE_BOOL and isinstance(option.val, str):
            if option.val == "yes":
                option.val = True
            else:
                option.val = False

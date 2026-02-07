"GUI for unpaper"

import re
import subprocess
import logging
import gi
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


class Unpaper:
    "GUI for unpaper"

    _version = None

    def __init__(self, default=None):

        self.default = default if default is not None else {}

        # Set up hash for options
        self.options = {
            "layout": {
                "type": "ComboBox",
                "string": _("Layout"),
                "options": {
                    "single": {
                        "string": _("Single"),
                        "tooltip": _(
                            "One page per sheet, oriented upwards without rotation."
                        ),
                    },
                    "double": {
                        "string": _("Double"),
                        "tooltip": _(
                            "Two pages per sheet, landscape orientation "
                            "(one page on the left half, one page on the right half)."
                        ),
                    },
                },
                "default": "single",
            },
            "output-pages": {
                "type": "SpinButton",
                "string": _("# Output pages"),
                "tooltip": _("Number of pages to output."),
                "min": 1,
                "max": 2,
                "step": 1,
                "default": 1,
            },
            "direction": {
                "type": "ComboBox",
                "string": _("Writing system"),
                "options": {
                    "ltr": {
                        "string": _("Left-to-right"),
                        "tooltip": _(
                            "Most writings systems, e.g. Latin, Greek, Cyrillic."
                        ),
                    },
                    "rtl": {
                        "string": _("Right-to-left"),
                        "tooltip": _("Scripts like Arabic or Hebrew."),
                    },
                },
                "default": "ltr",
                "export": False,
            },
            "no-deskew": {
                "type": "CheckButton",
                "string": _("No deskew"),
                "tooltip": _("Disable deskewing."),
                "default": False,
            },
            "no-mask-scan": {
                "type": "CheckButton",
                "string": _("No mask scan"),
                "tooltip": _("Disable mask detection."),
                "default": False,
            },
            "no-mask-center": {
                "type": "CheckButton",
                "string": _("No mask centering"),
                "tooltip": _("Disable mask centering."),
                "default": False,
            },
            "no-blackfilter": {
                "type": "CheckButton",
                "string": _("No black filter"),
                "tooltip": _("Disable black area scan."),
                "default": False,
            },
            "no-grayfilter": {
                "type": "CheckButton",
                "string": _("No gray filter"),
                "tooltip": _("Disable gray area scan."),
                "default": False,
            },
            "no-noisefilter": {
                "type": "CheckButton",
                "string": _("No noise filter"),
                "tooltip": _("Disable noise filter."),
                "default": False,
            },
            "no-blurfilter": {
                "type": "CheckButton",
                "string": _("No blur filter"),
                "tooltip": _("Disable blur filter."),
                "default": False,
            },
            "no-border-scan": {
                "type": "CheckButton",
                "string": _("No border scan"),
                "tooltip": _("Disable border scanning."),
                "default": False,
            },
            "no-border-align": {
                "type": "CheckButton",
                "string": _("No border align"),
                "tooltip": _(
                    "Disable aligning of the area detected by border scanning."
                ),
                "default": False,
            },
            "deskew-scan-direction": {
                "type": "CheckButtonGroup",
                "string": _("Deskew to edge"),
                "tooltip": _(
                    "Edges from which to scan for rotation. Each edge of a mask"
                    " can be used to detect the mask's rotation. If multiple "
                    "edges are specified, the average value will be used, "
                    "unless the statistical deviation exceeds --deskew-scan-deviation."
                ),
                "options": {
                    "left": {
                        "type": "CheckButton",
                        "string": _("Left"),
                        "tooltip": _("Use 'left' for scanning from the left edge."),
                    },
                    "top": {
                        "type": "CheckButton",
                        "string": _("Top"),
                        "tooltip": _("Use 'top' for scanning from the top edge."),
                    },
                    "right": {
                        "type": "CheckButton",
                        "string": _("Right"),
                        "tooltip": _("Use 'right' for scanning from the right edge."),
                    },
                    "bottom": {
                        "type": "CheckButton",
                        "string": _("Bottom"),
                        "tooltip": _("Use 'bottom' for scanning from the bottom."),
                    },
                },
                "default": "left,right",
            },
            "border-align": {
                "type": "CheckButtonGroup",
                "string": _("Align to edge"),
                "tooltip": _("Edge to which to align the page."),
                "options": {
                    "left": {
                        "type": "CheckButton",
                        "string": _("Left"),
                        "tooltip": _("Use 'left' to align to the left edge."),
                    },
                    "top": {
                        "type": "CheckButton",
                        "string": _("Top"),
                        "tooltip": _("Use 'top' to align to the top edge."),
                    },
                    "right": {
                        "type": "CheckButton",
                        "string": _("Right"),
                        "tooltip": _("Use 'right' to align to the right edge."),
                    },
                    "bottom": {
                        "type": "CheckButton",
                        "string": _("Bottom"),
                        "tooltip": _("Use 'bottom' to align to the bottom."),
                    },
                },
            },
            "border-margin": {
                "type": "SpinButtonGroup",
                "string": _("Border margin"),
                "options": {
                    "vertical": {
                        "type": "SpinButton",
                        "string": _("Vertical margin"),
                        "tooltip": _(
                            "Vertical distance to keep from the sheet edge when"
                            " aligning a border area."
                        ),
                        "min": 0,
                        "max": 1000,
                        "step": 1,
                        "order": 0,
                    },
                    "horizontal": {
                        "type": "SpinButton",
                        "string": _("Horizontal margin"),
                        "tooltip": _(
                            "Horizontal distance to keep from the sheet edge "
                            "when aligning a border area."
                        ),
                        "min": 0,
                        "max": 1000,
                        "step": 1,
                        "order": 1,
                    },
                },
            },
            "white-threshold": {
                "type": "SpinButton",
                "string": _("White threshold"),
                "tooltip": _(
                    "Brightness ratio above which a pixel is considered white."
                ),
                "min": 0,
                "max": 1,
                "step": 0.01,
                "default": 0.9,
            },
            "black-threshold": {
                "type": "SpinButton",
                "string": _("Black threshold"),
                "tooltip": _(
                    "Brightness ratio below which a pixel is considered black "
                    "(non-gray). This is used by the gray-filter. This value is"
                    " also used when converting a grayscale image to black-and-white mode."
                ),
                "min": 0,
                "max": 1,
                "step": 0.01,
                "default": 0.33,
            },
        }

    def _add_notebook_page_1(self, vbox, options):
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox1.set_border_width(vbox.get_border_width())
        dsbutton = self.add_widget(vbox1, options, "no-deskew")

        # Frame for Deskew Scan Direction
        dframe = self.add_widget(vbox1, options, "deskew-scan-direction")

        def dsbutton_toggled_cb(_widget):
            if dsbutton.get_active():
                dframe.set_sensitive(False)
            else:
                dframe.set_sensitive(True)

        def deskew_scan_direction_button_cb(widget):
            "Ensure that at least one checkbutton stays active"
            if count_active_children(dframe) == 0:
                widget.set_active(True)

        dsbutton.connect("toggled", dsbutton_toggled_cb)
        for key in options["deskew-scan-direction"]["options"]:
            button = options["deskew-scan-direction"]["options"][key]["widget"]
            button.connect("toggled", deskew_scan_direction_button_cb)

        return vbox1

    def _add_notebook_page_2(self, vbox, options):
        vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox2.set_border_width(vbox.get_border_width())
        bsbutton = self.add_widget(vbox2, options, "no-border-scan")
        babutton = self.add_widget(vbox2, options, "no-border-align")

        # Frame for Align Border
        bframe = self.add_widget(vbox2, options, "border-align")

        def bsbutton_toggled_cb(_widget):
            if bsbutton.get_active():
                bframe.set_sensitive(False)
                babutton.set_sensitive(False)
            else:
                babutton.set_sensitive(True)
                if not babutton.get_active():
                    bframe.set_sensitive(True)

        bsbutton.connect("toggled", bsbutton_toggled_cb)

        def babutton_toggled_cb(_widget):
            if babutton.get_active():
                bframe.set_sensitive(False)
            else:
                bframe.set_sensitive(True)

        babutton.connect("toggled", babutton_toggled_cb)

        # Define margins here to reference them below
        bmframe = self.add_widget(vbox2, options, "border-margin")

        def border_align_button_cb(_widget):
            "Ghost margin if nothing selected"
            bmframe.set_sensitive(count_active_children(bframe) > 0)

        for key in options["border-align"]["options"]:
            button = options["border-align"]["options"][key]["widget"]
            button.connect("toggled", border_align_button_cb)

        bmframe.set_sensitive(count_active_children(bframe) > 0)
        return vbox2

    def add_options(self, vbox):
        "Add options to given vbox"
        options = self.options

        # Layout ComboBox
        combobl = self.add_widget(vbox, options, "layout")
        outpages = self.add_widget(vbox, options, "output-pages")

        def combobl_changed_cb(_widget):
            if self.get_option("layout") == "double":
                outpages.set_range(1, 2)
            else:
                outpages.set_range(1, 1)

        combobl.connect("changed", combobl_changed_cb)
        combobw = self.add_widget(vbox, options, "direction")

        def outpages_changed_cb(_widget):
            combobw.get_parent().set_sensitive(outpages.get_value_as_int() == 2)

        outpages.connect("value-changed", outpages_changed_cb)
        combobw.get_parent().set_sensitive(False)

        # Notebook to collate options
        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)

        vbox1 = self._add_notebook_page_1(vbox, options)
        notebook.append_page(vbox1, Gtk.Label(label=_("Deskew")))

        # Notebook page 2
        vbox2 = self._add_notebook_page_2(vbox, options)
        notebook.append_page(vbox2, Gtk.Label(label=_("Border")))

        # Notebook page 3
        vbox3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox3.set_border_width(vbox.get_border_width())
        notebook.append_page(vbox3, Gtk.Label(label=_("Filters")))
        self.add_widget(vbox3, options, "white-threshold")
        self.add_widget(vbox3, options, "black-threshold")
        msbutton = self.add_widget(vbox3, options, "no-mask-scan")
        mcbutton = self.add_widget(vbox3, options, "no-mask-center")
        self.add_widget(vbox3, options, "no-blackfilter")
        self.add_widget(vbox3, options, "no-grayfilter")
        self.add_widget(vbox3, options, "no-noisefilter")
        self.add_widget(vbox3, options, "no-blurfilter")

        def msbutton_toggled_cb(_widget):
            "make no-mask-center depend on no-mask-scan"
            if msbutton.get_active():
                mcbutton.set_sensitive(False)
            else:
                mcbutton.set_sensitive(True)

        msbutton.connect("toggled", msbutton_toggled_cb)

        # Having added the widgets with callbacks if necessary, set the defaults
        self.set_options(self.default)

    def _add_combobox(self, vbox, hashref, option):  # pylint: disable=no-self-use
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=hashref[option]["string"])
        hbox.pack_start(label, False, False, 0)
        widget = Gtk.ComboBoxText()
        hbox.pack_end(widget, False, False, 0)

        # Add text and tooltips
        tooltip = []
        i = 0
        for key in hashref[option]["options"].keys():
            widget.append_text(hashref[option]["options"][key]["string"])
            tooltip.append(hashref[option]["options"][key]["tooltip"])
            hashref[option]["options"][key]["index"] = i
            i += 1

        def combobox_changed_cb(_widget):
            if widget.get_active() in tooltip:
                widget.set_tooltip_text(tooltip[widget.get_active()])

        widget.connect("changed", combobox_changed_cb)
        return widget

    def _add_checkbutton(self, vbox, hashref, option):  # pylint: disable=no-self-use
        widget = Gtk.CheckButton(label=hashref[option]["string"])
        widget.set_tooltip_text(hashref[option]["tooltip"])
        vbox.pack_start(widget, True, True, 0)
        return widget

    def _add_checkbuttongroup(self, vbox, hashref, option):
        widget = Gtk.Frame(label=hashref[option]["string"])
        vbox.pack_start(widget, True, True, 0)
        vboxf = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxf.set_border_width(vbox.get_border_width())
        widget.add(vboxf)
        widget.set_tooltip_text(hashref[option]["tooltip"])
        for key in hashref[option]["options"].keys():
            self.add_widget(vboxf, hashref[option]["options"], key)
        return widget

    def _add_spinbutton(self, vbox, hashref, option):
        default = self.default
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=hashref[option]["string"])
        hbox.pack_start(label, False, False, 0)
        widget = Gtk.SpinButton.new_with_range(
            hashref[option]["min"], hashref[option]["max"], hashref[option]["step"]
        )
        hbox.pack_end(widget, False, False, 0)
        widget.set_tooltip_text(hashref[option]["tooltip"])
        if option in default:
            widget.set_value(default[option])
        return widget

    def _add_spinbuttongroup(self, vbox, hashref, option):
        widget = Gtk.Frame(label=hashref[option]["string"])
        vbox.pack_start(widget, True, True, 0)
        vboxf = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxf.set_border_width(vbox.get_border_width())
        widget.add(vboxf)
        for key in sorted(hashref[option]["options"].keys()):
            self.add_widget(vboxf, hashref[option]["options"], key)
        return widget

    def add_widget(self, vbox, hashref, option):
        "Add widget to unpaper dialog"
        default = self.default
        widget = None
        if "default" in hashref[option] and option not in default:
            default[option] = hashref[option]["default"]

        if hashref[option]["type"] in [
            "ComboBox",
            "CheckButton",
            "CheckButtonGroup",
            "SpinButton",
            "SpinButtonGroup",
        ]:
            method_name = "_add_" + hashref[option]["type"].lower()
            method = getattr(self, method_name, None)
            widget = method(vbox, hashref, option)  # pylint: disable=not-callable

        hashref[option]["widget"] = widget
        return widget

    def _combobox_get_option(self, option):
        "get option for combobox"
        hashref = self.options
        i = hashref[option]["widget"].get_active()
        for key in hashref[option]["options"]:
            if hashref[option]["options"][key]["index"] == i:
                return key
        return None

    def _checkbutton_get_option(self, option):
        "get option for checkbutton"
        return self.options[option]["widget"].get_active()

    def _checkbuttongroup_get_option(self, option):
        "get option for checkbuttongroup"
        hashref = self.options
        items = []
        for key in sorted(hashref[option]["options"]):
            if hashref[option]["options"][key]["widget"].get_active():
                items.append(key)

        if items:
            return ",".join(items)
        return None

    def _spinbutton_get_option(self, option):
        "get option for spinbutton"
        if self.options[option]["step"] >= 1:
            return self.options[option]["widget"].get_value_as_int()
        return self.options[option]["widget"].get_value()

    def _spinbuttongroup_get_option(self, option):
        "get option for spinbuttongroup"
        hashref = self.options
        items = []
        for key in hashref[option]["options"]:
            items.append(str(hashref[option]["options"][key]["widget"].get_value()))

        if items:
            return ",".join(items)
        return None

    def get_option(self, option):
        "return given option"
        options = self.options
        default = self.default
        if "widget" in options[option] and options[option]["type"] in [
            "ComboBox",
            "CheckButton",
            "CheckButtonGroup",
            "SpinButton",
            "SpinButtonGroup",
        ]:
            method_name = "_" + options[option]["type"].lower() + "_get_option"
            method = getattr(self, method_name, None)
            return method(option)  # pylint: disable=not-callable

        if option in default:
            return default[option]
        if option in options and "default" in options[option]:
            return options[option]["default"]
        return None

    def get_options(self):
        "return all options"
        options = self.options
        default = self.default
        for option in options:
            value = self.get_option(option)
            if value is not None:
                default[option] = value

        return default

    def _combobox_set_option(self, option, options):
        "set option for combobox"
        hashref = self.options
        i = hashref[option]["options"][options[option]]["index"]
        if i is not None:
            hashref[option]["widget"].set_active(i)

    def _checkbutton_set_option(self, option, options):
        "set option for checkbutton"
        self.options[option]["widget"].set_active(options[option])

    def _checkbuttongroup_set_option(self, option, options):
        "set option for checkbuttongroup"
        hashref = self.options
        default = {}
        if option in options:
            for key in re.split(r",", options[option]):
                default[key] = True

        for key in hashref[option]["options"].keys():
            hashref[option]["options"][key]["widget"].set_active(key in default)

    def _spinbutton_set_option(self, option, options):
        "set option for spinbutton"
        self.options[option]["widget"].set_value(options[option])

    def _spinbuttongroup_set_option(self, option, options):
        "set option for spinbuttongroup"
        hashref = self.options
        default = []
        if option in options:
            default = re.split(r",", options[option])

        for key in sorted(hashref[option]["options"].keys()):
            if default:
                hashref[option]["options"][key]["widget"].set_value(
                    float(default.pop(0))
                )

    def set_options(self, options):
        "set options"
        hashref = self.options
        for option in options.keys():
            if "widget" in hashref[option] and hashref[option]["type"] in [
                "ComboBox",
                "CheckButton",
                "CheckButtonGroup",
                "SpinButton",
                "SpinButtonGroup",
            ]:
                method_name = "_" + hashref[option]["type"].lower() + "_set_option"
                method = getattr(self, method_name, None)
                method(option, options)

    def get_cmdline(self):
        "return list for unpaper subprocess call"
        hashref = self.options
        options = self.get_options()
        items = ["unpaper"]
        for option in sorted(hashref.keys()):
            if "export" in hashref[option] and not hashref[option]["export"]:
                continue

            if hashref[option]["type"] == "CheckButton":
                if option in options and options[option]:
                    items.append(f"--{option}")
            elif hashref[option]["type"] == "SpinButton":
                if option in options:
                    items += [f"--{option}", f"{self.get_option(option)}"]
            else:
                if option in options:
                    items += [f"--{option}", f"{options[option]}"]
        return items + ["--overwrite", "%s", "%s", "%s"]

    def program_version(self):
        "return program version"
        if self._version is None:
            version = program_version("stdout", r"([\d.]+)", ["unpaper", "--version"])
            if version is not None:
                self._version = version
        return self._version


def count_active_children(frame):
    "helper function to count active children in the frame"
    num = 0
    for child in frame.get_child().get_children():
        if child.get_active():
            num += 1
    return num


def program_version(stream, regex, cmd):
    "return program version"
    try:
        version = _program_version(
            stream,
            regex,
            subprocess.run(cmd, check=True, capture_output=True, text=True),
        )
    except FileNotFoundError:
        version = None
    return version


def _program_version(stream, regex, output):
    if stream == "stdout":
        output = output.stdout
    elif stream == "stderr":
        output = output.stderr
    elif stream == "both":
        output = output.stdout + output.stderr
    else:
        logger.error("Unknown stream: '%s'", stream)

    regex2 = re.search(regex, output)
    if regex2:
        return regex2.group(1)

    logger.info("Unable to parse version string from: '%s'", output)
    return None

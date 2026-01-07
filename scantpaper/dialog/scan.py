"Scan dialog"  # pylint: disable=too-many-lines

import re
import weakref
from copy import copy
import logging
from gi.repository import Gdk, Gtk, GObject
from comboboxtext import ComboBoxText
from dialog.paperlist import PaperList
from dialog.pagecontrols import PageControls, MAX_PAGES
from scanner.profile import Profile
from scanner.options import Options, within_tolerance
from i18n import _, d_sane
from const import POINTS_PER_INCH
from frontend import enums
from helpers import _weak_callback
from . import Dialog

PAPER_TOLERANCE = 1
OPTION_TOLERANCE = 0.001
CANVAS_SIZE = 200
CANVAS_BORDER = 10
CANVAS_POINT_SIZE = 10
CANVAS_MIN_WIDTH = 1
NO_INDEX = -1

logger = logging.getLogger(__name__)


class Scan(PageControls):  # pylint: disable=too-many-instance-attributes
    "Scan dialog"

    __gsignals__ = {
        "new-scan": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                object,  # Image object
                int,  # page number
                float,  # x-resolution
                float,  # y-resolution
            ),
        ),
        "changed-device": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "changed-device-list": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-scan-option": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                object,
                object,
                object,
            ),
        ),
        "changed-option-visibility": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-current-scan-options": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                object,
                str,
            ),
        ),
        "reloaded-scan-options": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "changed-profile": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "added-profile": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                object,
                object,
            ),
        ),
        "removed-profile": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-paper": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-paper-formats": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "started-process": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-progress": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                object,
                object,
            ),
        ),
        "finished-process": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "process-error": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                str,
                str,
            ),
        ),
        "clicked-scan-button": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    _device = ""
    _device_list = []
    dir = GObject.Property(
        type=object, nick="Directory", blurb="Directory in which to store scans"
    )
    _profile = None

    @GObject.Property(type=object, nick="Profile", blurb="Name of current profile")
    def profile(self):  # pylint: disable=method-hidden
        "getter for profile attribute"
        return self._profile

    @profile.setter
    def profile(self, newval):
        if newval == self._profile:
            return
        signal = None

        def do_changed_profile(_arg1, _arg2):
            self.disconnect(signal)
            self.combobsp.set_active_by_text(newval)

        signal = self.connect("changed-profile", do_changed_profile)
        self.set_profile(newval)

    _paper = ""

    @GObject.Property(
        type=str,
        default="",
        nick="Paper",
        blurb="Name of currently selected paper format",
    )
    def paper(self):
        "getter for paper attribute"
        return self._paper

    @paper.setter
    def paper(self, newval):
        if newval == self._paper:
            return
        if newval is not None:
            for fmt in self.ignored_paper_formats:
                if fmt == newval:
                    logger.info("Ignoring unsupported paper %s", newval)
                    return

        signal = None

        def do_changed_paper(_arg1, _arg2):
            nonlocal signal
            self.disconnect(signal)
            paper = _("Manual") if newval is None else newval
            self.combobp.set_active_by_text(paper)

        signal = self.connect("changed-paper", do_changed_paper)
        self._set_paper(newval)

    _paper_formats = {}

    @GObject.Property(
        type=object,
        nick="Paper formats",
        blurb="Hash of arrays defining paper formats, e.g. A4, Letter, etc.",
    )
    def paper_formats(self):
        "getter for paper_formats attribute"
        return self._paper_formats

    @paper_formats.setter
    def paper_formats(self, newval):
        self._paper_formats = newval
        self._set_paper_formats(newval)
        self.emit("changed-paper-formats", newval)

    _available_scan_options = Options([])
    _current_scan_options = Profile()
    _visible_scan_options = {}

    @GObject.Property(
        type=object,
        nick="Visible scan options",
        blurb="Hash of scan options to show or hide from the user",
    )
    def visible_scan_options(self):
        "getter for visible_scan_options attribute"
        return self._visible_scan_options

    @visible_scan_options.setter
    def visible_scan_options(self, newval):
        self._visible_scan_options = newval
        self.emit("changed-option-visibility", newval)

    progress_pulse_step = GObject.Property(
        type=float,
        minimum=0.0,
        maximum=1.0,
        default=0.1,
        nick="Progress pulse step",
        blurb="Pulse step of progress bar",
    )
    _allow_batch_flatbed = False
    reload_recursion_limit = GObject.Property(
        type=int,
        minimum=0,
        maximum=MAX_PAGES,
        default=0,
        nick="Reload recursion limit",
        blurb="More reloads than this are considered infinite loop",
    )
    num_reloads = GObject.Property(
        type=int,
        minimum=0,
        maximum=MAX_PAGES,
        default=0,
        nick="Number of reloads",
        blurb="To compare against reload-recursion-limit",
    )
    _cursor = "default"
    _ignore_duplex_capabilities = False

    @GObject.Property(type=str, default="", nick="Device", blurb="Device name")
    def device(self):
        "getter for device attribute"
        return self._device

    @device.setter
    def device(self, newval):
        if self._device != newval:
            self._device = newval
            self.set_device(newval)
            self.emit("changed-device", newval)

    @GObject.Property(
        type=object, nick="Device list", blurb="Array of hashes of available devices"
    )
    def device_list(self):
        "getter for device_list attribute"
        return self._device_list

    @device_list.setter
    def device_list(self, newval):
        self._device_list = newval
        self.set_device_list(newval)
        self.emit("changed-device-list", newval)

    @GObject.Property(
        type=bool,
        default=False,
        nick="Allow batch scanning from flatbed",
        blurb="Allow batch scanning from flatbed",
    )
    def allow_batch_flatbed(self):
        "getter for allow_batch_flatbed attribute"
        return self._allow_batch_flatbed

    @allow_batch_flatbed.setter
    def allow_batch_flatbed(self, newval):
        self._allow_batch_flatbed = newval
        if newval:
            self.framen.set_sensitive(True)
        else:
            options = self.available_scan_options

            # on startup, self.thread doesn't get defined until later
            if (
                hasattr(self, "thread")
                and options is not None
                and options.flatbed_selected(self.thread.device_handle)
            ):
                self.framen.set_sensitive(False)

                # emits changed-num-pages signal, allowing us to test
                # for $self->{framen}->set_sensitive(FALSE)
                self.num_pages = 1

    @GObject.Property(
        type=bool,
        default=False,
        nick="Ignore duplex capabilities",
        blurb="Ignore duplex capabilities",
    )
    def ignore_duplex_capabilities(self):
        "getter for ignore_duplex_capabilities attribute"
        return self._ignore_duplex_capabilities

    @ignore_duplex_capabilities.setter
    def ignore_duplex_capabilities(self, newval):
        self._ignore_duplex_capabilities = newval
        self._flatbed_or_duplex_callback()

    @GObject.Property(
        type=object,
        nick="Scan options available",
        blurb="Scan options currently available, whether active, selected, or not",
    )  # pylint: disable=method-hidden
    def available_scan_options(self):
        "getter for available_scan_options attribute"
        return self._available_scan_options

    @available_scan_options.setter
    def available_scan_options(self, newval):
        self._available_scan_options = newval
        if not self.allow_batch_flatbed and newval.flatbed_selected(
            self.thread.device_handle
        ):
            if self.num_pages != 1:
                self.num_pages = 1
            self.framen.set_sensitive(False)
        else:
            self.framen.set_sensitive(True)

        self._flatbed_or_duplex_callback()

        # reload-recursion-limit is read-only
        # Triangular number n + n-1 + n-2 + ... + 1 = n*(n+1)/2
        num = newval.num_options()
        self.reload_recursion_limit = num * (num + 1) // 2
        self.emit("reloaded-scan-options")

    @GObject.Property(type=object, nick="Cursor", blurb="name of current cursor")
    def cursor(self):  # pylint: disable=method-hidden
        "getter for cursor attribute"
        return self._cursor

    @cursor.setter
    def cursor(self, newval):
        "set the cursor"
        win = self.get_window()
        if newval is None:
            newval = self.cursor

        if win is not None:
            display = Gdk.Display.get_default()
            win.set_cursor(Gdk.Cursor.new_from_name(display, newval))

        self.scan_button.set_sensitive(newval == "default")

    @GObject.Property(
        type=object,
        nick="Current scan options",
        blurb="Scan options making up current profile",
    )  # pylint: disable=method-hidden
    def current_scan_options(self):
        "getter for current_scan_options attribute"
        return self._current_scan_options

    @current_scan_options.setter
    def current_scan_options(self, newval):
        self._current_scan_options = newval

    combobp = None

    def __init__(self, *args, **kwargs):
        profiles = {}
        if "profiles" in kwargs:
            profiles = kwargs.pop("profiles")
        super().__init__(*args, **kwargs)

        self.ignored_paper_formats = []
        self.option_widgets = {}
        self._geometry_boxes = {}

        self.connect("show", self.show)
        self._add_device_combobox()

        # Scan profiles
        self.profiles = {}
        framesp = Gtk.Frame(label=_("Scan profiles"))
        self._notebook_pages[0].pack_start(framesp, False, False, 0)
        vboxsp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        border_width = (
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        vboxsp.set_border_width(border_width)
        framesp.add(vboxsp)
        self.combobsp = ComboBoxText()
        for profile in profiles.keys():
            self._add_profile(
                profile,
                Profile(
                    frontend=profiles[profile]["frontend"],
                    backend=profiles[profile]["backend"],
                ),
            )
        self.combobsp_changed_signal = self.combobsp.connect(
            "changed", _weak_callback(self, "_do_profile_changed")
        )
        vboxsp.pack_start(self.combobsp, False, False, 0)
        hboxsp = Gtk.Box()
        vboxsp.pack_end(hboxsp, False, False, 0)

        # Save button
        ref = weakref.ref(self)
        icon = Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.BUTTON)
        vbutton = Gtk.Button()
        vbutton.set_image(icon)
        vbutton.connect("clicked", lambda w: _save_profile_callback(w, ref()))
        hboxsp.pack_start(vbutton, True, True, 0)

        # Edit button
        icon = Gtk.Image.new_from_icon_name("document-edit", Gtk.IconSize.BUTTON)
        ebutton = Gtk.Button()
        ebutton.set_image(icon)
        ebutton.connect("clicked", lambda w: _edit_profile_callback(w, ref()))
        hboxsp.pack_start(ebutton, False, False, 0)

        # Delete button
        icon = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON)
        dbutton = Gtk.Button()
        dbutton.set_image(icon)
        dbutton.connect(
            "clicked",
            lambda x: ref() and ref()._remove_profile(ref().combobsp.get_active_text()),
        )
        hboxsp.pack_start(dbutton, False, False, 0)

        self.scan_button = self.add_actions(
            [(_("Scan"), self._do_scan), ("gtk-close", self.hide)]
        )[0]

        # initialise stack of uuids - needed for cases where setting a profile
        # requires several reloads, and therefore reapplying the same profile
        # several times. Tested by t/06198_Dialog_Scan_Image_Sane.t
        self.setting_profile = []
        self.setting_current_scan_options = []
        self.connect(
            "changed-scan-option", self._changed_scan_option_callback, self._bscannum
        )

    def _add_device_combobox(self):
        self.hboxd = Gtk.Box()
        labeld = Gtk.Label(label=_("Device"))
        self.hboxd.pack_start(labeld, False, False, 0)
        self.combobd = ComboBoxText()
        self.combobd.append_text(_("Rescan for devices"))

        ref = weakref.ref(self)

        def do_device_dropdown_changed(_arg):
            self = ref()
            if self is None:
                return
            index = self.combobd.get_active()
            device_list = self.device_list
            if index > len(device_list) - 1:
                self.combobd.hide()
                labeld.hide()
                self.device = None  # to make sure that the device is reloaded
                self.get_devices()

            elif index > NO_INDEX:
                self.device = device_list[index].name

        self.combobd_changed_signal = self.combobd.connect(
            "changed", do_device_dropdown_changed
        )

        def do_changed_device(self, device):
            device_list = self.device_list
            if device not in [None, ""]:
                for dev in device_list:
                    if dev.name == device:
                        self.combobd.set_active_by_text(dev.label)
                        self.scan_options(device)
                        return
            else:
                self.combobd.set_active(NO_INDEX)

        self.connect("changed-device", do_changed_device)
        self.combobd.set_tooltip_text(_("Sets the device to be used for the scan"))
        self.hboxd.pack_end(self.combobd, False, False, 0)
        self.get_content_area().pack_start(self.hboxd, False, False, 0)

    def _do_scan(self):
        self.emit("clicked-scan-button")
        self.scan()

    def _do_profile_changed(self, combobsp):
        self.num_reloads = 0  # num-reloads is read-only
        self.profile = combobsp.get_active_text()

    def show(self, *args, **kwargs):
        PageControls.show(self, **kwargs)
        self.framex.hide()
        self._flatbed_or_duplex_callback()
        if (
            self.combobp is not None
            and self.combobp.get_active_text() is not None
            and self.combobp.get_active_text() != _("Manual")
        ):
            self._hide_geometry(self.available_scan_options)
        self.cursor = "default"

    def set_device(self, device):
        "set the active device"
        if device not in [None, ""]:
            idev = None
            device_list = self.device_list
            if len(device_list):
                for i, dev in enumerate(device_list):
                    if device == dev.name:
                        idev = i

                # Set the device dependent options after the number of pages
                #  to scan so that the source button callback can ghost the
                #  all button.
                # This then fires the callback, updating the options,
                #  so no need to do it further down.
                if idev is not None:
                    self.combobd.set_active(idev)
                else:
                    self.emit(
                        "process-error",
                        "open_device",
                        _("Error: unknown device: %s") % (device),
                    )

    def set_device_list(self, device_list):
        "fill the combobox with the list of devices"
        # Note any duplicate device names and delete if necessary
        seen = {}
        i = 0
        while i < len(device_list):
            if device_list[i].name not in seen:
                seen[device_list[i].name] = 0
            seen[device_list[i].name] += 1
            if seen[device_list[i].name] > 1:
                del device_list[i]

            else:
                i += 1

        # Note any duplicate model names and add the device if necessary
        seen = {}
        for dev in device_list:
            if not hasattr(dev, "model") or dev.model in [None, ""]:
                dev.model = dev.name
            if dev.model not in seen:
                seen[dev.model] = 0
            seen[dev.model] += 1

        for dev in device_list:
            if hasattr(dev, "vendor") and dev.vendor not in [None, ""]:
                dev.label = f"{dev.vendor} {dev.model}"
            else:
                dev.label = dev.model

            if seen[dev.model] > 1:
                dev.label += f" on {dev.name}"

        self.combobd.handler_block(self.combobd_changed_signal)

        # Remove all entries apart from rescan
        num_rows = self.combobd.get_num_rows()
        while num_rows > 1:
            num_rows -= 1
            self.combobd.remove(0)

        # read the model names into the combobox
        for i, dev in enumerate(device_list):
            self.combobd.insert_text(i, dev.label)

        self.combobd.handler_unblock(self.combobd_changed_signal)

    def _pack_widget(self, widget, data):
        "pack the given widget in the dialog"
        options, opt, hbox, hboxp = data
        if widget is not None:

            # Add label for units
            if opt.unit != enums.UNIT_NONE:
                text = None
                if opt.unit == enums.UNIT_PIXEL:
                    text = _("pel")

                elif opt.unit == enums.UNIT_BIT:
                    text = _("bit")

                elif opt.unit == enums.UNIT_MM:
                    text = _("mm")

                elif opt.unit == enums.UNIT_DPI:
                    text = _("ppi")

                elif opt.unit == enums.UNIT_PERCENT:
                    text = _("%")

                elif opt.unit == enums.UNIT_MICROSECOND:
                    text = _("μs")

                label = Gtk.Label(label=text)
                hbox.pack_end(label, False, False, 0)

            self.option_widgets[opt.name] = widget
            if opt.type == enums.TYPE_BUTTON:
                hbox.pack_end(widget, True, True, 0)

            else:
                hbox.pack_end(widget, False, False, 0)

            widget.set_tooltip_text(d_sane(opt.desc))

            # Look-up to hide/show the box if necessary
            if _geometry_option(opt):
                self._geometry_boxes[opt.name] = hbox

            self._create_paper_widget(options, hboxp)

        else:
            logger.warning("Unknown type %s", opt.type)

    def _create_paper_widget(self, options, hboxp):
        "create the paper widget"
        # Only define the paper size once the rest of the geometry widgets
        # have been created
        if (
            all(key in self._geometry_boxes for key in ["br-x", "br-y", "tl-x", "tl-y"])
            and all(
                (options.by_name(key) is None or key in self._geometry_boxes)
                for key in ["page-height", "page-width"]
            )
            and (not hasattr(self, "combobp") or self.combobp is None)
            and hboxp is not None
        ):

            # Paper list
            label = Gtk.Label(label=_("Paper size"))
            hboxp.pack_start(label, False, False, 0)
            self.combobp = ComboBoxText()
            self.combobp.append_text(_("Manual"))
            self.combobp.append_text(_("Edit"))
            self.combobp.set_tooltip_text(_("Selects or edits the paper size"))
            hboxp.pack_end(self.combobp, False, False, 0)
            self.combobp.set_active(0)

            def do_paper_size_changed(_arg):
                combobp_active_text = self.combobp.get_active_text()
                if not combobp_active_text:
                    return
                if combobp_active_text == _("Edit"):
                    self._edit_paper()
                elif combobp_active_text == _("Manual"):
                    for option in (
                        "tl-x",
                        "tl-y",
                        "br-x",
                        "br-y",
                        "page-height",
                        "page-width",
                    ):
                        if option in self._geometry_boxes:
                            self._geometry_boxes[option].show_all()

                    self.paper = None
                else:
                    self.paper = combobp_active_text

            self.combobp.connect("changed", do_paper_size_changed)

            # If the geometry is changed and we are not setting a profile,
            # unset the paper size,
            for option in ("tl-x", "tl-y", "br-x", "br-y", "page-height", "page-width"):
                if option in self.option_widgets:
                    widget = self.option_widgets[option]

                    def do_paper_dimension_changed(_data):
                        if not (
                            self.setting_current_scan_options or self.paper is None
                        ):
                            self.paper = None

                    widget.connect("changed", do_paper_dimension_changed)

    def _hide_geometry(self, _options):
        "hide geometry options"
        for option in ("tl-x", "tl-y", "br-x", "br-y", "page-height", "page-width"):
            if option in self._geometry_boxes:
                self._geometry_boxes[option].hide()

    def _get_paper_by_geometry(self):
        "return the paper size that matches the current geometry settings"
        formats = self.paper_formats
        if formats is None:
            return None
        options = self.available_scan_options
        current = {
            "l": options.val("tl-x", self.thread.device_handle),
            "t": options.val("tl-y", self.thread.device_handle),
        }
        current["x"] = current["l"] + options.val("br-x", self.thread.device_handle)
        current["y"] = current["t"] + options.val("br-y", self.thread.device_handle)
        for name, value in formats.items():
            match = True
            for edge in ["l", "t", "x", "y"]:
                if value[edge] != current[edge]:
                    match = False
                    break

            if match:
                return name
        return None

    def _update_options(self, new_options):
        """If setting an option triggers a reload, the widgets must be updated to reflect
        the new options"""
        logger.debug("Sane.get_option_descriptor() returned: %s", new_options)
        loops = self.num_reloads
        loops += 1
        self.num_reloads = loops  # num-reloads is read-only
        limit = self.reload_recursion_limit
        if self.num_reloads > limit:
            logger.error("reload-recursion-limit (%s) exceeded.", limit)
            self.emit(
                "process-error",
                "update_options",
                _(
                    "Reload recursion limit (%d) exceeded. Please file a bug, "
                    "attaching a log file reproducing the problem."
                )
                % (limit),
            )
            return

        # Clone the current scan options in case they are changed by the reload,
        # so that we can reapply it afterwards to ensure the same values are still
        # set.
        current_scan_options = copy(self.current_scan_options)

        # walk the widget tree and update them from the hash
        num_dev_options = new_options.num_options()
        options = self.available_scan_options
        for i in range(1, num_dev_options):
            if self._update_option(options.by_index(i), new_options.by_index(i)):
                return

        # This fires the reloaded-scan-options signal,
        # so don't set this until we have finished
        self.available_scan_options = new_options

        # Remove buttons from $current_scan_options to prevent buttons which cause
        # reloads from setting off infinite loops
        buttons = []
        for i in current_scan_options.each_backend_option():
            name, _val = current_scan_options.get_backend_option_by_index(i)
            opt = options.by_name(name)
            if opt.type == enums.TYPE_BUTTON:
                buttons.append(name)

        for button in buttons:
            current_scan_options.remove_backend_option_by_name(button)

        # Reapply current options to ensure the same values are still set.
        self._add_current_scan_options(current_scan_options)

        # In case the geometry values have changed,
        # update the available paper formats
        self._set_paper_formats(self.paper_formats)

    def _update_single_option(self, opt):
        widget = self.option_widgets[opt.name]
        if opt.type != enums.TYPE_BUTTON:
            value = getattr(self.thread.device_handle, opt.name.replace("-", "_"))

        # Switch
        if opt.type == enums.TYPE_BOOL:
            if _value_for_active_option(value, opt):
                widget.set_active(value)

        else:
            if isinstance(opt.constraint, tuple):
                step, page = widget.get_increments()
                step = 1
                if opt.constraint[2] > 0:
                    step = opt.constraint[2]

                widget.set_range(opt.constraint[0], opt.constraint[1])
                widget.set_increments(step, page)
                if _value_for_active_option(value, opt):
                    widget.set_value(value)

            elif isinstance(opt.constraint, list):
                widget.get_model().clear()
                index = 0
                for i, entry in enumerate(opt.constraint):
                    widget.append_text(d_sane(str(entry)))
                    if entry == value:
                        index = i

                if index is not None:
                    widget.set_active(index)

            elif opt.constraint is None and opt.type != enums.TYPE_BUTTON:  # entry
                if _value_for_active_option(value, opt):
                    widget.set_text(value)

    def _update_option(self, opt, new_opt):

        # could be undefined for !(new_opt.cap & SANE_CAP_SOFT_DETECT)
        # or where opt.name is not defined
        # e.g. opt.type == SANE_TYPE_GROUP
        if opt.type == enums.TYPE_GROUP or opt.name not in self.option_widgets:
            return False

        widget = self.option_widgets[opt.name]
        if new_opt.name != opt.name:
            logger.error(
                "Error updating options: reloaded options are numbered differently"
            )
            return True

        if opt.type != new_opt.type:
            logger.error(
                "Error updating options: reloaded options have different types"
            )
            return True

        # Block the signal handler for the widget to prevent infinite
        # loops of the widget updating the option, updating the widget, etc.
        widget.handler_block(widget.signal)
        opt = new_opt

        # HBox for option
        hbox = widget.get_parent()
        hbox.set_sensitive(
            (not opt.cap & enums.CAP_INACTIVE) and opt.cap & enums.CAP_SOFT_SELECT
        )

        # TODO: test options with multiple values in more detail
        if opt.size < 2:
            self._update_single_option(opt)

        widget.handler_unblock(widget.signal)
        return False

    def _set_paper_formats(self, formats):
        "Add paper size to combobox if scanner large enough"
        if self.combobp is not None:

            # Remove all formats, leaving Manual and Edit
            num = self.combobp.get_num_rows()
            while num > 2:
                num -= 1
                self.combobp.remove(0)
            self.ignored_paper_formats = []
            options = self.available_scan_options
            for fmt in formats:
                if options.supports_paper(formats[fmt], PAPER_TOLERANCE):
                    logger.debug("Options support paper size '%s'.", fmt)
                    self.combobp.prepend_text(fmt)

                else:
                    logger.debug("Options do not support paper size '%s'.", fmt)
                    self.ignored_paper_formats.append(fmt)

            # Set the combobox back from Edit to the previous value
            paper = self.paper
            if paper is None:
                paper = _("Manual")
            self.combobp.set_active_by_text(paper)

    def _set_paper(self, paper):
        """Treat a paper size as a profile, so build up the required profile of
        geometry settings and apply it"""
        if paper is None:
            self._paper = paper
            self.current_scan_options.remove_frontend_option("paper")
            self.emit("changed-paper", paper)
            return

        for name in self.ignored_paper_formats:
            if name == paper:
                if logger is not None:
                    logger.info("Ignoring unsupported paper %s", paper)
                return

        formats = self.paper_formats
        options = self.available_scan_options
        paper_profile = Profile()
        if (
            (options.by_name("page-height") is not None)
            and not options.by_name("page-height").cap & enums.CAP_INACTIVE
            and (options.by_name("page-width") is not None)
            and not options.by_name("page-width").cap & enums.CAP_INACTIVE
        ):
            paper_profile.add_backend_option(
                "page-height",
                formats[paper]["y"] + formats[paper]["t"],
                self.thread.device_handle.page_height,
            )
            paper_profile.add_backend_option(
                "page-width",
                formats[paper]["x"] + formats[paper]["l"],
                self.thread.device_handle.page_width,
            )

        paper_profile.add_backend_option(
            "tl-x", formats[paper]["l"], self.thread.device_handle.tl_x
        )
        paper_profile.add_backend_option(
            "tl-y", formats[paper]["t"], self.thread.device_handle.tl_y
        )
        paper_profile.add_backend_option(
            "br-x",
            formats[paper]["x"] + formats[paper]["l"],
            self.thread.device_handle.br_x,
        )
        paper_profile.add_backend_option(
            "br-y",
            formats[paper]["y"] + formats[paper]["t"],
            self.thread.device_handle.br_y,
        )

        # forget the previous option info calls, as these are only interesting
        # *whilst* setting a profile, and now we are starting from scratch
        self._option_info = {}
        if not paper_profile.num_backend_options():
            self._hide_geometry(options)
            self._paper = paper
            self.current_scan_options.add_frontend_option("paper", paper)
            self.emit("changed-paper", paper)
            return

        signal = None

        def do_changed_current_scan_options(_dialog, _profile, uuid):
            if paper_profile.uuid == uuid:
                self.disconnect(signal)
                self._hide_geometry(options)
                self._paper = paper
                self.current_scan_options.add_frontend_option("paper", paper)
                self.emit("changed-paper", paper)

        signal = self.connect(
            "changed-current-scan-options", do_changed_current_scan_options
        )

        # Don't trigger the changed-paper signal
        # until we have finished setting the profile
        self._add_current_scan_options(paper_profile)

    def _edit_paper(self):
        "Paper editor"
        combobp = self.combobp
        window = Dialog(
            transient_for=self,
            title=_("Edit paper size"),
        )
        vbox = window.get_content_area()

        hboxl = Gtk.Box()
        vbox.pack_start(hboxl, False, False, 0)
        vboxb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxl.pack_start(vboxb, False, False, 0)
        icon = Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        dbutton = Gtk.Button()
        dbutton.set_image(icon)
        vboxb.pack_start(dbutton, True, False, 0)
        icon = Gtk.Image.new_from_icon_name("list-remove", Gtk.IconSize.BUTTON)
        rbutton = Gtk.Button()
        rbutton.set_image(icon)
        vboxb.pack_end(rbutton, True, False, 0)

        slist = PaperList(self.paper_formats)
        dbutton.connect("clicked", slist.do_add_clicked)
        rbutton.connect("clicked", _remove_paper_callback, slist, window.parent)
        slist.get_model().connect("row-changed", slist.do_paper_sizes_row_changed)

        hboxl.pack_end(slist, False, False, 0)

        # Buttons
        hboxb = Gtk.Box()
        vbox.pack_start(hboxb, False, False, 0)
        abutton = Gtk.Button.new_with_label(_("Apply"))

        def do_apply_paper_sizes():
            formats = {}
            for row in slist.data:
                j = 0
                for _side in ["x", "y", "l", "t"]:
                    j += 1
                    formats[row[0]][_side] = row[j]

            # Add new definitions
            self.paper_formats = formats
            if self.ignored_paper_formats:
                main.show_message_dialog(
                    parent=window,
                    type="warning",
                    buttons="close",
                    text=_(
                        "The following paper sizes are too big to be scanned by"
                        " the selected device:"
                    )
                    + " "
                    + ", ".join(self.ignored_paper_formats),
                )

            window.destroy()

        abutton.connect("clicked", do_apply_paper_sizes)
        hboxb.pack_start(abutton, True, False, 0)
        cbutton = Gtk.Button.new_with_label(_("Cancel"))

        def do_cancel_paper_sizes():

            # Set the combobox back from Edit to the previous value
            combobp.set_active_by_text(self.paper)
            window.destroy()

        cbutton.connect("clicked", do_cancel_paper_sizes)
        hboxb.pack_end(cbutton, True, False, 0)
        window.show_all()

    def save_current_profile(self, name):
        "keeping this as a separate sub allows us to test it"
        self._add_profile(name, self.current_scan_options)

        # Block signal or else we fire another round of profile loads
        self.combobsp.handler_block(self.combobsp_changed_signal)
        self.combobsp.set_active(self.combobsp.get_num_rows() - 1)
        self.combobsp.handler_unblock(self.combobsp_changed_signal)
        self._profile = name

    def _add_profile(self, name, profile):
        "apply the given profile without resetting the current one"
        if name is None:
            logger.error("Cannot add profile with no name")
            return

        if profile is None:
            logger.error("Cannot add undefined profile")
            return

        if not isinstance(profile, Profile):
            logger.error("%s is not a Profile object", type(profile))
            return

        # if we don't clone the profile,
        # we get strange action-at-a-distance problems
        self.profiles[name] = copy(profile)
        self.combobsp.remove_item_by_text(name)
        self.combobsp.append_text(name)
        logger.debug("Saved profile '%s': %s", name, self.profiles[name])
        self.emit("added-profile", name, self.profiles[name])

    def set_option(self, option, value, uuid=None):
        "placeholder to be overrided by subclass"

    def scan_options(self, device=None):
        "placeholder to be overrided by subclass"

    def get_devices(self):
        "placeholder to be overrided by subclass"

    def scan(self):
        "placeholder to be overrided by subclass"

    def set_profile(self, name):
        "apply the give profile"
        if name is not None and name != "":

            # Only emit the changed-profile signal when the GUI has caught up
            signal = None

            def do_changed_current_scan_options(_1, _2, uuid_found):

                uuid = self.setting_profile[0]

                # there seems to be a race condition in t/0621_Dialog_Scan_CLI.t
                # where the uuid set below is not set in time to be tested in
                # this if.
                if uuid == uuid_found:
                    self.disconnect(signal)
                    self.setting_profile = []

                    # set property before emitting signal to ensure callbacks
                    # receive correct value
                    self._profile = name
                    self.emit("changed-profile", name)

            signal = self.connect(
                "changed-current-scan-options", do_changed_current_scan_options
            )

            # Add UUID to the stack and therefore don't unset the profile name
            self.setting_profile.append(self.profiles[name].uuid)
            self.set_current_scan_options(self.profiles[name])

        # no need to wait - nothing to do
        else:
            # set property before emitting signal to ensure callbacks
            # receive correct value
            self._profile = name
            self.emit("changed-profile", name)

    def _remove_profile(self, name):
        """Remove the profile. If it is active, deselect it first."""
        if (name is not None) and name in self.profiles:
            self.combobsp.remove_item_by_text(name)
            self.emit("removed-profile", name)
            del self.profiles[name]

    def set_current_scan_options(self, profile):
        "Set options to given profile"
        if profile is None:
            logger.error("Cannot add undefined profile")
            return

        if not isinstance(profile, Profile):
            logger.error("%s is not a Profile object", type(profile))
            return

        # forget the previous option info calls, as these are only interesting
        # *whilst* setting a profile, and now we are starting from scratch
        self._option_info = {}

        # If we have no options set, no need to reset to defaults
        if self.current_scan_options.num_backend_options() == 0:
            self._add_current_scan_options(profile)
            return

        # reload to get defaults before applying profile
        signal = None
        self.current_scan_options = copy(profile)

        def do_reloaded_scan_options(_widget):
            nonlocal signal
            self.disconnect(signal)
            self._add_current_scan_options(profile)

        signal = self.connect("reloaded-scan-options", do_reloaded_scan_options)
        self.scan_options(self.device)

    def _add_current_scan_options(self, profile):
        "Apply options referenced by hashref without resetting existing options"
        if profile is None:
            logger.error("Cannot add undefined profile")
            return

        if not isinstance(profile, Profile):
            logger.error("%s is not a Profile object", type(profile))
            return

        # First clone the profile, as otherwise it would be self-modifying
        clone = copy(profile)
        self.setting_current_scan_options.append(clone.uuid)

        # Give the GUI a chance to catch up between settings,
        # in case they have to be reloaded.
        # Use the callback to trigger the next loop
        self._set_option_profile(clone, profile.each_backend_option())

    def _set_option_profile(self, profile, itr):
        self.cursor = "wait"
        try:
            i = next(itr)
            name, val = profile.get_backend_option_by_index(i)
            options = self.available_scan_options
            opt = options.by_name(name)
            if opt is None or opt.cap & enums.CAP_INACTIVE:
                logger.warning("Ignoring inactive option '%s'.", name)
                self._set_option_profile(profile, itr)
                return

            # if we have a profile from a pre-v3 gscan2pdf config, the types
            # are likely wrong, so force the conversion
            if opt.type == enums.TYPE_INT:
                val = int(val)
            elif opt.type == enums.TYPE_FIXED:
                val = float(val)
            elif opt.type == enums.TYPE_BOOL:
                val = bool(val)

            # Don't try to set invalid option
            if isinstance(opt.constraint, list):
                if val not in opt.constraint:
                    logger.warning(
                        "Ignoring invalid argument '%s' for option '%s'.", val, name
                    )
                    self._set_option_profile(profile, itr)
                    return

            # Ignore option if info from previous set_option() reported SANE_INFO_INEXACT
            if (
                opt.name in self._option_info
                and self._option_info[opt.name] & enums.INFO_INEXACT
            ):
                logger.warning(
                    "Skip setting option '%s' to '%s', as previous call"
                    " set SANE_INFO_INEXACT",
                    name,
                    val,
                )
                self._set_option_profile(profile, itr)
                return

            # Ignore option if value already within tolerance
            curval = getattr(self.thread.device_handle, opt.name.replace("-", "_"))
            if within_tolerance(opt, curval, val, OPTION_TOLERANCE):
                logger.info(
                    "No need to set option '%s': already within tolerance.", name
                )
                self._set_option_profile(profile, itr)
                return

            logger.debug(
                f"Setting option '{name}'"
                + (
                    ""
                    if opt.type == enums.TYPE_BUTTON
                    else f" from '{curval}' to '{val}'."
                )
            )
            signal = None

            def do_changed_scan_option(_widget, _optname, _optval, uuid):

                # With multiple reloads, this can get called several times,
                # so only react to signal from the correct profile
                if uuid == profile.uuid:
                    self.disconnect(signal)
                    self._set_option_profile(profile, itr)

            signal = self.connect("changed-scan-option", do_changed_scan_option)

            self.set_option(opt, val, profile.uuid)

        except StopIteration:

            # Having set all backend options, set the frontend options
            # Set paper formats first to make sure that any paper required is
            # available
            self._set_paper_formats(self.paper_formats)
            for key in profile.each_frontend_option():
                setattr(self, key, profile.get_frontend_option(key))

            if not self.setting_profile:
                self.profile = None

            if self.setting_current_scan_options:
                self.setting_current_scan_options.pop()
            self.emit(
                "changed-current-scan-options",
                self.current_scan_options,
                profile.uuid,
            )
            self.cursor = "default"

    def _update_widget_value(self, opt, val):
        "update widget with value"
        if opt.name in self.option_widgets:
            widget = self.option_widgets[opt.name]
            logger.debug(
                f"Setting widget '{opt.name}'"
                + ("" if opt.type == enums.TYPE_BUTTON else f" to '{val}'.")
            )
            widget.handler_block(widget.signal)
            if isinstance(widget, (Gtk.CheckButton, Gtk.Switch)):
                if val == "":
                    val = 0
                if widget.get_active() != val:
                    widget.set_active(val)

            elif isinstance(widget, Gtk.SpinButton):
                if widget.get_value() != val:
                    widget.set_value(val)

            elif isinstance(widget, Gtk.ComboBox):
                if opt.constraint[widget.get_active()] != val:
                    index = opt.constraint.index(val)
                    if index > NO_INDEX:
                        widget.set_active(index)

            elif isinstance(widget, Gtk.Entry):
                if widget.get_text() != val:
                    widget.set_text(val)

            widget.handler_unblock(widget.signal)

        else:
            logger.warning("Widget for option '%s' undefined.", opt.name)

    def _get_xy_resolution(self):
        "return x and y values for resolution"
        options = self.available_scan_options
        if not options:
            return None, None
        resolutions = []
        for name in ["resolution", "x-resolution", "y-resolution"]:
            try:
                resolutions.append(options.val(name, self.thread.device_handle))
            except AttributeError:
                resolutions.append(0)
        resolution, xres, yres = resolutions

        # Potentially, a scanner could offer all three options, but then unset
        # resolution once the other two have been set.
        if resolution:

            # The resolution option, plus one of the other two, is defined.
            # Most sensibly, we should look at the order they were set.
            # However, if none of them are in current-scan-options, they still have
            # their default setting, and which of those gets priority is certainly
            # scanner specific.
            if xres == 0 and yres == 0:
                return resolution, resolution
            current_scan_options = self.current_scan_options
            for i in current_scan_options.each_backend_option():
                name, val = current_scan_options.get_backend_option_by_index(i)
                if name == "resolution":
                    xres = val
                    yres = val
                elif name == "x-resolution":
                    xres = val
                elif name == "y-resolution":
                    yres = val

        if xres == 0:
            xres = POINTS_PER_INCH
        if yres == 0:
            yres = POINTS_PER_INCH
        return xres, yres

    def _get_label_for_option(self, name):
        "return the label text of the option"
        widget = self.option_widgets[name]
        hbox = widget.get_parent()
        for child in hbox.get_children():
            if isinstance(child, Gtk.Label):
                return child.get_text()
        return None

    def _changed_scan_option_callback(self, _dialog, name, value, _uuid, bscannum):
        options = self.available_scan_options
        opt = options.by_name("source")
        if opt is not None and name == opt.name:
            if self.allow_batch_flatbed or not options.flatbed_selected(
                self.thread.device_handle
            ):
                self.framen.set_sensitive(True)
            else:
                bscannum.set_active(True)
                self.num_pages = 1
                self.sided = "single"
                self.framen.set_sensitive(False)

            if self.adf_defaults_scan_all_pages and re.search(
                r"(ADF|Automatic[ ]Document[ ]Feeder)",
                value,
                re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                self.num_pages = 0

        self._flatbed_or_duplex_callback()


def _remove_paper_callback(slist, _window):
    if slist.data:
        slist.do_remove_clicked()
    # else:
    #     main.show_message_dialog(
    #         parent=window,
    #         type="error",
    #         buttons="close",
    #         text=_("Cannot delete all paper sizes"),
    #     )


def _geometry_option(opt):
    "Return true if we have a valid geometry option"
    return (
        opt.type in [enums.TYPE_FIXED, enums.TYPE_INT]
        and opt.unit in [enums.UNIT_MM, enums.UNIT_PIXEL]
        and opt.name in ["tl-x", "tl-y", "br-x", "br-y", "page-height", "page-width"]
    )


def _value_for_active_option(value, opt):
    "return if the value is defined and the option is active"
    return not value and not opt.cap & enums.CAP_INACTIVE


def _save_profile_callback(_widget, parent):
    dialog = Gtk.Dialog(
        _("Name of scan profile"),
        parent=parent,
        destroy_with_parent=True,
    )
    dialog.add_buttons(
        Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
    )
    hbox = Gtk.Box()
    label = Gtk.Label(label=_("Name of scan profile"))
    hbox.pack_start(label, False, False, 0)
    entry = Gtk.Entry()
    entry.set_activates_default(True)
    hbox.pack_end(entry, True, True, 0)
    dialog.get_content_area().add(hbox)
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.show_all()
    flag = True
    while flag:
        if dialog.run() == Gtk.ResponseType.OK:
            name = entry.get_text()
            if not re.search(r"^\s*$", name, re.MULTILINE | re.DOTALL | re.VERBOSE):
                if name in parent.profiles:
                    warning = _("Profile '%s' exists. Overwrite?") % (name)
                    dialog2 = Gtk.Dialog(
                        title=warning,
                        transient_for=dialog,
                        destroy_with_parent=True,
                    )
                    dialog2.add_buttons(
                        _("OK"),
                        Gtk.ResponseType.OK,
                        _("Cancel"),
                        Gtk.ResponseType.CANCEL,
                    )
                    label = Gtk.Label(label=warning)
                    dialog2.get_content_area().add(label)
                    label.show()
                    if dialog2.run() == Gtk.ResponseType.OK:
                        parent.save_current_profile(entry.get_text())
                        flag = False

                    dialog2.destroy()

                else:
                    parent.save_current_profile(entry.get_text())
                    flag = False

        else:
            flag = False

    dialog.destroy()


def _edit_profile_callback(_widget, parent):

    name = parent.profile
    msg, profile = None, None
    if name is None or name == "":
        msg = _("Editing current scan options")
        profile = parent.current_scan_options

    else:
        msg = _('Editing scan profile "%s"') % (name)
        profile = parent.profiles[name]

    dialog = Gtk.Dialog(
        title=msg,
        transient_for=parent,
        destroy_with_parent=True,
    )
    dialog.add_buttons(
        _("OK"), Gtk.ResponseType.OK, _("Cancel"), Gtk.ResponseType.CANCEL
    )
    label = Gtk.Label(label=msg)
    dialog.get_content_area().pack_start(label, True, True, 0)

    # Clone so that we can cancel the changes, if necessary
    profile = copy(profile)
    _build_profile_table(
        profile, parent.available_scan_options, dialog.get_content_area()
    )
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.show_all()

    # save the profile and reload
    if dialog.run() == Gtk.ResponseType.OK:
        if (name is None) or name == "":
            parent.set_current_scan_options(profile)

        else:
            parent.profiles[name] = profile

            # unset profile to allow us to set it again on reload
            parent.profile = None

            # emit signal to update settings
            parent.emit("added-profile", name, parent.profiles[name])
            signal = None

            def do_parent_reloaded_scan_options(_widget):
                parent.disconnect(signal)
                parent.set_profile(name)

            signal = parent.connect(
                "reloaded-scan-options", do_parent_reloaded_scan_options
            )
            parent.scan_options(parent.device)

    dialog.destroy()


def do_delete_profile_backend_item(data):
    "callback for delete profile button click"
    profile, options, vbox, frameb, framef, name, i = data
    logger.debug("removing option '%s' from profile", name)
    profile.remove_backend_option_by_index(i)
    frameb.destroy()
    framef.destroy()
    _build_profile_table(profile, options, vbox)


def _build_profile_table(profile, options, vbox):

    frameb = Gtk.Frame(label=_("Backend options"))
    framef = Gtk.Frame(label=_("Frontend options"))
    vbox.pack_start(frameb, True, True, 0)
    vbox.pack_start(framef, True, True, 0)

    # listbox to align widgets
    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.NONE)
    frameb.add(listbox)
    for i in profile.each_backend_option():
        name, _val = profile.get_backend_option_by_index(i)
        opt = options.by_name(name)
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box()
        label = Gtk.Label(label=d_sane(opt.title))
        hbox.pack_start(label, False, True, 0)
        icon = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON)
        button = Gtk.Button()
        button.set_image(icon)
        hbox.pack_end(button, False, False, 0)

        button.connect(
            "clicked",
            do_delete_profile_backend_item,
            [profile, options, vbox, frameb, framef, name, i],
        )
        row.add(hbox)
        listbox.add(row)

    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.NONE)
    framef.add(listbox)

    for name in profile.each_frontend_option():
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box()
        label = Gtk.Label(label=name)
        hbox.pack_start(label, False, True, 0)
        icon = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON)
        button = Gtk.Button()
        button.set_image(icon)
        hbox.pack_end(button, False, False, 0)

        def do_delete_profile_frontend_item(_name):
            logger.debug("removing option '%s' from profile", _name)
            profile.remove_frontend_option(_name)
            frameb.destroy()
            framef.destroy()
            _build_profile_table(profile, options, vbox)

        button.connect("clicked", do_delete_profile_frontend_item, name)
        row.add(hbox)
        listbox.add(row)

    vbox.show_all()


def _new_val(oldval, newval):
    return ((newval is not None) and (oldval is not None) and newval != oldval) or (
        (newval is not None) ^ (oldval is not None)
    )


def make_progress_string(i, num_pages):
    "return a progress string"
    if num_pages > 0:
        return _("Scanning page %d of %d") % (i, num_pages)
    return _("Scanning page %d") % (i)

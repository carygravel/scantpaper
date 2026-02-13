"provide methods called from scan menu item"

import re
import os
import logging
from types import SimpleNamespace
import gi
from comboboxtext import ComboBoxText
from const import EMPTY
from dialog import Dialog
from dialog.sane import SaneScanDialog
from i18n import _
from postprocess_controls import RotateControls, OCRControls
from scanner.profile import Profile

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


class ScanMenuItemMixins:
    "provide methods called from scan menu item"

    def scan_dialog(self, _action, _param, hidden=False, scan=False):
        "Scan"
        if self._windows:
            self._windows.show_all()
            self._update_postprocessing_options_callback(self._windows)
            return

        # If device not set by config and there is a default device, then set it
        if "device" not in self.settings and "SANE_DEFAULT_DEVICE" in os.environ:
            self.settings["device"] = os.environ["SANE_DEFAULT_DEVICE"]

        # scan dialog
        kwargs = {
            "transient_for": self,
            "title": _("Scan Document"),
            "dir": self.session,
            "hide_on_delete": True,
            "paper_formats": self.settings["Paper"],
            "allow_batch_flatbed": self.settings["allow-batch-flatbed"],
            "adf_defaults_scan_all_pages": self.settings["adf-defaults-scan-all-pages"],
            "document": self.slist,
            "ignore_duplex_capabilities": self.settings["ignore-duplex-capabilities"],
            "cycle_sane_handle": self.settings["cycle sane handle"],
            "cancel_between_pages": (
                self.settings["allow-batch-flatbed"]
                and self.settings["cancel-between-pages"]
            ),
            "profiles": self.settings["profile"],
        }
        if self.settings["scan_window_width"]:
            kwargs["default_width"] = self.settings["scan_window_width"]
        if self.settings["scan_window_height"]:
            kwargs["default_height"] = self.settings["scan_window_height"]
        self._windows = SaneScanDialog(**kwargs)

        # Can't set the device when creating the window,
        # as the list does not exist then
        self._windows.connect("changed-device-list", self._changed_device_list_callback)

        # Update default device
        self._windows.connect("changed-device", self._changed_device_callback)
        self._windows.connect(
            "changed-page-number-increment",
            self._update_postprocessing_options_callback,
        )
        self._windows.connect(
            "changed-side-to-scan", self._changed_side_to_scan_callback
        )
        signal = None

        def started_progress_callback(_widget, message):
            logger.debug("'started-process' emitted with message: %s", message)
            self._scan_progress.set_fraction(0)
            self._scan_progress.set_text(message)
            self._scan_progress.show_all()
            nonlocal signal
            signal = self._scan_progress.connect("clicked", self._windows.cancel_scan)

        self._windows.connect("started-process", started_progress_callback)
        self._windows.connect("changed-progress", self._changed_progress_callback)
        self._windows.connect("finished-process", self._finished_process_callback)
        self._windows.connect("process-error", self._process_error_callback, signal)
        self._windows.connect("changed-profile", self._changed_profile_callback)
        self._windows.connect("added-profile", self._added_profile_callback)

        def removed_profile_callback(_widget, profile):
            del self.settings["profile"][profile]

        self._windows.connect("removed-profile", removed_profile_callback)

        def changed_current_scan_options_callback(_widget, profile, _uuid):
            "Update the default profile when the scan options change"
            self.settings["default-scan-options"] = profile.get()

        self._windows.connect(
            "changed-current-scan-options", changed_current_scan_options_callback
        )

        def changed_paper_formats_callback(_widget, formats):
            self.settings["Paper"] = formats

        self._windows.connect("changed-paper-formats", changed_paper_formats_callback)
        self._windows.connect("new-scan", self._new_scan_callback)
        self._windows.connect(
            "changed-scan-option", self._update_postprocessing_options_callback
        )
        self.add_postprocessing_options(self._windows)
        if not hidden:
            self._windows.show_all()
        self._update_postprocessing_options_callback(self._windows)
        args = self.get_application().args
        if args.device:
            device_list = []
            for d in args.device:
                device_list.append(SimpleNamespace(name=d, label=d))

            self._windows.device_list = device_list

        elif (
            not scan
            and self.settings["cache-device-list"]
            and len(self.settings["device list"])
        ):
            self._windows.device_list = self.settings["device list"]
        else:
            self._windows.get_devices()

    def add_postprocessing_options(self, widget):
        "Adds post-processing options to the dialog window."
        scwin = Gtk.ScrolledWindow()
        widget.notebook.append_page(scwin, Gtk.Label(label=_("Postprocessing")))
        scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vboxp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxp.set_border_width(widget.get_border_width())
        scwin.add(vboxp)

        # Rotate
        self._rotate_controls = RotateControls(
            rotate_facing=self.settings["rotate facing"],
            rotate_reverse=self.settings["rotate reverse"],
        )
        vboxp.pack_start(self._rotate_controls, False, False, 0)

        # CheckButton for unpaper
        ubutton = self._add_postprocessing_unpaper(vboxp)

        # CheckButton for user-defined tool
        udtbutton, self._scan_udt_cmbx = self._add_postprocessing_udt(vboxp)
        ocr_controls = OCRControls(
            available_engines=self._ocr_engine,
            engine=self.settings["ocr engine"],
            language=self.settings["ocr language"],
            active=self.settings["OCR on scan"],
            threshold=self.settings["threshold-before-ocr"],
            threshold_value=self.settings["threshold tool"],
        )
        vboxp.pack_start(ocr_controls, False, False, 0)

        def clicked_scan_button_cb(_w):
            self.settings["rotate facing"] = self._rotate_controls.rotate_facing
            self.settings["rotate reverse"] = self._rotate_controls.rotate_reverse
            logger.info("rotate facing %s", self.settings["rotate facing"])
            logger.info("rotate reverse %s", self.settings["rotate reverse"])
            self.settings["unpaper on scan"] = ubutton.get_active()
            logger.info("unpaper %s", self.settings["unpaper on scan"])
            self.settings["udt_on_scan"] = udtbutton.get_active()
            self.settings["current_udt"] = self._scan_udt_cmbx.get_active_text()
            logger.info("UDT %s", self.settings["udt_on_scan"])
            if "current_udt" in self.settings:
                logger.info("Current UDT %s", self.settings["current_udt"])

            self.settings["OCR on scan"] = ocr_controls.active
            logger.info("OCR %s", self.settings["OCR on scan"])
            if self.settings["OCR on scan"]:
                self.settings["ocr engine"] = ocr_controls.engine
                if self.settings["ocr engine"] is None:
                    self.settings["ocr engine"] = self._ocr_engine[0][0]
                logger.info("ocr engine %s", self.settings["ocr engine"])
                if self.settings["ocr engine"] == "tesseract":
                    self.settings["ocr language"] = ocr_controls.language
                    logger.info("ocr language %s", self.settings["ocr language"])

                self.settings["threshold-before-ocr"] = ocr_controls.threshold
                logger.info(
                    "threshold-before-ocr %s", self.settings["threshold-before-ocr"]
                )
                self.settings["threshold tool"] = ocr_controls.threshold_value

        widget.connect("clicked-scan-button", clicked_scan_button_cb)
        # self->{notebook}->get_nth_page(1)->show_all;

    def _add_postprocessing_unpaper(self, vboxp):
        hboxu = Gtk.Box()
        vboxp.pack_start(hboxu, False, False, 0)
        ubutton = Gtk.CheckButton(label=_("Clean up images"))
        ubutton.set_tooltip_text(_("Clean up scanned images with unpaper"))
        hboxu.pack_start(ubutton, True, True, 0)
        if not self._dependencies["unpaper"]:
            ubutton.set_sensitive(False)
            ubutton.set_active(False)
        elif self.settings["unpaper on scan"]:
            ubutton.set_active(True)

        button = Gtk.Button(label=_("Options"))
        button.set_tooltip_text(_("Set unpaper options"))
        hboxu.pack_end(button, True, True, 0)
        button.connect("clicked", self._show_unpaper_options)
        return ubutton

    def _show_unpaper_options(self, _button):
        windowuo = Dialog(
            transient_for=self,
            title=_("unpaper options"),
        )
        self._unpaper.add_options(windowuo.get_content_area())

        def unpaper_options_callback():
            self.settings["unpaper options"] = self._unpaper.get_options()
            windowuo.destroy()

        windowuo.add_actions(
            [
                ("gtk-ok", unpaper_options_callback),
                ("gtk-cancel", windowuo.destroy),
            ]
        )
        windowuo.show_all()

    def _add_postprocessing_udt(self, vboxp):
        "Adds a user-defined tool (UDT) post-processing option to the given VBox."
        hboxudt = Gtk.Box()
        vboxp.pack_start(hboxudt, False, False, 0)
        udtbutton = Gtk.CheckButton(label=_("Process with user-defined tool"))
        udtbutton.set_tooltip_text(_("Process scanned images with user-defined tool"))
        hboxudt.pack_start(udtbutton, True, True, 0)
        if not self.settings["user_defined_tools"]:
            hboxudt.set_sensitive(False)
            udtbutton.set_active(False)

        elif self.settings["udt_on_scan"]:
            udtbutton.set_active(True)

        return udtbutton, self._add_udt_combobox(hboxudt)

    def _add_udt_combobox(self, hbox):
        "Adds a ComboBoxText widget to the given hbox containing user-defined tools."
        toolarray = []
        for t in self.settings["user_defined_tools"]:
            toolarray.append([t, t])

        combobox = ComboBoxText(data=toolarray)
        combobox.set_active_index(self.settings["current_udt"])
        hbox.pack_start(combobox, True, True, 0)
        return combobox

    def _changed_device_callback(self, widget, device):
        "callback for changed device"
        # widget is windows
        logger.info("signal 'changed-device' emitted with data: '%s'", device)
        if device is not None:
            self.settings["device"] = device

            # Can't set the profile until the options have been loaded. This
            # should only be called the first time after loading the available
            # options
            widget.reloaded_signal = widget.connect(
                "reloaded-scan-options", self._reloaded_scan_options_callback
            )

    def _changed_device_list_callback(self, widget, device_list):  # widget is windows
        "callback for changed device list"
        logger.info("signal 'changed-device-list' emitted with data: %s", device_list)
        if len(device_list):

            # Apply the device blacklist
            if "device blacklist" in self.settings and self.settings[
                "device blacklist"
            ] not in [
                None,
                "",
            ]:
                initial_len = len(device_list)
                i = 0
                while i < len(device_list):
                    if re.search(
                        device_list[i].name,
                        self.settings["device blacklist"],
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        logger.info("Blacklisting device %s", device_list[i].name)
                        del device_list[i]
                    else:
                        i += 1

                if len(device_list) < initial_len:
                    widget.device_list = device_list

            if self.settings["cache-device-list"]:
                self.settings["device list"] = device_list

            # Only set default device if it hasn't been specified on the command line
            # and it is in the the device list
            if "device" in self.settings:
                for d in device_list:
                    if self.settings["device"] == d.name:
                        widget.device = self.settings["device"]
                        return

            widget.device = device_list[0].name

        else:
            self._windows = None

    def _changed_side_to_scan_callback(self, widget, _arg):
        "Callback function to handle the event when the side to scan is changed."
        logger.debug("changed_side_to_scan_callback( %s, %s )", widget, _arg)
        if len(self.slist.data) > 0:
            widget.page_number_start = self.slist.data[len(self.slist.data) - 1][0] + 1
        else:
            widget.page_number_start = 1

    def _update_postprocessing_options_callback(
        self, widget, _option_name=None, _option_val=None, _uuid=None
    ):
        "update the visibility of post-processing options based on the widget's scan options."
        # widget is windows
        options = widget.available_scan_options
        increment = widget.page_number_increment
        if options is not None:
            if increment != 1 or options.can_duplex():
                self._rotate_controls.can_duplex = True
            else:
                self._rotate_controls.can_duplex = False

    def _changed_progress_callback(self, _widget, progress, message):
        "Updates the progress bar based on the given progress value and message."
        if progress is not None and (0 <= progress <= 1):
            self._scan_progress.set_fraction(progress)
        else:
            self._scan_progress.pulse()
        if message is not None:
            self._scan_progress.set_text(message)

    def _changed_profile_callback(self, _widget, profile):
        self.settings["default profile"] = profile

    def _added_profile_callback(self, _widget, name, profile):
        self.settings["profile"][name] = profile.get()

    def _new_scan_callback(
        self, _widget, image_object, page_number, xresolution, yresolution
    ):
        "Callback function to handle a new scan."
        if image_object is None:
            return

        rotate = (
            self.settings["rotate facing"]
            if page_number % 2
            else self.settings["rotate reverse"]
        )
        options = {
            "page": page_number,
            "dir": self.session.name,
            "rotate": rotate,
            "ocr": self.settings["OCR on scan"],
            "engine": self.settings["ocr engine"],
            "language": self.settings["ocr language"],
            "queued_callback": self.post_process_progress.queued,
            "started_callback": self.post_process_progress.update,
            "finished_callback": self._import_scan_finished_callback,
            "error_callback": self._error_callback,
            "image_object": image_object,
            "resolution": (xresolution, yresolution, "PixelsPerInch"),
        }
        if self.settings["unpaper on scan"]:
            options["unpaper"] = self._unpaper

        if self.settings["threshold-before-ocr"]:
            options["threshold"] = self.settings["threshold tool"]

        if self.settings["udt_on_scan"]:
            options["udt"] = self.settings["current_udt"]

        logger.info("Importing scan with resolution=%s,%s", xresolution, yresolution)
        self.slist.import_scan(**options)

    def _reloaded_scan_options_callback(self, widget):  # widget is windows
        "This should only be called the first time after loading the available options"
        widget.disconnect(widget.reloaded_signal)
        profiles = self.settings["profile"].keys()
        if (
            "default profile" in self.settings
            and self.settings["default profile"] is not None
        ):
            widget.profile = self.settings["default profile"]

        elif "default-scan-options" in self.settings:
            widget.set_current_scan_options(
                Profile(self.settings["default-scan-options"])
            )

        elif profiles:
            widget.profile = list(profiles)[0]

        self._update_postprocessing_options_callback(widget)

    def _import_scan_finished_callback(self, response):
        "Callback function to handle the completion of a scan import process."
        self.post_process_progress.finish(response)

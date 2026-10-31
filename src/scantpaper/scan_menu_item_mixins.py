"""provide methods called from scan menu item."""

from __future__ import annotations

import logging
import os
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.comboboxtext import ComboBoxText
from scantpaper.const import DIALOG_ROW_SPACING
from scantpaper.dialog import Dialog
from scantpaper.dialog.sane import SaneScanDialog
from scantpaper.helpers import run_dialog, set_margins
from scantpaper.i18n import _
from scantpaper.postprocess_controls import OCRControls, RotateControls
from scantpaper.scanner.profile import Profile

if TYPE_CHECKING:
    from gi.repository import Gio, GLib

    from scantpaper.basethread import Response
    from scantpaper.scanner.options import Options

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

logger = logging.getLogger(__name__)


def _apply_device_blacklist(
    device_list: list[object], settings: dict[str, object], widget: SaneScanDialog
) -> None:
    """Remove blacklisted device names from the list in place."""
    if "device blacklist" not in settings or settings["device blacklist"] in [None, ""]:
        return
    initial_len = len(device_list)
    i = 0
    while i < len(device_list):
        if re.search(
            str(device_list[i].name),
            str(settings["device blacklist"]),
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        ):
            logger.info("Blacklisting device %s", device_list[i].name)
            del device_list[i]
        else:
            i += 1

    if len(device_list) < initial_len:
        widget.device_list = device_list


def _confirm_libusb_caching(
    parent: Gtk.Widget, device_list: list[object], settings: dict[str, object]
) -> bool:
    """Return whether the cached device list should be stored.

    Warn when libusb devices are present and let the user choose; a decline
    disables caching.
    """
    if not any("libusb" in d.name for d in device_list):
        return True
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        destroy_with_parent=True,
        modal=True,
        message_type="question",
        buttons=Gtk.ButtonsType.OK,
    )
    dialog.set_title(_("Really cache libusb device names?"))
    area = dialog.get_message_area()
    label = Gtk.Label(
        label=_(
            "Caching device list with libusb devices included is not recommended as they can change between reboots."
        )
        + _("Are you sure you want to do this?")
    )
    area.append(label)
    response = run_dialog(dialog)
    dialog.destroy()
    if response == Gtk.ResponseType.OK:
        return True
    settings["cache-device-list"] = False
    return False


class ScanMenuItemMixins:
    """provide methods called from scan menu item."""

    _scan_progress_cancel_signal: int | None = None

    def scan_dialog(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant | None,
        *,
        hidden: bool = False,
        scan: bool = False,
    ) -> None:
        """Scan."""
        if self._windows is not None:
            self._windows.present()
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
            "paper_sizes": self.settings["Paper"],
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

        self._connect_scan_dialog_signals(self._windows)
        self.add_postprocessing_options(self._windows)
        if not hidden:
            self._windows.present()
        self._update_postprocessing_options_callback(self._windows)
        args = self.get_application().args
        if args.device:
            device_list = [SimpleNamespace(name=d, label=d) for d in args.device]

            self._windows.device_list = device_list

        elif (
            not scan
            and self.settings["cache-device-list"]
            and len(self.settings["device list"])
        ):
            self._windows.device_list = self.settings["device list"]
        else:
            self._windows.get_devices()

    def _connect_scan_dialog_signals(self, window: SaneScanDialog) -> None:
        """Wire up all the SaneScanDialog signals."""
        # Can't set the device when creating the window,
        # as the list does not exist then
        window.connect("changed-device-list", self._changed_device_list_callback)

        # Update default device
        window.connect("changed-device", self._changed_device_callback)

        def started_progress_callback(_widget: Gtk.Widget, message: str) -> None:
            logger.debug("'started-process' emitted with message: %s", message)
            self._scan_progress.set_fraction(0)
            self._scan_progress.set_text(message)
            self._scan_progress.show()

        window.connect("started-process", started_progress_callback)
        window.connect("changed-progress", self._changed_progress_callback)
        window.connect("finished-process", self._finished_process_callback)

        def do_process_error(_widget: Gtk.Widget, process: str, msg: str) -> None:
            self._process_error_callback(_widget, process, msg, None)

        window.connect("process-error", do_process_error)
        window.connect("changed-profile", self._changed_profile_callback)
        window.connect("added-profile", self._added_profile_callback)
        self._connect_scan_progress_cancel(window)

        def removed_profile_callback(_widget: Gtk.Widget, profile: str) -> None:
            del self.settings["profile"][profile]

        window.connect("removed-profile", removed_profile_callback)

        def changed_current_scan_options_callback(
            _widget: Gtk.Widget, profile: Profile, _uuid: str
        ) -> None:
            """Update the default profile when the scan options change."""
            self.settings["default-scan-options"] = profile.get()

        window.connect(
            "changed-current-scan-options", changed_current_scan_options_callback
        )

        def changed_paper_sizes_callback(
            _widget: Gtk.Widget, formats: dict[str, object]
        ) -> None:
            self.settings["Paper"] = formats

        window.connect("changed-paper-sizes", changed_paper_sizes_callback)
        window.connect("new-scan", self._new_scan_callback)
        window.connect(
            "changed-scan-option", self._update_postprocessing_options_callback
        )
        window.connect(
            "changed-num-pages", self._update_postprocessing_options_callback
        )

    def _connect_scan_progress_cancel(self, window: SaneScanDialog) -> None:
        """Connect the progress-bar Cancel once per scan dialog."""
        if self._scan_progress_cancel_signal is not None:
            self._scan_progress.disconnect(self._scan_progress_cancel_signal)
        self._scan_progress_cancel_signal = self._scan_progress.connect(
            "clicked", window.cancel_scan
        )

    def add_postprocessing_options(self, widget: SaneScanDialog) -> None:
        """Add post-processing options to the dialog window."""
        scwin = Gtk.ScrolledWindow()
        widget.notebook.append_page(scwin, Gtk.Label(label=_("Postprocessing")))
        scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vboxp = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=DIALOG_ROW_SPACING,
            valign=Gtk.Align.START,
        )
        set_margins(vboxp, 0)
        scwin.set_child(vboxp)

        # Rotate
        self._rotate_controls = RotateControls(
            rotate_facing=self.settings["rotate facing"],
            rotate_reverse=self.settings["rotate reverse"],
        )
        vboxp.append(self._rotate_controls)

        # CheckButton for alternating rotation
        abutton = self._add_alternate_rotation_toggle(vboxp)
        self._alternate_rotation_button = abutton

        # CheckButton for unpaper
        ubutton = self._add_postprocessing_unpaper(vboxp)

        # CheckButton for user-defined tool
        udtbutton, self._scan_udt_cmbx = self._add_postprocessing_udt(vboxp)
        ocr_controls = OCRControls(
            available_engines=self._ocr_engine,
            engine=self.settings["ocr engine"],
            language=self.settings["ocr language"],
            variables=self.settings.get("tesseract variables", ""),
            psm=self.settings.get("ocr psm", ""),
            engine_mode=self.settings.get("ocr engine mode"),
            tessdata_dir=self.settings.get("tessdata directory", ""),
            active=self.settings["OCR on scan"],
            threshold=self.settings["threshold-before-ocr"],
            threshold_value=self.settings["threshold tool"],
        )
        vboxp.append(ocr_controls)

        def clicked_scan_button_cb(_w: Gtk.Widget) -> None:
            # Reset the transient per-batch OCR skip flag before each Scan click.
            self._skip_ocr_batch = False
            self.settings["rotate facing"] = self._rotate_controls.rotate_facing
            self.settings["rotate reverse"] = self._rotate_controls.rotate_reverse
            logger.info("rotate facing %s", self.settings["rotate facing"])
            logger.info("rotate reverse %s", self.settings["rotate reverse"])
            self.settings["alternate rotation"] = abutton.get_active()
            logger.info("alternate rotation %s", self.settings["alternate rotation"])
            # Reset parity only for multi-page batches at job start; manual mode
            # keeps parity stateful across scans
            windows = self._windows
            if (
                windows is not None
                and isinstance(cast("object", windows.allow_batch_flatbed), bool)
                and windows.allow_batch_flatbed
            ):
                num_pages = cast("object", windows.num_pages)
                if isinstance(num_pages, int) and num_pages > 1:
                    self._alternate_flatbed_count = 0
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
                self._store_scan_ocr_options(ocr_controls)
                self.settings["threshold-before-ocr"] = ocr_controls.threshold
                logger.info(
                    "threshold-before-ocr %s", self.settings["threshold-before-ocr"]
                )
                self.settings["threshold tool"] = ocr_controls.threshold_value

        widget.connect("clicked-scan-button", clicked_scan_button_cb)

    def _store_scan_ocr_options(self, ocr_controls: OCRControls) -> None:
        """Persist OCR settings and set the per-batch skip flag on error."""
        self.settings["ocr engine"] = ocr_controls.engine
        if self.settings["ocr engine"] is None:
            self.settings["ocr engine"] = self._ocr_engine[0][0]
        logger.info("ocr engine %s", self.settings["ocr engine"])
        if self.settings["ocr engine"] != "tesseract":
            return
        self.settings["ocr language"] = ocr_controls.language
        self.settings["tesseract variables"] = ocr_controls.variables
        self.settings["ocr psm"] = ocr_controls.psm
        self.settings["ocr engine mode"] = ocr_controls.engine_mode
        self.settings["tessdata directory"] = ocr_controls.tessdata_dir
        logger.info("ocr language %s", self.settings["ocr language"])
        validation_error = ocr_controls.validation_error
        if validation_error is not None:
            self._show_message_dialog(
                parent=self,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                process="ocr",
                text=validation_error,
                page=None,
            )
            # Keep the batch going but skip OCR for this batch.
            self._skip_ocr_batch = True

    def _add_alternate_rotation_toggle(self, vboxp: Gtk.Box) -> Gtk.CheckButton:
        """Add alternate rotation toggle button."""
        abutton = Gtk.CheckButton(label=_("Alternate rotation every 2nd page"))
        abutton.set_tooltip_text(
            _(
                "Rotate odd pages by the chosen angle and even pages by that "
                "angle plus 180 degrees. Use when scanning a book where every "
                "sheet is aligned to the same edge, so the back of each sheet "
                "is rotated 180 degrees relative to its front."
            )
        )
        if self.settings.get("alternate rotation", False):
            abutton.set_active(True)
        abutton.set_visible(False)

        def _on_alternate_rotation_toggled(button: Gtk.CheckButton) -> None:
            if not button.get_active():
                self._alternate_flatbed_count = 0
            self.settings["alternate rotation"] = button.get_active()

        abutton.connect("toggled", _on_alternate_rotation_toggled)
        vboxp.append(abutton)
        return abutton

    def _add_postprocessing_unpaper(self, vboxp: Gtk.Box) -> Gtk.CheckButton:
        hboxu = Gtk.Box(spacing=DIALOG_ROW_SPACING)
        vboxp.append(hboxu)
        ubutton = Gtk.CheckButton(label=_("Clean up images"))
        ubutton.set_tooltip_text(_("Clean up scanned images with unpaper"))
        hboxu.append(ubutton)
        ubutton.set_hexpand(True)
        if not self._dependencies["unpaper"]:
            ubutton.set_sensitive(sensitive=False)
            ubutton.set_active(False)
        elif self.settings["unpaper on scan"]:
            ubutton.set_active(True)

        button = Gtk.Button(label=_("Options"))
        button.set_tooltip_text(_("Set unpaper options"))
        hboxu.append(button)
        button.set_hexpand(True)
        button.connect("clicked", self._show_unpaper_options)
        return ubutton

    def _show_unpaper_options(self, _button: Gtk.Button) -> None:
        windowuo = Dialog(
            transient_for=self,
            title=_("unpaper options"),
        )
        self._unpaper.add_options(windowuo.get_content_area())

        def unpaper_options_callback() -> None:
            self.settings["unpaper options"] = self._unpaper.get_options()
            windowuo.destroy()

        windowuo.add_actions(
            [
                (_("_OK"), unpaper_options_callback),
                (_("_Cancel"), windowuo.destroy),
            ]
        )
        windowuo.present()

    def _add_postprocessing_udt(
        self, vboxp: Gtk.Box
    ) -> tuple[Gtk.CheckButton, ComboBoxText]:
        """Add a user-defined tool (UDT) post-processing option to the given VBox."""
        hboxudt = Gtk.Box(spacing=DIALOG_ROW_SPACING)
        vboxp.append(hboxudt)
        self._scan_udt_hbox = hboxudt
        udtbutton = Gtk.CheckButton(label=_("Process with user-defined tool"))
        udtbutton.set_tooltip_text(_("Process scanned images with user-defined tool"))
        self._scan_udt_button = udtbutton
        hboxudt.append(udtbutton)
        udtbutton.set_hexpand(True)
        if not self.settings["user_defined_tools"]:
            hboxudt.set_sensitive(sensitive=False)
            udtbutton.set_active(False)

        elif self.settings["udt_on_scan"]:
            udtbutton.set_active(True)

        return udtbutton, self._add_udt_combobox(hboxudt)

    def _add_udt_combobox(self, hbox: Gtk.Box) -> ComboBoxText:
        """Add a ComboBoxText widget to the given hbox containing user-defined tools."""
        toolarray = [[t, t] for t in self.settings["user_defined_tools"]]

        combobox = ComboBoxText(data=toolarray)
        combobox.set_active_index(self.settings["current_udt"])
        hbox.append(combobox)
        combobox.set_hexpand(True)
        return combobox

    def _changed_device_callback(
        self, widget: SaneScanDialog, device: str | None
    ) -> None:
        """Handle changed device signal."""
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

    def _changed_device_list_callback(
        self, widget: SaneScanDialog, device_list: list[object]
    ) -> None:  # widget is windows
        """Handle changed device list signal."""
        logger.info("signal 'changed-device-list' emitted with data: %s", device_list)
        if len(device_list):
            # Apply the device blacklist
            _apply_device_blacklist(device_list, self.settings, widget)

            if self.settings["cache-device-list"] and _confirm_libusb_caching(
                self, device_list, self.settings
            ):
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

    def _flatbed_source_active(self, widget: SaneScanDialog | None) -> bool:
        """Return whether the dialog is scanning from a flatbed with batch allowed."""
        if widget is None or not isinstance(
            cast("object", widget.allow_batch_flatbed), bool
        ):
            return False
        if not widget.allow_batch_flatbed:
            return False
        options = cast("Options | None", widget.available_scan_options)
        return bool(
            options is not None
            and widget.thread is not None
            and widget.flatbed_source_selected()
        )

    def _flatbed_batch_active(self, widget: SaneScanDialog | None) -> bool:
        """Return whether the dialog is scanning a flatbed batch of > 1 pages."""
        if not self._flatbed_source_active(widget):
            return False
        num_pages = cast("object", widget.num_pages)
        return isinstance(num_pages, int) and num_pages > 1

    def _alternating_rotation_active(self) -> bool:
        """Return whether parity-based rotation applies to the next scan."""
        return bool(
            self.settings.get("alternate rotation", False)
            and self._flatbed_source_active(self._windows)
        )

    def _update_postprocessing_options_callback(
        self,
        widget: SaneScanDialog,
        _option_name: str | None = None,
        _option_val: object | None = None,
        _uuid: str | None = None,
    ) -> None:
        """Update the visibility of post-processing options based on the widget's scan options."""
        # widget is windows
        options = cast("Options | None", widget.available_scan_options)
        if options is not None:
            self._rotate_controls.can_duplex = options.can_duplex()
        button = getattr(self, "_alternate_rotation_button", None)
        if button is not None:
            button.set_visible(self._flatbed_source_active(widget))

    def _changed_progress_callback(
        self, _widget: Gtk.Widget, progress: float | None, message: str | None
    ) -> None:
        """Update the progress bar based on the given progress value and message."""
        if progress is not None and (0 < progress <= 1):
            self._scan_progress.set_fraction(progress)
        else:
            self._scan_progress.pulse()
        if message is not None:
            self._scan_progress.set_text(message)
        self._scan_progress.show()

    def _changed_profile_callback(self, _widget: Gtk.Widget, profile: str) -> None:
        self.settings["default profile"] = profile

    def _added_profile_callback(
        self, _widget: Gtk.Widget, name: str, profile: Profile
    ) -> None:
        self.settings["profile"][name] = profile.get()

    def _new_scan_callback(
        self,
        _widget: Gtk.Widget,
        image_object: object,
        insert_after: str | None,
        side: str,
        xresolution: float,
        yresolution: float,
        *args: object,
    ) -> None:
        """Handle a new scan.

        The optional trailing argument is the depth-mismatch flag emitted
        with the "new-scan" signal.
        """
        if image_object is None:
            return
        enforce_depth = bool(args[0]) if args else False

        rotate = (
            self.settings["rotate facing"]
            if side == "facing"
            else self.settings["rotate reverse"]
        )
        if side == "facing" and self._alternating_rotation_active():
            count = getattr(self, "_alternate_flatbed_count", 0) + 1
            self._alternate_flatbed_count = count
            if count % 2 == 0:
                rotate = (rotate + 180) % 360
        options = {
            "dir": self.session.name,
            "rotate": rotate,
            "ocr": bool(self.settings["OCR on scan"])
            and not getattr(self, "_skip_ocr_batch", False),
            "engine": self.settings["ocr engine"],
            "language": self.settings["ocr language"],
            "variables": self.settings.get("tesseract variables", ""),
            "psm": self.settings.get("ocr psm", ""),
            "engine_mode": self.settings.get("ocr engine mode"),
            "tessdata_dir": self.settings.get("tessdata directory", ""),
            "queued_callback": self.post_process_progress.queued,
            "started_callback": self.post_process_progress.update,
            "finished_callback": self._import_scan_finished_callback,
            "error_callback": self._error_callback,
            "image_object": image_object,
            "resolution": (xresolution, yresolution, "PixelsPerInch"),
        }
        if insert_after is not None:
            options["insert_after"] = insert_after
        if self.settings["unpaper on scan"]:
            options["unpaper"] = self._unpaper

        if self.settings["threshold-before-ocr"]:
            options["threshold"] = self.settings["threshold tool"]

        if enforce_depth:
            options["enforce_depth"] = True
            options["depth_threshold"] = self.settings["threshold tool"]

        if self.settings["udt_on_scan"]:
            options["udt"] = self.settings["current_udt"]

        logger.info("Importing scan with resolution=%s,%s", xresolution, yresolution)
        self.slist.import_scan(**options)

    def _reloaded_scan_options_callback(self, widget: SaneScanDialog) -> None:
        """Call only the first time after loading the available options."""
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
            widget.profile = next(iter(profiles))

        self._update_postprocessing_options_callback(widget)

    def _import_scan_finished_callback(self, response: Response) -> None:
        """Handle the completion of a scan import process."""
        self.post_process_progress.finish(response)

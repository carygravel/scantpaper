"""Scan dialog for SANE backend."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from gi.repository import GObject, Gtk

from scantpaper.const import EMPTY
from scantpaper.dialog.scan import Scan, _geometry_option, make_progress_string
from scantpaper.frontend import enums
from scantpaper.frontend.image_sane import SaneThread
from scantpaper.helpers import (
    configure_fractional_spinbutton,
    format_number_precise,
    parse_number,
    spin_step,
)
from scantpaper.i18n import _, d_sane
from scantpaper.scanner.options import Options

if TYPE_CHECKING:
    from scantpaper.basethread import Response
    from scantpaper.scanner.options import Option

LAST_PAGE = -1
FIRST_OPTIONS_PAGE = 2
logger = logging.getLogger(__name__)


class SaneScanDialog(Scan):
    """Scan dialog for SANE backend."""

    cycle_sane_handle = GObject.Property(
        type=bool,
        default=False,
        nick="Cycle SANE handle after scan",
        blurb="In some scanners, this allows the ADF to eject the last page",
    )
    cancel_between_pages = GObject.Property(
        type=bool,
        default=False,
        nick="Cancel previous page when starting new one",
        blurb="Otherwise, some Brother scanners report out of documents, "
        "despite scanning from flatbed.",
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise SaneScanDialog."""
        super().__init__(*args, **kwargs)
        self.thread = SaneThread()
        self.thread.start()
        self.geometry_boxes = None
        self._option_info = {}

    def get_devices(self) -> None:
        """Run Sane.get_devices()."""
        self.cursor = "wait"
        pbar = None
        hboxd = self.hboxd

        def started_callback(_data: object) -> None:
            """Set up ProgressBar."""
            nonlocal pbar
            pbar = Gtk.ProgressBar()
            pbar.set_show_text(True)
            pbar.set_pulse_step(self.progress_pulse_step)
            pbar.set_text(_("Fetching list of devices"))
            hboxd.pack_start(pbar, expand=True, fill=True, padding=0)
            hboxd.hide()
            hboxd.show()
            pbar.show()

        def running_callback(_data: object) -> None:
            nonlocal pbar
            pbar.pulse()

        def finished_callback(response: Response) -> None:
            nonlocal self
            nonlocal pbar
            pbar.destroy()
            device_list = response.info
            logger.info("sane.get_devices() returned: %s", device_list)
            self.device_list = device_list
            if len(device_list) == 0:
                self.emit("process-error", "get_devices", _("No devices found"))
                self.destroy()

            hboxd.show_all()
            self.cursor = "default"

        self.thread.get_devices(
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
        )

    def scan_options(self, device: str | None = None) -> None:
        """Retrieve device-dependent scan options."""
        if device is None:
            device = self.device

        # Remove any existing pages
        while self.notebook.get_n_pages() > FIRST_OPTIONS_PAGE:
            self.notebook.remove_page(LAST_PAGE)

        # Remove lookups to geometry boxes and option widgets
        self.geometry_boxes = None
        self.option_widgets = {}
        self._option_info = {}

        self.thread.open_device(
            device_name=self.device,
            started_callback=self._device_opening_started,
            running_callback=self._running_callback,
            finished_callback=self._device_opened,
            error_callback=self._device_open_error,
        )

    def _running_callback(self, _data: object) -> None:
        self.emit("changed-progress", None, None)

    def _device_opening_started(self, _data: object) -> None:
        self.cursor = "wait"
        self.emit("started-process", _("Opening device"))

        # Ghost the scan button whilst options being updated
        self.set_response_sensitive(Gtk.ResponseType.OK, setting=False)

    def _device_opened(self, _data: object) -> None:
        self.emit("finished-process", "open_device")
        self._request_scan_options()

    def _device_open_error(self, response: Response) -> None:
        self.emit(
            "process-error",
            "open_device",
            _("Error opening device: ") + cast("str", response.status),
        )
        self.cursor = "default"

    def _request_scan_options(self) -> None:
        def started_callback(_data: object) -> None:
            self.emit("started-process", _("Retrieving options"))

        def finished_callback(response: Response) -> None:
            options = Options(response.info)
            self._initialise_options(options)
            self.emit("finished-process", "find_scan_options")

            # This fires the reloaded-scan-options signal,
            # so don't set this until we have finished
            self.available_scan_options = options
            self._set_paper_sizes(self.paper_sizes)
            self.cursor = "default"

        def error_callback(response: Response) -> None:
            self.emit(
                "process-error",
                "find_scan_options",
                _("Error retrieving scanner options: ") + cast("str", response.status),
            )
            self.cursor = "default"

        self.thread.get_options(
            started_callback=started_callback,
            running_callback=self._running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def _initialise_options(self, options: Options) -> None:
        logger.debug("sane.get_option_descriptor() returned: %s", options)
        vbox, hboxp = None, None
        num_dev_options = options.num_options()

        # We have hereby removed the active profile and paper,
        # so update the properties without triggering the signals
        self._profile = None
        self._paper = None
        self.combobp = None  # So we don't carry over from one device to another
        for i in range(1, num_dev_options):
            opt = options.by_index(i)
            vbox, hboxp = self._initialise_option(vbox, hboxp, options, opt)

        # Show new pages
        for i in range(2, self.notebook.get_n_pages()):
            self.notebook.get_nth_page(i).show_all()

        self.set_response_sensitive(Gtk.ResponseType.OK, setting=True)

    def _new_group_page(self, opt: Option) -> Gtk.Box:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text = (
            d_sane(opt.title)
            if (
                opt.type == enums.TYPE_GROUP
                # A brother scanner used an empty string as a group title,
                # which then results in a tab with no title, which is
                # confusing and can be missed, so set to the default.
                and opt.title != EMPTY
            )
            else _("Scan Options")
        )
        scwin = Gtk.ScrolledWindow()
        self.notebook.append_page(scwin, Gtk.Label(label=text))
        scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scwin.add(vbox)
        return vbox

    def _initialise_option(
        self,
        vbox: Gtk.Box | None,
        hboxp: Gtk.Box | None,
        options: Options,
        opt: Option,
    ) -> tuple[Gtk.Box | None, Gtk.Box | None]:
        # Notebook page for group
        if opt.type == enums.TYPE_GROUP or vbox is None:
            vbox = self._new_group_page(opt)
            if opt.type == enums.TYPE_GROUP:
                return vbox, hboxp

        if not opt.cap & enums.CAP_SOFT_DETECT:
            return vbox, hboxp

        # Widget
        try:
            val = self.thread.get_option_value(opt.name)
        except (KeyError, AttributeError):
            val = None

        # Define HBox for paper size here
        # so that it can be put before first geometry option
        if hboxp is None and _geometry_option(opt):
            hboxp = Gtk.Box()
            vbox.pack_start(hboxp, expand=False, fill=False, padding=0)

        # HBox for option
        hbox = Gtk.Box()
        vbox.pack_start(hbox, expand=False, fill=True, padding=0)
        if opt.cap & enums.CAP_INACTIVE or not opt.cap & enums.CAP_SOFT_SELECT:
            hbox.set_sensitive(False)

        if isinstance(val, list):  # $opt->{max_values} > 1
            widget = Gtk.Button(label=d_sane(opt.title))
        else:
            widget = self._create_widget(opt, val, hbox)
            if widget is None:
                return vbox, hboxp

        self._pack_widget(widget, [options, opt, hbox, hboxp])
        return vbox, hboxp

    def _create_widget_switch(self, opt: Option, val: object) -> Gtk.Switch:
        widget = Gtk.Switch()
        if val:
            widget.set_active(True)

        def activate_switch_cb(_widget: Gtk.Switch, _arg2: object) -> None:
            self.num_reloads = 0  # num-reloads is read-only
            self._reverted_option_counts.pop(opt.name, None)
            value = widget.get_active()
            self.set_option(opt, value=value)

        widget.signal = widget.connect("notify::active", activate_switch_cb)
        return widget

    def _create_widget_button(self, opt: Option) -> Gtk.Button:
        widget = Gtk.Button(label=d_sane(opt.title))

        def clicked_button_cb(_widget: Gtk.Button) -> None:
            self.num_reloads = 0  # num-reloads is read-only
            self._reverted_option_counts.pop(opt.name, None)
            self.set_option(opt, value=None)

        widget.signal = widget.connect("clicked", clicked_button_cb)
        return widget

    def _create_widget_spinbutton(
        self, opt: Option, val: object
    ) -> Gtk.SpinButton | None:
        if opt.constraint[0] > opt.constraint[1]:
            logger.error(
                _("Ignoring scan option '%s', minimum range (%s) > maximum (%s)"),
                opt.name,
                opt.constraint[0],
                opt.constraint[1],
            )
            return None
        step = spin_step(opt.constraint)

        widget = Gtk.SpinButton.new_with_range(
            opt.constraint[0], opt.constraint[1], step
        )

        # Set the default
        if val is not None and not opt.cap & enums.CAP_INACTIVE:
            widget.set_value(val)

        # Size fields take fractional values, with the locale's decimal
        # separator, trimmed display and strict commit-time input.
        if opt.type == enums.TYPE_FIXED:
            configure_fractional_spinbutton(widget)

        last_forwarded: list[object] = [None]

        def value_changed_spinbutton_cb(_widget: Gtk.SpinButton) -> None:
            self.num_reloads = 0  # num-reloads is read-only
            self._reverted_option_counts.pop(opt.name, None)
            value = widget.get_value()
            if opt.type == enums.TYPE_INT:
                value = int(value)
            if last_forwarded[0] != value:
                last_forwarded[0] = value
                self.set_option(opt, value=value)

        widget.signal = widget.connect("value-changed", value_changed_spinbutton_cb)
        return widget

    def _create_widget_combobox(self, opt: Option, val: object) -> Gtk.ComboBoxText:
        widget = Gtk.ComboBoxText()
        index = 0
        for i, constraint in enumerate(opt.constraint):
            if isinstance(constraint, (int, float)):
                widget.append_text(format_number_precise(constraint))
            else:
                widget.append_text(str(d_sane(constraint)))
            if val is not None and constraint == val:
                index = i

        # Set the default
        if index is not None:
            widget.set_active(index)

        def changed_combobox_cb(_arg: Gtk.ComboBoxText) -> None:
            self.num_reloads = 0  # num-reloads is read-only
            self._reverted_option_counts.pop(opt.name, None)
            i = widget.get_active()

            # refetch options in case they have changed.
            # tested by 06197_Dialog_Scan_Image_Sane
            options = self.available_scan_options
            updated_opt = options.by_name(opt.name)
            self.set_option(updated_opt, value=updated_opt.constraint[i])

        widget.signal = widget.connect("changed", changed_combobox_cb)
        return widget

    def _create_widget_entry(self, opt: Option, val: object) -> Gtk.Entry:
        widget = Gtk.Entry()

        # Set the default

        if val is not None and not opt.cap & enums.CAP_INACTIVE:
            if opt.type in (enums.TYPE_INT, enums.TYPE_FIXED):
                widget.set_text(format_number_precise(val))
            else:
                widget.set_text(str(val))

        def activate_entry_cb(_widget: Gtk.Entry) -> None:
            self.num_reloads = 0  # num-reloads is read-only
            self._reverted_option_counts.pop(opt.name, None)
            if opt.type == enums.TYPE_FIXED:
                try:
                    value = parse_number(widget.get_text())
                except ValueError:
                    return
            elif opt.type == enums.TYPE_INT:
                try:
                    value = parse_number(widget.get_text(), int)
                except ValueError:
                    return
            else:
                value = widget.get_text()
            self.set_option(opt, value=value)

        widget.signal = widget.connect("activate", activate_entry_cb)
        return widget

    def _create_widget(
        self, opt: Option, val: object, hbox: Gtk.Box
    ) -> Gtk.Widget | None:

        # Label
        if opt.type != enums.TYPE_BUTTON:
            text = opt.title
            if text is None or text == EMPTY:
                text = opt.name

            label = Gtk.Label(label=d_sane(text))
            hbox.pack_start(label, expand=False, fill=False, padding=0)

        widget = None
        if opt.type == enums.TYPE_BOOL:
            widget = self._create_widget_switch(opt, val)
        elif opt.type == enums.TYPE_BUTTON:
            widget = self._create_widget_button(opt)
        elif isinstance(opt.constraint, tuple):
            widget = self._create_widget_spinbutton(opt, val)
        elif isinstance(opt.constraint, list):
            widget = self._create_widget_combobox(opt, val)
        elif opt.constraint is None:
            widget = self._create_widget_entry(opt, val)
        return widget

    def _post_set_option_hook(
        self, option: Option, val: object, uuid: object | None
    ) -> None:

        # We can carry on applying defaults now, if necessary.
        self.emit(
            "finished-process",
            f"set_option {option.name}"
            + (EMPTY if option.type == enums.TYPE_BUTTON else f" to {val}"),
        )

        # Emit the changed-current-scan-options signal
        # unless we are actively setting it.
        # Clear the named profile only when the user manually changes an option
        # (uuid is None). Options set as part of a profile application carry a
        # non-None uuid and must NOT clear the profile, even if setting_profile
        # has already been cleared.
        if uuid is None and not self.setting_current_scan_options:
            self.emit("changed-current-scan-options", self.current_scan_options, EMPTY)
            self.profile = None

        self._update_widget_value(option, val)
        self.emit("changed-scan-option", option.name, val, uuid)

    def set_option(
        self, option: Option | None, value: object, uuid: object | None = None
    ) -> None:
        """Update the sane option in the thread.

        If necessary, reload the options,
        and walking the options tree, update the widgets.
        """
        if option is None:
            return

        value = self._clamp_option_value(option, value)

        def started_callback(_data: object) -> None:
            self.emit("started-process", _("Setting option %s") % (option.name))

        def running_callback(_data: object) -> None:
            self.emit("changed-progress", None, None)

        def finished_callback(response: Response) -> None:
            if response.status != "STATUS_INVAL":
                self.current_scan_options.add_backend_option(option.name, value)

            self._option_info[option.name] = response.info
            if response.info & enums.INFO_RELOAD_OPTIONS:
                self._reload_options_after_set(option, value, uuid)
            else:
                self._post_set_option_hook(option, value, uuid)

        def error_callback(response: Response) -> None:
            self.emit(
                "process-error",
                "set_option",
                _("Error setting option: ") + cast("str", response.status),
            )

        self.thread.set_option(
            name=option.name,
            value=value,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def _clamp_option_value(self, option: Option, value: object) -> object:
        """Ensure value is within max-min range of constraint."""
        if isinstance(option.constraint, tuple):
            if value < option.constraint[0]:
                value = option.constraint[0]
            elif value > option.constraint[1]:
                value = option.constraint[1]
        return value

    def _reload_options_after_set(
        self, option: Option, value: object, uuid: object | None
    ) -> None:
        def started_callback(_data: object) -> None:
            self.emit("started-process", _("Retrieving options"))

        def running_callback(_data: object) -> None:
            self.emit("changed-progress", None, None)

        def finished_callback(data: Response) -> None:
            self._update_options(Options(data.info))
            self._post_set_option_hook(option, value, uuid)

        def error_callback(response: Response) -> None:
            self.emit(
                "process-error",
                "find_scan_options",
                _("Error retrieving scanner options: ") + cast("str", response.status),
            )

        self.thread.get_options(
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def scan(self) -> None:
        """Scan."""
        self.cursor = "progress"

        # Get selected number of pages
        num_pages = self.num_pages
        if num_pages == 0 and self.max_pages > 0:
            num_pages = self.max_pages
        if (
            self.sided == "double"
            and self.side_to_scan == "reverse"
            and self._batch_n == 0
        ):
            self.emit("process-error", "scan", _("Must scan facing pages first"))

        xresolution, yresolution = self._get_xy_resolution()
        i = 1

        def started_callback(_data: object) -> None:
            logger.info("Scanning %s pages", num_pages)
            self.emit("started-process", make_progress_string(i, num_pages))

        def new_page_callback(image_ob: object) -> None:
            nonlocal i
            insert_after, side = self._insert_target(i)
            self.emit(
                "new-scan", image_ob, insert_after, side, xresolution, yresolution
            )
            i += 1
            self.emit(
                "changed-progress",
                None,
                make_progress_string(i, num_pages),
            )

        self.thread.scan_pages(
            dir=self.dir,
            num_pages=num_pages,
            cancel_between_pages=(
                self.cancel_between_pages
                and self.available_scan_options.flatbed_selected(
                    self.thread.get_option_value
                )
            ),
            started_callback=started_callback,
            running_callback=self._running_callback,
            finished_callback=self._scan_finished_callback,
            new_page_callback=new_page_callback,
            error_callback=self._scan_error_callback,
        )

    def _scan_finished_callback(self, _response: Response) -> None:
        self.emit("finished-process", "scan_pages")
        self.cursor = "default"
        if self.cycle_sane_handle:
            current = self.current_scan_options
            signal = None

            def reloaded_scan_options_cb(_widget: object) -> None:
                self.disconnect(signal)
                self.set_current_scan_options(current)

            signal = self.connect("reloaded-scan-options", reloaded_scan_options_cb)
            self.scan_options(self.device)

    def _scan_error_callback(self, response: Response) -> None:
        self.emit("process-error", "scan_pages", response.status)
        self.cursor = "default"

    def cancel_scan(self, _widget: Gtk.Widget) -> None:
        """Cancel any running or queued scan processes."""
        self.thread.cancel()
        logger.info("Cancelled scan")

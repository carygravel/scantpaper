"Scan dialog for SANE backend"

import logging
from gi.repository import GObject, Gtk
from frontend import enums
from frontend.image_sane import SaneThread
from dialog.scan import Scan, _geometry_option, make_progress_string
from scanner.options import Options
from i18n import _, d_sane

EMPTY = ""
LAST_PAGE = -1
logger = logging.getLogger(__name__)


class SaneScanDialog(Scan):
    "Scan dialog for SANE backend"

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.thread = SaneThread()
        self.thread.start()
        self.geometry_boxes = None
        self._option_info = {}

    def get_devices(self):
        "Run Sane.get_devices()"
        self.cursor = "wait"
        pbar = None
        hboxd = self.hboxd

        def started_callback(_data):
            "Set up ProgressBar"
            nonlocal pbar
            pbar = Gtk.ProgressBar()
            pbar.set_show_text(True)
            pbar.set_pulse_step(self.progress_pulse_step)
            pbar.set_text(_("Fetching list of devices"))
            hboxd.pack_start(pbar, True, True, 0)
            hboxd.hide()
            hboxd.show()
            pbar.show()

        def running_callback(_data):
            nonlocal pbar
            pbar.pulse()

        def finished_callback(response):
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

    def scan_options(self, device=None):
        "retrieve device-dependent scan options"

        if device is None:
            device = self.device

        # Remove any existing pages
        while self.notebook.get_n_pages() > 2:
            self.notebook.remove_page(LAST_PAGE)

        # Remove lookups to geometry boxes and option widgets
        self.geometry_boxes = None
        self.option_widgets = {}
        self._option_info = {}

        def started_callback(_data):
            self.cursor = "wait"
            self.emit("started-process", _("Opening device"))

            # Ghost the scan button whilst options being updated
            self.set_response_sensitive(Gtk.ResponseType.OK, False)

        def running_callback(_data):
            self.emit("changed-progress", None, None)

        def finished_callback(_data):
            self.emit("finished-process", "open_device")

            def started_callback(_data):
                self.emit("started-process", _("Retrieving options"))

            def running_callback(_data):
                self.emit("changed-progress", None, None)

            def finished_callback(response):
                options = Options(response.info)
                self._initialise_options(options)
                self.emit("finished-process", "find_scan_options")

                # This fires the reloaded-scan-options signal,
                # so don't set this until we have finished
                self.available_scan_options = options
                self._set_paper_formats(self.paper_formats)
                self.cursor = "default"

            def error_callback(response):
                self.emit(
                    "process-error",
                    "find_scan_options",
                    _("Error retrieving scanner options: ") + response.status,
                )
                self.cursor = "default"

            self.thread.get_options(
                started_callback=started_callback,
                running_callback=running_callback,
                finished_callback=finished_callback,
                error_callback=error_callback,
            )

        def error_callback(response):
            self.emit(
                "process-error",
                "open_device",
                _("Error opening device: ") + response.status,
            )
            self.cursor = "default"

        self.thread.open_device(
            device_name=self.device,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def _initialise_options(self, options):
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

            # Notebook page for group
            if opt.type == enums.TYPE_GROUP or vbox is None:
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                # vbox.set_border_width( self.get_style_context().get_property(
                #                                                 'content-area-border') )
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
                if opt.type == enums.TYPE_GROUP:
                    continue

            if not opt.cap & enums.CAP_SOFT_DETECT:
                continue

            # Widget
            widget = None
            try:
                val = getattr(self.thread.device_handle, opt.name.replace("-", "_"))
            except (KeyError, AttributeError):
                val = None

            # Define HBox for paper size here
            # so that it can be put before first geometry option
            if hboxp is None and _geometry_option(opt):
                hboxp = Gtk.Box()
                vbox.pack_start(hboxp, False, False, 0)

            # HBox for option
            hbox = Gtk.Box()
            vbox.pack_start(hbox, False, True, 0)
            if opt.cap & enums.CAP_INACTIVE or not opt.cap & enums.CAP_SOFT_SELECT:
                hbox.set_sensitive(False)

            if isinstance(val, list):  # $opt->{max_values} > 1
                widget = Gtk.Button(d_sane(opt.title))
                # widget.signal = widget.connect(
                #     "clicked",
                #     Gscan2pdf.Dialog.Scan.multiple_values_button_callback,
                #     [self, opt],
                # )
            else:
                widget = self._create_widget(opt, val, hbox)
                if widget is None:
                    continue

            self._pack_widget(widget, [options, opt, hbox, hboxp])

        # Show new pages
        for i in range(2, self.notebook.get_n_pages()):
            self.notebook.get_nth_page(i).show_all()

        self.set_response_sensitive(Gtk.ResponseType.OK, True)

    def _create_widget_switch(self, opt, val):
        widget = Gtk.Switch()
        if val:
            widget.set_active(True)

        def activate_switch_cb(_widget, _arg2):
            self.num_reloads = 0  # num-reloads is read-only
            value = widget.get_active()
            self.set_option(opt, value)

        widget.signal = widget.connect("notify::active", activate_switch_cb)
        return widget

    def _create_widget_button(self, opt):
        widget = Gtk.Button(label=d_sane(opt.title))

        def clicked_button_cb():
            self.num_reloads = 0  # num-reloads is read-only
            self.set_option(opt, None)

        widget.signal = widget.connect("clicked", clicked_button_cb)
        return widget

    def _create_widget_spinbutton(self, opt, val):
        if opt.constraint[0] > opt.constraint[1]:
            logger.error(
                _("Ignoring scan option '%s', minimum range (%s) > maximum (%s)"),
                opt.name,
                opt.constraint[0],
                opt.constraint[1],
            )
            return None
        step = 1
        if opt.constraint[2] > 0:
            step = opt.constraint[2]

        widget = Gtk.SpinButton.new_with_range(
            opt.constraint[0], opt.constraint[1], step
        )

        # Set the default
        if val is not None and not opt.cap & enums.CAP_INACTIVE:
            widget.set_value(val)

        def value_changed_spinbutton_cb():
            self.num_reloads = 0  # num-reloads is read-only
            value = widget.get_value()
            self.set_option(opt, value)

        widget.signal = widget.connect("value-changed", value_changed_spinbutton_cb)
        return widget

    def _create_widget_combobox(self, opt, val):
        widget = Gtk.ComboBoxText()
        index = 0
        for i, constraint in enumerate(opt.constraint):
            widget.append_text(str(d_sane(constraint)))
            if val is not None and constraint == val:
                index = i

        # Set the default
        if index is not None:
            widget.set_active(index)

        def changed_combobox_cb(_arg):
            self.num_reloads = 0  # num-reloads is read-only
            i = widget.get_active()

            # refetch options in case they have changed.
            # tested by 06197_Dialog_Scan_Image_Sane
            options = self.available_scan_options
            updated_opt = options.by_name(opt.name)
            self.set_option(updated_opt, updated_opt.constraint[i])

        widget.signal = widget.connect("changed", changed_combobox_cb)
        return widget

    def _create_widget_entry(self, opt, val):
        widget = Gtk.Entry()

        # Set the default

        if val is not None and not opt.cap & enums.CAP_INACTIVE:
            widget.set_text(str(val))

        def activate_entry_cb():
            self.num_reloads = 0  # num-reloads is read-only
            value = widget.get_text()
            self.set_option(opt, value)

        widget.signal = widget.connect("activate", activate_entry_cb)
        return widget

    def _create_widget(self, opt, val, hbox):

        # Label
        if opt.type != enums.TYPE_BUTTON:
            text = opt.title
            if text is None or text == EMPTY:
                text = opt.name

            label = Gtk.Label(label=d_sane(text))
            hbox.pack_start(label, False, False, 0)

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

    def _post_set_option_hook(self, option, val, uuid):

        # We can carry on applying defaults now, if necessary.
        self.emit(
            "finished-process",
            f"set_option {option.name}"
            + (EMPTY if option.type == enums.TYPE_BUTTON else f" to {val}"),
        )

        # Unset the profile unless we are actively setting it
        if not self.setting_profile:
            self.profile = None

            # Emit the changed-current-scan-options signal
            # unless we are actively setting it
            if not self.setting_current_scan_options:
                self.emit(
                    "changed-current-scan-options", self.current_scan_options, EMPTY
                )

        self._update_widget_value(option, val)
        self.emit("changed-scan-option", option.name, val, uuid)

    def set_option(self, option, value, uuid=None):
        """Update the sane option in the thread
        If necessary, reload the options,
        and walking the options tree, update the widgets"""
        if option is None:
            return

        # ensure value is within max-min range of constraint
        if isinstance(option.constraint, tuple):
            if value < option.constraint[0]:
                value = option.constraint[0]
            elif value > option.constraint[1]:
                value = option.constraint[1]

        def started_callback(_data):
            self.emit("started-process", _("Setting option %s") % (option.name))

        def running_callback(_data):
            self.emit("changed-progress", None, None)

        def finished_callback(response):
            if response.status != "STATUS_INVAL":
                self.current_scan_options.add_backend_option(option.name, value)

            self._option_info[option.name] = response.info
            if response.info & enums.INFO_RELOAD_OPTIONS:

                def started_callback(_data):
                    self.emit("started-process", _("Retrieving options"))

                def running_callback(_data):
                    self.emit("changed-progress", None, None)

                def finished_callback(data):
                    self._update_options(Options(data.info))
                    self._post_set_option_hook(option, value, uuid)

                def error_callback(response):
                    self.emit(
                        "process-error",
                        "find_scan_options",
                        _("Error retrieving scanner options: ") + response.status,
                    )

                self.thread.get_options(
                    started_callback=started_callback,
                    running_callback=running_callback,
                    finished_callback=finished_callback,
                    error_callback=error_callback,
                )

            else:
                self._post_set_option_hook(option, value, uuid)

        def error_callback(response):
            self.emit(
                "process-error",
                "set_option",
                _("Error setting option: ") + response.status,
            )

        self.thread.set_option(
            name=option.name,
            value=value,
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
        )

    def scan(self):
        self.cursor = "progress"

        # Get selected number of pages
        num_pages = self.num_pages
        start = self.page_number_start
        step = self.page_number_increment
        if step < 0 < num_pages:
            num_pages = self.max_pages
        if start == 1 and step < 0:
            self.emit("process-error", "scan", _("Must scan facing pages first"))

        xresolution, yresolution = self._get_xy_resolution()
        i = 1

        def started_callback(_data):
            nonlocal i
            nonlocal num_pages
            if num_pages == 0 and self.max_pages > 0:
                num_pages = self.max_pages

            logger.info(
                "Scanning %s pages from %s with step %s", num_pages, start, step
            )
            self.emit("started-process", make_progress_string(i, num_pages))

        def running_callback(progress):
            self.emit("changed-progress", progress, None)

        def finished_callback(_response):
            self.emit("finished-process", "scan_pages")
            self.cursor = "default"
            if self.cycle_sane_handle:
                current = self.current_scan_options
                signal = None

                def reloaded_scan_options_cb(_widget):
                    self.disconnect(signal)
                    self.set_current_scan_options(current)

                signal = self.connect("reloaded-scan-options", reloaded_scan_options_cb)
                self.scan_options(self.device)

        def new_page_callback(image_ob, pagenumber):
            nonlocal i
            nonlocal xresolution
            nonlocal yresolution
            self.emit("new-scan", image_ob, pagenumber, xresolution, yresolution)
            self.emit(
                "changed-progress",
                0,
                make_progress_string(i, num_pages),
            )
            i += 1

        def error_callback(response):
            self.emit("process-error", "scan_pages", response.status)
            self.cursor = "default"

        self.thread.scan_pages(
            dir=self.dir,
            num_pages=num_pages,
            start=start,
            step=step,
            cancel_between_pages=(
                self.cancel_between_pages
                and self.available_scan_options.flatbed_selected(
                    self.thread.device_handle
                )
            ),
            started_callback=started_callback,
            running_callback=running_callback,
            finished_callback=finished_callback,
            new_page_callback=new_page_callback,
            error_callback=error_callback,
        )

    def cancel_scan(self):
        "cancel any running or queued scan processes"
        self.thread.cancel()
        logger.info("Cancelled scan")

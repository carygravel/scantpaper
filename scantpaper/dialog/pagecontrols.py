"The page controls for the Scan dialog"

import re
from gi.repository import Gtk, GObject
from dialog import Dialog
from scanner.options import Options
from scanner.profile import Profile
from comboboxtext import ComboBoxText
from i18n import _

MAX_PAGES = 9999
MAX_INCREMENT = 99
DOUBLE_INCREMENT = 2
INFINITE = -1


class PageControls(Dialog):  # pylint: disable=too-many-instance-attributes
    "The page controls for the Scan dialog"

    __gsignals__ = {
        "changed-num-pages": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "changed-page-number-start": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "changed-page-number-increment": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "changed-side-to-scan": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    _num_pages = 1
    max_pages = GObject.Property(
        type=int,
        minimum=-1,
        maximum=MAX_PAGES,
        default=0,
        nick="Maximum number of pages",
        blurb="Maximum number of pages that can be scanned with current "
        "page-number-start and page-number-increment",
    )
    _previous_start = None  # previous value of _page_number_start
    _page_number_start = 1
    _page_number_increment = 1
    _sided = "single"
    _side_to_scan = "facing"
    _document = None
    available_scan_options = Options([])
    allow_batch_flatbed = False
    ignore_duplex_capabilities = False
    adf_defaults_scan_all_pages = GObject.Property(
        type=bool,
        default=True,
        nick="Select # pages = all on selecting ADF",
        blurb="Select # pages = all on selecting ADF",
    )

    @GObject.Property(
        type=int,
        minimum=0,
        maximum=MAX_PAGES,
        default=1,
        nick="Number of pages",
        blurb="Number of pages to be scanned",
    )  # pylint: disable=method-hidden
    def num_pages(self):
        "getter for num_pages attribute"
        return self._num_pages

    @num_pages.setter
    def num_pages(self, newval):
        if newval == self._num_pages:
            return
        options = self.available_scan_options
        if (
            newval == 1
            or self.allow_batch_flatbed
            or (
                hasattr(self, "thread")  # in __init__(), thread may not yet exist
                and self.thread.device_handle is not None
                and not options.flatbed_selected(self.thread.device_handle)
            )
        ):
            self._num_pages = newval
            self.current_scan_options.add_frontend_option("num_pages", newval)
            self.emit("changed-num-pages", newval)

    @GObject.Property(
        type=int,
        minimum=-MAX_INCREMENT,
        maximum=MAX_INCREMENT,
        default=1,
        nick="Starting page number",
        blurb="Page number of first page to be scanned",
    )  # pylint: disable=method-hidden
    def page_number_start(self):  # pylint: disable=method-hidden
        "getter for page_number_start attribute"
        return self._page_number_start

    @page_number_start.setter
    def page_number_start(self, newval):
        self._page_number_start = newval
        self.emit("changed-page-number-start", newval)

    @GObject.Property(
        type=int,
        minimum=-MAX_INCREMENT,
        maximum=MAX_INCREMENT,
        default=1,
        nick="Page number increment",
        blurb="Amount to increment page number when scanning multiple pages",
    )  # pylint: disable=method-hidden
    def page_number_increment(self):
        "getter for page_number_increment attribute"
        return self._page_number_increment

    @page_number_increment.setter
    def page_number_increment(self, newval):
        self._page_number_increment = newval
        self.emit("changed-page-number-increment", newval)

    # Would have nice to use an enum here, but not supported by the python bindings
    # GObject.TypeModule.register_enum( 'Gscan2pdf::Dialog::Scan::Sided',
    #         ["single","double"] )
    @GObject.Property(
        type=str, default="single", nick="Sided", blurb="Either single or double"
    )  # pylint: disable=method-hidden
    def sided(self):
        "getter for sided attribute"
        return self._sided

    @sided.setter
    def sided(self, newval):
        self._sided = newval
        widget = self.buttons
        if newval == "double":
            widget = self.buttond
        else:
            # selecting single-sided also selects facing page.
            self.side_to_scan = "facing"
        widget.set_active(True)

    # Would have nice to use an enum here, but not supported by the python bindings
    # GObject.TypeModule.register_enum( 'Gscan2pdf::Dialog::Scan::Side',
    #         ["facing","reverse"] )
    @GObject.Property(
        type=object, nick="Side to scan", blurb="Either facing or reverse"
    )  # pylint: disable=method-hidden
    def side_to_scan(self):
        "getter for side_to_scan attribute"
        return self._side_to_scan

    @side_to_scan.setter
    def side_to_scan(self, newval):
        if newval not in ["facing", "reverse"]:
            raise ValueError(f"Invalid value for side-to-scan: {newval}")
        self._side_to_scan = newval
        self.combobs.set_active(0 if newval == "facing" else 1)
        self.emit("changed-side-to-scan", newval)
        slist = self.document
        if slist and slist.data:
            possible = slist.pages_possible(
                self.page_number_start, self.page_number_increment
            )
            requested = self.num_pages
            if possible != INFINITE and (requested == 0 or requested > possible):
                self.num_pages = possible
                self.max_pages = possible

    @GObject.Property(
        type=object, nick="Document", blurb="Document object for new scans"
    )
    def document(self):
        "getter for document attribute"
        return self._document

    @document.setter
    def document(self, newval):
        self._document = newval
        # Update the start spinbutton if the page number is been edited.
        if newval:
            newval.get_model().connect(
                "row-changed", lambda x, y, z: self.update_start_page()
            )
            newval.get_model().connect(
                "row-inserted", lambda x, y, z: self.update_start_page()
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_scan_options = Profile()

        # Notebook to collate options
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.get_content_area().pack_end(self.notebook, True, True, 0)

        # Notebook page 1
        scwin = Gtk.ScrolledWindow()
        self.notebook.append_page(
            child=scwin, tab_label=Gtk.Label(label=_("Page Options"))
        )
        scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._notebook_pages = [Gtk.VBox()]
        border_width = (
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        self._notebook_pages[0].set_border_width(border_width)
        scwin.add(self._notebook_pages[0])

        # Frame for # pages
        self.framen = Gtk.Frame(label=_("# Pages"))
        self._notebook_pages[0].pack_start(self.framen, False, False, 0)
        vboxn = Gtk.VBox()
        vboxn.set_border_width(border_width)
        self.framen.add(vboxn)

        # the first radio button has to set the group,
        # which is None for the first button
        # All button
        bscanall = Gtk.RadioButton.new_with_label_from_widget(None, _("All"))
        bscanall.set_tooltip_text(_("Scan all pages"))
        vboxn.pack_start(bscanall, True, True, 0)
        bscanall.connect("clicked", self._do_clicked_scan_all, bscanall)

        # Entry button
        hboxn = Gtk.Box()
        vboxn.pack_start(hboxn, True, True, 0)
        self._bscannum = Gtk.RadioButton.new_with_label_from_widget(bscanall, "#:")
        self._bscannum.set_tooltip_text(_("Set number of pages to scan"))
        hboxn.pack_start(self._bscannum, False, False, 0)

        # Number of pages
        spin_buttonn = Gtk.SpinButton.new_with_range(1, MAX_PAGES, 1)
        spin_buttonn.set_tooltip_text(_("Set number of pages to scan"))
        hboxn.pack_end(spin_buttonn, False, False, 0)
        self._bscannum.connect("clicked", self._do_clicked_scan_number, spin_buttonn)
        self.connect(
            "changed-num-pages",
            self._do_changed_num_pages,
            bscanall,
            self._bscannum,
            spin_buttonn,
        )

        # Actively set a radio button to synchronise GUI and properties
        if self.num_pages > 0:
            self._bscannum.set_active(True)
        else:
            self._bscanall.set_active(True)

        # vbox for duplex/simplex page numbering in order to be able to show/hide
        # them together.
        self._vboxx = Gtk.VBox()
        self._notebook_pages[0].pack_start(self._vboxx, False, False, 0)

        # Switch between basic and extended modes
        hbox = Gtk.Box()
        label = Gtk.Label(label=_("Extended page numbering"))
        hbox.pack_start(label, False, False, 0)
        self.checkx = Gtk.Switch()
        hbox.pack_end(self.checkx, False, False, 0)
        self._vboxx.pack_start(hbox, False, False, 0)

        self._create_extended_mode(spin_buttonn, self._bscannum)

    def _create_extended_mode(self, spin_buttonn, bscannum):

        # Frame for extended mode
        self.framex = Gtk.Frame(label=_("Page number"))
        self._vboxx.pack_start(self.framex, False, False, 0)
        vboxx = Gtk.VBox()
        border_width = (
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        vboxx.set_border_width(border_width)
        self.framex.add(vboxx)

        # SpinButton for starting page number
        spin_buttons = spinbutton_in_hbox(vboxx, _("Start"), 1, MAX_PAGES, 1)
        spin_buttons.connect("value-changed", self._do_start_page_changed)
        self.connect(
            "changed-page-number-start",
            self._do_changed_page_number_start,
            spin_buttons,
        )

        # SpinButton for page number increment
        spin_buttoni = spinbutton_in_hbox(
            vboxx, _("Increment"), -MAX_INCREMENT, MAX_INCREMENT, 1
        )
        spin_buttoni.connect("value-changed", self._do_spin_buttoni_value_changed)
        self.connect(
            "changed-page-number-increment",
            self._do_changed_page_number_increment,
            spin_buttoni,
        )

        # Setting this here to fire callback running update_start
        spin_buttons.set_value(self.page_number_start)
        spin_buttonn.connect("value-changed", self._do_num_pages_changed, bscannum)

        # Frame for standard mode
        self.frames = Gtk.Frame(label=_("Source document"))
        self._vboxx.pack_start(self.frames, False, False, 0)
        vboxs = Gtk.VBox()
        vboxs.set_border_width(border_width)
        self.frames.add(vboxs)

        # Single sided button
        self.buttons = Gtk.RadioButton.new_with_label_from_widget(
            None, _("Single sided")
        )
        self.buttons.set_tooltip_text(_("Source document is single-sided"))
        vboxs.pack_start(self.buttons, True, True, 0)
        self.buttons.connect("clicked", self._do_buttons_clicked, spin_buttoni)

        # Double sided button
        self.buttond = Gtk.RadioButton.new_with_label_from_widget(
            self.buttons, _("Double sided")
        )
        self.buttond.set_tooltip_text(_("Source document is double-sided"))
        vboxs.pack_start(self.buttond, False, False, 0)

        # Facing/reverse page button
        hboxs = Gtk.Box()
        vboxs.pack_start(hboxs, True, True, 0)
        labels = Gtk.Label(label=_("Side to scan"))
        hboxs.pack_start(labels, False, False, 0)
        self.combobs = ComboBoxText()
        for text in (_("Facing"), _("Reverse")):
            self.combobs.append_text(text)
        self.combobs.connect("changed", self._do_side_to_scan_combo_changed)
        self.connect("changed-side-to-scan", self._do_side_to_scan_changed)
        self.combobs.set_tooltip_text(
            _("Sets which side of a double-sided document is scanned")
        )
        self.combobs.set_active(0)

        # Have to do this here because setting the facing combobox switches it
        self.buttons.set_active(True)
        self.num_pages = 1
        hboxs.pack_end(self.combobs, False, False, 0)

        self.buttond.connect("clicked", self._do_buttond_clicked, spin_buttoni)

        # Have to put the extended pagenumber checkbox here
        # to reference simple controls
        self.checkx.connect(
            "notify::active",
            _extended_pagenumber_checkbox_callback,
            [self, spin_buttoni],
        )

    def _do_clicked_scan_all(self, bscanall, _value):
        if bscanall.get_active():
            self.num_pages = 0

    def _do_start_page_changed(self, spin_buttons):
        self.page_number_start = spin_buttons.get_value()
        self.update_start_page()

    def _do_changed_page_number_start(self, _self, value, spin_buttons):
        spin_buttons.set_value(value)
        slist = self.document
        if slist is not None:
            self.max_pages = slist.pages_possible(value, self.page_number_increment)

    def _do_spin_buttoni_value_changed(self, spin_buttoni):
        value = spin_buttoni.get_value()
        if value == 0:
            value = -self.page_number_increment
            spin_buttoni.set_value(value)
            return
        self.page_number_increment = value

    def _do_changed_page_number_increment(self, _self, value, spin_buttoni):
        spin_buttoni.set_value(value)
        slist = self.document
        if slist is not None:
            self.max_pages = slist.pages_possible(self.page_number_start, value)

    def _do_clicked_scan_number(self, bscannum, spin_buttonn):
        if bscannum.get_active():
            self.num_pages = spin_buttonn.get_value()

    def _do_changed_num_pages(self, _self, value, bscanall, bscannum, spin_buttonn):
        if value == 0:
            bscanall.set_active(True)
        else:
            # if spin button is already $value, but pages = all is selected,
            # then the callback will not fire to activate # pages, so doing
            # it here
            bscannum.set_active(True)
            spin_buttonn.set_value(value)

        # Check that there is room in the list for the number of pages
        self._update_num_pages()

    def _do_num_pages_changed(self, spin_buttonn, bscannum):
        "Callback on changing number of pages"
        self.num_pages = spin_buttonn.get_value()
        bscannum.set_active(True)  # Set the radiobutton active

    def _do_buttons_clicked(self, buttons, spin_buttoni):
        spin_buttoni.set_value(1)
        self.sided = "single" if buttons.get_active() == 1 else "double"

    def _do_side_to_scan_combo_changed(self, combobs):
        self.buttond.set_active(True)  # Set the radiobutton active
        self.side_to_scan = "facing" if combobs.get_active() == 0 else "reverse"

    def _do_side_to_scan_changed(self, _self, value):
        if self.sided != "double":
            return
        self.page_number_increment = (
            DOUBLE_INCREMENT if value == "facing" else -DOUBLE_INCREMENT
        )
        if value == "facing":
            self.num_pages = 0

    def _do_buttond_clicked(self, _buttond, spin_buttoni):
        "Have to put the double-sided callback here to reference page side"
        spin_buttoni.set_value(
            DOUBLE_INCREMENT if self.combobs.get_active() == 0 else -DOUBLE_INCREMENT
        )

    def _update_num_pages(self):
        "Update the number of pages to scan spinbutton if necessary"
        slist = self.document
        if slist is None:
            return
        num = slist.pages_possible(self.page_number_start, self.page_number_increment)
        if 0 <= num <= self.max_pages:
            self.num_pages = num

    def update_start_page(self):
        """Called either from changed-value signal of spinbutton,
        or row-changed signal of SimpleList"""
        slist = self.document
        if not slist:
            return
        value = self.page_number_start
        if self._previous_start is None:
            self._previous_start = self.page_number_start
        step = value - self._previous_start
        if step == 0:
            step = self.page_number_increment
        self._previous_start = value
        while slist.pages_possible(value, step) == 0:
            if value < 1:
                value = 1
                step = 1
            else:
                value += step

        self.page_number_start = value
        self._previous_start = value
        self._update_num_pages()

    def reset_start_page(self):
        """Reset start page number after delete or new"""
        slist = self.document
        if slist is None:
            return
        num_pages = len(slist.data)
        if num_pages > 0:
            start_page = self.page_number_start
            step = self.page_number_increment
            if start_page > slist.data[num_pages - 1][0] + step:
                self.page_number_start = len(slist)
        else:
            self.page_number_start = 1

    def _flatbed_or_duplex_callback(self):

        options = self.available_scan_options
        if options is not None and hasattr(self, "thread") and hasattr(self, "_vboxx"):
            if options.flatbed_selected(self.thread.device_handle) or (
                options.can_duplex() and not self.ignore_duplex_capabilities
            ):
                self._vboxx.hide()

            else:
                self._vboxx.show()


def spinbutton_in_hbox(vbox, label, vmin, vmax, step):
    "pack a label and a spinbutton in an hbox"
    hbox = Gtk.Box()
    vbox.pack_start(hbox, False, False, 0)
    hbox.pack_start(Gtk.Label(label=label), False, False, 0)
    spin_button = Gtk.SpinButton.new_with_range(vmin, vmax, step)
    hbox.pack_end(spin_button, False, False, 0)
    return spin_button


def _extended_pagenumber_checkbox_callback(widget, _param, data):
    dialog, spin_buttoni = data
    if widget.get_active():
        dialog.frames.hide()
        dialog.framex.show_all()
    else:
        inc = spin_buttoni.get_value()
        if inc == 1:
            dialog.buttons.set_active(True)
        elif inc > 0:
            dialog.buttond.set_active(True)
            dialog.combobs.set_active(0)
        else:
            dialog.buttond.set_active(True)
            dialog.combobs.set_active(1)

        dialog.frames.show_all()
        dialog.framex.hide()

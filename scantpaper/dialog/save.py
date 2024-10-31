"subclass dialog for save options"

import datetime
import pathlib
import re
from comboboxtext import ComboBoxText
from dialog import Dialog
from entry_completion import EntryCompletion
from i18n import _
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # pylint: disable=wrong-import-position

MAX_DPI = 2400
ENTRY_WIDTH_DATE = 10
ENTRY_WIDTH_DATETIME = 19
IMAGE_TYPES = [
    ("pdf", _("PDF"), _("Portable Document Format")),
    ("gif", _("GIF"), _("CompuServe graphics interchange format")),
    ("jpg", _("JPEG"), _("Joint Photographic Experts Group JFIF format")),
    ("png", _("PNG"), _("Portable Network Graphics")),
    ("pnm", _("PNM"), _("Portable anymap")),
    ("ps", _("PS"), _("Postscript")),
    ("tif", _("TIFF"), _("Tagged Image File Format")),
    ("txt", _("Text"), _("Plain text")),
    ("hocr", _("hOCR"), _("hOCR markup language")),
    ("session", _("Session"), _("gscan2pdf session file")),
    ("prependpdf", _("Prepend to PDF"), _("Prepend to an existing PDF")),
    ("appendpdf", _("Append to PDF"), _("Append to an existing PDF")),
    ("djvu", _("DjVu"), _("Deja Vu")),
]
PDF_COMPRESSION_ALGS = [
    (
        "auto",
        _("Automatic"),
        _("Let gscan2pdf which type of compression to use."),
    ),
    ("lzw", _("LZW"), _("Compress output with Lempel-Ziv & Welch encoding.")),
    ("g3", _("G3"), _("Compress output with CCITT Group 3 encoding.")),
    ("g4", _("G4"), _("Compress output with CCITT Group 4 encoding.")),
    ("png", _("Flate"), _("Compress output with flate encoding.")),
    ("jpg", _("JPEG"), _("Compress output with JPEG (DCT) encoding.")),
    ("none", _("None"), _("Use no compression algorithm on output.")),
]
OCR_POSITIONS = [
    ["behind", _("Behind"), _("Put OCR output behind image.")],
    ["right", _("Right"), _("Put OCR output to the right of the image.")],
]
PS_BACKENDS = [
    (
        "libtiff",
        _("LibTIFF"),
        _("Use LibTIFF (tiff2ps) to create Postscript files from TIFF."),
    ),
    (
        "pdf2ps",
        _("Ghostscript"),
        _("Use Ghostscript (pdf2ps) to create Postscript files from PDF."),
    ),
    (
        "pdftops",
        _("Poppler"),
        _("Use Poppler (pdftops) to create Postscript files from PDF."),
    ),
]
TIFF_COMPRESSION_ALGS = [
    ("lzw", _("LZW"), _("Compress output with Lempel-Ziv & Welch encoding.")),
    (
        "zip",
        _("Zip"),
        _("Compress output with deflate encoding."),
    ),  # jpeg rather than jpg needed here because tiffcp uses -c jpeg
    ("jpeg", _("JPEG"), _("Compress output with JPEG encoding.")),
    ("packbits", _("Packbits"), _("Compress output with Packbits encoding.")),
    ("g3", _("G3"), _("Compress output with CCITT Group 3 encoding.")),
    ("g4", _("G4"), _("Compress output with CCITT Group 4 encoding.")),
    ("none", _("None"), _("Use no compression algorithm on output.")),
]
DATETIME_FORMAT = {
    True: "%Y-%m-%dT%H:%M:%S",
    False: "%Y-%m-%d",
}


class Save(Dialog):
    "subclass dialog for save options"
    _meta_datetime = None
    _meta_datetime_widget = None

    @GObject.Property(type=object)
    def meta_datetime(self):
        "Datetime object for document date"
        if self.meta_now_widget.get_active():
            return datetime.datetime.now()
        return self._meta_datetime

    @meta_datetime.setter
    def meta_datetime(self, newval):
        if newval != self._meta_datetime:
            self._meta_datetime = newval
            if self._meta_datetime_widget is not None:
                self._meta_datetime_widget.set_text(newval.isoformat())

    select_datetime = GObject.Property(
        type=bool,
        default=False,
        nick="Select datetime",
        blurb="TRUE = show datetime entry, FALSE = now/today",
    )
    _include_time = False

    @GObject.Property(type=bool, default=False)
    def include_time(self):
        "Whether to allow the time, as well as the date, to be entered"
        return self._include_time

    @include_time.setter
    def include_time(self, newval):
        if newval != self._include_time:
            self._on_toggle_include_time(newval)
            self._include_time = newval

    _meta_title = None
    _meta_title_suggestions = None
    _meta_title_widget = None

    @GObject.Property(type=str, default="")
    def meta_title(self):
        "Title metadata"
        if self._meta_title_widget is None:
            return self._meta_title
        return self._meta_title_widget.get_text()

    @meta_title.setter
    def meta_title(self, newval):
        self._meta_title = newval
        if self._meta_title_widget is not None:
            self._meta_title_widget.set_text(newval)
            self._meta_title_widget.add_to_suggestions(newval)

    @GObject.Property(type=object)
    def meta_title_suggestions(self):
        "Array of title metadata suggestions, used by entry completion widget"
        if self._meta_title_widget is None:
            return self._meta_title_suggestions
        return self._meta_title_widget.get_suggestions()

    @meta_title_suggestions.setter
    def meta_title_suggestions(self, newval):
        self._meta_title_suggestions = newval
        if self._meta_title_widget is not None:
            self._meta_title_widget.set_suggestions(newval)

    _meta_author = None
    _meta_author_suggestions = None
    _meta_author_widget = None

    @GObject.Property(type=str, default="")
    def meta_author(self):
        "Author metadata"
        if self._meta_author_widget is None:
            return self._meta_author
        return self._meta_author_widget.get_text()

    @meta_author.setter
    def meta_author(self, newval):
        self._meta_author = newval
        if self._meta_author_widget is not None:
            self._meta_author_widget.set_text(newval)
            self._meta_author_widget.add_to_suggestions(newval)

    @GObject.Property(type=object)
    def meta_author_suggestions(self):
        "Array of author metadata suggestions, used by entry completion widget"
        if self._meta_author_widget is None:
            return self._meta_author_suggestions
        return self._meta_author_widget.get_suggestions()

    @meta_author_suggestions.setter
    def meta_author_suggestions(self, newval):
        self._meta_author_suggestions = newval
        if self._meta_author_widget is not None:
            self._meta_author_widget.set_suggestions(newval)

    _meta_subject = None
    _meta_subject_suggestions = None
    _meta_subject_widget = None

    @GObject.Property(type=str, default="")
    def meta_subject(self):
        "Subject metadata"
        if self._meta_subject_widget is None:
            return self._meta_subject
        return self._meta_subject_widget.get_text()

    @meta_subject.setter
    def meta_subject(self, newval):
        self._meta_subject = newval
        if self._meta_subject_widget is not None:
            self._meta_subject_widget.set_text(newval)
            self._meta_subject_widget.add_to_suggestions(newval)

    @GObject.Property(type=object)
    def meta_subject_suggestions(self):
        "Array of subject metadata suggestions, used by entry completion widget"
        if self._meta_subject_widget is None:
            return self._meta_subject_suggestions
        return self._meta_subject_widget.get_suggestions()

    @meta_subject_suggestions.setter
    def meta_subject_suggestions(self, newval):
        self._meta_subject_suggestions = newval
        if self._meta_subject_widget is not None:
            self._meta_subject_widget.set_suggestions(newval)

    _meta_keywords = None
    _meta_keywords_suggestions = None
    _meta_keywords_widget = None

    @GObject.Property(type=str, default="")
    def meta_keywords(self):
        "Keyword metadata"
        if self._meta_keywords_widget is None:
            return self._meta_keywords
        return self._meta_keywords_widget.get_text()

    @meta_keywords.setter
    def meta_keywords(self, newval):
        self._meta_keywords = newval
        if self._meta_keywords_widget is not None:
            self._meta_keywords_widget.set_text(newval)
            self._meta_keywords_widget.add_to_suggestions(newval)

    @GObject.Property(type=object)
    def meta_keywords_suggestions(self):
        "Array of keyword metadata suggestions, used by entry completion widget"
        if self._meta_keywords_widget is None:
            return self._meta_keywords_suggestions
        return self._meta_keywords_widget.get_suggestions()

    @meta_keywords_suggestions.setter
    def meta_keywords_suggestions(self, newval):
        self._meta_keywords_suggestions = newval
        if self._meta_keywords_widget is not None:
            self._meta_keywords_widget.set_suggestions(newval)

    image_types = GObject.Property(
        type=object,
        nick="Array of available image types",
        blurb="To allow djvu, pdfunite dependencies to be optional",
    )
    image_type = GObject.Property(
        type=str,
        default="pdf",
        nick="Image type",
        blurb="Currently selected image type",
    )
    ps_backends = GObject.Property(
        type=object, nick="PS backends", blurb="Array of available postscript backends"
    )
    ps_backend = GObject.Property(
        type=str,
        default="pdftops",
        nick="PS backend",
        blurb="Currently selected postscript backend",
    )
    tiff_compression = GObject.Property(
        type=str,
        default=None,
        nick="TIFF compression",
        blurb="Currently selected TIFF compression method",
    )
    jpeg_quality = GObject.Property(
        type=float,
        minimum=1,
        maximum=100,
        default=75,
        nick="JPEG quality",
        blurb="Affects the compression level of JPEG encoding",
    )
    downsample_dpi = GObject.Property(
        type=float,
        minimum=1,
        maximum=MAX_DPI,
        default=150,
        nick="Downsample DPI",
        blurb="Resolution to use when downsampling",
    )
    downsample = GObject.Property(
        type=bool, default=False, nick="Downsample", blurb="Whether to downsample"
    )
    pdf_compression = GObject.Property(
        type=str,
        default="auto",
        nick="PDF compression",
        blurb="Currently selected PDF compression method",
    )
    available_fonts = GObject.Property(
        type=object, nick="Available fonts", blurb="Dict of true type fonts available"
    )
    text_position = GObject.Property(
        type=str,
        default="behind",
        nick="Text position",
        blurb="Where to place the OCR output",
    )
    pdf_font = GObject.Property(
        type=str,
        default=None,
        nick="PDF font",
        blurb="Font with which to write hidden OCR layer of PDF",
    )
    can_encrypt_pdf = GObject.Property(
        type=bool,
        default=False,
        nick="Can encrypt PDF",
        blurb="Backend is capable of encrypting the PDF",
    )
    pdf_user_password = GObject.Property(
        type=str, default=None, nick="PDF user password", blurb="PDF user password"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        box = self.get_content_area()

        # it needs its own box to be able to hide it if necessary
        self._meta_box_widget = Gtk.HBox()
        box.pack_start(self._meta_box_widget, False, False, 0)

        # Frame for metadata
        frame = Gtk.Frame(label=_("Document Metadata"))
        self._meta_box_widget.pack_start(frame, True, True, 0)
        box = Gtk.VBox()
        box.set_border_width(
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        frame.add(box)

        # grid to align widgets
        grid = Gtk.Grid()
        row = 0
        box.pack_start(grid, True, True, 0)

        # Date/time
        frame = Gtk.Frame(label=_("Date/Time"))
        grid.attach(frame, 0, row, 2, 1)
        row += 1
        frame.set_hexpand(True)
        vboxdt = Gtk.VBox()
        vboxdt.set_border_width(
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        frame.add(vboxdt)

        # the first radio button has to set the group,
        # which is undef for the first button
        # Now button
        self.meta_now_widget = Gtk.RadioButton.new_with_label(None, _("Now"))
        self.meta_now_widget.set_tooltip_text(_("Use current date and time"))
        vboxdt.pack_start(self.meta_now_widget, True, True, 0)

        # Specify button
        bspecify_dt = Gtk.RadioButton.new_with_label_from_widget(
            self.meta_now_widget, _("Specify")
        )
        bspecify_dt.set_tooltip_text(_("Specify date and time"))
        vboxdt.pack_start(bspecify_dt, True, True, 0)
        hboxe = Gtk.HBox()
        bspecify_dt.connect("clicked", self._clicked_specify_date_button, hboxe)
        self._meta_datetime_widget = Gtk.Entry()
        if self.meta_datetime is not None and self.meta_datetime != "":
            self._meta_datetime_widget.set_text(self.meta_datetime.isoformat())

        self._meta_datetime_widget.set_activates_default(True)
        self._meta_datetime_widget.set_tooltip_text(_("Year-Month-Day"))
        self._meta_datetime_widget.set_alignment(1.0)  # Right justify
        self._meta_datetime_widget.connect("insert-text", self._insert_text_handler)
        self._meta_datetime_widget.connect(
            "focus-out-event", self._datetime_focus_out_callback
        )
        icon = Gtk.Image.new_from_icon_name("document-edit", Gtk.IconSize.BUTTON)
        button = Gtk.Button()
        button.set_image(icon)
        button.connect("clicked", self._clicked_edit_date_button)
        button.set_tooltip_text(_("Select date with calendar"))
        vboxdt.pack_start(hboxe, True, True, 0)
        hboxe.pack_end(button, False, False, 0)
        hboxe.pack_end(self._meta_datetime_widget, False, False, 0)

        # Don't show these widgets when the window is shown
        hboxe.set_no_show_all(True)
        self._meta_datetime_widget.show()
        button.show()
        bspecify_dt.set_active(self.select_datetime)
        self._add_metadata_widgets(grid, row)

        self._on_toggle_include_time(self.include_time)

    def _clicked_specify_date_button(self, widget, hboxe):
        if widget.get_active():
            hboxe.show()
            self.select_datetime = True
        else:
            hboxe.hide()
            self.select_datetime = False

    def _datetime_focus_out_callback(self, entry_widget, _event):
        text = entry_widget.get_text()
        if text is not None:
            self.meta_datetime = datetime.datetime.strptime(
                text, DATETIME_FORMAT[self._include_time]
            )
        return False

    def _clicked_edit_date_button(self, _widget):
        window_date = Dialog(
            transient_for=self,
            title=_("Select Date"),
        )
        vbox_date = window_date.get_content_area()
        window_date.set_resizable(False)
        calendar = Gtk.Calendar()

        # Editing the entry and clicking the edit button bypasses the
        # focus-out-event, so update the date now
        self.meta_datetime = datetime.datetime.strptime(
            self._meta_datetime_widget.get_text(), DATETIME_FORMAT[self._include_time]
        )
        calendar.select_day(self.meta_datetime.day)
        calendar.select_month(self.meta_datetime.month - 1, self.meta_datetime.year)
        calendar_s = None

        def calendar_day_selected_callback(_widget):
            year, month, day = calendar.get_date()
            self.meta_datetime = datetime.datetime(year, month + 1, day)

        calendar_s = calendar.connect("day-selected", calendar_day_selected_callback)

        def calendar_day_selected_double_click_callback(widget):
            calendar_day_selected_callback(widget)
            window_date.destroy()

        calendar.connect(
            "day-selected-double-click", calendar_day_selected_double_click_callback
        )
        vbox_date.pack_start(calendar, True, True, 0)
        today_b = Gtk.Button(_("Today"))

        def today_clicked_callback(_widget):
            today = datetime.date.today()

            # block and unblock signal, and update entry manually
            # to remove possibility of race conditions
            calendar.handler_block(calendar_s)
            calendar.select_day(today.day)
            calendar.select_month(today.month - 1, today.year)
            calendar.handler_unblock(calendar_s)
            self._meta_datetime_widget.set_text(today.isoformat())

        today_b.connect("clicked", today_clicked_callback)
        vbox_date.pack_start(today_b, True, True, 0)
        window_date.show_all()

    def _insert_text_handler(self, widget, string, _length, position):
        text = widget.get_text()
        text_len = len(text)
        widget.handler_block_by_func(self._insert_text_handler)

        # trap + & - for incrementing and decrementing date
        if (
            (not self.include_time and text_len == ENTRY_WIDTH_DATE)
            or (self.include_time and text_len == ENTRY_WIDTH_DATETIME)
        ) and string in ["+", "-"]:
            day_offset = 1
            if string == "-":
                day_offset = -day_offset
            date = datetime.datetime.strptime(
                text, DATETIME_FORMAT[self._include_time]
            ) + datetime.timedelta(days=day_offset)
            widget.set_text(date.isoformat())
        # only allow integers and -
        elif not self.include_time and re.search(
            r"^[\d\-]+$", string, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            widget.insert_text(string, position)
            position += 1

        widget.handler_unblock_by_func(self._insert_text_handler)
        widget.stop_emission_by_name("insert-text")
        return position

    def _add_metadata_widgets(self, grid, row):
        for name, label in [
            ("title", _("Title")),
            ("author", _("Author")),
            ("subject", _("Subject")),
            ("keywords", _("Keywords")),
        ]:
            hbox = Gtk.HBox()
            grid.attach(hbox, 0, row, 1, 1)
            label = Gtk.Label(label=label)
            hbox.pack_start(label, False, True, 0)
            hbox = Gtk.HBox()
            grid.attach(hbox, 1, row, 1, 1)
            row += 1
            setattr(
                self,
                f"meta_{name}_widget",
                EntryCompletion(
                    getattr(self, f"meta_{name}"),
                    getattr(self, f"meta_{name}_suggestions"),
                ),
            )
            hbox.pack_start(getattr(self, f"meta_{name}_widget"), True, True, 0)

    def _on_toggle_include_time(self, newval):
        if hasattr(self, "_meta_box_widget"):
            if newval:
                self.meta_now_widget.get_child().set_text(_("Now"))
                self.meta_now_widget.set_tooltip_text(_("Use current date and time"))
                self._meta_datetime_widget.set_max_length(ENTRY_WIDTH_DATETIME)
                self._meta_datetime_widget.set_text(
                    self._meta_datetime_widget.get_text() + " 00:00:00"
                )
            else:
                self.meta_now_widget.get_child().set_text(_("Today"))
                self.meta_now_widget.set_tooltip_text(_("Use today's date"))
                self._meta_datetime_widget.set_max_length(ENTRY_WIDTH_DATE)

    def add_image_type(self):
        "add image type dropdown"
        vbox = self.get_content_area()

        # Image type ComboBox
        hboxi = Gtk.HBox()
        vbox.pack_start(hboxi, False, False, 0)
        label = Gtk.Label(label=_("Document type"))
        hboxi.pack_start(label, False, False, 0)
        combobi = ComboBoxText(data=filter_table(IMAGE_TYPES, self.image_types))
        hboxi.pack_end(combobi, False, False, 0)

        # Postscript backend
        hboxps = Gtk.HBox()
        vbox.pack_start(hboxps, True, True, 0)
        label = Gtk.Label(label=_("Postscript backend"))
        hboxps.pack_start(label, False, False, 0)
        combops = ComboBoxText(data=filter_table(PS_BACKENDS, self.ps_backends))

        def ps_backend_changed_callback(_widget):
            self.ps_backend = combops.get_active_index()

        combops.connect("changed", ps_backend_changed_callback)
        combops.set_active_index(
            "pdftops" if self.ps_backend is None else self.ps_backend
        )
        hboxps.pack_end(combops, True, True, 0)

        # Compression ComboBox
        hboxc = Gtk.HBox()
        vbox.pack_start(hboxc, False, False, 0)
        label = Gtk.Label(label=_("Compression"))
        hboxc.pack_start(label, False, False, 0)

        # Set up quality spinbutton here
        # so that it can be shown or hidden by callback
        hboxtq, _spinbuttontq = self.add_quality_spinbutton(vbox)

        # Fill compression ComboBox
        combobtc = ComboBoxText(data=TIFF_COMPRESSION_ALGS)

        def tiff_compression_changed_callback(_widget):
            self.tiff_compression = combobtc.get_active_index()
            if self.tiff_compression == "jpeg":
                hboxtq.show()
            else:
                hboxtq.hide()
                self.resize(1, 1)

        combobtc.connect("changed", tiff_compression_changed_callback)
        combobtc.set_active_index(self.tiff_compression)
        hboxc.pack_end(combobtc, False, False, 0)

        # PDF options
        vboxp, hboxpq = self.add_pdf_options()
        combobi.connect(
            "changed",
            self._image_type_changed_callback,
            [
                vboxp,
                hboxpq,
                hboxc,
                hboxtq,
                hboxps,
            ],
        )
        self.show_all()
        hboxc.set_no_show_all(True)
        hboxtq.set_no_show_all(True)
        hboxps.set_no_show_all(True)
        combobi.set_active_index(self.image_type)

    def _image_type_changed_callback(self, widget, data):
        (
            vboxp,
            hboxpq,
            hboxc,
            hboxtq,
            hboxps,
        ) = data
        self.image_type = widget.get_active_index()
        if re.search(r"pdf", self.image_type):
            self._pdf_selected_callback(data)
        elif self.image_type == "djvu":
            self._meta_box_widget.show()
            hboxc.hide()
            vboxp.hide()
            hboxpq.hide()
            hboxtq.hide()
            hboxps.hide()
        elif self.image_type == "tif":
            hboxc.show()
            self._meta_box_widget.hide()
            vboxp.hide()
            hboxpq.hide()
            if self.tiff_compression == "jpeg":
                hboxtq.show()
            else:
                hboxtq.hide()
            hboxps.hide()
        elif self.image_type == "ps":
            hboxc.hide()
            self._meta_box_widget.hide()
            vboxp.hide()
            hboxpq.hide()
            hboxtq.hide()
            hboxps.show()
        elif self.image_type == "jpg":
            self._meta_box_widget.hide()
            hboxc.hide()
            vboxp.hide()
            hboxpq.hide()
            hboxtq.show()
            hboxps.hide()
        else:
            self._meta_box_widget.hide()
            vboxp.hide()
            hboxc.hide()
            hboxpq.hide()
            hboxtq.hide()
            hboxps.hide()

        self.resize(1, 1)

    def _pdf_selected_callback(self, data):
        (
            vboxp,
            hboxpq,
            hboxc,
            hboxtq,
            hboxps,
        ) = data
        vboxp.show()
        hboxc.hide()
        hboxtq.hide()
        hboxps.hide()
        if self.image_type == "pdf":
            self._meta_box_widget.show()
        else:  # don't show metadata for pre-/append to pdf
            self._meta_box_widget.hide()

        if self.pdf_compression == "jpg":
            hboxpq.show()
        else:
            hboxpq.hide()

    def add_quality_spinbutton(self, vbox):
        """Set up quality spinbutton here so that it can be shown or hidden by callback"""
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("JPEG Quality"))
        hbox.pack_start(label, False, False, 0)
        spinbutton = Gtk.SpinButton.new_with_range(1, 100, 1)
        spinbutton.set_value(self.jpeg_quality)
        hbox.pack_end(spinbutton, False, False, 0)
        return hbox, spinbutton

    def add_pdf_options(self):
        "add pdf options"
        # pack everything in one vbox to be able to show/hide them all at once
        vboxp = Gtk.VBox()
        vbox = self.get_content_area()
        vbox.pack_start(vboxp, False, False, 0)

        self._add_pdf_downsample_options(vboxp)

        # Compression ComboBox
        hbox = Gtk.HBox()
        vboxp.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Compression"))
        hbox.pack_start(label, False, False, 0)

        # Set up quality spinbutton here so that it can be shown or hidden by callback
        hboxq, spinbuttonq = self.add_quality_spinbutton(vboxp)
        combob = ComboBoxText(data=PDF_COMPRESSION_ALGS)
        combob.connect("changed", self._pdf_compression_changed_callback, hboxq)

        def jpg_quality_changed_callback(_widget):
            self.jpeg_quality = spinbuttonq.get_value()

        spinbuttonq.connect("value-changed", jpg_quality_changed_callback)
        hbox.pack_end(combob, False, False, 0)
        hbox = Gtk.HBox()
        vboxp.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Position of OCR output"))
        hbox.pack_start(label, False, False, 0)
        combot = ComboBoxText(data=OCR_POSITIONS)

        def ocr_position_changed_callback(_widget):
            self.text_position = combot.get_active_index()

        combot.connect("changed", ocr_position_changed_callback)
        combot.set_active_index(self.text_position)
        hbox.pack_end(combot, False, False, 0)
        self.add_font_button(vboxp)
        if self.can_encrypt_pdf:
            passb = Gtk.Button(_("Encrypt PDF"))
            vboxp.pack_start(passb, True, True, 0)
            passb.connect("clicked", self._encrypt_clicked_callback)

        vboxp.show_all()
        hboxq.set_no_show_all(True)
        vboxp.set_no_show_all(True)

        # do this after show all and set_no_show_all
        # to make sure child widgets are shown.
        combob.set_active_index(self.pdf_compression)
        return vboxp, hboxq

    def _add_pdf_downsample_options(self, vboxp):
        hbox = Gtk.HBox()
        vboxp.pack_start(hbox, False, False, 0)
        button = Gtk.CheckButton(label=_("Downsample to"))
        hbox.pack_start(button, False, False, 0)
        spinbutton = Gtk.SpinButton.new_with_range(1, MAX_DPI, 1)
        spinbutton.set_value(self.downsample_dpi)
        label = Gtk.Label(label=_("PPI"))
        hbox.pack_end(label, False, False, 0)
        hbox.pack_end(spinbutton, False, False, 0)

        def downsample_toggled_callback(_widget):
            self.downsample = button.get_active()
            spinbutton.set_sensitive(self.downsample)

        button.connect("toggled", downsample_toggled_callback)

        def downsample_dpi_changed_callback():
            self.downsample_dpi = spinbutton.get_value()

        spinbutton.connect("value-changed", downsample_dpi_changed_callback)
        spinbutton.set_sensitive(self.downsample)
        button.set_active(self.downsample)

    def _pdf_compression_changed_callback(self, widget, hboxq):
        self.pdf_compression = widget.get_active_index()
        if self.pdf_compression == "jpg":
            hboxq.show()
        else:
            hboxq.hide()
            self.resize(1, 1)

    def _encrypt_clicked_callback(self, _widget):
        passwin = Dialog(
            transient_for=self,
            title=_("Set password"),
        )
        passwin.set_modal(True)
        passvbox = passwin.get_content_area()
        grid = Gtk.Grid()
        row = 0
        passvbox.pack_start(grid, True, True, 0)
        hbox = Gtk.HBox()
        label = Gtk.Label(label=_("User password"))
        hbox.pack_start(label, False, False, 0)
        grid.attach(hbox, 0, row, 1, 1)
        userentry = Gtk.Entry()
        if self.pdf_user_password:
            userentry.set_text(self.pdf_user_password)

        grid.attach(userentry, 1, row, 1, 1)
        row += 1

        def clicked_ok_callback(_widget):
            self.pdf_user_password = userentry.get_text()
            passwin.destroy()

        def clicked_cancel_callback(_widget):
            passwin.destroy()

        passwin.add_actions(
            [
                ("gtk-ok", clicked_ok_callback),
                ("gtk-cancel", clicked_cancel_callback),
            ]
        )
        passwin.show_all()

    def add_font_button(self, vboxp):
        "add font button"
        # It would be nice to use a Gtk3::FontButton here, but as we can only use
        # TTF, and we have to know the filename of the font, we must filter the
        # list of fonts, and so we must use a Gtk3::FontChooserDialog
        hboxf = Gtk.HBox()
        vboxp.pack_start(hboxf, True, True, 0)
        label = Gtk.Label(label=_("Font for non-ASCII text"))
        hboxf.pack_start(label, False, False, 0)
        fontb = Gtk.Button(label="Font name goes here")
        hboxf.pack_end(fontb, False, True, 0)
        if (
            self.pdf_font is None or not pathlib.Path(self.pdf_font).exists()
        ) and self.available_fonts is not None:
            self.pdf_font = list(self.available_fonts["by_file"].keys())[0]

        if (
            self.pdf_font is not None
            and self.available_fonts is not None
            and self.pdf_font in self.available_fonts["by_file"]
        ):
            family, style = self.available_fonts["by_file"][self.pdf_font]
            fontb.set_label(f"{family} {style}")

        else:
            fontb.set_label(_("Core"))

        def font_clicked_callback(_widget):
            fontwin = Gtk.FontChooserDialog(
                transient_for=self,
            )

            def font_filter_func(family, face):

                family = family.get_name()
                face = face.get_face_name()
                if (
                    family in self.available_fonts["by_family"]
                    and face in self.available_fonts["by_family"][family]
                ):
                    return True
                return False

            fontwin.set_filter_func(font_filter_func)
            if (
                self.pdf_font is not None
                and self.available_fonts is not None
                and self.pdf_font in self.available_fonts["by_file"]
            ):
                family, style = self.available_fonts["by_file"][self.pdf_font]
                font = family
                if style is not None and style != "":
                    font += f" {style}"

                fontwin.set_font(font)

            fontwin.show_all()
            if fontwin.run() == "ok":
                family = fontwin.get_font_family().get_name()
                face = fontwin.get_font_face().get_face_name()
                if (
                    family in self.available_fonts["by_family"]
                    and face in self.available_fonts["by_family"][family]
                ):

                    # also set local variable as a sort of cache
                    self.pdf_font = self.available_fonts["by_family"][family][face]
                    fontb.set_label(f"{family} {face}")

            fontwin.destroy()

        fontb.connect("clicked", font_clicked_callback)


def filter_table(table, types):
    "filter table list by types"
    sub_table = []
    for row in table:
        if row[0] in types:
            sub_table.append(row)
    return sub_table

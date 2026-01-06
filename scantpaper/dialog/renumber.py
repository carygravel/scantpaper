"Renumber dialog"

import logging
import gi
from dialog import Dialog
from pagerange import PageRange
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position

_MAX_PAGES = 9999
_MAX_INCREMENT = 99

logger = logging.getLogger(__name__)


class Renumber(Dialog):
    "Renumber dialog"

    __gsignals__ = {
        "changed-start": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "changed-increment": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "changed-document": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "changed-range": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "before-renumber": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    _start = 1

    @GObject.Property(
        type=int,
        minimum=1,
        maximum=999,
        default=1,
        nick="Number of first page",
        blurb="Number of first page",
    )
    def start(self):  # pylint: disable=method-hidden
        "getter for start attribute"
        return self._start

    @start.setter
    def start(self, newval):
        if newval == self._start:
            return
        self._start = newval
        self.emit("changed-start", newval)

    _increment = 1

    @GObject.Property(
        type=int,
        minimum=-99,
        maximum=99,
        default=1,
        nick="Increment",
        blurb="Amount to increment page number when renumbering multiple pages",
    )
    def increment(self):  # pylint: disable=method-hidden
        "getter for increment attribute"
        return self._increment

    @increment.setter
    def increment(self, newval):
        if newval == self._increment:
            return
        self._increment = newval
        self.emit("changed-increment", newval)

    _document = None

    @GObject.Property(type=object, nick="Document", blurb="Document object to renumber")
    def document(self):
        "getter for document attribute"
        return self._document

    @document.setter
    def document(self, newval):
        if newval == self._document:
            return
        self._document = newval
        self.emit("changed-document", newval)

    _range = "selected"

    @GObject.Property(
        type=str,
        default="selected",
        nick="Page Range to renumber",
        blurb="Page Range to renumber",
    )
    def range(self):  # pylint: disable=method-hidden
        "getter for range attribute"
        return self._range

    @range.setter
    def range(self, newval):
        if newval == self._range:
            return
        self._range = newval
        self.emit("changed-range", newval)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(_("Renumber"))
        self._start_old = None
        self._step_old = None
        self._row_signal = None
        self._selection_signal = None
        vbox = self.get_content_area()

        # Frame for page range
        frame = Gtk.Frame(label=_("Page Range"))
        vbox.pack_start(frame, False, False, 0)
        pr = PageRange()
        pr.connect("changed", self._page_range_changed_callback)
        self.connect("changed-range", lambda widget, value: pr.set_active(value))
        pr.set_active(self.range)
        frame.add(pr)

        # Frame for page numbering
        framex = Gtk.Frame(label=_("Page numbering"))
        vbox.pack_start(framex, False, False, 0)
        vboxx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        border_width = (
            self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left
        )  # ._get('content-area-border')
        vboxx.set_border_width(border_width)
        framex.add(vboxx)

        # SpinButton for starting page number
        hboxxs = Gtk.Box()
        vboxx.pack_start(hboxxs, False, False, 0)
        labelxs = Gtk.Label(label=_("Start"))
        hboxxs.pack_start(labelxs, False, False, 0)
        spin_buttons = Gtk.SpinButton.new_with_range(1, _MAX_PAGES, 1)
        spin_buttons.connect("value-changed", self._start_changed_callback)
        self.connect(
            "changed-start", lambda widget, value: spin_buttons.set_value(value)
        )
        spin_buttons.set_value(self.start)
        hboxxs.pack_end(spin_buttons, False, False, 0)

        # SpinButton for page number increment
        hboxi = Gtk.Box()
        vboxx.pack_start(hboxi, False, False, 0)
        labelxi = Gtk.Label(label=_("Increment"))
        hboxi.pack_start(labelxi, False, False, 0)
        spin_buttoni = Gtk.SpinButton.new_with_range(-_MAX_INCREMENT, _MAX_INCREMENT, 1)
        spin_buttoni.connect("value-changed", self._increment_changed_callback)
        self.connect(
            "changed-increment", lambda widget, value: spin_buttoni.set_value(value)
        )
        spin_buttoni.set_value(self.increment)
        hboxi.pack_end(spin_buttoni, False, False, 0)

        # Check whether the settings are possible
        self.connect("changed-document", self._changed_document_callback)

        self.add_actions([(_("Renumber"), self.renumber), ("gtk-close", self.hide)])

    def _page_range_changed_callback(self, _pr, rng):
        self.range = rng
        self.update()

    def _start_changed_callback(self, spin_buttons):
        self.start = spin_buttons.get_value()
        self.update()

    def _increment_changed_callback(self, spin_buttoni):
        self.increment = spin_buttoni.get_value()
        self.update()

    def _changed_document_callback(self, *_args):
        if self._row_signal is not None and self.document is not None:
            self.document.disconnect(self._row_signal)

        if self._selection_signal is not None and self.document is not None:
            self.document.disconnect(self._selection_signal)

        self.update()

        self._row_signal = self.document.get_model().connect(
            "row-changed", lambda x, y, z: self.update()
        )
        self._selection_signal = self.document.get_selection().connect(
            "changed", lambda x: self.update()
        )

    def update(self):
        """Helper function to prevent impossible settings in renumber dialog"""
        start = self.start
        step = self.increment
        dstart = start - self._start_old if self._start_old is not None else 0
        dstep = step - self._step_old if self._step_old is not None else 0
        if dstart == 0 and dstep == 0:
            dstart = 1

        elif dstart != 0 and dstep != 0:
            dstep = 0

        # Check for clash with non_selected

        slist = self.document
        if slist is not None:
            while not slist.valid_renumber(start, step, self.range):
                n = None
                if self.range == "all":
                    n = len(slist.data) - 1
                else:
                    page = slist.get_selected_indices()
                    n = len(page) - 1

                if start + step * n < 1:
                    if dstart < 0:
                        dstart = 1

                    else:
                        dstep = 1

                start += dstart
                step += dstep
                if step == 0:
                    step += dstep

            self.start = start
            self.increment = step

        self._start_old = start
        self._step_old = step

    def renumber(self):
        "renumber the document based on the values from the dialog"
        slist = self.document
        if slist.valid_renumber(self.start, self.increment, self.range):
            self.emit("before-renumber")
            if slist.row_changed_signal:
                slist.get_model().handler_block(slist.row_changed_signal)

            slist.renumber(self.start, self.increment, self.range)

            # Note selection before sorting
            pages = slist.get_selected_indices()

            # Convert to page numbers
            pages = [slist.data[idx][0] for idx in pages]

            # Block selection_changed_signal to prevent its firing changing pagerange to all
            if slist.selection_changed_signal:
                slist.get_selection().handler_block(slist.selection_changed_signal)

            # Select new page, deselecting others. This fires the select callback,
            # displaying the page
            slist.get_selection().unselect_all()
            slist._manual_sort_by_column(0)
            if slist.selection_changed_signal:
                slist.get_selection().handler_unblock(slist.selection_changed_signal)

            if slist.row_changed_signal:
                slist.get_model().handler_unblock(slist.row_changed_signal)

            # Convert back to indices
            for i, page in enumerate(pages):

                # Due to the sort, must search for new page
                idx = 0
                while idx < len(slist.data) - 1 and slist.data[idx][0] != page:
                    idx += 1

                pages[i] = idx

            # Reselect pages
            slist.select(pages)

        else:
            msg = _(
                "The current settings would result in duplicate page numbers."
                " Please select new start and increment values."
            )
            logger.error(msg)
            self.emit("error", msg)

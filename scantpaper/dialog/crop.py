"The crop dialog"

from gi.repository import Gtk, Gdk, GObject
from dialog import Dialog
from i18n import _

LAYOUT = [
    [
        "x",
        _("x"),
        _("The x-position of the left hand edge of the crop."),
    ],
    [
        "y",
        _("y"),
        _("The y-position of the top edge of the crop."),
    ],
    [
        "width",
        _("Width"),
        _("The width of the crop."),
    ],
    [
        "height",
        _("Height"),
        _("The height of the crop."),
    ],
]


class Crop(Dialog):
    "The crop dialog"

    __gsignals__ = {
        "changed-selection": (GObject.SignalFlags.RUN_FIRST, None, (Gdk.Rectangle,)),
    }

    @GObject.Property(
        type=Gdk.Rectangle,
        nick="Selection",
        blurb="Current selection",
    )
    def selection(self):  # pylint: disable=method-hidden
        "getter for selection attribute"
        return self._selection

    @selection.setter
    def selection(self, newval):
        if newval == self._selection:
            return
        for row in LAYOUT:
            dim = row[0]
            val = getattr(newval, dim)
            getattr(self, f"_sb_{dim}").set_value(val)
        self._selection = newval

    @GObject.Property(
        type=int,
        minimum=0,
        maximum=99999,
        default=0,
        nick="Page width",
        blurb="Width of current page in pixels",
    )
    def page_width(self):
        "getter for page_width attribute"
        return self._page_width

    @page_width.setter
    def page_width(self, newval):
        if newval == self._page_width:
            return
        self._update_sb_range("x")
        self._update_sb_range("width")
        self._page_width = newval

    @GObject.Property(
        type=int,
        minimum=0,
        maximum=99999,
        default=0,
        nick="Page height",
        blurb="Height of current page in pixels",
    )
    def page_height(self):
        "getter for page_width attribute"
        return self._page_height

    @page_height.setter
    def page_height(self, newval):
        if newval == self._page_height:
            return
        self._update_sb_range("y")
        self._update_sb_range("height")
        self._page_height = newval

    def __init__(self, *args, **kwargs):
        kwargs["title"] = _("Crop")
        kwargs["hide_on_delete"] = True
        self._selection = Gdk.Rectangle()
        self._page_width = 0
        self._page_height = 0
        super().__init__(*args, **kwargs)

        # Frame for page range
        self.add_page_range()

        # grid for layout
        grid = Gtk.Grid()
        vbox = self.get_content_area()
        vbox.pack_start(grid, True, True, 0)
        for i, row in enumerate(LAYOUT):
            hbox = Gtk.Box()
            label = Gtk.Label(label=row[1])
            grid.attach(hbox, 1, i, 1, 1)
            hbox.pack_start(label, False, True, 0)
            hbox = Gtk.Box()

            dim = row[0]
            attr_name = f"_sb_{dim}"
            widget = Gtk.SpinButton.new_with_range(
                0,
                getattr(
                    self, "page_" + ("width" if dim in ("x", "width") else "height")
                ),
                1,
            )
            setattr(self, attr_name, widget)
            widget.connect("value-changed", self.on_sb_selector_value_changed, dim)
            hbox.pack_end(widget, True, True, 0)

            grid.attach(hbox, 2, i, 1, 1)
            hbox = Gtk.Box()
            grid.attach(hbox, 3, i, 1, 1)
            label = Gtk.Label(label=_("pixels"))
            hbox.pack_start(label, False, True, 0)
            widget.set_tooltip_text(row[2])

    def on_sb_selector_value_changed(self, widget, dimension):
        "update selection when spinbutton changes"
        if self.selection is None:
            self.selection = Gdk.Rectangle()
        setattr(self.selection, dimension, widget.get_value())
        self._update_sb_range(dimension)
        self.emit("changed-selection", self.selection)

    def _update_sb_range(self, dimension):
        pagedim = "page_" + ("width" if dimension in ("x", "width") else "height")
        otherattr = {"x": "width", "y": "height", "width": "x", "height": "y"}[
            dimension
        ]
        if hasattr(self, f"_sb_{otherattr}"):  # spinbuttons created after properties
            getattr(self, f"_sb_{otherattr}").set_range(
                0, getattr(self, pagedim) - getattr(self.selection, dimension)
            )

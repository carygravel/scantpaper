"print dialog"

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # pylint: disable=wrong-import-position


class PrintOperation(Gtk.PrintOperation):
    "print dialog"

    def __init__(self, *_args, **kwargs):
        super().__init__()
        if kwargs["settings"] is not None:
            self.set_print_settings(kwargs["settings"])
        self.slist = kwargs["slist"]
        self.connect("begin-print", self.begin_print_callback)
        # FIXME: check print preview works for pages with ratios other than 1.
        self.connect("draw-page", self.draw_page_callback)

    def begin_print_callback(self, _self, _context):
        "begin print"
        settings = self.get_print_settings()
        pages = settings.get_print_pages()
        page_list = []
        if pages == Gtk.PrintPages.RANGES:
            page_set = set()
            ranges = settings.get_page_ranges()
            for r in ranges:
                for i in range(r.start + 1, r.end + 1):
                    page_set.add(i)

            for i, row in enumerate(self.slist.data):
                if row[0] in page_set:
                    page_list.append(i)
        else:
            page_list = [range(len(self.slist.data))]

        self.set_n_pages(len(page_list))

    def draw_page_callback(self, _self, context, page_number):
        "draw page"
        page = self.slist.data[page_number][2]
        cr = context.get_cairo_context()

        # Context dimensions
        pwidth = context.get_width()
        pheight = context.get_height()

        # Image dimensions
        pixbuf = page.get_pixbuf()
        xresolution, yresolution, _units = page.resolution
        ratio = xresolution / yresolution
        iwidth = pixbuf.get_width()
        iheight = pixbuf.get_height()

        # Scale context to fit image
        scale = pwidth / iwidth * ratio
        scale = min(scale, pheight / iheight)
        cr.scale(scale / ratio, scale)

        # Set source pixbuf
        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)

        # Paint
        cr.paint()

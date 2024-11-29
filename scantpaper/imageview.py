""" Image viewer widget that can zoom, pan, select """

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk, GObject


class Tool:
    """Base tool class for Dragger, Selector & DraggerSelector"""

    dragging = False
    drag_start = {"x": None, "y": None}

    def __init__(self, view):
        self._view = view

    def view(self):
        """Base view() method"""
        return self._view

    def button_pressed(self, _event):
        """Base button_pressed() method"""
        return False

    def button_released(self, _event):
        """Base button_released() method"""
        return False

    def motion(self, _event):
        """Base motion() method"""

    def cursor_at_point(self, ptx, pty):
        """Returns the name of the cursor at the specified coords"""
        display = Gdk.Display.get_default()
        cursor_type = (  # pylint: disable=assignment-from-no-return
            self.cursor_type_at_point(ptx, pty)
        )
        if cursor_type is not None:
            return Gdk.Cursor.new_from_name(display, cursor_type)
        return None

    def cursor_type_at_point(self, _x, _y) -> str:
        """Base cursor_type_at_point() method"""

    def connect(self, *args):
        """Base connect() method"""
        return self.view().connect(*args)

    def disconnect(self, *args):
        """Base disconnect() method"""
        return self.view().disconnect(*args)


class Dragger(Tool):
    """Tool to drag (pan) the image"""

    dnd_start = {"x": None, "y": None}
    dnd_eligible = False
    button = 1

    def button_pressed(self, event):
        """react to button-press events from the view"""
        # Don't block context menu
        if event.button == 3:
            return False

        self.drag_start = {"x": event.x, "y": event.y}
        self.dnd_start = {"x": event.x, "y": event.y}
        self.dnd_eligible = True
        self.dragging = True
        self.button = event.button
        self.view().update_cursor(event.x, event.y)
        return True

    def button_released(self, event):
        """react to button-release events from the view"""
        self.dragging = False
        self.view().update_cursor(event.x, event.y)

    def motion(self, event):
        """react to motion events from the view"""
        if not self.dragging:
            return
        offset = self.view().get_offset()
        zoom = self.view().get_zoom()
        ratio = self.view().get_resolution_ratio()
        offset_x = offset.x + (event.x - self.drag_start["x"]) / zoom * ratio
        offset_y = offset.y + (event.y - self.drag_start["y"]) / zoom
        self.drag_start["x"], self.drag_start["y"] = event.x, event.y
        self.view().set_offset(offset_x, offset_y)
        new_offset = self.view().get_offset()
        if not self.dnd_eligible:
            return

        if _approximately(new_offset.x, offset_x) and _approximately(
            new_offset.y, offset_y
        ):
            # If there was a movement in the image, disable start of dnd until
            # mouse button is pressed again
            self.dnd_eligible = False
            return

        # movement was clamped because of the edge, but did mouse move far enough?
        if self.view().drag_check_threshold(
            self.dnd_start["x"], self.dnd_start["y"], event.x, event.y
        ) and self.view().emit("dnd-start", event.x, event.y, self.button):
            self.dragging = False

    def cursor_type_at_point(self, x, y):
        """given the coordinates, return the cursor type"""
        x, y = self.view().to_image_coords(x, y)
        pixbuf_size = self.view().get_pixbuf_size()
        if 0 < x < pixbuf_size.width and 0 < y < pixbuf_size.height:
            if self.dragging:
                return "grabbing"
            return "grab"
        return None


def _approximately(v_a, v_b):
    return abs(v_a - v_b) < 0.01


CURSOR_PIXELS = 5


cursorhash = {
    "lower": {
        "lower": "nw-resize",
        "mid": "w-resize",
        "upper": "sw-resize",
    },
    "mid": {
        "lower": "n-resize",
        "mid": "crosshair",
        "upper": "s-resize",
    },
    "upper": {
        "lower": "ne-resize",
        "mid": "e-resize",
        "upper": "se-resize",
    },
}


def _drag_edge(edge, v1, v2, vevent, vdrag):
    if edge == "lower":
        v1 = vevent
        v2 = vdrag
    elif edge == "upper":
        v1 = vdrag
        v2 = vevent
    return v1, v2


class Selector(Tool):
    """Tool to draw rubber band boxes"""

    h_edge = None
    v_edge = None

    def button_pressed(self, event):
        """react to button-press events from the view"""
        # Don't block context menu
        if event.button == 3:
            return False

        self.drag_start = {"x": None, "y": None}
        self.dragging = True
        self.view().update_cursor(event.x, event.y)
        self._update_selection(event)
        return True

    def button_released(self, event):
        """react to button_release events from the view"""
        self.dragging = False
        self.view().update_cursor(event.x, event.y)
        self._update_selection(event)

    def motion(self, event):
        """react to motion events from the view"""
        if not self.dragging:
            return
        self._update_selection(event)

    def _update_selection(self, event):
        (x, y, x2, y2, x_old, y_old, x2_old, y2_old) = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        if self.h_edge is None:
            self.h_edge = "mid"
        if self.v_edge is None:
            self.v_edge = "mid"
        x, x2 = _drag_edge(self.h_edge, x, x2, event.x, self.drag_start["x"])
        y, y2 = _drag_edge(self.v_edge, y, y2, event.y, self.drag_start["y"])

        if self.h_edge == "mid" and self.v_edge == "mid":
            x = self.drag_start["x"]
            y = self.drag_start["y"]
            x2 = event.x
            y2 = event.y
        else:
            selection = self.view().get_selection()
            if (x is None) or (y is None):
                x_old, y_old = self.view().to_widget_coords(selection.x, selection.y)
            if (x2 is None) or (y2 is None):
                x2_old, y2_old = self.view().to_widget_coords(
                    selection.x + selection.width,
                    selection.y + selection.height,
                )
            if x is None:
                x = x_old
            if x2 is None:
                x2 = x2_old
            if y is None:
                y = y_old
            if y2 is None:
                y2 = y2_old

        w, h = self.view().to_image_distance(abs(x2 - x), abs(y2 - y))
        x, y = self.view().to_image_coords(min(x, x2), min(y, y2))
        sel = Gdk.Rectangle()
        sel.x, sel.y, sel.width, sel.height = (
            int(x + 0.5),
            int(y + 0.5),
            int(w + 0.5),
            int(h + 0.5),
        )
        self.view().set_selection(sel)

    def cursor_type_at_point(self, x, y):
        """given the coordinates, return the cursor type"""
        selection = self.view().get_selection()
        if selection is not None:
            (sx1, sy1) = self.view().to_widget_coords(selection.x, selection.y)
            (sx2, sy2) = self.view().to_widget_coords(
                selection.x + selection.width,
                selection.y + selection.height,
            )

            # If we are dragging, a corner cursor must stay as a corner cursor,
            # a left/right cursor must stay as left/right,
            # and a top/bottom cursor must stay as top/bottom
            if self.dragging:
                self._update_dragged_edge("x", x, sx1, sx2)
                self._update_dragged_edge("y", y, sy1, sy2)
                if self.h_edge == "mid":
                    if self.v_edge == "mid":
                        self.h_edge = "upper"
                        self.v_edge = "upper"
                        self.drag_start = {"x": x, "y": y}

                    else:
                        if "x" not in self.drag_start:
                            self.drag_start["x"] = (
                                sx2 if self.v_edge == "lower" else sx1
                            )

                elif self.v_edge == "mid":
                    if "y" not in self.drag_start:
                        self.drag_start["y"] = sy2 if self.h_edge == "lower" else sy1

            else:
                self._update_undragged_edge("h_edge", (x, y, sx1, sy1, sx2, sy2))
                self._update_undragged_edge("v_edge", (y, x, sy1, sx1, sy2, sx2))

        else:
            if self.dragging:
                self.drag_start = {"x": x, "y": y}
                (self.h_edge, self.v_edge) = ["upper", "upper"]

            else:
                (self.h_edge, self.v_edge) = ["mid", "mid"]

        return cursorhash[self.h_edge][self.v_edge]

    def _update_dragged_edge(self, direction, s, s1, s2):
        edge = ("h" if direction == "x" else "v") + "_edge"
        if getattr(self, edge) == "lower":
            if direction in self.drag_start:
                if s > self.drag_start[direction]:
                    setattr(self, edge, "upper")
                else:
                    setattr(self, edge, "lower")

            else:
                self.drag_start[direction] = s2
                setattr(self, edge, "lower")

        elif getattr(self, edge) == "upper":
            if direction in self.drag_start:
                if s < self.drag_start[direction]:
                    setattr(self, edge, "lower")

                else:
                    setattr(self, edge, "upper")

            else:
                self.drag_start[direction] = s1
                setattr(self, edge, "upper")

    def _update_undragged_edge(self, edge, coords):
        (x, y, sx1, sy1, sx2, sy2) = coords
        setattr(self, edge, "mid")
        if sy1 < y < sy2:
            if sx1 - CURSOR_PIXELS < x < sx1 + CURSOR_PIXELS:
                setattr(self, edge, "lower")

            elif sx2 - CURSOR_PIXELS < x < sx2 + CURSOR_PIXELS:
                setattr(self, edge, "upper")

    def get_selection(self):
        """get the selection from the view"""
        return self.view().get_selection()

    def set_selection(self, *args):
        """set the selection in the view"""
        self.view().set_selection(*args)


class SelectorDragger(Tool):
    """Select with LMB, drag with MMB"""

    def __init__(self, view):
        super().__init__(view)
        self._selector = Selector(view)
        self._dragger = Dragger(view)
        self._tool = self._selector

    def button_pressed(self, event):
        """react to button-press events from the view"""
        # left mouse button
        if event.button == 1:
            self._tool = self._selector
        elif event.button == 2:  # middle mouse button
            self._tool = self._dragger
        else:
            return False
        return self._tool.button_pressed(event)

    def button_released(self, event):
        """react to button-release events from the view"""
        self._tool.button_released(event)
        self._tool = self._selector

    def motion(self, event):
        """react to motion events from the view"""
        self._tool.motion(event)

    def cursor_type_at_point(self, x, y):
        """given the coordinates, return the cursor type"""
        return self._tool.cursor_type_at_point(x, y)


MAX_ZOOM = 100


class ImageView(Gtk.DrawingArea):
    """ImageView widget"""

    __gtype_name__ = "GtkImageView"
    __gsignals__ = {
        "zoom-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        "offset-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                int,
                int,
            ),
        ),
        "selection-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (Gdk.Rectangle,),
        ),
        # "tool-changed": (GObject.SignalFlags.RUN_FIRST, None, (Tool,)),
        "tool-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "dnd-start": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                float,
                float,
                int,  # button
            ),
        ),
    }
    pixbuf = GObject.Property(
        type=GdkPixbuf.Pixbuf, nick="pixbuf", blurb="Pixbuf to be shown"
    )
    offset = GObject.Property(
        type=Gdk.Rectangle, nick="Image offset", blurb="Gdk.Rectangle of x, y"
    )
    zoom = GObject.Property(
        type=float,
        minimum=0.001,
        maximum=100,
        default=1,
        nick="zoom",
        blurb="zoom level",
    )
    zoom_step = GObject.Property(
        type=float,
        minimum=1,
        maximum=10,
        default=2,
        nick="Zoom step",
        blurb="Zoom coefficient for every scrolling step",
    )
    resolution_ratio = GObject.Property(
        type=float,
        minimum=0.0001,
        maximum=1000,
        default=1,
        nick="resolution-ratio",
        blurb="Ratio of x-resolution/y-resolution",
    )
    tool = GObject.Property(type=object, nick="tool", blurb="Active Tool")
    selection = GObject.Property(
        type=Gdk.Rectangle, nick="Selection", blurb="Gdk.Rectangle of selected region"
    )
    zoom_is_fit = GObject.Property(
        type=bool,
        default=True,
        nick="Zoom is fit",
        blurb="Whether the zoom factor is automatically calculated to fit the window",
    )
    zoom_to_fit_limit = GObject.Property(
        type=float,
        minimum=0.0001,
        maximum=100,
        default=100,
        nick="Zoom to fit limit",
        blurb="When zooming automatically, don't zoom more than this",
    )
    interpolation = GObject.Property(
        type=int,
        default=cairo.FILTER_GOOD,
        nick="interpolation",
        blurb="Interpolation method to use, from cairo.Filter. See https://www.cairographics.org/documentation/pycairo/3/reference/constants.html#cairo-filter",
    )

    def do_draw(self, context):
        """respond to the draw signal"""
        allocation = self.get_allocation()
        style = self.get_style_context()
        pixbuf = self.get_pixbuf()
        ratio = self.get_resolution_ratio()
        style.add_class("imageview")
        style.save()
        style.add_class(Gtk.STYLE_CLASS_BACKGROUND)
        Gtk.render_background(
            style,
            context,
            allocation.x,
            allocation.y,
            allocation.width,
            allocation.height,
        )
        style.restore()
        if pixbuf is not None:
            if pixbuf.get_has_alpha():
                style.save()

                # '.imageview' affects also area outside of the image. But only
                # when background-image is specified. background-color seems to
                # have no effect there. Probably a bug in Gtk? Either way, this is
                # why need a special class 'transparent' to match the correct area
                # inside the image where both image and color work.
                style.add_class("transparent")
                (x1, y1) = self.to_widget_coords(0, 0)
                (x2, y2) = self.to_widget_coords(
                    pixbuf.get_width(), pixbuf.get_height()
                )
                Gtk.render_background(style, context, x1, y1, x2 - x1, y2 - y1)
                style.restore()

            zoom = self.get_zoom() / self.get_scale_factor()
            context.scale(zoom / ratio, zoom)
            offset = self.get_offset()
            context.translate(offset.x, offset.y)
            Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
            context.get_source().set_filter(self.get_interpolation())

        else:
            bgcol = style.get_background_color(Gtk.StateFlags.NORMAL)
            Gdk.cairo_set_source_rgba(context, bgcol)

        context.paint()
        selection = self.get_selection()
        if pixbuf is not None and selection is not None:
            (
                x,
                y,
                w,
                h,
            ) = (
                selection.x,
                selection.y,
                selection.width,
                selection.height,
            )
            if w <= 0 or h <= 0:
                return True
            style.save()
            style.add_class(Gtk.STYLE_CLASS_RUBBERBAND)
            Gtk.render_background(style, context, x, y, w, h)
            Gtk.render_frame(style, context, x, y, w, h)
            style.restore()

        return True

    def do_button_press_event(self, event):
        """respond to the button_press event"""
        return self.get_tool().button_pressed(event)

    def do_button_release_event(self, event):
        """respond to the button_release event"""
        self.get_tool().button_released(event)

    def do_motion_notify_event(self, event):
        """respond to the motion_notify event"""
        self.update_cursor(event.x, event.y)
        self.get_tool().motion(event)

    def do_scroll_event(self, event):
        """respond to the scroll event"""
        center_x, center_y = self.to_image_coords(event.x, event.y)
        if center_x is None:
            return
        zoom = None
        self.setzoom_is_fit(False)
        if event.direction == Gdk.ScrollDirection.UP:
            zoom = self.get_zoom() * self.zoom_step
        else:
            zoom = self.get_zoom() / self.zoom_step
        self._set_zoom_with_center(zoom, center_x, center_y)

    def do_configure_event(self, _event):
        """respond to the configure event"""
        if self.zoom_is_fit:
            self.zoom_to_box(self.get_pixbuf_size())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_app_paintable(True)
        self.add_events(
            Gdk.EventMask.EXPOSURE_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
        )
        self.set_tool(Dragger(self))
        self.set_redraw_on_allocate(False)

    def set_pixbuf(self, pixbuf, zoom_to_fit=False):
        """set pixbuf, optionally zooming to fit"""
        self.pixbuf = pixbuf
        self.setzoom_is_fit(zoom_to_fit)
        if not zoom_to_fit:
            self.set_offset(0, 0)
        self.queue_draw()

    def get_pixbuf(self):
        """return current pixbuf"""
        return self.pixbuf

    def get_pixbuf_size(self):
        """return size of current pixbuf"""
        pixbuf = self.get_pixbuf()
        if pixbuf is None:
            return None
        size = Gdk.Rectangle()
        size.width, size.height = pixbuf.get_width(), pixbuf.get_height()
        return size

    def set_zoom(self, zoom):
        """setting the zoom via the public API disables zoom-to-fit"""
        self.setzoom_is_fit(False)
        self._set_zoom_no_center(zoom)

    def _set_zoom(self, zoom):
        zoom = min(zoom, MAX_ZOOM)
        self.zoom = zoom
        self.emit("zoom-changed", zoom)
        self.queue_draw()

    def get_zoom(self):
        """return current zoom"""
        return self.zoom

    def to_widget_coords(self, x, y):
        """convert x, y in image coords to widget coords"""
        zoom = self.get_zoom()
        ratio = self.get_resolution_ratio()
        offset = self.get_offset()
        factor = self.get_scale_factor()
        return (x + offset.x) * zoom / factor / ratio, (y + offset.y) * zoom / factor

    def to_image_coords(self, x, y):
        """convert x, y in widget coords to image coords"""
        zoom = self.get_zoom()
        ratio = self.get_resolution_ratio()
        offset = self.get_offset()
        if offset is None:
            return None, None
        factor = self.get_scale_factor()
        return x * factor / zoom * ratio - offset.x, y * factor / zoom - offset.y

    def to_image_distance(self, x, y):
        """convert x, y in widget distance to image distance"""
        zoom = self.get_zoom()
        ratio = self.get_resolution_ratio()
        factor = self.get_scale_factor()
        return x * factor / zoom * ratio, y * factor / zoom

    def _set_zoom_with_center(self, zoom, center_x, center_y):
        allocation = self.get_allocation()
        ratio = self.get_resolution_ratio()
        factor = self.get_scale_factor()
        offset_x = allocation.width * factor / 2 / zoom * ratio - center_x
        offset_y = allocation.height * factor / 2 / zoom - center_y
        self._set_zoom(zoom)
        self.set_offset(offset_x, offset_y)

    def _set_zoom_no_center(self, zoom):
        allocation = self.get_allocation()
        (center_x, center_y) = self.to_image_coords(
            allocation.width / 2, allocation.height / 2
        )
        self._set_zoom_with_center(zoom, center_x, center_y)

    def setzoom_is_fit(self, zoom_to_fit, limit=None):
        """zoom to fit current pixbuf"""
        self.zoom_is_fit = zoom_to_fit
        if limit is not None:
            self.zoom_to_fit_limit = limit

        if zoom_to_fit:
            self.zoom_to_box(self.get_pixbuf_size())

    def zoom_to_box(self, box, additional_factor=None):
        """zoom to fit given box, with an optional factor for a border"""
        if box is None:
            return
        if additional_factor is None:
            additional_factor = 1
        allocation = self.get_allocation()
        ratio = self.get_resolution_ratio()
        limit = self.zoom_to_fit_limit
        sc_factor_w = min(limit, allocation.width / box.width) * ratio
        sc_factor_h = min(limit, allocation.height / box.height)
        self._set_zoom_with_center(
            min(sc_factor_w, sc_factor_h) * additional_factor * self.get_scale_factor(),
            (box.x + box.width / 2) / ratio,
            box.y + box.height / 2,
        )

    def zoom_to_selection(self, context_factor):
        """zoom to fit current selection, with an optional factor for a border"""
        self.zoom_to_box(self.get_selection(), context_factor)

    def getzoom_is_fit(self):
        """return value of zoom_to_fit property"""
        return self.zoom_is_fit

    def zoom_in(self):
        """zoom in one step"""
        self.setzoom_is_fit(False)
        self._set_zoom_no_center(self.get_zoom() * self.zoom_step)

    def zoom_out(self):
        """zoom out one step"""
        self.setzoom_is_fit(False)
        self._set_zoom_no_center(self.get_zoom() / self.zoom_step)

    def zoom_to_fit(self):
        """set zoom-to-fit property True"""
        self.setzoom_is_fit(True)

    def set_fitting(self, value):
        """set zoom-to-fit property"""
        self.setzoom_is_fit(value)

    def set_offset(self, offset_x, offset_y):
        """set offset (pan)"""
        if self.get_pixbuf() is None:
            return

        # Convert the widget size to image scale to make the comparisons easier
        allocation = self.get_allocation()
        (allocation.width, allocation.height) = self.to_image_distance(
            allocation.width, allocation.height
        )
        pixbuf_size = self.get_pixbuf_size()
        offset_x = _clamp_direction(offset_x, allocation.width, pixbuf_size.width)
        offset_y = _clamp_direction(offset_y, allocation.height, pixbuf_size.height)
        self.offset = Gdk.Rectangle()
        self.offset.x, self.offset.y = offset_x, offset_y
        self.emit("offset-changed", offset_x, offset_y)
        self.queue_draw()

    def get_offset(self):
        """get current offset (pan)"""
        return self.offset

    def get_viewport(self):
        """get current viewport"""
        allocation = self.get_allocation()
        pixbuf = self.get_pixbuf()
        viewport = Gdk.Rectangle()
        if pixbuf is not None:
            viewport.x, viewport.y = self.to_image_coords(0, 0)
            viewport.width, viewport.height = self.to_image_distance(
                allocation.width, allocation.height
            )
        else:
            viewport.width, viewport.height = allocation.width, allocation.height
        return viewport

    def set_tool(self, tool):
        """set tool"""
        if not isinstance(tool, Tool):
            raise ValueError("invalid set_tool call")
        self.tool = tool
        if self.get_selection() is not None:
            self.queue_draw()
        self.emit("tool-changed", tool)

    def get_tool(self):
        """get current tool"""
        return self.tool

    def set_selection(self, selection):
        """set selection"""
        pixbuf_size = self.get_pixbuf_size()
        if pixbuf_size is None:
            return
        if selection.x < 0:
            selection.width += selection.x
            selection.x = 0

        if selection.y < 0:
            selection.height += selection.y
            selection.y = 0

        if selection.x + selection.width > pixbuf_size.width:
            selection.width = pixbuf_size.width - selection.x

        if selection.y + selection.height > pixbuf_size.height:
            selection.height = pixbuf_size.height - selection.y

        if (self.selection is not None) or (selection is not None):
            self.selection = selection
            self.queue_draw()
            self.emit("selection-changed", selection)

    def get_selection(self):
        """get current selection"""
        return self.selection

    def set_resolution_ratio(self, ratio):
        """set ratio between x and y resolutions"""
        self.resolution_ratio = ratio
        if self.zoom_is_fit:
            self.zoom_to_box(self.get_pixbuf_size())
        self.queue_draw()

    def get_resolution_ratio(self):
        """get ratio between x and y resolutions"""
        return self.resolution_ratio

    def update_cursor(self, x, y):
        """update cursor based on given coords"""
        pixbuf_size = self.get_pixbuf_size()
        if pixbuf_size is None:
            return
        win = self.get_window()
        cursor = self.get_tool().cursor_at_point(x, y)
        if cursor is not None:
            win.set_cursor(cursor)

    def set_interpolation(self, interpolation):
        """set interpolation method"""
        self.interpolation = interpolation
        self.queue_draw()

    def get_interpolation(self):
        """get current interpolation method"""
        return self.interpolation


def _clamp_direction(offset, allocation, pixbuf_size):
    # Centre the image if it is smaller than the widget
    if allocation > pixbuf_size:
        offset = (allocation - pixbuf_size) / 2

    # Otherwise don't allow the LH/top edge of the image to be visible
    elif offset > 0:
        offset = 0

    # Otherwise don't allow the RH/bottom edge of the image to be visible
    elif offset < allocation - pixbuf_size:
        offset = allocation - pixbuf_size

    return offset

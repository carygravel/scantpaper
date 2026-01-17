"Classes to do with displaying HOCR ouput"

import re
import math
import html
import logging
import gi
from bboxtree import Bboxtree

gi.require_version("GooCanvas", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gdk,
    GLib,
    GObject,
    GooCanvas,
)


MAX_COLOR_INT = 65535
COLOR_TOLERANCE = 0.00001
_60_DEGREES = 60
MAX_ZOOM = 15
EMPTY_LIST = -1
MAX_CONFIDENCE_DEFAULT = 95
MIN_CONFIDENCE_DEFAULT = 50
FULLPAGE_OCR_SCALE = 0.8
COLOR_GREEN = 2
COLOR_CYAN = 3
COLOR_BLUE = 4
COLOR_YELLOW = 6
NOT_FOUND = -1
_100_PERCENT = 100
_360_DEGREES = 360
EMPTY = ""
SPACE = " "
HOCR_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf $Gscan2pdf::Canvas::VERSION' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
"""

logger = logging.getLogger(__name__)


def rect2bboxarray(rect):  # FIXME: this should be part of Rectangle()
    "given a Rectangle(), return an array of int suitable for hocr output"
    return [
        int(rect.x),
        int(rect.y),
        int(rect.x + rect.width),
        int(rect.y + rect.height),
    ]


def rgb2hsv(rgb):
    "convert from rgb to hsv colour space"
    minv = rgb.red if rgb.red < rgb.green else rgb.green
    minv = minv if minv < rgb.blue else rgb.blue
    maxv = rgb.red if rgb.red > rgb.green else rgb.green
    maxv = maxv if maxv > rgb.blue else rgb.blue
    hsv = {}
    hsv["v"] = maxv
    delta = maxv - minv
    if delta < COLOR_TOLERANCE:
        hsv["s"] = 0
        hsv["h"] = 0  # undefined, maybe nan?
        return hsv

    hsv["s"] = delta / maxv

    if rgb.red >= maxv:  # > is bogus, just keeps compiler happy
        hsv["h"] = (
            (rgb.green - rgb.blue) / delta
        ) % COLOR_YELLOW  # between yellow & magenta

    elif rgb.green >= maxv:
        hsv["h"] = COLOR_GREEN + (rgb.blue - rgb.red) / delta  # between cyan & yellow

    else:
        hsv["h"] = COLOR_BLUE + (rgb.red - rgb.green) / delta  # between magenta & cyan

    hsv["h"] *= _60_DEGREES
    if hsv["h"] < 0.0:
        hsv["h"] += _360_DEGREES

    return hsv


def string2hsv(spec):
    "return hsv color from string"
    return rgb2hsv(string2rgb(spec))


def string2rgb(spec):
    "return Gdk.RGBA object from string"
    color = Gdk.RGBA()
    _flag = color.parse(spec)
    return color


def linear_interpolation(x1, x2, m):
    "1D linear interpolation"
    return x1 * (1 - m) + x2 * m


def hsv2rgb(hsv):
    "convert from hsv to rgb colour space"
    if hsv["s"] <= 0.0:  # < is bogus, just shuts up warnings
        return Gdk.RGBA(hsv["v"], hsv["v"], hsv["v"])

    hh = hsv["h"]
    if hh >= _360_DEGREES:
        hh = 0.0
    hh /= _60_DEGREES
    i = int(hh)
    ff = hh - i
    p = hsv["v"] * (1.0 - hsv["s"])
    q = hsv["v"] * (1.0 - hsv["s"] * ff)
    t = hsv["v"] * (1.0 - hsv["s"] * (1.0 - ff))

    if i == 0:
        red = hsv["v"]
        green = t
        blue = p

    elif i == 1:
        red = q
        green = hsv["v"]
        blue = p

    elif i == COLOR_GREEN:
        red = p
        green = hsv["v"]
        blue = t

    elif i == COLOR_CYAN:
        red = p
        green = q
        blue = hsv["v"]

    elif i == COLOR_BLUE:
        red = t
        green = p
        blue = hsv["v"]

    else:
        red = hsv["v"]
        green = p
        blue = q

    return Gdk.RGBA(red, green, blue)


def _clamp_direction(offset, allocation, pixbuf_size):
    "Centre the image if it is smaller than the widget"

    if allocation > pixbuf_size:
        offset = (allocation - pixbuf_size) / 2

    # Otherwise don't allow the LH/top edge of the image to be visible
    elif offset > 0:
        offset = 0

    # Otherwise don't allow the RH/bottom edge of the image to be visible
    elif offset < allocation - pixbuf_size:
        offset = allocation - pixbuf_size

    return offset


class Canvas(
    GooCanvas.Canvas
):  # TODO: replace this with https://github.com/gaphor/gaphas
    "Subclass GooCanvas.Canvas to add properties and methods to display hocr output"

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
    }

    @GObject.Property(
        type=Gdk.Rectangle, nick="Canvas offset", blurb="Gdk.Rectangle of x, y"
    )
    def offset(self):  # pylint: disable=method-hidden
        "getter for offset attribute"
        return self._offset

    @offset.setter
    def offset(self, newval):
        "setter for offset attribute"
        if newval.x != self._offset.x or newval.y != self._offset.y:
            self._offset = newval
            self.scroll_to(-newval.x, -newval.y)
            self.emit("offset-changed", newval.x, newval.y)

    _max_color = "black"

    @GObject.Property(
        type=str,
        default="black",
        nick="Maximum color",
        blurb="Color for maximum confidence",
    )
    def max_color(self):
        "getter for max_color attribute"
        return self._max_color

    @max_color.setter
    def max_color(self, newval):
        "setter for max_color attribute"
        self._max_color = newval
        self.max_color_hsv = string2hsv(self._max_color)

    max_color_hsv = GObject.Property(
        type=object,
        nick="Maximum color (HSV)",
        blurb="HSV Color for maximum confidence",
    )

    _min_color = "red"

    @GObject.Property(
        type=str,
        default="red",
        nick="Minimum color",
        blurb="Color for minimum confidence",
    )
    def min_color(self):
        "getter for min_color attribute"
        return self._min_color

    @min_color.setter
    def min_color(self, newval):
        "setter for min_color attribute"
        self._min_color = newval
        self.min_color_hsv = string2hsv(self._min_color)

    min_color_hsv = GObject.Property(
        type=object,
        nick="Minimum color (HSV)",
        blurb="HSV Color for minimum confidence",
    )
    max_confidence = GObject.Property(
        type=int,
        minimum=0,
        maximum=_100_PERCENT,
        default=MAX_CONFIDENCE_DEFAULT,
        nick="Maximum confidence",
        blurb="Confidence threshold for max-color",
    )
    min_confidence = GObject.Property(
        type=int,
        minimum=0,
        maximum=_100_PERCENT,
        default=MIN_CONFIDENCE_DEFAULT,
        nick="Minimum confidence",
        blurb="Confidence threshold for min-color",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("button-press-event", self._button_pressed)
        self.connect("button-release-event", self._button_released)
        self.connect("motion-notify-event", self._motion)
        self.connect("scroll-event", self._scroll)
        #     self.add_events(
        #     Glib.Object.Introspection.convert_sv_to_flags(
        #         'Gtk3::Gdk::EventMask', 'exposure-mask' ) |
        #         Glib.Object.Introspection.convert_sv_to_flags(
        #         'Gtk3::Gdk::EventMask', 'button-press-mask' ) |
        #         Glib.Object.Introspection.convert_sv_to_flags(
        #         'Gtk3::Gdk::EventMask', 'button-release-mask' ) |
        #         Glib.Object.Introspection.convert_sv_to_flags(
        #         'Gtk3::Gdk::EventMask', 'pointer-motion-mask' ) |
        #         Glib.Object.Introspection.convert_sv_to_flags(
        #         'Gtk3::Gdk::EventMask', 'scroll-mask'
        #         )
        # )
        self._old_idles = {}
        self._device = Gdk.Display.get_default().get_default_seat().get_pointer()
        self._offset = Gdk.Rectangle()
        self._current_index = "position"
        self.position_index = None
        self.confidence_index = None
        self._dragging = False
        self._drag_start = {}
        self._pixbuf_size = None

        # allow the widget to be accessed via CSS
        self.set_name("gscan2pdf-ocr-canvas")

    def get_max_color_hsv(self):
        "return the max hsv colour"
        val = self.max_color_hsv
        if val is None:
            self.max_color_hsv = string2hsv(self.max_color)
            return self.max_color_hsv

        return val

    def get_min_color_hsv(self):
        "return the min hsv colour"
        val = self.min_color_hsv
        if val is None:
            self.min_color_hsv = string2hsv(self.min_color)
            return self.min_color_hsv

        return val

    # FIXME: why is this called twice when running OCR from tools?
    def set_text(self, **kwargs):
        "set the canvas text from a page object"

        if self._old_idles:
            for box in list(self._old_idles.keys()):
                GLib.Source.remove(self._old_idles[box])
                del self._old_idles[box]

        self.position_index = None
        root = GooCanvas.CanvasGroup()
        width, height = kwargs["page"].get_size()

        self.set_root_item(root)
        self._pixbuf_size = {"width": width, "height": height}
        self.set_bounds(0, 0, width, height)

        # Attach the text to the canvas
        self.confidence_index = ListIter()
        tree = Bboxtree(getattr(kwargs["page"], kwargs["layer"]))
        itr = tree.each_bbox()
        try:
            box = next(itr)
        except StopIteration:
            return
        options = {
            "iter": itr,
            "box": box,
            "parents": [root],
            "transformations": [[0, 0, 0]],
            "edit_callback": kwargs.get("edit_callback"),
            "idle": kwargs.get("idle", True),
            "finished_callback": kwargs.get("finished_callback"),
        }
        self._boxed_text_wrapper(options)

    def get_first_bbox(self):
        "return first bbox, depending on which index is active"
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_first_bbox()
        else:
            bbox = self.position_index.first_word()

        self.set_other_index(bbox)
        return bbox

    def get_previous_bbox(self):
        "return previous bbox, depending on which index is active"
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_previous_bbox()
        else:
            bbox = self.position_index.previous_word()

        self.set_other_index(bbox)
        return bbox

    def get_next_bbox(self):
        "return next bbox, depending on which index is active"
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_next_bbox()
        else:
            bbox = self.position_index.next_word()

        self.set_other_index(bbox)
        return bbox

    def get_last_bbox(self):
        "return last bbox, depending on which index is active"
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_last_bbox()
        else:
            bbox = self.position_index.last_word()

        self.set_other_index(bbox)
        return bbox

    def get_current_bbox(self):
        "return current bbox"
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_current_bbox()

        else:
            bbox = self.position_index.get_current_bbox()

        self.set_other_index(bbox)
        return bbox

    def set_index_by_bbox(self, bbox):
        "set the index by bbox"
        if bbox is None:
            raise IndexError
        if self._current_index == "confidence":
            self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)
        else:
            self.position_index = TreeIter(bbox)

    def set_other_index(self, bbox):
        "swap indices"
        if bbox is None:
            return
        if self._current_index == "confidence":
            self.position_index = TreeIter(bbox)
        else:
            self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)

    def get_pixbuf_size(self):
        "return the size of the associated pixbuf"
        return self._pixbuf_size

    def clear_text(self):
        "clear the canvas"
        self.set_root_item(GooCanvas.CanvasGroup())
        self._pixbuf_size = None

    def set_offset(self, offset_x, offset_y):
        "set the offset"
        if self.get_pixbuf_size() is None:
            return

        # Convert the widget size to image scale to make the comparisons easier
        allocation = self.get_allocation()
        allocation.width, allocation.height = self._to_image_distance(
            allocation.width, allocation.height
        )
        pixbuf_size = self.get_pixbuf_size()
        offset_x = _clamp_direction(offset_x, allocation.width, pixbuf_size["width"])
        offset_y = _clamp_direction(offset_y, allocation.height, pixbuf_size["height"])
        min_x = 0
        min_y = 0
        if offset_x > 0:
            min_x = -offset_x

        if offset_y > 0:
            min_y = -offset_y

        self.set_bounds(
            min_x, min_y, pixbuf_size["width"] - min_x, pixbuf_size["height"] - min_y
        )
        offset = Gdk.Rectangle()
        offset.x = offset_x
        offset.y = offset_y
        self.offset = offset

    def get_offset(self):
        "return the offset"
        return self._offset

    def get_bbox_at(self, bbox):
        "return the bbox at the given coords"
        x = bbox.x + bbox.width / 2
        y = bbox.y + bbox.height / 2
        parent = self.get_item_at(x, y, False)
        while parent is not None and (
            not hasattr(parent, "type") or parent.type == "word"
        ):
            parent = parent.get_parent()
        if parent is None:
            raise ReferenceError
        return parent

    def add_box(self, **kwargs):
        "add box to canvas"
        if "parent" in kwargs:
            parent = kwargs["parent"]
        else:
            parent = self.get_bbox_at(kwargs["bbox"])

        transformation = [0, 0, 0]
        if "transformation" in kwargs:
            transformation = kwargs["transformation"]
        elif isinstance(parent, Bbox):
            transformation = [parent.textangle, parent.bbox.x, parent.bbox.y]

        options2 = {
            "canvas": self,
            "parent": parent,
            "bbox": kwargs["bbox"],
            "transformation": transformation,
            "text": kwargs["text"],
        }

        # copy parameters from box from OCR output
        for key in ["baseline", "confidence", "id", "text", "textangle", "type"]:
            if key in kwargs:
                options2[key] = kwargs[key]

        if "textangle" not in options2:
            options2["textangle"] = 0
        if "type" not in options2:
            options2["type"] = "word"
        if "confidence" not in options2 and options2["type"] == "word":
            options2["confidence"] = _100_PERCENT

        bbox = Bbox(**options2)
        if self.position_index is None:
            self.position_index = TreeIter(bbox)

        if len(kwargs["text"]) > 0:
            self.confidence_index.add_box_to_index(bbox, bbox.confidence)

            # clicking text box produces a dialog to edit the text
            if "edit_callback" in kwargs:
                bbox.connect(
                    "button-press-event",
                    bbox.button_press_callback,
                    kwargs["edit_callback"],
                    bbox,
                )

        return bbox

    def _boxed_text(self, options):
        "Draw text on the canvas with a box around it"
        box = options["box"]

        # each call should use own copy of arrays to prevent race conditions
        transformations = options["transformations"]
        parents = options["parents"]
        rotation, _, _ = transformations[box["depth"]]
        textangle = box["textangle"] if "textangle" in box else 0

        # copy box parameters from method arguments
        options2 = {"parent": parents[box["depth"]]}
        options2["edit_callback"] = options["edit_callback"]
        options2["text"] = box["text"] if "text" in box else ""

        # copy parameters from box from OCR output
        for key in ["baseline", "confidence", "id", "textangle", "type"]:
            if key in box:
                options2[key] = box[key]

        options2["bbox"] = Rectangle.from_bbox(*box["bbox"])
        bbox = self.add_box(**options2)

        # always one more parent, as the page has a root
        if box["depth"] > len(parents) - 2:
            parents.append(bbox)
        else:
            parents[box["depth"] + 1] = bbox

        transformations.append(
            [textangle + rotation, options2["bbox"].x, options2["bbox"].y]
        )
        try:
            child = next(options["iter"])
        except StopIteration:
            if options["finished_callback"]:
                options["finished_callback"]()
            return

        options3 = {
            "box": child,
            "iter": options["iter"],
            "parents": parents,
            "transformations": transformations,
            "edit_callback": options["edit_callback"],
            "idle": options["idle"],
            "finished_callback": options["finished_callback"],
        }
        self._boxed_text_wrapper(options3)

        # $rect->signal_connect(
        #  'button-press-event' => sub {
        #   my ( $widget, $target, $ev ) = @_;
        #   print "rect button-press-event\n";
        #   #  return TRUE;
        #  }
        # );
        # $g->signal_connect(
        #  'button-press-event' => sub {
        #   my ( $widget, $target, $ev ) = @_;
        #   print "group $widget button-press-event\n";
        #   my $n = $widget->get_n_children;
        #   for ( my $i = 0 ; $i < $n ; $i++ ) {
        #    my $item = $widget->get_child($i);
        #    if ( $item->isa('GooCanvas2::CanvasText') ) {
        #     print "contains $item\n", $item->get('text'), "\n";
        #     last;
        #    }
        #   }
        #   #  return TRUE;
        #  }
        # );

    def _boxed_text_wrapper(self, kwargs):
        if kwargs["idle"]:

            def _boxed_text_in_idle():
                self._boxed_text(kwargs)
                del self._old_idles[str(kwargs["box"])]
                return GLib.SOURCE_REMOVE

            self._old_idles[str(kwargs["box"])] = GLib.idle_add(_boxed_text_in_idle)
        else:
            self._boxed_text(kwargs)

    def hocr(self):
        "Convert the canvas into hocr"
        if self.get_pixbuf_size() is None:
            return ""
        root = self.get_root_item()
        string = root.get_child(0).to_hocr(2)
        return (
            HOCR_HEADER
            + f""" <body>
{string} </body>
</html>
"""
        )

    def _to_image_distance(self, x, y):
        "convert x, y in widget distance to image distance"
        zoom = self.get_scale()
        return x / zoom, y / zoom

    def _set_zoom_with_center(self, zoom, center_x, center_y):
        "set zoom with centre in image coordinates"
        zoom = min(zoom, MAX_ZOOM)
        allocation = self.get_allocation()
        offset_x = allocation.width / 2 / zoom - center_x
        offset_y = allocation.height / 2 / zoom - center_y
        self.set_scale(zoom)
        self.emit("zoom-changed", zoom)
        self.set_offset(offset_x, offset_y)

    def _button_pressed(self, _self, event):

        # middle mouse button
        if event.button == 2:

            # Using the root window x,y position for dragging the canvas, as the
            # values returned by event.x and y cause a bouncing effect, and
            # only the value since the last event is required.
            _screen, x, y = self._device.get_position()
            self._drag_start = {"x": x, "y": y}
            self._dragging = True
            win = self.get_window()
            win.set_cursor(
                Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grabbing")
            )

    def _button_released(self, _self, event):
        if event.button == 2:
            self._dragging = False
            win = self.get_window()
            win.set_cursor(None)

        return True

    def _motion(self, _self, _event):
        if not self._dragging:
            return False
        offset = self.get_offset()
        zoom = self.get_scale()
        _screen, x, y = self._device.get_position()
        offset_x = offset.x + (x - self._drag_start["x"]) / zoom
        offset_y = offset.y + (y - self._drag_start["y"]) / zoom
        self._drag_start["x"], self._drag_start["y"] = (x, y)
        self.set_offset(offset_x, offset_y)
        return True

    def _scroll(self, _self, event):
        image_x, image_y = self.convert_from_pixels(event.x, event.y)
        zoom = None
        if event.direction == Gdk.ScrollDirection.UP:
            zoom = self.get_scale() * 2
        else:
            zoom = self.get_scale() / 2

        # set the offset so that the point under the mouse stays under the mouse
        # after the zoom
        self.set_scale(zoom)
        factor = self.get_scale_factor()
        offset_x = event.x / zoom * factor - image_x
        offset_y = event.y / zoom * factor - image_y
        self.set_offset(offset_x, offset_y)

        # don't allow the event to propagate, as this pans it in y
        return True

    def sort_by_confidence(self):
        "Iterate through the bboxes by confidence"
        self._current_index = "confidence"

    def sort_by_position(self):
        "Iterate through the bboxes by position"
        self._current_index = "position"


class Bbox(GooCanvas.CanvasGroup):
    """BBox subclasses CanvasGroup to include a CanvasRect, and either a
    CanvasText, or other BBoxes"""

    __gsignals__ = {
        "text-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "bbox-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "clicked": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    text = GObject.Property(
        type=str, default=EMPTY, nick="Text", blurb="String of box text"
    )
    bbox = GObject.Property(
        type=Gdk.Rectangle,
        nick="Bounding box",
        blurb="Gdk.Rectangle of x, y, width, height",
    )
    canvas = GObject.Property(
        type=Canvas,
        nick="Canvas to which the Bbox belongs",
        blurb="Canvas to which the Bbox belongs",
    )
    transformation = GObject.Property(
        type=object, nick="Transformation", blurb="List of angle, x, y"
    )
    confidence = GObject.Property(
        type=int,
        minimum=0,
        maximum=_100_PERCENT,
        default=0,
        nick="Confidence",
        blurb="Confidence of bbox",
    )
    textangle = GObject.Property(
        type=int,
        minimum=-180,
        maximum=180,
        default=0,
        nick="Text angle",
        blurb="Angle of text in bbox",
    )
    type = GObject.Property(type=str, default="word", nick="Type", blurb="Type of box")
    id = GObject.Property(
        type=str, default=EMPTY, nick="ID", blurb="ID of box as given by OCR engine"
    )
    baseline = GObject.Property(
        type=object, nick="Baseline", blurb="Baseline of box as given by OCR engine"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        rotation, x0, y0 = self.transformation
        self.translate(self.bbox.x - x0, self.bbox.y - y0)
        textangle = self.textangle
        color = self.confidence2color()

        # draw the rect first to make sure the text goes on top
        # and receives any mouse clicks
        GooCanvas.CanvasRect(
            parent=self,
            x=0,
            y=0,
            width=self.bbox.width,
            height=self.bbox.height,
            stroke_color=color,
            line_width=2 if self.text else 1,
        )

        # show text baseline (currently of no use)
        # if ( $box->{baseline} ) {
        #    my ( $slope, $offs ) = @{ $box->{baseline} }[-2,-1];
        #    # "real" baseline with slope
        #    $rect = GooCanvas2::CanvasPolyline->new_line( $g,
        #        0, $height + $offs, $width, $height + $offs + $width * $slope,
        #        'stroke-color' => 'green' );
        #    # virtual, horizontally aligned baseline
        #    my $y_offs = $height + $offs + 0.5 * $width * $slope;
        #    $rect = GooCanvas2::CanvasPolyline->new_line( $g,
        #        0, $y_offs, $width, $y_offs,
        #        'stroke-color' => 'orange' );
        # }

        if self.text != "":

            # create text and then scale, shift & rotate it into the bounding box
            text = GooCanvas.CanvasText(
                parent=self,
                text=self.text,
                x=self.bbox.width / 2,
                y=self.bbox.height / 2,
                width=-1,
                anchor="center",
                font="Sans",
                fill_color=color,
            )
            angle = -(textangle + rotation) % _360_DEGREES
            bounds = text.get_bounds()
            if bounds.x2 - bounds.x1 == 0:
                logger.error("text '%s' has no width, skipping", self.text)
                return

            scale = (self.bbox.height if angle else self.bbox.width) / (
                bounds.x2 - bounds.x1
            )

            # gocr case: gocr creates text only which we treat as page text
            if self.type == "page":
                scale *= FULLPAGE_OCR_SCALE

            self.transform_text(scale, angle)

    def button_press_callback(self, _self, target, event, edit_callback, bbox):
        "button press callback"
        if event.button == 1:
            self.parent.get_parent()._dragging = False
            edit_callback(self, target, event, bbox)

    def get_stack_index_by_position(self, bbox):
        """given a parent bbox and a new box, return the index
        where the new box should be inserted in the stack of children.
        Using binary search
        https://en.wikipedia.org/wiki/Binary_search_algorithm#Alternative_procedure"""

        l = 0
        r = self.get_n_children() - 1

        # Initial trim to ensure l and r point to Bboxes if possible
        while l < r:
            child = self.get_child(l)
            if isinstance(child, Bbox):
                break
            l += 1

        while l < r:
            child = self.get_child(r)
            if isinstance(child, Bbox):
                break
            r -= 1

        newboxpos = bbox.get_centroid()
        axis = 0 if self.type == "line" else 1

        # Standard binary search with adjustment for non-Bbox items
        while l <= r:
            m = (l + r) // 2

            # Find nearest Bbox to m
            # Search left then right
            orig_m = m
            child = self.get_child(m)
            found = False

            # Search left down to l
            left_m = m
            while left_m >= l:
                child = self.get_child(left_m)
                if isinstance(child, Bbox):
                    m = left_m
                    found = True
                    break
                left_m -= 1

            # If not found left, search right up to r
            if not found:
                right_m = orig_m + 1
                while right_m <= r:
                    child = self.get_child(right_m)
                    if isinstance(child, Bbox):
                        m = right_m
                        found = True
                        break
                    right_m += 1

            if not found:
                # No Bboxes in [l, r]
                break

            boxpos = child.get_centroid()
            if boxpos[axis] > newboxpos[axis]:
                r = m - 1
            else:
                l = m + 1

        # Final adjustment: ensure l is valid insertion point
        # If l points to a Bbox that is smaller, we should step over it
        # (Though the binary search logic l=m+1 usually handles this)
        if l < self.get_n_children():
            child = self.get_child(l)
            if isinstance(child, Bbox):
                boxpos = child.get_centroid()
                if boxpos[axis] < newboxpos[axis]:
                    l += 1

        return l

    def confidence2color(self):
        """Convert confidence percentage into colour
        Any confidence level greater than max_conf is treated as max_conf and given
        max_color. Any confidence level less than min_conf is treated as min_conf and
        given min_color. Anything in between is appropriately interpolated in HSV space.
        """

        confidence = self.confidence
        canvas = self.canvas
        max_conf = canvas.max_confidence
        if confidence >= max_conf:
            return canvas.max_color

        min_conf = canvas.min_confidence
        if confidence <= min_conf:
            return canvas.min_color

        max_hsv = canvas.get_max_color_hsv()
        min_hsv = canvas.get_min_color_hsv()
        m = (confidence - min_conf) / (max_conf - min_conf)
        hsv = {}
        hsv["h"], hsv["s"], hsv["v"] = (
            linear_interpolation(min_hsv["h"], max_hsv["h"], m),
            linear_interpolation(min_hsv["s"], max_hsv["s"], m),
            linear_interpolation(min_hsv["v"], max_hsv["v"], m),
        )
        rgb = hsv2rgb(hsv)
        return (
            f"#{int(rgb.red * MAX_COLOR_INT):04x}"
            f"{int(rgb.green * MAX_COLOR_INT):04x}"
            f"{int(rgb.blue * MAX_COLOR_INT):04x}"
        )

    def get_box_widget(self):
        "return rect widget of bbox"
        return self.get_child(0)

    def get_text_widget(self):
        "return text widget of bbox"
        child = self.get_child(1)
        if isinstance(child, GooCanvas.CanvasText):
            return child
        raise AttributeError

    def get_centroid(self):
        "return centroid of bbox"
        bbox = self.bbox
        return bbox.x + bbox.width / 2, bbox.y + bbox.height / 2

    def get_position_index(self):
        "return positional index of bbox"
        parent = self.parent
        while parent and not isinstance(parent, Bbox):
            parent = parent.parent

        sort_direction = 0
        if parent.type != "line":
            sort_direction = 1
        children = sorted(
            parent.get_children(),
            key=lambda child: child.get_centroid()[sort_direction],
        )
        for i, child in enumerate(children):
            if child == self:
                return i
        raise IndexError

    def get_child_ordinal(self, child):
        "return index of given child"
        for i in range(self.get_n_children()):
            if child == self.get_child(i):
                return i

        return NOT_FOUND

    def get_children(self):
        "return bbox (not Rect or Text) children"
        children = []
        for i in range(self.get_n_children()):
            child = self.get_child(i)
            if isinstance(child, Bbox):
                children.append(child)

        return children

    def walk_children(self, callback):
        "for each child, execute given callback"
        for child in self.get_children():
            if callback is not None:
                callback(child)
                child.walk_children(callback)

    def transform_text(self, scale, angle=0):
        "scale, rotate & shift text"
        text_widget = self.get_text_widget()
        bbox = self.bbox
        text = self.text
        if bbox and len(text):
            x, y, width, height = (
                bbox.x,
                bbox.y,
                bbox.width,
                bbox.height,
            )
            x2, y2 = (x + width, y + height)
            text_widget.set_simple_transform(0, 0, scale, angle)
            bounds = text_widget.get_bounds()
            x_offset = (x + x2 - bounds.x1 - bounds.x2) / 2
            y_offset = (y + y2 - bounds.y1 - bounds.y2) / 2
            text_widget.set_simple_transform(x_offset, y_offset, scale, angle)

    def update_box(self, text, selection):
        "Set the text in the given widget"

        rect_w = self.get_box_widget()
        rect_w.stroke_color = "black"
        rect_w.width = selection.width
        rect_w.height = selection.height
        if len(text) > 0:
            old_box = self.bbox
            old_pos_ind = self.get_position_index()
            self.translate(selection.x - old_box.x, selection.y - old_box.y)
            text_w = self.get_text_widget()
            old_conf = self.confidence
            text_w.text = text
            self.text = text
            self.confidence = _100_PERCENT

            # colour for 100% confidence
            text_w.fill_color = "black"

            # re-adjust text size & position
            if self.type != "page":
                self.bbox = selection
                text_w.set_simple_transform(0, 0, 1, 0)
                rotation = self.transformation[0]
                angle = -(self.textangle + rotation) % _360_DEGREES

                # don't scale & rotate if text has no width
                if text_w.bounds.x1 != text_w.bounds.x2:
                    scale = (selection.height if angle else selection.width) / (
                        text_w.bounds.x2 - text_w.bounds.x1
                    )
                    self.transform_text(scale, angle)

            new_conf = self.confidence
            if old_conf != new_conf:
                canvas = self.canvas
                canvas.confidence_index.remove_current_box_from_index()
                canvas.confidence_index.add_box_to_index(self, new_conf)

            new_pos_ind = self.get_position_index()
            if old_pos_ind != new_pos_ind:
                parent = self.parent
                parent.move_child(old_pos_ind, new_pos_ind)

        else:
            self.delete_box()

    def delete_box(self):
        "delete bbox"
        self.canvas.confidence_index.remove_current_box_from_index()
        try:
            self.canvas.position_index.next_word()
        except StopIteration:
            try:
                self.canvas.position_index.previous_word()
            except StopIteration:
                pass

        for i in range(self.parent.get_n_children()):
            group = self.parent.get_child(i)
            if group == self:
                self.parent.remove_child(i)
                break

        logger.info("deleted box %s at %s, %s", self.text, self.bbox.x, self.bbox.y)

    def to_hocr(self, indent=0):
        "return an hocr string of the bbox"
        string = EMPTY

        # try to preserve as much information as possible
        if self.bbox and self.type:

            # determine hOCR element types & mapping to HTML tags
            typestr = "ocr_" + self.type
            tag = "span"
            if self.type == "page":
                tag = "div"

            elif re.search(r"^(?:carea|column)$", self.type):
                typestr = "ocr_carea"
                tag = "div"

            elif self.type == "para":
                typestr = "ocr_par"
                tag = "p"

            # build properties of hOCR elements
            idn = f"id='{self.id}'" if self.id else EMPTY
            title = (
                "title="
                + "'"
                + "bbox "
                + SPACE.join([str(x) for x in rect2bboxarray(self.bbox)])
                + ("; textangle " + str(self.textangle) if self.textangle else EMPTY)
                + (
                    "; baseline " + SPACE.join([str(x) for x in self.baseline])
                    if self.baseline is not None
                    else EMPTY
                )
                + (("; x_wconf " + str(self.confidence)) if self.confidence else EMPTY)
                + "'"
            )

            # append to output (recurse to nested levels)
            if string != EMPTY:
                string += "\n"
            string += (
                SPACE * indent
                + f"<{tag} class='{typestr}' {idn} {title}>"
                + (html.escape(self.text) if (self.text != "") else "\n")
            )
            childstr = EMPTY
            for bbox in self.get_children():
                childstr += bbox.to_hocr(indent + 1)

            if childstr != EMPTY:
                childstr += SPACE * indent

            string += childstr + f"</{tag}>\n"

        return string


class ListIter:
    "an interator to allow us to index around a linear list"

    def __init__(self):
        self.list = []
        self.index = EMPTY_LIST

    def get_first_bbox(self):
        "return first bbox"
        self.index = 0
        return self.get_current_bbox()

    def get_previous_bbox(self):
        "return previous bbox"
        if self.index > 0:
            self.index -= 1

        return self.get_current_bbox()

    def get_next_bbox(self):
        "return next bbox"
        if self.index < len(self.list) - 1:
            self.index += 1

        return self.get_current_bbox()

    def get_last_bbox(self):
        "return last bbox"
        self.index = len(self.list) - 1
        return self.get_current_bbox()

    def get_current_bbox(self):
        "return bbox currently selected"
        if self.index > EMPTY_LIST:
            return self.list[self.index][0]
        raise StopIteration

    def set_index_by_bbox(self, bbox, value):
        """There may be multiple boxes with the same value, so use a binary
        search to find the next smallest confidence, and then a linear search to
        find the box"""

        l = self.get_index_for_value(value - 1)
        for i in range(l, len(self.list)):
            if self.list[i][0] == bbox:
                self.index = i
                return i

        self.index = EMPTY_LIST
        return EMPTY_LIST

    def get_index_for_value(self, value):
        """Return index of value using binary search
        https://en.wikipedia.org/wiki/Binary_search_algorithm#Alternative_procedure"""

        l = 0
        r = len(self.list) - 1
        if r == EMPTY_LIST:
            return 0
        while l != r:
            m = math.ceil((l + r) / 2)
            if self.list[m][1] > value:
                r = m - 1

            else:
                l = m

        if self.list[l][1] < value:
            l += 1

        return l

    def insert_after_position(self, bbox, i, value):
        "insert bbox after given index"

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        if i > len(self.list) - 1:
            logger.warning(
                "insert_after_position: position $i does not exist in index",
            )
            return

        self.list.insert(i + 1, [bbox, value])

    def insert_before_position(self, bbox, i, value):
        "insert bbox before given index"

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        if i > len(self.list) - 1:
            logger.warning(
                "insert_before_position: position $i does not exist in index",
            )
            return

        self.list.insert(i, [bbox, value])

    def add_box_to_index(self, bbox, value):
        "insert into list sorted by confidence level using a binary search"

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        i = self.get_index_for_value(value)
        if i > len(self.list) - 1:
            self.list.append([bbox, value])
            return

        self.insert_before_position(bbox, i, value)

    def remove_current_box_from_index(self):
        "remove the current box from the index"
        if self.index < 0:
            logger.warning("Attempted to delete undefined index from confidence list")
            return

        self.list.pop(self.index)
        self.index = min(self.index, len(self.list) - 1)


class TreeIter:
    """Class allowing us to iterate around the tree of bounding boxes

    self._bbox is a list of hierarchy of the bboxes between
    the current box (position -1) and the page box (position 0)

    self._iter is a list of the positions (i.e. which sibling) of the aboves
    boxes in the hierarchy"""

    def __init__(self, bbox):
        if not isinstance(bbox, Bbox):
            raise TypeError("bbox is not a Bbox object")

        self._bbox = [bbox]
        self._iter = []
        while bbox.type != "page":
            parent = bbox.parent
            self._iter.insert(0, parent.get_child_ordinal(bbox))
            self._bbox.insert(0, parent)
            bbox = parent
        self._iter.insert(0, 0)  # for page
        # Now _bbox and _iter have same length.
        # Top of stacks are the initial bbox and its index in parent.

    def first_bbox(self):
        "return first bbox"
        self._bbox = [self._bbox[0]]
        self._iter = [0]
        return self._bbox[0]

    def first_word(self):
        "return first word"
        bbox = self.first_bbox()
        if bbox.type != "word":
            return self.next_word()
        return bbox

    def next_bbox(self):
        "return next word"

        # Save state in case we need to restore it after StopIteration
        old_bbox = self._bbox.copy()
        old_iter = self._iter.copy()

        current = self._bbox[-1]

        # 1. Try to go down to first child
        n = current.get_n_children()
        for i in range(n):
            child = current.get_child(i)
            if isinstance(child, Bbox):
                self._bbox.append(child)
                self._iter.append(i)
                return child

        # 2. No children, try to go to next sibling
        while len(self._bbox) > 1:
            self._bbox.pop()
            last_idx = self._iter.pop()
            parent = self._bbox[-1]
            n_parent = parent.get_n_children()

            for i in range(last_idx + 1, n_parent):
                sibling = parent.get_child(i)
                if isinstance(sibling, Bbox):
                    self._bbox.append(sibling)
                    self._iter.append(i)
                    return sibling

        # Restore state before raising
        self._bbox = old_bbox
        self._iter = old_iter
        raise StopIteration

    def next_word(self):
        "return next bbox"
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.next_bbox()
        while bbox.type != "word":
            try:
                bbox = self.next_bbox()
            except StopIteration as exc:
                self._iter = current_iter
                self._bbox = current_bbox
                raise StopIteration from exc
        return bbox

    def previous_bbox(self):
        "return previous bbox"
        if len(self._bbox) <= 1:
            raise StopIteration

        self._bbox.pop()
        last_idx = self._iter.pop()
        parent = self._bbox[-1]

        # Try to find a previous sibling
        for i in range(last_idx - 1, -1, -1):
            sibling = parent.get_child(i)
            if isinstance(sibling, Bbox):
                self._bbox.append(sibling)
                self._iter.append(i)
                return self.last_leaf()

        # No previous sibling, previous is the parent itself
        return parent

    def previous_word(self):
        "return previous word"
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.previous_bbox()
        while bbox.type != "word":
            try:
                bbox = self.previous_bbox()
            except StopIteration as exc:
                self._iter = current_iter
                self._bbox = current_bbox
                raise StopIteration from exc

        if bbox == current_bbox[-1]:
            self._iter = current_iter
            self._bbox = current_bbox
            raise StopIteration

        return bbox

    def last_bbox(self):
        "return last bbox"
        self._bbox = [self._bbox[0]]
        self._iter = [1]
        return self.last_leaf()

    def last_word(self):
        "return last word"
        bbox = self.last_bbox()
        while bbox is not None and bbox.type != "word":
            bbox = self.previous_bbox()

        return bbox

    def last_leaf(self):
        "return last bbox"
        n = self._bbox[-1].get_n_children() - 1
        while n > EMPTY_LIST:
            child = self._bbox[-1].get_child(n)
            if isinstance(child, Bbox):
                self._iter.append(n)
                self._bbox.append(child)
                return self.last_leaf()
            n -= 1

        return self._bbox[-1]

    def get_current_bbox(self):
        "return bbox currently being viewed"
        return self._bbox[-1]


class Rectangle(Gdk.Rectangle):
    "Helper class so that we can parse arguments when initialising"

    def __init__(self, **kwargs):
        super().__init__()
        for key in ["x", "y", "width", "height"]:
            if key not in kwargs:
                raise AttributeError(f"Rectangle requires attribute '{key}'.")
            setattr(self, key, kwargs[key])

    @classmethod
    def from_bbox(cls, x1, y1, x2, y2):
        "Create Rectangle from hocr bbox coords"
        return Rectangle(x=x1, y=y1, width=abs(x2 - x1), height=abs(y2 - y1))

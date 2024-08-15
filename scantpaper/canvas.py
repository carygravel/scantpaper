import re
import math
import html
import gi
import logging

gi.require_version("GooCanvas", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GObject, GooCanvas

from bboxtree import Bboxtree

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


def rect2bboxarray(rect):

    return [
        int(rect.x),
        int(rect.y),
        int(rect.x + rect.width),
        int(rect.y + rect.height),
    ]


def rgb2hsv(rgb):
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

    if maxv > 0:  # NOTE: if Max is == 0, this divide would cause a crash
        hsv["s"] = delta / maxv
    else:
        # if max is 0, then r = g = b = 0
        # s = 0, h is undefined

        hsv["s"] = 0
        hsv["h"] = 0  # undefined
        return hsv

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
    return rgb2hsv(string2rgb(spec))


def string2rgb(spec):
    color = Gdk.RGBA()
    flag = color.parse(spec)
    return color


def linear_interpolation(x1, x2, m):
    return x1 * (1 - m) + x2 * m


def hsv2rgb(hsv):
    out = Gdk.Color(0, 0, 0)
    if hsv["s"] <= 0.0:  # < is bogus, just shuts up warnings
        out.red = hsv["v"]
        out.green = hsv["v"]
        out.blue = hsv["v"]
        return out

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
    offset = GObject.Property(type=object, nick="Image offset", blurb="dict of x, y")
    max_color = GObject.Property(
        type=str,
        default="black",
        nick="Maximum color",
        blurb="Color for maximum confidence",
    )
    max_color_hsv = GObject.Property(
        type=object,
        nick="Maximum color (HSV)",
        blurb="HSV Color for maximum confidence",
    )
    min_color = GObject.Property(
        type=str,
        default="red",
        nick="Minimum color",
        blurb="Color for minimum confidence",
    )
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
        self.old_idles = {}
        self.device = Gdk.Display.get_default().get_default_seat().get_pointer()

        # Set up the canvas
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

        self.offset = Gdk.Rectangle()
        self.current_index = "position"
        self.position_index = None

        # allow the widget to accessed via CSS
        self.set_name("gscan2pdf-ocr-canvas")

    def SET_PROPERTY(self, pspec, newval):

        name = pspec.get_name()
        oldval = self.get(name)
        if (newval is not None) and (oldval is not None) and newval != oldval:
            if name == "offset":
                if (newval is not None) ^ (oldval is not None):
                    self[name] = newval
                    self.scroll_to(-newval["x"], -newval["y"])
                    self.emit("offset-changed", newval["x"], newval["y"])

            elif name == "max_color":
                self[name] = newval
                self.max_color_hsv = string2hsv(newval)

            elif name == "min_color":
                self[name] = newval
                self.min_color_hsv = string2hsv(newval)

            else:
                self[name] = newval

            #                $self->SUPER::SET_PROPERTY( $pspec, $newval );

        return

    def get_max_color_hsv(self):

        val = self.max_color_hsv
        if val is None:
            self.max_color_hsv = string2hsv(self.max_color)
            return self.max_color_hsv

        return val

    def get_min_color_hsv(self):

        val = self.min_color_hsv
        if val is None:
            self.min_color_hsv = string2hsv(self.min_color)
            return self.min_color_hsv

        return val

    def set_text(
        self, page, layer, edit_callback, idle, finished_callback=None
    ):  # FIXME: why is this called twice when running OCR from tools?

        if idle is None:
            idle = True

        if self.old_idles:
            for box, source in self.old_idles.items():
                Glib.Source.remove(source)
                del self.old_idles[box]

        self.position_index = None
        root = GooCanvas.CanvasGroup()
        width, height = page.get_size()
        xres, yres, units = page.get_resolution()

        self.set_root_item(root)
        self.pixbuf_size = {"width": width, "height": height}
        self.set_bounds(0, 0, width, height)

        # Attach the text to the canvas
        self.confidence_index = ListIter()
        tree = Bboxtree(getattr(page, layer))
        itr = tree.each_bbox()
        box = next(itr)
        if box is None:
            return
        options = {
            "iter": itr,
            "box": box,
            "parents": [root],
            "transformations": [[0, 0, 0]],
            "edit_callback": edit_callback,
            "idle": idle,
            "finished_callback": finished_callback,
        }
        if idle:

            def anonymous_01():
                self._boxed_text(options)
                del self.old_idles[box]
                return Glib.SOURCE_REMOVE

            self.old_idles[box] = Glib.Idle.add(anonymous_01)

        else:
            self._boxed_text(options)

    def get_first_bbox(self):

        bbox = None
        if self.current_index == "confidence":
            bbox = self.confidence_index.get_first_bbox()
        else:
            bbox = self.position_index.first_word()

        self.set_other_index(bbox)
        return bbox

    def get_previous_bbox(self):
        bbox = None
        if self.current_index == "confidence":
            bbox = self.confidence_index.get_previous_bbox()
        else:
            bbox = self.position_index.previous_word()

        self.set_other_index(bbox)
        return bbox

    def get_next_bbox(self):
        bbox = None
        if self.current_index == "confidence":
            bbox = self.confidence_index.get_next_bbox()
        else:
            bbox = self.position_index.next_word()

        self.set_other_index(bbox)
        return bbox

    def get_last_bbox(self):

        bbox = None
        if self.current_index == "confidence":
            bbox = self.confidence_index.get_last_bbox()

        else:
            bbox = self.position_index.last_word()

        self.set_other_index(bbox)
        return bbox

    def get_current_bbox(self):

        bbox = None
        if self.current_index == "confidence":
            bbox = self.confidence_index.get_current_bbox()

        else:
            bbox = self.position_index.get_current_bbox()

        self.set_other_index(bbox)
        return bbox

    def set_index_by_bbox(self, bbox):

        if bbox is None:
            return
        if self.current_index == "confidence":
            return self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)

        self.position_index = TreeIter([bbox])

    def set_other_index(self, bbox):

        if bbox is None:
            return
        if self.current_index == "confidence":
            self.position_index = TreeIter([bbox])

        else:
            self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)

    def get_pixbuf_size(self):

        return self.pixbuf_size

    def clear_text(self):

        self.set_root_item(GooCanvas.CanvasGroup())
        self.pixbuf_size = None

    def set_offset(self, offset_x, offset_y):

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
        self.offset = {"x": offset_x, "y": offset_y}
        return

    def get_offset(self):
        return self.offset

    def get_bbox_at(self, bbox):
        x = bbox.x + bbox.width / 2
        y = bbox.y + bbox.height / 2
        parent = self.get_item_at(x, y, False)
        while parent is not None and (
            not hasattr(parent, "type") or parent.type == "word"
        ):
            parent = parent.get_parent()

        return parent

    def add_box(self, **kwargs):
        if "parent" in kwargs:
            parent = kwargs["parent"]
        else:
            parent = self.get_bbox_at(kwargs["bbox"])
            if parent is None:
                return

        transformation = [0, 0, 0]
        if "transformation" in kwargs:
            transformation = kwargs["transformation"]
        elif isinstance(parent, Bbox):
            parent_box = parent.bbox
            transformation = [parent.textangle, parent_box.x, parent_box.y]

        options2 = {
            "canvas": self,
            "parent": parent,
            "bbox": kwargs["bbox"],
            "transformation": transformation,
        }
        if len(kwargs["text"]):
            options2["text"] = kwargs["text"]

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
            self.position_index = TreeIter([bbox])

        if bbox is not None and len(kwargs["text"]) > 0:
            self.confidence_index.add_box_to_index(bbox, bbox.confidence)

            # clicking text box produces a dialog to edit the text
            if "edit_callback" in kwargs:

                def anonymous_02(widget, target, event):

                    if event.button() == 1:
                        parent.get_parent()["dragging"] = False
                        kwargs["edit_callback"](widget, target, event, bbox)

                bbox.connect("button-press-event", anonymous_02)

        return bbox

    def _boxed_text(self, options):
        "Draw text on the canvas with a box around it"
        box = options["box"]

        # each call should use own copy of arrays to prevent race conditions
        transformations = options["transformations"]
        parents = options["parents"]
        transformation = transformations[box["depth"]]
        rotation, x0, y0 = transformation
        x1, y1, x2, y2 = box["bbox"]
        textangle = box["textangle"] if "textangle" in box else 0

        # copy box parameters from method arguments
        options2 = {"parent": parents[box["depth"]]}
        options2["edit_callback"] = options["edit_callback"]
        options2["text"] = box["text"] if "text" in box else ""

        # copy parameters from box from OCR output
        for key in ["baseline", "confidence", "id", "textangle", "type"]:
            if key in box:
                options2[key] = box[key]

        options2["bbox"] = Rectangle(
            x=x1, y=y1, width=abs(x2 - x1), height=abs(y2 - y1)
        )
        bbox = self.add_box(**options2)

        # always one more parent, as the page has a root
        if box["depth"] + 1 > len(parents) - 1:
            parents.append(bbox)
        else:
            parents[box["depth"] + 1] = bbox

        transformations.append([textangle + rotation, x1, y1])
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
        if options["idle"]:

            def anonymous_03():
                self._boxed_text(options3)
                del self.old_idles[child]
                return Glib.SOURCE_REMOVE

            self.old_idles[child] = Glib.Idle.add(anonymous_03)

        else:
            self._boxed_text(options3)

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

    def hocr(self):
        """Convert the canvas into hocr"""
        if self.get_pixbuf_size() is None:
            return
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
        """convert x, y in widget distance to image distance"""
        zoom = self.get_scale()
        return x / zoom, y / zoom

    def _set_zoom_with_center(self, zoom, center_x, center_y):
        """set zoom with centre in image coordinates"""
        if zoom > MAX_ZOOM:
            zoom = MAX_ZOOM
        allocation = self.get_allocation()
        offset_x = allocation.width / 2 / zoom - center_x
        offset_y = allocation.height / 2 / zoom - center_y
        self.set_scale(zoom)
        self.emit("zoom-changed", zoom)
        self.set_offset(offset_x, offset_y)
        return

    def _button_pressed(self, event):

        # middle mouse button

        if event.button() == 2:

            # Using the root window x,y position for dragging the canvas, as the
            # values returned by event.x and y cause a bouncing effect, and
            # only the value since the last event is required.

            screen, x, y = self.device.get_position()
            self.drag_start = {"x": x, "y": y}
            self.dragging = True

        #    self.update_cursor( event.x, event.y );

        # allow the event to propagate in case the user was clicking on text to edit

        return

    def _button_released(self, event):

        if event.button() == 2:
            self.dragging = False

        #    self.update_cursor( event.x, event.y );

        return

    def _motion(self, event):

        if not self.dragging:
            return False
        offset = self.get_offset()
        zoom = self.get_scale()
        screen, x, y = self.device.get_position()
        offset_x = offset["x"] + (x - self.drag_start["x"]) / zoom
        offset_y = offset["y"] + (y - self.drag_start["y"]) / zoom
        (self.drag_start["x"], self.drag_start["y"]) = (x, y)
        self.set_offset(offset_x, offset_y)
        return

    def _scroll(self, event):

        (center_x, center_y) = self.convert_from_pixels(event.x(), event.y())
        zoom = None
        if event.direction() == "up":
            zoom = self.get_scale() * 2

        else:
            zoom = self.get_scale() / 2

        self._set_zoom_with_center(zoom, center_x, center_y)

        # don't allow the event to propagate, as this pans it in y

        return True

    def sort_by_confidence(self):

        self.current_index = "confidence"
        return

    def sort_by_position(self):

        self.current_index = "position"
        return


class Bbox(GooCanvas.CanvasGroup):

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
        type=object, nick="Transformation", blurb="Hash of angle, x, y"
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
        # parent = kwargs["parent"]
        # if isinstance(parent, Bbox) and parent.get_n_children() > 1:
        #     del kwargs["parent"]

        # if "parent" not in kwargs:
        #     i = parent.get_stack_index_by_position(self)
        #     parent.add_child(self, i)

        rotation, x0, y0 = self.transformation
        x, y, width, height = (
            self.bbox.x,
            self.bbox.y,
            self.bbox.width,
            self.bbox.height,
        )
        self.translate(x - x0, y - y0)
        textangle = self.textangle
        color = self.confidence2color()

        # draw the rect first to make sure the text goes on top
        # and receives any mouse clicks
        rect = GooCanvas.CanvasRect(
            parent=self,
            x=0,
            y=0,
            width=width,
            height=height,
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
                x=width / 2,
                y=height / 2,
                width=-1,
                anchor="center",
                font="Sans",
                fill_color=color,
            )
            angle = -(textangle + rotation) % _360_DEGREES
            bounds = text.get_bounds()
            if bounds.x2 - bounds.x1 == 0:
                logger.error(f"text '{self.text}' has no width, skipping")
                return

            scale = (height if angle else width) / (bounds.x2 - bounds.x1)

            # gocr case: gocr creates text only which we treat as page text
            if self.type == "page":
                scale *= FULLPAGE_OCR_SCALE

            self.transform_text(scale, angle)

    def get_tree_iter(self):
        """an iterator for depth-first walking the bboxes below self
        iterator returns bbox
         my $iter = $self->get_tree_iter();
         while (my $bbox = $iter->()) {}"""
        iter = 0
        tree = self
        assert False
        # TODO: copy iter code
        # return sub :
        #     bbox = tree[-1]
        #     i    = iter[-1]
        #     n    = bbox.get_n_children
        #     if iter[-1] < n :
        #         bbox = bbox.get_child(i)
        #         push tree, bbox
        #         push iter, 0
        #         return bbox

        #     while iter[-1] >= n :
        #         pop tree
        #         pop iter
        #         if not tree :
        #             return
        #         bbox = tree[-1]
        #         n    = bbox.get_n_children
        #         iter[-1] += 1

        #     return bbox

    def get_stack_index_by_position(self, bbox):
        """given a parent bbox and a new box, return the index
        where the new box should be inserted in the stack of children.
        Using binary search
        https://en.wikipedia.org/wiki/Binary_search_algorithm#Alternative_procedure"""

        l = 0
        r = self.get_n_children() - 1
        child = self.get_child(l)
        while not isinstance(child, Bbox) and l < r:
            l += 1
            child = self.get_child(l)

        child = self.get_child(r)
        while not isinstance(child, Bbox) and l < r:
            r -= 1
            child = self.get_child(r)

        newboxpos = bbox.get_centroid()
        axis = 0 if self.type == "line" else 1
        while l != r:
            m = math.ceil((l + r) / 2)
            child = self.get_child(m)
            while not isinstance(child, Bbox):
                if m > l:
                    m -= 1
                elif m < r:
                    m += 1
                else:
                    last
                child = self.get_child(m)

            boxpos = child.get_centroid()
            if boxpos[axis] > newboxpos[axis]:
                r = m - 1

            else:
                l = m

        boxpos = self.get_child(l).get_centroid()
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
        return "#%04x%04x%04x" % (
            int(rgb.red * MAX_COLOR_INT),
            int(rgb.green * MAX_COLOR_INT),
            int(rgb.blue * MAX_COLOR_INT),
        )

    def get_box_widget(self):
        return self.get_child(0)

    def get_text_widget(self):

        child = self.get_child(1)
        if isinstance(child, GooCanvas.CanvasText):
            return child

    def get_centroid(self):

        bbox = self.bbox
        return bbox.x + bbox.width / 2, bbox.y + bbox.height / 2

    def get_position_index(self):

        parent = self.get_property("parent")
        while parent and not isinstance(parent, Bbox):
            parent = parent.get_property("parent")

        sort_direction = 0
        if parent.type != "line":
            sort_direction = 1
        # children = parent.get_children().sorted(key=lambda child: child.get_centroid()[sort_direction])
        children = parent.get_children()
        children = sorted(
            children, key=lambda child: child.get_centroid()[sort_direction]
        )
        for i, child in enumerate(children):
            if child == self:
                return i

    def get_child_ordinal(self, child):
        for i in range(self.get_n_children()):
            if child == self.get_child(i):
                return i

        return NOT_FOUND

    def get_children(self):

        children = []
        for i in range(self.get_n_children()):
            child = self.get_child(i)
            if isinstance(child, Bbox):
                children.append(child)

        return children

    def walk_children(self, callback):

        for child in self.get_children:
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
            bounds = text_widget.bounds
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
                bounds = text_w.bounds
                transformation = self.transformation
                rotation = transformation[0]
                textangle = self.textangle
                angle = -(textangle + rotation) % _360_DEGREES

                # don't scale & rotate if text has no width
                if bounds.x1 != bounds.x2:
                    scale = (selection.height if angle else selection.width) / (
                        bounds.x2 - bounds.x1
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
        self.canvas.confidence_index.remove_current_box_from_index()
        bbox = self.canvas.position_index.next_word()
        if bbox is None:
            bbox = self.canvas.position_index.previous_word()

        parent = self.parent
        for i in range(parent.get_n_children()):
            group = parent.get_child(i)
            if group == self:
                parent.remove_child(i)
                break

        logger.info(
            f"deleted box {self.text} at {self.bbox.x}, {self.bbox.y}",
        )

    def to_hocr(self, indent=0):

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
            id = f"id='{self.id}'" if self.id else EMPTY
            title = (
                "title="
                + "'"
                + "bbox "
                + SPACE.join([str(x) for x in rect2bboxarray(self.bbox)])
                + ("; textangle " + str(self.textangle) if self.textangle else EMPTY)
                + (
                    "; baseline " + SPACE.join(str(x) for x in self.baseline)
                    if self.baseline
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
                + f"<{tag} class='{typestr}' {id} {title}>"
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
    def __init__(self):

        self.list = []
        self.index = EMPTY_LIST

    def get_first_bbox(self):

        self.index = 0
        return self.get_current_bbox()

    def get_previous_bbox(self):
        if self.index > 0:
            self.index -= 1

        return self.get_current_bbox()

    def get_next_bbox(self):
        if self.index < len(self.list) - 1:
            self.index += 1

        return self.get_current_bbox()

    def get_last_bbox(self):

        self.index = len(self.list) - 1
        return self.get_current_bbox()

    def get_current_bbox(self):

        if self.index > EMPTY_LIST:
            return self.list[self.index][0]

        return

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

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        if i > len(self.list) - 1:
            logger.warning(
                "insert_after_position: position $i does not exist in index",
            )
            return

        self.list.insert(i + 1, [bbox, value])

    def insert_after_box(self, bbox):

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

    def insert_before_position(self, bbox, i, value):

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        if i > len(self.list) - 1:
            logger.warning(
                "insert_before_position: position $i does not exist in index",
            )
            return

        self.list.insert(i, [bbox, value])

    def insert_before_box(self, bbox):

        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return

        return

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
        return

    def remove_current_box_from_index(self):

        if self.index < 0:
            logger.warning("Attempted to delete undefined index from confidence list")
            return

        self.list.pop(self.index)
        if self.index > len(self.list) - 1:
            self.index = len(self.list) - 1


class TreeIter:  # TODO: rewrite with proper python iterators
    """Class allowing us to iterate around the tree of bounding boxes

    self._bbox is a list of hierarchy of the bboxes between
    the current box (position -1) and the page box (position 0)

    self._iter is a list of the positions (i.e. which sibling) of the aboves
    boxes in the hierarchy

    """

    def __init__(self, bboxes, itr=None):
        for bbox in bboxes:
            if not isinstance(bbox, Bbox):
                raise TypeError("bbox is not a Bbox object")

        self._bbox = bboxes
        if itr is None:
            self._iter = []
        else:
            self._iter = itr
        while self._bbox[0].type != "page":
            parent = bbox.parent
            self._iter.insert(0, parent.get_child_ordinal(bbox))
            self._bbox.insert(0, parent)
            bbox = parent
        self._iter.insert(0, 1)  # for page

    def first_bbox(self):

        self._bbox = [self._bbox[0]]
        self._iter = [1]
        return self._bbox[0]

    def first_word(self):

        bbox = self.first_bbox()
        if bbox.type != "word":
            return self.next_word()

        return bbox

    def next_bbox(self):
        "depth first"

        current = self._bbox[-1]

        # look through children
        n = current.get_n_children()
        while self._iter[-1] < n:
            child = current.get_child(self._iter[-1])
            if isinstance(child, Bbox):
                self._bbox.append(child)
                self._iter.append(current.get_child_ordinal(child))
                return child

            self._iter[-1] += 1

        # no children - look at next sibling
        if len(self._bbox) > 1:
            if self._bbox[-2].get_n_children() - 1 > self._iter[-1]:
                self._bbox[-1] = self._bbox[-2].get_child(self._iter[-1])
                return self._bbox[-1]

            # traverse up until we can increment an index
            while len(self._bbox) > 2:
                self._bbox.pop()
                self._iter.pop()
                if self._bbox[-2].get_n_children() - 1 > self._iter[-1]:
                    self._iter[-1] += 1
                    self._bbox[-1] = self._bbox[-2].get_child(self._iter[-1])
                    return self._bbox[-1]

    def next_word(self):
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.next_bbox()
        while bbox is not None and bbox.type != "word":
            bbox = self.next_bbox()

        if bbox is None:
            self._iter = current_iter
            self._bbox = current_bbox
            return

        return bbox

    def previous_bbox(self):
        "depth first"
        # if we're not on the first sibling
        if self._iter[-1] > 1:

            # pick the previous sibling
            while self._iter[-1] > 1:
                self._iter[-1] -= 1
                self._bbox[-1] = self._bbox[-2].get_child(self._iter[-1])
                # self._bbox[-1] = self._bbox[-2].get_children()[self._iter[-1]]
                if isinstance(self._bbox[-1], Bbox):
                    return self.last_leaf()

        # don't pop the root bbox
        if len(self._bbox) > 1:

            # otherwise the previous box is just the parent
            self._iter.pop()
            self._bbox.pop()
            if len(self._bbox) == 0:
                return
            return self._bbox[-1]

    def previous_word(self):
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.previous_bbox()
        while bbox is not None and bbox.type != "word":
            bbox = self.previous_bbox()

        if bbox is None or bbox == current_bbox[-1]:
            self._iter = current_iter
            self._bbox = current_bbox
            return

        return bbox

    def last_bbox(self):
        "depth first"

        self._bbox = [self._bbox[0]]
        self._iter = [1]
        return self.last_leaf()

    def last_word(self):

        bbox = self.last_bbox()
        while bbox is not None and bbox.type != "word":
            bbox = self.previous_bbox()

        return bbox

    def last_leaf(self):

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

        return self._bbox[-1]


class Rectangle(Gdk.Rectangle):
    "Helper class so that we can parse arguments when initialising"

    def __init__(self, **kwargs):
        super().__init__()
        for key in ["x", "y", "width", "height"]:
            if key not in kwargs:
                raise AttributeError(f"Rectangle requires attribute '{key}'.")
            setattr(self, key, kwargs[key])

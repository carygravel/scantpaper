"""Classes to do with displaying HOCR output."""

from __future__ import annotations

import html
import logging
import math
import re
from typing import TYPE_CHECKING, Any, ClassVar, cast

import gi

from scantpaper.bboxtree import is_empty_branch
from scantpaper.const import _100_PERCENT, EMPTY, EMPTY_LIST, NOT_FOUND, SPACE
from scantpaper.gobject import property_

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.bboxtree import BBox

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import (  # noqa: E402
    Gdk,
    GLib,
    GObject,
    Gtk,
    Pango,
    PangoCairo,
)

MAX_COLOR_INT = 65535
COLOR_TOLERANCE = 0.00001
_60_DEGREES = 60
MIN_ZOOM = 0.001
MAX_ZOOM = 15
MAX_CONFIDENCE_DEFAULT = 95
MIN_CONFIDENCE_DEFAULT = 50
FULLPAGE_OCR_SCALE = 0.8
COLOR_GREEN = 2
COLOR_CYAN = 3
COLOR_BLUE = 4
COLOR_YELLOW = 6
_360_DEGREES = 360
BATCH_SIZE = 100
LAYOUT_FONT_DESCRIPTION = "Sans 10"
HOCR_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper $Gscan2pdf::Canvas::VERSION' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
"""

logger = logging.getLogger(__name__)


def rect2bboxarray(rect: Gdk.Rectangle) -> list[int]:
    """Given a Rectangle(), return an array of int suitable for hocr output."""
    return [
        int(rect.x),
        int(rect.y),
        int(rect.x + rect.width),
        int(rect.y + rect.height),
    ]


def rgb2hsv(rgb: Gdk.RGBA) -> dict[str, float]:
    """Convert from rgb to hsv colour space."""
    minv = min(rgb.green, rgb.red)
    minv = min(rgb.blue, minv)
    maxv = max(rgb.green, rgb.red)
    maxv = max(rgb.blue, maxv)
    hsv = {}
    hsv["v"] = maxv
    delta = maxv - minv
    if delta < COLOR_TOLERANCE:
        hsv["s"] = 0
        hsv["h"] = 0
        return cast("dict[str, float]", (hsv))

    hsv["s"] = delta / maxv

    if rgb.red >= maxv:
        hsv["h"] = (rgb.green - rgb.blue) / delta

    elif rgb.green >= maxv:
        hsv["h"] = COLOR_GREEN + (rgb.blue - rgb.red) / delta

    else:
        hsv["h"] = COLOR_BLUE + (rgb.red - rgb.green) / delta

    hsv["h"] *= _60_DEGREES
    if hsv["h"] < 0.0:
        hsv["h"] += _360_DEGREES

    return cast("dict[str, float]", (hsv))


def string2hsv(spec: str) -> dict[str, float]:
    """Return hsv color from string."""
    return rgb2hsv(string2rgb(spec))


def string2rgb(spec: str) -> Gdk.RGBA:
    """Return Gdk.RGBA object from string."""
    color = Gdk.RGBA()
    _flag = color.parse(spec)
    return color


def linear_interpolation(x1: float, x2: float, m: float) -> float:
    """1D linear interpolation."""
    return x1 * (1 - m) + x2 * m


def hsv2rgb(hsv: dict[str, float]) -> Gdk.RGBA:
    """Convert from hsv to rgb colour space."""
    if hsv["s"] <= 0.0:
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


def _collect_words(node: object, words: list[Bbox]) -> None:
    """Append every word beneath node to words, in reading order."""
    for child in node.get_children():  # type: ignore[attr-defined]
        if child.type == "word":
            words.append(child)
        else:
            _collect_words(child, words)


def _reading_order_neighbours(
    bbox: Bbox, words: list[Bbox]
) -> tuple[Bbox | None, Bbox | None]:
    """Return the words immediately after and before bbox in reading order.

    Deleting a word leaves the navigation cursor with nothing to point at, so
    the neighbours are read off the pre-deletion reading order: the next word
    is preferred, and the previous one is used when there is no next.
    """
    for i, word in enumerate(words):
        if word is bbox:
            following = words[i + 1] if i + 1 < len(words) else None
            preceding = words[i - 1] if i > 0 else None
            return following, preceding
    return None, None


def _clamp_direction(offset: float, allocation: float, pixbuf_size: float) -> float:
    """Centre the image if it is smaller than the widget."""
    if allocation > pixbuf_size:
        offset = (allocation - pixbuf_size) / 2

    elif offset > 0:
        offset = 0

    elif offset < allocation - pixbuf_size:
        offset = allocation - pixbuf_size

    return offset


def button_press_callback(
    bbox: Bbox,
    _target: Gtk.Widget,
    event: Gdk.EventButton,
    edit_callback: Callable[..., object],
) -> None:
    """Button press callback."""
    if event.button == 1:
        canvas = cast("Canvas", bbox.canvas)
        if canvas:
            canvas.dragging = False
        edit_callback(bbox, _target)
        bbox.emit("clicked")


class Rectangle(Gdk.Rectangle):
    """Helper class so that we can parse arguments when initialising."""

    def __init__(self, **kwargs: object) -> None:
        """Initialise Rectangle."""
        super().__init__()
        for key in ["x", "y", "width", "height"]:
            if key not in kwargs:
                msg = f"Rectangle requires attribute '{key}'."
                raise AttributeError(msg)
            setattr(self, key, kwargs[key])

    @classmethod
    def from_bbox(
        cls: type[Rectangle], x1: float, y1: float, x2: float, y2: float
    ) -> Rectangle:
        """Create Rectangle from hocr bbox coords."""
        return Rectangle(x=x1, y=y1, width=abs(x2 - x1), height=abs(y2 - y1))


class Bbox:
    """Bounding box with text, rectangle, and hierarchy info for OCR display."""

    def __init__(self, **kwargs: object) -> None:
        """Initialise Rectangle."""
        self.parent: Bbox | _CanvasRoot | None = None
        self.children: list[Bbox] = []
        self._callbacks = {}
        self._text_widget = None

        self.text: str = cast("str", kwargs.get("text", EMPTY))
        self.bbox = kwargs.get("bbox")
        self.canvas = kwargs.get("canvas")
        self.transformation: list[int] = cast(
            "list[int]", kwargs.get("transformation", [0, 0, 0])
        )
        self.confidence = kwargs.get("confidence")
        self.textangle: int = cast("int", kwargs.get("textangle", 0))
        self.type: str = cast("str", kwargs.get("type", "word"))
        self.id = kwargs.get("id", EMPTY)
        self.baseline: list[int | float] | None = cast(
            "list[int | float] | None", kwargs.get("baseline")
        )
        self.edit_callback = kwargs.get("edit_callback")

        parent = cast("Bbox | _CanvasRoot | None", kwargs.get("parent"))
        if parent is not None:
            parent.children.append(self)
            self.parent = parent

    def connect(
        self, signal: str, callback: Callable[..., object], *args: object
    ) -> None:
        """Connect a callback to a signal."""
        if signal not in self._callbacks:
            self._callbacks[signal] = []
        self._callbacks[signal].append((callback, args))

    def emit(self, signal: str, *args: object) -> None:
        """Emit a signal."""
        for callback, cb_args in self._callbacks.get(signal, []):
            callback(*args, *cb_args)

    def get_children(self) -> list[Bbox]:
        """Return bbox children.

        The live ``children`` list is returned so that structural edits made by
        the caller are reflected in the scene graph. Non-``Bbox`` items are not
        expected here; ``Bbox.__init__`` is the only place that appends.
        """
        return self.children

    def detach_from_parent(self) -> None:
        """Remove this bbox from its parent by identity."""
        if self.parent is None:
            return
        for i, child in enumerate(self.parent.children):
            if child is self:
                del self.parent.children[i]
                break

    def get_n_children(self) -> int:
        """Return number of bbox children."""
        return len(self.get_children())

    def get_child(self, i: int) -> Bbox:
        """Return i-th bbox child."""
        return self.get_children()[i]

    def get_centroid(self) -> tuple[float, float]:
        """Return centroid of bbox."""
        bbox = self.bbox
        return cast(
            "tuple[float, float]", (bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)
        )

    def get_position_index(self) -> int:
        """Return positional index of bbox."""
        parent = self.parent
        while parent is not None and not isinstance(parent, Bbox):
            parent = parent.parent

        sort_direction = 0
        if parent is not None and parent.type != "line":
            sort_direction = 1
        children = sorted(
            parent.get_children(),
            key=lambda child: child.get_centroid()[sort_direction],
        )
        for i, child in enumerate(children):
            if child == self:
                return i
        raise IndexError

    def get_child_ordinal(self, child: Bbox) -> int:
        """Return index of given child."""
        children = self.get_children()
        for i, candidate in enumerate(children):
            if child == candidate:
                return i
        return NOT_FOUND

    def walk_children(self, callback: Callable[..., object] | None) -> None:
        """For each child, execute given callback."""
        for child in self.get_children():
            if callback is not None:
                callback(child)
                child.walk_children(callback)

    def confidence2color(self) -> str:
        """Convert confidence percentage into colour using pre-calculated lookup table."""
        return cast("str", (self.canvas.get_color_for_confidence(self.confidence)))

    def set_word(self, text: str, selection: Gdk.Rectangle) -> None:
        """Set this word's text, geometry and confidence. No side effects."""
        self.text = text
        self.confidence = _100_PERCENT
        if self.type != "page":
            self.bbox = selection

    def update_box(self, text: str, selection: Gdk.Rectangle) -> None:
        """Correct this word's text, keeping the canvas indexes consistent.

        The structural work belongs to the Canvas, which owns the scene graph;
        this is only the entry point used by the editing controls.
        """
        if self.canvas is None:
            self.set_word(text, selection)
            return
        self.canvas.update_word(self, text, selection)

    def delete_box(self) -> None:
        """Delete this word from the canvas scene graph."""
        if self.canvas is not None:
            self.canvas.delete_word(self)

        logger.info("deleted box %s at %s, %s", self.text, self.bbox.x, self.bbox.y)

    def to_hocr(self, indent: int = 0) -> str:
        """Return an hocr string of the bbox."""
        string = EMPTY

        if self.bbox and self.type:
            typestr = "ocr_" + self.type
            tag = "span"
            if self.type == "page":
                tag = "div"

            elif re.search(r"^(?:carea|column)$", str(self.type)):
                typestr = "ocr_carea"
                tag = "div"

            elif self.type == "para":
                typestr = "ocr_par"
                tag = "p"

            idn = f"id='{self.id}'" if self.id else EMPTY
            title = (
                "title="
                "'"
                "bbox "
                + SPACE.join([str(x) for x in rect2bboxarray(self.bbox)])
                + ("; textangle " + str(self.textangle) if self.textangle else EMPTY)
                + (
                    "; baseline " + SPACE.join([str(x) for x in self.baseline])
                    if self.baseline is not None
                    else EMPTY
                )
                + (
                    "; x_wconf " + str(self.confidence)
                    if self.confidence is not None
                    else EMPTY
                )
                + "'"
            )

            string += (
                SPACE * indent
                + f"<{tag} class='{typestr}' {idn} {title}>"
                + (html.escape(cast("str", self.text)) if (self.text != "") else "\n")
            )
            childstr = EMPTY
            for bbox in self.get_children():
                childstr += bbox.to_hocr(indent + 1)

            if childstr != EMPTY:
                childstr += SPACE * indent

            string += childstr + f"</{tag}>\n"

        return string

    def get_stack_index_by_position(self, bbox: Bbox) -> int:
        """Given a parent bbox and a new box, return the stack insertion index.

        Using binary search.
        """
        children = self.get_children()
        lo = 0
        r = len(children) - 1

        newboxpos = bbox.get_centroid()
        axis = 0 if self.type == "line" else 1

        while lo <= r:
            m = (lo + r) // 2
            child = children[m]
            boxpos = child.get_centroid()
            if boxpos[axis] > newboxpos[axis]:
                r = m - 1
            else:
                lo = m + 1

        return lo


class _CanvasRoot:
    """Root container for the Bbox tree."""

    def __init__(self) -> None:
        self.children = []

    def get_child(self, i: int) -> Bbox:
        """Return i-th child."""
        return cast("Bbox", (self.children[i]))

    def get_n_children(self) -> int:
        """Return number of children."""
        return len(self.children)

    def get_children(self) -> list[Bbox]:
        """Return all children."""
        return cast("list[Bbox]", (self.children))


class Canvas(Gtk.DrawingArea):
    """Subclass Gtk.DrawingArea to display OCR text and annotations using Cairo."""

    __gsignals__: ClassVar[
        dict[str, tuple[GObject.SignalFlags, object, tuple[object, ...]]]
    ] = {
        "zoom-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        "offset-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                int,
                int,
            ),
        ),
        "selection-drawn": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (Gdk.Rectangle,),
        ),
    }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise Canvas."""
        super().__init__(*args, **kwargs)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._button_pressed)
        self.connect("button-release-event", self._button_released)
        self.connect("motion-notify-event", self._motion)
        self.connect("scroll-event", self._scroll)

        self._device = Gdk.Display.get_default().get_default_seat().get_pointer()
        self._offset = Gdk.Rectangle()
        self._zoom = 1.0
        self._current_index = "position"
        self.position_index = None
        self.confidence_index = None
        self._layout_cache: dict[tuple[Bbox, str, str], Pango.Layout] = {}
        self.dragging = False
        self._drag_start: dict[str, float] = {}
        self._pixbuf_size = None
        self._color_lookup_table = None
        self._root_item = _CanvasRoot()
        self._selection: Gdk.Rectangle | None = None
        self._drawing = False
        self._draw_start: tuple[float, float] | None = None
        self._drag_selection: Gdk.Rectangle | None = None

        self._max_color = "black"
        self._max_color_hsv = None
        self._min_color = "red"
        self._min_color_hsv = None
        self._min_confidence = MIN_CONFIDENCE_DEFAULT
        self._max_confidence = MAX_CONFIDENCE_DEFAULT

        self.set_name("scantpaper-ocr-canvas")

    @property_(type=Gdk.Rectangle, nick="Canvas offset", blurb="Gdk.Rectangle of x, y")
    def offset(self) -> Gdk.Rectangle:
        """Getter for offset attribute."""
        return self._offset

    @offset.setter
    def offset(self, newval: Gdk.Rectangle) -> None:
        """Setter for offset attribute."""
        if self.get_pixbuf_size() is None:
            return

        allocation = self.get_allocation()
        allocation.width, allocation.height = self._to_image_distance(
            allocation.width, allocation.height
        )
        pixbuf_size = cast("dict[str, int]", self.get_pixbuf_size())
        newval.x = _clamp_direction(newval.x, allocation.width, pixbuf_size["width"])
        newval.y = _clamp_direction(newval.y, allocation.height, pixbuf_size["height"])

        if newval.x != self._offset.x or newval.y != self._offset.y:
            self._offset = newval
            self.queue_draw()
            self.emit("offset-changed", newval.x, newval.y)

    @property_(
        type=float,
        default=1,
        nick="zoom",
        blurb="zoom level",
    )
    def zoom(self) -> float:
        """Getter for zoom attribute."""
        return cast("float", (self._zoom))

    @zoom.setter
    def zoom(self, newval: float) -> None:
        """Setter for zoom attribute."""
        newval = min(newval, MAX_ZOOM)
        newval = max(newval, MIN_ZOOM)
        if newval != self._zoom:
            self._zoom = newval
            self.queue_draw()
            self.emit("zoom-changed", newval)

    @property_(
        type=Gdk.Rectangle, nick="Selection", blurb="Gdk.Rectangle of selected region"
    )
    def selection(self) -> Gdk.Rectangle | None:
        """Getter for the selection attribute."""
        return self._selection

    @selection.setter
    def selection(self, newval: Gdk.Rectangle | None) -> None:
        """Setter for the selection attribute."""
        self._selection = newval
        self.queue_draw()

    @property_(
        type=str,
        default="black",
        nick="Maximum color",
        blurb="Color for maximum confidence",
    )
    def max_color(self) -> str:
        """Getter for max_color attribute."""
        return cast("str", (self._max_color))

    @max_color.setter
    def max_color(self, newval: str) -> None:
        """Setter for max_color attribute."""
        self._max_color = newval
        self._max_color_hsv = string2hsv(self._max_color)
        self._color_lookup_table = None

    @property_(
        type=str,
        default="red",
        nick="Minimum color",
        blurb="Color for minimum confidence",
    )
    def min_color(self) -> str:
        """Getter for min_color attribute."""
        return cast("str", (self._min_color))

    @min_color.setter
    def min_color(self, newval: str) -> None:
        """Setter for min_color attribute."""
        self._min_color = newval
        self._min_color_hsv = string2hsv(self._min_color)
        self._color_lookup_table = None

    @property_(
        type=int,
        minimum=0,
        maximum=_100_PERCENT,
        default=MIN_CONFIDENCE_DEFAULT,
        nick="Minimum confidence",
        blurb="Confidence threshold for min-color",
    )
    def min_confidence(self) -> int:
        """Getter for min_confidence attribute."""
        return cast("int", (self._min_confidence))

    @min_confidence.setter
    def min_confidence(self, newval: int) -> None:
        """Setter for min_confidence attribute."""
        self._min_confidence = newval
        self._color_lookup_table = None

    @property_(
        type=int,
        minimum=0,
        maximum=_100_PERCENT,
        default=MAX_CONFIDENCE_DEFAULT,
        nick="Maximum confidence",
        blurb="Confidence threshold for max-color",
    )
    def max_confidence(self) -> int:
        """Getter for max_confidence attribute."""
        return cast("int", (self._max_confidence))

    @max_confidence.setter
    def max_confidence(self, newval: int) -> None:
        """Setter for max_confidence attribute."""
        self._max_confidence = newval
        self._color_lookup_table = None

    def get_max_color_hsv(self) -> dict[str, float]:
        """Return the max hsv colour."""
        if self._max_color_hsv is None:
            self._max_color_hsv = string2hsv(self._max_color)
        return cast("dict[str, float]", (self._max_color_hsv))

    def get_min_color_hsv(self) -> dict[str, float]:
        """Return the min hsv colour."""
        if self._min_color_hsv is None:
            self._min_color_hsv = string2hsv(self._min_color)
        return cast("dict[str, float]", (self._min_color_hsv))

    def _build_color_lookup_table(self, num_bands: int = 10) -> None:
        self._color_lookup_table = []
        min_conf = self.min_confidence
        max_conf = self.max_confidence
        band_width = (max_conf - min_conf) / num_bands

        for i in range(num_bands):
            band_confidence = min_conf + (i + 0.5) * band_width
            max_hsv = self.get_max_color_hsv()
            min_hsv = self.get_min_color_hsv()
            m = (band_confidence - min_conf) / (max_conf - min_conf)
            hsv = {
                "h": linear_interpolation(min_hsv["h"], max_hsv["h"], m),
                "s": linear_interpolation(min_hsv["s"], max_hsv["s"], m),
                "v": linear_interpolation(min_hsv["v"], max_hsv["v"], m),
            }
            rgb = hsv2rgb(hsv)
            color = (
                f"#{int(rgb.red * MAX_COLOR_INT):04x}"
                f"{int(rgb.green * MAX_COLOR_INT):04x}"
                f"{int(rgb.blue * MAX_COLOR_INT):04x}"
            )
            self._color_lookup_table.append(color)

    def get_color_for_confidence(self, confidence: int | None) -> str:
        """Get color string for given confidence value."""
        if confidence is None:
            return self.max_color
        min_conf = self.min_confidence
        max_conf = self.max_confidence

        if confidence >= max_conf:
            return self.max_color

        if confidence <= min_conf:
            return self.min_color

        if self._color_lookup_table is None:
            self._build_color_lookup_table()

        num_bands = len(self._color_lookup_table)
        band_width = (max_conf - min_conf) / num_bands
        band_index = int((confidence - min_conf) / band_width)

        return cast("str", (self._color_lookup_table[band_index]))

    def set_text(
        self,
        bboxes: list[BBox],
        sorted_word_indices: list[int],
        **kwargs: object,
    ) -> None:
        """Set the canvas text from a list of bboxes."""
        if not bboxes:
            self.clear_text()
            if kwargs.get("finished_callback"):
                cast("Callable[..., object]", kwargs["finished_callback"])()
            return

        self.position_index = None
        root = _CanvasRoot()

        self.confidence_index = ListIter()
        itr = enumerate(bboxes)
        try:
            idx, box = next(itr)
        except StopIteration:
            return

        _x1, _y1, width, height = box["bbox"]

        self.set_root_item(root)
        self._pixbuf_size = {"width": width, "height": height}

        original_callback = kwargs.get("finished_callback")
        bbox_map = {}

        def finished_with_rebuild() -> None:
            words = []
            for i in sorted_word_indices:
                bbox = bbox_map.get(i)
                words.append((bbox, bbox.confidence))
            self.confidence_index.list = words
            self.confidence_index.index = EMPTY_LIST

            if original_callback:
                cast("Callable[..., object]", original_callback)()

        options = {
            "iter": itr,
            "idx": idx,
            "box": box,
            "bbox_map": bbox_map,
            "parents": [root],
            "transformations": [[0, 0, 0]],
            "edit_callback": kwargs.get("edit_callback"),
            "finished_callback": finished_with_rebuild,
            "skip_confidence_index": True,
        }
        GLib.idle_add(self._boxed_text, options)

    def _on_draw(self, _widget: Gtk.Widget, ctx: object) -> None:
        """GTK3 draw signal handler."""
        self._draw_scene(ctx)

    def _draw_scene(self, ctx: object) -> None:
        """Draw the scene graph using Cairo."""
        if self._pixbuf_size is None:
            return

        ctx.save()

        scale = self._zoom
        ctx.scale(scale, scale)
        ctx.translate(self._offset.x, self._offset.y)

        self._draw_tree(ctx, self._root_item)

        ctx.restore()

        rect = self._drag_selection if self._drawing else self.selection
        if rect is not None:
            self._draw_selection_rubberband(ctx, rect)

    def _draw_selection_rubberband(self, ctx: object, rect: Gdk.Rectangle) -> None:
        """Draw the selection rectangle in widget coordinates."""
        if rect.width <= 0 or rect.height <= 0:
            return
        wx = rect.x * self._zoom + self._offset.x
        wy = rect.y * self._zoom + self._offset.y
        ww = rect.width * self._zoom
        wh = rect.height * self._zoom
        style = self.get_style_context()
        style.save()
        style.add_class(Gtk.STYLE_CLASS_RUBBERBAND)
        Gtk.render_background(style, ctx, wx, wy, ww, wh)
        Gtk.render_frame(style, ctx, wx, wy, ww, wh)
        style.restore()

    def _draw_tree(self, ctx: object, item: _CanvasRoot | Bbox | None) -> None:
        """Recursively draw bbox tree."""
        if item is None:
            return
        children = item.get_children()
        for child in children:
            self._draw_bbox(ctx, child)
            self._draw_tree(ctx, child)

    def _draw_bbox(self, ctx: object, bbox: Bbox) -> None:
        """Draw a single bbox using Cairo."""
        x = bbox.bbox.x
        y = bbox.bbox.y
        w = bbox.bbox.width
        h = bbox.bbox.height

        if w <= 0 or h <= 0:
            return

        color_str = bbox.confidence2color()
        color_rgba = string2rgb(color_str)

        ctx.save()

        ctx.set_source_rgba(
            color_rgba.red, color_rgba.green, color_rgba.blue, color_rgba.alpha
        )
        ctx.set_line_width(2 if bbox.text else 1)
        ctx.rectangle(x, y, w, h)
        ctx.stroke()

        if bbox.text:
            rotation, _x0, _y0 = bbox.transformation
            angle = -(bbox.textangle + rotation) % _360_DEGREES

            layout = self._layout_for(ctx, bbox)

            if layout is not None:
                ink_extents = layout.get_pixel_extents()[0]
                text_w = ink_extents.width
                text_h = ink_extents.height

                if text_w > 0:
                    scale = h / text_w if angle else w / text_w

                    if bbox.type == "page":
                        scale *= FULLPAGE_OCR_SCALE

                    ctx.save()

                    ctx.translate(x + w / 2, y + h / 2)
                    ctx.rotate(angle * math.pi / 180)
                    ctx.scale(scale, scale)

                    centered_x = -(text_w / 2)
                    centered_y = -(text_h / 2)

                    ctx.set_source_rgba(
                        color_rgba.red,
                        color_rgba.green,
                        color_rgba.blue,
                        color_rgba.alpha,
                    )
                    ctx.move_to(centered_x, centered_y)
                    PangoCairo.show_layout(ctx, layout)

                    ctx.restore()

        ctx.restore()

    def _create_pango_layout(self, ctx: object, bbox: Bbox) -> Pango.Layout:
        """Create a PangoLayout for a bbox's text."""
        layout = PangoCairo.create_layout(ctx)
        layout.set_font_description(
            Pango.FontDescription.from_string(LAYOUT_FONT_DESCRIPTION)
        )
        layout.set_text(bbox.text, -1)
        return layout

    def _layout_for(self, ctx: object, bbox: Bbox) -> Pango.Layout | None:
        """Return the layout for bbox, creating it if needed.

        The cache lives on the Canvas, never on the Bbox, and is keyed on the
        text alongside the font description. A corrected word therefore gets a
        new layout on the next frame instead of redrawing the glyphs it had when
        it was first drawn, which was the stale-text bug; and because the text is
        part of the key, no explicit invalidation on edit is needed. Entries are
        dropped along with the bbox by Canvas.delete_word.
        """
        key = (bbox, bbox.text, LAYOUT_FONT_DESCRIPTION)
        layout = self._layout_cache.get(key)
        if layout is None:
            layout = self._create_pango_layout(ctx, bbox)
            self._layout_cache[key] = layout
        return layout

    def get_first_bbox(self) -> Bbox | None:
        """Return first bbox, depending on which index is active."""
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_first_bbox()
        else:
            bbox = self.position_index.first_word()

        self.set_other_index(bbox)
        return cast("Bbox | None", (bbox))

    def get_previous_bbox(self) -> Bbox | None:
        """Return previous bbox, depending on which index is active."""
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_previous_bbox()
        else:
            bbox = self.position_index.previous_word()

        self.set_other_index(bbox)
        return cast("Bbox | None", (bbox))

    def get_next_bbox(self) -> Bbox | None:
        """Return next bbox, depending on which index is active."""
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_next_bbox()
        else:
            bbox = self.position_index.next_word()

        self.set_other_index(bbox)
        return cast("Bbox | None", (bbox))

    def get_last_bbox(self) -> Bbox | None:
        """Return last bbox, depending on which index is active."""
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_last_bbox()
        else:
            bbox = self.position_index.last_word()

        self.set_other_index(bbox)
        return cast("Bbox | None", (bbox))

    def get_current_bbox(self) -> Bbox | None:
        """Return current bbox."""
        bbox = None
        if self._current_index == "confidence":
            bbox = self.confidence_index.get_current_bbox()

        else:
            bbox = self.position_index.get_current_bbox()

        self.set_other_index(bbox)
        return cast("Bbox | None", (bbox))

    def set_index_by_bbox(self, bbox: Bbox) -> None:
        """Set the index by bbox."""
        if bbox is None:
            raise IndexError
        if self._current_index == "confidence":
            self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)
        else:
            self.position_index = TreeIter(bbox)

    def set_other_index(self, bbox: Bbox | None) -> None:
        """Swap indices."""
        if bbox is None:
            return
        if self._current_index == "confidence":
            self.position_index = TreeIter(bbox)
        else:
            self.confidence_index.set_index_by_bbox(bbox, bbox.confidence)

    def update_word(self, bbox: Bbox, text: str, selection: Gdk.Rectangle) -> None:
        """Apply a correction to a word, keeping both indexes consistent."""
        old_pos_ind = bbox.get_position_index()
        old_conf = bbox.confidence
        bbox.set_word(text, selection)

        if old_conf != bbox.confidence:
            self.reindex_by_confidence(bbox)

        new_pos_ind = bbox.get_position_index()
        parent = bbox.parent
        if old_pos_ind != new_pos_ind and parent is not None:
            self._move_child(parent, old_pos_ind, new_pos_ind)

        bbox.emit("text-changed", text)
        bbox.emit("bbox-changed", selection)
        self.queue_draw()

    def delete_word(self, bbox: Bbox) -> None:
        """Remove a word from the scene graph and from both indexes."""
        words = self._words_in_reading_order()
        following, preceding = _reading_order_neighbours(bbox, words)
        parent = bbox.parent
        if self.confidence_index is not None:
            self.confidence_index.remove_bbox(bbox)
        bbox.detach_from_parent()
        if parent is not None:
            self._prune_empty_ancestors(parent)
        self._discard_cached_layouts(bbox)
        if self.position_index is not None:
            successor = following if following is not None else preceding
            if successor is not None:
                self.position_index = TreeIter(successor)
            else:
                self.position_index.exhaust()
        self.queue_draw()

    def reindex_by_confidence(self, bbox: Bbox) -> None:
        """Move a word to its new rank in the confidence index."""
        self.confidence_index.remove_bbox(bbox)
        self.confidence_index.add_box_to_index(bbox, bbox.confidence)

    def _move_child(
        self, parent: Bbox | _CanvasRoot, old_index: int, new_index: int
    ) -> None:
        """Reorder a child of parent to match its new geometry."""
        children = parent.get_children()
        if 0 <= old_index < len(children) and 0 <= new_index < len(children):
            children.insert(new_index, children.pop(old_index))

    def _discard_cached_layouts(self, bbox: Bbox) -> None:
        """Drop the cached layouts of a box that is leaving the scene graph."""
        for key in [key for key in self._layout_cache if key[0] is bbox]:
            del self._layout_cache[key]

    def _prune_empty_ancestors(self, parent: Bbox | _CanvasRoot | None) -> None:
        """Remove ancestors left with neither text nor descendants.

        The page box is exempt: it carries the page geometry and must survive so
        that a fully emptied page still serialises valid page bounds.
        """
        node = parent
        while isinstance(node, Bbox) and node.type != "page":
            grandparent = node.parent if isinstance(node.parent, Bbox) else None
            if not is_empty_branch(
                has_text=bool(node.text), has_descendants=bool(node.children)
            ):
                break
            node.detach_from_parent()
            node = grandparent

    def _words_in_reading_order(self) -> list[Bbox]:
        """Return every word in the scene graph, in reading order."""
        words: list[Bbox] = []
        _collect_words(self.get_root_item(), words)
        return words

    def get_pixbuf_size(self) -> dict[str, int] | None:
        """Return the size of the associated pixbuf."""
        return cast("dict[str, int] | None", (self._pixbuf_size))

    def clear_text(self) -> None:
        """Clear the canvas."""
        self._root_item = _CanvasRoot()
        self._pixbuf_size = None
        self._color_lookup_table = None
        self.queue_draw()

    def set_offset(self, offset_x: float, offset_y: float) -> None:
        """Set the offset."""
        offset = Gdk.Rectangle()
        offset.x = offset_x
        offset.y = offset_y
        self.offset = offset

    def get_offset(self) -> Gdk.Rectangle:
        """Return the offset."""
        return self._offset

    def _hit_test(self, widget_x: float, widget_y: float) -> Bbox | None:
        """Find the bbox at widget coordinates, return deepest leaf."""
        if self._pixbuf_size is None or self._root_item is None:
            raise ReferenceError

        scale = self._zoom
        image_x = widget_x / scale - self._offset.x
        image_y = widget_y / scale - self._offset.y

        return self._find_bbox_at(self._root_item, image_x, image_y)

    def _find_bbox_at(
        self, item: _CanvasRoot | Bbox | None, x: float, y: float
    ) -> Bbox | None:
        """Find deepest bbox containing point (x, y)."""
        if item is None:
            return None
        found = None
        for child in item.get_children():
            if child.bbox is not None:
                bx, by, bw, bh = (
                    child.bbox.x,
                    child.bbox.y,
                    child.bbox.width,
                    child.bbox.height,
                )
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    found = child
                    deeper = self._find_bbox_at(child, x, y)
                    if deeper is not None:
                        found = deeper

        return found

    def get_bbox_at(self, bbox: Gdk.Rectangle) -> Bbox:
        """Return the bbox at the given coords."""
        x = bbox.x + bbox.width / 2
        y = bbox.y + bbox.height / 2
        result = self._find_bbox_at(self._root_item, x, y)
        if result is None:
            raise ReferenceError
        if result.type == "word" and isinstance(result.parent, Bbox):
            return result.parent
        return result

    def add_box(self, **kwargs: object) -> Bbox:
        """Add box to canvas."""
        if "parent" in kwargs:
            parent = kwargs["parent"]
        else:
            parent = self.get_bbox_at(kwargs["bbox"])

        transformation = [0, 0, 0]
        if "transformation" in kwargs:
            transformation = kwargs["transformation"]
        elif isinstance(parent, Bbox):
            transformation = [parent.textangle, parent.bbox.x, parent.bbox.y]
        else:
            transformation = [0, 0, 0]

        options2 = self._bbox_kwargs(
            kwargs,
            cast("Bbox | _CanvasRoot", parent),
            cast("list[int]", transformation),
        )

        bbox = Bbox(**options2)
        if self.position_index is None:
            self.position_index = TreeIter(bbox)

        if len(cast("str", kwargs["text"])) > 0 and not kwargs.get(
            "skip_confidence_index", False
        ):
            self.confidence_index.add_box_to_index(bbox, bbox.confidence)

        self.queue_draw()
        return bbox

    def _bbox_kwargs(
        self,
        kwargs: dict[str, Any],
        parent: Bbox | _CanvasRoot,
        transformation: list[int],
    ) -> dict[str, Any]:
        """Build the option dict for a new Bbox from the add_box kwargs."""
        options = {
            "canvas": self,
            "parent": parent,
            "bbox": kwargs["bbox"],
            "transformation": transformation,
            "text": kwargs["text"],
        }

        for key in ["baseline", "confidence", "id", "text", "textangle", "type"]:
            if key in kwargs:
                options[key] = kwargs[key]

        if "textangle" not in options:
            options["textangle"] = 0
        if "type" not in options:
            options["type"] = "word"
        if "confidence" not in options and options["type"] == "word":
            options["confidence"] = _100_PERCENT

        options["edit_callback"] = kwargs.get("edit_callback")
        return options

    def _boxed_text(self, options: dict[str, Any]) -> bool:
        """Draw text on the canvas with a box around it."""
        for _ in range(BATCH_SIZE):
            idx = cast("int", options["idx"])
            box = cast("dict[str, Any]", options["box"])
            depth = cast("int", box["depth"])

            transformations = options["transformations"]
            parents = cast("list[Bbox]", options["parents"])
            rotation, _, _ = transformations[depth]
            textangle = box.get("textangle", 0)

            options2 = {"parent": parents[depth]}
            options2["edit_callback"] = options["edit_callback"]
            options2["text"] = box.get("text", "")
            options2["skip_confidence_index"] = options.get(
                "skip_confidence_index", False
            )

            for key in ["baseline", "confidence", "id", "textangle", "type"]:
                if key in box:
                    options2[key] = box[key]

            options2["bbox"] = Rectangle.from_bbox(*cast("list[int]", box["bbox"]))
            bbox = self.add_box(**options2)
            cast("dict[int, Bbox]", options["bbox_map"])[idx] = bbox

            if depth > len(parents) - 2:
                parents.append(bbox)
            else:
                parents[depth + 1] = bbox

            transformations.append(
                [textangle + rotation, options2["bbox"].x, options2["bbox"].y]
            )
            try:
                options["idx"], options["box"] = next(options["iter"])
            except StopIteration:
                if options["finished_callback"]:
                    cast("Callable[..., object]", options["finished_callback"])()
                self.queue_draw()
                return cast("bool", (GLib.SOURCE_REMOVE))

        self.queue_draw()
        return cast("bool", (GLib.SOURCE_CONTINUE))

    def hocr(self) -> str:
        """Convert the canvas into hocr."""
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

    def _to_image_distance(self, x: float, y: float) -> tuple[float, float]:
        """Convert x, y in widget distance to image distance."""
        return x / self.zoom, y / self.zoom

    def _set_zoom_with_center(
        self, zoom: float, center_x: float, center_y: float
    ) -> None:
        """Set zoom with centre in image coordinates."""
        zoom = min(zoom, MAX_ZOOM)
        allocation = self.get_allocation()
        offset_x = allocation.width / 2 / zoom - center_x
        offset_y = allocation.height / 2 / zoom - center_y
        self.zoom = zoom
        self.set_offset(offset_x, offset_y)

    def _button_pressed(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> None:
        if event.button == Gdk.BUTTON_MIDDLE:
            _screen, x, y = self._device.get_position()
            self._drag_start = {"x": x, "y": y}
            self.dragging = True
            win = self.get_window()
            win.set_cursor(
                Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grabbing")
            )
        elif event.button == 1:
            focus = False
            try:
                bbox = self._hit_test(event.x, event.y)
                if (
                    bbox is not None
                    and hasattr(bbox, "edit_callback")
                    and bbox.edit_callback
                ):
                    button_press_callback(
                        bbox,
                        _widget,
                        event,
                        cast("Callable[..., object]", bbox.edit_callback),
                    )
                    focus = True
            except ReferenceError:
                pass
            self._drawing = False
            self._drag_selection = None
            if not focus and self.get_pixbuf_size() is not None:
                self._start_draw(event)

    def _start_draw(self, event: Gdk.EventButton) -> None:
        """Begin drawing a selection rectangle at the press position."""
        self._drawing = True
        self._draw_start = (event.x, event.y)
        self._drag_selection = self._widget_to_image_rect(
            event.x, event.y, event.x, event.y
        )

    def _widget_to_image_rect(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> Gdk.Rectangle:
        """Convert two widget points into an image-coordinate rectangle."""
        scale = self._zoom
        offset = self._offset
        image_x1 = min(x1, x2) / scale - offset.x
        image_y1 = min(y1, y2) / scale - offset.y
        image_x2 = max(x1, x2) / scale - offset.x
        image_y2 = max(y1, y2) / scale - offset.y
        rect = Gdk.Rectangle()
        rect.x, rect.y = int(image_x1 + 0.5), int(image_y1 + 0.5)
        rect.width, rect.height = (
            int(image_x2 - image_x1 + 0.5),
            int(image_y2 - image_y1 + 0.5),
        )
        return rect

    def _button_released(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1 and self._drawing:
            rect = self._drag_selection
            self._drawing = False
            self._drag_selection = None
            if rect is not None and rect.width > 0 and rect.height > 0:
                self.emit("selection-drawn", rect)
            self.queue_draw()
            return True
        if event.button == Gdk.BUTTON_MIDDLE:
            self.dragging = False
            win = self.get_window()
            win.set_cursor(None)
        return True

    def _motion(self, _widget: Gtk.Widget, _event: Gdk.EventMotion) -> bool:
        if self._drawing and self._draw_start is not None:
            self._drag_selection = self._widget_to_image_rect(
                self._draw_start[0], self._draw_start[1], _event.x, _event.y
            )
            self.queue_draw()
            return True
        if not self.dragging:
            return False
        offset = self.get_offset()
        zoom = self.zoom
        _screen, x, y = self._device.get_position()
        offset_x = offset.x + (x - self._drag_start["x"]) / zoom
        offset_y = offset.y + (y - self._drag_start["y"]) / zoom
        self._drag_start["x"], self._drag_start["y"] = (x, y)
        self.set_offset(offset_x, offset_y)
        return True

    def _scroll(self, _widget: Gtk.Widget, event: Gdk.EventScroll) -> bool:
        allocation = self.get_allocation()
        centre_x = allocation.width / 2
        centre_y = allocation.height / 2
        image_x = (
            (event.x - centre_x) / self._zoom + centre_x / self._zoom - self._offset.x
        )
        image_y = (
            (event.y - centre_y) / self._zoom + centre_y / self._zoom - self._offset.y
        )

        if event.direction == Gdk.ScrollDirection.UP:
            zoom = self.zoom * 2
        else:
            zoom = self.zoom / 2

        zoom = min(zoom, MAX_ZOOM)
        zoom = max(zoom, MIN_ZOOM)

        offset_x = (event.x - centre_x) / zoom + centre_x / zoom - image_x
        offset_y = (event.y - centre_y) / zoom + centre_y / zoom - image_y

        self.zoom = zoom
        self.set_offset(offset_x, offset_y)

        return True

    def sort_by_confidence(self) -> None:
        """Iterate through the bboxes by confidence."""
        self._current_index = "confidence"

    def sort_by_position(self) -> None:
        """Iterate through the bboxes by position."""
        self._current_index = "position"

    def set_root_item(self, item: _CanvasRoot) -> None:
        """Set the root item of the scene graph."""
        self._root_item = item

    def get_root_item(self) -> _CanvasRoot:
        """Get the root item of the scene graph."""
        return cast("_CanvasRoot", (self._root_item))


class ListIter:
    """an interator to allow us to index around a linear list."""

    def __init__(self) -> None:
        """Initialise ListIter."""
        self.list = []
        self.index = EMPTY_LIST

    def get_first_bbox(self) -> Bbox | None:
        """Return first bbox, or None when the list is empty."""
        self.index = 0
        return self.get_current_bbox()

    def get_previous_bbox(self) -> Bbox | None:
        """Return previous bbox, or None when there is none."""
        if self.index > 0:
            self.index -= 1
        return self.get_current_bbox()

    def get_next_bbox(self) -> Bbox | None:
        """Return next bbox, or None when there is none."""
        if self.index < len(self.list) - 1:
            self.index += 1
        return self.get_current_bbox()

    def get_last_bbox(self) -> Bbox | None:
        """Return last bbox, or None when the list is empty."""
        self.index = len(self.list) - 1
        return self.get_current_bbox()

    def get_current_bbox(self) -> Bbox | None:
        """Return bbox currently selected, or None when the index is empty."""
        if self.index > EMPTY_LIST:
            return cast("Bbox", (self.list[self.index][0]))
        return None

    def set_index_by_bbox(self, bbox: Bbox, value: float) -> int:
        """Set the index to the given bbox."""
        lo = self.get_index_for_value(value - 1)
        for i in range(lo, len(self.list)):
            if self.list[i][0] == bbox:
                self.index = i
                return i
        self.index = EMPTY_LIST
        return EMPTY_LIST

    def get_index_for_value(self, value: float) -> int:
        """Return index of value using binary search."""
        lo = 0
        r = len(self.list) - 1
        if r == EMPTY_LIST:
            return 0
        while lo != r:
            m = math.ceil((lo + r) / 2)
            if self.list[m][1] > value:
                r = m - 1
            else:
                lo = m
        if self.list[lo][1] < value:
            lo += 1
        return lo

    def insert_after_position(self, bbox: Bbox | None, i: int, value: float) -> None:
        """Insert bbox after given index."""
        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return
        if i > len(self.list) - 1:
            logger.warning(
                "insert_after_position: position $i does not exist in index",
            )
            return
        self.list.insert(i + 1, [bbox, value])

    def insert_before_position(self, bbox: Bbox | None, i: int, value: float) -> None:
        """Insert bbox before given index."""
        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return
        if i > len(self.list) - 1:
            logger.warning(
                "insert_before_position: position $i does not exist in index",
            )
            return
        self.list.insert(i, [bbox, value])

    def add_box_to_index(self, bbox: Bbox | None, value: int | None) -> None:
        """Insert into list sorted by confidence level using a binary search."""
        if bbox is None:
            logger.warning("Attempted to add undefined box to confidence list")
            return
        if value is None:
            return
        i = self.get_index_for_value(value)
        if i > len(self.list) - 1:
            self.list.append([bbox, value])
            return
        self.insert_before_position(bbox, i, value)

    def remove_bbox(self, bbox: Bbox) -> None:
        """Remove bbox from the index by identity, leaving the cursor sensible.

        The cursor is left on the entry that followed the removed one, or on the
        preceding entry when the removed one was last.
        """
        for i, entry in enumerate(self.list):
            if entry[0] is not bbox:
                continue
            del self.list[i]
            if i < self.index:
                self.index -= 1
            self.index = min(self.index, len(self.list) - 1)
            return
        logger.warning("Attempted to delete a box that is not in the index")


class TreeIter:
    """Class allowing us to iterate around the tree of bounding boxes."""

    def __init__(self, bbox: Bbox) -> None:
        """Initialise TreeIter."""
        if not isinstance(bbox, Bbox):
            msg = "bbox is not a Bbox object"
            raise TypeError(msg)
        self._bbox = [bbox]
        self._iter = []
        while bbox.type != "page":
            parent = bbox.parent
            self._iter.insert(0, parent.get_child_ordinal(bbox))
            self._bbox.insert(0, cast("Bbox", parent))
            bbox = cast("Bbox", parent)
        self._iter.insert(0, 0)
        self._exhausted = False

    def exhaust(self) -> None:
        """Mark the iterator as having no current word."""
        self._exhausted = True

    def first_bbox(self) -> Bbox:
        """Return first bbox."""
        self._bbox = [self._bbox[0]]
        self._iter = [0]
        self._exhausted = False
        return self._bbox[0]

    def first_word(self) -> Bbox:
        """Return first word."""
        bbox = self.first_bbox()
        if bbox.type != "word":
            return self.next_word()
        return bbox

    def next_bbox(self) -> Bbox:
        """Return next bbox."""
        old_bbox = self._bbox.copy()
        old_iter = self._iter.copy()

        current = self._bbox[-1]
        n = current.get_n_children()
        for i in range(n):
            child = current.get_child(i)
            self._bbox.append(child)
            self._iter.append(i)
            return cast("Bbox", (child))

        while len(self._bbox) > 1:
            self._bbox.pop()
            last_idx = self._iter.pop()
            parent = self._bbox[-1]
            n_parent = parent.get_n_children()

            for i in range(last_idx + 1, n_parent):
                sibling = parent.get_child(i)
                self._bbox.append(sibling)
                self._iter.append(i)
                return cast("Bbox", (sibling))

        self._bbox = old_bbox
        self._iter = old_iter
        self._exhausted = True
        raise StopIteration

    def next_word(self) -> Bbox:
        """Return next bbox."""
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.next_bbox()
        while bbox.type != "word":
            try:
                bbox = self.next_bbox()
            except StopIteration as exc:  # noqa: PERF203 — iterator exhaustion; catch-StopIteration loop is idiomatic here
                self._iter = current_iter
                self._bbox = current_bbox
                self._exhausted = True
                raise StopIteration from exc
        return bbox

    def previous_bbox(self) -> Bbox:
        """Return previous bbox."""
        if len(self._bbox) <= 1:
            self._exhausted = True
            raise StopIteration
        self._bbox.pop()
        last_idx = self._iter.pop()
        parent = self._bbox[-1]

        for i in range(last_idx - 1, -1, -1):
            sibling = parent.get_child(i)
            self._bbox.append(sibling)
            self._iter.append(i)
            return self.last_leaf()
        return cast("Bbox", (parent))

    def previous_word(self) -> Bbox:
        """Return previous word."""
        current_iter = self._iter.copy()
        current_bbox = self._bbox.copy()
        bbox = self.get_current_bbox()
        bbox = self.previous_bbox()
        while bbox.type != "word":
            try:
                bbox = self.previous_bbox()
            except StopIteration as exc:  # noqa: PERF203 — iterator exhaustion; catch-StopIteration loop is idiomatic here
                self._iter = current_iter
                self._bbox = current_bbox
                raise StopIteration from exc
        if bbox == current_bbox[-1]:
            self._iter = current_iter
            self._bbox = current_bbox
            self._exhausted = True
            raise StopIteration
        return bbox

    def last_bbox(self) -> Bbox:
        """Return last bbox."""
        self._bbox = [self._bbox[0]]
        self._iter = [1]
        self._exhausted = False
        return self.last_leaf()

    def last_word(self) -> Bbox | None:
        """Return last word."""
        bbox = self.last_bbox()
        while bbox.type != "word":
            bbox = self.previous_bbox()
        return bbox

    def last_leaf(self) -> Bbox:
        """Return last bbox."""
        n = self._bbox[-1].get_n_children() - 1
        while n > EMPTY_LIST:
            child = self._bbox[-1].get_child(n)
            self._iter.append(n)
            self._bbox.append(child)
            return self.last_leaf()
        return cast("Bbox", (self._bbox[-1]))

    def get_current_bbox(self) -> Bbox | None:
        """Return bbox currently being viewed, or None when exhausted."""
        if self._exhausted:
            return None
        return cast("Bbox", (self._bbox[-1]))

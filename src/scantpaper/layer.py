"""provide controls and editing logic for a page text or annotation layer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.canvas import Canvas
from scantpaper.comboboxtext import ComboBoxText
from scantpaper.const import EMPTY, ZOOM_CONTEXT_FACTOR
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from typing import ClassVar

    from scantpaper.basethread import Response
    from scantpaper.bboxtree import BBox
    from scantpaper.canvas import Bbox
    from scantpaper.docthread import DocThread
    from scantpaper.imageview import ImageView
    from scantpaper.page import Page

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    Gdk,
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)

INDEX = [
    [
        "confidence",
        _("Sort by confidence"),
        _("Sort OCR text boxes by confidence."),
    ],
    ["position", _("Sort by position"), _("Sort OCR text boxes by position.")],
]

_IMPORT_METHOD_BY_ATTR = {
    "text_layer": "import_hocr",
    "annotations": "import_annotations",
}

_SET_METHOD_BY_ATTR = {
    "text_layer": "set_text",
    "annotations": "set_annotations",
}

_DEFAULT_TEXT_BY_ATTR = {
    "text_layer": _("my-new-word"),
    "annotations": _("my-new-annotation"),
}


class LayerControls(Gtk.Box):
    """Feature-flag configurable control bar for editing a layer."""

    __gsignals__: ClassVar[
        dict[str, tuple[GObject.SignalFlags, object, tuple[object, ...]]]
    ] = {
        "text-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "bbox-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "sort-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "go-to-first": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-previous": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-next": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "go-to-last": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "ok-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "copy-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "add-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "delete-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(
        self,
        *args: object,
        sort: bool = False,
        nav: bool = False,
        copy: bool = False,
        **kwargs: object,
    ) -> None:
        """Initialise the control bar with optional sort, navigation, and copy."""
        super().__init__(*args, **kwargs)
        textview = Gtk.TextView()
        textview.set_tooltip_text(_("Text layer"))
        self.textbuffer = textview.get_buffer()

        if nav:
            self.pack_start(
                self._make_icon_button(
                    "go-first", _("Go to least confident text"), "go-to-first"
                ),
                expand=False,
                fill=False,
                padding=0,
            )
            self.pack_start(
                self._make_icon_button(
                    "go-previous", _("Go to previous text"), "go-to-previous"
                ),
                expand=False,
                fill=False,
                padding=0,
            )
        if sort:
            sort_cmbx = ComboBoxText(data=INDEX)
            sort_cmbx.set_tooltip_text(_("Select sort method for OCR boxes"))
            sort_cmbx.connect(
                "changed",
                lambda _: self.emit("sort-changed", INDEX[sort_cmbx.get_active()][0]),
            )
            sort_cmbx.set_active(0)
            self.pack_start(sort_cmbx, expand=False, fill=False, padding=0)
        if nav:
            self.pack_start(
                self._make_icon_button("go-next", _("Go to next text"), "go-to-next"),
                expand=False,
                fill=False,
                padding=0,
            )
            self.pack_start(
                self._make_icon_button(
                    "go-last", _("Go to most confident text"), "go-to-last"
                ),
                expand=False,
                fill=False,
                padding=0,
            )
        self.add_button = self._make_icon_button(
            "list-add", _("Add text"), "add-clicked"
        )

        obutton = self._make_mnemonic_button(
            _("_OK"), _("Accept corrections"), "ok-clicked"
        )
        cbutton = self._make_mnemonic_button(
            _("_Cancel"), _("Cancel corrections"), close=True
        )
        ubutton = None
        if copy:
            ubutton = self._make_mnemonic_button(
                _("_Copy"), _("Duplicate text"), "copy-clicked"
            )
        dbutton = self._make_mnemonic_button(
            _("_Delete"), _("Delete text"), "delete-clicked"
        )

        self.pack_start(textview, expand=True, fill=True, padding=0)
        self.pack_end(dbutton, expand=False, fill=False, padding=0)
        self.pack_end(cbutton, expand=False, fill=False, padding=0)
        self.pack_end(obutton, expand=False, fill=False, padding=0)
        if copy:
            self.pack_end(ubutton, expand=False, fill=False, padding=0)
        self.pack_end(self.add_button, expand=False, fill=False, padding=0)

    def _make_icon_button(self, icon: str, tooltip: str, signal: str) -> Gtk.Button:
        """Build an icon button that emits the given signal."""
        button = Gtk.Button()
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _: self.emit(signal))
        return button

    def _make_mnemonic_button(
        self,
        label: str,
        tooltip: str,
        signal: str | None = None,
        *,
        close: bool = False,
    ) -> Gtk.Button:
        """Build a mnemonic button that emits the given signal or closes."""
        button = Gtk.Button.new_with_mnemonic(label=label)
        button.set_tooltip_text(tooltip)
        if close:
            button.connect("clicked", lambda _: self.hide())
        else:
            button.connect("clicked", lambda _: self.emit(signal))
        return button

    def set_add_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the Add control and set its explanatory tooltip.

        A disabled Add control cannot place a slice without a selection, so it
        explains that a rectangle must be drawn or selected first.
        """
        self.add_button.set_sensitive(enabled)
        if enabled:
            self.add_button.set_tooltip_text(_("Add text"))
        else:
            self.add_button.set_tooltip_text(
                _("Draw or select a rectangle before adding")
            )


class LayerEditor:
    """Edit one layer (text or annotations) over a page."""

    def __init__(
        self,
        *,
        page_attr: str,
        view: ImageView,
        thread: DocThread,
        get_page: Callable[[], Page | None],
        features: Collection[str] = (),
    ) -> None:
        """Initialise the editor with its canvas and controls."""
        self.page_attr = page_attr
        self.import_method = _IMPORT_METHOD_BY_ATTR[page_attr]
        self._view = view
        self._thread = thread
        self._get_page = get_page
        self._sort_enabled = "sort" in features
        self._nav_enabled = "nav" in features
        self._copy_enabled = "copy" in features
        self._default_text = _DEFAULT_TEXT_BY_ATTR[page_attr]
        self._current_bbox: Bbox | None = None
        self.canvas = Canvas()
        self.controls = LayerControls(
            sort=self._sort_enabled, nav=self._nav_enabled, copy=self._copy_enabled
        )
        self._connect_controls()
        self.canvas.connect("selection-drawn", self._on_selection_drawn)
        self._view.connect("notify::selection", lambda *_: self._update_add_state())
        self._update_add_state()

    def _parse(
        self, json_string: str, finished_callback: Callable[..., object] | None = None
    ) -> None:
        """Parse a layer JSON string in the worker thread."""
        self._thread.parse_bboxtree(json_string, finished_callback=finished_callback)

    def _persist(self, page: Page) -> None:
        """Persist the page's layer through the worker thread."""
        setter = getattr(self._thread, _SET_METHOD_BY_ATTR[self.page_attr])
        setter(page.id, getattr(page, self.page_attr))

    def _connect_controls(self) -> None:
        """Wire the control bar signals to this editor's handlers."""
        controls = self.controls
        if self._nav_enabled:
            controls.connect(
                "go-to-first", lambda _: self.edit(self.canvas.get_first_bbox())
            )
            controls.connect(
                "go-to-previous", lambda _: self.edit(self.canvas.get_previous_bbox())
            )
            controls.connect(
                "go-to-next", lambda _: self.edit(self.canvas.get_next_bbox())
            )
            controls.connect(
                "go-to-last", lambda _: self.edit(self.canvas.get_last_bbox())
            )
        if self._sort_enabled:
            controls.connect("sort-changed", self._sort)
        controls.connect("ok-clicked", self.ok)
        controls.connect("add-clicked", self.add)
        controls.connect("delete-clicked", self.delete)
        if self._copy_enabled:
            controls.connect("copy-clicked", self.copy)

    def _on_selection_drawn(self, _canvas: object, rect: Gdk.Rectangle) -> None:
        """Commit a rectangle drawn in the layer pane to the shared selection."""
        self._view.set_selection(rect)

    def _update_add_state(self) -> None:
        """Enable the Add control only when a selection exists."""
        self.controls.set_add_enabled(enabled=self._view.get_selection() is not None)

    def _sort(self, _widget: object, sort_method: str) -> None:
        """Sort the canvas by the selected method."""
        if sort_method == "confidence":
            self.canvas.sort_by_confidence()
        else:
            self.canvas.sort_by_position()

    def _controls_text(self) -> str:
        """Return the current text in the control buffer."""
        return cast(
            "str",
            self.controls.textbuffer.get_text(
                self.controls.textbuffer.get_start_iter(),
                self.controls.textbuffer.get_end_iter(),
                include_hidden_chars=False,
            ),
        )

    def _page(self) -> Page | None:
        """Return the current page, if any."""
        return self._get_page()

    def _commit(self) -> None:
        """Import the canvas hocr into the page and persist it."""
        page = self._page()
        if page is None:
            return
        getattr(page, self.import_method)(self.canvas.hocr())
        self._persist(page)

    def edit(self, bbox: Bbox | None, _target: object | None = None) -> None:
        """Focus the editor on the given bbox, or clear it when there is none.

        With nothing left to edit the control is emptied rather than left
        showing the text of a slice that no longer exists.
        """
        self._current_bbox = bbox
        if bbox is None:
            logger.debug("edit did not return a bbox")
            self.controls.textbuffer.set_text(EMPTY)
            return
        self.controls.textbuffer.set_text(bbox.text)
        self.controls.show_all()
        self._view.set_selection(bbox.bbox)
        self._view.setzoom_is_fit(zoom_to_fit=False)
        self._view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        self.canvas.set_index_by_bbox(bbox)

    def clear(self) -> None:
        """Forget the focused slice and empty the control and canvas.

        Used when the page has no layer to edit, so the editor cannot keep
        showing, or acting on, a slice from an earlier tree.
        """
        self._current_bbox = None
        self.controls.textbuffer.set_text(EMPTY)
        self.canvas.clear_text()

    def create(
        self,
        page: Page,
        offset: Gdk.Rectangle | None,
        finished_callback: Callable[..., object] | None = None,
    ) -> None:
        """Create the canvas for the given page, parsing its layer.

        The rebuilt tree is a fresh set of slices, so focus and the control
        are cleared up front; flows that re-focus afterwards (e.g. `add()`
        on a freshly created layer) still run and set their own focus.
        """
        self._current_bbox = None
        self.controls.textbuffer.set_text(EMPTY)

        def on_parsed(result: Response) -> None:
            info = cast("dict[str, object]", result.info)
            self.canvas.set_text(
                bboxes=cast("list[BBox]", info["bboxes"]),
                sorted_word_indices=cast("list[int]", info["sorted_word_indices"]),
                edit_callback=self.edit,
                finished_callback=finished_callback,
            )
            if offset is not None:
                self.canvas.set_offset(offset.x, offset.y)
            self.canvas.show()

        if getattr(page, self.page_attr):
            self._parse(getattr(page, self.page_attr), on_parsed)
        else:
            self.canvas.clear_text()
            if finished_callback:
                finished_callback()

    def ok(self, _widget: object) -> None:
        """Accept the corrections for the current bbox.

        An emptied control is a deletion, not a correction. It is routed
        through the same path as the Delete button rather than being left for
        the setter to interpret, so that the editor can move on to a surviving
        slice instead of re-focusing the one that was just removed.
        """
        bbox = self._current_bbox
        if bbox is None:
            return
        text = self._controls_text()
        if text == EMPTY:
            self.delete(_widget)
            return
        old_text = bbox.text
        self.canvas.update_word(bbox, text, self._view.get_selection())
        self._commit()
        self.edit(bbox)
        logger.info("Corrected '%s'->'%s'", old_text, text)

    def copy(self, _widget: object) -> None:
        """Duplicate the current text into a new box at the selection."""
        self._current_bbox = self.canvas.add_box(
            text=self._controls_text(),
            bbox=self._view.get_selection(),
        )
        self._commit()
        self.edit(self._current_bbox)

    def add(self, _widget: object) -> None:
        """Add a new box at the current selection, or seed a fresh layer."""
        text = self._controls_text()
        if text == EMPTY:
            text = self._default_text
        page = self._page()
        if page is None:
            return
        selection = self._view.get_selection()
        if getattr(page, self.page_attr, None):
            logger.info("Added '%s'", text)
            self._current_bbox = self.canvas.add_box(
                text=text, bbox=self._view.get_selection()
            )
            getattr(page, self.import_method)(self.canvas.hocr())
            self.edit(self._current_bbox)
        else:
            logger.info("Creating new %s with '%s'", self.page_attr, text)
            setattr(page, self.page_attr, self._new_layer_json(selection, text))

            def on_new(*_args: object) -> None:
                self.edit(self.canvas.get_first_bbox())

            self.create(page, self._view.get_offset(), finished_callback=on_new)
        self._persist(page)

    def delete(self, _widget: object) -> None:
        """Delete the current box and persist the result."""
        bbox = self._current_bbox
        if bbox is None:
            return
        self.canvas.delete_word(bbox)
        self._commit()
        self.edit(self.canvas.get_current_bbox())

    def set_active(self, *, active: bool) -> None:
        """Show or hide the control bar."""
        if active:
            self.controls.show_all()
        else:
            self.controls.hide()

    def _new_layer_json(self, selection: Gdk.Rectangle | None, text: str) -> str:
        """Build the bboxtree JSON for a freshly created layer."""
        page = self._page()
        if page is None or selection is None:
            return ""
        width, height = page.get_size()
        return (
            f'[{{"type":"page","bbox":[0,0,{width},{height}],"depth":0}},'
            f'{{"type":"word","bbox":[{selection.x},{selection.y},'
            f"{selection.x + selection.width},"
            f'{selection.y + selection.height}],"text":"{text}","depth":1}}]'
        )

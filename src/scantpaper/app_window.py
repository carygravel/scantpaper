"""application window."""

from __future__ import annotations

import contextlib
import locale
import logging
import os
import pathlib
import re
import shutil
import sqlite3
import sys
from typing import Any, cast

import gi
import ocrmypdf
import sane  # To get SANE_* enums

from scantpaper import config
from scantpaper.clipboard import Clipboard
from scantpaper.const import (
    DRAGGER_TOOL,
    EMPTY,
    HALF,
    LOCAL_DOCS_URI,
    PROG_NAME,
    SELECTOR_TOOL,
    THUMBNAIL,
    URL,
    VERSION,
)
from scantpaper.dependencies import DEPS
from scantpaper.dialog import MultipleMessage
from scantpaper.document import Document
from scantpaper.edit_menu_mixins import EditMenuMixins
from scantpaper.file_menu_mixins import FileMenuMixins
from scantpaper.helpers import pack_box, recursive_slurp, run_dialog
from scantpaper.i18n import _, ngettext
from scantpaper.imageview import Dragger, ImageView, Selector, SelectorDragger
from scantpaper.progress import Progress
from scantpaper.scan_menu_item_mixins import ScanMenuItemMixins
from scantpaper.session_mixins import SessionMixins
from scantpaper.tesseract import (
    get_tesseract_codes,
    locale_installed,
    resolve_tessdata_dir,
)
from scantpaper.tools_menu_mixins import ToolsMenuMixins
from scantpaper.unpaper import Unpaper

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    Gio,
    GLib,
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)

GLib.set_application_name(PROG_NAME)
GLib.set_prgname("com.github.scantpaper")

# Notebook page indices, in the order _pack_viewer_tools appends them.
_IMAGE_PAGE = 0
_TEXT_PAGE = 1
_ANNOTATION_PAGE = 2

# The layers that can be active; the image-only tab is represented by None.
_EDIT_LAYERS = ("text", "annotation")


def _attach_thumbnail_css() -> Gtk.CssProvider | None:
    """Pin the paint size of the thumbnail pixbufs to the generated size.

    GTK4 paints Gtk.CellRendererPixbuf through an icon helper that clamps
    the paint to the stylesheet's -gtk-icon-size, shrinking the page
    thumbnails to 16px however large the pixbuf is. The renderer adds the
    "image" class to the treeview's own CSS node at paint time, so scoping
    the rule with the thumbnail list's class pins it without touching
    anything else.
    """
    display = Gdk.Display.get_default()
    if display is None:
        return None
    provider = Gtk.CssProvider()
    provider.load_from_data(
        f".thumbnail-list.image {{ -gtk-icon-size: {THUMBNAIL}px; }}".encode()
    )
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    return provider


def _attach_selection_css() -> Gtk.CssProvider | None:
    """Style the selection rectangles so they are visible on GTK4.

    The GTK4 default theme ships no `.rubberband` class rule; it only
    styles `rubberband` as a node that is a child of selection widgets,
    so the image view and canvas selection paint nothing. Load the class
    rule at APPLICATION priority so the shipped default still follows the
    active theme, and a user's `~/.config/gtk-4.0/gtk.css` `.rubberband`
    rule (user priority) overrides it.
    """
    display = Gdk.Display.get_default()
    if display is None:
        return None
    provider = Gtk.CssProvider()
    provider.load_from_data(
        b".rubberband {\n"
        b"  background-color: alpha(@theme_selected_bg_color, 0.2);\n"
        b"  background-image: none;\n"
        b"  border: 1px solid @theme_selected_bg_color;\n"
        b"}\n"
    )
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    return provider


def drag_motion_callback(
    target: Gtk.DropTarget, x: float, y: float, tree: Gtk.TreeView
) -> Gdk.DragAction:
    """Handle drag motion over the thumbnail list."""
    try:
        path, how = tree.get_dest_row_at_pos(int(x), int(y))
    except TypeError:  # for NoneType, which can't be unpacked
        return Gdk.DragAction.MOVE

    # Add the marker showing the drop in the tree
    tree.set_drag_dest_row(path, how)

    # Make move the default
    action = Gdk.DragAction.MOVE
    if target.get_actions() == Gdk.DragAction.COPY:
        action = Gdk.DragAction.COPY

    scroll = cast("Gtk.ScrolledWindow | None", tree.get_parent())
    if scroll is not None:
        adj = scroll.get_vadjustment()
        value, step = adj.get_value(), adj.get_step_increment()
        if y > adj.get_page_size() - step / 2:
            v = value + step
            m = adj.get_upper() - adj.get_page_size()
            adj.set_value(min(v, m))
        elif y < step / 2:
            v = value - step
            m = adj.get_lower()
            adj.set_value(max(v, m))
    return action


def view_html(_action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
    """Perhaps we should use gtk and mallard for this in the future."""
    # Or possibly https://github.com/ultrabug/mkdocs-static-i18n
    # At the moment, we have no translations,
    # but when we do, replace C with locale

    if pathlib.Path(LOCAL_DOCS_URI).exists():
        uri = GLib.filename_to_uri(LOCAL_DOCS_URI, None)  # None => no hostname
    else:
        uri = URL

    logger.info("Opening %s via default launcher", uri)
    context = Gio.AppLaunchContext()
    Gio.AppInfo.launch_default_for_uri(uri, context)


class ApplicationWindow(
    Gtk.ApplicationWindow,
    SessionMixins,
    FileMenuMixins,
    ScanMenuItemMixins,
    EditMenuMixins,
    ToolsMenuMixins,
):
    """ApplicationWindow class."""

    settings: dict[str, Any]
    _configfile = None
    _current_page = None
    _rotate_controls = None
    session = None  # session dir
    _args = None
    view = None
    _text_editor = None  # LayerEditor for the text layer
    _ann_editor = None  # LayerEditor for the annotation layer
    t_canvas = None  # Canvas for text layer (alias of _text_editor.canvas)
    a_canvas = None  # Canvas for annotation layer (alias of _ann_editor.canvas)
    _active_layer: str | None = None  # "text" | "annotation" | None (image tab)
    _in_edit_mode_change = False  # guards tab/action feedback loops
    _lockfd = None
    _pref_udt_cmbx = None
    _scan_udt_cmbx = None
    _scan_udt_hbox = None
    _scan_udt_button = None
    slist = None

    # Temp::File object for PDF to be emailed
    # Define here to make sure that it doesn't get deleted until the next email
    # is created or we quit
    _pdf_email = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise ."""
        kwargs["title"] = f"{PROG_NAME} v{VERSION}"
        super().__init__(*args, **kwargs)

        # https://gitlab.gnome.org/GNOME/gtk/-/blob/gtk-3-24/gtk/gtkbuilder.rnc
        base_path = pathlib.Path(pathlib.Path(__file__).parent).resolve()
        self.builder = Gtk.Builder()
        # Ensure Gtk.Builder uses the same gettext domain as the application
        self.builder.set_translation_domain(PROG_NAME)
        self.builder.add_from_file(str(base_path / "app.ui"))
        # GTK4 removed Gtk.Builder.connect_signals; app.ui declares no
        # <signal> handlers, they are all wired in Python below.
        self.detail_popup = self.builder.get_object("detail_popup")

        # These will be in the window group and have the "win" prefix
        self._actions = {}
        self._read_config()
        self._init_actions()

        self.clipboard = Clipboard()
        self.clipboard.connect("changed", self._update_paste_action)
        self._update_paste_action()

        # add the actions to the window that have window-classed callbacks
        self.add_action(self._actions["tooltype"])
        self.add_action(self._actions["viewtype"])
        self.add_action(self._actions["editmode"])

        # connect the action callback for tools and view
        self._actions["tooltype"].connect("activate", self._change_image_tool_cb)
        self._actions["viewtype"].connect("activate", self._change_view_cb)
        self._actions["editmode"].connect("activate", self._edit_mode_callback)

        self._dependencies = {}
        self._ocr_engine = []
        self._pre_flight()
        self.print_settings = None
        self._message_dialog = None
        self._windows = None
        self._windowc = None
        self._windowo = None
        self._windowu = None
        self._windowi = None
        self._windowe = None
        self._windowr = None
        self._windowp = None
        self._hpaned = self.builder.get_object("hpaned")
        self._vpaned = self.builder.get_object("vpaned")
        self._vpaned_initialised = False
        self._vnotebook = self.builder.get_object("vnotebook")
        self._hpanei = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._vpanei = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.connect("close-request", self._close_request)
        self.connect("notify::maximized", self._maximized_notify)

        # If defined in the config file, set the window state, size and position
        if self.settings["restore window"]:
            self.set_default_size(
                self.settings["window_width"], self.settings["window_height"]
            )

            if self.settings["window_maximize"]:
                self.maximize()

        self.set_icon_name("scantpaper")

        self._thumb_popup = self.builder.get_object("thumb_popup")

        self._populate_main_window()

    def _init_actions(self) -> None:
        for name, function in [
            ("new", self.new_),
            ("open", self.open_dialog),
            ("open-session", self._open_session_action),
            ("scan", self.scan_dialog),
            ("save", self.save_dialog),
            ("email", self.email),
            ("print", self.print_dialog),
            ("quit", self.quit_app),
            ("undo", self.undo),
            ("redo", self.unundo),
            ("cut", self.cut_selection),
            ("copy", self.copy_selection),
            ("paste", self.paste_selection),
            ("delete", self.delete_selection),
            ("select-all", self.select_all),
            ("select-odd", self._select_odd),
            ("select-even", self._select_even),
            ("select-invert", self.select_invert),
            ("select-blank", self.select_blank),
            ("select-dark", self.select_dark),
            ("select-modified", self.select_modified_since_ocr),
            ("select-no-ocr", self.select_no_ocr),
            ("clear-ocr", self.clear_ocr),
            ("properties", self.properties),
            ("preferences", self.preferences),
            ("zoom-100", self.zoom_100),
            ("zoom-to-fit", self.zoom_to_fit),
            ("zoom-in", self.zoom_in),
            ("zoom-out", self.zoom_out),
            ("rotate-90", self.rotate_90),
            ("rotate-180", self.rotate_180),
            ("rotate-270", self.rotate_270),
            ("threshold", self.threshold),
            ("brightness-contrast", self.brightness_contrast),
            ("negate", self.negate),
            ("unsharp", self.unsharp),
            ("crop-dialog", self.crop_dialog),
            ("crop-selection", self.crop_selection),
            ("split", self.split_dialog),
            ("unpaper", self.unpaper_dialog),
            ("ocr", self.ocr_dialog),
            ("user-defined", self.user_defined_dialog),
            ("help", view_html),
            ("about", self.about),
        ]:
            self._actions[name] = Gio.SimpleAction.new(name, None)
            self._actions[name].connect("activate", function)
            self.add_action(self._actions[name])

        # action with a state created (name, parameter type, initial state)
        self._actions["tooltype"] = Gio.SimpleAction.new_stateful(
            "tooltype",
            GLib.VariantType("s"),
            GLib.Variant("s", self.settings["image_control_tool"]),
        )
        self._actions["viewtype"] = Gio.SimpleAction.new_stateful(
            "viewtype",
            GLib.VariantType("s"),
            GLib.Variant("s", self.settings["viewer_tools"]),
        )
        self._actions["editmode"] = Gio.SimpleAction.new_stateful(
            "editmode",
            GLib.VariantType("s"),
            GLib.Variant("s", self._active_layer_setting()),
        )

    def _close_request(self, _widget: Gtk.Widget) -> bool:
        return not self._can_quit()

    def _maximized_notify(
        self, _widget: GObject.Object, _pspec: GObject.ParamSpec
    ) -> None:
        self.settings["window_maximize"] = bool(self.is_maximized())

    def _pre_flight(self) -> None:
        """Initialise variables, read configuration, and initialise components."""
        if self.settings["cwd"] is None:
            self.settings["cwd"] = str(pathlib.Path.cwd())
        self.settings["version"] = VERSION

        logger.info("Operating system: %s", sys.platform)
        if sys.platform == "linux":
            recursive_slurp(pathlib.Path("/etc").glob("*-release"))

        logger.info("Python version %s", sys.version_info)
        logger.info("GLib VERSION_MIN_REQUIRED %s", GLib.VERSION_MIN_REQUIRED)
        logger.info(
            "GLib built %s.%s.%s",
            GLib.MAJOR_VERSION,
            GLib.MINOR_VERSION,
            GLib.MICRO_VERSION,
        )
        logger.info("gi.__version__ %s", gi.__version__)
        logger.info("gi.version_info %s", gi.version_info)
        logger.info(
            "Built for GTK %s.%s.%s",
            Gtk.MAJOR_VERSION,
            Gtk.MINOR_VERSION,
            Gtk.MICRO_VERSION,
        )
        logger.info(
            "Running with GTK %s.%s.%s",
            Gtk.get_major_version(),
            Gtk.get_minor_version(),
            Gtk.get_micro_version(),
        )
        logger.info("sane.__version__ %s", sane.__version__)
        logger.info("sane.init() %s", sane.init())
        logger.info("SQLite C library version: %s", sqlite3.sqlite_version)
        logger.info("SQLite thread safety level: %s", sqlite3.threadsafety)
        logger.info("ocrmypdf.__version__ %s", ocrmypdf.__version__)

        # initialise image control tool radio button setting
        self._change_image_tool_cb(
            self._actions["tooltype"],
            GLib.Variant("s", self.settings["image_control_tool"]),
        )

    def _read_config(self) -> None:
        """Read the configuration file."""
        # config files: XDG_CONFIG_HOME/scantpaperrc or HOME/.config/scantpaperrc
        rcdir = (
            os.environ["XDG_CONFIG_HOME"]
            if "XDG_CONFIG_HOME" in os.environ
            else f"{os.environ['HOME']}/.config"
        )
        self._configfile = f"{rcdir}/{PROG_NAME}rc"
        old_configfile = f"{rcdir}/gscan2pdfrc"
        if (
            not pathlib.Path(self._configfile).exists()
            and pathlib.Path(old_configfile).exists()
        ):
            shutil.copy(old_configfile, self._configfile)
        self.settings = config.read_config(self._configfile)
        self._config_load_warnings = list(
            getattr(self.settings, "load_warnings", None) or ()
        )
        self._config_warnings_acknowledged = not self._config_load_warnings
        config.add_defaults(self.settings)
        config.remove_invalid_paper(self.settings["Paper"])

    def _populate_main_window(self) -> None:
        """Populate the main window with various UI components and set up necessary callbacks."""
        self._connect_popover_signals()
        self._create_temp_directory()

        # Set up an SimpleList for the thumbnail view
        self.slist = Document(dir=self.session.name, db=self.session.name + ".sdb")

        _attach_thumbnail_css()
        _attach_selection_css()

        # Update list in Document so that it can be used by get_resolution()
        self.slist.set_paper_sizes(self.settings["Paper"])

        main_vbox = self.builder.get_object("main_vbox")
        self.set_child(main_vbox)

        self._populate_panes()

        # Create the toolbar
        self._create_toolbar()

        self._add_text_view_layers()

        # Keep the active layer following the notebook page in tabbed mode.
        self._vnotebook.connect("switch-page", self._on_switch_page)

        # Set up call back for list selection to update detail view
        self.slist.selection_changed_signal = self.slist.get_selection().connect(
            "changed", self._page_selection_changed_callback
        )

        # Without these, the imageviewer and page list steal -/+/ctrl x/c/v keys
        # from the OCR textview
        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-pressed", self._on_key_press)
        self.add_controller(self._key_controller)

        # If defined in the config file, set the current directory
        if "cwd" not in self.settings:
            self.settings["cwd"] = str(pathlib.Path.cwd())
        self._unpaper = Unpaper(self.settings["unpaper options"])
        self._update_uimanager()

        self._notify_config_load_warnings()

        # Progress bars below window
        phbox = self.builder.get_object("progress_hbox")
        self._scan_progress = Progress()
        pack_box(phbox, self._scan_progress, expand=True)
        self.post_process_progress = Progress()
        pack_box(phbox, self.post_process_progress, expand=True)
        # Child widgets are already shown in Progress.__init__, container starts hidden
        self.post_process_progress.cancel_callback = self._cancel_post_process

        # Apply the persisted active layer (default text) so the View menu is
        # correct from the first paint. In tabbed mode the visible page is left
        # alone (the window opens on the scan), and the control bar only appears
        # while the layer's own canvas is shown, so it stays hidden here. In a
        # split view the layer's canvas and bar are shown beside the image.
        if self.settings["viewer_tools"] == "tabbed":
            self._apply_active_layer_state(self._active_layer_setting())
        else:
            self._set_active_layer(self._active_layer_for_split())

        # Open scan dialog in background
        if self.settings["auto-open-scan-dialog"]:
            self.scan_dialog(None, None, hidden=True)

        self._find_crashed_sessions()

        # Deal with --import command line option
        args = self.get_application().args
        if args.import_files is not None:
            self._import_files(args.import_files)
        if args.import_all is not None:
            self._import_files(args.import_all, all_pages=True)

    def _cancel_post_process(self) -> None:
        """Cancel all queued and running post-process jobs."""
        self.slist.cancel(self.post_process_progress.finish)

    def _populate_panes(self) -> None:

        # HPaned for thumbnails and detail view
        self._hpaned.set_position(self.settings["thumb panel"])

        # Scrolled window for thumbnails
        scwin_thumbs = self.builder.get_object("scwin_thumbs")

        # resize = FALSE to stop the panel expanding on being resized
        # (Debian #507032)
        # controls in pack1/2 don't seem to be available via UI XML in Gtk4
        self._hpaned.set_start_child(None)
        self._hpaned.set_start_child(scwin_thumbs)

        # Highlight the drop position and auto-scroll while dragging. The GTK4
        # replacement for the old "drag-motion" signal is the "motion" signal
        # of the drop targets that BaseDocument installs.
        self.slist.rows_drop_target.connect("motion", drag_motion_callback, self.slist)
        self.slist.files_drop_target.connect("motion", drag_motion_callback, self.slist)

        # Set up callback for right mouse clicks (GTK4: Gtk.GestureClick).
        self._add_secondary_click_controller(self.slist)
        scwin_thumbs.set_child(self.slist)

        # Notebook, split panes for detail view and OCR output
        # controls in pack1/2 don't seem to be available via UI XML in Gtk4
        self._vpaned.set_start_child(None)
        self._vpaned.set_start_child(self._vnotebook)
        edit_hbox = self.builder.get_object("edit_hbox")
        self._vpaned.set_end_child(None)
        self._vpaned.set_end_child(edit_hbox)

        # ImageView for detail view
        self.view = ImageView()
        if self.settings["image_control_tool"] == SELECTOR_TOOL:
            self.view.set_tool(Selector(self.view))
        elif self.settings["image_control_tool"] == DRAGGER_TOOL:
            self.view.set_tool(Dragger(self.view))
        else:
            self.view.set_tool(SelectorDragger(self.view))

        self._add_secondary_click_controller(self.view)
        self.view.selection_changed_signal = self.view.connect(
            "selection-changed", self._view_selection_changed_callback
        )
        self.view.connect("notify::selection", self._on_view_selection_notify)

    def _missing_packages_message(self) -> str:
        """Return the warning message for packages needed by the tools."""
        msg = EMPTY
        self._dependencies["ocr"] = self._dependencies["tesseract"]
        for dep in DEPS:
            if not dep.warn_at_startup:
                continue
            if dep.name == "tesseract":
                if not self._dependencies["ocr"]:
                    msg += dep.message + "\n"
                else:
                    lc_messages = locale.setlocale(locale.LC_MESSAGES)
                    tessdata_path, tessdata_error = resolve_tessdata_dir("")
                    if tessdata_error is not None:
                        # A broad TESSDATA_PREFIX is reported in the log, not as
                        # a missing-language package: the language list cannot
                        # be discovered safely through it.
                        logger.warning(tessdata_error)
                    else:
                        lang_msg = locale_installed(
                            lc_messages, get_tesseract_codes(tessdata_path)
                        )
                        if lang_msg == "":
                            logger.info(
                                "Using GUI language %s, for which a tesseract language package is present",
                                lc_messages,
                            )
                        else:
                            logger.warning(lang_msg)
                            msg += lang_msg
                continue
            if not self._dependencies[dep.name]:
                msg += dep.message + "\n"

        return msg

    def _create_toolbar(self) -> None:
        # Check for presence of various packages
        self._check_dependencies()

        msg = self._missing_packages_message()

        # Undo/redo, save & tools start off ghosted anyway-
        for action in [
            "undo",
            "redo",
            "save",
            "email",
            "print",
            "threshold",
            "brightness-contrast",
            "negate",
            "unsharp",
            "crop-dialog",
            "crop-selection",
            "split",
            "unpaper",
            "ocr",
            "user-defined",
        ]:
            self._actions[action].set_enabled(False)

        # Put up warning if needed
        if msg != EMPTY:
            msg = _("Warning: missing packages") + f"\n{msg}"
            self._show_message_dialog(
                parent=self,
                message_type="warning",
                buttons=Gtk.ButtonsType.OK,
                text=msg,
                store_response=True,
            )

    def _init_split_pane(
        self,
        pane: Gtk.Paned,
        orientation: Gtk.Orientation,
        saved_position: int | None,
        *,
        end_at_minimum: bool = False,
    ) -> None:
        """Give a split pane a usable divider position on startup.

        A freshly created GtkPaned derives its divider from the children's
        initial size requests, which are empty before any image loads, so it
        can collapse to an edge and hide the image. Restore a saved position,
        or set a default on the first allocation, so both panes are visible. A
        saved position is clamped into
        [handle + child1_min, size - handle - child2_min]: a position saved
        under an older, larger geometry would otherwise fill the whole pane
        and hide a child. (GtkPaned's own minimum request is just the handle
        size, and it overflows rather than clamps a too-large position.)

        The default is a half split, which suits the image/layer panes. For the
        outer pane that stacks the view above the edit bar, ``end_at_minimum``
        instead pins the end child (the bar) to its minimum height so it only
        takes the space it needs.
        """

        def measure(widget: Gtk.Widget | None) -> int:
            if widget is None:
                return 0
            return cast("int", widget.measure(orientation, -1).minimum)

        def bounds() -> tuple[int, int, int]:
            size = cast(
                "int",
                pane.get_width()
                if orientation == Gtk.Orientation.HORIZONTAL
                else pane.get_height(),
            )
            handle = measure(pane)
            return (
                handle + measure(pane.get_start_child()),
                size - handle - measure(pane.get_end_child()),
                size,
            )

        def on_tick(_widget: Gtk.Widget, _clock: Gdk.FrameClock) -> bool:
            low, high, size = bounds()
            if size <= 1:
                # Not allocated yet; keep ticking until the pane has a size.
                return True
            if saved_position is None:
                position = high if end_at_minimum else size // 2
            else:
                position = int(saved_position)
            pane.set_position(max(min(position, high), low))
            # Returning False removes the tick callback.
            return False

        pane.add_tick_callback(on_tick)

    def _pack_viewer_tools(self) -> None:
        # The .ui and _populate_panes leave _vnotebook in _vpaned's pack1.
        # GtkPaned.pack1 silently keeps an existing pack1 child, so it must be
        # removed before packing the (possibly different) view container, or a
        # split view would never become visible on startup.
        child1 = self._vpaned.get_start_child()
        if child1 is not None:
            self._vpaned.set_start_child(None)
        if self.settings["viewer_tools"] == "tabbed":
            # Returning to the notebook: release the split panes first so the
            # pages can be re-appended.
            self._hpanei.set_start_child(None)
            self._hpanei.set_end_child(None)
            self._vpanei.set_start_child(None)
            self._vpanei.set_end_child(None)
            self._vnotebook.append_page(self.view, Gtk.Label(label=_("Image")))
            self._vnotebook.append_page(self.t_canvas, Gtk.Label(label=_("Text layer")))
            self._vnotebook.append_page(
                self.a_canvas, Gtk.Label(label=_("Annotations"))
            )
            self._vpaned.set_start_child(self._vnotebook)
        elif self.settings["viewer_tools"] == "horizontal":
            self._dock_view_and_layer(self._hpanei)
            self._vpaned.set_start_child(self._hpanei)
            self._init_split_pane(
                self._hpanei,
                Gtk.Orientation.HORIZONTAL,
                self.settings.get("split panel h"),
            )
        else:  # vertical
            self._dock_view_and_layer(self._vpanei)
            self._vpaned.set_start_child(self._vpanei)
            self._init_split_pane(
                self._vpanei,
                Gtk.Orientation.VERTICAL,
                self.settings.get("split panel v"),
            )

        # The outer pane collapses to child1's minimum request (the tab
        # header or the paned handle) unless given an explicit position:
        # a bare DrawingArea requests a 0x0 minimum, so the image view
        # would end up a 0-1px sliver. Apply the default once per process,
        # so view-mode switches keep the user's adjustment.
        if not self._vpaned_initialised:
            self._vpaned_initialised = True
            self._init_split_pane(
                self._vpaned,
                Gtk.Orientation.VERTICAL,
                None,
                end_at_minimum=True,
            )

    def _dock_view_and_layer(self, pane: Gtk.Paned) -> None:
        """Show the image and the active layer's canvas side by side."""
        # Release both split panes: switching orientation must empty the pane
        # the children are currently docked in before they can be re-docked.
        for split in (self._hpanei, self._vpanei):
            split.set_start_child(None)
            split.set_end_child(None)
        for widget in (self.view, self.t_canvas, self.a_canvas):
            if widget is not None and self._vnotebook.page_num(widget) != -1:
                self._vnotebook.detach_tab(widget)
        pane.set_start_child(self.view)
        pane.set_end_child(self._active_canvas())

    def _connect_popover_signals(self) -> None:
        detail = {
            "detail_zoom_100": self._on_zoom_100,
            "detail_zoom_to_fit": self._on_zoom_to_fit,
            "detail_zoom_in": self._on_zoom_in,
            "detail_zoom_out": self._on_zoom_out,
            "detail_rotate_90": self._on_rotate_90,
            "detail_rotate_180": self._on_rotate_180,
            "detail_rotate_270": self._on_rotate_270,
            "detail_crop": self._on_crop,
            "detail_cut": self._on_cut,
            "detail_copy": self._on_copy,
            "detail_paste": self._on_paste,
            "detail_delete": self._on_delete,
            "detail_properties": self._on_properties,
        }
        thumb = {
            "thumb_save": self._on_save,
            "thumb_email": self._on_email,
            "thumb_print": self._on_print,
            "thumb_select_all": self._on_select_all,
            "thumb_select_odd": self._on_select_odd,
            "thumb_select_even": self._on_select_even,
            "thumb_invert_selection": self._on_invert_selection,
            "thumb_rotate_90": self._on_rotate_90,
            "thumb_rotate_180": self._on_rotate_180,
            "thumb_rotate_270": self._on_rotate_270,
            "thumb_crop": self._on_crop,
            "thumb_cut": self._on_cut,
            "thumb_copy": self._on_copy,
            "thumb_paste": self._on_paste,
            "thumb_delete": self._on_delete,
            "thumb_clear_ocr": self._on_clear_ocr,
            "thumb_properties": self._on_properties,
        }
        self.detail_popup.set_parent(self)
        self._thumb_popup.set_parent(self)
        for mapping in (detail, thumb):
            for object_id, handler in mapping.items():
                self.builder.get_object(object_id).connect("clicked", handler)

    def _add_secondary_click_controller(self, widget: Gtk.Widget) -> None:
        """Attach the right-click popup handler to a widget (GTK4 gestures)."""
        gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self._handle_clicks)
        widget.add_controller(gesture)

    def _handle_clicks(
        self,
        gesture: Gtk.GestureClick,
        _n_press: int,
        _x: float,
        _y: float,
    ) -> None:
        widget = gesture.get_widget()
        if isinstance(widget, ImageView):  # main image
            self.detail_popup.popup()
        else:  # Thumbnail SimpleList
            self.settings["Page range"] = "selected"
            self._thumb_popup.popup()

        # block event propagation
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _view_selection_changed_callback(
        self, _view: ImageView, sel: Gdk.Rectangle
    ) -> None:
        # copy required here because somehow the garbage collection
        # destroys the Gdk.Rectangle too early and afterwards, the
        # contents are corrupt.
        self.settings["selection"] = sel.copy()

    def _on_view_selection_notify(
        self, _view: GObject.Object, _pspec: GObject.ParamSpec
    ) -> None:
        sel = self.view.selection
        if sel is not None:
            self.settings["selection"] = sel.copy()

    def _on_key_press(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval != Gdk.KEY_Delete:
            return False
        self.delete_selection(None, None)
        return True

    _in_tool_change = False

    def _change_image_tool_cb(
        self, action: Gio.SimpleAction, value: GLib.Variant
    ) -> None:
        # GTK3 GtkCheckMenuItem.set_active() calls gtk_menu_item_activate(),
        # re-activating the action with the deactivated item's target value.
        if self._in_tool_change:
            return
        self._in_tool_change = True

        value = value.get_string()
        if action.get_state().get_string() == value:
            self._in_tool_change = False
            return

        action.set_state(GLib.Variant("s", value))

        if self.view:  # could be undefined at application start
            tool = Selector(self.view)
            if value == "dragger":
                tool = Dragger(self.view)
            elif value == "selectordragger":
                tool = SelectorDragger(self.view)
            self.view.set_tool(tool)
            if (
                value in ["selector", "selectordragger"]
                and "selection" in self.settings
                and self.settings["selection"] is not None
            ):
                self.view.handler_block(self.view.selection_changed_signal)
                self.view.set_selection(self.settings["selection"])
                self.view.handler_unblock(self.view.selection_changed_signal)

        self.settings["image_control_tool"] = value
        self._in_tool_change = False

    def _active_layer_setting(self) -> str:
        """Return the persisted active layer, defaulting to the text layer."""
        stored = self.settings.get("editmode")
        if stored in _EDIT_LAYERS:
            return cast("str", stored)
        return "text"

    def _active_layer_for_split(self) -> str:
        """Return the layer to show beside the image in a split view.

        Falls back to the last layer that was active, so entering a split from
        the image-only tab keeps the layer the user was working on.
        """
        if self._active_layer in _EDIT_LAYERS:
            return cast("str", self._active_layer)
        return self._active_layer_setting()

    def _active_canvas(self) -> Gtk.Widget | None:
        """Return the canvas belonging to the layer shown in a split view."""
        if self._active_layer_for_split() == "annotation":
            return self.a_canvas
        return self.t_canvas

    def _sync_editmode_action(self, mode: str) -> None:
        """Mirror the active layer onto the editmode action."""
        action = self._actions["editmode"]
        if action.get_state().get_string() != mode:
            action.set_state(GLib.Variant("s", mode))

    def _layer_on_screen(self, page_num: int | None = None) -> bool:
        """Return whether the active layer's canvas is the one being shown.

        In tabbed mode the Image page shows the unannotated scan, so the layer's
        control bar is hidden there even though the layer stays selected. The
        bar reappears when the layer's own page or a split view is show.
        """
        if self.settings["viewer_tools"] != "tabbed":
            return True
        if page_num is None:
            page_num = cast("int", self._vnotebook.get_current_page())
        return page_num != _IMAGE_PAGE

    def _update_layer_visibility(self, page_num: int | None = None) -> None:
        """Show the active layer's control bar only while its canvas is shown."""
        layer = self._active_layer if self._layer_on_screen(page_num) else None
        self._text_editor.set_active(active=layer == "text")
        self._ann_editor.set_active(active=layer == "annotation")

    def _select_page_for_layer(self, mode: str) -> None:
        """Select the notebook page representing the given layer."""
        page = _TEXT_PAGE if mode == "text" else _ANNOTATION_PAGE
        self._in_edit_mode_change = True
        self._vnotebook.set_current_page(page)
        self._in_edit_mode_change = False

    def _apply_active_layer_state(self, mode: str, page_num: int | None = None) -> None:
        """Record mode as the active layer and update its editor."""
        self._active_layer = mode
        self.settings["editmode"] = mode
        self._sync_editmode_action(mode)
        self._update_layer_visibility(page_num)

    def _set_active_layer(self, mode: str) -> None:
        """Make mode the active layer and show its editor everywhere.

        In tabbed mode the matching page is selected; in a split view the pane
        is repacked so the layer's canvas is the one shown beside the image.
        """
        self._active_layer = mode
        self.settings["editmode"] = mode
        self._sync_editmode_action(mode)
        if self.settings["viewer_tools"] == "tabbed":
            self._select_page_for_layer(mode)
        else:
            self._pack_viewer_tools()
        self._update_layer_visibility()

    def _on_switch_page(
        self, _notebook: Gtk.Notebook, _page: object, page_num: int
    ) -> None:
        """Follow a tab change in tabbed mode."""
        if self._in_edit_mode_change or self.settings["viewer_tools"] != "tabbed":
            return
        if page_num == _TEXT_PAGE:
            mode = "text"
        elif page_num == _ANNOTATION_PAGE:
            mode = "annotation"
        else:
            # The image page is not a layer: keep the last active one selected
            # but hide its bar, which reappears with its own canvas.
            mode = self._active_layer or self._active_layer_setting()
        self._apply_active_layer_state(mode, page_num)

    def _change_view_cb(
        self, action: Gio.SimpleAction, parameter: GLib.Variant
    ) -> None:
        """Switch between tabbed and split views."""
        action.set_state(parameter)
        mode = parameter.get_string()
        self.settings["viewer_tools"] = mode
        layer = self._active_layer_for_split()
        self._active_layer = layer
        # Appending or detaching notebook pages emits switch-page; the guard
        # stops the handler from clobbering the active layer mid-transition.
        self._in_edit_mode_change = True
        try:
            self._pack_viewer_tools()
            if mode == "tabbed":
                self._vnotebook.set_current_page(
                    _TEXT_PAGE if layer == "text" else _ANNOTATION_PAGE
                )
        finally:
            self._in_edit_mode_change = False
        self.settings["editmode"] = layer
        self._sync_editmode_action(layer)
        self._update_layer_visibility()

    def _page_selection_changed_callback(self, _selection: Gtk.TreeSelection) -> None:
        selection = self.slist.get_selected_indices()

        # Display the new image
        # When editing the page number, there is a race condition where the page
        # can be undefined
        if selection:
            i = selection.pop(0)
            path = Gtk.TreePath.new_from_indices([i])
            self.slist.scroll_to_cell(
                path,
                self.slist.get_column(0),
                use_align=True,
                row_align=HALF,
                col_align=HALF,
            )
            with contextlib.suppress(ValueError):
                # if a page is deleted this is still fired, so ignore it
                self._display_image(self.slist.data[i][2])
        else:
            self.view.set_pixbuf(None)
            self.t_canvas.clear_text()
            self.a_canvas.clear_text()
            self._current_page = None

        self._update_uimanager()

        # Because changing the selection hits the database in the thread, we also
        # have to ensure that any progress bars are hidden afterwards if neceesary.
        self.post_process_progress.finish(None)

    def _update_paste_action(self, _clipboard: object = None) -> None:
        """Enable or disable the paste action based on clipboard contents."""
        if "paste" in self._actions:
            self._actions["paste"].set_enabled(self.clipboard.has_data)

    def _update_uimanager(self) -> None:
        action_names = [
            "cut",
            "copy",
            "delete",
            "select-all",
            "select-odd",
            "select-even",
            "select-invert",
            "select-blank",
            "select-dark",
            "select-modified",
            "select-no-ocr",
            "clear-ocr",
            "properties",
            "tooltype",
            "viewtype",
            "editmode",
            "zoom-100",
            "zoom-to-fit",
            "zoom-in",
            "zoom-out",
            "rotate-90",
            "rotate-180",
            "rotate-270",
            "threshold",
            "brightness-contrast",
            "negate",
            "unsharp",
            "crop-dialog",
            "crop-selection",
            "unpaper",
            "split",
            "ocr",
            "user-defined",
        ]
        enabled = bool(self.slist.get_selected_indices())
        for action_name in action_names:
            if action_name in self._actions:
                self._actions[action_name].set_enabled(enabled)
        self.detail_popup.set_sensitive(enabled)

        # Ghost unpaper item if unpaper not available
        if not self._dependencies["unpaper"] and "unpaper" in self._actions:
            self._actions["unpaper"].set_enabled(False)
            del self._actions["unpaper"]

        # Ghost ocr item if ocr  not available
        if not self._dependencies["ocr"]:
            self._actions["ocr"].set_enabled(False)

        self._update_send_save_actions()

        # Un/ghost Undo/redo
        self._actions["undo"].set_enabled(self.slist.thread.can_undo())
        self._actions["redo"].set_enabled(self.slist.thread.can_redo())

        # Check free space in session directory
        self._check_disk_space()

    def _update_send_save_actions(self) -> None:
        """Enable or disable email/print/save depending on page selection."""
        if len(self.slist.data) > 0:
            if self._dependencies["xdg"]:
                self._actions["email"].set_enabled(True)

            self._actions["print"].set_enabled(True)
            self._actions["save"].set_enabled(True)

        else:
            if self._dependencies["xdg"]:
                self._actions["email"].set_enabled(False)
                if self._windowe is not None:
                    self._windowe.hide()

            self._actions["print"].set_enabled(False)
            self._actions["save"].set_enabled(False)

    def _check_disk_space(self) -> None:
        """Warn if free space in the session directory is running low."""
        df = shutil.disk_usage(self.session.name).free / 1024 / 1024
        logger.debug(
            "Free space in %s (Mb): %s (warning at %s)",
            self.session.name,
            df,
            self.settings["available-tmp-warning"],
        )
        if df < cast("int", self.settings["available-tmp-warning"]):
            text = ngettext(
                "%(mb)dMb free in %(name)s.", "%(mb)dMb free in %(name)s.", int(df)
            ) % {
                "mb": int(df),
                "name": self.session.name,
            }
            self._show_message_dialog(
                parent=self,
                message_type="warning",
                buttons=Gtk.ButtonsType.CLOSE,
                text=text,
            )

    def _notify_config_load_warnings(self) -> None:
        """Inform the user that settings could not be read in full."""
        if not self._config_load_warnings or self._config_warnings_acknowledged:
            return
        self._config_warnings_acknowledged = True
        self._show_message_dialog(
            parent=self,
            message_type="info",
            buttons=Gtk.ButtonsType.CLOSE,
            text="\n".join(self._config_load_warnings),
        )

    def _show_message_dialog(self, **kwargs: object) -> None:
        """Display a message dialog with the given options."""
        if self._message_dialog is None:
            self._message_dialog = MultipleMessage(
                title=_("Messages"), transient_for=kwargs["parent"]
            )
            self._message_dialog.set_default_size(
                self.settings["message_window_width"],
                self.settings["message_window_height"],
            )

        kwargs["responses"] = self.settings["message"]
        self._message_dialog.add_message(kwargs)
        response = None
        if self._message_dialog.grid_rows > 1:
            response = run_dialog(self._message_dialog)

        self._message_dialog.store_responses(
            response,
            cast("dict[str, dict[str, object]]", self.settings["message"]),
        )
        # GTK4 removed the Gtk3 PyGObject Widget.get_size() tuple helper.
        self.settings["message_window_width"] = self._message_dialog.get_width()
        self.settings["message_window_height"] = self._message_dialog.get_height()
        self._message_dialog.destroy()
        self._message_dialog = None

    def _process_error_callback(
        self, widget: Gtk.Widget, process: str, msg: str, signal: int | None
    ) -> None:
        """Handle process errors."""
        logger.info("signal 'process-error' emitted with data: %s %s", process, msg)
        if signal is not None:
            self._scan_progress.disconnect(signal)

        self._scan_progress.hide()
        if process == "open_device" and re.search(
            r"(Invalid[ ]argument|Device[ ]busy|Error[ ]during[ ]device[ ]I/O)", msg
        ):
            self._handle_device_open_error()
            return

        self._show_message_dialog(
            parent=widget,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            page=EMPTY,
            process=process,
            text=msg,
            store_response=True,
        )

    def _handle_device_open_error(self) -> None:
        """Handle an error opening the last device used."""
        error_name = "error opening device"
        response = None
        if (
            error_name in cast("dict[str, Any]", self.settings["message"])
            and self.settings["message"][error_name]["response"] == "ignore"
        ):
            response = self.settings["message"][error_name]["response"]
        else:
            response = self._ask_device_open_error(error_name)

        # The modal dialog runs a nested main loop, so the progress bar may
        # have been re-shown by running callbacks. Ensure it stays hidden
        # regardless of the option chosen.
        self._scan_progress.hide()
        self._windows = None  # force scan dialog to be rebuilt
        if response == "reopen":
            self.scan_dialog(None, None)
        elif response == "rescan":
            self.scan_dialog(None, None, hidden=False, scan=True)
        elif response == "restart":
            self._restart()

        # for ignore, we do nothing

    def _ask_device_open_error(self, error_name: str) -> str:
        """Ask how to proceed after an open-device error; return the response."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            destroy_with_parent=True,
            modal=True,
            message_type="question",
            buttons=Gtk.ButtonsType.OK,
        )
        dialog.set_title(_("Error opening the last device used."))
        area = dialog.get_message_area()
        label = Gtk.Label(label=_("There was an error opening the last device used."))
        area.append(label)
        radio1 = Gtk.CheckButton.new_with_label(
            label=_("Whoops! I forgot to turn it on. Try again now.")
        )
        area.append(radio1)
        # GTK3 made the first radio button of a group active by default;
        # grouped check buttons in GTK4 do not, so activate it explicitly.
        radio1.set_active(True)
        radio2 = Gtk.CheckButton.new_with_label(label=_("Rescan for devices"))
        radio2.set_group(radio1)
        area.append(radio2)
        radio3 = Gtk.CheckButton.new_with_label(label=_("Restart scantpaper."))
        radio3.set_group(radio1)
        area.append(radio3)
        radio4 = Gtk.CheckButton.new_with_label(
            label=_("Just ignore the error. I don't need the scanner yet."),
        )
        radio4.set_group(radio1)
        area.append(radio4)
        cb_cache_device_list = Gtk.CheckButton.new_with_label(_("Cache device list"))
        cb_cache_device_list.set_active(self.settings["cache-device-list"])
        area.append(cb_cache_device_list)
        cb = Gtk.CheckButton.new_with_label(label=_("Don't show this message again"))
        area.append(cb)
        response = run_dialog(dialog)
        dialog.destroy()
        if response != Gtk.ResponseType.OK or radio4.get_active():
            response = "ignore"
        elif radio1.get_active():
            response = "reopen"
        elif radio3.get_active():
            response = "restart"
        else:
            response = "rescan"
        if cb.get_active():
            # The key need not exist yet: this dialog is shown precisely when
            # there is no stored response for it.
            self.settings["message"].setdefault(error_name, {})["response"] = response
        return response

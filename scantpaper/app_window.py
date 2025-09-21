"application window"

import os
import pathlib
import locale
import re
import glob
import logging
import shutil
import sqlite3
import sys
from const import DRAGGER_TOOL, EMPTY, HALF, SELECTOR_TOOL, VERSION, PROG_NAME
from dialog import MultipleMessage
from document import Document
from unpaper import Unpaper
from canvas import Canvas
from imageview import ImageView, Selector, Dragger, SelectorDragger
from progress import Progress
from file_menu_mixins import FileMenuMixins
from session_mixins import SessionMixins
from scan_menu_item_mixins import ScanMenuItemMixins
from edit_menu_mixins import EditMenuMixins
from tools_menu_mixins import ToolsMenuMixins
import config
from i18n import _
from helpers import recursive_slurp
from tesseract import locale_installed, get_tesseract_codes
import sane  # To get SANE_* enums
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)

GLib.set_application_name(PROG_NAME)
GLib.set_prgname("net.sourceforge.gscan2pdf")


def drag_motion_callback(tree, context, x, y, t):
    "Handle drag motion"
    try:
        path, how = tree.get_dest_row_at_pos(x, y)
    except TypeError:  # for NoneType, which can't be unpacked
        return
    scroll = tree.get_parent()

    # Add the marker showing the drop in the tree
    tree.set_drag_dest_row(path, how)

    # Make move the default
    action = Gdk.DragAction.MOVE
    if context.get_actions() == Gdk.DragAction.COPY:
        action = Gdk.DragAction.COPY

    Gdk.drag_status(context, action, t)
    adj = scroll.get_vadjustment()
    value, step = adj.get_value(), adj.get_step_increment()
    if y > adj.get_page_size() - step / 2:
        v = value + step
        m = adj.get_upper(-adj.get_page_size())
        adj.set_value(m if v > m else v)
    elif y < step / 2:
        v = value - step
        m = adj.get_lower()
        adj.set_value(m if v < m else v)


def view_html(_action, _param):
    "Perhaps we should use gtk and mallard for this in the future"
    # Or possibly https://github.com/ultrabug/mkdocs-static-i18n
    # At the moment, we have no translations,
    # but when we do, replace C with locale

    uri = f"/usr/share/help/C/{PROG_NAME}/documentation.html"
    if pathlib.Path(uri).exists():
        uri = GLib.filename_to_uri(uri, None)  # undef => no hostname
    else:
        uri = "http://gscan2pdf.sf.net"

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
    "ApplicationWindow class"

    settings = None
    _configfile = None
    _current_page = None
    _current_ocr_bbox = None
    _current_ann_bbox = None
    _prevent_image_tool_update = False
    _rotate_controls = None
    session = None  # session dir
    _args = None  # GooCanvas for text layer
    view = None
    t_canvas = None  # GooCanvas for annotation layer
    a_canvas = None
    _ocr_text_hbox = None
    _ocr_textbuffer = None
    _ann_hbox = None
    _ann_textbuffer = None
    _lockfd = None
    _pref_udt_cmbx = None
    _scan_udt_cmbx = None
    _fonts = None
    slist = None

    # Temp::File object for PDF to be emailed
    # Define here to make sure that it doesn't get deleted until the next email
    # is created or we quit
    _pdf_email = None

    def __init__(self, *args, **kwargs):
        kwargs["title"] = f"{PROG_NAME} v{VERSION}"
        super().__init__(*args, **kwargs)

        # https://gitlab.gnome.org/GNOME/gtk/-/blob/gtk-3-24/gtk/gtkbuilder.rnc
        base_path = os.path.abspath(os.path.dirname(__file__))
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(base_path, "app.ui"))
        self.builder.connect_signals(self)
        self.detail_popup = self.builder.get_object("detail_popup")

        # These will be in the window group and have the "win" prefix
        self._actions = {}
        self._init_actions()

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
        self._vnotebook = self.builder.get_object("vnotebook")
        self._hpanei = Gtk.HPaned()
        self._vpanei = Gtk.VPaned()
        self.connect("delete-event", lambda w, e: not self._can_quit())
        self.connect("window-state-event", self._window_state_event_callback)

        # If defined in the config file, set the window state, size and position
        if self.settings["restore window"]:
            self.set_default_size(
                self.settings["window_width"], self.settings["window_height"]
            )
            if "window_x" in self.settings and "window_y" in self.settings:
                self.move(self.settings["window_x"], self.settings["window_y"])

            if self.settings["window_maximize"]:
                self.maximize()

        self.set_icon_name("gscan2pdf")

        self._thumb_popup = self.builder.get_object("thumb_popup")

        # app.add_window(window)
        self._populate_main_window()

    def _init_actions(self):
        for name, function in [
            ("new", self.new),
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
            ("renumber", self.renumber_dialog),
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
            "tooltype", GLib.VariantType("s"), GLib.Variant("s", DRAGGER_TOOL)
        )
        self._actions["viewtype"] = Gio.SimpleAction.new_stateful(
            "viewtype", GLib.VariantType("s"), GLib.Variant("s", "tabbed")
        )
        self._actions["editmode"] = Gio.SimpleAction.new_stateful(
            "editmode", GLib.VariantType("s"), GLib.Variant("s", "text")
        )

    def _window_state_event_callback(self, _w, event):
        "Note when the window is maximised or not"
        self.settings["window_maximize"] = bool(
            event.new_window_state & Gdk.WindowState.MAXIMIZED
        )

    def _pre_flight(self):
        """Initialise variables, read configuration, logs system information,
        and initialise various components"""

        self._read_config()
        if self.settings["cwd"] is None:
            self.settings["cwd"] = os.getcwd()
        self.settings["version"] = VERSION

        logger.info("Operating system: %s", sys.platform)
        if sys.platform == "linux":
            recursive_slurp(glob.glob("/etc/*-release"))

        logger.info("Python version %s", sys.version_info)
        logger.info("GLib VERSION_MIN_REQUIRED %s", GLib.VERSION_MIN_REQUIRED)
        logger.info(
            "GLib._version %s", GLib._version  # pylint: disable=protected-access
        )
        logger.info("gi.__version__ %s", gi.__version__)
        logger.info("gi.version_info %s", gi.version_info)
        logger.info("Gtk._version %s", Gtk._version)  # pylint: disable=protected-access
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

        # initialise image control tool radio button setting
        self._change_image_tool_cb(
            self._actions["tooltype"],
            GLib.Variant("s", self.settings["image_control_tool"]),
        )

        self.builder.get_object(
            "context_" + self.settings["image_control_tool"]
        ).set_active(True)
        self.get_application().set_menubar(self.builder.get_object("menubar"))

    def _read_config(self):
        "Read the configuration file"
        # config files: XDG_CONFIG_HOME/gscan2pdfrc or HOME/.config/gscan2pdfrc
        rcdir = (
            os.environ["XDG_CONFIG_HOME"]
            if "XDG_CONFIG_HOME" in os.environ
            else f"{os.environ['HOME']}/.config"
        )
        self._configfile = f"{rcdir}/{PROG_NAME}rc"
        old_configfile = f"{rcdir}/gscan2pdfrc"
        if not os.path.exists(self._configfile) and os.path.exists(old_configfile):
            shutil.copy(old_configfile, self._configfile)
        self.settings = config.read_config(self._configfile)
        config.add_defaults(self.settings)
        config.remove_invalid_paper(self.settings["Paper"])

    def _populate_main_window(self):
        "Populates the main window with various UI components and sets up necessary callbacks"

        # The temp directory has to be available before we start checking for
        # dependencies in order to be used for the pdftk check.
        self._create_temp_directory()

        # Set up an SimpleList for the thumbnail view
        self.slist = Document(dir=self.session.name)

        # Update list in Document so that it can be used by get_resolution()
        self.slist.set_paper_sizes(self.settings["Paper"])

        main_vbox = self.builder.get_object("main_vbox")
        self.add(main_vbox)

        self._populate_panes()

        # Create the toolbar
        self._create_toolbar()

        self._add_text_view_layers()

        # Set up call back for list selection to update detail view
        self.slist.selection_changed_signal = self.slist.get_selection().connect(
            "changed", self._page_selection_changed_callback
        )

        # Without these, the imageviewer and page list steal -/+/ctrl x/c/v keys
        # from the OCR textview
        self.connect("key-press-event", Gtk.Window.propagate_key_event)
        self.connect("key-release-event", Gtk.Window.propagate_key_event)

        # _after ensures that Editables get first bite
        self.connect_after("key-press-event", self._on_key_press)

        # If defined in the config file, set the current directory
        if "cwd" not in self.settings:
            self.settings["cwd"] = os.getcwd()
        self._unpaper = Unpaper(self.settings["unpaper options"])
        self._update_uimanager()
        self.show_all()

        # Progress bars below window
        phbox = self.builder.get_object("progress_hbox")
        phbox.show()
        self._scan_progress = Progress()
        phbox.pack_start(self._scan_progress, True, True, 0)
        self.post_process_progress = Progress()
        phbox.pack_start(self.post_process_progress, True, True, 0)

        # OCR text editing interface
        self._ocr_text_hbox.hide()
        self._ann_hbox.hide()

        # Open scan dialog in background
        if self.settings["auto-open-scan-dialog"]:
            self.scan_dialog(None, None, True)

        # Deal with --import command line option
        args = self.get_application().args
        if args.import_files is not None:
            self._import_files(args.import_files)
        if args.import_all is not None:
            self._import_files(args.import_all, True)

    def _changed_text_sort_method(self, _widget, data):
        ocr_index, ocr_text_scmbx = data
        if ocr_index[ocr_text_scmbx.get_active()][0] == "confidence":
            self.t_canvas.sort_by_confidence()
        else:
            self.t_canvas.sort_by_position()

    def _populate_panes(self):

        # HPaned for thumbnails and detail view
        self._hpaned.set_position(self.settings["thumb panel"])

        # Scrolled window for thumbnails
        scwin_thumbs = self.builder.get_object("scwin_thumbs")

        # resize = FALSE to stop the panel expanding on being resized
        # (Debian #507032)
        # controls in pack1/2 don't seem to be available via UI XML in Gtk4
        self._hpaned.remove(scwin_thumbs)
        self._hpaned.pack1(scwin_thumbs, False)

        # If dragged below the bottom of the window, scroll it.
        self.slist.connect("drag-motion", drag_motion_callback)

        # Set up callback for right mouse clicks.
        self.slist.connect("button-press-event", self._handle_clicks)
        self.slist.connect("button-release-event", self._handle_clicks)
        scwin_thumbs.add(self.slist)

        # Notebook, split panes for detail view and OCR output
        # controls in pack1/2 don't seem to be available via UI XML in Gtk4
        self._vpaned.remove(self._vnotebook)
        self._vpaned.pack1(self._vnotebook, True)
        edit_hbox = self.builder.get_object("edit_hbox")
        self._vpaned.remove(edit_hbox)
        self._vpaned.pack2(edit_hbox, False)
        self._hpanei.show()
        self._vpanei.show()

        # ImageView for detail view
        self.view = ImageView()
        if self.settings["image_control_tool"] == SELECTOR_TOOL:
            self.view.set_tool(Selector(self.view))

        elif self.settings["image_control_tool"] == DRAGGER_TOOL:
            self.view.set_tool(Dragger(self.view))

        else:
            self.view.set_tool(SelectorDragger(self.view))

        self.view.connect("button-press-event", self._handle_clicks)
        self.view.connect("button-release-event", self._handle_clicks)
        self.view.zoom_changed_signal = self.view.connect(
            "zoom-changed", self._view_zoom_changed_callback
        )
        self.view.offset_changed_signal = self.view.connect(
            "offset-changed", self._view_offset_changed_callback
        )
        self.view.selection_changed_signal = self.view.connect(
            "selection-changed", self._view_selection_changed_callback
        )

        # GooCanvas for text layer
        self.t_canvas = Canvas()
        self.t_canvas.zoom_changed_signal = self.t_canvas.connect(
            "zoom-changed", self._text_zoom_changed_callback
        )
        self.t_canvas.offset_changed_signal = self.t_canvas.connect(
            "offset-changed", self._text_offset_changed_callback
        )

        # GooCanvas for annotation layer
        self.a_canvas = Canvas()
        self.a_canvas.zoom_changed_signal = self.a_canvas.connect(
            "zoom-changed", self._ann_zoom_changed_callback
        )
        self.a_canvas.offset_changed_signal = self.a_canvas.connect(
            "offset-changed", self._ann_offset_changed_callback
        )

    def _create_toolbar(self):

        # Check for presence of various packages
        self._check_dependencies()

        # Ghost save image item if imagemagick not available
        msg = EMPTY
        if not self._dependencies["imagemagick"]:
            msg += _("Save image and Save as PDF both require imagemagick") + "\n"

        # Ghost save image item if libtiff not available
        if not self._dependencies["libtiff"]:
            msg += _("Save image requires libtiff") + "\n"

        # Ghost djvu item if cjb2 not available
        if not self._dependencies["djvu"]:
            msg += _("Save as DjVu requires djvulibre-bin") + "\n"

        # Ghost email item if xdg-email not available
        if not self._dependencies["xdg"]:
            msg += _("Email as PDF requires xdg-email") + "\n"

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

        if not self._dependencies["unpaper"]:
            msg += _("unpaper missing") + "\n"

        self._dependencies["ocr"] = self._dependencies["tesseract"]
        if not self._dependencies["ocr"]:
            msg += _("OCR requires tesseract") + "\n"

        if self._dependencies["tesseract"]:
            lc_messages = locale.setlocale(locale.LC_MESSAGES)
            lang_msg = locale_installed(lc_messages, get_tesseract_codes())
            if lang_msg == "":
                logger.info(
                    "Using GUI language %s, for which a tesseract language package is present",
                    lc_messages,
                )
            else:
                logger.warning(lang_msg)
                msg += lang_msg

        if not self._dependencies["pdftk"]:
            msg += _("PDF encryption requires pdftk") + "\n"

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

        # extract the toolbar
        toolbar = self.builder.get_object("toolbar")

        # turn off labels
        settings = toolbar.get_settings()
        settings.gtk_toolbar_style = "icons"  # only icons

    def _pack_viewer_tools(self):
        if self.settings["viewer_tools"] == "tabbed":
            self._vnotebook.append_page(self.view, Gtk.Label(label=_("Image")))
            self._vnotebook.append_page(self.t_canvas, Gtk.Label(label=_("Text layer")))
            self._vnotebook.append_page(
                self.a_canvas, Gtk.Label(label=_("Annotations"))
            )
            self._vpaned.pack1(self._vnotebook, True, True)
            self._vnotebook.show_all()
        elif self.settings["viewer_tools"] == "horizontal":
            self._hpanei.pack1(self.view, True, True)
            self._hpanei.pack2(self.t_canvas, True, True)
            if self.a_canvas.get_parent():
                self._vnotebook.remove(self.a_canvas)
            self._vpaned.pack1(self._hpanei, True, True)
        else:  # vertical
            self._vpanei.pack1(self.view, True, True)
            self._vpanei.pack2(self.t_canvas, True, True)
            if self.a_canvas.get_parent():
                self._vnotebook.remove(self.a_canvas)
            self._vpaned.pack1(self._vpanei, True, True)

    def _handle_clicks(self, widget, event):
        if event.button == 3:  # RIGHT_MOUSE_BUTTON
            if isinstance(widget, ImageView):  # main image
                self.detail_popup.show_all()
                self.detail_popup.popup_at_pointer(event)
            else:  # Thumbnail SimpleList
                self.settings["Page range"] = "selected"
                self._thumb_popup.show_all()
                self._thumb_popup.popup_at_pointer(event)

            # block event propagation
            return True

        # allow event propagation
        return False

    def _view_zoom_changed_callback(self, _view, zoom):
        if self.t_canvas is not None:
            self.t_canvas.handler_block(self.t_canvas.zoom_changed_signal)
            self.t_canvas.set_scale(zoom)
            self.t_canvas.handler_unblock(self.t_canvas.zoom_changed_signal)

    def _view_offset_changed_callback(self, _view, x, y):
        if self.t_canvas is not None:
            self.t_canvas.handler_block(self.t_canvas.offset_changed_signal)
            self.t_canvas.set_offset(x, y)
            self.t_canvas.handler_unblock(self.t_canvas.offset_changed_signal)

    def _view_selection_changed_callback(self, _view, sel):
        # copy required here because somehow the garbage collection
        # destroys the Gdk.Rectangle too early and afterwards, the
        # contents are corrupt.
        self.settings["selection"] = sel.copy()
        if sel is not None and self._windowc is not None:
            self._windowc.selection = self.settings["selection"]

    def _on_key_press(self, _widget, event):

        # Let the keypress propagate
        if event.keyval != Gdk.KEY_Delete:
            return Gdk.EVENT_PROPAGATE
        self.delete_selection(None, None)
        return Gdk.EVENT_STOP

    def _change_image_tool_cb(self, action, value):

        # Prevent triggering the handler if it was triggered programmatically
        if self._prevent_image_tool_update:
            return

        # ignore value if it hasn't changed
        if action.get_state() == value:
            return

        # Set the flag to prevent recursive updates
        self._prevent_image_tool_update = True
        action.set_state(value)
        value = value.get_string()
        button = self.builder.get_object(f"context_{value}")
        button.set_active(True)
        self._prevent_image_tool_update = False

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
            ):
                self.view.handler_block(self.view.selection_changed_signal)
                self.view.set_selection(self.settings["selection"])
                self.view.handler_unblock(self.view.selection_changed_signal)

        self.settings["image_control_tool"] = value

    def _change_view_cb(self, action, parameter):
        "Callback to switch between tabbed and split views"
        action.set_state(parameter)

        # self.settings["viewer_tools"] still has old value
        if self.settings["viewer_tools"] == "tabbed":
            self._vpaned.remove(self._vnotebook)
            self._vnotebook.remove(self.view)
            self._vnotebook.remove(self.t_canvas)
        elif self.settings["viewer_tools"] == "horizontal":
            self._vpaned.remove(self._hpanei)
            self._hpanei.remove(self.view)
            self._hpanei.remove(self.t_canvas)
        else:  # vertical
            self._vpaned.remove(self._vpanei)
            self._vpanei.remove(self.view)
            self._vpanei.remove(self.t_canvas)
            self._vpanei.remove(self.a_canvas)

        self.settings["viewer_tools"] = parameter.get_string()
        self._pack_viewer_tools()

    def _page_selection_changed_callback(self, _selection):
        selection = self.slist.get_selected_indices()

        # Display the new image
        # When editing the page number, there is a race condition where the page
        # can be undefined
        if selection:
            i = selection.pop(0)
            path = Gtk.TreePath.new_from_indices([i])
            self.slist.scroll_to_cell(path, self.slist.get_column(0), True, HALF, HALF)
            sel = self.view.get_selection()
            try:
                self._display_image(self.slist.data[i][2])
            except ValueError:
                pass  # if a page is deleted this is still fired, so ignore it
            if sel is not None:
                self.view.set_selection(sel)
        else:
            self.view.set_pixbuf(None)
            self.t_canvas.clear_text()
            self.a_canvas.clear_text()
            self._current_page = None

        self._update_uimanager()

        # Because changing the selection hits the database in the thread, we also
        # have to ensure that any progress bars are hidden afterwards if neceesary.
        self.post_process_progress.finish(None)

    def _update_uimanager(self):
        action_names = [
            "cut",
            "copy",
            "delete",
            "renumber",
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
        if not self._dependencies["unpaper"]:
            self._actions["unpaper"].set_enabled(False)
            del self._actions["unpaper"]

        # Ghost ocr item if ocr  not available
        if not self._dependencies["ocr"]:
            self._actions["ocr"].set_enabled(False)

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

        self._actions["paste"].set_enabled(bool(self.slist.clipboard))

        # Un/ghost Undo/redo
        self._actions["undo"].set_enabled(self.slist.thread.can_undo())
        self._actions["redo"].set_enabled(self.slist.thread.can_redo())

        # Check free space in session directory
        df = shutil.disk_usage(self.session.name)
        if df:
            df = df.free / 1024 / 1024
            logger.debug(
                "Free space in %s (Mb): %s (warning at %s)",
                self.session.name,
                df,
                self.settings["available-tmp-warning"],
            )
            if df < self.settings["available-tmp-warning"]:
                text = _("%dMb free in %s.") % (df, self.session.name)
                self._show_message_dialog(
                    parent=self,
                    message_type="warning",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=text,
                )

        # If the scan dialog has already been drawn, update the start page spinbutton
        if self._windows:
            self._windows.update_start_page()

    def _show_message_dialog(self, **kwargs):
        "Displays a message dialog with the given options."
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
            self._message_dialog.show_all()
            response = self._message_dialog.run()

        if self._message_dialog is not None:  # could be undefined for multiple calls
            self._message_dialog.store_responses(response, self.settings["message"])
            (
                self.settings["message_window_width"],
                self.settings["message_window_height"],
            ) = self._message_dialog.get_size()
            self._message_dialog.destroy()
            self._message_dialog = None

    def _process_error_callback(self, widget, process, msg, signal):
        "Callback function to handle process errors."
        logger.info("signal 'process-error' emitted with data: %s %s", process, msg)
        if signal is not None:
            self._scan_progress.disconnect(signal)

        self._scan_progress.hide()
        if process == "open_device" and re.search(
            r"(Invalid[ ]argument|Device[ ]busy)", msg
        ):
            error_name = "error opening device"
            response = None
            if (
                error_name in self.settings["message"]
                and self.settings["message"][error_name]["response"] == "ignore"
            ):
                response = self.settings["message"][error_name]["response"]
            else:
                dialog = Gtk.MessageDialog(
                    parent=self,
                    destroy_with_parent=True,
                    modal=True,
                    message_type="question",
                    buttons=Gtk.ButtonsType.OK,
                )
                dialog.set_title(_("Error opening the last device used."))
                area = dialog.get_message_area()
                label = Gtk.Label(
                    label=_("There was an error opening the last device used.")
                )
                area.add(label)
                radio1 = Gtk.RadioButton.new_with_label(
                    None, label=_("Whoops! I forgot to turn it on. Try again now.")
                )
                area.add(radio1)
                area.add(
                    Gtk.RadioButton.new_with_label_from_widget(
                        radio1, label=_("Rescan for devices")
                    )
                )
                radio3 = Gtk.RadioButton.new_with_label_from_widget(
                    radio1, label=_("Restart gscan2pdf.")
                )
                area.add(radio3)
                radio4 = Gtk.RadioButton.new_with_label_from_widget(
                    radio1,
                    label=_("Just ignore the error. I don't need the scanner yet."),
                )
                area.add(radio4)
                cb_cache_device_list = Gtk.CheckButton.new_with_label(
                    _("Cache device list")
                )
                cb_cache_device_list.set_active(self.settings["cache-device-list"])
                area.add(cb_cache_device_list)
                cb = Gtk.CheckButton.new_with_label(
                    label=_("Don't show this message again")
                )
                area.add(cb)
                dialog.show_all()
                response = dialog.run()
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
                    self.settings["message"][error_name]["response"] = response

            self._windows = None  # force scan dialog to be rebuilt
            if response == "reopen":
                self.scan_dialog(None, None)
            elif response == "rescan":
                self.scan_dialog(None, None, False, True)
            elif response == "restart":
                self._restart()

            # for ignore, we do nothing
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

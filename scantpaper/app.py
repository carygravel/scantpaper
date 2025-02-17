"main application"

# TODO:
# rotate icons wrong way round
# save_pdf landscape squashes into portrait
# fix TypeErrors when dragging edges of selection
# fix panning text layer
# fix editing text layer
# deleting last page produces TypeError
# lint
# fix progress bar, including during scan
# restore last used scan settings
# use pathlib for all paths
# refactor methods using slist.clipboard
# persist data with sqlite
# fix deprecation warnings from Gtk.IconSet and Gtk.IconFactory
# migrate to Gtk4
# remaining FIXMEs and TODOs

# gscan2pdf --- to aid the scan to PDF or DjVu process

# Release procedure:
#    Use
#      make tidy
#      TEST_AUTHOR=1 make test
#    immediately before release so as not to affect any patches
#    in between, and then consistently before each commit afterwards.
# 0. Test scan in lineart, greyscale and colour.
# 1. New screendump required? Print screen creates screenshot.png in Desktop.
#    Download new translations (https://translations.launchpad.net/gscan2pdf)
#    Update translators in credits (https://launchpad.net/gscan2pdf/+topcontributors)
#    Check $VERSION. If necessary bump with something like
#     xargs sed -i "s/\(\$VERSION *= \)'2\.13\.1'/\1'2.13.2'/" < MANIFEST
#    Make appropriate updates to ../debian/changelog
# 2.  perl Makefile.PL
#     Upload .pot
# 3.  make remote-html
# 4. Build .deb for sf
#     make signed_tardist
#     sudo sbuild-update -udr sid-amd64-sbuild
#     sbuild -sc sid-amd64-sbuild
#     #debsign .changes
#    lintian -iI --pedantic .changes
#    autopkgtest .changes -- schroot sid-amd64-sbuild
#    check contents with dpkg-deb --contents
#    test dist sudo dpkg -i gscan2pdf_x.x.x_all.deb
# 5.  git status
#     git tag vx.x.x
#     git push --tags origin master
#    If the latter doesn't work, try:
#     git push --tags https://ra28145@git.code.sf.net/p/gscan2pdf/code master
# 6. create version directory in https://sourceforge.net/projects/gscan2pdf/files/gscan2pdf
#     make file_releases
# 7. Build packages for Debian & Ubuntu
#    name the release -0~ppa1<release>, where release (https://wiki.ubuntu.com/Releases) is:
#      * kinetic (until 2023-07)
#      * jammy (until 2027-04)
#      * focal (until 2025-04, dh12)
#     debuild -S -sa
#     dput ftp-master .changes
#     dput gscan2pdf-ppa .changes
#    https://launchpad.net/~jeffreyratcliffe/+archive
# 8. gscan2pdf-announce@lists.sourceforge.net, gscan2pdf-help@lists.sourceforge.net,
#    sane-devel@lists.alioth.debian.org
# 9. To interactively debug in the schroot:
#      * duplicate the config file, typically in /etc/schroot/chroot.d/, changing
#        the sbuild profile to desktop
#       schroot -c sid-amd64-desktop -u root
#       apt-get build-dep gscan2pdf
#       su - <user>
#       xvfb-run prove -lv <tests>

import argparse
import os
import pathlib
import locale
import re
import glob
import logging
import fcntl
import gettext
import datetime
import shutil
import sys
import tempfile
from types import SimpleNamespace
import warnings
import gi
import tesserocr
from dialog import Dialog, MultipleMessage, filter_message, response_stored
from dialog.renumber import Renumber
from dialog.save import Save as SaveDialog
from dialog.sane import SaneScanDialog
from dialog.crop import Crop
from comboboxtext import ComboBoxText
from document import Document
from basedocument import slurp
from scanner.profile import Profile
from unpaper import Unpaper
from canvas import Canvas
from bboxtree import Bboxtree
from imageview import ImageView, Selector, Dragger, SelectorDragger
from simplelist import SimpleList
from print_operation import PrintOperation
import config
from i18n import _, d_sane
from helpers import (
    get_tmp_dir,
    program_version,
    exec_command,
    parse_truetype_fonts,
    expand_metadata_pattern,
    collate_metadata,
)
from tesseract import languages, locale_installed, get_tesseract_codes
import sane  # To get SANE_* enums

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gtk,
    Gdk,
    GdkPixbuf,
    GLib,
    Gio,
)

HALF = 0.5
UNIT_SLIDER_STEP = 0.001
SIGMA_STEP = 0.1
MAX_SIGMA = 5
_90_DEGREES = 90
_180_DEGREES = 180
_270_DEGREES = 270
DRAGGER_TOOL = 10
SELECTOR_TOOL = 20
SELECTORDRAGGER_TOOL = 30
TABBED_VIEW = 100
SPLIT_VIEW_H = 101
SPLIT_VIEW_V = 102
EDIT_TEXT = 200
EDIT_ANNOTATION = 201
EMPTY_LIST = -1
_100_PERCENT = 100
MAX_DPI = 2400
BITS_PER_BYTE = 8
HELP_WINDOW_WIDTH = 800
HELP_WINDOW_HEIGHT = 600
HELP_WINDOW_DIVIDER_POS = 200
_1KB = 1024
_1MB = _1KB * _1KB
_100_000MB = 100_000
ZOOM_CONTEXT_FACTOR = 0.5

GLib.set_application_name("gscan2pdf")
GLib.set_prgname("net.sourceforge.gscan2pdf")
prog_name = GLib.get_application_name()
VERSION = "3.0.0"

# Image border to ensure that a scaled to fit image gets no scrollbars
border = 1

debug = False
EMPTY = ""
SPACE = " "
DOT = "."
PERCENT = "%"
ASTERISK = "*"
args = None
logger = logging.getLogger(__name__)

# Define application-wide variables here so that they can be referenced
# in the menu callbacks
slist = None
windowi = None
windowe = None
windows = None
windowo = None
windowu = None
windowudt = None
save_button = None
thbox = None
tpbar = None
tcbutton = None
scbutton = None
unpaper = None
dependencies = {}
menubar = None
toolbar = None
ocr_engine = []
windowr = None
view = None
windowp = None
message_dialog = None
windowc = None
# GooCanvas for text layer
canvas = None
ocr_text_hbox = None
ocr_textbuffer = None
ocr_textview = None
# GooCanvas for annotation layer
a_canvas = None
ann_hbox = None
ann_textbuffer = None
ann_textview = None
# session dir
session = None
# filehandle for session lockfile
lockfh = None
# Temp::File object for PDF to be emailed
# Define here to make sure that it doesn't get deleted until the next email
# is created or we quit
pdf = None
# SimpleList in preferences dialog
option_visibility_list = None
# Comboboxes for user-defined tools and rotate buttons
comboboxudt = None
rotate_side_cmbx = None
rotate_side_cmbx2 = None
# Declare the XML structure
builder = None
detail_popup = None
global SETTING
SETTING = None
global signal
signal = None
actions = {}


def parse_arguments():
    "parse command line arguments"
    parser = argparse.ArgumentParser(
        prog=prog_name, description="What the program does"
    )
    parser.add_argument("--device", nargs="+")
    parser.add_argument("--import", nargs="+", dest="import_files")
    parser.add_argument("--import-all", nargs="+")
    parser.add_argument("--locale")
    parser.add_argument("--log", type=argparse.FileType("w"))
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument(
        "--debug",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "--info", action="store_const", dest="log_level", const=logging.INFO
    )
    parser.add_argument(
        "--warn", action="store_const", dest="log_level", const=logging.WARNING
    )
    parser.add_argument(
        "--error", action="store_const", dest="log_level", const=logging.ERROR
    )
    parser.add_argument(
        "--fatal", action="store_const", dest="log_level", const=logging.CRITICAL
    )
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=args.log_level)
    else:
        logging.basicConfig(level=args.log_level)

    # if help is not None:
    #     try:
    #         subprocess.run([f"perldoc {PROGRAM_NAME}"]) == 0
    #     except:
    #         raise _('Error displaying help'), "\n"
    logger.info("Starting %s %s", prog_name, VERSION)
    logger.info("Called with %s", SPACE.join([sys.executable] + sys.argv))

    # make sure argv has absolute paths in case we change directories
    # and then restart the program
    sys.argv = [os.path.abspath(path) for path in sys.argv if os.path.isfile(path)]

    logger.info("Log level %s", args.log_level)
    if args.locale is None:
        gettext.bindtextdomain(f"{prog_name}")
    else:
        if re.search(r"^\/", args.locale, re.MULTILINE | re.DOTALL | re.VERBOSE):
            gettext.bindtextdomain(f"{prog_name}", locale)
        else:
            gettext.bindtextdomain(f"{prog_name}", os.getcwd() + f"/{locale}")
    gettext.textdomain(prog_name)

    logger.info("Using %s locale", locale.setlocale(locale.LC_CTYPE))
    logger.info("Startup LC_NUMERIC %s", locale.setlocale(locale.LC_NUMERIC))
    return args


def check_dependencies():
    "Check for presence of various packages"

    dependencies["tesseract"] = tesserocr.tesseract_version()
    dependencies["tesserocr"] = tesserocr.__version__
    if dependencies["tesseract"]:
        logger.info(
            "Found tesserocr %s, %s",
            dependencies["tesserocr"],
            dependencies["tesseract"],
        )
    dependencies["unpaper"] = Unpaper().program_version()
    if dependencies["unpaper"]:
        logger.info("Found unpaper %s", dependencies["unpaper"])

    dependency_rules = [
        [
            "imagemagick",
            "stdout",
            r"Version:\sImageMagick\s([\d.-]+)",
            ["convert", "--version"],
        ],
        ["graphicsmagick", "stdout", r"GraphicsMagick\s([\d.-]+)", ["gm", "-version"]],
        ["xdg", "stdout", r"xdg-email\s([^\n]+)", ["xdg-email", "--version"]],
        ["djvu", "stderr", r"DjVuLibre-([\d.]+)", ["cjb2", "--version"]],
        ["libtiff", "both", r"LIBTIFF,\sVersion\s([\d.]+)", ["tiffcp", "-h"]],
        # pdftops and pdfunite are both in poppler-utils, and so the version is
        # the version is the same.
        # Both are needed, though to update %dependencies
        ["pdftops", "stderr", r"pdftops\sversion\s([\d.]+)", ["pdftops", "-v"]],
        ["pdfunite", "stderr", r"pdfunite\sversion\s([\d.]+)", ["pdfunite", "-v"]],
        ["pdf2ps", "stdout", r"([\d.]+)", ["gs", "--version"]],
        ["pdftk", "stdout", r"([\d.]+)", ["pdftk", "--version"]],
        ["xz", "stdout", r"([\d.]+)", ["xz", "--version"]],
    ]

    for name, stream, regex, cmd in dependency_rules:
        dependencies[name] = program_version(stream, regex, cmd)
        if dependencies[name] and dependencies[name] == "-1":
            del dependencies[name]

        if not dependencies["imagemagick"] and dependencies["graphicsmagick"]:
            msg = (
                _("GraphicsMagick is being used in ImageMagick compatibility mode.")
                + SPACE
                + _("Whilst this might work, it is not currently supported.")
                + SPACE
                + _("Please switch to ImageMagick in case of problems.")
            )
            show_message_dialog(
                parent=app.window,
                message_type="warning",
                buttons=Gtk.ButtonsType.OK,
                text=msg,
                store_response=True,
            )
            dependencies["imagemagick"] = dependencies["graphicsmagick"]

        if dependencies[name]:
            logger.info("Found %s %s", name, dependencies[name])
            if name == "pdftk":

                # Don't create PDF  directly with imagemagick, as
                # some distros configure imagemagick not to write PDFs
                with tempfile.NamedTemporaryFile(
                    dir=session.name, suffix=".jpg"
                ) as tempimg:
                    exec_command(["convert", "rose:", tempimg.name])
                with tempfile.NamedTemporaryFile(
                    dir=session.name, suffix=".pdf"
                ) as temppdf:
                    # pdfobj = PDF.Builder( -file = temppdf )
                    # page   = pdfobj.page()
                    # size   = Gscan2pdf.Document.POINTS_PER_INCH
                    # page.mediabox( size, size )
                    # gfx    = page.gfx()
                    # imgobj = pdfobj.image_jpeg(tempimg)
                    # gfx.image( imgobj, 0, 0, size, size )
                    # pdfobj.save()
                    # pdfobj.end()
                    proc = exec_command([name, temppdf.name, "dump_data"])
                msg = None
                if re.search(
                    r"Error:[ ]could[ ]not[ ]load[ ]a[ ]required[ ]library",
                    proc.stdout,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    msg = _(
                        "pdftk is installed, but seems to be missing required dependencies:\n%s"
                    ) % (proc.stdout)

                # elif not re.search(r"NumberOfPages",proc.stdout,
                #                    re.MULTILINE|re.DOTALL|re.VERBOSE):
                #     logger.debug(f"before msg {_}")
                #     msg = _(
                # 'pdftk is installed, but cannot access the directory used for temporary files.'
                #                       )                       + _(
                # 'One reason for this might be that pdftk was installed via snap.'
                #                       )                       + _(
                # 'In this case, removing pdftk, and reinstalling without using '
                #   'snap would allow gscan2pdf to use pdftk.'
                #                       )                       + _(
                # 'Another workaround would be to select a temporary directory under '
                #  'your home directory in Edit/Preferences.'
                #                       )

                if msg:
                    del dependencies[name]
                    show_message_dialog(
                        parent=app.window,
                        message_type="warning",
                        buttons=Gtk.ButtonsType.OK,
                        text=msg,
                        store_response=True,
                    )

    # OCR engine options
    if dependencies["tesseract"]:
        ocr_engine.append(
            ["tesseract", _("Tesseract"), _("Process image with Tesseract.")]
        )

    # Build a look-up table of all true-type fonts installed
    proc = exec_command(["fc-list", ":", "family", "style", "file"])
    app._fonts = parse_truetype_fonts(proc.stdout)


def update_uimanager():
    "ghost or unghost as necessary as # pages > 0 or not"
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
    enabled = bool(slist.get_selected_indices())
    for action_name in action_names:
        if action_name in actions:
            actions[action_name].set_enabled(enabled)
    detail_popup.set_sensitive(enabled)

    # Ghost unpaper item if unpaper not available
    if not dependencies["unpaper"]:
        actions["unpaper"].set_enabled(False)
        del actions["unpaper"]

    # Ghost ocr item if ocr  not available
    if not dependencies["ocr"]:
        actions["ocr"].set_enabled(False)

    if len(slist.data) > 0:
        if dependencies["xdg"]:
            actions["email"].set_enabled(True)

        actions["print"].set_enabled(True)
        actions["save"].set_enabled(True)
        if save_button is not None:
            save_button.set_sensitive(True)

    else:
        if dependencies["xdg"]:
            actions["email"].set_enabled(False)
            if windowe is not None:
                windowe.hide()

        actions["print"].set_enabled(False)
        actions["save"].set_enabled(False)
        if save_button is not None:
            save_button.set_sensitive(False)

    actions["paste"].set_enabled(bool(slist.clipboard))

    # If the scan dialog has already been drawn, update the start page spinbutton
    if windows:
        windows._update_start_page()


def selection_changed_callback(_selection):
    "Handle selection change"
    selection = slist.get_selected_indices()

    # Display the new image
    # When editing the page number, there is a race condition where the page
    # can be undefined
    if selection:
        i = selection.pop(0)
        path = Gtk.TreePath.new_from_indices([i])
        slist.scroll_to_cell(path, slist.get_column(0), True, HALF, HALF)
        sel = view.get_selection()
        display_image(slist.data[i][2])
        if sel is not None:
            view.set_selection(sel)
    else:
        view.set_pixbuf(None)
        canvas.clear_text()
        a_canvas.clear_text()
        app.window._current_page = None

    update_uimanager()


def drag_motion_callback(tree, context, x, y, t):
    "Handle drag motion"
    try:
        path, how = tree.get_dest_row_at_pos(x, y)
    except:
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


def create_temp_directory():
    "Create a temporary directory for the session"
    global session
    app.tmpdir = get_tmp_dir(SETTING["TMPDIR"], r"gscan2pdf-\w\w\w\w")
    find_crashed_sessions(app.tmpdir)

    # Create temporary directory if necessary
    if session is None:
        if app.tmpdir is not None and app.tmpdir != EMPTY:
            if not os.path.isdir(app.tmpdir):
                os.mkdir(app.tmpdir)
            try:
                session = tempfile.TemporaryDirectory(
                    prefix="gscan2pdf-", dir=app.tmpdir
                )
            except:
                session = tempfile.TemporaryDirectory(prefix="gscan2pdf-")
        else:
            session = (
                tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
                    prefix="gscan2pdf-"
                )
            )

        slist.set_dir(session.name)
        create_lockfile()
        slist.save_session()
        logger.info("Using %s for temporary files", session.name)
        app.tmpdir = os.path.dirname(session.name)
        if "TMPDIR" in SETTING and SETTING["TMPDIR"] != app.tmpdir:
            logger.warning(
                _(
                    "Warning: unable to use %s for temporary storage. Defaulting to %s instead."
                ),
                SETTING["TMPDIR"],
                app.tmpdir,
            )
            SETTING["TMPDIR"] = app.tmpdir


def create_lockfile():
    "create a lockfile in the session directory"
    with open(os.path.join(session.name, "lockfile"), "w", encoding="utf-8") as lockfh:
        fcntl.lockf(lockfh, fcntl.LOCK_EX)


def find_crashed_sessions(tmpdir):
    "Look for crashed sessions"
    if tmpdir is None or tmpdir == EMPTY:
        tmpdir = tempfile.gettempdir()

    logger.info("Checking %s for crashed sessions", tmpdir)
    sessions = glob.glob(os.path.join(tmpdir, "gscan2pdf-????"))
    crashed, selected = [], []

    # Forget those used by running sessions
    for session in sessions:
        try:
            create_lockfile()
            crashed.append(session)
        except Exception as e:
            logger.warning("Error opening lockfile %s (%s)", lockfh, str(e))

    # Flag those with no session file
    missing = []
    for i, session in enumerate(crashed):
        if not os.access(os.path.join(session, "session"), os.R_OK):
            missing.append(session)
            del crashed[i]

    if missing:
        logger.info("Unrestorable sessions: %s", SPACE.join(missing))
        dialog = Gtk.Dialog(
            title=_("Crashed sessions"),
            transient_for=app.window,
            modal=True,
        )
        dialog.add_buttons(
            Gtk.STOCK_DELETE,
            Gtk.ResponseType.OK,
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
        )
        text = Gtk.TextView()
        text.set_wrap_mode("word")
        text.get_buffer().set_text(
            _("The following list of sessions cannot be restored.")
            + SPACE
            + _("Please retrieve any images you require from them.")
            + SPACE
            + _("Selected sessions will be deleted.")
        )
        dialog.get_content_area().add(text)
        columns = {_("Session"): "text"}
        sessionlist = SimpleList(**columns)
        sessionlist.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        sessionlist.data.append(missing)
        dialog.get_content_area().add(sessionlist)
        (button) = dialog.get_action_area().get_children()

        def changed_selection_callback():
            button.set_sensitive(len(sessionlist.get_selected_indices()) > 0)

        sessionlist.get_selection().connect("changed", changed_selection_callback)
        sessionlist.get_selection().select_all()
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            selected = sessionlist.get_selected_indices()
            for i, _v in enumerate(selected):
                selected[i] = missing[i]
            logger.info("Selected for deletion: %s", SPACE.join(selected))
            if selected:
                shutil.rmtree(selected)
        else:
            logger.info("None selected")

        dialog.destroy()

    # Allow user to pick a crashed session to restore
    if crashed:
        dialog = Gtk.Dialog(
            title=_("Pick crashed session to restore"),
            transient_for=app.window,
            modal=True,
        )
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        label = Gtk.Label(label=_("Pick crashed session to restore"))
        box = dialog.get_content_area()
        box.add(label)
        columns = {_("Session"): "text"}
        sessionlist = SimpleList(**columns)
        sessionlist.data.append(crashed)
        box.add(sessionlist)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            selected = sessionlist.get_selected_indices()

        dialog.destroy()
        if selected is not None:
            session = crashed[selected]
            create_lockfile()
            slist.set_dir(session)
            open_session(session)


def display_callback(response):
    "Find the page from the input uuid and display it"
    uuid = response.request.args[0]["page"].uuid
    i = slist.find_page_by_uuid(uuid)
    if i is None:
        logger.error("Can't display page with uuid %s: page not found", uuid)
    else:
        display_image(slist.data[i][2])


def display_image(page):
    "Display the image in the view"
    app.window._current_page = page
    view.set_pixbuf(app.window._current_page.get_pixbuf(), True)
    xresolution, yresolution, _units = app.window._current_page.resolution
    view.set_resolution_ratio(xresolution / yresolution)

    # Get image dimensions to constrain selector spinbuttons on crop dialog
    width, height = app.window._current_page.get_size()

    # Update the ranges on the crop dialog
    if windowc is not None and app.window._current_page is not None:
        windowc.page_width = width
        windowc.page_height = height
        SETTING["selection"] = windowc.selection
        view.set_selection(SETTING["selection"])

    # Delete OCR output if it has become corrupted
    if app.window._current_page.text_layer is not None:
        bbox = Bboxtree(app.window._current_page.text_layer)
        if not bbox.valid():
            logger.error(
                "deleting corrupt text layer: %s", app.window._current_page.text_layer
            )
            app.window._current_page.text_layer = None

    if app.window._current_page.text_layer:
        create_txt_canvas(app.window._current_page)
    else:
        canvas.clear_text()

    if app.window._current_page.annotations:
        create_ann_canvas(app.window._current_page)
    else:
        a_canvas.clear_text()


def create_txt_canvas(page, finished_callback=None):
    "Create the text canvas"
    offset = view.get_offset()
    canvas.set_text(
        page=page,
        layer="text_layer",
        edit_callback=app.window.edit_ocr_text,
        idle=True,
        finished_callback=finished_callback,
    )
    canvas.set_scale(view.get_zoom())
    canvas.set_offset(offset.x, offset.y)
    canvas.show()


def create_ann_canvas(page, finished_callback=None):
    "Create the annotation canvas"
    offset = view.get_offset()
    a_canvas.set_text(
        page=page,
        layer="annotations",
        edit_callback=app.window.edit_annotation,
        idle=True,
        finished_callback=finished_callback,
    )
    a_canvas.set_scale(view.get_zoom())
    a_canvas.set_offset(offset.x, offset.y)
    a_canvas.show()


def edit_tools_callback(_action, current):
    "Show/hide the edit tools"
    if current.get_current_value() == EDIT_TEXT:
        ocr_text_hbox.show()
        ann_hbox.hide()
        return

    ocr_text_hbox.hide()
    ann_hbox.show()


def scans_saved(message):
    "Check that all pages have been saved"
    if not slist.scans_saved():
        response = ask_question(
            parent=app.window,
            type="question",
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=message,
            store_response=True,
            stored_responses=[Gtk.ResponseType.OK],
        )
        if response != Gtk.ResponseType.OK:
            return False

    return True


def new(_action, _param):
    "Deletes all scans after warning"
    if not scans_saved(
        _("Some pages have not been saved.\nDo you really want to clear all pages?")
    ):
        return

    # Update undo/redo buffers
    take_snapshot()

    # in certain circumstances, before v2.5.5, having deleted one of several
    # pages, pressing the new button would cause some sort of race condition
    # between the tied array of the slist and the callbacks displaying the
    # thumbnails, so block this whilst clearing the array.
    slist.get_model().handler_block(slist.row_changed_signal)
    slist.get_selection().handler_block(slist.selection_changed_signal)

    # Depopulate the thumbnail list
    slist.data = []

    # Unblock slist signals now finished
    slist.get_selection().handler_unblock(slist.selection_changed_signal)
    slist.get_model().handler_unblock(slist.row_changed_signal)

    # Now we have to clear everything manually
    slist.get_selection().unselect_all()
    view.set_pixbuf(None)
    canvas.clear_text()
    a_canvas.clear_text()
    app.window._current_page = None

    # Reset start page in scan dialog
    windows._reset_start_page()


def add_filter(file_chooser, name, file_extensions):
    "Create a file filter to show only supported file types in FileChooser dialog"
    ffilter = Gtk.FileFilter()
    for extension in file_extensions:
        pattern = []

        # Create case insensitive pattern
        for char in extension:
            pattern.append("[" + char.upper() + char.lower() + "]")

        ffilter.add_pattern("*." + EMPTY.join(pattern))

    types = None
    for ext in file_extensions:
        if types is not None:
            types += f", *.{ext}"

        else:
            types = f"*.{ext}"

    ffilter.set_name(f"{name} ({types})")
    file_chooser.add_filter(ffilter)
    ffilter = Gtk.FileFilter()
    ffilter.add_pattern("*")
    ffilter.set_name("All files")
    file_chooser.add_filter(ffilter)


def error_callback(response):
    "Handle errors"
    args = response.request.args
    process = response.request.process
    stage = response.type.name.lower()
    message = response.status
    page = None
    if "page" in args[0]:
        page = slist.data[slist.find_page_by_uuid(args[0]["page"].uuid)][0]

    options = {
        "parent": app.window,
        "message_type": "error",
        "buttons": Gtk.ButtonsType.CLOSE,
        "process": process,
        "text": message,
        "store-response": True,
        "page": page,
    }

    logger.error(
        "Error running '%s' callback for '%s' process: %s", stage, process, message
    )

    def show_message_dialog_wrapper():
        """Wrap show_message_dialog() in GLib.idle_add() to allow the thread to
        return immediately in order to allow it to work on subsequent pages
        despite errors on previous ones"""
        show_message_dialog(**options)

    GLib.idle_add(show_message_dialog_wrapper)
    thbox.hide()


def open_session_file(filename):
    "open session"
    logger.info("Restoring session in %s", session)
    slist.open_session_file(info=filename, error_callback=error_callback)


def open_session_action(_action):
    "open session"
    file_chooser = Gtk.FileChooserDialog(
        title=_("Open crashed session"),
        parent=app.window,
        action=Gtk.FileChooserAction.SELECT_FOLDER,
    )
    file_chooser.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
    )
    file_chooser.set_default_response(Gtk.ResponseType.OK)
    file_chooser.set_current_folder(SETTING["cwd"])
    if file_chooser.run() == Gtk.ResponseType.OK:

        # Update undo/redo buffers
        take_snapshot()
        filename = file_chooser.get_filenames()
        open_session(filename[0])

    file_chooser.destroy()


def open_session(sesdir):
    "open session"
    logger.info("Restoring session in %s", session)
    slist.open_session(dir=sesdir, delete=False, error_callback=error_callback)


def setup_tpbar(response):  # , pid
    "Helper function to set up thread progress bar"
    logger.debug("setup_tpbar( %s )", response)
    pid = None
    process_name, num_completed, total = (
        response.request.process,
        response.num_completed_jobs,
        response.total_jobs,
    )
    if total and process_name is not None:
        tpbar.set_text(
            _("Process %i of %i (%s)") % (num_completed + 1, total, process_name)
        )
        tpbar.set_fraction((num_completed + HALF) / total)
        thbox.show_all()

        def cancel_process():
            """Pass the signal back to:
            1. be able to cancel it when the process has finished
            2. flag that the progress bar has been set up
               and avoid the race condition where the callback is
               entered before the num_completed and total variables have caught up"""
            slist.cancel([pid])
            thbox.hide()

        global signal
        signal = tcbutton.connect("clicked", cancel_process)


def update_tpbar(response):
    "Helper function to update thread progress bar"
    if response and response.total_jobs:
        if response.request.process:
            # if  "message"  in options :
            #     options["process"] += f" - {options['message']}"
            tpbar.set_text(
                _("Process %i of %i (%s)")
                % (
                    response.num_completed_jobs + 1,
                    response.total_jobs,
                    response.request.process,
                )
            )

        else:
            tpbar.set_text(
                _("Process %i of %i")
                % (response.num_completed_jobs + 1, response.total_jobs)
            )

        # if  "progress"  in options :
        #     tpbar.set_fraction(
        #     ( options["jobs_completed"] + options["progress"] ) / options["jobs_total"] )
        # else :
        tpbar.set_fraction((response.num_completed_jobs + HALF) / response.total_jobs)

        thbox.show_all()


def finish_tpbar(response):
    "Helper function to update thread progress bar"
    if not response.pending:
        thbox.hide()
    if signal is not None:
        tcbutton.disconnect(signal)


def open_dialog(_action, _param):
    "Throw up file selector and open selected file"
    # cd back to cwd to get filename
    os.chdir(SETTING["cwd"])
    file_chooser = Gtk.FileChooserDialog(
        title=_("Open image"),
        parent=app.window,
        action=Gtk.FileChooserAction.OPEN,
    )
    file_chooser.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
    )
    file_chooser.set_select_multiple(True)
    file_chooser.set_default_response(Gtk.ResponseType.OK)
    file_chooser.set_current_folder(SETTING["cwd"])
    add_filter(
        file_chooser,
        _("Image files"),
        [
            "jpg",
            "png",
            "pnm",
            "ppm",
            "pbm",
            "gif",
            "tif",
            "tiff",
            "pdf",
            "djvu",
            "ps",
            "gs2p",
        ],
    )
    if file_chooser.run() == Gtk.ResponseType.OK:

        # cd back to tempdir to import
        os.chdir(session.name)

        # Update undo/redo buffers
        take_snapshot()
        filenames = file_chooser.get_filenames()
        file_chooser.destroy()

        # Update cwd
        SETTING["cwd"] = os.path.dirname(filenames[0])
        import_files(filenames)
    else:
        file_chooser.destroy()

    # cd back to tempdir
    os.chdir(session.name)


def import_files_password_callback(filename):
    "Ask for password for encrypted PDF"
    text = _("Enter user password for PDF %s") % (filename)
    dialog = Gtk.MessageDialog(
        app.window,
        ["destroy-with-parent", "modal"],
        "question",
        Gtk.ButtonsType.OK_CANCEL,
        text,
    )
    dialog.set_title(text)
    vbox = dialog.get_content_area()
    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char(ASTERISK)
    vbox.pack_end(entry, False, False, 0)
    dialog.show_all()
    response = dialog.run()
    text = entry.get_text()
    dialog.destroy()
    if response == Gtk.ResponseType.OK and text != EMPTY:
        return text
    return None


def import_files_finished_callback(response):
    "import_files finished callback"
    logger.debug("finished import_files(%s)", response)
    finish_tpbar(response)
    # slist.save_session()


def import_files_metadata_callback(metadata):
    "Update the metadata from the imported file"
    logger.debug("import_files_metadata_callback(%s)", metadata)
    for dialog in (windowi, windowe):
        if dialog is not None:
            dialog.update_from_import_metadata(metadata)
    config.update_config_from_imported_metadata(SETTING, metadata)


def import_files(filenames, all_pages=False):
    "Import given files"
    # FIXME: import_files() now returns an array of pids.
    options = {
        "paths": filenames,
        "password_callback": import_files_password_callback,
        "queued_callback": setup_tpbar,
        "started_callback": update_tpbar,
        "running_callback": update_tpbar,
        "finished_callback": import_files_finished_callback,
        "metadata_callback": import_files_metadata_callback,
        "error_callback": error_callback,
    }
    if all_pages:

        def all_pages_callback(info):

            return 1, info["pages"]

        options["pagerange_callback"] = all_pages_callback

    else:

        def select_pagerange_callback(info):

            dialog = Gtk.Dialog(
                title=_("Pages to extract"),
                transient_for=app.window,
                modal=True,
                destroy_with_parent=True,
            )
            dialog.add_buttons(
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
            )
            vbox = dialog.get_content_area()
            hbox = Gtk.HBox()
            vbox.pack_start(hbox, True, True, 0)
            label = Gtk.Label(label=_("First page to extract"))
            hbox.pack_start(label, False, False, 0)
            spinbuttonf = Gtk.SpinButton.new_with_range(1, info["pages"], 1)
            hbox.pack_end(spinbuttonf, False, False, 0)
            hbox = Gtk.HBox()
            vbox.pack_start(hbox, True, True, 0)
            label = Gtk.Label(label=_("Last page to extract"))
            hbox.pack_start(label, False, False, 0)
            spinbuttonl = Gtk.SpinButton.new_with_range(1, info["pages"], 1)
            spinbuttonl.set_value(info["pages"])
            hbox.pack_end(spinbuttonl, False, False, 0)
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.OK:
                return int(spinbuttonf.get_value()), int(spinbuttonl.get_value())
            return None, None

        options["pagerange_callback"] = select_pagerange_callback

    slist.import_files(**options)


def save_pdf(filename, option, list_of_page_uuids):
    "Save selected pages as PDF under given name."

    # Compile options
    options = {
        "compression": SETTING["pdf compression"],
        "downsample": SETTING["downsample"],
        "downsample dpi": SETTING["downsample dpi"],
        "quality": SETTING["quality"],
        "text_position": SETTING["text_position"],
        "font": SETTING["pdf font"],
        "user-password": windowi.pdf_user_password,
        "set_timestamp": SETTING["set_timestamp"],
        "convert whitespace to underscores": SETTING[
            "convert whitespace to underscores"
        ],
    }
    if option == "prependpdf":
        options["prepend"] = filename

    elif option == "appendpdf":
        options["append"] = filename

    elif option == "ps":
        options["ps"] = filename
        options["pstool"] = SETTING["ps_backend"]

    if SETTING["post_save_hook"]:
        options["post_save_hook"] = SETTING["current_psh"]

    # Create the PDF
    logger.debug("Started saving %s", filename)
    signal = None

    def save_pdf_finished_callback(response):
        if not response.pending:
            thbox.hide()
        if signal is not None:
            tcbutton.disconnect(signal)

        mark_pages(list_of_page_uuids)
        if "view files toggle" in SETTING and SETTING["view files toggle"]:
            if "ps" in options:
                launch_default_for_file(options["ps"])
            else:
                launch_default_for_file(filename)

        logger.debug("Finished saving %s", filename)

    slist.save_pdf(
        path=filename,
        list_of_pages=list_of_page_uuids,
        metadata=collate_metadata(SETTING, datetime.datetime.now()),
        options=options,
        queued_callback=setup_tpbar,
        started_callback=update_tpbar,
        running_callback=update_tpbar,
        finished_callback=save_pdf_finished_callback,
        error_callback=error_callback,
    )


def launch_default_for_file(filename):
    "Launch default viewer for file"
    uri = GLib.filename_to_uri(os.path.abspath(filename), None)
    logger.info("Opening %s via default launcher", uri)
    context = Gio.AppLaunchContext()
    try:
        Gio.AppInfo.launch_default_for_uri(uri, context)
    except Exception as e:
        logger.error("Unable to launch viewer: %s", e)


def save_dialog(_action, _param):
    "Display page selector and on save a fileselector."
    global windowi
    if windowi is not None:
        windowi.present()
        return

    image_types = [
        "pdf",
        "gif",
        "jpg",
        "png",
        "pnm",
        "ps",
        "tif",
        "txt",
        "hocr",
        "session",
    ]
    if dependencies["pdfunite"]:
        image_types.extend(["prependpdf", "appendpdf"])

    if dependencies["djvu"]:
        image_types.append("djvu")
    ps_backends = []
    for backend in ["libtiff", "pdf2ps", "pdftops"]:
        if dependencies[backend]:
            ps_backends.append(backend)

    windowi = SaveDialog(
        transient_for=app.window,
        title=_("Save"),
        hide_on_delete=True,
        page_range=SETTING["Page range"],
        include_time=SETTING["use_time"],
        meta_datetime=datetime.datetime.now() + SETTING["datetime offset"],
        select_datetime=bool(SETTING["datetime offset"]),
        meta_title=SETTING["title"],
        meta_title_suggestions=SETTING["title-suggestions"],
        meta_author=SETTING["author"],
        meta_author_suggestions=SETTING["author-suggestions"],
        meta_subject=SETTING["subject"],
        meta_subject_suggestions=SETTING["subject-suggestions"],
        meta_keywords=SETTING["keywords"],
        meta_keywords_suggestions=SETTING["keywords-suggestions"],
        image_types=image_types,
        image_type=SETTING["image type"],
        ps_backends=ps_backends,
        jpeg_quality=SETTING["quality"],
        downsample_dpi=SETTING["downsample dpi"],
        downsample=SETTING["downsample"],
        pdf_compression=SETTING["pdf compression"],
        available_fonts=app._fonts,
        text_position=SETTING["text_position"],
        pdf_font=SETTING["pdf font"],
        can_encrypt_pdf="pdftk" in dependencies,
        tiff_compression=SETTING["tiff compression"],
    )

    # Frame for page range
    windowi.add_page_range()
    windowi.add_image_type()

    # Post-save hook
    pshbutton = Gtk.CheckButton(label=_("Post-save hook"))
    pshbutton.set_tooltip_text(
        _(
            "Run command on saved file. The available commands are those "
            "user-defined tools that do not specify %o"
        )
    )
    vbox = windowi.get_content_area()
    vbox.pack_start(pshbutton, False, True, 0)
    update_post_save_hooks()
    vbox.pack_start(windowi.comboboxpsh, False, True, 0)
    pshbutton.connect(
        "toggled",
        lambda _action: windowi.comboboxpsh.set_sensitive(pshbutton.get_active()),
    )
    pshbutton.set_active(SETTING["post_save_hook"])
    windowi.comboboxpsh.set_sensitive(pshbutton.get_active())
    kbutton = Gtk.CheckButton(label=_("Close dialog on save"))
    kbutton.set_tooltip_text(_("Close dialog on save"))
    kbutton.set_active(SETTING["close_dialog_on_save"])
    vbox.pack_start(kbutton, False, True, 0)

    windowi.add_actions(
        [
            ("gtk-save", lambda: save_button_clicked_callback(kbutton, pshbutton)),
            ("gtk-cancel", windowi.hide),
        ]
    )
    windowi.show_all()
    windowi.resize(1, 1)
    return


def list_of_page_uuids():
    "Compile list of pages"
    pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
    if not pagelist:
        return []
    return [slist.data[i][2].uuid for i in pagelist]


def save_button_clicked_callback(kbutton, pshbutton):
    "Save selected pages"

    # Compile list of pages
    SETTING["Page range"] = windowi.page_range
    uuids = list_of_page_uuids()

    # dig out the image type, compression and quality
    SETTING["image type"] = windowi.image_type
    SETTING["close_dialog_on_save"] = kbutton.get_active()
    SETTING["post_save_hook"] = pshbutton.get_active()
    if SETTING["post_save_hook"] and windowi.comboboxpsh.get_active() > EMPTY_LIST:
        SETTING["current_psh"] = windowi.comboboxpsh.get_active_text()

    if re.search(r"pdf", SETTING["image type"]):

        # dig out the compression
        SETTING["downsample"] = windowi.downsample
        SETTING["downsample dpi"] = windowi.downsample_dpi
        SETTING["pdf compression"] = windowi.pdf_compression
        SETTING["quality"] = windowi.jpeg_quality
        SETTING["text_position"] = windowi.text_position
        SETTING["pdf font"] = windowi.pdf_font

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])
        file_chooser = None
        if SETTING["image type"] == "pdf":
            windowi.update_config_dict(SETTING)

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("PDF filename"),
                parent=windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
            )

            filename = expand_metadata_pattern(
                template=SETTING["default filename"],
                convert_whitespace=SETTING["convert whitespace to underscores"],
                author=SETTING["author"],
                title=SETTING["title"],
                docdate=windowi.meta_datetime,
                today_and_now=datetime.datetime.now(),
                extension="pdf",
                subject=SETTING["subject"],
                keywords=SETTING["keywords"],
            )
            file_chooser.set_current_name(filename)
            file_chooser.set_do_overwrite_confirmation(True)

        else:
            file_chooser = Gtk.FileChooserDialog(
                title=_("PDF filename"),
                parent=windowi,
                action=Gtk.FileChooserAction.OPEN,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN,
                Gtk.ResponseType.OK,
            )

        add_filter(file_chooser, _("PDF files"), ["pdf"])
        file_chooser.set_current_folder(SETTING["cwd"])
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.connect(
            "response", file_chooser_response_callback, [SETTING["image type"], uuids]
        )
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "djvu":
        windowi.update_config_dict(SETTING)

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("DjVu filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        filename = expand_metadata_pattern(
            template=SETTING["default filename"],
            convert_whitespace=SETTING["convert whitespace to underscores"],
            author=SETTING["author"],
            title=SETTING["title"],
            docdate=windowi.meta_datetime,
            today_and_now=datetime.datetime.now(),
            extension="djvu",
            subject=SETTING["subject"],
            keywords=SETTING["keywords"],
        )
        file_chooser.set_current_name(filename)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        add_filter(file_chooser, _("DjVu files"), ["djvu"])
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
            "response", file_chooser_response_callback, ["djvu", uuids]
        )
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "tif":
        SETTING["tiff compression"] = windowi.tiff_compression
        SETTING["quality"] = windowi.jpeg_quality

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("TIFF filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        add_filter(file_chooser, _("Image files"), [SETTING["image type"]])
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect("response", file_chooser_response_callback, ["tif", uuids])
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "txt":

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("Text filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        add_filter(file_chooser, _("Text files"), ["txt"])
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect("response", file_chooser_response_callback, ["txt", uuids])
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "hocr":

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("hOCR filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        file_chooser.set_do_overwrite_confirmation(True)
        add_filter(file_chooser, _("hOCR files"), ["hocr"])
        file_chooser.connect(
            "response", file_chooser_response_callback, ["hocr", uuids]
        )
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "ps":
        SETTING["ps_backend"] = windowi.ps_backend
        logger.info("Selected '%s' as ps backend", SETTING["ps_backend"])

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("PS filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        add_filter(file_chooser, _("Postscript files"), ["ps"])
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect("response", file_chooser_response_callback, ["ps", uuids])
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "session":

        # cd back to cwd to save
        os.chdir(SETTING["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("gscan2pdf session filename"),
            parent=windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(SETTING["cwd"])
        add_filter(file_chooser, _("gscan2pdf session files"), ["gs2p"])
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect("response", file_chooser_response_callback, ["gs2p"])
        file_chooser.show()

        # cd back to tempdir
        os.chdir(session.name)

    elif SETTING["image type"] == "jpg":
        SETTING["quality"] = windowi.jpeg_quality
        save_image(uuids)

    else:
        save_image(uuids)


def file_chooser_response_callback(dialog, response, data):
    "Callback for file chooser dialog"
    filetype, uuids = data
    suffix = filetype
    if re.search(r"pdf", suffix, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE):
        suffix = "pdf"
    if response == Gtk.ResponseType.OK:
        filename = dialog.get_filename()
        logger.debug("FileChooserDialog returned %s", filename)
        if not re.search(
            rf"[.]{suffix}$",
            filename,
            re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
        ):
            filename = f"{filename}.{filetype}"
            if file_exists(dialog, filename):
                return

        if file_writable(dialog, filename):
            return

        # Update cwd
        SETTING["cwd"] = os.path.dirname(filename)
        if re.search(r"pdf", filetype):
            save_pdf(filename, filetype, uuids)

        elif filetype == "djvu":
            save_djvu(filename, uuids)

        elif filetype == "tif":
            save_tiff(filename, None, uuids)

        elif filetype == "txt":
            save_text(filename, uuids)

        elif filetype == "hocr":
            save_hocr(filename, uuids)

        elif filetype == "ps":
            if SETTING["ps_backend"] == "libtiff":
                tif = tempfile.TemporaryFile(dir=session, suffix=".tif")
                save_tiff(tif.filename(), filename, uuids)

            else:
                save_pdf(filename, "ps", uuids)

        elif filetype == "gs2p":
            slist.save_session(filename, VERSION)

        if windowi is not None and SETTING["close_dialog_on_save"]:
            windowi.hide()

    dialog.destroy()


def file_exists(chooser, filename):
    "Check if a file exists and prompt the user for confirmation if it does."

    if os.path.isfile(filename):

        # File exists; get the file chooser to ask the user to confirm.
        chooser.set_filename(filename)

        # Give the name change a chance to take effect
        GLib.idle_add(lambda: chooser.response(Gtk.ResponseType.OK))
        return True

    return False


def file_writable(chooser, filename):
    "Check if a file or its directory is writable and show an error dialog if not."

    if not os.access(
        os.path.dirname(filename), os.W_OK
    ):  # FIXME: replace with try/except
        text = _("Directory %s is read-only") % (os.path.dirname(filename))
        show_message_dialog(
            parent=chooser,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            text=text,
        )
        return True

    elif os.path.isfile(filename) and not os.access(
        filename, os.W_OK
    ):  # FIXME: replace with try/except
        text = _("File %s is read-only") % (filename)
        show_message_dialog(
            parent=chooser,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            text=text,
        )
        return True

    return False


def save_image(uuids):
    "Save selected pages as image under given name."

    # cd back to cwd to save
    os.chdir(SETTING["cwd"])

    # Set up file selector
    file_chooser = Gtk.FileChooserDialog(
        title=_("Image filename"),
        parent=windowi,
        action=Gtk.FileChooserAction.SAVE,
    )
    file_chooser.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK
    )
    file_chooser.set_default_response(Gtk.ResponseType.OK)
    file_chooser.set_current_folder(SETTING["cwd"])
    add_filter(
        file_chooser,
        _("Image files"),
        ["jpg", "png", "pnm", "gif", "tif", "tiff", "pdf", "djvu", "ps"],
    )
    file_chooser.set_do_overwrite_confirmation(True)
    if file_chooser.run() == Gtk.ResponseType.OK:
        filename = file_chooser.get_filename()

        # Update cwd
        SETTING["cwd"] = os.path.dirname(filename)

        # cd back to tempdir
        os.chdir(session.name)
        if len(uuids) > 1:
            w = len(uuids)
            for i in range(1, len(uuids) + 1):
                current_filename = f"${filename}_%0${w}d.{SETTING['image type']}" % (i)
                if os.path.isfile(current_filename):
                    text = _("This operation would overwrite %s") % (current_filename)
                    show_message_dialog(
                        parent=file_chooser,
                        message_type="error",
                        buttons=Gtk.ButtonsType.CLOSE,
                        text=text,
                    )
                    file_chooser.destroy()
                    return

            filename = f"${filename}_%0${w}d.{SETTING['image type']}"

        else:
            if not re.search(
                rf"[.]{SETTING['image type']}$",
                filename,
                re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                filename = f"{filename}.{SETTING['image type']}"
                if file_exists(file_chooser, filename):
                    return

            if file_writable(file_chooser, filename):
                return

        # Create the image
        logger.debug("Started saving %s", filename)
        signal = None

        def save_image_finished_callback(response):
            filename = response.request.args[0]["path"]
            uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
            if not response.pending:
                thbox.hide()
            if signal is not None:
                tcbutton.disconnect(signal)

            mark_pages(uuids)
            if "view files toggle" in SETTING and SETTING["view files toggle"]:
                w = len(uuids)
                if w > 1:
                    for i in range(1, w + 1):
                        launch_default_for_file(filename % (i))
                else:
                    launch_default_for_file(filename)

            logger.debug("Finished saving %s", filename)

        slist.save_image(
            path=filename,
            list_of_pages=uuids,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=save_image_finished_callback,
            error_callback=error_callback,
        )
        if windowi is not None:
            windowi.hide()

    file_chooser.destroy()


def save_tiff(filename, ps, uuids):
    "Save a list of pages as a TIFF file with specified options"
    options = {
        "compression": SETTING["tiff compression"],
        "quality": SETTING["quality"],
        "ps": ps,
    }
    if SETTING["post_save_hook"]:
        options["post_save_hook"] = SETTING["current_psh"]

    def save_tiff_finished_callback(response):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        finish_tpbar(response)
        mark_pages(uuids)
        file = ps if ps is not None else filename
        if "view files toggle" in SETTING and SETTING["view files toggle"]:
            launch_default_for_file(file)

        logger.debug("Finished saving %s", file)

    slist.save_tiff(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=setup_tpbar,
        started_callback=update_tpbar,
        running_callback=update_tpbar,
        finished_callback=save_tiff_finished_callback,
        error_callback=error_callback,
    )


def save_djvu(filename, uuids):
    "Save a list of pages as a DjVu file."

    # cd back to tempdir
    os.chdir(session.name)

    # Create the DjVu
    logger.debug("Started saving %s", filename)
    options = {
        "set_timestamp": SETTING["set_timestamp"],
        "convert whitespace to underscores": SETTING[
            "convert whitespace to underscores"
        ],
    }
    if SETTING["post_save_hook"]:
        options["post_save_hook"] = SETTING["current_psh"]

    def save_djvu_finished_callback(response):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        finish_tpbar(response)
        mark_pages(uuids)
        if "view files toggle" in SETTING and SETTING["view files toggle"]:
            launch_default_for_file(filename)
        logger.debug("Finished saving %s", filename)

    slist.save_djvu(
        path=filename,
        list_of_pages=uuids,
        options=options,
        metadata=collate_metadata(SETTING, datetime.datetime.now()),
        queued_callback=setup_tpbar,
        started_callback=update_tpbar,
        running_callback=update_tpbar,
        finished_callback=save_djvu_finished_callback,
        error_callback=error_callback,
    )


def save_text(filename, uuids):
    "Save OCR text"
    options = {}
    if SETTING["post_save_hook"]:
        options["post_save_hook"] = SETTING["current_psh"]

    def save_text_finished_callback(response):

        finish_tpbar(response)
        mark_pages(uuids)
        if "view files toggle" in SETTING and SETTING["view files toggle"]:
            launch_default_for_file(filename)

        logger.debug("Finished saving %s", filename)

    slist.save_text(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=setup_tpbar,
        started_callback=update_tpbar,
        running_callback=update_tpbar,
        finished_callback=save_text_finished_callback,
        error_callback=error_callback,
    )


def save_hocr(filename, uuids):
    "Save HOCR (HTML OCR) data to a file"
    options = {}
    if SETTING["post_save_hook"]:
        options["post_save_hook"] = SETTING["current_psh"]

    def save_hocr_finished_callback(response):
        finish_tpbar(response)
        mark_pages(uuids)
        if "view files toggle" in SETTING and SETTING["view files toggle"]:
            launch_default_for_file(filename)

        logger.debug("Finished saving %s", filename)

    slist.save_hocr(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=setup_tpbar,
        started_callback=update_tpbar,
        running_callback=update_tpbar,
        finished_callback=save_hocr_finished_callback,
        error_callback=error_callback,
    )


def email(_action, _param):
    "Display page selector and email."
    global windowe
    if windowe is not None:
        windowe.present()
        return

    windowe = SaveDialog(
        transient_for=app.window,
        title=_("Email as PDF"),
        hide_on_delete=True,
        page_range=SETTING["Page range"],
        include_time=SETTING["use_time"],
        meta_datetime=datetime.datetime.now() + SETTING["datetime offset"],
        select_datetime=bool(SETTING["datetime offset"]),
        meta_title=SETTING["title"],
        meta_title_suggestions=SETTING["title-suggestions"],
        meta_author=SETTING["author"],
        meta_author_suggestions=SETTING["author-suggestions"],
        meta_subject=SETTING["subject"],
        meta_subject_suggestions=SETTING["subject-suggestions"],
        meta_keywords=SETTING["keywords"],
        meta_keywords_suggestions=SETTING["keywords-suggestions"],
        jpeg_quality=SETTING["quality"],
        downsample_dpi=SETTING["downsample dpi"],
        downsample=SETTING["downsample"],
        pdf_compression=SETTING["pdf compression"],
        text_position=SETTING["text_position"],
        pdf_font=SETTING["pdf font"],
        can_encrypt_pdf="pdftk" in dependencies,
    )

    # Frame for page range
    windowe.add_page_range()

    # PDF options
    windowe.add_pdf_options()

    def email_callback():

        # Set options
        windowe.update_config_dict(SETTING)

        # Compile list of pages
        SETTING["Page range"] = windowe.page_range
        uuids = list_of_page_uuids()

        # dig out the compression
        SETTING["downsample"] = windowe.downsample
        SETTING["downsample dpi"] = windowe.downsample_dpi
        SETTING["pdf compression"] = windowe.pdf_compression
        SETTING["quality"] = windowe.jpeg_quality

        # Compile options
        options = {
            "compression": SETTING["pdf compression"],
            "downsample": SETTING["downsample"],
            "downsample dpi": SETTING["downsample dpi"],
            "quality": SETTING["quality"],
            "text_position": SETTING["text_position"],
            "font": SETTING["pdf font"],
            "user-password": windowe.pdf_user_password,
        }
        filename = expand_metadata_pattern(
            template=SETTING["default filename"],
            convert_whitespace=SETTING["convert whitespace to underscores"],
            author=SETTING["author"],
            title=SETTING["title"],
            docdate=windowe.meta_datetime,
            today_and_now=datetime.datetime.now(),
            extension="pdf",
            subject=SETTING["subject"],
            keywords=SETTING["keywords"],
        )
        if re.search(r"^\s+$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE):
            filename = "document"
        pdf = f"{session}/{filename}.pdf"

        # Create the PDF

        def email_finished_callback(response):
            finish_tpbar(response)
            mark_pages(uuids)
            if "view files toggle" in SETTING and SETTING["view files toggle"]:
                launch_default_for_file(pdf)

            status = exec_command(["xdg-email", "--attach", pdf, "x@y"])
            if status:
                show_message_dialog(
                    parent=app.window,
                    message_type="error",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=_("Error creating email"),
                )

        slist.save_pdf(
            path=pdf,
            list_of_pages=uuids,
            metadata=collate_metadata(SETTING, datetime.datetime.now()),
            options=options,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=email_finished_callback,
            error_callback=error_callback,
        )
        windowe.hide()

    windowe.add_actions([("gtk-ok", email_callback), ("gtk-cancel", windowe.hide)])
    windowe.show_all()


def scan_dialog(_action, _param, hidden=False, scan=False):
    "Scan"
    global windows
    if windows:
        windows.show_all()
        update_postprocessing_options_callback(windows)
        return

    # If device not set by config and there is a default device, then set it
    if "device" not in SETTING and "SANE_DEFAULT_DEVICE" in os.environ:
        SETTING["device"] = os.environ["SANE_DEFAULT_DEVICE"]

    # scan dialog
    kwargs = {
        "transient_for": app.window,
        "title": _("Scan Document"),
        "dir": session,
        "hide_on_delete": True,
        "paper_formats": SETTING["Paper"],
        "allow_batch_flatbed": SETTING["allow-batch-flatbed"],
        "adf_defaults_scan_all_pages": SETTING["adf-defaults-scan-all-pages"],
        "document": slist,
        "ignore_duplex_capabilities": SETTING["ignore-duplex-capabilities"],
        "cycle_sane_handle": SETTING["cycle sane handle"],
        "cancel_between_pages": (
            SETTING["allow-batch-flatbed"] and SETTING["cancel-between-pages"]
        ),
    }
    if SETTING["scan_window_width"]:
        kwargs["default_width"] = SETTING["scan_window_width"]
    if SETTING["scan_window_height"]:
        kwargs["default_height"] = SETTING["scan_window_height"]
    windows = SaneScanDialog(**kwargs)

    # Can't set the device when creating the window,
    # as the list does not exist then
    windows.connect("changed-device-list", changed_device_list_callback)

    # Update default device
    windows.connect("changed-device", changed_device_callback)
    windows.connect(
        "changed-page-number-increment", update_postprocessing_options_callback
    )
    windows.connect("changed-side-to-scan", changed_side_to_scan_callback)
    signal = None

    def started_progress_callback(_widget, message):
        logger.debug("'started-process' emitted with message: %s", message)
        app.window._spbar.set_fraction(0)
        app.window._spbar.set_text(message)
        app.window._shbox.show_all()
        nonlocal signal
        signal = scbutton.connect("clicked", windows.cancel_scan)

    windows.connect("started-process", started_progress_callback)
    windows.connect("changed-progress", changed_progress_callback)
    windows.connect("finished-process", finished_process_callback)
    windows.connect("process-error", process_error_callback, signal)

    # Profiles
    for profile in SETTING["profile"].keys():
        windows._add_profile(
            profile,
            Profile(
                frontend=SETTING["profile"][profile]["frontend"],
                backend=SETTING["profile"][profile]["backend"],
            ),
        )

    def changed_profile_callback(_widget, profile):
        SETTING["default profile"] = profile

    windows.connect("changed-profile", changed_profile_callback)

    def added_profile_callback(_widget, name, profile):
        SETTING["profile"][name] = profile.get()

    windows.connect("added-profile", added_profile_callback)

    def removed_profile_callback(_widget, profile):
        del SETTING["profile"][profile]

    windows.connect("removed-profile", removed_profile_callback)

    def changed_current_scan_options_callback(_widget, profile, _uuid):
        "Update the default profile when the scan options change"
        SETTING["default-scan-options"] = profile.get()

    windows.connect(
        "changed-current-scan-options", changed_current_scan_options_callback
    )

    def changed_paper_formats_callback(_widget, formats):
        SETTING["Paper"] = formats

    windows.connect("changed-paper-formats", changed_paper_formats_callback)
    windows.connect("new-scan", new_scan_callback)
    windows.connect("changed-scan-option", update_postprocessing_options_callback)
    add_postprocessing_options(windows)
    if not hidden:
        windows.show_all()
    update_postprocessing_options_callback(windows)
    if args.device:
        device_list = []
        for d in args.device:
            device_list.append(SimpleNamespace(name=d, label=d))

        windows.device_list = device_list

    elif not scan and SETTING["cache-device-list"] and len(SETTING["device list"]):
        windows.device_list = SETTING["device list"]
    else:
        windows.get_devices()


def changed_device_callback(widget, device):
    "callback for changed device"
    # $widget is $windows
    if device != EMPTY:
        logger.info("signal 'changed-device' emitted with data: '%s'", device)
        SETTING["device"] = device

        # Can't set the profile until the options have been loaded. This
        # should only be called the first time after loading the available
        # options
        widget.reloaded_signal = widget.connect(
            "reloaded-scan-options", reloaded_scan_options_callback
        )
    else:
        logger.info("signal 'changed-device' emitted with data: undef")


def changed_device_list_callback(widget, device_list):  # $widget is $windows
    "callback for changed device list"
    logger.info("signal 'changed-device-list' emitted with data: %s", device_list)
    if len(device_list):

        # Apply the device blacklist
        if "device blacklist" in SETTING and SETTING["device blacklist"] not in [
            None,
            "",
        ]:
            i = 0
            while i < len(device_list):
                if re.search(
                    device_list[i].name,
                    SETTING["device blacklist"],
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    logger.info("Blacklisting device %s", device_list[i].name)
                    del device_list[i]
                else:
                    i += 1

            if len(device_list) < len(device_list):
                widget.device_list = device_list
                return

        if SETTING["cache-device-list"]:
            SETTING["device list"] = device_list

        # Only set default device if it hasn't been specified on the command line
        # and it is in the the device list
        if "device" in SETTING:
            for d in device_list:
                if SETTING["device"] == d.name:
                    widget.device = SETTING["device"]
                    return

        widget.device = device_list[0].name

    else:
        global windows
        windows = None


def changed_side_to_scan_callback(widget, _arg):
    "Callback function to handle the event when the side to scan is changed."
    logger.debug("changed_side_to_scan_callback( %s, %s )", widget, _arg)
    if len(slist.data) - 1 > EMPTY_LIST:
        widget.page_number_start = slist.data[len(slist.data) - 1][0] + 1
    else:
        widget.page_number_start = 1


def reloaded_scan_options_callback(widget):  # widget is windows
    "This should only be called the first time after loading the available options"
    widget.disconnect(widget.reloaded_signal)
    profiles = SETTING["profile"].keys()
    if "default profile" in SETTING:
        widget.profile = SETTING["default profile"]

    elif "default-scan-options" in SETTING:
        widget.set_current_scan_options(Profile(SETTING["default-scan-options"]))

    elif profiles:
        widget.profile = profiles[0]

    update_postprocessing_options_callback(widget)


def changed_progress_callback(_widget, progress, message):
    "Updates the progress bar based on the given progress value and message."
    if progress is not None and (0 <= progress <= 1):
        app.window._spbar.set_fraction(progress)
    else:
        app.window._spbar.pulse()
    if message is not None:
        app.window._spbar.set_text(message)


def import_scan_finished_callback(response):
    "Callback function to handle the completion of a scan import process."
    logger.debug("import_scan_finished_callback( %s )", response)
    # FIXME: response is hard-coded to None in _post_process_scan().
    # Work out how to pass number of pending requests
    # We have two threads, the scan thread, and the document thread.
    # We should probably combine the results in one progress bar
    # finish_tpbar(response)
    # slist.save_session()


def new_scan_callback(_self, image_object, page_number, xresolution, yresolution):
    "Callback function to handle a new scan."
    if image_object is None:
        return

    # Update undo/redo buffers
    take_snapshot()
    rotate = SETTING["rotate facing"] if page_number % 2 else SETTING["rotate reverse"]
    options = {
        "page": page_number,
        "dir": session.name,
        "to_png": SETTING["to_png"],
        "rotate": rotate,
        "ocr": SETTING["OCR on scan"],
        "engine": SETTING["ocr engine"],
        "language": SETTING["ocr language"],
        "queued_callback": setup_tpbar,
        "started_callback": update_tpbar,
        "finished_callback": import_scan_finished_callback,
        "error_callback": error_callback,
        "image_object": image_object,
        "resolution": (xresolution, yresolution, "PixelsPerInch"),
    }
    if SETTING["unpaper on scan"]:
        options["unpaper"] = unpaper

    if SETTING["threshold-before-ocr"]:
        options["threshold"] = SETTING["threshold tool"]

    if SETTING["udt_on_scan"]:
        options["udt"] = SETTING["current_udt"]

    logger.info("Importing scan with resolution=%s,%s", xresolution, yresolution)

    slist.import_scan(**options)


def process_error_callback(widget, process, msg, signal):
    "Callback function to handle process errors."
    logger.info("signal 'process-error' emitted with data: %s %s", process, msg)
    if signal is not None:
        scbutton.disconnect(signal)

    app.window._shbox.hide()
    if process == "open_device" and re.search(
        r"(Invalid[ ]argument|Device[ ]busy)",
        msg,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    ):
        error_name = "error opening device"
        response = None
        if (
            error_name in SETTING["message"]
            and SETTING["message"][error_name]["response"] == "ignore"
        ):
            response = SETTING["message"][error_name]["response"]

        else:
            dialog = Gtk.MessageDialog(
                parent=app.window,
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
            radio2 = Gtk.RadioButton.new_with_label_from_widget(
                radio1, label=_("Rescan for devices")
            )
            area.add(radio2)
            radio3 = Gtk.RadioButton.new_with_label_from_widget(
                radio1, label=_("Restart gscan2pdf.")
            )
            area.add(radio3)
            radio4 = Gtk.RadioButton.new_with_label_from_widget(
                radio1, label=_("Just ignore the error. I don't need the scanner yet.")
            )
            area.add(radio4)
            cb_cache_device_list = Gtk.CheckButton.new_with_label(
                _("Cache device list")
            )
            cb_cache_device_list.set_active(SETTING["cache-device-list"])
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
                SETTING["message"][error_name]["response"] = response

        global windows
        windows = None  # force scan dialog to be rebuilt
        if response == "reopen":
            scan_dialog(None, None)
        elif response == "rescan":
            scan_dialog(None, None, False, True)
        elif response == "restart":
            restart()

        # for ignore, we do nothing
        return

    show_message_dialog(
        parent=widget,
        message_type="error",
        buttons=Gtk.ButtonsType.CLOSE,
        page=EMPTY,
        process=process,
        text=msg,
        store_response=True,
    )


def finished_process_callback(_widget, process, button_signal=None):
    "Callback function to handle the completion of a process."
    logger.debug("signal 'finished-process' emitted with data: %s", process)
    if button_signal is not None:
        scbutton.disconnect(button_signal)

    app.window._shbox.hide()
    if process == "scan_pages" and windows.sided == "double":

        def prompt_reverse_sides():
            message, side = None, None
            if windows.side_to_scan == "facing":
                message = _("Finished scanning facing pages. Scan reverse pages?")
                side = "reverse"
            else:
                message = _("Finished scanning reverse pages. Scan facing pages?")
                side = "facing"

            response = ask_question(
                parent=windows,
                type="question",
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=message,
                default_response=Gtk.ResponseType.OK,
                store_response=True,
                stored_responses=[Gtk.ResponseType.OK],
            )
            if response == Gtk.ResponseType.OK:
                windows.side_to_scan = side

        GLib.idle_add(prompt_reverse_sides)


def restart():
    "Restart the application"
    ask_quit()
    os.execv(sys.executable, ["python"] + sys.argv)


def update_postprocessing_options_callback(
    widget, _option_name=None, _option_val=None, _uuid=None
):
    "update the visibility of post-processing options based on the widget's scan options."
    # widget is windows
    options = widget.available_scan_options
    increment = widget.page_number_increment
    if options is not None:
        if increment != 1 or options.can_duplex():
            rotate_side_cmbx.show()
            rotate_side_cmbx2.show()

        else:
            rotate_side_cmbx.hide()
            rotate_side_cmbx2.hide()


def add_postprocessing_rotate(vbox):
    "Adds post-processing rotation options to the given vbox."
    hboxr = Gtk.HBox()
    vbox.pack_start(hboxr, False, False, 0)
    rbutton = Gtk.CheckButton(label=_("Rotate"))
    rbutton.set_tooltip_text(_("Rotate image after scanning"))
    hboxr.pack_start(rbutton, True, True, 0)
    side = [
        ["both", _("Both sides"), _("Both sides.")],
        ["facing", _("Facing side"), _("Facing side.")],
        ["reverse", _("Reverse side"), _("Reverse side.")],
    ]
    global rotate_side_cmbx
    global rotate_side_cmbx2
    rotate_side_cmbx = ComboBoxText(data=side)
    rotate_side_cmbx.set_tooltip_text(_("Select side to rotate"))
    hboxr.pack_start(rotate_side_cmbx, True, True, 0)
    rotate = [
        [_90_DEGREES, _("90"), _("Rotate image 90 degrees clockwise.")],
        [_180_DEGREES, _("180"), _("Rotate image 180 degrees clockwise.")],
        [_270_DEGREES, _("270"), _("Rotate image 90 degrees anticlockwise.")],
    ]
    comboboxr = ComboBoxText(data=rotate)
    comboboxr.set_tooltip_text(_("Select direction of rotation"))
    hboxr.pack_end(comboboxr, True, True, 0)
    hboxr = Gtk.HBox()
    vbox.pack_start(hboxr, False, False, 0)
    r2button = Gtk.CheckButton(label=_("Rotate"))
    r2button.set_tooltip_text(_("Rotate image after scanning"))
    hboxr.pack_start(r2button, True, True, 0)
    rotate_side_cmbx2 = Gtk.ComboBoxText()
    rotate_side_cmbx2.set_tooltip_text(_("Select side to rotate"))
    hboxr.pack_start(rotate_side_cmbx2, True, True, 0)
    comboboxr2 = ComboBoxText(data=rotate)
    comboboxr2.set_tooltip_text(_("Select direction of rotation"))
    hboxr.pack_end(comboboxr2, True, True, 0)

    def toggled_rotate_callback():
        if rbutton.get_active():
            if side[rotate_side_cmbx.get_active()][0] != "both":
                hboxr.set_sensitive(True)
        else:
            hboxr.set_sensitive(False)

    rbutton.connect("toggled", toggled_rotate_callback)

    def toggled_rotate_side_callback(_arg):
        if side[rotate_side_cmbx.get_active()][0] == "both":
            hboxr.set_sensitive(False)
            r2button.set_active(False)
        else:
            if rbutton.get_active():
                hboxr.set_sensitive(True)

                # Empty combobox
            while rotate_side_cmbx2.get_active() > EMPTY_LIST:
                rotate_side_cmbx2.remove(0)
                rotate_side_cmbx2.set_active(0)

            side2 = []
            for s in side:
                if s[0] != "both" and s[0] != side[rotate_side_cmbx.get_active()][0]:
                    side2.append(s)

            rotate_side_cmbx2.append_text(side2[0][1])
            rotate_side_cmbx2.set_active(0)

    rotate_side_cmbx.connect("changed", toggled_rotate_side_callback)

    # In case it isn't set elsewhere
    comboboxr2.set_active_index(_90_DEGREES)
    if SETTING["rotate facing"] or SETTING["rotate reverse"]:
        rbutton.set_active(True)

    if SETTING["rotate facing"] == SETTING["rotate reverse"]:
        rotate_side_cmbx.set_active_index("both")
        comboboxr.set_active_index(SETTING["rotate facing"])

    elif SETTING["rotate facing"]:
        rotate_side_cmbx.set_active_index("facing")
        comboboxr.set_active_index(SETTING["rotate facing"])
        if SETTING["rotate reverse"]:
            r2button.set_active(True)
            rotate_side_cmbx2.set_active_index("reverse")
            comboboxr2.set_active_index(SETTING["rotate reverse"])

    else:
        rotate_side_cmbx.set_active_index("reverse")
        comboboxr.set_active_index(SETTING["rotate reverse"])

    return rbutton, r2button, comboboxr, comboboxr2


def add_postprocessing_udt(vboxp):
    "Adds a user-defined tool (UDT) post-processing option to the given VBox."
    hboxudt = Gtk.HBox()
    vboxp.pack_start(hboxudt, False, False, 0)
    udtbutton = Gtk.CheckButton(label=_("Process with user-defined tool"))
    udtbutton.set_tooltip_text(_("Process scanned images with user-defined tool"))
    hboxudt.pack_start(udtbutton, True, True, 0)
    if not SETTING["user_defined_tools"]:
        hboxudt.set_sensitive(False)
        udtbutton.set_active(False)

    elif SETTING["udt_on_scan"]:
        udtbutton.set_active(True)

    return udtbutton, add_udt_combobox(hboxudt)


def add_udt_combobox(hbox):
    "Adds a ComboBoxText widget to the given hbox containing user-defined tools."
    toolarray = []
    for t in SETTING["user_defined_tools"]:
        toolarray.append([t, t])

    combobox = ComboBoxText(data=toolarray)
    combobox.set_active_index(SETTING["current_udt"])
    hbox.pack_start(combobox, True, True, 0)
    return combobox


def add_postprocessing_ocr(vbox):
    "Adds post-processing OCR options to the given vbox."
    hboxo = Gtk.HBox()
    vbox.pack_start(hboxo, False, False, 0)
    obutton = Gtk.CheckButton(label=_("OCR scanned pages"))
    obutton.set_tooltip_text(_("OCR scanned pages"))
    if not dependencies["ocr"]:
        hboxo.set_sensitive(False)
        obutton.set_active(False)

    elif SETTING["OCR on scan"]:
        obutton.set_active(True)

    hboxo.pack_start(obutton, True, True, 0)
    comboboxe = ComboBoxText(data=ocr_engine)
    comboboxe.set_tooltip_text(_("Select OCR engine"))
    hboxo.pack_end(comboboxe, True, True, 0)
    comboboxtl, hboxtl = None, None

    if dependencies["tesseract"]:
        hboxtl, comboboxtl, _tesslang = add_tess_languages(vbox)

        def ocr_engine_changed_callback(comboboxe):
            if comboboxe.get_active_text() == "tesseract":
                hboxtl.show_all()
            else:
                hboxtl.hide()

        comboboxe.connect("changed", ocr_engine_changed_callback)
        if not obutton.get_active():
            hboxtl.set_sensitive(False)

        obutton.connect("toggled", lambda x: hboxtl.set_sensitive(x.get_active()))

    comboboxe.set_active_index(SETTING["ocr engine"])
    if len(ocr_engine) > 0 and comboboxe.get_active_index() is None:
        comboboxe.set_active(0)

    # Checkbox & SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox.pack_start(hboxt, False, True, 0)
    cbto = Gtk.CheckButton(label=_("Threshold before OCR"))
    cbto.set_tooltip_text(
        _(
            "Threshold the image before performing OCR. "
            + "This only affects the image passed to the OCR engine, and not the image stored."
        )
    )
    cbto.set_active(SETTING["threshold-before-ocr"])
    hboxt.pack_start(cbto, False, True, 0)
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end(labelp, False, True, 0)
    spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbutton.set_value(SETTING["threshold tool"])
    spinbutton.set_sensitive(cbto.get_active())
    hboxt.pack_end(spinbutton, False, True, 0)
    cbto.connect("toggled", lambda _: spinbutton.set_sensitive(cbto.get_active()))
    return obutton, comboboxe, hboxtl, comboboxtl, cbto, spinbutton


def add_postprocessing_options(self):
    "Adds post-processing options to the dialog window."
    scwin = Gtk.ScrolledWindow()
    self.notebook.append_page(scwin, Gtk.Label(label=_("Postprocessing")))
    scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    vboxp = Gtk.VBox()
    vboxp.set_border_width(self.get_border_width())
    scwin.add(vboxp)

    # Rotate
    rbutton, r2button, comboboxr, comboboxr2 = add_postprocessing_rotate(vboxp)

    # CheckButton for unpaper
    hboxu = Gtk.HBox()
    vboxp.pack_start(hboxu, False, False, 0)
    ubutton = Gtk.CheckButton(label=_("Clean up images"))
    ubutton.set_tooltip_text(_("Clean up scanned images with unpaper"))
    hboxu.pack_start(ubutton, True, True, 0)
    if not dependencies["unpaper"]:
        ubutton.set_sensitive(False)
        ubutton.set_active(False)
    elif SETTING["unpaper on scan"]:
        ubutton.set_active(True)

    button = Gtk.Button(label=_("Options"))
    button.set_tooltip_text(_("Set unpaper options"))
    hboxu.pack_end(button, True, True, 0)

    def show_unpaper_options():
        windowuo = Dialog(
            transient_for=app.window,
            title=_("unpaper options"),
        )
        unpaper.add_options(windowuo.get_content_area())

        def unpaper_options_callback():

            # Update $SETTING
            SETTING["unpaper options"] = unpaper.get_options()
            windowuo.destroy()

        windowuo.add_actions(
            [
                ("gtk-ok", unpaper_options_callback),
                ("gtk-cancel", windowuo.destroy),
            ]
        )
        windowuo.show_all()

    button.connect("clicked", show_unpaper_options)
    # CheckButton for user-defined tool
    udtbutton, self.comboboxudt = add_postprocessing_udt(vboxp)
    obutton, comboboxe, hboxtl, comboboxtl, tbutton, tsb = add_postprocessing_ocr(vboxp)

    def clicked_scan_button_cb(w):
        SETTING["rotate facing"] = 0
        SETTING["rotate reverse"] = 0
        if rbutton.get_active():
            if rotate_side_cmbx.get_active_index() == "both":
                SETTING["rotate facing"] = comboboxr.get_active_index()
                SETTING["rotate reverse"] = SETTING["rotate facing"]

            elif rotate_side_cmbx.get_active_index() == "facing":
                SETTING["rotate facing"] = comboboxr.get_active_index()

            else:
                SETTING["rotate reverse"] = comboboxr.get_active_index()

            if r2button.get_active():
                if rotate_side_cmbx2.get_active_index() == "facing":
                    SETTING["rotate facing"] = comboboxr2.get_active_index()

                else:
                    SETTING["rotate reverse"] = comboboxr2.get_active_index()

        logger.info("rotate facing %s", SETTING["rotate facing"])
        logger.info("rotate reverse %s", SETTING["rotate reverse"])
        SETTING["unpaper on scan"] = ubutton.get_active()
        logger.info("unpaper %s", SETTING["unpaper on scan"])
        SETTING["udt_on_scan"] = udtbutton.get_active()
        SETTING["current_udt"] = self.comboboxudt.get_active_text()
        logger.info("UDT %s", SETTING["udt_on_scan"])
        if "current_udt" in SETTING:
            logger.info("Current UDT %s", SETTING["current_udt"])

        SETTING["OCR on scan"] = obutton.get_active()
        logger.info("OCR %s", SETTING["OCR on scan"])
        if SETTING["OCR on scan"]:
            SETTING["ocr engine"] = comboboxe.get_active_index()
            if SETTING["ocr engine"] is None:
                SETTING["ocr engine"] = ocr_engine[0][0]
            logger.info("ocr engine %s", SETTING["ocr engine"])
            if SETTING["ocr engine"] == "tesseract":
                SETTING["ocr language"] = comboboxtl.get_active_index()
                logger.info("ocr language %s", SETTING["ocr language"])

            SETTING["threshold-before-ocr"] = tbutton.get_active()
            logger.info("threshold-before-ocr %s", SETTING["threshold-before-ocr"])
            SETTING["threshold tool"] = tsb.get_value()

    self.connect("clicked-scan-button", clicked_scan_button_cb)

    def show_callback(_w):
        i = comboboxe.get_active()
        if i > -1 and hboxtl is not None and ocr_engine[i][0] != "tesseract":
            hboxtl.hide()

    self.connect("show", show_callback)
    # $self->{notebook}->get_nth_page(1)->show_all;


def print_dialog(_action, _param):
    "print"
    os.chdir(SETTING["cwd"])
    print_op = PrintOperation(settings=app.window.print_settings, slist=slist)
    res = print_op.run(Gtk.PrintOperationAction.PRINT_DIALOG, app.window)
    if res == Gtk.PrintOperationResult.APPLY:
        app.window.print_settings = print_op.get_print_settings()
    os.chdir(session.name)


def cut_selection(_action, _param):
    "Cut the selection"
    slist.clipboard = slist.cut_selection()
    update_uimanager()


def copy_selection(_action, _param):
    "Copy the selection"
    slist.clipboard = slist.copy_selection(True)
    update_uimanager()


def paste_selection(_action, _param):
    "Paste the selection"
    if slist.clipboard is None:
        return
    take_snapshot()
    pages = slist.get_selected_indices()
    if pages:
        slist.paste_selection(slist.clipboard, pages[-1], "after", True)
    else:
        slist.paste_selection(slist.clipboard, None, None, True)
    update_uimanager()


def delete_selection(_action, _param):
    "Delete the selected scans"
    # Update undo/redo buffers
    take_snapshot()
    slist._delete_selection_extra()

    # Reset start page in scan dialog
    if windows:
        windows._reset_start_page()
    update_uimanager()


def select_all(_action, _param):
    "Select all scans"
    # if ($textview -> has_focus) {
    #  my ($start, $end) = $textbuffer->get_bounds;
    #  $textbuffer->select_range ($start, $end);
    # }
    # else {

    slist.get_selection().select_all()

    # }


def select_odd_even(odd):
    "Select all odd(0) or even(1) scans"
    selection = []
    for i, row in enumerate(slist.data):
        if row[0] % 2 ^ odd:
            selection.append(i)

    slist.get_selection().unselect_all()
    slist.select(selection)


def select_invert(_action, _param):
    "Invert selection"
    selection = slist.get_selected_indices()
    inverted = []
    for i in range(len(slist.data)):
        if i not in selection:
            inverted.append(_)
    slist.get_selection().unselect_all()
    slist.select(inverted)


def select_modified_since_ocr(_action, _param):
    "Selects pages that have been modified since the last OCR process."
    selection = []
    for page in range(len(slist.data)):
        dirty_time = (
            page.dirty_time
            if hasattr(page, "dirty_time")
            else datetime.datetime(1970, 1, 1)
        )
        ocr_time = (
            page.ocr_time
            if hasattr(page, "ocr_time")
            else datetime.datetime(1970, 1, 1)
        )
        ocr_flag = page.ocr_flag if hasattr(page, "ocr_flag") else False
        if ocr_flag and (ocr_time <= dirty_time):
            selection.append(_)

    slist.get_selection().unselect_all()
    slist.select(selection)


def select_no_ocr(_action, _param):
    "Select pages with no ocr output"
    selection = []
    for i, row in enumerate(slist.data):
        if not hasattr(row[2], "text_layer") or row[2].text_layer is None:
            selection.append(i)

    slist.get_selection().unselect_all()
    slist.select(selection)


def clear_ocr(_action, _param):
    "Clear the OCR output from selected pages"
    # Update undo/redo buffers
    take_snapshot()

    # Clear the existing canvas
    canvas.clear_text()
    selection = slist.get_selected_indices()
    for i in selection:
        slist.data[i][2].text_layer = None

    # slist.save_session()


def select_blank(_action, _param):
    "Analyse and select blank pages"
    analyse(True, False)


def select_blank_pages():
    "Select blank pages"
    for page in slist.data:

        # compare Std Dev to threshold
        # std_dev is a list -- 1 value per channel
        if sum(page[2].std_dev) / len(page[2].std_dev) <= SETTING["Blank threshold"]:
            slist.select(page)
            logger.info("Selecting blank page")
        else:
            slist.unselect(page)
            logger.info("Unselecting non-blank page")

        logger.info(
            "StdDev: %s threshold: %s",
            page[2].std_dev,
            SETTING["Blank threshold"],
        )


def select_dark(_action, _param):
    "Analyse and select dark pages"
    analyse(False, True)


def select_dark_pages():
    "Select dark pages"
    for page in slist.data:

        # compare Mean to threshold
        # mean is a list -- 1 value per channel
        if sum(page[2].mean) / len(page[2].std_dev) <= SETTING["Dark threshold"]:
            slist.select(page)
            logger.info("Selecting dark page")
        else:
            slist.unselect(page)
            logger.info("Unselecting non-dark page")

        logger.info(
            "mean: %s threshold: %s",
            page[2].mean,
            SETTING["Dark threshold"],
        )


def renumber_dialog(_action, _param):
    "Dialog for renumber"
    if app.window.renumber_dialog is not None:
        app.window.renumber_dialog.present()
        return

    app.window.renumber_dialog = Renumber(
        transient_for=app.window,
        document=slist,
        hide_on_delete=False,
    )
    app.window.renumber_dialog.connect("before-renumber", lambda x: take_snapshot())
    app.window.renumber_dialog.connect(
        "error",
        lambda msg: show_message_dialog(
            parent=app.window.renumber_dialog,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            text=msg,
        ),
    )
    app.window.renumber_dialog.show_all()


def indices2pages(indices):
    "Helper function to convert an array of indices into an array of Gscan2pdf::Page objects"
    pages = []
    for i in indices:
        pages.append(slist.data[i][2].uuid)
    return pages


def rotate(angle, pagelist):
    "Rotate selected images"

    # Update undo/redo buffers
    take_snapshot()
    for page in pagelist:
        slist.rotate(
            angle=angle,
            page=page,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=finish_tpbar,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def analyse(select_blank, select_dark):
    "Analyse selected images"

    # Update undo/redo buffers
    take_snapshot()
    pages_to_analyse = []
    for row in slist.data:
        page = row[2]
        dirty_time = (
            page.dirty_time
            if hasattr(page, "dirty_time")
            else datetime.datetime(1970, 1, 1)
        )
        analyse_time = (
            page.analyse_time
            if hasattr(page, "analyse_time")
            else datetime.datetime(1970, 1, 1)
        )
        if analyse_time <= dirty_time:
            logger.info(
                "Updating: %s analyse_time: %s dirty_time: %s",
                row[0],
                analyse_time,
                dirty_time,
            )
            pages_to_analyse.append(page.uuid)

    if len(pages_to_analyse) > 0:

        def analyse_finished_callback(response):
            finish_tpbar(response)
            if select_blank:
                select_blank_pages()
            if select_dark:
                select_dark_pages()

        # slist.save_session()

        slist.analyse(
            list_of_pages=pages_to_analyse,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=analyse_finished_callback,
            error_callback=error_callback,
        )

    else:
        if select_blank:
            select_blank_pages()
        if select_dark:
            select_dark_pages()


def threshold(_action, _param):
    "Display page selector and on apply threshold accordingly"
    windowt = Dialog(
        transient_for=app.window,
        title=_("Threshold"),
    )

    # Frame for page range
    windowt.add_page_range()

    # SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox = windowt.get_content_area()
    vbox.pack_start(hboxt, False, True, 0)
    label = Gtk.Label(label=_("Threshold"))
    hboxt.pack_start(label, False, True, 0)
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end(labelp, False, True, 0)
    spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbutton.set_value(SETTING["threshold tool"])
    hboxt.pack_end(spinbutton, False, True, 0)

    def threshold_apply_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        SETTING["threshold tool"] = spinbutton.get_value()
        SETTING["Page range"] = windowt.page_range
        pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
        if not pagelist:
            return
        page = 0
        for i in pagelist:
            page += 1

            def threshold_finished_callback(response):
                finish_tpbar(response)
                # slist.save_session()

            slist.threshold(
                threshold=SETTING["threshold tool"],
                page=slist.data[i][2].uuid,
                queued_callback=setup_tpbar,
                started_callback=update_tpbar,
                running_callback=update_tpbar,
                finished_callback=threshold_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    windowt.add_actions(
        [
            ("gtk-apply", threshold_apply_callback),
            ("gtk-cancel", windowt.destroy),
        ]
    )
    windowt.show_all()


def brightness_contrast(_action, _param):
    "Display page selector and on apply brightness & contrast accordingly"
    windowt = Dialog(
        transient_for=app.window,
        title=_("Brightness / Contrast"),
    )
    hbox, label = None, None

    # Frame for page range
    windowt.add_page_range()

    # SpinButton for brightness
    hbox = Gtk.HBox()
    vbox = windowt.get_content_area()
    vbox.pack_start(hbox, False, True, 0)
    label = Gtk.Label(label=_("Brightness"))
    hbox.pack_start(label, False, True, 0)
    label = Gtk.Label(label=PERCENT)
    hbox.pack_end(label, False, True, 0)
    spinbuttonb = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbuttonb.set_value(SETTING["brightness tool"])
    hbox.pack_end(spinbuttonb, False, True, 0)

    # SpinButton for contrast
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, False, True, 0)
    label = Gtk.Label(label=_("Contrast"))
    hbox.pack_start(label, False, True, 0)
    label = Gtk.Label(label=PERCENT)
    hbox.pack_end(label, False, True, 0)
    spinbuttonc = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbuttonc.set_value(SETTING["contrast tool"])
    hbox.pack_end(spinbuttonc, False, True, 0)

    def brightness_contrast_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        SETTING["brightness tool"] = spinbuttonb.get_value()
        SETTING["contrast tool"] = spinbuttonc.get_value()
        SETTING["Page range"] = windowt.page_range
        pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
        if not pagelist:
            return
        for i in pagelist:

            def brightness_contrast_finished_callback(response):
                finish_tpbar(response)
                # slist.save_session()

            slist.brightness_contrast(
                brightness=SETTING["brightness tool"],
                contrast=SETTING["contrast tool"],
                page=slist.data[i][2].uuid,
                queued_callback=setup_tpbar,
                started_callback=update_tpbar,
                running_callback=update_tpbar,
                finished_callback=brightness_contrast_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    windowt.add_actions(
        [
            ("gtk-apply", brightness_contrast_callback),
            ("gtk-cancel", windowt.destroy),
        ]
    )
    windowt.show_all()


def negate(_action, _param):
    "Display page selector and on apply negate accordingly"
    windowt = Dialog(
        transient_for=app.window,
        title=_("Negate"),
    )

    # Frame for page range
    windowt.add_page_range()

    def negate_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        SETTING["Page range"] = windowt.page_range
        pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
        if not pagelist:
            return
        for i in pagelist:

            def negate_finished_callback(response):
                finish_tpbar(response)
                # slist.save_session()

            slist.negate(
                page=slist.data[i][2].uuid,
                queued_callback=setup_tpbar,
                started_callback=update_tpbar,
                running_callback=update_tpbar,
                finished_callback=negate_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    windowt.add_actions(
        [("gtk-apply", negate_callback), ("gtk-cancel", windowt.destroy)]
    )
    windowt.show_all()


def unsharp(_action, _param):
    "Display page selector and on apply unsharp accordingly"
    windowum = Dialog(
        transient_for=app.window,
        title=_("Unsharp mask"),
    )

    # Frame for page range

    windowum.add_page_range()
    spinbuttonr = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbuttons = Gtk.SpinButton.new_with_range(0, 2 * _100_PERCENT, 1)
    spinbuttont = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    layout = [
        [
            _("Radius"),
            spinbuttonr,
            _("pixels"),
            SETTING["unsharp radius"],
            _("Blur Radius."),
        ],
        [
            _("Percentage"),
            spinbuttons,
            _("%"),
            SETTING["unsharp percentage"],
            _("Unsharp strength, in percent."),
        ],
        [
            _("Threshold"),
            spinbuttont,
            None,
            SETTING["unsharp threshold"],
            _(
                "Threshold controls the minimum brightness change that will be sharpened."
            ),
        ],
    ]

    # grid for layout
    grid = Gtk.Grid()
    vbox = windowum.get_content_area()
    vbox.pack_start(grid, True, True, 0)
    for i, row in enumerate(layout):
        col = 0
        hbox = Gtk.HBox()
        label = Gtk.Label(label=row[col])
        grid.attach(hbox, col, i, 1, 1)
        col += 1
        hbox.pack_start(label, False, True, 0)
        hbox = Gtk.HBox()
        hbox.pack_end(row[col], True, True, 0)
        grid.attach(hbox, col, i, 1, 1)
        col += 1
        if col in row:
            hbox = Gtk.HBox()
            grid.attach(hbox, col, i, 1, 1)
            label = Gtk.Label(label=row[col])
            hbox.pack_start(label, False, True, 0)

        col += 1
        if col in row:
            row[1].set_value(row[col])

        col += 1
        row[1].set_tooltip_text(row[col])

    def unsharp_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        SETTING["unsharp radius"] = spinbuttonr.get_value()
        SETTING["unsharp percentage"] = int(spinbuttons.get_value())
        SETTING["unsharp threshold"] = int(spinbuttont.get_value())
        SETTING["Page range"] = windowum.page_range
        pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
        if not pagelist:
            return
        for i in pagelist:

            def unsharp_finished_callback(response):
                finish_tpbar(response)
                # slist.save_session()

            slist.unsharp(
                page=slist.data[i][2].uuid,
                radius=SETTING["unsharp radius"],
                percent=SETTING["unsharp percentage"],
                threshold=SETTING["unsharp threshold"],
                queued_callback=setup_tpbar,
                started_callback=update_tpbar,
                running_callback=update_tpbar,
                finished_callback=unsharp_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    windowum.add_actions(
        [("gtk-apply", unsharp_callback), ("gtk-cancel", windowum.destroy)]
    )
    windowum.show_all()


def crop_dialog(_action, _param):
    "Display page selector and on apply crop accordingly"
    global windowc
    if windowc is not None:
        windowc.present()
        return

    width, height = app.window._current_page.get_size()
    windowc = Crop(transient_for=app.window, page_width=width, page_height=height)

    def on_changed_selection(_widget, selection):
        SETTING["selection"] = selection
        view.handler_block(view.selection_changed_signal)
        view.set_selection(selection)
        view.handler_unblock(view.selection_changed_signal)

    windowc.connect("changed-selection", on_changed_selection)

    if SETTING["selection"]:
        windowc.selection = SETTING["selection"]

    def crop_callback():
        SETTING["Page range"] = windowc.page_range
        crop_selection(
            None,  # action
            None,  # param
            slist.get_page_index(SETTING["Page range"], error_callback),
        )

    windowc.add_actions([("gtk-apply", crop_callback), ("gtk-cancel", windowc.hide)])
    windowc.show_all()


def crop_selection(_action, _param, pagelist=None):
    "Crop the selected area of the specified pages."
    if not SETTING["selection"]:
        return

    # Update undo/redo buffers
    take_snapshot()
    if not pagelist:
        pagelist = slist.get_selected_indices()

    if not pagelist:
        return

    for i in pagelist:

        def crop_finished_callback(response):
            finish_tpbar(response)
            # slist.save_session()

        slist.crop(
            page=slist.data[i][2].uuid,
            x=SETTING["selection"].x,
            y=SETTING["selection"].y,
            w=SETTING["selection"].width,
            h=SETTING["selection"].height,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=crop_finished_callback,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def split_dialog(_action, _param):
    "Display page selector and on apply crop accordingly"

    # Until we have a separate tool for the divider, kill the whole
    #        sub { $windowsp->hide }
    #    if ( defined $windowsp ) {
    #        $windowsp->present;
    #        return;
    #    }

    windowsp = Dialog(
        transient_for=app.window,
        title=_("Split"),
        hide_on_delete=True,
    )

    # Frame for page range
    windowsp.add_page_range()
    hbox = Gtk.HBox()
    vbox = windowsp.get_content_area()
    vbox.pack_start(hbox, False, False, 0)
    label = Gtk.Label(label=_("Direction"))
    hbox.pack_start(label, False, True, 0)
    direction = [
        [
            "v",
            _("Vertically"),
            _("Split the page vertically into left and right pages."),
        ],
        [
            "h",
            _("Horizontally"),
            _("Split the page horizontally into top and bottom pages."),
        ],
    ]
    combob = ComboBoxText(data=direction)
    width, height = app.window._current_page.get_size()
    sb_pos = Gtk.SpinButton.new_with_range(0, width, 1)

    def changed_split_direction(_widget):
        if direction[combob.get_active()][0] == "v":
            sb_pos.set_range(0, width)

        else:
            sb_pos.set_range(0, height)

        update_view_position(
            direction[combob.get_active()][0], sb_pos.get_value(), width, height
        )

    combob.connect("changed", changed_split_direction)
    combob.set_active_index("v")
    hbox.pack_end(combob, False, True, 0)

    # SpinButton for position
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, False, True, 0)
    label = Gtk.Label(label=_("Position"))
    hbox.pack_start(label, False, True, 0)
    hbox.pack_end(sb_pos, False, True, 0)

    def changed_split_position_sb_value(_widget):
        update_view_position(
            direction[combob.get_active()][0], sb_pos.get_value(), width, height
        )

    sb_pos.connect("value-changed", changed_split_position_sb_value)
    sb_pos.set_value(width / 2)

    def changed_split_position_selection(_widget, sel):
        if sel:
            if direction[combob.get_active()][0] == "v":
                sb_pos.set_value(sel.x + sel.width)
            else:
                sb_pos.set_value(sel.y + sel.height)

    view.position_changed_signal = view.connect(
        "selection-changed", changed_split_position_selection
    )

    def split_apply_callback():

        # Update undo/redo buffers
        take_snapshot()
        SETTING["split-direction"] = direction[combob.get_active()][0]
        SETTING["split-position"] = sb_pos.get_value()
        SETTING["Page range"] = windowsp.page_range
        pagelist = slist.get_page_index(SETTING["Page range"], error_callback)
        if not pagelist:
            return
        page = 0
        for i in pagelist:
            page += 1

            def split_finished_callback(response):
                finish_tpbar(response)
                # slist.save_session()

            slist.split_page(
                direction=SETTING["split-direction"],
                position=SETTING["split-position"],
                page=slist.data[i][2].uuid,
                queued_callback=setup_tpbar,
                started_callback=update_tpbar,
                running_callback=update_tpbar,
                finished_callback=split_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    def split_cancel_callback():
        view.disconnect(view.position_changed_signal)
        windowsp.destroy()

    windowsp.add_actions(
        [
            ("gtk-apply", split_apply_callback),
            (
                "gtk-cancel",
                # Until we have a separate tool for the divider, kill the whole
                #        sub { $windowsp->hide }
                split_cancel_callback,
            ),
        ]
    )
    windowsp.show_all()


def update_view_position(direction, position, width, height):
    "Updates the view's selection rectangle based on the given direction and dimensions."
    selection = Gdk.Rectangle()
    if direction == "v":
        selection.width = position
        selection.height = height
    else:
        selection.width = width
        selection.height = position

    view.set_selection(selection)


def user_defined_dialog(_action, _param):
    "Displays a dialog for selecting and applying user-defined tools."
    global windowudt
    if windowudt is not None:
        windowudt.present()
        return

    windowudt = Dialog(
        transient_for=app.window,
        title=_("User-defined tools"),
        hide_on_delete=True,
    )

    # Frame for page range
    windowudt.add_page_range()
    hbox = Gtk.HBox()
    vbox = windowudt.get_content_area()
    vbox.pack_start(hbox, False, False, 0)
    label = Gtk.Label(label=_("Selected tool"))
    hbox.pack_start(label, False, True, 0)
    comboboxudt = add_udt_combobox(hbox)

    def udt_apply_callback():
        SETTING["Page range"] = windowudt.page_range
        pagelist = indices2pages(
            slist.get_page_index(SETTING["Page range"], error_callback)
        )
        if not pagelist:
            return
        SETTING["current_udt"] = comboboxudt.get_active_text()
        user_defined_tool(pagelist, SETTING["current_udt"])
        windowudt.hide()

    windowudt.add_actions(
        [("gtk-ok", udt_apply_callback), ("gtk-cancel", windowudt.hide)]
    )
    windowudt.show_all()


def user_defined_tool(pages, cmd):
    "Run a user-defined tool on the selected images"

    # Update undo/redo buffers
    take_snapshot()
    for page in pages:

        def user_defined_finished_callback(response):
            finish_tpbar(response)
            # slist.save_session()

        slist.user_defined(
            page=page,
            command=cmd,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=user_defined_finished_callback,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def unpaper_page(pages, options):
    "queue $page to be processed by unpaper"
    if options is None:
        options = {}

    # Update undo/redo buffers
    take_snapshot()
    for pageobject in pages:

        def unpaper_finished_callback(response):
            finish_tpbar(response)
            # slist.save_session()

        slist.unpaper(
            page=pageobject,
            options=options,
            queued_callback=setup_tpbar,
            started_callback=update_tpbar,
            running_callback=update_tpbar,
            finished_callback=unpaper_finished_callback,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def unpaper(_action, _param):
    "Run unpaper to clean up scan."
    global windowu
    if windowu is not None:
        windowu.present()
        return

    windowu = Dialog(
        transient_for=app.window,
        title=_("unpaper"),
        hide_on_delete=True,
    )

    # Frame for page range
    windowu.add_page_range()

    # add unpaper options
    vbox = windowu.get_content_area()
    unpaper.add_options(vbox)

    def unpaper_apply_callback():

        # Update $SETTING
        SETTING["unpaper options"] = unpaper.get_options()
        SETTING["Page range"] = windowu.page_range

        # run unpaper
        pagelist = indices2pages(
            slist.get_page_index(SETTING["Page range"], error_callback)
        )
        if not pagelist:
            return
        unpaper_page(
            pagelist,
            {
                "command": unpaper.get_cmdline(),
                "direction": unpaper.get_option("direction"),
            },
        )
        windowu.hide()

    windowu.add_actions(
        [("gtk-ok", unpaper_apply_callback), ("gtk-cancel", windowu.hide)]
    )
    windowu.show_all()


def add_tess_languages(vbox):
    "Add hbox for tesseract languages"
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, False, False, 0)
    label = Gtk.Label(label=_("Language to recognise"))
    hbox.pack_start(label, False, True, 0)

    # Tesseract language files
    tesslang = []
    tesscodes = get_tesseract_codes()
    langs = languages(tesscodes)
    for lang in sorted(tesscodes):
        tesslang.append([lang, langs[lang]])

    combobox = ComboBoxText(data=tesslang)
    combobox.set_active_index(SETTING["ocr language"])
    if not combobox.get_active_index():
        combobox.set_active(0)
    hbox.pack_end(combobox, False, True, 0)
    return hbox, combobox, tesslang


def ocr_dialog(_action, _parma):
    "Run OCR on current page and display result"
    global windowo
    if windowo is not None:
        windowo.present()
        return

    windowo = Dialog(
        transient_for=app.window,
        title=_("OCR"),
        hide_on_delete=True,
    )

    # Frame for page range
    windowo.add_page_range()

    # OCR engine selection
    hboxe = Gtk.HBox()
    vbox = windowo.get_content_area()
    vbox.pack_start(hboxe, False, True, 0)
    label = Gtk.Label(label=_("OCR Engine"))
    hboxe.pack_start(label, False, True, 0)
    combobe = ComboBoxText(data=ocr_engine)
    combobe.set_active_index(SETTING["ocr engine"])
    hboxe.pack_end(combobe, False, True, 0)
    comboboxtl, hboxtl, tesslang = None, None, []
    if dependencies["tesseract"]:
        hboxtl, comboboxtl, tesslang = add_tess_languages(vbox)

        def changed_ocr_engine():
            if ocr_engine[combobe.get_active()][0] == "tesseract":
                hboxtl.show_all()
            else:
                hboxtl.hide()

        combobe.connect("changed", changed_ocr_engine)

    # Checkbox & SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox.pack_start(hboxt, False, True, 0)
    cbto = Gtk.CheckButton(label=_("Threshold before OCR"))
    cbto.set_tooltip_text(
        _(
            "Threshold the image before performing OCR. "
            + "This only affects the image passed to the OCR engine, and not the image stored."
        )
    )
    if "threshold-before-ocr" in SETTING:
        cbto.set_active(SETTING["threshold-before-ocr"])

    hboxt.pack_start(cbto, False, True, 0)
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end(labelp, False, True, 0)
    spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbutton.set_value(SETTING["threshold tool"])
    spinbutton.set_sensitive(cbto.get_active())
    hboxt.pack_end(spinbutton, False, True, 0)

    def toggled_threshold_ocr():
        spinbutton.set_sensitive(cbto.get_active())

    cbto.connect("toggled", toggled_threshold_ocr)

    def ocr_apply_callback():
        lang = None
        if comboboxtl is not None:
            lang = tesslang[comboboxtl.get_active()][0]

        run_ocr(
            ocr_engine[combobe.get_active()][0],
            lang,
            cbto.get_active(),
            spinbutton.get_value(),
        )

    windowo.add_actions([("gtk-ok", ocr_apply_callback), ("gtk-cancel", windowo.hide)])
    windowo.show_all()
    if hboxtl is not None and ocr_engine[combobe.get_active()][0] != "tesseract":
        hboxtl.hide()


def ocr_finished_callback(response):
    "Callback function to be executed when OCR processing is finished."
    finish_tpbar(response)
    # slist.save_session()


def ocr_display_callback(response):
    "Callback function to handle the display of OCR (Optical Character Recognition) results."
    uuid = response.request.args[0]["page"].uuid
    i = slist.find_page_by_uuid(uuid)
    if i is None:
        logger.error("Can't display page with uuid %s: page not found", uuid)
    else:
        page = slist.get_selected_indices()
        if page and i == page[0]:
            create_txt_canvas(slist.data[i][2])


def run_ocr(engine, tesslang, threshold_flag, threshold):
    "Run OCR on a set of pages"
    if engine == "tesseract":
        SETTING["ocr language"] = tesslang

    kwargs = {
        "queued_callback": setup_tpbar,
        "started_callback": update_tpbar,
        "running_callback": update_tpbar,
        "finished_callback": ocr_finished_callback,
        "error_callback": error_callback,
        "display_callback": ocr_display_callback,
        "engine": engine,
        "language": SETTING["ocr language"],
    }
    SETTING["ocr engine"] = engine
    SETTING["threshold-before-ocr"] = threshold_flag
    if threshold_flag:
        SETTING["threshold tool"] = threshold
        kwargs["threshold"] = threshold

    # fill pagelist with filenames
    # depending on which radiobutton is active
    SETTING["Page range"] = windowo.page_range
    pagelist = indices2pages(
        slist.get_page_index(SETTING["Page range"], error_callback)
    )
    if not pagelist:
        return
    kwargs["pages"] = pagelist
    slist.ocr_pages(**kwargs)
    windowo.hide()


def ask_quit():
    "Remove temporary files, note window state, save settings and quit."
    if not scans_saved(
        _("Some pages have not been saved.\nDo you really want to quit?")
    ):
        return False

    # Make sure that we are back in the start directory,
    # otherwise we can't delete the temp dir.
    os.chdir(SETTING["cwd"])

    # Remove temporary files
    for file in glob.glob(session.name + "/*"):
        os.remove(file)
    os.rmdir(session.name)
    # Write window state to settings
    SETTING["window_width"], SETTING["window_height"] = app.window.get_size()
    SETTING["window_x"], SETTING["window_y"] = app.window.get_position()
    SETTING["thumb panel"] = app.window._hpaned.get_position()
    if windows:
        SETTING["scan_window_width"], SETTING["scan_window_height"] = windows.get_size()
        logger.info("Killing Sane thread(s)")
        windows.thread.quit()

    # Write config file
    config.write_config(app.window._configfile, SETTING)
    logger.info("Killing document thread(s)")
    slist.thread.quit()
    logger.debug("Quitting")

    # compress log file if we have xz
    if args.log and dependencies["xz"]:
        exec_command(["xz", "-f", args.log])

    return True


def view_html(_action, _param):
    "Perhaps we should use gtk and mallard for this in the future"
    # Or possibly https://github.com/ultrabug/mkdocs-static-i18n
    # At the moment, we have no translations,
    # but when we do, replace C with locale

    uri = f"/usr/share/help/C/{prog_name}/documentation.html"
    if pathlib.Path(uri).exists():
        uri = GLib.filename_to_uri(uri, None)  # undef => no hostname
    else:
        uri = "http://gscan2pdf.sf.net"

    logger.info("Opening %s via default launcher", uri)
    context = Gio.AppLaunchContext()
    Gio.AppInfo.launch_default_for_uri(uri, context)


def take_snapshot():
    "Update undo/redo buffers before doing something"
    slist.take_snapshot()

    # Unghost Undo/redo
    actions["undo"].set_enabled(True)

    # Check free space in session directory
    df = shutil.disk_usage(session.name)
    if df:
        df = df.free / 1024 / 1024
        logger.debug(
            "Free space in %s (Mb): %s (warning at %s)",
            session.name,
            df,
            SETTING["available-tmp-warning"],
        )
        if df < SETTING["available-tmp-warning"]:
            text = _("%dMb free in %s.") % (df, session.name)
            show_message_dialog(
                parent=app.window,
                message_type="warning",
                buttons=Gtk.ButtonsType.CLOSE,
                text=text,
            )


def undo(_action, _param):
    "Put things back to last snapshot after updating redo buffer"
    logger.info("Undoing")
    slist.undo()

    # Update menus/buttons
    update_uimanager()
    actions["undo"].set_enabled(False)
    actions["redo"].set_enabled(True)


def unundo(_action, _param):
    "Put things back to last snapshot after updating redo buffer"
    logger.info("Redoing")
    slist.unundo()

    # Update menus/buttons
    update_uimanager()
    actions["undo"].set_enabled(True)
    actions["redo"].set_enabled(False)


def register_icon(iconfactory, stock_id, path):
    "Add icons"
    try:
        icon = GdkPixbuf.Pixbuf.new_from_file(path)
        if icon is None:
            logger.warning("Unable to load icon `%s'", path)
        else:
            iconfactory.add(stock_id, Gtk.IconSet.new_from_pixbuf(icon))
    except Exception as err:
        logger.warning("Unable to load icon `%s': %s", path, err)


def mark_pages(pages):
    "marked page list as saved"
    slist.get_model().handler_block(slist.row_changed_signal)
    for p in pages:
        i = slist.find_page_by_uuid(p)
        if i is not None:
            slist.data[i][2].saved = True

    slist.get_model().handler_unblock(slist.row_changed_signal)


def preferences(_action, _param):
    "Preferences dialog"
    global windowr
    if windowr is not None:
        windowr.present()
        return

    windowr = Dialog(
        transient_for=app.window,
        title=_("Preferences"),
        hide_on_delete=True,
    )
    vbox = windowr.get_content_area()

    # Notebook for scan and general options
    notebook = Gtk.Notebook()
    vbox.pack_start(notebook, True, True, 0)
    (
        vbox1,
        cbo,
        blacklist,
        cbcsh,
        cb_batch_flatbed,
        cb_cancel_btw_pages,
        cb_adf_all_pages,
        cb_cache_device_list,
        cb_ignore_duplex,
    ) = _preferences_scan_options(windowr.get_border_width())
    notebook.append_page(vbox1, Gtk.Label(label=_("Scan options")))
    (
        vbox2,
        fileentry,
        cbw,
        cbtz,
        cbtm,
        cbts,
        cbtp,
        tmpentry,
        spinbuttonw,
        spinbuttonb,
        spinbuttond,
        _ocr_function,
        comboo,
        cbv,
        cbb,
        vboxt,
    ) = _preferences_general_options(windowr.get_border_width())
    notebook.append_page(vbox2, Gtk.Label(label=_("General options")))

    def preferences_apply_callback():
        windowr.hide()

        SETTING["auto-open-scan-dialog"] = cbo.get_active()
        try:
            text = blacklist.get_text()
            re.search(text, "dummy_device", re.MULTILINE | re.DOTALL | re.VERBOSE)
        except:
            msg = _("Invalid regex. Try without special characters such as '*'")
            logger.warning(msg)
            show_message_dialog(
                parent=windowr,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=msg,
                store_response=True,
            )
            blacklist.set_text(SETTING["device blacklist"])

        SETTING["device blacklist"] = blacklist.get_text()
        SETTING["cycle sane handle"] = cbcsh.get_active()
        SETTING["allow-batch-flatbed"] = cb_batch_flatbed.get_active()
        SETTING["cancel-between-pages"] = cb_cancel_btw_pages.get_active()
        SETTING["adf-defaults-scan-all-pages"] = cb_adf_all_pages.get_active()
        SETTING["cache-device-list"] = cb_cache_device_list.get_active()
        SETTING["ignore-duplex-capabilities"] = cb_ignore_duplex.get_active()
        SETTING["default filename"] = fileentry.get_text()
        SETTING["restore window"] = cbw.get_active()
        SETTING["use_timezone"] = cbtz.get_active()
        SETTING["use_time"] = cbtm.get_active()
        SETTING["set_timestamp"] = cbts.get_active()
        SETTING["to_png"] = cbtp.get_active()
        SETTING["convert whitespace to underscores"] = cbb.get_active()
        if windows:
            windows.cycle_sane_handle = SETTING["cycle sane handle"]
            windows.cancel_between_pages = SETTING["cancel-between-pages"]
            windows.allow_batch_flatbed = SETTING["allow-batch-flatbed"]
            windows.ignore_duplex_capabilities = SETTING["ignore-duplex-capabilities"]

        if windowi is not None:
            windowi.include_time = SETTING["use_time"]

        SETTING["available-tmp-warning"] = spinbuttonw.get_value()
        SETTING["Blank threshold"] = spinbuttonb.get_value()
        SETTING["Dark threshold"] = spinbuttond.get_value()
        SETTING["OCR output"] = comboo.get_active_index()

        # Store viewer preferences
        SETTING["view files toggle"] = cbv.get_active()
        update_list_user_defined_tools(vboxt, [comboboxudt, windows.comboboxudt])
        tmp = os.path.abspath(os.path.join(session.name, ".."))  # Up a level

        # Expand tildes in the filename
        newdir = get_tmp_dir(
            str(pathlib.Path(tmpentry.get_text()).expanduser()), r"gscan2pdf-\w\w\w\w"
        )
        if newdir != tmp:
            SETTING["TMPDIR"] = newdir
            response = ask_question(
                parent=app.window,
                type="question",
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=_("Changes will only take effect after restarting gscan2pdf.")
                + SPACE
                + _("Restart gscan2pdf now?"),
            )
            if response == Gtk.ResponseType.OK:
                restart()

    windowr.add_actions(
        [("gtk-ok", preferences_apply_callback), ("gtk-cancel", windowr.hide)]
    )
    windowr.show_all()


def _preferences_scan_options(border_width):

    vbox = Gtk.VBox()
    vbox.set_border_width(border_width)
    cbo = Gtk.CheckButton(label=_("Open scanner at program start"))
    cbo.set_tooltip_text(
        _(
            "Automatically open the scan dialog in the background at program start. "
            "This saves time clicking the scan button and waiting for the "
            "program to find the list of scanners"
        )
    )
    if "auto-open-scan-dialog" in SETTING:
        cbo.set_active(SETTING["auto-open-scan-dialog"])

    vbox.pack_start(cbo, True, True, 0)

    # Device blacklist
    hboxb = Gtk.HBox()
    vbox.pack_start(hboxb, False, False, 0)
    label = Gtk.Label(label=_("Device blacklist"))
    hboxb.pack_start(label, False, False, 0)
    blacklist = Gtk.Entry()
    hboxb.add(blacklist)
    hboxb.set_tooltip_text(_("Device blacklist (regular expression)"))
    if "device blacklist" in SETTING and SETTING["device blacklist"] is not None:
        blacklist.set_text(SETTING["device blacklist"])

    # Cycle SANE handle after scan
    cbcsh = Gtk.CheckButton(label=_("Cycle SANE handle after scan"))
    cbcsh.set_tooltip_text(
        _("Some ADFs do not feed out the last page if this is not enabled")
    )
    if "cycle sane handle" in SETTING:
        cbcsh.set_active(SETTING["cycle sane handle"])

    vbox.pack_start(cbcsh, False, False, 0)

    # Allow batch scanning from flatbed
    cb_batch_flatbed = Gtk.CheckButton(label=_("Allow batch scanning from flatbed"))
    cb_batch_flatbed.set_tooltip_text(
        _(
            "If not set, switching to a flatbed scanner will force # pages to "
            "1 and single-sided mode."
        )
    )
    cb_batch_flatbed.set_active(SETTING["allow-batch-flatbed"])
    vbox.pack_start(cb_batch_flatbed, False, False, 0)

    # Ignore duplex capabilities
    cb_ignore_duplex = Gtk.CheckButton(label=_("Ignore duplex capabilities of scanner"))
    cb_ignore_duplex.set_tooltip_text(
        _(
            "If set, any duplex capabilities are ignored, and facing/reverse "
            "widgets are displayed to allow manual interleaving of pages."
        )
    )
    cb_ignore_duplex.set_active(SETTING["ignore-duplex-capabilities"])
    vbox.pack_start(cb_ignore_duplex, False, False, 0)

    # Force new scan job between pages
    cb_cancel_btw_pages = Gtk.CheckButton(label=_("Force new scan job between pages"))
    cb_cancel_btw_pages.set_tooltip_text(
        _(
            "Otherwise, some Brother scanners report out of documents, "
            "despite scanning from flatbed."
        )
    )
    cb_cancel_btw_pages.set_active(SETTING["cancel-between-pages"])
    vbox.pack_start(cb_cancel_btw_pages, False, False, 0)
    cb_cancel_btw_pages.set_sensitive(SETTING["allow-batch-flatbed"])
    cb_batch_flatbed.connect(
        "toggled",
        lambda _: cb_cancel_btw_pages.set_sensitive(cb_batch_flatbed.get_active()),
    )

    # Select num-pages = all on selecting ADF
    cb_adf_all_pages = Gtk.CheckButton(label=_("Select # pages = all on selecting ADF"))
    cb_adf_all_pages.set_tooltip_text(
        _(
            "If this option is enabled, when switching to source=ADF, # pages = all is selected"
        )
    )
    cb_adf_all_pages.set_active(SETTING["adf-defaults-scan-all-pages"])
    vbox.pack_start(cb_adf_all_pages, False, False, 0)

    # Cache device list
    cb_cache_device_list = Gtk.CheckButton(label=_("Cache device list"))
    cb_cache_device_list.set_tooltip_text(
        _(
            "If this option is enabled, opening the scanner is quicker, "
            "as gscan2pdf does not first search for available devices."
        )
        + _(
            "This is only effective if the device names do not change between sessions."
        )
    )
    cb_cache_device_list.set_active(SETTING["cache-device-list"])
    vbox.pack_start(cb_cache_device_list, False, False, 0)

    return (
        vbox,
        cbo,
        blacklist,
        cbcsh,
        cb_batch_flatbed,
        cb_cancel_btw_pages,
        cb_adf_all_pages,
        cb_cache_device_list,
        cb_ignore_duplex,
    )


def _preferences_general_options(border_width):

    vbox = Gtk.VBox()
    vbox.set_border_width(border_width)

    # Restore window setting
    cbw = Gtk.CheckButton(label=_("Restore window settings on startup"))
    cbw.set_active(SETTING["restore window"])
    vbox.pack_start(cbw, True, True, 0)

    # View saved files
    cbv = Gtk.CheckButton(label=_("View files on saving"))
    cbv.set_active(SETTING["view files toggle"])
    vbox.pack_start(cbv, True, True, 0)

    # Default filename
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Default PDF & DjVu filename"))
    hbox.pack_start(label, False, False, 0)
    fileentry = Gtk.Entry()
    fileentry.set_tooltip_text(
        _(
            """strftime codes, e.g.:
%Y	current year

with the following additions:
%Da	author
%De	filename extension
%Dk	keywords
%Ds	subject
%Dt	title

All document date codes use strftime codes with a leading D, e.g.:
%DY	document year
%Dm	document month
%Dd	document day
"""
        )
    )
    hbox.add(fileentry)
    fileentry.set_text(SETTING["default filename"])

    # Replace whitespace in filenames with underscores
    cbb = Gtk.CheckButton.new_with_label(
        _("Replace whitespace in filenames with underscores")
    )
    cbb.set_active(SETTING["convert whitespace to underscores"])
    vbox.pack_start(cbb, True, True, 0)

    # Timezone
    cbtz = Gtk.CheckButton.new_with_label(_("Use timezone from locale"))
    cbtz.set_active(SETTING["use_timezone"])
    vbox.pack_start(cbtz, True, True, 0)

    # Time
    cbtm = Gtk.CheckButton.new_with_label(_("Specify time as well as date"))
    cbtm.set_active(SETTING["use_time"])
    vbox.pack_start(cbtm, True, True, 0)

    # Set file timestamp with metadata
    cbts = Gtk.CheckButton.new_with_label(
        _("Set access and modification times to metadata date")
    )
    cbts.set_active(SETTING["set_timestamp"])
    vbox.pack_start(cbts, True, True, 0)

    # Convert scans from PNM to PNG
    cbtp = Gtk.CheckButton.new_with_label(
        _("Convert scanned images to PNG before further processing")
    )
    cbtp.set_active(SETTING["to_png"])
    vbox.pack_start(cbtp, True, True, 0)

    # Temporary directory settings
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Temporary directory"))
    hbox.pack_start(label, False, False, 0)
    tmpentry = Gtk.Entry()
    hbox.add(tmpentry)
    tmpentry.set_text(os.path.dirname(session.name))
    button = Gtk.Button(label=_("Browse"))

    def choose_temp_dir():
        file_chooser = Gtk.FileChooserDialog(
            title=_("Select temporary directory"),
            parent=windowr,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        file_chooser.set_current_folder(tmpentry.get_text())
        if file_chooser.run() == Gtk.ResponseType.OK:
            tmpentry.set_text(
                get_tmp_dir(file_chooser.get_filename(), r"gscan2pdf-\w\w\w\w")
            )

        file_chooser.destroy()

    button.connect("clicked", choose_temp_dir)
    hbox.pack_end(button, True, True, 0)

    # Available space in temporary directory
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Warn if available space less than (Mb)"))
    hbox.pack_start(label, False, False, 0)
    spinbuttonw = Gtk.SpinButton.new_with_range(0, _100_000MB, 1)
    spinbuttonw.set_value(SETTING["available-tmp-warning"])
    spinbuttonw.set_tooltip_text(
        _(
            "Warn if the available space in the temporary directory is less than this value"
        )
    )
    hbox.add(spinbuttonw)

    # Blank page standard deviation threshold
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Blank threshold"))
    hbox.pack_start(label, False, False, 0)
    spinbuttonb = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
    spinbuttonb.set_value(SETTING["Blank threshold"])
    spinbuttonb.set_tooltip_text(_("Threshold used for selecting blank pages"))
    hbox.add(spinbuttonb)

    # Dark page mean threshold
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Dark threshold"))
    hbox.pack_start(label, False, False, 0)
    spinbuttond = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
    spinbuttond.set_value(SETTING["Dark threshold"])
    spinbuttond.set_tooltip_text(_("Threshold used for selecting dark pages"))
    hbox.add(spinbuttond)

    # OCR output
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("OCR output"))
    hbox.pack_start(label, False, False, 0)
    ocr_function = [
        [
            "replace",
            _("Replace"),
            _("Replace the contents of the text buffer with that from the OCR output."),
        ],
        ["prepend", _("Prepend"), _("Prepend the OCR output to the text buffer.")],
        ["append", _("Append"), _("Append the OCR output to the text buffer.")],
    ]
    comboo = ComboBoxText(data=ocr_function)
    comboo.set_active_index(SETTING["OCR output"])
    hbox.pack_end(comboo, True, True, 0)

    # Manage user-defined tools
    frame = Gtk.Frame(label=_("Manage user-defined tools"))
    vbox.pack_start(frame, True, True, 0)
    vboxt = Gtk.VBox()
    vboxt.set_border_width(border_width)
    frame.add(vboxt)
    for tool in SETTING["user_defined_tools"]:
        add_user_defined_tool_entry(vboxt, [], tool)

    abutton = Gtk.Button()
    abutton.set_image(Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
    vboxt.pack_start(abutton, True, True, 0)

    def clicked_add_udt(_action):
        add_user_defined_tool_entry(
            vboxt, [comboboxudt, windows.comboboxudt], "my-tool %i %o"
        )
        vboxt.reorder_child(abutton, EMPTY_LIST)
        update_list_user_defined_tools(vboxt, [comboboxudt, windows.comboboxudt])

    abutton.connect("clicked", clicked_add_udt)
    return (
        vbox,
        fileentry,
        cbw,
        cbtz,
        cbtm,
        cbts,
        cbtp,
        tmpentry,
        spinbuttonw,
        spinbuttonb,
        spinbuttond,
        ocr_function,
        comboo,
        cbv,
        cbb,
        vboxt,
    )


def _cb_array_append(combobox_array, text):

    for combobox in combobox_array:
        if combobox is not None:
            combobox.append_text(text)


def update_list_user_defined_tools(vbox, combobox_array):
    "Update list of user-defined tools"
    tools = []
    for combobox in combobox_array:
        if combobox is not None:
            while combobox.get_num_rows() > 0:
                combobox.remove(0)

    for hbox in vbox.get_children():
        if isinstance(hbox, Gtk.HBox):
            for widget in hbox.get_children():
                if isinstance(widget, Gtk.Entry):
                    text = widget.get_text()
                    tools.append(text)
                    _cb_array_append(combobox_array, text)

    SETTING["user_defined_tools"] = tools
    update_post_save_hooks()
    for combobox in combobox_array:
        if combobox is not None:
            combobox.set_active_by_text(SETTING["current_udt"])


def add_user_defined_tool_entry(vbox, combobox_array, tool):
    "Add user-defined tool entry"
    _cb_array_append(combobox_array, tool)
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    entry = Gtk.Entry()
    entry.set_text(tool)
    entry.set_tooltip_text(
        _(
            """Use %i and %o for the input and output filenames respectively,
or a single %i if the image is to be modified in-place.

The other variable available is:
%r resolution"""
        )
    )
    hbox.pack_start(entry, True, True, 0)
    button = Gtk.Button.new_with_mnemonic(label=_("_Delete"))

    def delete_udt():
        hbox.destroy()
        update_list_user_defined_tools(vbox, combobox_array)

    button.connect("clicked", delete_udt)
    hbox.pack_end(button, False, False, 0)
    hbox.show_all()


def update_post_save_hooks():
    "Updates the post-save hooks"
    if windowi is not None:
        if hasattr(windowi, "comboboxpsh"):

            # empty combobox
            for _i in range(1, windowi.comboboxpsh.get_num_rows() + 1):
                windowi.comboboxpsh.remove(0)

        else:
            # create it
            windowi.comboboxpsh = ComboBoxText()

        # fill it again
        for tool in SETTING["user_defined_tools"]:
            if not re.search(r"%o", tool, re.MULTILINE | re.DOTALL | re.VERBOSE):
                windowi.comboboxpsh.append_text(tool)

        windowi.comboboxpsh.set_active_by_text(SETTING["current_psh"])


def properties(_action, _param):
    "Display and manage the properties dialog for setting X and Y resolution."
    global windowp
    if windowp is not None:
        windowp.present()
        return

    windowp = Dialog(
        transient_for=app.window,
        title=_("Properties"),
        hide_on_delete=True,
    )
    vbox = windowp.get_content_area()
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=d_sane("X Resolution"))
    hbox.pack_start(label, False, False, 0)
    xspinbutton = Gtk.SpinButton.new_with_range(0, MAX_DPI, 1)
    xspinbutton.set_digits(1)
    hbox.pack_start(xspinbutton, True, True, 0)
    label = Gtk.Label(label=_("dpi"))
    hbox.pack_end(label, False, False, 0)
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=d_sane("Y Resolution"))
    hbox.pack_start(label, False, False, 0)
    yspinbutton = Gtk.SpinButton.new_with_range(0, MAX_DPI, 1)
    yspinbutton.set_digits(1)
    hbox.pack_start(yspinbutton, True, True, 0)
    label = Gtk.Label(label=_("dpi"))
    hbox.pack_end(label, False, False, 0)
    xresolution, yresolution = get_selected_properties()
    logger.debug("get_selected_properties returned %s,%s", xresolution, yresolution)
    xspinbutton.set_value(xresolution)
    yspinbutton.set_value(yresolution)

    def selection_changed_callback():
        xresolution, yresolution = get_selected_properties()
        logger.debug("get_selected_properties returned %s,%s", xresolution, yresolution)
        xspinbutton.set_value(xresolution)
        yspinbutton.set_value(yresolution)

    slist.get_selection().connect("changed", selection_changed_callback)

    def properties_apply_callback():
        windowp.hide()
        xresolution = xspinbutton.get_value()
        yresolution = yspinbutton.get_value()
        slist.get_model().handler_block(slist.row_changed_signal)
        for i in slist.get_selected_indices():
            logger.debug(
                "setting resolution %s,%s for page %s",
                xresolution,
                yresolution,
                slist.data[i][0],
            )
            slist.data[i][2].resolution = xresolution, yresolution, "PixelsPerInch"

        slist.get_model().handler_unblock(slist.row_changed_signal)

    windowp.add_actions(
        [("gtk-ok", properties_apply_callback), ("gtk-cancel", windowp.hide)]
    )
    windowp.show_all()


def get_selected_properties():
    "Helper function for properties()"
    page = slist.get_selected_indices()
    xresolution = None
    yresolution = None
    if len(page) > 0:
        i = page.pop(0)
        xresolution, yresolution, _units = slist.data[i][2].resolution
        logger.debug(
            "Page %s has resolutions %s,%s", slist.data[i][0], xresolution, yresolution
        )

    for i in page:
        if slist.data[i][2].resolution[0] != xresolution:
            xresolution = None
            break

    for i in page:
        if slist.data[i][2].resolution[0] != yresolution:
            yresolution = None
            break

    # round the value to a sensible number of significant figures
    return xresolution, yresolution


def ask_question(**kwargs):
    "Helper function to display a message dialog, wait for a response, and return it"

    # replace any numbers with metacharacters to compare to filter
    text = filter_message(kwargs["text"])
    if response_stored(text, SETTING["message"]):
        logger.debug(
            f"Skipped MessageDialog with '{kwargs['text']}', "
            + f"automatically replying '{SETTING['message'][text]['response']}'"
        )
        return SETTING["message"][text]["response"]

    cb = None
    dialog = Gtk.MessageDialog(
        parent=kwargs["parent"],
        modal=True,
        destroy_with_parent=True,
        message_type=kwargs["type"],
        buttons=kwargs["buttons"],
        text=kwargs["text"],
    )
    logger.debug("Displayed MessageDialog with '%s'", kwargs["text"])
    if "store-response" in kwargs:
        cb = Gtk.CheckButton.new_with_label(_("Don't show this message again"))
        dialog.get_message_area().add(cb)

    if "default-response" in kwargs:
        dialog.set_default_response(kwargs["default-response"])

    dialog.show_all()
    response = dialog.run()
    dialog.destroy()
    if "store-response" in kwargs and cb.get_active():
        flag = True
        if kwargs["stored-responses"]:
            flag = False
            for i in kwargs["stored-responses"]:
                if i == response:
                    flag = True
                    break

        if flag:
            SETTING["message"][text]["response"] = response

    logger.debug("Replied '%s'", response)
    return response


def show_message_dialog(**options):
    "Displays a message dialog with the given options."
    global message_dialog
    if message_dialog is None:
        message_dialog = MultipleMessage(
            title=_("Messages"), transient_for=options["parent"]
        )
        message_dialog.set_default_size(
            SETTING["message_window_width"], SETTING["message_window_height"]
        )

    options["responses"] = SETTING["message"]
    message_dialog.add_message(options)
    response = None
    if message_dialog.grid_rows > 1:
        message_dialog.show_all()
        response = message_dialog.run()

    if message_dialog is not None:  # could be undefined for multiple calls
        message_dialog.store_responses(response, SETTING["message"])
        SETTING["message_window_width"], SETTING["message_window_height"] = (
            message_dialog.get_size()
        )
        message_dialog.destroy()
        message_dialog = None


def recursive_slurp(files):
    """
    Recursively processes a list of files and directories, logging the contents
    of each file.
    """
    for file in files:
        if os.path.isdir(file):
            recursive_slurp(glob.glob(f"{file}/*"))
        else:
            output = slurp(file)
            if output is not None:
                output = output.rstrip()
                logger.info(output)


def quit_app(_action, _param):
    "Handle the quit action for the application."
    if ask_quit():
        app.quit()


def select_odd(_action, _param):
    "Selects odd-numbered pages"
    select_odd_even(0)


def select_even(_action, _param):
    "Selects even-numbered pages"
    select_odd_even(1)


def zoom_100(_action, _param):
    "Sets the zoom level of the view to 100%."
    view.set_zoom(1.0)


def zoom_to_fit(_action, _param):
    "Adjusts the view to fit the content within the visible area."
    view.zoom_to_fit()


def zoom_in(_action, _param):
    "Zooms in the current view"
    view.zoom_in()


def zoom_out(_action, _param):
    "Zooms out the current view"
    view.zoom_out()


def rotate_90(_action, _param):
    "Rotates the selected pages by 90 degrees"
    rotate(_90_DEGREES, indices2pages(slist.get_selected_indices()))


def rotate_180(_action, _param):
    "Rotates the selected pages by 180 degrees"
    rotate(_180_DEGREES, indices2pages(slist.get_selected_indices()))


def rotate_270(_action, _param):
    "Rotates the selected pages by 270 degrees"
    rotate(_270_DEGREES, indices2pages(slist.get_selected_indices()))


class ApplicationWindow(Gtk.ApplicationWindow):
    "ApplicationWindow class"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._configfile = None
        self._current_page = None
        self._current_ocr_bbox = None
        self._current_ann_bbox = None
        self._prevent_image_tool_update = False
        self._pre_flight()
        self.print_settings = None
        self.renumber_dialog = None
        self.connect("delete-event", lambda w, e: not ask_quit())

        def window_state_event_callback(_w, event):
            "Note when the window is maximised or not"
            SETTING["window_maximize"] = bool(
                event.new_window_state & Gdk.WindowState.MAXIMIZED
            )

        self.connect("window-state-event", window_state_event_callback)

        # If defined in the config file, set the window state, size and position
        if SETTING["restore window"]:
            self.set_default_size(SETTING["window_width"], SETTING["window_height"])
            if "window_x" in SETTING and "window_y" in SETTING:
                self.move(SETTING["window_x"], SETTING["window_y"])

            if SETTING["window_maximize"]:
                self.maximize()

        try:
            self.set_icon_from_file(f"{self.get_application()._iconpath}/gscan2pdf.svg")
        except Exception as e:
            logger.warning(
                "Unable to load icon `%s/gscan2pdf.svg': %s",
                self.get_application()._iconpath,
                str(e),
            )

        self._thumb_popup = builder.get_object("thumb_popup")

        # app.add_window(window)
        self.populate_main_window()

    def _pre_flight(self):
        """
        Pre-flight initialization function that sets up global variables,
        captures warnings, reads configuration, logs system information,
        and initializes various components.
        """
        global args
        global SETTING
        args = parse_arguments()

        # Catch and log Python warnings
        logging.captureWarnings(True)

        # Suppress Warning: g_value_get_int: assertion 'G_VALUE_HOLDS_INT (value)' failed
        # from dialog.save.Save._meta_datetime_widget.set_text()
        # https://bugzilla.gnome.org/show_bug.cgi?id=708676
        warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

        SETTING = self._read_config()
        if SETTING["cwd"] is None:
            SETTING["cwd"] = os.getcwd()
        SETTING["version"] = VERSION

        logger.info("Operating system: %s", sys.platform)
        if sys.platform == "linux":
            recursive_slurp(glob.glob("/etc/*-release"))

        logger.info("Python version %s", sys.version_info)
        logger.info("GLib VERSION_MIN_REQUIRED %s", GLib.VERSION_MIN_REQUIRED)
        logger.info("GLib._version %s", GLib._version)
        logger.info("gi.__version__ %s", gi.__version__)
        logger.info("gi.version_info %s", gi.version_info)
        logger.info("Gtk._version %s", Gtk._version)
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

        # add the actions to the window that have window-classed callbacks
        app.add_action(actions["tooltype"])
        app.add_action(actions["viewtype"])

        # connect the action callback for tools and view
        actions["tooltype"].connect("activate", self._change_image_tool_cb)
        actions["viewtype"].connect("activate", self._change_view_cb)

        # initialise image control tool radio button setting
        self._change_image_tool_cb(
            actions["tooltype"], GLib.Variant("s", SETTING["image_control_tool"])
        )
        builder.get_object("context_" + SETTING["image_control_tool"]).set_active(True)

    def _read_config(self):
        "Read the configuration file"
        # config files: XDG_CONFIG_HOME/gscan2pdfrc or HOME/.config/gscan2pdfrc
        rcdir = (
            os.environ["XDG_CONFIG_HOME"]
            if "XDG_CONFIG_HOME" in os.environ
            else f"{os.environ['HOME']}/.config"
        )
        self._configfile = f"{rcdir}/{prog_name}rc"
        cfg = config.read_config(self._configfile)
        config.add_defaults(cfg)
        config.remove_invalid_paper(cfg["Paper"])
        return cfg

    def on_maximize_toggle(self, action, value):
        "Toggles the maximized state of the window"
        action.set_state(value)
        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()

    def populate_main_window(self):
        """
        Populates the main window with various UI components and sets up necessary callbacks.

        This method performs the following tasks:
        - Creates the main vertical box container and adds it to the window.
        - Sets up a SimpleList for document handling and updates its paper sizes.
        - Creates a temporary directory for dependency checks.
        - Creates and packs the toolbar into the main vertical box.
        - Sets up a horizontal pane for thumbnails and detail view.
        - Configures a scrolled window for thumbnails and connects drag and click events.
        - Sets up a notebook and split panes for detail view and OCR output.
        - Initializes the ImageView for detail view and connects various event callbacks.
        - Sets up Goo.Canvas for text and annotation layers with zoom and offset change callbacks.
        - Configures the OCR text editing interface with various buttons and their callbacks.
        - Configures the annotation editing interface with various buttons and their callbacks.
        - Sets up the callback for list selection to update the detail view.
        - Connects key press events to handle delete key functionality.
        - Sets the current working directory if defined in the config file.
        - Initializes the Unpaper tool with specified options.
        - Updates the UI manager and shows all components.
        - Adds progress bars below the window.
        - Opens the scan dialog in the background if auto-open is enabled.
        - Handles command line options for importing files.
        """
        global slist
        main_vbox = Gtk.VBox()
        self.add(main_vbox)

        # Set up a SimpleList
        slist = Document()

        # Update list in Document so that it can be used by get_resolution()
        slist.set_paper_sizes(SETTING["Paper"])

        # The temp directory has to be available before we start checking for
        # dependencies in order to be used for the pdftk check.
        create_temp_directory()

        # Create the toolbar
        main_vbox.pack_start(self.create_toolbar(), False, False, 0)

        # HPaned for thumbnails and detail view
        self._hpaned = Gtk.HPaned()
        self._hpaned.set_position(SETTING["thumb panel"])
        main_vbox.pack_start(self._hpaned, True, True, 0)

        # Scrolled window for thumbnails
        scwin_thumbs = Gtk.ScrolledWindow()

        # resize = FALSE to stop the panel expanding on being resized
        # (Debian #507032)
        self._hpaned.pack1(scwin_thumbs, False, True)
        scwin_thumbs.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scwin_thumbs.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        # If dragged below the bottom of the window, scroll it.
        slist.connect("drag-motion", drag_motion_callback)

        # Set up callback for right mouse clicks.
        slist.connect("button-press-event", self.handle_clicks)
        slist.connect("button-release-event", self.handle_clicks)
        scwin_thumbs.add(slist)

        # Notebook, split panes for detail view and OCR output
        self._vnotebook = Gtk.Notebook()
        self._hpanei = Gtk.HPaned()
        self._vpanei = Gtk.VPaned()
        self._hpanei.show()
        self._vpanei.show()

        # ImageView for detail view
        global view
        view = ImageView()
        if SETTING["image_control_tool"] == SELECTOR_TOOL:
            view.set_tool(Selector(view))

        elif SETTING["image_control_tool"] == DRAGGER_TOOL:
            view.set_tool(Dragger(view))

        else:
            view.set_tool(SelectorDragger(view))

        view.connect("button-press-event", self.handle_clicks)
        view.connect("button-release-event", self.handle_clicks)

        def view_zoom_changed_callback(_view, zoom):
            if canvas is not None:
                canvas.handler_block(canvas.zoom_changed_signal)
                canvas.set_scale(zoom)
                canvas.handler_unblock(canvas.zoom_changed_signal)

        view.zoom_changed_signal = view.connect(
            "zoom-changed", view_zoom_changed_callback
        )

        def view_offset_changed_callback(_view, x, y):
            if canvas is not None:
                canvas.handler_block(canvas.offset_changed_signal)
                canvas.set_offset(x, y)
                canvas.handler_unblock(canvas.offset_changed_signal)

        view.offset_changed_signal = view.connect(
            "offset-changed", view_offset_changed_callback
        )

        def view_selection_changed_callback(_view, sel):
            "Callback if the selection changes"
            # copy required here because somehow the garbage collection
            # destroys the Gdk.Rectangle too early and afterwards, the
            # contents are corrupt.
            SETTING["selection"] = sel.copy()
            if sel is not None and windowc is not None:
                windowc.selection = SETTING["selection"]

        view.selection_changed_signal = view.connect(
            "selection-changed", view_selection_changed_callback
        )

        # Goo.Canvas for text layer
        global canvas
        canvas = Canvas()

        def text_zoom_changed_callback(canvas, _zoom):
            view.handler_block(view.zoom_changed_signal)
            view.set_zoom(canvas.get_scale())
            view.handler_unblock(view.zoom_changed_signal)

        canvas.zoom_changed_signal = canvas.connect(
            "zoom-changed", text_zoom_changed_callback
        )

        def text_offset_changed_callback():
            view.handler_block(view.offset_changed_signal)
            offset = canvas.get_offset()
            view.set_offset(offset["x"], offset["y"])
            view.handler_unblock(view.offset_changed_signal)

        canvas.offset_changed_signal = canvas.connect(
            "offset-changed", text_offset_changed_callback
        )

        # Goo.Canvas for annotation layer
        global a_canvas
        a_canvas = Canvas()

        def ann_zoom_changed_callback():
            view.handler_block(view.zoom_changed_signal)
            view.set_zoom(a_canvas.get_scale())
            view.handler_unblock(view.zoom_changed_signal)

        a_canvas.zoom_changed_signal = a_canvas.connect(
            "zoom-changed", ann_zoom_changed_callback
        )

        def ann_offset_changed_callback():
            view.handler_block(view.offset_changed_signal)
            offset = a_canvas.get_offset()
            view.set_offset(offset["x"], offset["y"])
            view.handler_unblock(view.offset_changed_signal)

        a_canvas.offset_changed_signal = a_canvas.connect(
            "offset-changed", ann_offset_changed_callback
        )

        # split panes for detail view/text layer canvas and text layer dialog
        self._vpaned = Gtk.VPaned()
        self._hpaned.pack2(self._vpaned, True, True)
        self._vpaned.show()
        ocr_text_hbox = Gtk.HBox()
        edit_vbox = Gtk.HBox()
        self._vpaned.pack2(edit_vbox, False, True)
        edit_vbox.pack_start(ocr_text_hbox, True, True, 0)
        ocr_textview = Gtk.TextView()
        ocr_textview.set_tooltip_text(_("Text layer"))
        ocr_textbuffer = ocr_textview.get_buffer()
        ocr_text_fbutton = Gtk.Button()
        ocr_text_fbutton.set_image(
            Gtk.Image.new_from_icon_name("go-first", Gtk.IconSize.BUTTON)
        )
        ocr_text_fbutton.set_tooltip_text(_("Go to least confident text"))
        ocr_text_fbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(canvas.get_first_bbox())
        )
        ocr_text_pbutton = Gtk.Button()
        ocr_text_pbutton.set_image(
            Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
        )
        ocr_text_pbutton.set_tooltip_text(_("Go to previous text"))
        ocr_text_pbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(canvas.get_previous_bbox())
        )
        ocr_index = [
            [
                "confidence",
                _("Sort by confidence"),
                _("Sort OCR text boxes by confidence."),
            ],
            ["position", _("Sort by position"), _("Sort OCR text boxes by position.")],
        ]
        ocr_text_scmbx = ComboBoxText(data=ocr_index)
        ocr_text_scmbx.set_tooltip_text(_("Select sort method for OCR boxes"))

        def changed_text_sort_method(_arg):
            if ocr_index[ocr_text_scmbx.get_active()][0] == "confidence":
                canvas.sort_by_confidence()
            else:
                canvas.sort_by_position()

        ocr_text_scmbx.connect("changed", changed_text_sort_method)
        ocr_text_scmbx.set_active(0)
        ocr_text_nbutton = Gtk.Button()
        ocr_text_nbutton.set_image(
            Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
        )
        ocr_text_nbutton.set_tooltip_text(_("Go to next text"))
        ocr_text_nbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(canvas.get_next_bbox())
        )
        ocr_text_lbutton = Gtk.Button()
        ocr_text_lbutton.set_image(
            Gtk.Image.new_from_icon_name("go-last", Gtk.IconSize.BUTTON)
        )
        ocr_text_lbutton.set_tooltip_text(_("Go to most confident text"))
        ocr_text_lbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(canvas.get_last_bbox())
        )
        ocr_text_obutton = Gtk.Button.new_with_mnemonic(label=_("_OK"))
        ocr_text_obutton.set_tooltip_text(_("Accept corrections"))

        def ocr_text_button_clicked(_widget):
            take_snapshot()
            text = ocr_textbuffer.text
            logger.info("Corrected '%s'->'%s'", self._current_ocr_bbox.text, text)
            self._current_ocr_bbox.update_box(text, view.get_selection())
            self._current_page.import_hocr(canvas.hocr())
            self.edit_ocr_text(self._current_ocr_bbox)

        ocr_text_obutton.connect("clicked", ocr_text_button_clicked)
        ocr_text_cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        ocr_text_cbutton.set_tooltip_text(_("Cancel corrections"))
        ocr_text_cbutton.connect("clicked", lambda _: ocr_text_hbox.hide())
        ocr_text_ubutton = Gtk.Button.new_with_mnemonic(label=_("_Copy"))
        ocr_text_ubutton.set_tooltip_text(_("Duplicate text"))

        def ocr_text_copy(_widget):
            self._current_ocr_bbox = canvas.add_box(
                text=ocr_textbuffer.text, bbox=view.get_selection()
            )
            self._current_page.import_hocr(canvas.hocr())
            self.edit_ocr_text(self._current_ocr_bbox)

        ocr_text_ubutton.connect("clicked", ocr_text_copy)
        ocr_text_abutton = Gtk.Button()
        ocr_text_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        )
        ocr_text_abutton.set_tooltip_text(_("Add text"))

        def ocr_text_add(_widget):
            take_snapshot()
            text = ocr_textbuffer.text
            if (text is None) or text == EMPTY:
                text = _("my-new-word")

            # If we don't yet have a canvas, create one
            selection = view.get_selection()
            if hasattr(self._current_page, "text_layer"):
                logger.info("Added '%s'", text)
                self._current_ocr_bbox = canvas.add_box(
                    text=text, bbox=view.get_selection()
                )
                self._current_page.import_hocr(canvas.hocr())
                self.edit_ocr_text(self._current_ocr_bbox)
            else:
                logger.info("Creating new text layer with '%s'", text)
                self._current_page.text_layer = (
                    '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},'
                    '{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]'
                    % (
                        self._current_page["width"],
                        self._current_page["height"],
                        selection["x"],
                        selection["y"],
                        selection["x"] + selection["width"],
                        selection["y"] + selection["height"],
                        text,
                    )
                )

                def ocr_new_page(_widget):
                    self._current_ocr_bbox = canvas.get_first_bbox()
                    self.edit_ocr_text(self._current_ocr_bbox)

                create_txt_canvas(self._current_page, ocr_new_page)

        ocr_text_abutton.connect("clicked", ocr_text_add)
        ocr_text_dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        ocr_text_dbutton.set_tooltip_text(_("Delete text"))

        def ocr_text_delete(_widget):
            self._current_ocr_bbox.delete_box()
            self._current_page.import_hocr(canvas.hocr())
            self.edit_ocr_text(canvas.get_current_bbox())

        ocr_text_dbutton.connect("clicked", ocr_text_delete)
        ocr_text_hbox.pack_start(ocr_text_fbutton, False, False, 0)
        ocr_text_hbox.pack_start(ocr_text_pbutton, False, False, 0)
        ocr_text_hbox.pack_start(ocr_text_scmbx, False, False, 0)
        ocr_text_hbox.pack_start(ocr_text_nbutton, False, False, 0)
        ocr_text_hbox.pack_start(ocr_text_lbutton, False, False, 0)
        ocr_text_hbox.pack_start(ocr_textview, False, False, 0)
        ocr_text_hbox.pack_end(ocr_text_dbutton, False, False, 0)
        ocr_text_hbox.pack_end(ocr_text_cbutton, False, False, 0)
        ocr_text_hbox.pack_end(ocr_text_obutton, False, False, 0)
        ocr_text_hbox.pack_end(ocr_text_ubutton, False, False, 0)
        ocr_text_hbox.pack_end(ocr_text_abutton, False, False, 0)

        # split panes for detail view/text layer canvas and text layer dialog
        ann_hbox = Gtk.HBox()
        edit_vbox.pack_start(ann_hbox, True, True, 0)
        ann_textview = Gtk.TextView()
        ann_textview.set_tooltip_text(_("Annotations"))
        ann_textbuffer = ann_textview.get_buffer()
        ann_obutton = Gtk.Button.new_with_mnemonic(label=_("_Ok"))
        ann_obutton.set_tooltip_text(_("Accept corrections"))

        def ann_text_ok(_widget):
            text = ann_textbuffer.text
            logger.info("Corrected '%s'->'%s'", self._current_ann_bbox.text, text)
            self._current_ann_bbox.update_box(text, view.get_selection())
            self._current_page.import_annotations(a_canvas.hocr())
            self.edit_annotation(self._current_ann_bbox)

        ann_obutton.connect("clicked", ann_text_ok)
        ann_cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        ann_cbutton.set_tooltip_text(_("Cancel corrections"))
        ann_cbutton.connect("clicked", ann_hbox.hide)
        ann_abutton = Gtk.Button()
        ann_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        )
        ann_abutton.set_tooltip_text(_("Add annotation"))

        def ann_text_new(_widget):
            text = ann_textbuffer.text
            if text is None or text == EMPTY:
                text = _("my-new-annotation")

            # If we don't yet have a canvas, create one
            selection = view.get_selection()
            if hasattr(self._current_page, "text_layer"):
                logger.info("Added '%s'", ann_textbuffer.text)
                self._current_ann_bbox = a_canvas.add_box(
                    text=text, bbox=view.get_selection()
                )
                self._current_page.import_annotations(a_canvas.hocr())
                self.edit_annotation(self._current_ann_bbox)
            else:
                logger.info("Creating new annotation canvas with '%s'", text)
                self._current_page["annotations"] = (
                    '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},'
                    '{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]'
                    % (
                        self._current_page["width"],
                        self._current_page["height"],
                        selection["x"],
                        selection["y"],
                        selection["x"] + selection["width"],
                        selection["y"] + selection["height"],
                        text,
                    )
                )

                def ann_text_new_page(_widget):
                    self._current_ann_bbox = a_canvas.get_first_bbox()
                    self.edit_annotation(self._current_ann_bbox)

                create_ann_canvas(self._current_page, ann_text_new_page)

        ann_abutton.connect("clicked", ann_text_new)
        ann_dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        ann_dbutton.set_tooltip_text(_("Delete annotation"))

        def ann_text_delete(_widget):
            self._current_ann_bbox.delete_box()
            self._current_page.import_hocr(a_canvas.hocr())
            self.edit_annotation(canvas.get_bbox_by_index())

        ann_dbutton.connect("clicked", ann_text_delete)
        ann_hbox.pack_start(ann_textview, False, False, 0)
        ann_hbox.pack_end(ann_dbutton, False, False, 0)
        ann_hbox.pack_end(ann_cbutton, False, False, 0)
        ann_hbox.pack_end(ann_obutton, False, False, 0)
        ann_hbox.pack_end(ann_abutton, False, False, 0)
        self._pack_viewer_tools()

        # Set up call back for list selection to update detail view
        slist.selection_changed_signal = slist.get_selection().connect(
            "changed", selection_changed_callback
        )

        # Without these, the imageviewer and page list steal -/+/ctrl x/c/v keys
        # from the OCR textview
        self.connect("key-press-event", Gtk.Window.propagate_key_event)
        self.connect("key-release-event", Gtk.Window.propagate_key_event)

        def on_key_press(_widget, event):

            # Let the keypress propagate
            if event.keyval != Gdk.KEY_Delete:
                return Gdk.EVENT_PROPAGATE
            delete_selection(None, None)
            return Gdk.EVENT_STOP

        # _after ensures that Editables get first bite
        self.connect_after("key-press-event", on_key_press)

        # If defined in the config file, set the current directory
        if "cwd" not in SETTING:
            SETTING["cwd"] = os.getcwd()
        global unpaper
        unpaper = Unpaper(SETTING["unpaper options"])
        update_uimanager()
        self.show_all()

        # Progress bars below window
        phbox = Gtk.HBox()
        main_vbox.pack_end(phbox, False, False, 0)
        phbox.show()
        self._shbox = Gtk.HBox()
        phbox.add(self._shbox)
        self._spbar = Gtk.ProgressBar()
        self._spbar.set_show_text(True)
        self._shbox.add(self._spbar)
        global scbutton
        scbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        self._shbox.pack_end(scbutton, False, False, 0)
        global thbox
        thbox = Gtk.HBox()
        phbox.add(thbox)
        global tpbar
        tpbar = Gtk.ProgressBar()
        tpbar.set_show_text(True)
        thbox.add(tpbar)
        global tcbutton
        tcbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        thbox.pack_end(tcbutton, False, False, 0)
        ocr_text_hbox.show()
        ann_hbox.hide()

        # Open scan dialog in background
        if SETTING["auto-open-scan-dialog"]:
            scan_dialog(None, None, True)

        # Deal with --import command line option
        if args.import_files is not None:
            import_files(args.import_files)
        if args.import_all is not None:
            import_files(args.import_all, True)

    def create_toolbar(self):
        "Create the menu bar, initialize its menus, and return the menu bar"

        # Check for presence of various packages
        check_dependencies()

        # Ghost save image item if imagemagick not available
        msg = EMPTY
        if not dependencies["imagemagick"]:
            msg += _("Save image and Save as PDF both require imagemagick\n")

        # Ghost save image item if libtiff not available
        if not dependencies["libtiff"]:
            msg += _("Save image requires libtiff\n")

        # Ghost djvu item if cjb2 not available
        if not dependencies["djvu"]:
            msg += _("Save as DjVu requires djvulibre-bin\n")

        # Ghost email item if xdg-email not available
        if not dependencies["xdg"]:
            msg += _("Email as PDF requires xdg-email\n")

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
            actions[action].set_enabled(False)
        # uimanager.get_widget('/MenuBar/Tools/User-defined').set_sensitive(False)

        if not dependencies["unpaper"]:
            msg += _("unpaper missing\n")

        dependencies["ocr"] = dependencies["tesseract"]
        if not dependencies["ocr"]:
            msg += _("OCR requires tesseract\n")

        if dependencies["tesseract"]:
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

        if not dependencies["pdftk"]:
            msg += _("PDF encryption requires pdftk\n")

        # Put up warning if needed
        if msg != EMPTY:
            msg = _("Warning: missing packages") + f"\n{msg}"
            show_message_dialog(
                parent=self,
                message_type="warning",
                buttons=Gtk.ButtonsType.OK,
                text=msg,
                store_response=True,
            )

        # extract the toolbar
        toolbar = builder.get_object("toolbar")

        # turn off labels
        settings = toolbar.get_settings()
        settings.gtk_toolbar_style = "icons"  # only icons
        return toolbar

    def _pack_viewer_tools(self):
        "Pack widgets according to viewer_tools"
        if SETTING["viewer_tools"] == "tabbed":
            self._vnotebook.append_page(view, Gtk.Label(label=_("Image")))
            self._vnotebook.append_page(canvas, Gtk.Label(label=_("Text layer")))
            self._vnotebook.append_page(a_canvas, Gtk.Label(label=_("Annotations")))
            self._vpaned.pack1(self._vnotebook, True, True)
            self._vnotebook.show_all()
        elif SETTING["viewer_tools"] == "horizontal":
            self._hpanei.pack1(view, True, True)
            self._hpanei.pack2(canvas, True, True)
            if a_canvas.get_parent():
                self._vnotebook.remove(a_canvas)
            self._vpaned.pack1(self._hpanei, True, True)
        else:  # vertical
            self._vpanei.pack1(view, True, True)
            self._vpanei.pack2(canvas, True, True)
            if a_canvas.get_parent():
                self._vnotebook.remove(a_canvas)
            self._vpaned.pack1(self._vpanei, True, True)

    def handle_clicks(self, widget, event):
        "Handle right-clicks"
        if event.button == 3:  # RIGHT_MOUSE_BUTTON
            if isinstance(widget, ImageView):  # main image
                detail_popup.show_all()
                detail_popup.popup_at_pointer(event)
            else:  # Thumbnail simplelist
                SETTING["Page range"] = "selected"
                self._thumb_popup.show_all()
                self._thumb_popup.popup_at_pointer(event)

            # block event propagation
            return True

        # allow event propagation
        return False

    def _change_image_tool_cb(self, action, value):
        "Callback for tool-changed signal ImageView"

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
        button = builder.get_object(f"context_{value}")
        button.set_active(True)
        self._prevent_image_tool_update = False

        if view:  # could be undefined at application start
            tool = Selector(view)
            if value == "dragger":
                tool = Dragger(view)
            elif value == "selectordragger":
                tool = SelectorDragger(view)
            view.set_tool(tool)
            if value in ["selector", "selectordragger"] and "selection" in SETTING:
                view.handler_block(view.selection_changed_signal)
                view.set_selection(SETTING["selection"])
                view.handler_unblock(view.selection_changed_signal)

        SETTING["image_control_tool"] = value

    def _change_view_cb(self, action, parameter):
        "Callback to switch between tabbed and split views"
        action.set_state(parameter)

        # SETTING["viewer_tools"] still has old value
        if SETTING["viewer_tools"] == "tabbed":
            self._vpaned.remove(self._vnotebook)
            self._vnotebook.remove(view)
            self._vnotebook.remove(canvas)
        elif SETTING["viewer_tools"] == "horizontal":
            self._vpaned.remove(self._hpanei)
            self._hpanei.remove(view)
            self._hpanei.remove(canvas)
        else:  # vertical
            self._vpaned.remove(self._vpanei)
            self._vpanei.remove(view)
            self._vpanei.remove(canvas)
            self._vpanei.remove(a_canvas)

        SETTING["viewer_tools"] = parameter.get_string()
        self._pack_viewer_tools()

    def edit_ocr_text(self, widget, _target=None, ev=None, bbox=None):
        "Edit OCR text"
        if not ev:
            bbox = widget

        if bbox is None:
            return

        self._current_ocr_bbox = bbox
        ocr_textbuffer.text = bbox.text
        ocr_text_hbox.show_all()
        view.set_selection(bbox.bbox)
        view.set_zoom_to_fit(False)
        view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            canvas.set_index_by_bbox(bbox)

    def edit_annotation(self, widget, _target=None, ev=None, bbox=None):
        "Edit annotation"
        if not ev:
            bbox = widget

        self._current_ann_bbox = bbox
        ann_textbuffer.text = bbox.text
        ann_hbox.show_all()
        view.set_selection(bbox.bbox)
        view.set_zoom_to_fit(False)
        view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            a_canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            a_canvas.set_index_by_bbox(bbox)


class Application(Gtk.Application):
    "Application class"

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.gscan2pdf",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
            **kwargs,
        )
        self.window = None
        # self.add_main_option(
        #     "test",
        #     ord("t"),
        #     GLib.OptionFlags.NONE,
        #     GLib.OptionArg.NONE,
        #     "Command line test",
        #     None,
        # )

        # Add extra icons early to be available for Gtk.Builder
        if os.path.isdir("/usr/share/gscan2pdf"):
            self._iconpath = "/usr/share/gscan2pdf"
        else:
            self._iconpath = "icons"
        self._init_icons(
            [
                ("rotate90", "stock-rotate-90.svg"),
                ("rotate180", "180_degree.svg"),
                ("rotate270", "stock-rotate-270.svg"),
                ("scanner", "scanner.svg"),
                ("pdf", "pdf.svg"),
                ("selection", "stock-selection-all-16.png"),
                ("hand-tool", "hand-tool.svg"),
                ("mail-attach", "mail-attach.svg"),
                ("crop", "crop.svg"),
            ],
        )

        # https://gitlab.gnome.org/GNOME/gtk/-/blob/gtk-3-24/gtk/gtkbuilder.rnc
        base_path = os.path.abspath(os.path.dirname(__file__))
        global builder
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(base_path, "app.ui"))
        builder.connect_signals(self)
        self._fonts = None
        # dir below session dir
        self.tmpdir = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # These will be in the application group and have the "app" prefix
        for name, function in [
            ("new", new),
            ("open", open_dialog),
            ("open-session", open_session_action),
            ("scan", scan_dialog),
            ("save", save_dialog),
            ("email", email),
            ("print", print_dialog),
            ("quit", quit_app),
            ("undo", undo),
            ("redo", unundo),
            ("cut", cut_selection),
            ("copy", copy_selection),
            ("paste", paste_selection),
            ("delete", delete_selection),
            ("renumber", renumber_dialog),
            ("select-all", select_all),
            ("select-odd", select_odd),
            ("select-even", select_even),
            ("select-invert", select_invert),
            ("select-blank", select_blank),
            ("select-dark", select_dark),
            ("select-modified", select_modified_since_ocr),
            ("select-no-ocr", select_no_ocr),
            ("clear-ocr", clear_ocr),
            ("properties", properties),
            ("preferences", preferences),
            ("zoom-100", zoom_100),
            ("zoom-to-fit", zoom_to_fit),
            ("zoom-in", zoom_in),
            ("zoom-out", zoom_out),
            ("rotate-90", rotate_90),
            ("rotate-180", rotate_180),
            ("rotate-270", rotate_270),
            ("threshold", threshold),
            ("brightness-contrast", brightness_contrast),
            ("negate", negate),
            ("unsharp", unsharp),
            ("crop-dialog", crop_dialog),
            ("crop-selection", crop_selection),
            ("split", split_dialog),
            ("unpaper", unpaper),
            ("ocr", ocr_dialog),
            ("user-defined", user_defined_dialog),
            ("help", view_html),
            ("about", self.about),
        ]:
            actions[name] = Gio.SimpleAction.new(name, None)
            actions[name].connect("activate", function)
            self.add_action(actions[name])

        # action with a state created (name, parameter type, initial state)
        actions["tooltype"] = Gio.SimpleAction.new_stateful(
            "tooltype", GLib.VariantType.new("s"), GLib.Variant.new_string("dragger")
        )
        actions["viewtype"] = Gio.SimpleAction.new_stateful(
            "viewtype", GLib.VariantType.new("s"), GLib.Variant.new_string("tabbed")
        )
        self.set_menubar(builder.get_object("menubar"))

        global detail_popup
        detail_popup = builder.get_object("detail_popup")

    def do_activate(self):
        "only allow a single window and raise any existing ones"

        # Windows are associated with the application
        # until the last one is closed and the application shuts down
        if not self.window:
            self.window = ApplicationWindow(
                application=self, title=f"{prog_name} v{VERSION}"
            )
        self.window.present()

    # It's a shame that we have to define these here, but I can't see a way
    # to connect the actions in a context menu in app.ui otherwise
    def on_dragger(self, _widget):
        "Handles the event when the dragger tool is selected."
        # builder calls this the first time before the window is defined
        if self.window:
            self.window._change_image_tool_cb(
                actions["tooltype"], GLib.Variant("s", "dragger")
            )

    def on_selector(self, _widget):
        "Handles the event when the selector tool is selected."
        # builder calls this the first time before the window is defined
        if self.window:
            self.window._change_image_tool_cb(
                actions["tooltype"], GLib.Variant("s", "selector")
            )

    def on_selectordragger(self, _widget):
        "Handles the event when the selector dragger tool is selected."
        # builder calls this the first time before the window is defined
        if self.window:
            self.window._change_image_tool_cb(
                actions["tooltype"], GLib.Variant("s", "selectordragger")
            )

    def on_zoom_100(self, _widget):
        "Zooms the current page to 100%"
        zoom_100(None, None)

    def on_zoom_to_fit(self, _widget):
        "Zooms the current page so that it fits the viewing pane."
        zoom_to_fit(None, None)

    def on_zoom_in(self, _widget):
        "Zooms in the current page."
        zoom_in(None, None)

    def on_zoom_out(self, _widget):
        "Zooms out the current page."
        zoom_out(None, None)

    def on_rotate_90(self, _widget):
        "Rotate the selected pages by 90 degrees."
        rotate_90(None, None)

    def on_rotate_180(self, _widget):
        "Rotate the selected pages by 180 degrees."
        rotate_180(None, None)

    def on_rotate_270(self, _widget):
        "Rotate the selected pages by 270 degrees."
        rotate_270(None, None)

    def on_save(self, _widget):
        "Displays the save dialog."
        save_dialog(None, None)

    def on_email(self, _widget):
        "displays the email dialog."
        email(None, None)

    def on_print(self, _widget):
        "displays the print dialog."
        print_dialog(None, None)

    def on_renumber(self, _widget):
        "Displays the renumber dialog."
        renumber_dialog(None, None)

    def on_select_all(self, _widget):
        "selects all pages."
        select_all(None, None)

    def on_select_odd(self, _widget):
        "selects the pages with odd numbers."
        select_odd_even(0)

    def on_select_even(self, _widget):
        "selects the pages with even numbers."
        select_odd_even(1)

    def on_invert_selection(self, _widget):
        "Inverts the current selection."
        select_invert(None, None)

    def on_crop(self, _widget):
        "Displays the crop dialog."
        crop_selection(None, None)

    def on_cut(self, _widget):
        "cuts the selected pages to the clipboard."
        cut_selection(None, None)

    def on_copy(self, _widget):
        "copies the selected pages to the clipboard."
        copy_selection(None, None)

    def on_paste(self, _widget):
        "pastes the copied pages."
        paste_selection(None, None)

    def on_delete(self, _widget):
        "deletes the selected pages."
        delete_selection(None, None)

    def on_clear_ocr(self, _widget):
        "Clears the OCR (Optical Character Recognition) data."
        clear_ocr(None, None)

    def on_properties(self, _widget):
        "displays the properties dialog."
        properties(None, None)

    def on_quit(self, _action, _param):
        "Handles the quit action."
        self.quit()

    def _init_icons(self, icons):
        "Initialise iconfactory"
        iconfactory = Gtk.IconFactory()
        for iconname, filename in icons:
            register_icon(iconfactory, iconname, self._iconpath + "/" + filename)
        iconfactory.add_default()

    def about(self, _action, _param):
        "Display about dialog"
        about = Gtk.AboutDialog()

        # Gtk.AboutDialog->set_url_hook ($func, $data=undef);
        # Gtk.AboutDialog->set_email_hook ($func, $data=undef);

        about.set_program_name(prog_name)
        about.set_version(VERSION)
        authors = [
            "Frederik Elwert",
            "Klaus Ethgen",
            "Andy Fingerhut",
            "Leon Fisk",
            "John Goerzen",
            "Alistair Grant",
            "David Hampton",
            "Sascha Hunold",
            "Jason Kankiewicz",
            "Matthijs Kooijman",
            "Peter Marschall",
            "Chris Mayo",
            "Hiroshi Miura",
            "Petr Písař",
            "Pablo Saratxaga",
            "Torsten Schönfeld",
            "Roy Shahbazian",
            "Jarl Stefansson",
            "Wikinaut",
            "Jakub Wilk",
            "Sean Dreilinger",
        ]
        about.set_authors(["Jeff Ratcliffe"])
        about.add_credit_section("Patches gratefully received from", authors)
        about.set_comments(_("To aid the scan-to-PDF process"))
        about.set_copyright(_("Copyright 2006--2025 Jeffrey Ratcliffe"))
        licence = """gscan2pdf --- to aid the scan to PDF or DjVu process
    Copyright 2006 -- 2025 Jeffrey Ratcliffe <jffry@posteo.net>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the version 3 GNU General Public License as
    published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
    """
        about.set_license(licence)
        about.set_website("http://gscan2pdf.sf.net")
        translators = """Yuri Chornoivan
    Davidmp
    Whistle
    Dušan Kazik
    Cédric VALMARY (Tot en òc)
    Eric Spierings
    Milo Casagrande
    Raúl González Duque
    R120X
    NSV
    Alexandre Prokoudine
    Aputsiaĸ Niels Janussen
    Paul Wohlhart
    Pierre Slamich
    Tiago Silva
    Igor Zubarev
    Jarosław Ogrodnik
    liorda
    Clopy
    Daniel Nylander
    csola
    dopais
    Po-Hsu Lin
    Tobias Bannert
    Ettore Atalan
    Eric Brandwein
    Mikhail Novosyolov
    rodroes
    morodan
    Hugues Drolet
    Martin Butter
    Albano Battistella
    Olesya Gerasimenko
    Pavel Borecki
    Stephan Woidowski
    Jonatan Nyberg
    Berov
    Utku BERBEROĞLU
    Arthur Rodrigues
    Matthias Sprau
    Buckethead
    Eugen Artus
    Quentin PAGÈS
    Alexandre NICOLADIE
    Aleksandr Proklov
    Silvio Brera
    papoteur
    """
        about.set_translator_credits(translators)
        about.set_artists(["lodp, Andreas E."])
        about.set_logo(
            GdkPixbuf.Pixbuf.new_from_file(f"{self._iconpath}/gscan2pdf.svg")
        )
        about.set_transient_for(self.window)
        about.run()
        about.destroy()


if __name__ == "__main__":
    global app
    app = Application()
    # app.run(sys.argv)
    app.run()

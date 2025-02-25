"main application"

# TODO:
# rotate icons wrong way round
# save_pdf landscape squashes into portrait
# fix TypeErrors when dragging edges of selection
# fix panning text layer
# fix editing text layer
# deleting last page produces TypeError
# saving a scan profile produced TypeError
# lint
# fix progress bar, including during scan
# restore last used scan settings
# use pathlib for all paths
# refactor methods using self.slist.clipboard
# refactor ocr & annotation manipulation into single class
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
from progress import Progress
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
EDIT_TEXT = 200
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

EMPTY = ""
SPACE = " "
DOT = "."
PERCENT = "%"
ASTERISK = "*"
logger = logging.getLogger(__name__)

dependencies = {}
ocr_engine = []
# Temp::File object for PDF to be emailed
# Define here to make sure that it doesn't get deleted until the next email
# is created or we quit
pdf = None
# Comboboxes for user-defined tools and rotate buttons
comboboxudt = None
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


def selection_changed_callback(_selection):
    "Handle selection change"
    selection = app.window.slist.get_selected_indices()

    # Display the new image
    # When editing the page number, there is a race condition where the page
    # can be undefined
    if selection:
        i = selection.pop(0)
        path = Gtk.TreePath.new_from_indices([i])
        app.window.slist.scroll_to_cell(
            path, app.window.slist.get_column(0), True, HALF, HALF
        )
        sel = app.window.view.get_selection()
        display_image(app.window.slist.data[i][2])
        if sel is not None:
            app.window.view.set_selection(sel)
    else:
        app.window.view.set_pixbuf(None)
        app.window.t_canvas.clear_text()
        app.window.a_canvas.clear_text()
        app.window._current_page = None

    app.window.update_uimanager()


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


def display_callback(response):
    "Find the page from the input uuid and display it"
    uuid = response.request.args[0]["page"].uuid
    i = app.window.slist.find_page_by_uuid(uuid)
    if i is None:
        logger.error("Can't display page with uuid %s: page not found", uuid)
    else:
        display_image(app.window.slist.data[i][2])


def display_image(page):
    "Display the image in the view"
    app.window._current_page = page
    app.window.view.set_pixbuf(app.window._current_page.get_pixbuf(), True)
    xresolution, yresolution, _units = app.window._current_page.resolution
    app.window.view.set_resolution_ratio(xresolution / yresolution)

    # Get image dimensions to constrain selector spinbuttons on crop dialog
    width, height = app.window._current_page.get_size()

    # Update the ranges on the crop dialog
    if app.window._windowc is not None and app.window._current_page is not None:
        app.window._windowc.page_width = width
        app.window._windowc.page_height = height
        app.window.settings["selection"] = app.window._windowc.selection
        app.window.view.set_selection(app.window.settings["selection"])

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
        app.window.t_canvas.clear_text()

    if app.window._current_page.annotations:
        create_ann_canvas(app.window._current_page)
    else:
        app.window.a_canvas.clear_text()


def create_txt_canvas(page, finished_callback=None):
    "Create the text canvas"
    offset = app.window.view.get_offset()
    app.window.t_canvas.set_text(
        page=page,
        layer="text_layer",
        edit_callback=app.window.edit_ocr_text,
        idle=True,
        finished_callback=finished_callback,
    )
    app.window.t_canvas.set_scale(app.window.view.get_zoom())
    app.window.t_canvas.set_offset(offset.x, offset.y)
    app.window.t_canvas.show()


def create_ann_canvas(page, finished_callback=None):
    "Create the annotation canvas"
    offset = app.window.view.get_offset()
    app.window.a_canvas.set_text(
        page=page,
        layer="annotations",
        edit_callback=app.window.edit_annotation,
        idle=True,
        finished_callback=finished_callback,
    )
    app.window.a_canvas.set_scale(app.window.view.get_zoom())
    app.window.a_canvas.set_offset(offset.x, offset.y)
    app.window.a_canvas.show()


def scans_saved(message):
    "Check that all pages have been saved"
    if not app.window.slist.scans_saved():
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
    # between the tied array of the app.window.slist and the callbacks displaying the
    # thumbnails, so block this whilst clearing the array.
    app.window.slist.get_model().handler_block(app.window.slist.row_changed_signal)
    app.window.slist.get_selection().handler_block(
        app.window.slist.selection_changed_signal
    )

    # Depopulate the thumbnail list
    app.window.slist.data = []

    # Unblock app.window.slist signals now finished
    app.window.slist.get_selection().handler_unblock(
        app.window.slist.selection_changed_signal
    )
    app.window.slist.get_model().handler_unblock(app.window.slist.row_changed_signal)

    # Now we have to clear everything manually
    app.window.slist.get_selection().unselect_all()
    app.window.view.set_pixbuf(None)
    app.window.t_canvas.clear_text()
    app.window.a_canvas.clear_text()
    app.window._current_page = None

    # Reset start page in scan dialog
    app.window._windows._reset_start_page()


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
        page = app.window.slist.data[
            app.window.slist.find_page_by_uuid(args[0]["page"].uuid)
        ][0]

    kwargs = {
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
        app.window.show_message_dialog(**kwargs)

    GLib.idle_add(show_message_dialog_wrapper)
    app.window.post_process_progress.hide()


def open_session_file(filename):
    "open session"
    logger.info("Restoring session in %s", app.window.session)
    app.window.slist.open_session_file(info=filename, error_callback=error_callback)


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
    file_chooser.set_current_folder(app.window.settings["cwd"])
    if file_chooser.run() == Gtk.ResponseType.OK:

        # Update undo/redo buffers
        take_snapshot()
        filename = file_chooser.get_filenames()
        open_session(filename[0])

    file_chooser.destroy()


def open_session(sesdir):
    "open session"
    logger.info("Restoring session in %s", app.window.session)
    app.window.slist.open_session(
        dir=sesdir, delete=False, error_callback=error_callback
    )


def open_dialog(_action, _param):
    "Throw up file selector and open selected file"
    # cd back to cwd to get filename
    os.chdir(app.window.settings["cwd"])
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
    file_chooser.set_current_folder(app.window.settings["cwd"])
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
        os.chdir(app.window.session.name)

        # Update undo/redo buffers
        take_snapshot()
        filenames = file_chooser.get_filenames()
        file_chooser.destroy()

        # Update cwd
        app.window.settings["cwd"] = os.path.dirname(filenames[0])
        import_files(filenames)
    else:
        file_chooser.destroy()

    # cd back to tempdir
    os.chdir(app.window.session.name)


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
    app.window.post_process_progress.finish(response)
    # slist.save_session()


def import_files_metadata_callback(metadata):
    "Update the metadata from the imported file"
    logger.debug("import_files_metadata_callback(%s)", metadata)
    for dialog in (app.window._windowi, app.window._windowe):
        if dialog is not None:
            dialog.update_from_import_metadata(metadata)
    config.update_config_from_imported_metadata(app.window.settings, metadata)


def import_files(filenames, all_pages=False):
    "Import given files"
    # FIXME: import_files() now returns an array of pids.
    options = {
        "paths": filenames,
        "password_callback": import_files_password_callback,
        "queued_callback": app.window.post_process_progress.queued,
        "started_callback": app.window.post_process_progress.update,
        "running_callback": app.window.post_process_progress.update,
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

    app.window.slist.import_files(**options)


def launch_default_for_file(filename):
    "Launch default viewer for file"
    uri = GLib.filename_to_uri(os.path.abspath(filename), None)
    logger.info("Opening %s via default launcher", uri)
    context = Gio.AppLaunchContext()
    try:
        Gio.AppInfo.launch_default_for_uri(uri, context)
    except Exception as e:
        logger.error("Unable to launch viewer: %s", e)


def list_of_page_uuids():
    "Compile list of pages"
    pagelist = app.window.slist.get_page_index(
        app.window.settings["Page range"], error_callback
    )
    if not pagelist:
        return []
    return [app.window.slist.data[i][2].uuid for i in pagelist]


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
        app.window.show_message_dialog(
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
        app.window.show_message_dialog(
            parent=chooser,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            text=text,
        )
        return True

    return False


def save_tiff(filename, ps, uuids):
    "Save a list of pages as a TIFF file with specified options"
    options = {
        "compression": app.window.settings["tiff compression"],
        "quality": app.window.settings["quality"],
        "ps": ps,
    }
    if app.window.settings["post_save_hook"]:
        options["post_save_hook"] = app.window.settings["current_psh"]

    def save_tiff_finished_callback(response):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        app.window.post_process_progress.finish(response)
        mark_pages(uuids)
        file = ps if ps is not None else filename
        if (
            "view files toggle" in app.window.settings
            and app.window.settings["view files toggle"]
        ):
            launch_default_for_file(file)

        logger.debug("Finished saving %s", file)

    app.window.slist.save_tiff(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=app.window.post_process_progress.queued,
        started_callback=app.window.post_process_progress.update,
        running_callback=app.window.post_process_progress.update,
        finished_callback=save_tiff_finished_callback,
        error_callback=error_callback,
    )


def save_djvu(filename, uuids):
    "Save a list of pages as a DjVu file."

    # cd back to tempdir
    os.chdir(app.window.session.name)

    # Create the DjVu
    logger.debug("Started saving %s", filename)
    options = {
        "set_timestamp": app.window.settings["set_timestamp"],
        "convert whitespace to underscores": app.window.settings[
            "convert whitespace to underscores"
        ],
    }
    if app.window.settings["post_save_hook"]:
        options["post_save_hook"] = app.window.settings["current_psh"]

    def save_djvu_finished_callback(response):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        app.window.post_process_progress.finish(response)
        mark_pages(uuids)
        if (
            "view files toggle" in app.window.settings
            and app.window.settings["view files toggle"]
        ):
            launch_default_for_file(filename)
        logger.debug("Finished saving %s", filename)

    app.window.slist.save_djvu(
        path=filename,
        list_of_pages=uuids,
        options=options,
        metadata=collate_metadata(app.window.settings, datetime.datetime.now()),
        queued_callback=app.window.post_process_progress.queued,
        started_callback=app.window.post_process_progress.update,
        running_callback=app.window.post_process_progress.update,
        finished_callback=save_djvu_finished_callback,
        error_callback=error_callback,
    )


def save_text(filename, uuids):
    "Save OCR text"
    options = {}
    if app.window.settings["post_save_hook"]:
        options["post_save_hook"] = app.window.settings["current_psh"]

    def save_text_finished_callback(response):

        app.window.post_process_progress.finish(response)
        mark_pages(uuids)
        if (
            "view files toggle" in app.window.settings
            and app.window.settings["view files toggle"]
        ):
            launch_default_for_file(filename)

        logger.debug("Finished saving %s", filename)

    app.window.slist.save_text(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=app.window.post_process_progress.queued,
        started_callback=app.window.post_process_progress.update,
        running_callback=app.window.post_process_progress.update,
        finished_callback=save_text_finished_callback,
        error_callback=error_callback,
    )


def save_hocr(filename, uuids):
    "Save HOCR (HTML OCR) data to a file"
    options = {}
    if app.window.settings["post_save_hook"]:
        options["post_save_hook"] = app.window.settings["current_psh"]

    def save_hocr_finished_callback(response):
        app.window.post_process_progress.finish(response)
        mark_pages(uuids)
        if (
            "view files toggle" in app.window.settings
            and app.window.settings["view files toggle"]
        ):
            launch_default_for_file(filename)

        logger.debug("Finished saving %s", filename)

    app.window.slist.save_hocr(
        path=filename,
        list_of_pages=uuids,
        options=options,
        queued_callback=app.window.post_process_progress.queued,
        started_callback=app.window.post_process_progress.update,
        running_callback=app.window.post_process_progress.update,
        finished_callback=save_hocr_finished_callback,
        error_callback=error_callback,
    )


def changed_side_to_scan_callback(widget, _arg):
    "Callback function to handle the event when the side to scan is changed."
    logger.debug("changed_side_to_scan_callback( %s, %s )", widget, _arg)
    if len(app.window.slist.data) - 1 > EMPTY_LIST:
        widget.page_number_start = (
            app.window.slist.data[len(app.window.slist.data) - 1][0] + 1
        )
    else:
        widget.page_number_start = 1


def changed_progress_callback(_widget, progress, message):
    "Updates the progress bar based on the given progress value and message."
    if progress is not None and (0 <= progress <= 1):
        app.window._scan_progress.set_fraction(progress)
    else:
        app.window._scan_progress.pulse()
    if message is not None:
        app.window._scan_progress.set_text(message)


def import_scan_finished_callback(response):
    "Callback function to handle the completion of a scan import process."
    logger.debug("import_scan_finished_callback( %s )", response)
    # FIXME: response is hard-coded to None in _post_process_scan().
    # Work out how to pass number of pending requests
    # We have two threads, the scan thread, and the document thread.
    # We should probably combine the results in one progress bar
    # app.window.post_process_progress.finish(response)
    # slist.save_session()


def new_scan_callback(_self, image_object, page_number, xresolution, yresolution):
    "Callback function to handle a new scan."
    if image_object is None:
        return

    # Update undo/redo buffers
    take_snapshot()
    rotate = (
        app.window.settings["rotate facing"]
        if page_number % 2
        else app.window.settings["rotate reverse"]
    )
    options = {
        "page": page_number,
        "dir": app.window.session.name,
        "to_png": app.window.settings["to_png"],
        "rotate": rotate,
        "ocr": app.window.settings["OCR on scan"],
        "engine": app.window.settings["ocr engine"],
        "language": app.window.settings["ocr language"],
        "queued_callback": app.window.post_process_progress.queued,
        "started_callback": app.window.post_process_progress.update,
        "finished_callback": import_scan_finished_callback,
        "error_callback": error_callback,
        "image_object": image_object,
        "resolution": (xresolution, yresolution, "PixelsPerInch"),
    }
    if app.window.settings["unpaper on scan"]:
        options["unpaper"] = app.window._unpaper

    if app.window.settings["threshold-before-ocr"]:
        options["threshold"] = app.window.settings["threshold tool"]

    if app.window.settings["udt_on_scan"]:
        options["udt"] = app.window.settings["current_udt"]

    logger.info("Importing scan with resolution=%s,%s", xresolution, yresolution)

    app.window.slist.import_scan(**options)


def restart():
    "Restart the application"
    app.window.can_quit()
    os.execv(sys.executable, ["python"] + sys.argv)


def print_dialog(_action, _param):
    "print"
    os.chdir(app.window.settings["cwd"])
    print_op = PrintOperation(
        settings=app.window.print_settings, slist=app.window.slist
    )
    res = print_op.run(Gtk.PrintOperationAction.PRINT_DIALOG, app.window)
    if res == Gtk.PrintOperationResult.APPLY:
        app.window.print_settings = print_op.get_print_settings()
    os.chdir(app.window.session.name)


def cut_selection(_action, _param):
    "Cut the selection"
    app.window.slist.clipboard = app.window.slist.cut_selection()
    app.window.update_uimanager()


def copy_selection(_action, _param):
    "Copy the selection"
    app.window.slist.clipboard = app.window.slist.copy_selection(True)
    app.window.update_uimanager()


def paste_selection(_action, _param):
    "Paste the selection"
    if app.window.slist.clipboard is None:
        return
    take_snapshot()
    pages = app.window.slist.get_selected_indices()
    if pages:
        app.window.slist.paste_selection(
            app.window.slist.clipboard, pages[-1], "after", True
        )
    else:
        app.window.slist.paste_selection(app.window.slist.clipboard, None, None, True)
    app.window.update_uimanager()


def delete_selection(_action, _param):
    "Delete the selected scans"
    # Update undo/redo buffers
    take_snapshot()
    app.window.slist._delete_selection_extra()

    # Reset start page in scan dialog
    if app.window._windows:
        app.window._windows._reset_start_page()
    app.window.update_uimanager()


def select_all(_action, _param):
    "Select all scans"
    # if ($textview -> has_focus) {
    #  my ($start, $end) = $textbuffer->get_bounds;
    #  $textbuffer->select_range ($start, $end);
    # }
    # else {

    app.window.slist.get_selection().select_all()

    # }


def select_odd_even(odd):
    "Select all odd(0) or even(1) scans"
    selection = []
    for i, row in enumerate(app.window.slist.data):
        if row[0] % 2 ^ odd:
            selection.append(i)

    app.window.slist.get_selection().unselect_all()
    app.window.slist.select(selection)


def select_invert(_action, _param):
    "Invert selection"
    selection = app.window.slist.get_selected_indices()
    inverted = []
    for i in range(len(app.window.slist.data)):
        if i not in selection:
            inverted.append(_)
    app.window.slist.get_selection().unselect_all()
    app.window.slist.select(inverted)


def select_modified_since_ocr(_action, _param):
    "Selects pages that have been modified since the last OCR process."
    selection = []
    for page in range(len(app.window.slist.data)):
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

    app.window.slist.get_selection().unselect_all()
    app.window.slist.select(selection)


def select_no_ocr(_action, _param):
    "Select pages with no ocr output"
    selection = []
    for i, row in enumerate(app.window.slist.data):
        if not hasattr(row[2], "text_layer") or row[2].text_layer is None:
            selection.append(i)

    app.window.slist.get_selection().unselect_all()
    app.window.slist.select(selection)


def clear_ocr(_action, _param):
    "Clear the OCR output from selected pages"
    # Update undo/redo buffers
    take_snapshot()

    # Clear the existing canvas
    app.window.t_canvas.clear_text()
    selection = app.window.slist.get_selected_indices()
    for i in selection:
        app.window.slist.data[i][2].text_layer = None

    # slist.save_session()


def select_blank(_action, _param):
    "Analyse and select blank pages"
    analyse(True, False)


def select_blank_pages():
    "Select blank pages"
    for page in app.window.slist.data:

        # compare Std Dev to threshold
        # std_dev is a list -- 1 value per channel
        if (
            sum(page[2].std_dev) / len(page[2].std_dev)
            <= app.window.settings["Blank threshold"]
        ):
            app.window.slist.select(page)
            logger.info("Selecting blank page")
        else:
            app.window.slist.unselect(page)
            logger.info("Unselecting non-blank page")

        logger.info(
            "StdDev: %s threshold: %s",
            page[2].std_dev,
            app.window.settings["Blank threshold"],
        )


def select_dark(_action, _param):
    "Analyse and select dark pages"
    analyse(False, True)


def select_dark_pages():
    "Select dark pages"
    for page in app.window.slist.data:

        # compare Mean to threshold
        # mean is a list -- 1 value per channel
        if (
            sum(page[2].mean) / len(page[2].std_dev)
            <= app.window.settings["Dark threshold"]
        ):
            app.window.slist.select(page)
            logger.info("Selecting dark page")
        else:
            app.window.slist.unselect(page)
            logger.info("Unselecting non-dark page")

        logger.info(
            "mean: %s threshold: %s",
            page[2].mean,
            app.window.settings["Dark threshold"],
        )


def renumber_dialog(_action, _param):
    "Dialog for renumber"
    if app.window.renumber_dialog is not None:
        app.window.renumber_dialog.present()
        return

    app.window.renumber_dialog = Renumber(
        transient_for=app.window,
        document=app.window.slist,
        hide_on_delete=False,
    )
    app.window.renumber_dialog.connect("before-renumber", lambda x: take_snapshot())
    app.window.renumber_dialog.connect(
        "error",
        lambda msg: app.window.show_message_dialog(
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
        pages.append(app.window.slist.data[i][2].uuid)
    return pages


def rotate(angle, pagelist):
    "Rotate selected images"

    # Update undo/redo buffers
    take_snapshot()
    for page in pagelist:
        app.window.slist.rotate(
            angle=angle,
            page=page,
            queued_callback=app.window.post_process_progress.queued,
            started_callback=app.window.post_process_progress.update,
            running_callback=app.window.post_process_progress.update,
            finished_callback=app.window.post_process_progress.finish,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def analyse(select_blank, select_dark):
    "Analyse selected images"

    # Update undo/redo buffers
    take_snapshot()
    pages_to_analyse = []
    for row in app.window.slist.data:
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
            app.window.post_process_progress.finish(response)
            if select_blank:
                select_blank_pages()
            if select_dark:
                select_dark_pages()

        # slist.save_session()

        app.window.slist.analyse(
            list_of_pages=pages_to_analyse,
            queued_callback=app.window.post_process_progress.queued,
            started_callback=app.window.post_process_progress.update,
            running_callback=app.window.post_process_progress.update,
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
    spinbutton.set_value(app.window.settings["threshold tool"])
    hboxt.pack_end(spinbutton, False, True, 0)

    def threshold_apply_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        app.window.settings["threshold tool"] = spinbutton.get_value()
        app.window.settings["Page range"] = windowt.page_range
        pagelist = app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
        if not pagelist:
            return
        page = 0
        for i in pagelist:
            page += 1

            def threshold_finished_callback(response):
                app.window.post_process_progress.finish(response)
                # slist.save_session()

            app.window.slist.threshold(
                threshold=app.window.settings["threshold tool"],
                page=app.window.slist.data[i][2].uuid,
                queued_callback=app.window.post_process_progress.queued,
                started_callback=app.window.post_process_progress.update,
                running_callback=app.window.post_process_progress.update,
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
    spinbuttonb.set_value(app.window.settings["brightness tool"])
    hbox.pack_end(spinbuttonb, False, True, 0)

    # SpinButton for contrast
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, False, True, 0)
    label = Gtk.Label(label=_("Contrast"))
    hbox.pack_start(label, False, True, 0)
    label = Gtk.Label(label=PERCENT)
    hbox.pack_end(label, False, True, 0)
    spinbuttonc = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
    spinbuttonc.set_value(app.window.settings["contrast tool"])
    hbox.pack_end(spinbuttonc, False, True, 0)

    def brightness_contrast_callback():
        # HBox for buttons
        # Update undo/redo buffers
        take_snapshot()
        app.window.settings["brightness tool"] = spinbuttonb.get_value()
        app.window.settings["contrast tool"] = spinbuttonc.get_value()
        app.window.settings["Page range"] = windowt.page_range
        pagelist = app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
        if not pagelist:
            return
        for i in pagelist:

            def brightness_contrast_finished_callback(response):
                app.window.post_process_progress.finish(response)
                # slist.save_session()

            app.window.slist.brightness_contrast(
                brightness=app.window.settings["brightness tool"],
                contrast=app.window.settings["contrast tool"],
                page=app.window.slist.data[i][2].uuid,
                queued_callback=app.window.post_process_progress.queued,
                started_callback=app.window.post_process_progress.update,
                running_callback=app.window.post_process_progress.update,
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
        app.window.settings["Page range"] = windowt.page_range
        pagelist = app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
        if not pagelist:
            return
        for i in pagelist:

            def negate_finished_callback(response):
                app.window.post_process_progress.finish(response)
                # slist.save_session()

            app.window.slist.negate(
                page=app.window.slist.data[i][2].uuid,
                queued_callback=app.window.post_process_progress.queued,
                started_callback=app.window.post_process_progress.update,
                running_callback=app.window.post_process_progress.update,
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
            app.window.settings["unsharp radius"],
            _("Blur Radius."),
        ],
        [
            _("Percentage"),
            spinbuttons,
            _("%"),
            app.window.settings["unsharp percentage"],
            _("Unsharp strength, in percent."),
        ],
        [
            _("Threshold"),
            spinbuttont,
            None,
            app.window.settings["unsharp threshold"],
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
        app.window.settings["unsharp radius"] = spinbuttonr.get_value()
        app.window.settings["unsharp percentage"] = int(spinbuttons.get_value())
        app.window.settings["unsharp threshold"] = int(spinbuttont.get_value())
        app.window.settings["Page range"] = windowum.page_range
        pagelist = app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
        if not pagelist:
            return
        for i in pagelist:

            def unsharp_finished_callback(response):
                app.window.post_process_progress.finish(response)
                # slist.save_session()

            app.window.slist.unsharp(
                page=app.window.slist.data[i][2].uuid,
                radius=app.window.settings["unsharp radius"],
                percent=app.window.settings["unsharp percentage"],
                threshold=app.window.settings["unsharp threshold"],
                queued_callback=app.window.post_process_progress.queued,
                started_callback=app.window.post_process_progress.update,
                running_callback=app.window.post_process_progress.update,
                finished_callback=unsharp_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    windowum.add_actions(
        [("gtk-apply", unsharp_callback), ("gtk-cancel", windowum.destroy)]
    )
    windowum.show_all()


def crop_selection(_action, _param, pagelist=None):
    "Crop the selected area of the specified pages."
    if not app.window.settings["selection"]:
        return

    # Update undo/redo buffers
    take_snapshot()
    if not pagelist:
        pagelist = app.window.slist.get_selected_indices()

    if not pagelist:
        return

    for i in pagelist:

        def crop_finished_callback(response):
            app.window.post_process_progress.finish(response)
            # slist.save_session()

        app.window.slist.crop(
            page=app.window.slist.data[i][2].uuid,
            x=app.window.settings["selection"].x,
            y=app.window.settings["selection"].y,
            w=app.window.settings["selection"].width,
            h=app.window.settings["selection"].height,
            queued_callback=app.window.post_process_progress.queued,
            started_callback=app.window.post_process_progress.update,
            running_callback=app.window.post_process_progress.update,
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

    app.window.view.position_changed_signal = app.window.view.connect(
        "selection-changed", changed_split_position_selection
    )

    def split_apply_callback():

        # Update undo/redo buffers
        take_snapshot()
        app.window.settings["split-direction"] = direction[combob.get_active()][0]
        app.window.settings["split-position"] = sb_pos.get_value()
        app.window.settings["Page range"] = windowsp.page_range
        pagelist = app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
        if not pagelist:
            return
        page = 0
        for i in pagelist:
            page += 1

            def split_finished_callback(response):
                app.window.post_process_progress.finish(response)
                # slist.save_session()

            app.window.slist.split_page(
                direction=app.window.settings["split-direction"],
                position=app.window.settings["split-position"],
                page=app.window.slist.data[i][2].uuid,
                queued_callback=app.window.post_process_progress.queued,
                started_callback=app.window.post_process_progress.update,
                running_callback=app.window.post_process_progress.update,
                finished_callback=split_finished_callback,
                error_callback=error_callback,
                display_callback=display_callback,
            )

    def split_cancel_callback():
        app.window.view.disconnect(app.window.view.position_changed_signal)
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

    app.window.view.set_selection(selection)


def user_defined_dialog(_action, _param):
    "Displays a dialog for selecting and applying user-defined tools."
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
    comboboxudt = app.window.add_udt_combobox(hbox)

    def udt_apply_callback():
        app.window.settings["Page range"] = windowudt.page_range
        pagelist = indices2pages(
            app.window.slist.get_page_index(
                app.window.settings["Page range"], error_callback
            )
        )
        if not pagelist:
            return
        app.window.settings["current_udt"] = comboboxudt.get_active_text()
        user_defined_tool(pagelist, app.window.settings["current_udt"])
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
            app.window.post_process_progress.finish(response)
            # slist.save_session()

        app.window.slist.user_defined(
            page=page,
            command=cmd,
            queued_callback=app.window.post_process_progress.queued,
            started_callback=app.window.post_process_progress.update,
            running_callback=app.window.post_process_progress.update,
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
            app.window.post_process_progress.finish(response)
            # slist.save_session()

        app.window.slist.unpaper(
            page=pageobject,
            options=options,
            queued_callback=app.window.post_process_progress.queued,
            started_callback=app.window.post_process_progress.update,
            running_callback=app.window.post_process_progress.update,
            finished_callback=unpaper_finished_callback,
            error_callback=error_callback,
            display_callback=display_callback,
        )


def ocr_finished_callback(response):
    "Callback function to be executed when OCR processing is finished."
    app.window.post_process_progress.finish(response)
    # slist.save_session()


def ocr_display_callback(response):
    "Callback function to handle the display of OCR (Optical Character Recognition) results."
    uuid = response.request.args[0]["page"].uuid
    i = app.window.slist.find_page_by_uuid(uuid)
    if i is None:
        logger.error("Can't display page with uuid %s: page not found", uuid)
    else:
        page = app.window.slist.get_selected_indices()
        if page and i == page[0]:
            create_txt_canvas(app.window.slist.data[i][2])


def run_ocr(engine, tesslang, threshold_flag, threshold):
    "Run OCR on a set of pages"
    if engine == "tesseract":
        app.window.settings["ocr language"] = tesslang

    kwargs = {
        "queued_callback": app.window.post_process_progress.queued,
        "started_callback": app.window.post_process_progress.update,
        "running_callback": app.window.post_process_progress.update,
        "finished_callback": ocr_finished_callback,
        "error_callback": error_callback,
        "display_callback": ocr_display_callback,
        "engine": engine,
        "language": app.window.settings["ocr language"],
    }
    app.window.settings["ocr engine"] = engine
    app.window.settings["threshold-before-ocr"] = threshold_flag
    if threshold_flag:
        app.window.settings["threshold tool"] = threshold
        kwargs["threshold"] = threshold

    # fill pagelist with filenames
    # depending on which radiobutton is active
    app.window.settings["Page range"] = app.windwo._windowo.page_range
    pagelist = indices2pages(
        app.window.slist.get_page_index(
            app.window.settings["Page range"], error_callback
        )
    )
    if not pagelist:
        return
    kwargs["pages"] = pagelist
    app.window.slist.ocr_pages(**kwargs)
    app.window._windowo.hide()


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
    app.window.slist.take_snapshot()

    # Unghost Undo/redo
    actions["undo"].set_enabled(True)

    # Check free space in session directory
    df = shutil.disk_usage(app.window.session.name)
    if df:
        df = df.free / 1024 / 1024
        logger.debug(
            "Free space in %s (Mb): %s (warning at %s)",
            app.window.session.name,
            df,
            app.window.settings["available-tmp-warning"],
        )
        if df < app.window.settings["available-tmp-warning"]:
            text = _("%dMb free in %s.") % (df, app.window.session.name)
            app.window.show_message_dialog(
                parent=app.window,
                message_type="warning",
                buttons=Gtk.ButtonsType.CLOSE,
                text=text,
            )


def undo(_action, _param):
    "Put things back to last snapshot after updating redo buffer"
    logger.info("Undoing")
    app.window.slist.undo()

    # Update menus/buttons
    app.window.update_uimanager()
    actions["undo"].set_enabled(False)
    actions["redo"].set_enabled(True)


def unundo(_action, _param):
    "Put things back to last snapshot after updating redo buffer"
    logger.info("Redoing")
    app.window.slist.unundo()

    # Update menus/buttons
    app.window.update_uimanager()
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
    app.window.slist.get_model().handler_block(app.window.slist.row_changed_signal)
    for p in pages:
        i = app.window.slist.find_page_by_uuid(p)
        if i is not None:
            app.window.slist.data[i][2].saved = True

    app.window.slist.get_model().handler_unblock(app.window.slist.row_changed_signal)


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
    if "auto-open-scan-dialog" in app.window.settings:
        cbo.set_active(app.window.settings["auto-open-scan-dialog"])

    vbox.pack_start(cbo, True, True, 0)

    # Device blacklist
    hboxb = Gtk.HBox()
    vbox.pack_start(hboxb, False, False, 0)
    label = Gtk.Label(label=_("Device blacklist"))
    hboxb.pack_start(label, False, False, 0)
    blacklist = Gtk.Entry()
    hboxb.add(blacklist)
    hboxb.set_tooltip_text(_("Device blacklist (regular expression)"))
    if (
        "device blacklist" in app.window.settings
        and app.window.settings["device blacklist"] is not None
    ):
        blacklist.set_text(app.window.settings["device blacklist"])

    # Cycle SANE handle after scan
    cbcsh = Gtk.CheckButton(label=_("Cycle SANE handle after scan"))
    cbcsh.set_tooltip_text(
        _("Some ADFs do not feed out the last page if this is not enabled")
    )
    if "cycle sane handle" in app.window.settings:
        cbcsh.set_active(app.window.settings["cycle sane handle"])

    vbox.pack_start(cbcsh, False, False, 0)

    # Allow batch scanning from flatbed
    cb_batch_flatbed = Gtk.CheckButton(label=_("Allow batch scanning from flatbed"))
    cb_batch_flatbed.set_tooltip_text(
        _(
            "If not set, switching to a flatbed scanner will force # pages to "
            "1 and single-sided mode."
        )
    )
    cb_batch_flatbed.set_active(app.window.settings["allow-batch-flatbed"])
    vbox.pack_start(cb_batch_flatbed, False, False, 0)

    # Ignore duplex capabilities
    cb_ignore_duplex = Gtk.CheckButton(label=_("Ignore duplex capabilities of scanner"))
    cb_ignore_duplex.set_tooltip_text(
        _(
            "If set, any duplex capabilities are ignored, and facing/reverse "
            "widgets are displayed to allow manual interleaving of pages."
        )
    )
    cb_ignore_duplex.set_active(app.window.settings["ignore-duplex-capabilities"])
    vbox.pack_start(cb_ignore_duplex, False, False, 0)

    # Force new scan job between pages
    cb_cancel_btw_pages = Gtk.CheckButton(label=_("Force new scan job between pages"))
    cb_cancel_btw_pages.set_tooltip_text(
        _(
            "Otherwise, some Brother scanners report out of documents, "
            "despite scanning from flatbed."
        )
    )
    cb_cancel_btw_pages.set_active(app.window.settings["cancel-between-pages"])
    vbox.pack_start(cb_cancel_btw_pages, False, False, 0)
    cb_cancel_btw_pages.set_sensitive(app.window.settings["allow-batch-flatbed"])
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
    cb_adf_all_pages.set_active(app.window.settings["adf-defaults-scan-all-pages"])
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
    cb_cache_device_list.set_active(app.window.settings["cache-device-list"])
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
    cbw.set_active(app.window.settings["restore window"])
    vbox.pack_start(cbw, True, True, 0)

    # View saved files
    cbv = Gtk.CheckButton(label=_("View files on saving"))
    cbv.set_active(app.window.settings["view files toggle"])
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
    fileentry.set_text(app.window.settings["default filename"])

    # Replace whitespace in filenames with underscores
    cbb = Gtk.CheckButton.new_with_label(
        _("Replace whitespace in filenames with underscores")
    )
    cbb.set_active(app.window.settings["convert whitespace to underscores"])
    vbox.pack_start(cbb, True, True, 0)

    # Timezone
    cbtz = Gtk.CheckButton.new_with_label(_("Use timezone from locale"))
    cbtz.set_active(app.window.settings["use_timezone"])
    vbox.pack_start(cbtz, True, True, 0)

    # Time
    cbtm = Gtk.CheckButton.new_with_label(_("Specify time as well as date"))
    cbtm.set_active(app.window.settings["use_time"])
    vbox.pack_start(cbtm, True, True, 0)

    # Set file timestamp with metadata
    cbts = Gtk.CheckButton.new_with_label(
        _("Set access and modification times to metadata date")
    )
    cbts.set_active(app.window.settings["set_timestamp"])
    vbox.pack_start(cbts, True, True, 0)

    # Convert scans from PNM to PNG
    cbtp = Gtk.CheckButton.new_with_label(
        _("Convert scanned images to PNG before further processing")
    )
    cbtp.set_active(app.window.settings["to_png"])
    vbox.pack_start(cbtp, True, True, 0)

    # Temporary directory settings
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Temporary directory"))
    hbox.pack_start(label, False, False, 0)
    tmpentry = Gtk.Entry()
    hbox.add(tmpentry)
    tmpentry.set_text(os.path.dirname(app.window.session.name))
    button = Gtk.Button(label=_("Browse"))

    def choose_temp_dir():
        file_chooser = Gtk.FileChooserDialog(
            title=_("Select temporary directory"),
            parent=app.window._windowr,
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
    spinbuttonw.set_value(app.window.settings["available-tmp-warning"])
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
    spinbuttonb.set_value(app.window.settings["Blank threshold"])
    spinbuttonb.set_tooltip_text(_("Threshold used for selecting blank pages"))
    hbox.add(spinbuttonb)

    # Dark page mean threshold
    hbox = Gtk.HBox()
    vbox.pack_start(hbox, True, True, 0)
    label = Gtk.Label(label=_("Dark threshold"))
    hbox.pack_start(label, False, False, 0)
    spinbuttond = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
    spinbuttond.set_value(app.window.settings["Dark threshold"])
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
    comboo.set_active_index(app.window.settings["OCR output"])
    hbox.pack_end(comboo, True, True, 0)

    # Manage user-defined tools
    frame = Gtk.Frame(label=_("Manage user-defined tools"))
    vbox.pack_start(frame, True, True, 0)
    vboxt = Gtk.VBox()
    vboxt.set_border_width(border_width)
    frame.add(vboxt)
    for tool in app.window.settings["user_defined_tools"]:
        add_user_defined_tool_entry(vboxt, [], tool)

    abutton = Gtk.Button()
    abutton.set_image(Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
    vboxt.pack_start(abutton, True, True, 0)

    def clicked_add_udt(_action):
        add_user_defined_tool_entry(
            vboxt, [comboboxudt, app.window._windows.comboboxudt], "my-tool %i %o"
        )
        vboxt.reorder_child(abutton, EMPTY_LIST)
        update_list_user_defined_tools(
            vboxt, [comboboxudt, app.window._windows.comboboxudt]
        )

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

    app.window.settings["user_defined_tools"] = tools
    app.window.update_post_save_hooks()
    for combobox in combobox_array:
        if combobox is not None:
            combobox.set_active_by_text(app.window.settings["current_udt"])


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


def get_selected_properties():
    "Helper function for properties()"
    page = app.window.slist.get_selected_indices()
    xresolution = None
    yresolution = None
    if len(page) > 0:
        i = page.pop(0)
        xresolution, yresolution, _units = app.window.slist.data[i][2].resolution
        logger.debug(
            "Page %s has resolutions %s,%s",
            app.window.slist.data[i][0],
            xresolution,
            yresolution,
        )

    for i in page:
        if app.window.slist.data[i][2].resolution[0] != xresolution:
            xresolution = None
            break

    for i in page:
        if app.window.slist.data[i][2].resolution[0] != yresolution:
            yresolution = None
            break

    # round the value to a sensible number of significant figures
    return xresolution, yresolution


def ask_question(**kwargs):
    "Helper function to display a message dialog, wait for a response, and return it"

    # replace any numbers with metacharacters to compare to filter
    text = filter_message(kwargs["text"])
    if response_stored(text, app.window.settings["message"]):
        logger.debug(
            f"Skipped MessageDialog with '{kwargs['text']}', "
            + f"automatically replying '{app.window.settings['message'][text]['response']}'"
        )
        return app.window.settings["message"][text]["response"]

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
            app.window.settings["message"][text]["response"] = response

    logger.debug("Replied '%s'", response)
    return response


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
    if app.window.can_quit():
        app.quit()


def select_odd(_action, _param):
    "Selects odd-numbered pages"
    select_odd_even(0)


def select_even(_action, _param):
    "Selects even-numbered pages"
    select_odd_even(1)


def zoom_100(_action, _param):
    "Sets the zoom level of the view to 100%."
    app.window.view.set_zoom(1.0)


def zoom_to_fit(_action, _param):
    "Adjusts the view to fit the content within the visible area."
    app.window.view.zoom_to_fit()


def zoom_in(_action, _param):
    "Zooms in the current view"
    app.window.view.zoom_in()


def zoom_out(_action, _param):
    "Zooms out the current view"
    app.window.view.zoom_out()


def rotate_90(_action, _param):
    "Rotates the selected pages by 90 degrees"
    rotate(_90_DEGREES, indices2pages(app.window.slist.get_selected_indices()))


def rotate_180(_action, _param):
    "Rotates the selected pages by 180 degrees"
    rotate(_180_DEGREES, indices2pages(app.window.slist.get_selected_indices()))


def rotate_270(_action, _param):
    "Rotates the selected pages by 270 degrees"
    rotate(_270_DEGREES, indices2pages(app.window.slist.get_selected_indices()))


class ApplicationWindow(Gtk.ApplicationWindow):
    "ApplicationWindow class"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = None
        self._configfile = None
        self._current_page = None
        self._current_ocr_bbox = None
        self._current_ann_bbox = None
        self._prevent_image_tool_update = False
        self._rotate_side_cmbx = None
        self._rotate_side_cmbx2 = None
        self.session = None  # session dir
        self._args = None  # GooCanvas for text layer
        self.view = None
        self.t_canvas = None  # GooCanvas for annotation layer
        self.a_canvas = None
        self._ocr_text_hbox = None
        self._ocr_textbuffer = None
        self._ann_hbox = None
        self._ann_textbuffer = None
        self._lockfd = None
        self.slist = None

        # These will be in the window group and have the "win" prefix
        for name, function in [
            ("new", new),
            ("open", open_dialog),
            ("open-session", open_session_action),
            ("scan", self.scan_dialog),
            ("save", self.save_dialog),
            ("email", self.email),
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
            ("properties", self.properties),
            ("preferences", self.preferences),
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
            ("crop-dialog", self.crop_dialog),
            ("crop-selection", crop_selection),
            ("split", split_dialog),
            ("unpaper", self.unpaper),
            ("ocr", self.ocr_dialog),
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
        actions["editmode"] = Gio.SimpleAction.new_stateful(
            "editmode", GLib.VariantType.new("s"), GLib.Variant.new_string("text")
        )

        # add the actions to the window that have window-classed callbacks
        self.add_action(actions["tooltype"])
        self.add_action(actions["viewtype"])
        self.add_action(actions["editmode"])

        # connect the action callback for tools and view
        actions["tooltype"].connect("activate", self._change_image_tool_cb)
        actions["viewtype"].connect("activate", self._change_view_cb)
        actions["editmode"].connect("activate", self._edit_mode_callback)

        self._pre_flight()
        self.print_settings = None
        self.renumber_dialog = None
        self._message_dialog = None
        self._windows = None
        self._windowc = None
        self._windowo = None
        self._windowu = None
        self._windowi = None
        self._windowe = None
        self._windowr = None
        self._windowp = None
        self.connect("delete-event", lambda w, e: not self.can_quit())

        def window_state_event_callback(_w, event):
            "Note when the window is maximised or not"
            self.settings["window_maximize"] = bool(
                event.new_window_state & Gdk.WindowState.MAXIMIZED
            )

        self.connect("window-state-event", window_state_event_callback)

        # If defined in the config file, set the window state, size and position
        if self.settings["restore window"]:
            self.set_default_size(
                self.settings["window_width"], self.settings["window_height"]
            )
            if "window_x" in self.settings and "window_y" in self.settings:
                self.move(self.settings["window_x"], self.settings["window_y"])

            if self.settings["window_maximize"]:
                self.maximize()

        try:
            self.set_icon_from_file(f"{self.get_application()._iconpath}/gscan2pdf.svg")
        except Exception as e:
            logger.warning(
                "Unable to load icon `%s/gscan2pdf.svg': %s",
                self.get_application()._iconpath,
                str(e),
            )

        self._thumb_popup = app.builder.get_object("thumb_popup")

        # app.add_window(window)
        self.populate_main_window()

    def _pre_flight(self):
        """
        Pre-flight initialization function that initialises variables,
        captures warnings, reads configuration, logs system information,
        and initializes various components.
        """
        self._args = parse_arguments()

        # Catch and log Python warnings
        logging.captureWarnings(True)

        # Suppress Warning: g_value_get_int: assertion 'G_VALUE_HOLDS_INT (value)' failed
        # from dialog.save.Save._meta_datetime_widget.set_text()
        # https://bugzilla.gnome.org/show_bug.cgi?id=708676
        warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

        self._read_config()
        if self.settings["cwd"] is None:
            self.settings["cwd"] = os.getcwd()
        self.settings["version"] = VERSION

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

        # initialise image control tool radio button setting
        self._change_image_tool_cb(
            actions["tooltype"], GLib.Variant("s", self.settings["image_control_tool"])
        )

        app = self.get_application()
        app.builder.get_object(
            "context_" + self.settings["image_control_tool"]
        ).set_active(True)
        app.set_menubar(app.builder.get_object("menubar"))

    def _read_config(self):
        "Read the configuration file"
        # config files: XDG_CONFIG_HOME/gscan2pdfrc or HOME/.config/gscan2pdfrc
        rcdir = (
            os.environ["XDG_CONFIG_HOME"]
            if "XDG_CONFIG_HOME" in os.environ
            else f"{os.environ['HOME']}/.config"
        )
        self._configfile = f"{rcdir}/{prog_name}rc"
        self.settings = config.read_config(self._configfile)
        config.add_defaults(self.settings)
        config.remove_invalid_paper(self.settings["Paper"])

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
        main_vbox = Gtk.VBox()
        self.add(main_vbox)

        # Set up a SimpleList
        self.slist = Document()

        # Update list in Document so that it can be used by get_resolution()
        self.slist.set_paper_sizes(self.settings["Paper"])

        # The temp directory has to be available before we start checking for
        # dependencies in order to be used for the pdftk check.
        self.create_temp_directory()

        # Create the toolbar
        main_vbox.pack_start(self.create_toolbar(), False, False, 0)

        # HPaned for thumbnails and detail view
        self._hpaned = Gtk.HPaned()
        self._hpaned.set_position(self.settings["thumb panel"])
        main_vbox.pack_start(self._hpaned, True, True, 0)

        # Scrolled window for thumbnails
        scwin_thumbs = Gtk.ScrolledWindow()

        # resize = FALSE to stop the panel expanding on being resized
        # (Debian #507032)
        self._hpaned.pack1(scwin_thumbs, False, True)
        scwin_thumbs.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scwin_thumbs.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        # If dragged below the bottom of the window, scroll it.
        self.slist.connect("drag-motion", drag_motion_callback)

        # Set up callback for right mouse clicks.
        self.slist.connect("button-press-event", self.handle_clicks)
        self.slist.connect("button-release-event", self.handle_clicks)
        scwin_thumbs.add(self.slist)

        # Notebook, split panes for detail view and OCR output
        self._vnotebook = Gtk.Notebook()
        self._hpanei = Gtk.HPaned()
        self._vpanei = Gtk.VPaned()
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

        self.view.connect("button-press-event", self.handle_clicks)
        self.view.connect("button-release-event", self.handle_clicks)

        def view_zoom_changed_callback(_view, zoom):
            if self.t_canvas is not None:
                self.t_canvas.handler_block(self.t_canvas.zoom_changed_signal)
                self.t_canvas.set_scale(zoom)
                self.t_canvas.handler_unblock(self.t_canvas.zoom_changed_signal)

        self.view.zoom_changed_signal = self.view.connect(
            "zoom-changed", view_zoom_changed_callback
        )

        def view_offset_changed_callback(_view, x, y):
            if self.t_canvas is not None:
                self.t_canvas.handler_block(self.t_canvas.offset_changed_signal)
                self.t_canvas.set_offset(x, y)
                self.t_canvas.handler_unblock(self.t_canvas.offset_changed_signal)

        self.view.offset_changed_signal = self.view.connect(
            "offset-changed", view_offset_changed_callback
        )

        def view_selection_changed_callback(_view, sel):
            "Callback if the selection changes"
            # copy required here because somehow the garbage collection
            # destroys the Gdk.Rectangle too early and afterwards, the
            # contents are corrupt.
            self.settings["selection"] = sel.copy()
            if sel is not None and self._windowc is not None:
                self._windowc.selection = self.settings["selection"]

        self.view.selection_changed_signal = self.view.connect(
            "selection-changed", view_selection_changed_callback
        )

        # GooCanvas for text layer
        self.t_canvas = Canvas()

        def text_zoom_changed_callback(canvas, _zoom):
            self.view.handler_block(self.view.zoom_changed_signal)
            self.view.set_zoom(canvas.get_scale())
            self.view.handler_unblock(self.view.zoom_changed_signal)

        self.t_canvas.zoom_changed_signal = self.t_canvas.connect(
            "zoom-changed", text_zoom_changed_callback
        )

        def text_offset_changed_callback():
            self.view.handler_block(self.view.offset_changed_signal)
            offset = self.t_canvas.get_offset()
            self.view.set_offset(offset["x"], offset["y"])
            self.view.handler_unblock(self.view.offset_changed_signal)

        self.t_canvas.offset_changed_signal = self.t_canvas.connect(
            "offset-changed", text_offset_changed_callback
        )

        # GooCanvas for annotation layer
        self.a_canvas = Canvas()

        def ann_zoom_changed_callback():
            self.view.handler_block(self.view.zoom_changed_signal)
            self.view.set_zoom(self.a_canvas.get_scale())
            self.view.handler_unblock(self.view.zoom_changed_signal)

        self.a_canvas.zoom_changed_signal = self.a_canvas.connect(
            "zoom-changed", ann_zoom_changed_callback
        )

        def ann_offset_changed_callback():
            self.view.handler_block(self.view.offset_changed_signal)
            offset = self.a_canvas.get_offset()
            self.view.set_offset(offset["x"], offset["y"])
            self.view.handler_unblock(self.view.offset_changed_signal)

        self.a_canvas.offset_changed_signal = self.a_canvas.connect(
            "offset-changed", ann_offset_changed_callback
        )

        # split panes for detail view/text layer canvas and text layer dialog
        self._vpaned = Gtk.VPaned()
        self._hpaned.pack2(self._vpaned, True, True)
        self._vpaned.show()
        self._ocr_text_hbox = Gtk.HBox()
        edit_vbox = Gtk.HBox()
        self._vpaned.pack2(edit_vbox, False, True)
        edit_vbox.pack_start(self._ocr_text_hbox, True, True, 0)
        ocr_textview = Gtk.TextView()
        ocr_textview.set_tooltip_text(_("Text layer"))
        self._ocr_textbuffer = ocr_textview.get_buffer()
        ocr_text_fbutton = Gtk.Button()
        ocr_text_fbutton.set_image(
            Gtk.Image.new_from_icon_name("go-first", Gtk.IconSize.BUTTON)
        )
        ocr_text_fbutton.set_tooltip_text(_("Go to least confident text"))
        ocr_text_fbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(self.t_canvas.get_first_bbox())
        )
        ocr_text_pbutton = Gtk.Button()
        ocr_text_pbutton.set_image(
            Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
        )
        ocr_text_pbutton.set_tooltip_text(_("Go to previous text"))
        ocr_text_pbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(self.t_canvas.get_previous_bbox())
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
                self.t_canvas.sort_by_confidence()
            else:
                self.t_canvas.sort_by_position()

        ocr_text_scmbx.connect("changed", changed_text_sort_method)
        ocr_text_scmbx.set_active(0)
        ocr_text_nbutton = Gtk.Button()
        ocr_text_nbutton.set_image(
            Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
        )
        ocr_text_nbutton.set_tooltip_text(_("Go to next text"))
        ocr_text_nbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(self.t_canvas.get_next_bbox())
        )
        ocr_text_lbutton = Gtk.Button()
        ocr_text_lbutton.set_image(
            Gtk.Image.new_from_icon_name("go-last", Gtk.IconSize.BUTTON)
        )
        ocr_text_lbutton.set_tooltip_text(_("Go to most confident text"))
        ocr_text_lbutton.connect(
            "clicked", lambda _: self.edit_ocr_text(self.t_canvas.get_last_bbox())
        )
        ocr_text_obutton = Gtk.Button.new_with_mnemonic(label=_("_OK"))
        ocr_text_obutton.set_tooltip_text(_("Accept corrections"))

        def ocr_text_button_clicked(_widget):
            take_snapshot()
            text = self._ocr_textbuffer.get_text(
                self._ocr_textbuffer.get_start_iter(),
                self._ocr_textbuffer.get_end_iter(),
                False,
            )
            logger.info("Corrected '%s'->'%s'", self._current_ocr_bbox.text, text)
            self._current_ocr_bbox.update_box(text, self.view.get_selection())
            self._current_page.import_hocr(self.t_canvas.hocr())
            self.edit_ocr_text(self._current_ocr_bbox)

        ocr_text_obutton.connect("clicked", ocr_text_button_clicked)
        ocr_text_cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        ocr_text_cbutton.set_tooltip_text(_("Cancel corrections"))
        ocr_text_cbutton.connect("clicked", lambda _: self._ocr_text_hbox.hide())
        ocr_text_ubutton = Gtk.Button.new_with_mnemonic(label=_("_Copy"))
        ocr_text_ubutton.set_tooltip_text(_("Duplicate text"))

        def ocr_text_copy(_widget):
            self._current_ocr_bbox = self.t_canvas.add_box(
                text=self._ocr_textbuffer.get_text(
                    self._ocr_textbuffer.get_start_iter(),
                    self._ocr_textbuffer.get_end_iter(),
                    False,
                ),
                bbox=self.view.get_selection(),
            )
            self._current_page.import_hocr(self.t_canvas.hocr())
            self.edit_ocr_text(self._current_ocr_bbox)

        ocr_text_ubutton.connect("clicked", ocr_text_copy)
        ocr_text_abutton = Gtk.Button()
        ocr_text_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        )
        ocr_text_abutton.set_tooltip_text(_("Add text"))

        def ocr_text_add(_widget):
            take_snapshot()
            text = self._ocr_textbuffer.get_text(
                self._ocr_textbuffer.get_start_iter(),
                self._ocr_textbuffer.get_end_iter(),
                False,
            )
            if text is None or text == EMPTY:
                text = _("my-new-word")

            # If we don't yet have a canvas, create one
            selection = self.view.get_selection()
            if hasattr(self._current_page, "text_layer"):
                logger.info("Added '%s'", text)
                self._current_ocr_bbox = self.t_canvas.add_box(
                    text=text, bbox=self.view.get_selection()
                )
                self._current_page.import_hocr(self.t_canvas.hocr())
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
                    self._current_ocr_bbox = self.t_canvas.get_first_bbox()
                    self.edit_ocr_text(self._current_ocr_bbox)

                create_txt_canvas(self._current_page, ocr_new_page)

        ocr_text_abutton.connect("clicked", ocr_text_add)
        ocr_text_dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        ocr_text_dbutton.set_tooltip_text(_("Delete text"))

        def ocr_text_delete(_widget):
            self._current_ocr_bbox.delete_box()
            self._current_page.import_hocr(self.t_canvas.hocr())
            self.edit_ocr_text(self.t_canvas.get_current_bbox())

        ocr_text_dbutton.connect("clicked", ocr_text_delete)
        self._ocr_text_hbox.pack_start(ocr_text_fbutton, False, False, 0)
        self._ocr_text_hbox.pack_start(ocr_text_pbutton, False, False, 0)
        self._ocr_text_hbox.pack_start(ocr_text_scmbx, False, False, 0)
        self._ocr_text_hbox.pack_start(ocr_text_nbutton, False, False, 0)
        self._ocr_text_hbox.pack_start(ocr_text_lbutton, False, False, 0)
        self._ocr_text_hbox.pack_start(ocr_textview, False, False, 0)
        self._ocr_text_hbox.pack_end(ocr_text_dbutton, False, False, 0)
        self._ocr_text_hbox.pack_end(ocr_text_cbutton, False, False, 0)
        self._ocr_text_hbox.pack_end(ocr_text_obutton, False, False, 0)
        self._ocr_text_hbox.pack_end(ocr_text_ubutton, False, False, 0)
        self._ocr_text_hbox.pack_end(ocr_text_abutton, False, False, 0)

        # split panes for detail view/text layer canvas and text layer dialog
        self._ann_hbox = Gtk.HBox()
        edit_vbox.pack_start(self._ann_hbox, True, True, 0)
        ann_textview = Gtk.TextView()
        ann_textview.set_tooltip_text(_("Annotations"))
        self._ann_textbuffer = ann_textview.get_buffer()
        ann_obutton = Gtk.Button.new_with_mnemonic(label=_("_Ok"))
        ann_obutton.set_tooltip_text(_("Accept corrections"))

        def ann_text_ok(_widget):
            text = self._ann_textbuffer.get_text(
                self._ann_textbuffer.get_start_iter(),
                self._ann_textbuffer.get_end_iter(),
                False,
            )
            logger.info("Corrected '%s'->'%s'", self._current_ann_bbox.text, text)
            self._current_ann_bbox.update_box(text, self.view.get_selection())
            self._current_page.import_annotations(self.a_canvas.hocr())
            self.edit_annotation(self._current_ann_bbox)

        ann_obutton.connect("clicked", ann_text_ok)
        ann_cbutton = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        ann_cbutton.set_tooltip_text(_("Cancel corrections"))
        ann_cbutton.connect("clicked", self._ann_hbox.hide)
        ann_abutton = Gtk.Button()
        ann_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        )
        ann_abutton.set_tooltip_text(_("Add annotation"))

        def ann_text_new(_widget):
            text = self._ann_textbuffer.get_text(
                self._ann_textbuffer.get_start_iter(),
                self._ann_textbuffer.get_end_iter(),
                False,
            )
            if text is None or text == EMPTY:
                text = _("my-new-annotation")

            # If we don't yet have a canvas, create one
            selection = self.view.get_selection()
            if hasattr(self._current_page, "text_layer"):
                logger.info("Added '%s'", text)
                self._current_ann_bbox = self.a_canvas.add_box(
                    text=text, bbox=self.view.get_selection()
                )
                self._current_page.import_annotations(self.a_canvas.hocr())
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
                    self._current_ann_bbox = self.a_canvas.get_first_bbox()
                    self.edit_annotation(self._current_ann_bbox)

                create_ann_canvas(self._current_page, ann_text_new_page)

        ann_abutton.connect("clicked", ann_text_new)
        ann_dbutton = Gtk.Button.new_with_mnemonic(label=_("_Delete"))
        ann_dbutton.set_tooltip_text(_("Delete annotation"))

        def ann_text_delete(_widget):
            self._current_ann_bbox.delete_box()
            self._current_page.import_hocr(self.a_canvas.hocr())
            self.edit_annotation(self.t_canvas.get_bbox_by_index())

        ann_dbutton.connect("clicked", ann_text_delete)
        self._ann_hbox.pack_start(ann_textview, False, False, 0)
        self._ann_hbox.pack_end(ann_dbutton, False, False, 0)
        self._ann_hbox.pack_end(ann_cbutton, False, False, 0)
        self._ann_hbox.pack_end(ann_obutton, False, False, 0)
        self._ann_hbox.pack_end(ann_abutton, False, False, 0)
        self._pack_viewer_tools()

        # Set up call back for list selection to update detail view
        self.slist.selection_changed_signal = self.slist.get_selection().connect(
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
        if "cwd" not in self.settings:
            self.settings["cwd"] = os.getcwd()
        self._unpaper = Unpaper(self.settings["unpaper options"])
        self.update_uimanager()
        self.show_all()

        # Progress bars below window
        phbox = Gtk.HBox()
        main_vbox.pack_end(phbox, False, False, 0)
        phbox.show()
        self._scan_progress = Progress()
        phbox.add(self._scan_progress)
        self.post_process_progress = Progress()
        phbox.add(self.post_process_progress)

        # OCR text editing interface
        self._ocr_text_hbox.show()
        self._ann_hbox.hide()

        # Open scan dialog in background
        if self.settings["auto-open-scan-dialog"]:
            self.scan_dialog(None, None, True)

        # Deal with --import command line option
        if self._args.import_files is not None:
            import_files(self._args.import_files)
        if self._args.import_all is not None:
            import_files(self._args.import_all, True)

    def create_toolbar(self):
        "Create the menu bar, initialize its menus, and return the menu bar"

        # Check for presence of various packages
        self.check_dependencies()

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
            self.show_message_dialog(
                parent=self,
                message_type="warning",
                buttons=Gtk.ButtonsType.OK,
                text=msg,
                store_response=True,
            )

        # extract the toolbar
        toolbar = app.builder.get_object("toolbar")

        # turn off labels
        settings = toolbar.get_settings()
        settings.gtk_toolbar_style = "icons"  # only icons
        return toolbar

    def _pack_viewer_tools(self):
        "Pack widgets according to viewer_tools"
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

    def handle_clicks(self, widget, event):
        "Handle right-clicks"
        if event.button == 3:  # RIGHT_MOUSE_BUTTON
            if isinstance(widget, ImageView):  # main image
                app.detail_popup.show_all()
                app.detail_popup.popup_at_pointer(event)
            else:  # Thumbnail simplelist
                self.settings["Page range"] = "selected"
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
        button = app.builder.get_object(f"context_{value}")
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

    def _edit_mode_callback(self, action, parameter):
        "Show/hide the edit tools"
        action.set_state(parameter)
        if parameter.get_string() == "text":
            self._ocr_text_hbox.show()
            self._ann_hbox.hide()
            return
        self._ocr_text_hbox.hide()
        self._ann_hbox.show()

    def edit_ocr_text(self, widget, _target=None, ev=None, bbox=None):
        "Edit OCR text"
        logger.debug("edit_ocr_text(%s, %s, %s, %s)", widget, _target, ev, bbox)
        if not ev:
            bbox = widget

        if bbox is None:
            return

        self._current_ocr_bbox = bbox
        self._ocr_textbuffer.set_text(bbox.text)
        self._ocr_text_hbox.show_all()
        self.view.set_selection(bbox.bbox)
        self.view.set_zoom_to_fit(False)
        self.view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            self.t_canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            self.t_canvas.set_index_by_bbox(bbox)

    def edit_annotation(self, widget, _target=None, ev=None, bbox=None):
        "Edit annotation"
        if not ev:
            bbox = widget

        self._current_ann_bbox = bbox
        self._ann_textbuffer.set_text(bbox.text)
        self._ann_hbox.show_all()
        self.view.set_selection(bbox.bbox)
        self.view.set_zoom_to_fit(False)
        self.view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
        if ev:
            self.a_canvas.pointer_ungrab(widget, ev.time())

        if bbox:
            self.a_canvas.set_index_by_bbox(bbox)

    def update_uimanager(self):
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
            if action_name in actions:
                actions[action_name].set_enabled(enabled)
        app.detail_popup.set_sensitive(enabled)

        # Ghost unpaper item if unpaper not available
        if not dependencies["unpaper"]:
            actions["unpaper"].set_enabled(False)
            del actions["unpaper"]

        # Ghost ocr item if ocr  not available
        if not dependencies["ocr"]:
            actions["ocr"].set_enabled(False)

        if len(self.slist.data) > 0:
            if dependencies["xdg"]:
                actions["email"].set_enabled(True)

            actions["print"].set_enabled(True)
            actions["save"].set_enabled(True)

        else:
            if dependencies["xdg"]:
                actions["email"].set_enabled(False)
                if self._windowe is not None:
                    self._windowe.hide()

            actions["print"].set_enabled(False)
            actions["save"].set_enabled(False)

        actions["paste"].set_enabled(bool(self.slist.clipboard))

        # If the scan dialog has already been drawn, update the start page spinbutton
        if self._windows:
            self._windows._update_start_page()

    def create_temp_directory(self):
        "Create a temporary directory for the session"
        tmpdir = get_tmp_dir(self.settings["TMPDIR"], r"gscan2pdf-\w\w\w\w")
        self.find_crashed_sessions(tmpdir)

        # Create temporary directory if necessary
        if self.session is None:
            if tmpdir is not None and tmpdir != EMPTY:
                if not os.path.isdir(tmpdir):
                    os.mkdir(tmpdir)
                try:
                    self.session = tempfile.TemporaryDirectory(
                        prefix="gscan2pdf-", dir=tmpdir
                    )
                except:
                    self.session = tempfile.TemporaryDirectory(prefix="gscan2pdf-")
            else:
                self.session = (
                    tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
                        prefix="gscan2pdf-"
                    )
                )

            self.slist.set_dir(self.session.name)
            self._lockfd = self.create_lockfile()
            self.slist.save_session()
            logger.info("Using %s for temporary files", self.session.name)
            tmpdir = os.path.dirname(self.session.name)
            if "TMPDIR" in self.settings and self.settings["TMPDIR"] != tmpdir:
                logger.warning(
                    _(
                        "Warning: unable to use %s for temporary storage. Defaulting to %s instead."
                    ),
                    self.settings["TMPDIR"],
                    tmpdir,
                )
                self.settings["TMPDIR"] = tmpdir

    def create_lockfile(self):
        "create a lockfile in the session directory"
        lockfd = open(
            os.path.join(self.session.name, "lockfile"), "w", encoding="utf-8"
        )
        fcntl.lockf(lockfd, fcntl.LOCK_EX)
        return lockfd

    def check_dependencies(self):
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
            [
                "graphicsmagick",
                "stdout",
                r"GraphicsMagick\s([\d.-]+)",
                ["gm", "-version"],
            ],
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
                self.show_message_dialog(
                    parent=self,
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
                        dir=self.session.name, suffix=".jpg"
                    ) as tempimg:
                        exec_command(["convert", "rose:", tempimg.name])
                    with tempfile.NamedTemporaryFile(
                        dir=self.session.name, suffix=".pdf"
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
                        self.show_message_dialog(
                            parent=self,
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

    def find_crashed_sessions(self, tmpdir):
        "Look for crashed sessions"
        if tmpdir is None or tmpdir == EMPTY:
            tmpdir = tempfile.gettempdir()

        logger.info("Checking %s for crashed sessions", tmpdir)
        sessions = glob.glob(os.path.join(tmpdir, "gscan2pdf-????"))
        crashed, selected = [], []

        # Forget those used by running sessions
        for session in sessions:
            try:
                self.create_lockfile()
                crashed.append(session)
            except Exception as e:
                logger.warning("Error opening lockfile %s", str(e))

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
                transient_for=self,
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
                transient_for=self,
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
                self.session = crashed[selected]
                self.create_lockfile()
                self.slist.set_dir(self.session)
                open_session(self.session)

    def show_message_dialog(self, **kwargs):
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

    def properties(self, _action, _param):
        "Display and manage the properties dialog for setting X and Y resolution."
        if self._windowp is not None:
            self._windowp.present()
            return

        self._windowp = Dialog(
            transient_for=self,
            title=_("Properties"),
            hide_on_delete=True,
        )
        vbox = self._windowp.get_content_area()
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
            logger.debug(
                "get_selected_properties returned %s,%s", xresolution, yresolution
            )
            xspinbutton.set_value(xresolution)
            yspinbutton.set_value(yresolution)

        self.slist.get_selection().connect("changed", selection_changed_callback)

        def properties_apply_callback():
            self._windowp.hide()
            xresolution = xspinbutton.get_value()
            yresolution = yspinbutton.get_value()
            self.slist.get_model().handler_block(self.slist.row_changed_signal)
            for i in self.slist.get_selected_indices():
                logger.debug(
                    "setting resolution %s,%s for page %s",
                    xresolution,
                    yresolution,
                    self.slist.data[i][0],
                )
                self.slist.data[i][2].resolution = (
                    xresolution,
                    yresolution,
                    "PixelsPerInch",
                )

            self.slist.get_model().handler_unblock(self.slist.row_changed_signal)

        self._windowp.add_actions(
            [("gtk-ok", properties_apply_callback), ("gtk-cancel", self._windowp.hide)]
        )
        self._windowp.show_all()

    def scan_dialog(self, _action, _param, hidden=False, scan=False):
        "Scan"
        if self._windows:
            self._windows.show_all()
            self.update_postprocessing_options_callback(self._windows)
            return

        # If device not set by config and there is a default device, then set it
        if "device" not in self.settings and "SANE_DEFAULT_DEVICE" in os.environ:
            self.settings["device"] = os.environ["SANE_DEFAULT_DEVICE"]

        # scan dialog
        kwargs = {
            "transient_for": self,
            "title": _("Scan Document"),
            "dir": self.session,
            "hide_on_delete": True,
            "paper_formats": self.settings["Paper"],
            "allow_batch_flatbed": self.settings["allow-batch-flatbed"],
            "adf_defaults_scan_all_pages": self.settings["adf-defaults-scan-all-pages"],
            "document": self.slist,
            "ignore_duplex_capabilities": self.settings["ignore-duplex-capabilities"],
            "cycle_sane_handle": self.settings["cycle sane handle"],
            "cancel_between_pages": (
                self.settings["allow-batch-flatbed"]
                and self.settings["cancel-between-pages"]
            ),
        }
        if self.settings["scan_window_width"]:
            kwargs["default_width"] = self.settings["scan_window_width"]
        if self.settings["scan_window_height"]:
            kwargs["default_height"] = self.settings["scan_window_height"]
        self._windows = SaneScanDialog(**kwargs)

        # Can't set the device when creating the window,
        # as the list does not exist then
        self._windows.connect("changed-device-list", self.changed_device_list_callback)

        # Update default device
        self._windows.connect("changed-device", self.changed_device_callback)
        self._windows.connect(
            "changed-page-number-increment", self.update_postprocessing_options_callback
        )
        self._windows.connect("changed-side-to-scan", changed_side_to_scan_callback)
        signal = None

        def started_progress_callback(_widget, message):
            logger.debug("'started-process' emitted with message: %s", message)
            self._scan_progress.set_fraction(0)
            self._scan_progress.set_text(message)
            self._scan_progress.show_all()
            nonlocal signal
            signal = self._scan_progress.connect("clicked", self._windows.cancel_scan)

        self._windows.connect("started-process", started_progress_callback)
        self._windows.connect("changed-progress", changed_progress_callback)
        self._windows.connect("finished-process", self.finished_process_callback)
        self._windows.connect("process-error", self.process_error_callback, signal)

        # Profiles
        for profile in self.settings["profile"].keys():
            self._windows._add_profile(
                profile,
                Profile(
                    frontend=self.settings["profile"][profile]["frontend"],
                    backend=self.settings["profile"][profile]["backend"],
                ),
            )

        def changed_profile_callback(_widget, profile):
            self.settings["default profile"] = profile

        self._windows.connect("changed-profile", changed_profile_callback)

        def added_profile_callback(_widget, name, profile):
            self.settings["profile"][name] = profile.get()

        self._windows.connect("added-profile", added_profile_callback)

        def removed_profile_callback(_widget, profile):
            del self.settings["profile"][profile]

        self._windows.connect("removed-profile", removed_profile_callback)

        def changed_current_scan_options_callback(_widget, profile, _uuid):
            "Update the default profile when the scan options change"
            self.settings["default-scan-options"] = profile.get()

        self._windows.connect(
            "changed-current-scan-options", changed_current_scan_options_callback
        )

        def changed_paper_formats_callback(_widget, formats):
            self.settings["Paper"] = formats

        self._windows.connect("changed-paper-formats", changed_paper_formats_callback)
        self._windows.connect("new-scan", new_scan_callback)
        self._windows.connect(
            "changed-scan-option", self.update_postprocessing_options_callback
        )
        self.add_postprocessing_options(self._windows)
        if not hidden:
            self._windows.show_all()
        self.update_postprocessing_options_callback(self._windows)
        if self._args.device:
            device_list = []
            for d in self._args.device:
                device_list.append(SimpleNamespace(name=d, label=d))

            self._windows.device_list = device_list

        elif (
            not scan
            and self.settings["cache-device-list"]
            and len(self.settings["device list"])
        ):
            self._windows.device_list = self.settings["device list"]
        else:
            self._windows.get_devices()

    def add_postprocessing_options(self, widget):
        "Adds post-processing options to the dialog window."
        scwin = Gtk.ScrolledWindow()
        widget.notebook.append_page(scwin, Gtk.Label(label=_("Postprocessing")))
        scwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vboxp = Gtk.VBox()
        vboxp.set_border_width(widget.get_border_width())
        scwin.add(vboxp)

        # Rotate
        rbutton, r2button, comboboxr, comboboxr2 = self.add_postprocessing_rotate(vboxp)

        # CheckButton for unpaper
        hboxu = Gtk.HBox()
        vboxp.pack_start(hboxu, False, False, 0)
        ubutton = Gtk.CheckButton(label=_("Clean up images"))
        ubutton.set_tooltip_text(_("Clean up scanned images with unpaper"))
        hboxu.pack_start(ubutton, True, True, 0)
        if not dependencies["unpaper"]:
            ubutton.set_sensitive(False)
            ubutton.set_active(False)
        elif self.settings["unpaper on scan"]:
            ubutton.set_active(True)

        button = Gtk.Button(label=_("Options"))
        button.set_tooltip_text(_("Set unpaper options"))
        hboxu.pack_end(button, True, True, 0)

        def show_unpaper_options():
            windowuo = Dialog(
                transient_for=self,
                title=_("unpaper options"),
            )
            self._unpaper.add_options(windowuo.get_content_area())

            def unpaper_options_callback():

                # Update $self.settings
                self.settings["unpaper options"] = self._unpaper.get_options()
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
        udtbutton, widget.comboboxudt = self.add_postprocessing_udt(vboxp)
        obutton, comboboxe, hboxtl, comboboxtl, tbutton, tsb = (
            self.add_postprocessing_ocr(vboxp)
        )

        def clicked_scan_button_cb(w):
            self.settings["rotate facing"] = 0
            self.settings["rotate reverse"] = 0
            if rbutton.get_active():
                if self._rotate_side_cmbx.get_active_index() == "both":
                    self.settings["rotate facing"] = comboboxr.get_active_index()
                    self.settings["rotate reverse"] = self.settings["rotate facing"]

                elif self._rotate_side_cmbx.get_active_index() == "facing":
                    self.settings["rotate facing"] = comboboxr.get_active_index()

                else:
                    self.settings["rotate reverse"] = comboboxr.get_active_index()

                if r2button.get_active():
                    if self._rotate_side_cmbx2.get_active_index() == "facing":
                        self.settings["rotate facing"] = comboboxr2.get_active_index()

                    else:
                        self.settings["rotate reverse"] = comboboxr2.get_active_index()

            logger.info("rotate facing %s", self.settings["rotate facing"])
            logger.info("rotate reverse %s", self.settings["rotate reverse"])
            self.settings["unpaper on scan"] = ubutton.get_active()
            logger.info("unpaper %s", self.settings["unpaper on scan"])
            self.settings["udt_on_scan"] = udtbutton.get_active()
            self.settings["current_udt"] = widget.comboboxudt.get_active_text()
            logger.info("UDT %s", self.settings["udt_on_scan"])
            if "current_udt" in self.settings:
                logger.info("Current UDT %s", self.settings["current_udt"])

            self.settings["OCR on scan"] = obutton.get_active()
            logger.info("OCR %s", self.settings["OCR on scan"])
            if self.settings["OCR on scan"]:
                self.settings["ocr engine"] = comboboxe.get_active_index()
                if self.settings["ocr engine"] is None:
                    self.settings["ocr engine"] = ocr_engine[0][0]
                logger.info("ocr engine %s", self.settings["ocr engine"])
                if self.settings["ocr engine"] == "tesseract":
                    self.settings["ocr language"] = comboboxtl.get_active_index()
                    logger.info("ocr language %s", self.settings["ocr language"])

                self.settings["threshold-before-ocr"] = tbutton.get_active()
                logger.info(
                    "threshold-before-ocr %s", self.settings["threshold-before-ocr"]
                )
                self.settings["threshold tool"] = tsb.get_value()

        widget.connect("clicked-scan-button", clicked_scan_button_cb)

        def show_callback(_w):
            i = comboboxe.get_active()
            if i > -1 and hboxtl is not None and ocr_engine[i][0] != "tesseract":
                hboxtl.hide()

        widget.connect("show", show_callback)
        # self->{notebook}->get_nth_page(1)->show_all;

    def add_postprocessing_udt(self, vboxp):
        "Adds a user-defined tool (UDT) post-processing option to the given VBox."
        hboxudt = Gtk.HBox()
        vboxp.pack_start(hboxudt, False, False, 0)
        udtbutton = Gtk.CheckButton(label=_("Process with user-defined tool"))
        udtbutton.set_tooltip_text(_("Process scanned images with user-defined tool"))
        hboxudt.pack_start(udtbutton, True, True, 0)
        if not self.settings["user_defined_tools"]:
            hboxudt.set_sensitive(False)
            udtbutton.set_active(False)

        elif self.settings["udt_on_scan"]:
            udtbutton.set_active(True)

        return udtbutton, self.add_udt_combobox(hboxudt)

    def add_udt_combobox(self, hbox):
        "Adds a ComboBoxText widget to the given hbox containing user-defined tools."
        toolarray = []
        for t in self.settings["user_defined_tools"]:
            toolarray.append([t, t])

        combobox = ComboBoxText(data=toolarray)
        combobox.set_active_index(self.settings["current_udt"])
        hbox.pack_start(combobox, True, True, 0)
        return combobox

    def add_postprocessing_ocr(self, vbox):
        "Adds post-processing OCR options to the given vbox."
        hboxo = Gtk.HBox()
        vbox.pack_start(hboxo, False, False, 0)
        obutton = Gtk.CheckButton(label=_("OCR scanned pages"))
        obutton.set_tooltip_text(_("OCR scanned pages"))
        if not dependencies["ocr"]:
            hboxo.set_sensitive(False)
            obutton.set_active(False)

        elif self.settings["OCR on scan"]:
            obutton.set_active(True)

        hboxo.pack_start(obutton, True, True, 0)
        comboboxe = ComboBoxText(data=ocr_engine)
        comboboxe.set_tooltip_text(_("Select OCR engine"))
        hboxo.pack_end(comboboxe, True, True, 0)
        comboboxtl, hboxtl = None, None

        if dependencies["tesseract"]:
            hboxtl, comboboxtl, _tesslang = self.add_tess_languages(vbox)

            def ocr_engine_changed_callback(comboboxe):
                if comboboxe.get_active_text() == "tesseract":
                    hboxtl.show_all()
                else:
                    hboxtl.hide()

            comboboxe.connect("changed", ocr_engine_changed_callback)
            if not obutton.get_active():
                hboxtl.set_sensitive(False)

            obutton.connect("toggled", lambda x: hboxtl.set_sensitive(x.get_active()))

        comboboxe.set_active_index(self.settings["ocr engine"])
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
        cbto.set_active(self.settings["threshold-before-ocr"])
        hboxt.pack_start(cbto, False, True, 0)
        labelp = Gtk.Label(label=PERCENT)
        hboxt.pack_end(labelp, False, True, 0)
        spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbutton.set_value(self.settings["threshold tool"])
        spinbutton.set_sensitive(cbto.get_active())
        hboxt.pack_end(spinbutton, False, True, 0)
        cbto.connect("toggled", lambda _: spinbutton.set_sensitive(cbto.get_active()))
        return obutton, comboboxe, hboxtl, comboboxtl, cbto, spinbutton

    def add_tess_languages(self, vbox):
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
        combobox.set_active_index(self.settings["ocr language"])
        if not combobox.get_active_index():
            combobox.set_active(0)
        hbox.pack_end(combobox, False, True, 0)
        return hbox, combobox, tesslang

    def changed_device_callback(self, widget, device):
        "callback for changed device"
        # widget is windows
        if device != EMPTY:
            logger.info("signal 'changed-device' emitted with data: '%s'", device)
            self.settings["device"] = device

            # Can't set the profile until the options have been loaded. This
            # should only be called the first time after loading the available
            # options
            widget.reloaded_signal = widget.connect(
                "reloaded-scan-options", self.reloaded_scan_options_callback
            )
        else:
            logger.info("signal 'changed-device' emitted with data: undef")

    def changed_device_list_callback(self, widget, device_list):  # widget is windows
        "callback for changed device list"
        logger.info("signal 'changed-device-list' emitted with data: %s", device_list)
        if len(device_list):

            # Apply the device blacklist
            if "device blacklist" in self.settings and self.settings[
                "device blacklist"
            ] not in [
                None,
                "",
            ]:
                i = 0
                while i < len(device_list):
                    if re.search(
                        device_list[i].name,
                        self.settings["device blacklist"],
                        re.MULTILINE | re.DOTALL | re.VERBOSE,
                    ):
                        logger.info("Blacklisting device %s", device_list[i].name)
                        del device_list[i]
                    else:
                        i += 1

                if len(device_list) < len(device_list):
                    widget.device_list = device_list
                    return

            if self.settings["cache-device-list"]:
                self.settings["device list"] = device_list

            # Only set default device if it hasn't been specified on the command line
            # and it is in the the device list
            if "device" in self.settings:
                for d in device_list:
                    if self.settings["device"] == d.name:
                        widget.device = self.settings["device"]
                        return

            widget.device = device_list[0].name

        else:
            self._windows = None

    def add_postprocessing_rotate(self, vbox):
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
        self._rotate_side_cmbx = ComboBoxText(data=side)
        self._rotate_side_cmbx.set_tooltip_text(_("Select side to rotate"))
        hboxr.pack_start(self._rotate_side_cmbx, True, True, 0)
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
        self._rotate_side_cmbx2 = Gtk.ComboBoxText()
        self._rotate_side_cmbx2.set_tooltip_text(_("Select side to rotate"))
        hboxr.pack_start(self._rotate_side_cmbx2, True, True, 0)
        comboboxr2 = ComboBoxText(data=rotate)
        comboboxr2.set_tooltip_text(_("Select direction of rotation"))
        hboxr.pack_end(comboboxr2, True, True, 0)

        def toggled_rotate_callback():
            if rbutton.get_active():
                if side[self._rotate_side_cmbx.get_active()][0] != "both":
                    hboxr.set_sensitive(True)
            else:
                hboxr.set_sensitive(False)

        rbutton.connect("toggled", toggled_rotate_callback)

        def toggled_rotate_side_callback(_arg):
            if side[self._rotate_side_cmbx.get_active()][0] == "both":
                hboxr.set_sensitive(False)
                r2button.set_active(False)
            else:
                if rbutton.get_active():
                    hboxr.set_sensitive(True)

                    # Empty combobox
                while self._rotate_side_cmbx2.get_active() > EMPTY_LIST:
                    self._rotate_side_cmbx2.remove(0)
                    self._rotate_side_cmbx2.set_active(0)

                side2 = []
                for s in side:
                    if (
                        s[0] != "both"
                        and s[0] != side[self._rotate_side_cmbx.get_active()][0]
                    ):
                        side2.append(s)

                self._rotate_side_cmbx2.append_text(side2[0][1])
                self._rotate_side_cmbx2.set_active(0)

        self._rotate_side_cmbx.connect("changed", toggled_rotate_side_callback)

        # In case it isn't set elsewhere
        comboboxr2.set_active_index(_90_DEGREES)
        if self.settings["rotate facing"] or self.settings["rotate reverse"]:
            rbutton.set_active(True)

        if self.settings["rotate facing"] == self.settings["rotate reverse"]:
            self._rotate_side_cmbx.set_active_index("both")
            comboboxr.set_active_index(self.settings["rotate facing"])

        elif self.settings["rotate facing"]:
            self._rotate_side_cmbx.set_active_index("facing")
            comboboxr.set_active_index(self.settings["rotate facing"])
            if self.settings["rotate reverse"]:
                r2button.set_active(True)
                self._rotate_side_cmbx2.set_active_index("reverse")
                comboboxr2.set_active_index(self.settings["rotate reverse"])

        else:
            self._rotate_side_cmbx.set_active_index("reverse")
            comboboxr.set_active_index(self.settings["rotate reverse"])

        return rbutton, r2button, comboboxr, comboboxr2

    def update_postprocessing_options_callback(
        self, widget, _option_name=None, _option_val=None, _uuid=None
    ):
        "update the visibility of post-processing options based on the widget's scan options."
        # widget is windows
        options = widget.available_scan_options
        increment = widget.page_number_increment
        if options is not None:
            if increment != 1 or options.can_duplex():
                self._rotate_side_cmbx.show()
                self._rotate_side_cmbx2.show()

            else:
                self._rotate_side_cmbx.hide()
                self._rotate_side_cmbx2.hide()

    def reloaded_scan_options_callback(self, widget):  # widget is windows
        "This should only be called the first time after loading the available options"
        widget.disconnect(widget.reloaded_signal)
        profiles = self.settings["profile"].keys()
        if "default profile" in self.settings:
            widget.profile = self.settings["default profile"]

        elif "default-scan-options" in self.settings:
            widget.set_current_scan_options(
                Profile(self.settings["default-scan-options"])
            )

        elif profiles:
            widget.profile = profiles[0]

        self.update_postprocessing_options_callback(widget)

    def process_error_callback(self, widget, process, msg, signal):
        "Callback function to handle process errors."
        logger.info("signal 'process-error' emitted with data: %s %s", process, msg)
        if signal is not None:
            self._scan_progress.disconnect(signal)

        self._scan_progress.hide()
        if process == "open_device" and re.search(
            r"(Invalid[ ]argument|Device[ ]busy)",
            msg,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
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
                radio2 = Gtk.RadioButton.new_with_label_from_widget(
                    radio1, label=_("Rescan for devices")
                )
                area.add(radio2)
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
                restart()

            # for ignore, we do nothing
            return

        self.show_message_dialog(
            parent=widget,
            message_type="error",
            buttons=Gtk.ButtonsType.CLOSE,
            page=EMPTY,
            process=process,
            text=msg,
            store_response=True,
        )

    def finished_process_callback(self, widget, process, button_signal=None):
        "Callback function to handle the completion of a process."
        logger.debug("signal 'finished-process' emitted with data: %s", process)
        if button_signal is not None:
            self._scan_progress.disconnect(button_signal)

        self._scan_progress.hide()
        if process == "scan_pages" and widget.sided == "double":

            def prompt_reverse_sides():
                message, side = None, None
                if widget.side_to_scan == "facing":
                    message = _("Finished scanning facing pages. Scan reverse pages?")
                    side = "reverse"
                else:
                    message = _("Finished scanning reverse pages. Scan facing pages?")
                    side = "facing"

                response = ask_question(
                    parent=widget,
                    type="question",
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=message,
                    default_response=Gtk.ResponseType.OK,
                    store_response=True,
                    stored_responses=[Gtk.ResponseType.OK],
                )
                if response == Gtk.ResponseType.OK:
                    widget.side_to_scan = side

            GLib.idle_add(prompt_reverse_sides)

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
        about.set_transient_for(self)
        about.run()
        about.destroy()

    def crop_dialog(self, _action, _param):
        "Display page selector and on apply crop accordingly"
        if self._windowc is not None:
            self._windowc.present()
            return

        width, height = self._current_page.get_size()
        self._windowc = Crop(transient_for=self, page_width=width, page_height=height)

        def on_changed_selection(_widget, selection):
            # copy required here because somehow the garbage collection
            # destroys the Gdk.Rectangle too early and afterwards, the
            # contents are corrupt.
            self.settings["selection"] = selection.copy()
            self.view.handler_block(self.view.selection_changed_signal)
            self.view.set_selection(selection)
            self.view.handler_unblock(self.view.selection_changed_signal)

        self._windowc.connect("changed-selection", on_changed_selection)

        if self.settings["selection"]:
            self._windowc.selection = self.settings["selection"]

        def crop_callback():
            self.settings["Page range"] = self._windowc.page_range
            crop_selection(
                None,  # action
                None,  # param
                self.slist.get_page_index(self.settings["Page range"], error_callback),
            )

        self._windowc.add_actions(
            [("gtk-apply", crop_callback), ("gtk-cancel", self._windowc.hide)]
        )
        self._windowc.show_all()

    def unpaper(self, _action, _param):
        "Run unpaper to clean up scan."
        if self._windowu is not None:
            self._windowu.present()
            return

        self._windowu = Dialog(
            transient_for=self,
            title=_("unpaper"),
            hide_on_delete=True,
        )

        # Frame for page range
        self._windowu.add_page_range()

        # add unpaper options
        vbox = self._windowu.get_content_area()
        self._unpaper.add_options(vbox)

        def unpaper_apply_callback():

            # Update $self.settings
            self.settings["unpaper options"] = self._unpaper.get_options()
            self.settings["Page range"] = self._windowu.page_range

            # run unpaper
            pagelist = indices2pages(
                self.slist.get_page_index(self.settings["Page range"], error_callback)
            )
            if not pagelist:
                return
            unpaper_page(
                pagelist,
                {
                    "command": self._unpaper.get_cmdline(),
                    "direction": self._unpaper.get_option("direction"),
                },
            )
            self._windowu.hide()

        self._windowu.add_actions(
            [("gtk-ok", unpaper_apply_callback), ("gtk-cancel", self._windowu.hide)]
        )
        self._windowu.show_all()

    def ocr_dialog(self, _action, _parma):
        "Run OCR on current page and display result"
        if self._windowo is not None:
            self._windowo.present()
            return

        self._windowo = Dialog(
            transient_for=self,
            title=_("OCR"),
            hide_on_delete=True,
        )

        # Frame for page range
        self._windowo.add_page_range()

        # OCR engine selection
        hboxe = Gtk.HBox()
        vbox = self._windowo.get_content_area()
        vbox.pack_start(hboxe, False, True, 0)
        label = Gtk.Label(label=_("OCR Engine"))
        hboxe.pack_start(label, False, True, 0)
        combobe = ComboBoxText(data=ocr_engine)
        combobe.set_active_index(self.settings["ocr engine"])
        hboxe.pack_end(combobe, False, True, 0)
        comboboxtl, hboxtl, tesslang = None, None, []
        if dependencies["tesseract"]:
            hboxtl, comboboxtl, tesslang = self.add_tess_languages(vbox)

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
        if "threshold-before-ocr" in self.settings:
            cbto.set_active(self.settings["threshold-before-ocr"])

        hboxt.pack_start(cbto, False, True, 0)
        labelp = Gtk.Label(label=PERCENT)
        hboxt.pack_end(labelp, False, True, 0)
        spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbutton.set_value(self.settings["threshold tool"])
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

        self._windowo.add_actions(
            [("gtk-ok", ocr_apply_callback), ("gtk-cancel", self._windowo.hide)]
        )
        self._windowo.show_all()
        if hboxtl is not None and ocr_engine[combobe.get_active()][0] != "tesseract":
            hboxtl.hide()

    def save_dialog(self, _action, _param):
        "Display page selector and on save a fileselector."
        if self._windowi is not None:
            self._windowi.present()
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

        self._windowi = SaveDialog(
            transient_for=self,
            title=_("Save"),
            hide_on_delete=True,
            page_range=self.settings["Page range"],
            include_time=self.settings["use_time"],
            meta_datetime=datetime.datetime.now() + self.settings["datetime offset"],
            select_datetime=bool(self.settings["datetime offset"]),
            meta_title=self.settings["title"],
            meta_title_suggestions=self.settings["title-suggestions"],
            meta_author=self.settings["author"],
            meta_author_suggestions=self.settings["author-suggestions"],
            meta_subject=self.settings["subject"],
            meta_subject_suggestions=self.settings["subject-suggestions"],
            meta_keywords=self.settings["keywords"],
            meta_keywords_suggestions=self.settings["keywords-suggestions"],
            image_types=image_types,
            image_type=self.settings["image type"],
            ps_backends=ps_backends,
            jpeg_quality=self.settings["quality"],
            downsample_dpi=self.settings["downsample dpi"],
            downsample=self.settings["downsample"],
            pdf_compression=self.settings["pdf compression"],
            available_fonts=app._fonts,
            text_position=self.settings["text_position"],
            pdf_font=self.settings["pdf font"],
            can_encrypt_pdf="pdftk" in dependencies,
            tiff_compression=self.settings["tiff compression"],
        )

        # Frame for page range
        self._windowi.add_page_range()
        self._windowi.add_image_type()

        # Post-save hook
        pshbutton = Gtk.CheckButton(label=_("Post-save hook"))
        pshbutton.set_tooltip_text(
            _(
                "Run command on saved file. The available commands are those "
                "user-defined tools that do not specify %o"
            )
        )
        vbox = self._windowi.get_content_area()
        vbox.pack_start(pshbutton, False, True, 0)
        self.update_post_save_hooks()
        vbox.pack_start(self._windowi.comboboxpsh, False, True, 0)
        pshbutton.connect(
            "toggled",
            lambda _action: self._windowi.comboboxpsh.set_sensitive(
                pshbutton.get_active()
            ),
        )
        pshbutton.set_active(self.settings["post_save_hook"])
        self._windowi.comboboxpsh.set_sensitive(pshbutton.get_active())
        kbutton = Gtk.CheckButton(label=_("Close dialog on save"))
        kbutton.set_tooltip_text(_("Close dialog on save"))
        kbutton.set_active(self.settings["close_dialog_on_save"])
        vbox.pack_start(kbutton, False, True, 0)

        self._windowi.add_actions(
            [
                (
                    "gtk-save",
                    lambda: self.save_button_clicked_callback(kbutton, pshbutton),
                ),
                ("gtk-cancel", self._windowi.hide),
            ]
        )
        self._windowi.show_all()
        self._windowi.resize(1, 1)

    def save_button_clicked_callback(self, kbutton, pshbutton):
        "Save selected pages"

        # Compile list of pages
        self.settings["Page range"] = self._windowi.page_range
        uuids = list_of_page_uuids()

        # dig out the image type, compression and quality
        self.settings["image type"] = self._windowi.image_type
        self.settings["close_dialog_on_save"] = kbutton.get_active()
        self.settings["post_save_hook"] = pshbutton.get_active()
        if (
            self.settings["post_save_hook"]
            and self._windowi.comboboxpsh.get_active() > EMPTY_LIST
        ):
            self.settings["current_psh"] = self._windowi.comboboxpsh.get_active_text()

        if re.search(r"pdf", self.settings["image type"]):

            # dig out the compression
            self.settings["downsample"] = self._windowi.downsample
            self.settings["downsample dpi"] = self._windowi.downsample_dpi
            self.settings["pdf compression"] = self._windowi.pdf_compression
            self.settings["quality"] = self._windowi.jpeg_quality
            self.settings["text_position"] = self._windowi.text_position
            self.settings["pdf font"] = self._windowi.pdf_font

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])
            file_chooser = None
            if self.settings["image type"] == "pdf":
                self._windowi.update_config_dict(self.settings)

                # Set up file selector
                file_chooser = Gtk.FileChooserDialog(
                    title=_("PDF filename"),
                    parent=self._windowi,
                    action=Gtk.FileChooserAction.SAVE,
                )
                file_chooser.add_buttons(
                    Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK,
                    Gtk.ResponseType.OK,
                )

                filename = expand_metadata_pattern(
                    template=self.settings["default filename"],
                    convert_whitespace=self.settings[
                        "convert whitespace to underscores"
                    ],
                    author=self.settings["author"],
                    title=self.settings["title"],
                    docdate=self._windowi.meta_datetime,
                    today_and_now=datetime.datetime.now(),
                    extension="pdf",
                    subject=self.settings["subject"],
                    keywords=self.settings["keywords"],
                )
                file_chooser.set_current_name(filename)
                file_chooser.set_do_overwrite_confirmation(True)

            else:
                file_chooser = Gtk.FileChooserDialog(
                    title=_("PDF filename"),
                    parent=self._windowi,
                    action=Gtk.FileChooserAction.OPEN,
                )
                file_chooser.add_buttons(
                    Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OPEN,
                    Gtk.ResponseType.OK,
                )

            add_filter(file_chooser, _("PDF files"), ["pdf"])
            file_chooser.set_current_folder(self.settings["cwd"])
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.connect(
                "response",
                self.file_chooser_response_callback,
                [self.settings["image type"], uuids],
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "djvu":
            self._windowi.update_config_dict(self.settings)

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("DjVu filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            filename = expand_metadata_pattern(
                template=self.settings["default filename"],
                convert_whitespace=self.settings["convert whitespace to underscores"],
                author=self.settings["author"],
                title=self.settings["title"],
                docdate=self._windowi.meta_datetime,
                today_and_now=datetime.datetime.now(),
                extension="djvu",
                subject=self.settings["subject"],
                keywords=self.settings["keywords"],
            )
            file_chooser.set_current_name(filename)
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            add_filter(file_chooser, _("DjVu files"), ["djvu"])
            file_chooser.set_do_overwrite_confirmation(True)
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["djvu", uuids]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "tif":
            self.settings["tiff compression"] = self._windowi.tiff_compression
            self.settings["quality"] = self._windowi.jpeg_quality

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("TIFF filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            add_filter(file_chooser, _("Image files"), [self.settings["image type"]])
            file_chooser.set_do_overwrite_confirmation(True)
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["tif", uuids]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "txt":

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("Text filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            add_filter(file_chooser, _("Text files"), ["txt"])
            file_chooser.set_do_overwrite_confirmation(True)
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["txt", uuids]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "hocr":

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("hOCR filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            file_chooser.set_do_overwrite_confirmation(True)
            add_filter(file_chooser, _("hOCR files"), ["hocr"])
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["hocr", uuids]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "ps":
            self.settings["ps_backend"] = self._windowi.ps_backend
            logger.info("Selected '%s' as ps backend", self.settings["ps_backend"])

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("PS filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            add_filter(file_chooser, _("Postscript files"), ["ps"])
            file_chooser.set_do_overwrite_confirmation(True)
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["ps", uuids]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "session":

            # cd back to cwd to save
            os.chdir(self.settings["cwd"])

            # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                title=_("gscan2pdf session filename"),
                parent=self._windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
            file_chooser.add_buttons(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            )
            file_chooser.set_default_response(Gtk.ResponseType.OK)
            file_chooser.set_current_folder(self.settings["cwd"])
            add_filter(file_chooser, _("gscan2pdf session files"), ["gs2p"])
            file_chooser.set_do_overwrite_confirmation(True)
            file_chooser.connect(
                "response", self.file_chooser_response_callback, ["gs2p"]
            )
            file_chooser.show()

            # cd back to tempdir
            os.chdir(self.session.name)

        elif self.settings["image type"] == "jpg":
            self.settings["quality"] = self._windowi.jpeg_quality
            self.save_image(uuids)

        else:
            self.save_image(uuids)

    def file_chooser_response_callback(self, dialog, response, data):
        "Callback for file chooser dialog"
        filetype, uuids = data
        suffix = filetype
        if re.search(
            r"pdf", suffix, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
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
            self.settings["cwd"] = os.path.dirname(filename)
            if re.search(r"pdf", filetype):
                self.save_pdf(filename, filetype, uuids)

            elif filetype == "djvu":
                save_djvu(filename, uuids)

            elif filetype == "tif":
                save_tiff(filename, None, uuids)

            elif filetype == "txt":
                save_text(filename, uuids)

            elif filetype == "hocr":
                save_hocr(filename, uuids)

            elif filetype == "ps":
                if self.settings["ps_backend"] == "libtiff":
                    tif = tempfile.TemporaryFile(dir=self.session, suffix=".tif")
                    save_tiff(tif.filename(), filename, uuids)

                else:
                    self.save_pdf(filename, "ps", uuids)

            elif filetype == "gs2p":
                self.slist.save_session(filename, VERSION)

            if self._windowi is not None and self.settings["close_dialog_on_save"]:
                self._windowi.hide()

        dialog.destroy()

    def save_pdf(self, filename, option, list_of_page_uuids):
        "Save selected pages as PDF under given name."

        # Compile options
        options = {
            "compression": self.settings["pdf compression"],
            "downsample": self.settings["downsample"],
            "downsample dpi": self.settings["downsample dpi"],
            "quality": self.settings["quality"],
            "text_position": self.settings["text_position"],
            "font": self.settings["pdf font"],
            "user-password": self._windowi.pdf_user_password,
            "set_timestamp": self.settings["set_timestamp"],
            "convert whitespace to underscores": self.settings[
                "convert whitespace to underscores"
            ],
        }
        if option == "prependpdf":
            options["prepend"] = filename

        elif option == "appendpdf":
            options["append"] = filename

        elif option == "ps":
            options["ps"] = filename
            options["pstool"] = self.settings["ps_backend"]

        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        # Create the PDF
        logger.debug("Started saving %s", filename)

        def save_pdf_finished_callback(response):
            self.post_process_progress.finish(response)
            mark_pages(list_of_page_uuids)
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                if "ps" in options:
                    launch_default_for_file(options["ps"])
                else:
                    launch_default_for_file(filename)

            logger.debug("Finished saving %s", filename)

        self.slist.save_pdf(
            path=filename,
            list_of_pages=list_of_page_uuids,
            metadata=collate_metadata(self.settings, datetime.datetime.now()),
            options=options,
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_pdf_finished_callback,
            error_callback=error_callback,
        )

    def save_image(self, uuids):
        "Save selected pages as image under given name."

        # cd back to cwd to save
        os.chdir(self.settings["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("Image filename"),
            parent=self._windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(self.settings["cwd"])
        add_filter(
            file_chooser,
            _("Image files"),
            ["jpg", "png", "pnm", "gif", "tif", "tiff", "pdf", "djvu", "ps"],
        )
        file_chooser.set_do_overwrite_confirmation(True)
        if file_chooser.run() == Gtk.ResponseType.OK:
            filename = file_chooser.get_filename()

            # Update cwd
            self.settings["cwd"] = os.path.dirname(filename)

            # cd back to tempdir
            os.chdir(self.session.name)
            if len(uuids) > 1:
                w = len(uuids)
                for i in range(1, len(uuids) + 1):
                    current_filename = (
                        f"${filename}_%0${w}d.{self.settings['image type']}" % (i)
                    )
                    if os.path.isfile(current_filename):
                        text = _("This operation would overwrite %s") % (
                            current_filename
                        )
                        self.show_message_dialog(
                            parent=file_chooser,
                            message_type="error",
                            buttons=Gtk.ButtonsType.CLOSE,
                            text=text,
                        )
                        file_chooser.destroy()
                        return

                filename = f"${filename}_%0${w}d.{self.settings['image type']}"

            else:
                if not re.search(
                    rf"[.]{self.settings['image type']}$",
                    filename,
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    filename = f"{filename}.{self.settings['image type']}"
                    if file_exists(file_chooser, filename):
                        return

                if file_writable(file_chooser, filename):
                    return

            # Create the image
            logger.debug("Started saving %s", filename)

            def save_image_finished_callback(response):
                filename = response.request.args[0]["path"]
                uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
                self.post_process_progress.finish(response)

                mark_pages(uuids)
                if (
                    "view files toggle" in self.settings
                    and self.settings["view files toggle"]
                ):
                    w = len(uuids)
                    if w > 1:
                        for i in range(1, w + 1):
                            launch_default_for_file(filename % (i))
                    else:
                        launch_default_for_file(filename)

                logger.debug("Finished saving %s", filename)

            self.slist.save_image(
                path=filename,
                list_of_pages=uuids,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=save_image_finished_callback,
                error_callback=error_callback,
            )
            if self._windowi is not None:
                self._windowi.hide()

        file_chooser.destroy()

    def update_post_save_hooks(self):
        "Updates the post-save hooks"
        if self._windowi is not None:
            if hasattr(self._windowi, "comboboxpsh"):

                # empty combobox
                for _i in range(1, self._windowi.comboboxpsh.get_num_rows() + 1):
                    self._windowi.comboboxpsh.remove(0)

            else:
                # create it
                self._windowi.comboboxpsh = ComboBoxText()

            # fill it again
            for tool in self.settings["user_defined_tools"]:
                if not re.search(r"%o", tool, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    self._windowi.comboboxpsh.append_text(tool)

            self._windowi.comboboxpsh.set_active_by_text(self.settings["current_psh"])

    def email(self, _action, _param):
        "Display page selector and email."
        if self._windowe is not None:
            self._windowe.present()
            return

        self._windowe = SaveDialog(
            transient_for=self,
            title=_("Email as PDF"),
            hide_on_delete=True,
            page_range=self.settings["Page range"],
            include_time=self.settings["use_time"],
            meta_datetime=datetime.datetime.now() + self.settings["datetime offset"],
            select_datetime=bool(self.settings["datetime offset"]),
            meta_title=self.settings["title"],
            meta_title_suggestions=self.settings["title-suggestions"],
            meta_author=self.settings["author"],
            meta_author_suggestions=self.settings["author-suggestions"],
            meta_subject=self.settings["subject"],
            meta_subject_suggestions=self.settings["subject-suggestions"],
            meta_keywords=self.settings["keywords"],
            meta_keywords_suggestions=self.settings["keywords-suggestions"],
            jpeg_quality=self.settings["quality"],
            downsample_dpi=self.settings["downsample dpi"],
            downsample=self.settings["downsample"],
            pdf_compression=self.settings["pdf compression"],
            text_position=self.settings["text_position"],
            pdf_font=self.settings["pdf font"],
            can_encrypt_pdf="pdftk" in dependencies,
        )

        # Frame for page range
        self._windowe.add_page_range()

        # PDF options
        self._windowe.add_pdf_options()

        def email_callback():

            # Set options
            self._windowe.update_config_dict(self.settings)

            # Compile list of pages
            self.settings["Page range"] = self._windowe.page_range
            uuids = list_of_page_uuids()

            # dig out the compression
            self.settings["downsample"] = self._windowe.downsample
            self.settings["downsample dpi"] = self._windowe.downsample_dpi
            self.settings["pdf compression"] = self._windowe.pdf_compression
            self.settings["quality"] = self._windowe.jpeg_quality

            # Compile options
            options = {
                "compression": self.settings["pdf compression"],
                "downsample": self.settings["downsample"],
                "downsample dpi": self.settings["downsample dpi"],
                "quality": self.settings["quality"],
                "text_position": self.settings["text_position"],
                "font": self.settings["pdf font"],
                "user-password": self._windowe.pdf_user_password,
            }
            filename = expand_metadata_pattern(
                template=self.settings["default filename"],
                convert_whitespace=self.settings["convert whitespace to underscores"],
                author=self.settings["author"],
                title=self.settings["title"],
                docdate=self._windowe.meta_datetime,
                today_and_now=datetime.datetime.now(),
                extension="pdf",
                subject=self.settings["subject"],
                keywords=self.settings["keywords"],
            )
            if re.search(r"^\s+$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE):
                filename = "document"
            pdf = f"{self.session}/{filename}.pdf"

            # Create the PDF

            def email_finished_callback(response):
                self.post_process_progress.finish(response)
                mark_pages(uuids)
                if (
                    "view files toggle" in self.settings
                    and self.settings["view files toggle"]
                ):
                    launch_default_for_file(pdf)

                status = exec_command(["xdg-email", "--attach", pdf, "x@y"])
                if status:
                    self.show_message_dialog(
                        parent=self,
                        message_type="error",
                        buttons=Gtk.ButtonsType.CLOSE,
                        text=_("Error creating email"),
                    )

            self.slist.save_pdf(
                path=pdf,
                list_of_pages=uuids,
                metadata=collate_metadata(self.settings, datetime.datetime.now()),
                options=options,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=email_finished_callback,
                error_callback=error_callback,
            )
            self._windowe.hide()

        self._windowe.add_actions(
            [("gtk-ok", email_callback), ("gtk-cancel", self._windowe.hide)]
        )
        self._windowe.show_all()

    def preferences(self, _action, _param):
        "Preferences dialog"
        if self._windowr is not None:
            self._windowr.present()
            return

        self._windowr = Dialog(
            transient_for=self,
            title=_("Preferences"),
            hide_on_delete=True,
        )
        vbox = self._windowr.get_content_area()

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
        ) = _preferences_scan_options(self._windowr.get_border_width())
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
        ) = _preferences_general_options(self._windowr.get_border_width())
        notebook.append_page(vbox2, Gtk.Label(label=_("General options")))

        def preferences_apply_callback():
            self._windowr.hide()

            self.settings["auto-open-scan-dialog"] = cbo.get_active()
            try:
                text = blacklist.get_text()
                re.search(text, "dummy_device", re.MULTILINE | re.DOTALL | re.VERBOSE)
            except:
                msg = _("Invalid regex. Try without special characters such as '*'")
                logger.warning(msg)
                self.show_message_dialog(
                    parent=self._windowr,
                    message_type="error",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=msg,
                    store_response=True,
                )
                blacklist.set_text(self.settings["device blacklist"])

            self.settings["device blacklist"] = blacklist.get_text()
            self.settings["cycle sane handle"] = cbcsh.get_active()
            self.settings["allow-batch-flatbed"] = cb_batch_flatbed.get_active()
            self.settings["cancel-between-pages"] = cb_cancel_btw_pages.get_active()
            self.settings["adf-defaults-scan-all-pages"] = cb_adf_all_pages.get_active()
            self.settings["cache-device-list"] = cb_cache_device_list.get_active()
            self.settings["ignore-duplex-capabilities"] = cb_ignore_duplex.get_active()
            self.settings["default filename"] = fileentry.get_text()
            self.settings["restore window"] = cbw.get_active()
            self.settings["use_timezone"] = cbtz.get_active()
            self.settings["use_time"] = cbtm.get_active()
            self.settings["set_timestamp"] = cbts.get_active()
            self.settings["to_png"] = cbtp.get_active()
            self.settings["convert whitespace to underscores"] = cbb.get_active()
            if self._windows:
                self._windows.cycle_sane_handle = self.settings["cycle sane handle"]
                self._windows.cancel_between_pages = self.settings[
                    "cancel-between-pages"
                ]
                self._windows.allow_batch_flatbed = self.settings["allow-batch-flatbed"]
                self._windows.ignore_duplex_capabilities = self.settings[
                    "ignore-duplex-capabilities"
                ]

            if self._windowi is not None:
                self._windowi.include_time = self.settings["use_time"]

            self.settings["available-tmp-warning"] = spinbuttonw.get_value()
            self.settings["Blank threshold"] = spinbuttonb.get_value()
            self.settings["Dark threshold"] = spinbuttond.get_value()
            self.settings["OCR output"] = comboo.get_active_index()

            # Store viewer preferences
            self.settings["view files toggle"] = cbv.get_active()
            update_list_user_defined_tools(
                vboxt, [comboboxudt, self._windows.comboboxudt]
            )
            tmp = os.path.abspath(os.path.join(self.session.name, ".."))  # Up a level

            # Expand tildes in the filename
            newdir = get_tmp_dir(
                str(pathlib.Path(tmpentry.get_text()).expanduser()),
                r"gscan2pdf-\w\w\w\w",
            )
            if newdir != tmp:
                self.settings["TMPDIR"] = newdir
                response = ask_question(
                    parent=self,
                    type="question",
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=_("Changes will only take effect after restarting gscan2pdf.")
                    + SPACE
                    + _("Restart gscan2pdf now?"),
                )
                if response == Gtk.ResponseType.OK:
                    restart()

        self._windowr.add_actions(
            [("gtk-ok", preferences_apply_callback), ("gtk-cancel", self._windowr.hide)]
        )
        self._windowr.show_all()

    def can_quit(self):
        "Remove temporary files, note window state, save settings and quit."
        if not scans_saved(
            _("Some pages have not been saved.\nDo you really want to quit?")
        ):
            return False

        # Make sure that we are back in the start directory,
        # otherwise we can't delete the temp dir.
        os.chdir(self.settings["cwd"])

        # Remove temporary files
        for file in glob.glob(self.session.name + "/*"):
            os.remove(file)
        os.rmdir(self.session.name)
        # Write window state to settings
        self.settings["window_width"], self.settings["window_height"] = self.get_size()
        self.settings["window_x"], self.settings["window_y"] = self.get_position()
        self.settings["thumb panel"] = self._hpaned.get_position()
        if self._windows:
            (
                self.settings["scan_window_width"],
                self.settings["scan_window_height"],
            ) = self._windows.get_size()
            logger.info("Killing Sane thread(s)")
            self._windows.thread.quit()

        # Write config file
        config.write_config(self._configfile, self.settings)
        logger.info("Killing document thread(s)")
        self.slist.thread.quit()
        logger.debug("Quitting")

        # remove lock
        fcntl.lockf(self._lockfd, fcntl.LOCK_UN)

        # compress log file if we have xz
        if self._args.log and dependencies["xz"]:
            exec_command(["xz", "-f", self._args.log])

        return True


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
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(base_path, "app.ui"))
        self.builder.connect_signals(self)
        self.detail_popup = self.builder.get_object("detail_popup")
        self._fonts = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

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
        self.window.save_dialog(None, None)

    def on_email(self, _widget):
        "displays the email dialog."
        self.window.email(None, None)

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
        self.window.properties(None, None)

    def on_quit(self, _action, _param):
        "Handles the quit action."
        self.quit()

    def _init_icons(self, icons):
        "Initialise iconfactory"
        iconfactory = Gtk.IconFactory()
        for iconname, filename in icons:
            register_icon(iconfactory, iconname, self._iconpath + "/" + filename)
        iconfactory.add_default()


if __name__ == "__main__":
    global app
    app = Application()
    # app.run(sys.argv)
    app.run()

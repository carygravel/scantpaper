#!/usr/bin/python3

# TODO: use pathlib for all paths

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
#      * bionic (until 2023-04, dh11, no tests, no fonts-noto-extra, liblocale-codes-perl >= 3.55, also in Build-Depends-Indep)
#     debuild -S -sa
#     dput ftp-master .changes
#     dput gscan2pdf-ppa .changes
#    https://launchpad.net/~jeffreyratcliffe/+archive
# 8. gscan2pdf-announce@lists.sourceforge.net, gscan2pdf-help@lists.sourceforge.net, sane-devel@lists.alioth.debian.org
# 9. To interactively debug in the schroot:
#     duplicate the config file, typically in /etc/schroot/chroot.d/, changing the sbuild profile to desktop
#     schroot -c sid-amd64-desktop -u root
#     apt-get build-dep gscan2pdf
#     su - <user>
#     xvfb-run prove -lv <tests>

import os
import pathlib
import locale
import re
import subprocess
import glob
import logging
import gi
import argparse
import sys
import fcntl
import shutil
from types import SimpleNamespace
import tesserocr
from dialog import Dialog, MultipleMessage, filter_message, response_stored
from dialog.renumber import Renumber
from dialog.save import Save as SaveDialog
from dialog.scan import Scan
from dialog.sane import SaneScanDialog
from comboboxtext import ComboBoxText
from document import Document
from basedocument import slurp
from scanner.profile import Profile
from unpaper import Unpaper
from canvas import Canvas
from bboxtree import Bboxtree
import config
from i18n import _, d_sane
from helpers import get_tmp_dir, program_version, exec_command, parse_truetype_fonts, expand_metadata_pattern, collate_metadata
from tesseract import languages, _iso639_1to3, locale_installed, get_tesseract_codes
import sane             # To get SANE_* enums

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio # pylint: disable=wrong-import-position
from imageview import ImageView, Selector, Dragger, SelectorDragger
from simplelist import SimpleList

# the config file is saved with the numeric locale
import tempfile
import logging
import datetime   
import gettext

HALF                    = 0.5
UNIT_SLIDER_STEP        = 0.001
SIGMA_STEP              = 0.1
MAX_SIGMA               = 5
_90_DEGREES             = 90
_180_DEGREES            = 180
_270_DEGREES            = 270
DRAGGER_TOOL            = 10
SELECTOR_TOOL           = 20
SELECTORDRAGGER_TOOL    = 30
TABBED_VIEW             = 100
SPLIT_VIEW_H            = 101
SPLIT_VIEW_V            = 102
EDIT_TEXT               = 200
EDIT_ANNOTATION         = 201
EMPTY_LIST              = -1
_100_PERCENT            = 100
MAX_DPI                 = 2400
BITS_PER_BYTE           = 8
HELP_WINDOW_WIDTH       = 800
HELP_WINDOW_HEIGHT      = 600
HELP_WINDOW_DIVIDER_POS = 200
_1KB                    = 1024
_1MB                    = _1KB * _1KB
_100_000MB              = 100_000
ZOOM_CONTEXT_FACTOR     = 0.5

GLib.set_application_name('gscan2pdf')
GLib.set_prgname('net.sourceforge.gscan2pdf')
prog_name = GLib.get_application_name()
VERSION   = '3.0.0'

# Image border to ensure that a scaled to fit image gets no scrollbars
border = 1

debug    = False
EMPTY    = ""
SPACE    = " "
DOT      = "."
PERCENT  = "%"
ASTERISK = "*"
args,orig_args=None,None
logger = logging.getLogger(__name__)

# Define application-wide variables here so that they can be referenced
# in the menu callbacks
(
    slist,     windowi,     windowe, windows, windowo, windowrn, windowu,
    windowudt, save_button, window,  thbox,   tpbar,
    tcbutton,  spbar,       shbox,   scbutton, unpaper, hpaned,
    undo_buffer,
    redo_buffer,    undo_selection, redo_selection, dependencies,
    menubar,        toolbar,
    ocr_engine,     clipboard,
    windowr,        view,    windowp, message_dialog,
    print_settings, windowc, current_page,

    # Goo::Canvas for text layer
    canvas, vpaned, ocr_text_hbox, ocr_textbuffer, ocr_textview, ocr_bbox,

    # Goo::Canvas for annotation layer
    a_canvas, ann_hbox, ann_textbuffer, ann_textview, ann_bbox,

    # Notebook, split panes for detail view and OCR output
    vnotebook, hpanei, vpanei,

    # Spinbuttons for selector on crop dialog
    sb_selector_x, sb_selector_y, sb_selector_w, sb_selector_h,

    # dir below session dir
    tmpdir,

    # session dir
    session,

    # filehandle for session lockfile
    lockfh,

    # Temp::File object for PDF to be emailed
    # Define here to make sure that it doesn't get deleted until the next email
    # is created or we quit
    pdf,

    # hash of true type fonts available. Used by PDF OCR output
    fonts,

    # SimpleList in preferences dialog
    option_visibility_list,

    # Comboboxes for user-defined tools and rotate buttons
    comboboxudt, rotate_side_cmbx, rotate_side_cmbx2,

    # Declare the XML structure
    uimanager,
)=(None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,[],[],[],[],{},None,None,[],None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,)


def pack_viewer_tools() :
    "Pack widgets according to viewer_tools"
    global vnotebook
    global view
    global canvas
    global a_canvas
    global vpaned
    global hpanei
    if SETTING["viewer_tools"] == TABBED_VIEW :
        vnotebook.append_page( view, Gtk.Label( label=_('Image') ) )
        vnotebook.append_page( canvas,            Gtk.Label(label= _('Text layer') ) )
        vnotebook.append_page( a_canvas,            Gtk.Label( label=_('Annotations') ) )
        vpaned.pack1( vnotebook, True, True )
        vnotebook.show_all()
 
    elif SETTING["viewer_tools"] == SPLIT_VIEW_H :
        hpanei.pack1( view, True, True )
        hpanei.pack2( canvas, True, True )
        if a_canvas.get_parent() :
            vnotebook.remove(a_canvas)

        vpaned.pack1( hpanei, True, True )
 
    else :    # $SPLIT_VIEW_V
        vpanei.pack1( view, True, True )
        vpanei.pack2( canvas, True, True )
        if a_canvas.get_parent() :
            vnotebook.remove(a_canvas)

        vpaned.pack1( vpanei, True, True )


def parse_arguments() :
    parser = argparse.ArgumentParser(
                    prog=prog_name,
                    description='What the program does')
    parser.add_argument("--device", nargs="+")
    parser.add_argument("--import", nargs="+", dest="import_files")
    parser.add_argument("--import-all", nargs="+")
    parser.add_argument("--locale")
    parser.add_argument("--log", type=argparse.FileType('w'))
    parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    parser.add_argument("--debug", action='store_const', dest="log_level", const=logging.DEBUG, default=logging.WARNING)
    parser.add_argument("--info", action='store_const', dest="log_level", const=logging.INFO)
    parser.add_argument("--warn", action='store_const', dest="log_level", const=logging.WARNING)
    parser.add_argument("--error", action='store_const', dest="log_level", const=logging.ERROR)
    parser.add_argument("--fatal", action='store_const', dest="log_level", const=logging.CRITICAL)
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=log_level)
    else:
        logging.basicConfig(level=args.log_level)
#     log_conf = """ log4perl.appender.Screen        = Log::Log4perl::Appender::Screen
#  log4perl.appender.Screen.layout = Log::Log4perl::Layout::SimpleLayout
#  log4perl.appender.Screen.utf8   = 1
# """
#     if  (log is not None) :
#         log_conf += """ log4perl.appender.Logfile          = Log::Log4perl::Appender::File
#  log4perl.appender.Logfile.filename = $log
#  log4perl.appender.Logfile.mode     = write
#  log4perl.appender.Logfile.layout   = Log::Log4perl::Layout::SimpleLayout
#  log4perl.appender.Logfile.utf8     = 1
#  log4perl.category                  = $log_level, Logfile, Screen
# """
 
#     else :
#         log_conf += """ log4perl.category                  = $log_level, Screen
# """

    # if  (help is not None) :
    #     subprocess.run([f"perldoc {PROGRAM_NAME}"]) == 0           or raise _('Error displaying help'), "\n"

    logger.info(f"Starting {prog_name} {VERSION}")
    orig_args = [sys.executable]+ sys.argv
    logger.info( 'Called with ' + SPACE.join(orig_args)   )
    logger.info(f"Log level {args.log_level}")
    if  args.locale is None :
        gettext.bindtextdomain(f"{prog_name}")
    else :
        if   re.search(r"^\/",args.locale,re.MULTILINE|re.DOTALL|re.VERBOSE) :
            gettext.bindtextdomain(f"{prog_name}", locale)
        else :
            gettext.bindtextdomain(f"{prog_name}", getcwd + f"/{locale}" )
    gettext.textdomain(prog_name)

    logger.info( 'Using %s locale', locale.setlocale(locale.LC_CTYPE) )
    logger.info( 'Startup LC_NUMERIC %s', locale.setlocale(locale.LC_NUMERIC) )
    return args


def read_config() :

    # config files: XDG_CONFIG_HOME/gscan2pdfrc or HOME/.config/gscan2pdfrc
    rcdir      = os.environ['XDG_CONFIG_HOME'] if 'XDG_CONFIG_HOME' in os.environ else f"{os.environ['HOME']}/.config"
    rcf    = f"{rcdir}/{prog_name}rc"
    cfg = config.read_config(rcf)
    config.add_defaults( cfg )
    config.remove_invalid_paper( cfg["Paper"] )
    return rcf, cfg


def check_dependencies() :
    "Check for presence of various packages"

    dependencies["tesseract"] = tesserocr.tesseract_version()
    dependencies["tesserocr"] = tesserocr.__version__
    if dependencies["tesseract"] :
        logger.info(f"Found tesserocr {dependencies['tesserocr']}, {dependencies['tesseract']}")
    dependencies["unpaper"]   = Unpaper().program_version()
    if dependencies["unpaper"] :
        logger.info(f"Found unpaper {dependencies['unpaper']}")

    dependency_rules = [
        ['imagemagick', 'stdout',             r"Version:\sImageMagick\s([\d.-]+)",             ['convert', '--version' ]],
        ['graphicsmagick',                 'stdout',             r"GraphicsMagick\s([\d.-]+)", ['gm', '-version' ]        ],         
        [    'xdg',                      'stdout',             r"xdg-email\s([^\n]+)", [    'xdg-email', '--version' ]        ],         
        [    'djvu', 'stderr', r"DjVuLibre-([\d.]+)", [    'cjb2', '--version' ]        ],         
        [    'libtiff', 'both',    r"LIBTIFF,\sVersion\s([\d.]+)", [    'tiffcp', '-h' ]        ],          
        # pdftops and pdfunite are both in poppler-utils, and so the version is
        # the version is the same.
        # Both are needed, though to update %dependencies
        [    'pdftops',                         'stderr',             r"pdftops\sversion\s([\d.]+)", [    'pdftops', '-v' ]        ],         
        [    'pdfunite',                         'stderr',             r"pdfunite\sversion\s([\d.]+)", [    'pdfunite', '-v' ]        ],         
        [    'pdf2ps', 'stdout', r"([\d.]+)", [    'gs',    '--version' ] ],         
        [    'pdftk',  'stdout', r"([\d.]+)", [    'pdftk', '--version' ] ],         
        [    'xz',     'stdout', r"([\d.]+)", [    'xz',    '--version' ] ]
    ]
    
    for name, stream, regex, cmd in     dependency_rules :
        dependencies[name] =           program_version( stream, regex, cmd )
        if dependencies[name] and dependencies[name] == '-1' :
            del(dependencies[name]) 

        if not dependencies["imagemagick"] and dependencies["graphicsmagick"]         :
            msg = _(
'GraphicsMagick is being used in ImageMagick compatibility mode.'
              )               + SPACE               + _('Whilst this might work, it is not currently supported.')               + SPACE               + _('Please switch to ImageMagick in case of problems.')
            show_message_dialog(
                parent           = window,
                message_type             = 'warning',
                buttons          = Gtk.ButtonsType.OK,
                text             = msg,
                store_response = True
            )
            dependencies["imagemagick"] = dependencies["graphicsmagick"]

        if dependencies[name] :
            logger.info(f"Found {name} {dependencies[name]}")
            if name == 'pdftk' :

                # Don't create PDF  directly with imagemagick, as
                # some distros configure imagemagick not to write PDFs
                tempimg =                   tempfile.NamedTemporaryFile( dir = session.name, suffix = '.jpg' )
                exec_command(                [                'convert', 'rose:', tempimg.name ] )
                temppdf =                   tempfile.NamedTemporaryFile( dir = session.name, suffix = '.pdf' )
                # pdfobj = PDF.Builder( -file = temppdf )
                # page   = pdfobj.page()
                # size   = Gscan2pdf.Document.POINTS_PER_INCH
                # page.mediabox( size, size )
                # gfx    = page.gfx()
                # imgobj = pdfobj.image_jpeg(tempimg)
                # gfx.image( imgobj, 0, 0, size, size )
                # pdfobj.save()
                # pdfobj.end()
                proc = exec_command(                [                name, temppdf.name, 'dump_data' ] )
                msg=None
                if                      re.search(r"Error:[ ]could[ ]not[ ]load[ ]a[ ]required[ ]library",proc.stdout,re.MULTILINE|re.DOTALL|re.VERBOSE)                 :
                    msg = _(
"pdftk is installed, but seems to be missing required dependencies:\n%s"
                    ) % (proc.stdout)  
 
#                 elif   not re.search(r"NumberOfPages",proc.stdout,re.MULTILINE|re.DOTALL|re.VERBOSE) :
#                     logger.debug(f"before msg {_}")
#                     msg = _(
# 'pdftk is installed, but cannot access the directory used for temporary files.'
#                       )                       + _(
# 'One reason for this might be that pdftk was installed via snap.'
#                       )                       + _(
# 'In this case, removing pdftk, and reinstalling without using snap would allow gscan2pdf to use pdftk.'
#                       )                       + _(
# 'Another workaround would be to select a temporary directory under your home directory in Edit/Preferences.'
#                       )

                if msg :
                    del(dependencies[name]) 
                    show_message_dialog(
                        parent           = window,
                        message_type             = 'warning',
                        buttons          = Gtk.ButtonsType.OK,
                        text             = msg,
                        store_response = True
                    )
                    
    # OCR engine options
    if dependencies["tesseract"] :
        ocr_engine.append([
        'tesseract', _('Tesseract'), _('Process image with Tesseract.') ])            

    # Build a look-up table of all true-type fonts installed
    proc  =       exec_command(    [    'fc-list', ":", "family", "style", 'file'] )
    fonts = parse_truetype_fonts(proc.stdout)


def update_uimanager() :
    "ghost or unghost as necessary as # pages > 0 or not"
    widgets = [
        '/MenuBar/View/DraggerTool',
        '/MenuBar/View/SelectorTool',
        '/MenuBar/View/SelectorDraggerTool',
        '/MenuBar/View/Tabbed',
        '/MenuBar/View/SplitH',
        '/MenuBar/View/SplitV',
        '/MenuBar/View/Zoom 100',
        '/MenuBar/View/Zoom to fit',
        '/MenuBar/View/Zoom in',
        '/MenuBar/View/Zoom out',
        '/MenuBar/View/Rotate 90',
        '/MenuBar/View/Rotate 180',
        '/MenuBar/View/Rotate 270',
        '/MenuBar/View/Edit text layer',
        '/MenuBar/View/Edit annotations',
        '/MenuBar/Tools/Threshold',
        '/MenuBar/Tools/BrightnessContrast',
        '/MenuBar/Tools/Negate',
        '/MenuBar/Tools/Unsharp',
        '/MenuBar/Tools/CropDialog',
        '/MenuBar/Tools/unpaper',
        '/MenuBar/Tools/split',
        '/MenuBar/Tools/OCR',
        '/MenuBar/Tools/User-defined',

        '/ToolBar/DraggerTool',
        '/ToolBar/SelectorTool',
        '/ToolBar/SelectorDraggerTool',
        '/ToolBar/Zoom 100',
        '/ToolBar/Zoom to fit',
        '/ToolBar/Zoom in',
        '/ToolBar/Zoom out',
        '/ToolBar/Rotate 90',
        '/ToolBar/Rotate 180',
        '/ToolBar/Rotate 270',
        '/ToolBar/Edit text layer',
        '/ToolBar/Edit annotations',
        '/ToolBar/CropSelection',

        '/Detail_Popup/DraggerTool',
        '/Detail_Popup/SelectorTool',
        '/Detail_Popup/SelectorDraggerTool',
        '/Detail_Popup/Zoom 100',
        '/Detail_Popup/Zoom to fit',
        '/Detail_Popup/Zoom in',
        '/Detail_Popup/Zoom out',
        '/Detail_Popup/Rotate 90',
        '/Detail_Popup/Rotate 180',
        '/Detail_Popup/Rotate 270',
        '/Detail_Popup/Edit text layer',
        '/Detail_Popup/Edit annotations',
        '/Detail_Popup/CropSelection',

        '/Thumb_Popup/Rotate 90',
        '/Thumb_Popup/Rotate 180',
        '/Thumb_Popup/Rotate 270',
        '/Thumb_Popup/CropSelection',
    ]
    global uimanager
    if slist.get_selected_indices() :
        for widget in         widgets :
            uimanager.get_widget(widget).set_sensitive(True)
    else :
        for widget in         widgets :
            uimanager.get_widget(widget).set_sensitive(False)

    # Ghost unpaper item if unpaper not available
    if not dependencies["unpaper"] :
        uimanager.get_widget('/MenuBar/Tools/unpaper').set_sensitive(False)

    # Ghost ocr item if ocr  not available
    if not dependencies["ocr"] :
        uimanager.get_widget('/MenuBar/Tools/OCR').set_sensitive(False)

    if len( slist.data ) :
        if dependencies["xdg"] :
            uimanager.get_widget('/MenuBar/File/Email as PDF')               .set_sensitive(True)
            uimanager.get_widget('/ToolBar/Email as PDF')               .set_sensitive(True)
            uimanager.get_widget('/Thumb_Popup/Email as PDF')               .set_sensitive(True)

        if dependencies["imagemagick"] and dependencies["libtiff"] :
            uimanager.get_widget('/MenuBar/File/Save').set_sensitive(True)
            uimanager.get_widget('/ToolBar/Save').set_sensitive(True)
            uimanager.get_widget('/Thumb_Popup/Save').set_sensitive(True)

        uimanager.get_widget('/MenuBar/File/Print').set_sensitive(True)
        uimanager.get_widget('/ToolBar/Print').set_sensitive(True)
        uimanager.get_widget('/Thumb_Popup/Print').set_sensitive(True)
        if  (save_button is not None) :
            save_button.set_sensitive(True)
 
    else :
        if dependencies["xdg"] :
            uimanager.get_widget('/MenuBar/File/Email as PDF')               .set_sensitive(False)
            uimanager.get_widget('/ToolBar/Email as PDF')               .set_sensitive(False)
            uimanager.get_widget('/Thumb_Popup/Email as PDF')               .set_sensitive(False)
            if  (windowe is not None) :
                windowe.hide()

        if dependencies["imagemagick"] and dependencies["libtiff"] :
            uimanager.get_widget('/MenuBar/File/Save').set_sensitive(False)
            uimanager.get_widget('/ToolBar/Save').set_sensitive(False)
            uimanager.get_widget('/Thumb_Popup/Save').set_sensitive(False)

        uimanager.get_widget('/MenuBar/File/Print').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Print').set_sensitive(False)
        uimanager.get_widget('/Thumb_Popup/Print').set_sensitive(False)
        if  (save_button is not None) :
            save_button.set_sensitive(False)


   # If the scan dialog has already been drawn, update the start page spinbutton
    global windows
    if windows :
        windows._update_start_page()


def selection_changed_callback(_selection):
    global view
    global canvas
    global a_canvas
    global current_page
    selection = slist.get_selected_indices()

    # Display the new image
    # When editing the page number, there is a race condition where the page
    # can be undefined
    if selection:
        i = selection.pop(0)
        path = Gtk.TreePath.new_from_indices([i])
        slist.scroll_to_cell( path, slist.get_column(0), True, HALF, HALF )
        sel = view.get_selection()
        display_image( slist.data[i][2] )
        if sel is not None:
            view.set_selection(sel)
    else :
        view.set_pixbuf(None)
        canvas.clear_text()
        a_canvas.clear_text()
        current_page=None

    update_uimanager()


def drag_motion_callback( tree, context, x, y, t ) :
    
    try:
        path, how  = tree.get_dest_row_at_pos( x, y )     
    except:
        return
    scroll = tree.get_parent()

    # Add the marker showing the drop in the tree
    tree.set_drag_dest_row( path, how )

    # Make move the default
    action=Gdk.DragAction.MOVE
    if context.get_actions() == Gdk.DragAction.COPY:
        action = Gdk.DragAction.COPY

    Gdk.drag_status( context, action, t )
    adj = scroll.get_vadjustment()
    value, step = adj.get_value(), adj.get_step_increment()
    if y > adj.get_page_size() -step/2    :
        v = value + step
        m = adj.get_upper(-adj.get_page_size())  
        adj.set_value(    m if v>m  else v )
    elif y < step / 2 :
        v = value - step
        m = adj.get_lower()
        adj.set_value(    m if v<m  else v )

    return False


def create_temp_directory() :
    global session
    global tmpdir
    global slist
    tmpdir = get_tmp_dir( SETTING["TMPDIR"],r'gscan2pdf-\w\w\w\w' )
    find_crashed_sessions(tmpdir)

    # Create temporary directory if necessary
    if   session is None :
        if  tmpdir is not None and tmpdir != EMPTY :
            if not os.path.isdir( tmpdir) :
                os.mkdir( tmpdir)
            try :
                session =                   tempfile.TemporaryDirectory( prefix='gscan2pdf-', dir = tmpdir )
            except :
                session = tempfile.TemporaryDirectory( prefix='gscan2pdf-')
        else :
            session = tempfile.TemporaryDirectory( prefix='gscan2pdf-')

        slist.set_dir(session.name)
        try:
            lockfh=open(os.path.join( session.name, 'lockfile' ), 'w', encoding="utf-8")
        except:
            raise "Cannot open lockfile\n"
        fcntl.lockf( lockfh, fcntl.LOCK_EX) #raise "Cannot lock file\n"
        slist.save_session()
        logger.info(f"Using {session.name} for temporary files")
        tmpdir = os.path.dirname(session.name)
        if  "TMPDIR"  in SETTING and SETTING["TMPDIR"] != tmpdir :
            logger.warning(
                _(
'Warning: unable to use %s for temporary storage. Defaulting to %s instead.'
                ) % (SETTING["TMPDIR"],tmpdir)                 
            )
            SETTING["TMPDIR"] = tmpdir


def find_crashed_sessions(tmpdir) :
    "Look for crashed sessions"
    if   tmpdir is None or tmpdir == EMPTY :
        tmpdir =  tempfile.gettempdir()

    logger.info(f"Checking {tmpdir} for crashed sessions")
    sessions  =       glob.glob(os.path.join( tmpdir, 'gscan2pdf-????' )) 
    crashed, selected=[],[]

    # Forget those used by running sessions
    for session in     sessions :
        try:
            lockfh=open('>',os.path.join( session, 'lockfile' ))
            fcntl.lockf( lockfh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            crashed.append(_)  
        except:
            pass

        fcntl.lockf( lockfh, fcntl.LOCK_UN) #raise f"Unlocking error on {lockfh} ({ERRNO})\n"
        try:
            lockfh.close()  
        
        except:
            logger.warning( f"Error closing {lockfh} ({ERRNO})")

    # Flag those with no session file
    missing=[]
    for i in      range(len(crashed))    :
        if not os.access(os.path.join( crashed[i], 'session' ),os.R_OK)  :
            missing.append(crashed[i])  
            del(crashed[i])   


    if missing :
        logger.info( 'Unrestorable sessions: ' + SPACE.join(missing)   )
        dialog = Gtk.Dialog(
            title=_('Crashed sessions'),
            transient_for=window, modal=True,
        )
        dialog.add_buttons(
            Gtk.STOCK_DELETE, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
        )
        text = Gtk.TextView()
        text.set_wrap_mode('word')
        text.get_buffer().set_text(
                _('The following list of sessions cannot be restored.')
              + SPACE
              + _('Please retrieve any images you require from them.')
              + SPACE
              + _('Selected sessions will be deleted.') )
        dialog.get_content_area().add(text)
        columns = {_('Session'): 'text'}
        sessionlist = SimpleList(**columns)
        sessionlist.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        sessionlist.data.append(missing)  
        dialog.get_content_area().add(sessionlist)
        (button) = dialog.get_action_area().get_children()

        def anonymous_44():
            button.set_sensitive(
                    len(sessionlist.get_selected_indices())  > 0 )

        sessionlist.get_selection().connect(            'changed' , anonymous_44         )
        sessionlist.get_selection().select_all()
        dialog.show_all()
        if dialog.run() =='ok'  :
            selected = sessionlist.get_selected_indices()
            for i, v in             enumerate(selected) :
                selected[i] = missing[i]
            logger.info( 'Selected for deletion: ' + SPACE.join(selected)   )
            if selected :
                remove_tree(selected)
 
        else :
            logger.info('None selected')

        dialog.destroy()


    # Allow user to pick a crashed session to restore
    if crashed :
        dialog = Gtk.Dialog(
            title=_('Pick crashed session to restore'),
            transient_for=window, modal=True,
        )
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        label = Gtk.Label(label= _('Pick crashed session to restore') )
        box   = dialog.get_content_area()
        box.add(label)
        columns = {_('Session'): 'text'}
        sessionlist = SimpleList(**columns)
        sessionlist.data.append(crashed)  
        box.add(sessionlist)
        dialog.show_all()
        if dialog.run() =='ok'  :
            (selected) = sessionlist.get_selected_indices()

        dialog.destroy()
        if  selected is not None :
            session = crashed[selected]
            lockfh=open('>',os.path.join( session, 'lockfile' ))      #raise "Cannot open lockfile\n"
            fcntl.lockf( lockfh, fcntl.LOCK_EX )# raise "Cannot lock file\n"
            slist.set_dir(session)
            open_session(session)


def display_callback(response) :
    "Find the page from the input uuid and display it"
    uuid = response.request.args[0]["page"].uuid
    i = slist.find_page_by_uuid(uuid)
    if i is None:
        logger.error("Can't display page with uuid %s: page not found", uuid)
    else:
        display_image(slist.data[i][2])


def display_image(page) :
    "Display the image in the view"
    current_page = page
    global view
    global canvas
    view.set_pixbuf( current_page.get_pixbuf(), True )
    xresolution, yresolution, units = current_page.resolution
    view.set_resolution_ratio(xresolution / yresolution )

    # Get image dimensions to constrain selector spinbuttons on crop dialog
    width, height  = current_page.get_size()

    # Update the ranges on the crop dialog
    if  (sb_selector_w is not None) and  (current_page is not None) :
        sb_selector_w.set_range( 0, width - sb_selector_x.get_value() )
        sb_selector_h.set_range( 0, height - sb_selector_y.get_value() )
        sb_selector_x.set_range( 0, width - sb_selector_w.get_value() )
        sb_selector_y.set_range( 0, height - sb_selector_h.get_value() )
        SETTING["selection"]["x"]      = sb_selector_x.get_value()
        SETTING["selection"]["y"]      = sb_selector_y.get_value()
        SETTING["selection"]["width"]  = sb_selector_w.get_value()
        SETTING["selection"]["height"] = sb_selector_h.get_value()
        view.set_selection( SETTING["selection"] )

    # Delete OCR output if it has become corrupted
    if current_page.text_layer is not None:
        bbox = Bboxtree(current_page.text_layer)
        if not bbox.valid():
            logger.error(f"deleting corrupt text layer: {current_page.text_layer}")
            current_page.text_layer = None

    if current_page.text_layer:
        create_txt_canvas(current_page)
    else:
        canvas.clear_text()

    if current_page.annotations:
        create_ann_canvas(current_page)
    else:
        a_canvas.clear_text()


def create_txt_canvas( page, finished_callback=None ) :
    
    global view
    global canvas
    offset = view.get_offset()
    canvas.set_text( page=page, layer='text_layer', edit_callback=edit_ocr_text, idle=True,
        finished_callback=finished_callback )
    canvas.set_scale( view.get_zoom() )
    canvas.set_offset( offset.x, offset.y )
    canvas.show()


def create_ann_canvas( page, finished_callback ) :
    
    global view
    global canvas
    global a_canvas
    offset = view.get_offset()
    a_canvas.set_text( page, 'annotations', edit_annotation, True,
        finished_callback )
    a_canvas.set_scale( view.get_zoom() )
    a_canvas.set_offset( offset["x"], offset["y"] )
    a_canvas.show()


def edit_tools_callback( action, current ) :
    
    logger.debug( f"in edit_tools_callback with {action}, {current} "
          + current.get_current_value() )
    if current.get_current_value() == EDIT_TEXT :
        ocr_text_hbox.show()
        ann_hbox.hide()
        return

    ocr_text_hbox.hide()
    ann_hbox.show()
    return


def edit_ocr_text( widget, target, ev, bbox ) :
    
    global view
    global canvas
    if not ev :
        bbox = widget

    if   (bbox is None) :
        return
    ocr_bbox = bbox
    ocr_textbuffer.text=bbox.text
    ocr_text_hbox.show_all()
    view.set_selection( bbox.bbox )
    view.set_zoom_to_fit(False)
    view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
    if ev :
        canvas.pointer_ungrab( widget, ev.time() )

    if bbox :
        canvas.set_index_by_bbox(bbox)

    return True


def edit_annotation( widget, target, ev, bbox ) :
    
    global view
    global a_canvas
    if not ev :
        bbox = widget

    ann_bbox = bbox
    ann_textbuffer.text=bbox.text
    ann_hbox.show_all()
    view.set_selection( bbox.bbox )
    view.set_zoom_to_fit(False)
    view.zoom_to_selection(ZOOM_CONTEXT_FACTOR)
    if ev :
        a_canvas.pointer_ungrab( widget, ev.time() )

    if bbox :
        a_canvas.set_index_by_bbox(bbox)

    return True



def scans_saved(message) :
    "Check that all pages have been saved"    
    if not slist.scans_saved() :
        response = ask_question(
            parent             = window,
            type               = 'question',
            buttons            = Gtk.ButtonsType.OK_CANCEL,
            text               = message,
            store_response   = True,
            stored_responses = [Gtk.ResponseType.OK]
        )
        if response != Gtk.ResponseType.OK :
            return False

    return True



def new() :
    "Deletes all scans after warning"
    if not scans_saved(
            _(
"Some pages have not been saved.\nDo you really want to clear all pages?"
            )
        )     :
        return

    # Update undo/redo buffers
    take_snapshot()

    # in certain circumstances, before v2.5.5, having deleted one of several
    # pages, pressing the new button would cause some sort of race condition
    # between the tied array of the slist and the callbacks displaying the
    # thumbnails, so block this whilst clearing the array.
    slist.get_model().handler_block( slist.row_changed_signal )
    slist.get_selection().handler_block(slist.selection_changed_signal )

    # Depopulate the thumbnail list
    slist.data = []

    # Unblock slist signals now finished
    slist.get_selection().handler_unblock(slist.selection_changed_signal )
    slist.get_model().handler_unblock( slist.row_changed_signal )

    # Now we have to clear everything manually
    slist.get_selection().unselect_all()
    global view
    view.set_pixbuf(None)
    global canvas
    canvas.clear_text()
    global a_canvas
    a_canvas.clear_text()
    current_page=None

    # Reset start page in scan dialog
    global windows
    windows.reset_start_page()


def add_filter( file_chooser, name, file_extensions ) :
    "Create a file filter to show only supported file types in FileChooser dialog"    
    filter = Gtk.FileFilter()
    for  extension in     file_extensions :
        pattern=[]

        # Create case insensitive pattern
        for  char in          extension    :
            pattern.append('['+char.upper()+char.lower()+']')        

        filter.add_pattern( "*." + EMPTY.join(pattern)  )

    types=None
    for ext in     file_extensions :
        if  types is not None :
            types += f", *.{ext}"
 
        else :
            types = f"*.{ext}"

    filter.set_name(f"{name} ({types})")
    file_chooser.add_filter(filter)
    filter = Gtk.FileFilter()
    filter.add_pattern("*")
    filter.set_name('All files')
    file_chooser.add_filter(filter)


def error_callback( response ) :
    args = response.request.args
    process = response.request.process
    stage = response.type.name.lower()
    message = response.status
    page = None
    if "page" in args[0]:
        page = args[0]["page"]

    options = {
        "parent"           : window,
        "message_type"     : 'error',
        "buttons"          : Gtk.ButtonsType.CLOSE,
        "process"          : process,
        "text"             : message,
        'store-response' : True,
        "page"           : page,
    }

    logger.error( f"Error running '{stage}' callback for '{process}' process: {message}")

    def show_message_dialog_wrapper():
        """ Wrap show_message_dialog() in GLib.idle_add() to allow the thread to
        return immediately in order to allow it to work on subsequent pages
        despite errors on previous ones"""
        show_message_dialog(**options)

    GLib.idle_add(show_message_dialog_wrapper)
    global thbox
    thbox.hide()


def open_session_file(filename) :
    
    logger.info(f"Restoring session in {session}")
    slist.open_session_file(
        info           = filename,
        error_callback = error_callback
    )


def open_session_action(action) :
    
    file_chooser = Gtk.FileChooserDialog(
        title=_('Open crashed session'),
        parent=window, action=Gtk.FileChooserAction.SELECT_FOLDER,
    )
    file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK)
    file_chooser.set_default_response('ok')
    file_chooser.set_current_folder( SETTING["cwd"] )
    if file_chooser.run() == Gtk.ResponseType.OK:

        # Update undo/redo buffers
        take_snapshot()
        filename = file_chooser.get_filenames()
        open_session( filename[0] )

    file_chooser.destroy()
    return


def open_session(sesdir) :
    
    logger.info(f"Restoring session in {session}")
    slist.open_session(
        dir            = sesdir,
        delete         = False,
        error_callback = error_callback
    )


def setup_tpbar( process, completed, total, pid ) :
    "Helper function to set up thread progress bar"    
    if total and  (process is not None) :
        tpbar.set_text(
            _('Process %i of %i (%s)') % (completed+1,total,process) 
        )
        tpbar.set_fraction( ( completed + HALF ) / total )
        thbox.show_all()
    
        def anonymous_46():
            """ Pass the signal back to:
            1. be able to cancel it when the process has finished
            2. flag that the progress bar has been set up
               and avoid the race condition where the callback is
               entered before the $completed and $total variables have caught up"""
            slist.cancel( [ pid ] )
            thbox.hide()

        return tcbutton.connect( 'clicked' , anonymous_46  )


def update_tpbar(response) :
    "Helper function to update thread progress bar"
    if response is None or response.info is None:
        return    
    options = response.info
    if options["jobs_total"] :
        if  "process"  in options :
            if  "message"  in options :
                options["process"] += f" - {options['message']}"
            tpbar.set_text(
                _('Process %i of %i (%s)') % (options["jobs_completed"]+1,options["jobs_total"],options["process"])                  
            )
 
        else :
            tpbar.set_text(
                _('Process %i of %i') % (options["jobs_completed"]+1,options["jobs_total"]) 
            )

        if  "progress"  in options :
            tpbar.set_fraction(
            ( options["jobs_completed"] + options["progress"] ) /                   options["jobs_total"] )
 
        else :
            tpbar.set_fraction(
            ( options["jobs_completed"] + HALF ) / options["jobs_total"] )

        thbox.show_all()
        return True


def open_dialog(_action) :
    "Throw up file selector and open selected file"
    # cd back to cwd to get filename
    os.chdir( SETTING["cwd"])
    file_chooser = Gtk.FileChooserDialog(
        title=_('Open image'),
        parent=window, action=Gtk.FileChooserAction.OPEN,
    )
    file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    file_chooser.set_select_multiple(True)
    file_chooser.set_default_response(Gtk.ResponseType.OK)
    file_chooser.set_current_folder( SETTING["cwd"] )
    add_filter( file_chooser, _('Image files'),
        ['jpg', 'png', 'pnm', 'ppm', 'pbm', 'gif', 'tif', 'tiff', 'pdf', 'djvu',
        'ps',  'gs2p'] )
    if  file_chooser.run() == Gtk.ResponseType.OK:

        # cd back to tempdir to import
        os.chdir( session.name)

        # Update undo/redo buffers
        take_snapshot()
        filenames = file_chooser.get_filenames()
        file_chooser.destroy()

        # Update cwd
        SETTING["cwd"] = os.path.dirname( filenames[0] )
        import_files(filenames)
    else :
        file_chooser.destroy()

    # cd back to tempdir
    os.chdir( session.name)


def import_files_password_callback(filename):
            
    text = _('Enter user password for PDF %s') % (filename)  
    dialog =               Gtk.MessageDialog( window,
                [
    'destroy-with-parent', 'modal' ],
                'question', Gtk.ResponseType.OK_CANCEL, text )
    dialog.set_title(text)
    vbox  = dialog.get_content_area()
    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char(ASTERISK)
    vbox.pack_end( entry, False, False, 0 )
    dialog.show_all()
    response = dialog.run()
    text = entry.get_text()
    dialog.destroy()
    if response == Gtk.ResponseType.OK and text != EMPTY :
        return text
    return None


def import_files_queued_callback(response):
    #*argv
    #filenames
    logger.debug(f"queued import_files({response})")
#    return update_tpbar(*argv)


def import_files_started_callback( response ):
    #thread, process, completed, total
    #filenames
            
    logger.debug(f"started import_files({response})")
    # signal =    setup_tpbar( process, completed, total, pid )
    # if signal is not None:
    #     return True  


def import_files_running_callback(response):
    #*argv
    pass
    #return update_tpbar(*argv)


def import_files_finished_callback(response):
    #pending, filenames
    logger.debug(f"finished import_files({response})")
    # if not pending :
    #     thbox.hide()
    # if signal is not None :
    #     tcbutton.disconnect(signal)

    # slist.save_session()


def import_files_metadata_callback(metadata):
    logger.debug(f"import_files_metadata_callback({metadata})")
    global SETTING
    for  dialog in          ( windowi, windowe ) :
        if  dialog is not None :
            dialog.update_from_import_metadata(metadata)
    config.update_config_from_imported_metadata(SETTING, metadata)


def import_files( filenames, all_pages=False ) :
    
    # FIXME: import_files() now returns an array of pids.
    ( signal, pid )=(None,None)
    options = {
        "paths"             : filenames,
        "password_callback" : import_files_password_callback ,
        "queued_callback" : import_files_queued_callback ,
        "started_callback" : import_files_started_callback ,
        "running_callback" : import_files_running_callback ,
        "finished_callback" : import_files_finished_callback ,
        "metadata_callback" : import_files_metadata_callback ,
        "error_callback" : error_callback,
    }
    if all_pages :
        def all_pages_callback(info):
            
            return 1, info["pages"]


        options["pagerange_callback"] = all_pages_callback 
 
    else :
        def select_pagerange_callback(info):
            
            dialog = Gtk.Dialog(
                title=_('Pages to extract'),
                transient_for=window,
                modal=True,destroy_with_parent=True,
            )
            dialog.add_buttons(
                Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
            )
            vbox = dialog.get_content_area()
            hbox = Gtk.HBox()
            vbox.pack_start( hbox, True, True, 0 )
            label = Gtk.Label(label= _('First page to extract') )
            hbox.pack_start( label, False, False, 0 )
            spinbuttonf =               Gtk.SpinButton.new_with_range( 1, info["pages"], 1 )
            hbox.pack_end( spinbuttonf, False, False, 0 )
            hbox = Gtk.HBox()
            vbox.pack_start( hbox, True, True, 0 )
            label = Gtk.Label( label=_('Last page to extract') )
            hbox.pack_start( label, False, False, 0 )
            spinbuttonl =               Gtk.SpinButton.new_with_range( 1, info["pages"], 1 )
            spinbuttonl.set_value( info["pages"] )
            hbox.pack_end( spinbuttonl, False, False, 0 )
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.OK :
                return int(spinbuttonf.get_value()), int(spinbuttonl.get_value())
            return None, None


        options["pagerange_callback"] = select_pagerange_callback 

    pid = slist.import_files(**options)


def save_pdf( filename, option, list_of_page_uuids ) :
    "Save selected pages as PDF under given name."    

    # Compile options
    options = {
        "compression"      : SETTING['pdf compression'],
        "downsample"       : SETTING["downsample"],
        'downsample dpi' : SETTING['downsample dpi'],
        "quality"          : SETTING["quality"],
        "text_position"    : SETTING["text_position"],
        "font"             : SETTING['pdf font'],
        'user-password'  : windowi.pdf_user_password,
        "set_timestamp"    : SETTING["set_timestamp"],
        'convert whitespace to underscores' :
          SETTING['convert whitespace to underscores'],
    }
    if option == 'prependpdf' :
        options["prepend"] = filename
 
    elif option == 'appendpdf' :
        options["append"] = filename
 
    elif option == 'ps' :
        options["ps"]     = filename
        options["pstool"] = SETTING["ps_backend"]

    if SETTING["post_save_hook"] :
        options["post_save_hook"] = SETTING["current_psh"]

    # Create the PDF
    logger.debug(f"Started saving {filename}")
    signal, pid =(None,None)

    def save_pdf_started_callback( response ):
        if response.info is not None:
            process, completed, total = response.info            
            signal = setup_tpbar( process, completed, total, pid )
            if signal is not None:
                return True  
        return False


    def save_pdf_finished_callback( response ):
        #new_page, pending
            
        # if not pending :
        #     thbox.hide()
        if  signal is not None :
            tcbutton.disconnect(signal)

        mark_pages(list_of_page_uuids)
        if  'view files toggle'  in SETTING                and SETTING['view files toggle']             :
            if  "ps"  in options :
                launch_default_for_file( options["ps"] )
            else :
                launch_default_for_file(filename)

        logger.debug(f"Finished saving {filename}")

    pid = slist.save_pdf(
        path          = filename,
        list_of_pages = list_of_page_uuids,
        metadata      = collate_metadata( SETTING,            datetime.datetime.now()  ),
        options         = options,
        queued_callback = update_tpbar ,
        started_callback = save_pdf_started_callback ,
        running_callback = update_tpbar ,
        finished_callback = save_pdf_finished_callback ,
        error_callback = error_callback
    )


def launch_default_for_file(filename) :
    
    uri = GLib.filename_to_uri( os.path.abspath(filename), None )
    logger.info(f"Opening {uri} via default launcher")
    context = Gio.AppLaunchContext()
    try :
        Gio.AppInfo.launch_default_for_uri( uri, context ) 
    except Exception as e:
        logger.error(f"Unable to launch viewer: {e}")
    return



def save_dialog(_action) :
    "Display page selector and on save a fileselector."
    global windowi
    if  windowi is not None :
        windowi.present()
        return

    image_types = ["pdf","gif","jpg","png","pnm","ps","tif","txt","hocr","session"]
    if dependencies["pdfunite"] :
        image_types.extend(['prependpdf','appendpdf'])   

    if dependencies["djvu"] :
        image_types.append('djvu')  
    ps_backends=[]
    for  backend in     ["libtiff","pdf2ps","pdftops"] :
        if dependencies[backend] :
            ps_backends.append(backend)  

    windowi = SaveDialog(
        transient_for  = window,
        title            = _('Save'),
        hide_on_delete = True,
        page_range     = SETTING['Page range'],
        include_time   = SETTING["use_time"],
        meta_datetime  = datetime.datetime.now()+SETTING['datetime offset'],
        select_datetime = bool( SETTING['datetime offset']),
        meta_title                = SETTING['title'],
        meta_title_suggestions    = SETTING['title-suggestions'],
        meta_author               = SETTING['author'],
        meta_author_suggestions   = SETTING['author-suggestions'],
        meta_subject              = SETTING['subject'],
        meta_subject_suggestions  = SETTING['subject-suggestions'],
        meta_keywords             = SETTING['keywords'],
        meta_keywords_suggestions = SETTING['keywords-suggestions'],
        image_types               = image_types,
        image_type                = SETTING['image type'],
        ps_backends               = ps_backends,
        jpeg_quality              = SETTING["quality"],
        downsample_dpi            = SETTING['downsample dpi'],
        downsample                  = SETTING["downsample"],
        pdf_compression           = SETTING['pdf compression'],
        available_fonts           = fonts,
        text_position               = SETTING["text_position"],
        pdf_font                  = SETTING['pdf font'],
        can_encrypt_pdf           =  "pdftk"  in dependencies,
        tiff_compression          = SETTING['tiff compression'],
    )

    # Frame for page range

    windowi.add_page_range()
    windowi.add_image_type()

    # Post-save hook

    pshbutton = Gtk.CheckButton( label=_('Post-save hook') )
    pshbutton.set_tooltip_text(
        _(
'Run command on saved file. The available commands are those user-defined tools that do not specify %o'
        )
    )
    vbox = windowi.get_content_area()
    vbox.pack_start( pshbutton, False, True, 0 )
    update_post_save_hooks()
    vbox.pack_start( windowi.comboboxpsh, False, True, 0 )
    pshbutton.connect(
        'toggled' , lambda _action: windowi.comboboxpsh.set_sensitive( pshbutton.get_active() )
    )
    pshbutton.set_active( SETTING["post_save_hook"] )
    windowi.comboboxpsh.set_sensitive( pshbutton.get_active() )
    kbutton = Gtk.CheckButton( label=_('Close dialog on save') )
    kbutton.set_tooltip_text( _('Close dialog on save') )
    kbutton.set_active( SETTING["close_dialog_on_save"] )
    vbox.pack_start( kbutton, False, True, 0 )

    windowi.add_actions( [('gtk-save',
        lambda : save_button_clicked_callback( kbutton, pshbutton ) ),
        ('gtk-cancel', windowi.hide)]  )
    windowi.show_all()
    windowi.resize( 1, 1 )
    return


def list_of_page_uuids() :
    "Compile list of pages"
    uuids=[]
    pagelist =       slist.get_page_index( SETTING['Page range'], error_callback )
    if not pagelist :
        return []
    return [slist.data[i][2].uuid for i in pagelist]


def save_button_clicked_callback( kbutton, pshbutton ) :
    # Compile list of pages
    SETTING['Page range'] = windowi.page_range
    uuids = list_of_page_uuids()

    # dig out the image type, compression and quality
    SETTING['image type']         = windowi.image_type
    SETTING["close_dialog_on_save"] = kbutton.get_active()
    SETTING["post_save_hook"] = pshbutton.get_active()
    if SETTING["post_save_hook"]        and windowi.comboboxpsh.get_active()>EMPTY_LIST       :
        SETTING["current_psh"] = windowi.comboboxpsh.get_active_text()

    if re.search(r"pdf", SETTING['image type'] ):

            # dig out the compression
        SETTING["downsample"]        = windowi.downsample
        SETTING['downsample dpi']  = windowi.downsample_dpi
        SETTING['pdf compression'] = windowi.pdf_compression
        SETTING["quality"]           = windowi.jpeg_quality
        SETTING["text_position"] = windowi.text_position
        SETTING['pdf font']    = windowi.pdf_font

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])
        file_chooser=None
        if SETTING['image type'] == 'pdf' :
            windowi.update_config_dict(SETTING)

                # Set up file selector
            file_chooser = Gtk.FileChooserDialog(
                    title=_('PDF filename'),
                    parent=windowi, action=Gtk.FileChooserAction.SAVE,
                )
            file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK)

            filename = expand_metadata_pattern(
                    template           = SETTING['default filename'],
                    convert_whitespace =
                      SETTING['convert whitespace to underscores'],
                    author        = SETTING["author"],
                    title         = SETTING["title"],
                    docdate       = windowi.meta_datetime,
                    today_and_now = datetime.datetime.now(),
                    extension     = 'pdf',
                    subject       = SETTING["subject"],
                    keywords      = SETTING["keywords"],
                )
            file_chooser.set_current_name(filename)
            file_chooser.set_do_overwrite_confirmation(True)
 
        else :
            file_chooser = Gtk.FileChooserDialog(
                    title=_('PDF filename'),
                    parent=windowi, action=Gtk.FileChooserAction.OPEN,
                )
            file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        add_filter( file_chooser, _('PDF files'), ['pdf'] )
        file_chooser.set_current_folder( SETTING["cwd"] )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [ SETTING['image type'], uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='djvu':
        windowi.update_config_dict(SETTING)

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
                title=_('DjVu filename'),
                parent=windowi, action=Gtk.FileChooserAction.SAVE,
            )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        filename = expand_metadata_pattern(
                template           = SETTING['default filename'],
                convert_whitespace =
                  SETTING['convert whitespace to underscores'],
                author        = SETTING["author"],
                title         = SETTING["title"],
                docdate       = windowi.meta_datetime,
                today_and_now = datetime.datetime.now(),
                extension     = 'djvu',
                subject       = SETTING["subject"],
                keywords      = SETTING["keywords"],
            )
        file_chooser.set_current_name(filename)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        add_filter( file_chooser, _('DjVu files'), ['djvu'] )
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [        'djvu', uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='tif':
        SETTING['tiff compression'] = windowi.tiff_compression
        SETTING["quality"]            = windowi.jpeg_quality

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_('TIFF filename'),
            parent=windowi, action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        add_filter( file_chooser, _('Image files'),
                [SETTING['image type']] )
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [        'tif', uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='txt':

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
                title=_('Text filename'),
                parent=windowi, action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        add_filter( file_chooser, _('Text files'), ['txt'] )
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [        'txt', uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='hocr':

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
                title=_('hOCR filename'),
                parent=windowi, action=Gtk.FileChooserAction.SAVE,
            )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        file_chooser.set_do_overwrite_confirmation(True)
        add_filter( file_chooser, _('hOCR files'), ['hocr'] )
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [        'hocr', uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='ps':
        SETTING["ps_backend"] = windowi.ps_backend
        logger.info(f"Selected '{SETTING['ps_backend']}' as ps backend")

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
                title=_('PS filename'),
                parent=windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        add_filter( file_chooser, _('Postscript files'), ['ps'] )
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [        'ps', uuids ]
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='session':

            # cd back to cwd to save
        os.chdir( SETTING["cwd"])

            # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
                title=_('gscan2pdf session filename'),
                parent=windowi,
                action=Gtk.FileChooserAction.SAVE,
            )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder( SETTING["cwd"] )
        add_filter( file_chooser, _('gscan2pdf session files'), ['gs2p'] )
        file_chooser.set_do_overwrite_confirmation(True)
        file_chooser.connect(
                'response' , file_chooser_response_callback,
                [
        'gs2p']
            )
        file_chooser.show()

            # cd back to tempdir
        os.chdir( session.name)

    elif  SETTING['image type'] =='jpg':
        SETTING["quality"] = windowi.jpeg_quality
        save_image(uuids)

    else :
        save_image(uuids)


def file_chooser_response_callback( dialog, response, data ) :
    filetype, uuids = data
    suffix = filetype
    if   re.search(r"pdf",suffix,re.IGNORECASE|re.MULTILINE|re.DOTALL|re.VERBOSE) :
        suffix = 'pdf'
    if response == Gtk.ResponseType.OK :
        filename = dialog.get_filename()
        logger.debug(f"FileChooserDialog returned {filename}")
        if   not re.search(fr"[.]{suffix}$",filename,re.IGNORECASE|re.MULTILINE|re.DOTALL|re.VERBOSE) :
            filename = f"{filename}.{filetype}"
            if file_exists( dialog, filename ) :
                return  

        if file_writable( dialog, filename ) :
            return  

        # Update cwd
        SETTING["cwd"] = os.path.dirname(filename)
        if re.search(r"pdf",filetype):
            save_pdf( filename, filetype, uuids )

        elif filetype=='djvu':
            save_djvu( filename, uuids )

        elif filetype=='tif':
            save_tiff( filename, None, uuids )

        elif filetype=='txt':
            save_text( filename, uuids )

        elif filetype=='hocr':
            save_hocr( filename, uuids )

        elif filetype=='ps':
            if SETTING["ps_backend"] == 'libtiff' :
                tif =                       tempfile.TemporaryFile( dir = session, suffix = '.tif' )
                save_tiff( tif.filename(), filename, uuids )
 
            else :
                save_pdf( filename, 'ps', uuids )


        elif filetype=='gs2p':
            slist.save_session( filename, VERSION )

        if  windowi is not None and SETTING["close_dialog_on_save"] :
            windowi.hide()

    dialog.destroy()


def file_exists( chooser, filename ) :
    
    if os.path.isfile(filename)  :

        # File exists; get the file chooser to ask the user to confirm.
        chooser.set_filename(filename)

        def anonymous_62():
            """ Give the name change time to take effect."""
            chooser.response('ok')

        GLib.idle_add(anonymous_62)
        return True

    return


def file_writable( chooser, filename ) :
    
    if not os.access( os.path.dirname(filename), os.W_OK) : # FIXME: replace with try/except
        text = _('Directory %s is read-only') % (os.path.dirname(filename))  
        show_message_dialog(
            parent  = chooser,
            message_type    = 'error',
            buttons = Gtk.ButtonsType.CLOSE,
            text    = text
        )
        return True
 
    elif os.path.isfile(filename)  and not os.access( filename, os.W_OK) :# FIXME: replace with try/except
        text = _('File %s is read-only') % (filename)  
        show_message_dialog(
            parent  = chooser,
            message_type    = 'error',
            buttons = Gtk.ButtonsType.CLOSE,
            text    = text
        )
        return True

    return False


def save_image(uuids) :
    
    # cd back to cwd to save
    os.chdir( SETTING["cwd"])

    # Set up file selector
    file_chooser = Gtk.FileChooserDialog(
        title=_('Image filename'),
        parent=windowi, 
        action=Gtk.FileChooserAction.SAVE,
    )
    file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
    file_chooser.set_default_response(Gtk.ResponseType.OK)
    file_chooser.set_current_folder( SETTING["cwd"] )
    add_filter( file_chooser, _('Image files'),
        ['jpg', 'png', 'pnm', 'gif', 'tif', 'tiff', 'pdf', 'djvu', 'ps'] )
    file_chooser.set_do_overwrite_confirmation(True)
    if file_chooser.run() == Gtk.ResponseType.OK:
        filename = file_chooser.get_filename()

        # Update cwd
        SETTING["cwd"] = os.path.dirname(filename)

        # cd back to tempdir
        os.chdir( session.name)
        if len(uuids) > 1 :
            w = len(uuids)
            for i in range(1,len(uuids)+1) :
                current_filename = f"${filename}_%0${w}d.{SETTING['image type']}" % (i)                    
                if os.path.isfile(current_filename)  :
                    text = _('This operation would overwrite %s') % (current_filename)                        
                    show_message_dialog(
                        parent  = file_chooser,
                        message_type    = 'error',
                        buttons = Gtk.ButtonsType.CLOSE,
                        text    = text
                    )
                    file_chooser.destroy()
                    return


            filename = f"${filename}_%0${w}d.{SETTING['image type']}"
 
        else :
            if   not re.search(fr"[.]{SETTING['image type']}$",filename,re.IGNORECASE|re.MULTILINE|re.DOTALL|re.VERBOSE) :
                filename = f"{filename}.{SETTING['image type']}"
                if ( file_exists( file_chooser, filename ) ):
                    return  

            if file_writable( file_chooser, filename ):
                return  

        # Create the image
        logger.debug(f"Started saving {filename}")
        ( signal, pid )=(None,None)
        def anonymous_63(*argv):
            return update_tpbar(*argv)


        def save_image_started_callback( response ):
            #thread, process, completed, total
            pass
                
            # signal = setup_tpbar( process, completed, total, pid )
            # if signal is not None:
            #     return True  


        def anonymous_65(*argv):
            return update_tpbar(*argv)


        def save_image_finished_callback( response ):
            #new_page, pending
            filename = response.request.args[0]["path"]
            uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
            # if not pending :
            #     thbox.hide()
            # if  signal is not None :
            #     tcbutton.disconnect(signal)

            mark_pages(uuids)
            if  'view files toggle'  in SETTING                    and SETTING['view files toggle']                 :
                if len(uuids) > 1 :
                    w = len(uuids) 
                    for i in range(1,len(uuids)+1) :
                        launch_default_for_file( filename % (i)   )
                else :
                    launch_default_for_file(filename)

            logger.debug(f"Finished saving {filename}")


        pid = slist.save_image(
            path            = filename,
            list_of_pages   = uuids,
            queued_callback = anonymous_63 ,
            started_callback = save_image_started_callback ,
            running_callback = anonymous_65 ,
            finished_callback = save_image_finished_callback ,
            error_callback = error_callback
        )
        if  windowi is not None :
            windowi.hide()

    file_chooser.destroy()


def save_tiff( filename, ps, uuids ) :
    

    # Compile options

    options = {
        "compression" : SETTING['tiff compression'],
        "quality"     : SETTING["quality"],
        "ps"          : ps,
    }
    if SETTING["post_save_hook"] :
        options["post_save_hook"] = SETTING["current_psh"]

    ( signal, pid )=(None,None)
    def anonymous_67(*argv):
        return update_tpbar(*argv)


    def save_tiff_started_callback( response ):
        #thread, process, completed, total
        pass
            
        # signal =  setup_tpbar( process, completed, total, pid )
        # if signal is not None:
        #     return True  


    def anonymous_69(*argv):
        return update_tpbar(*argv)


    def save_tiff_finished_callback( response ):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        #new_page, pending
            
        # if not pending :
        #     thbox.hide()
        # if  signal is not None :
        #     tcbutton.disconnect(signal)

        mark_pages(uuids)
        file =   ps if ps is not None  else filename
        if  'view files toggle'  in SETTING                and SETTING['view files toggle']             :
            launch_default_for_file(file)

        logger.debug(f"Finished saving {file}")


    pid = slist.save_tiff(
        path            = filename,
        list_of_pages   = uuids,
        options         = options,
        queued_callback = anonymous_67 ,
        started_callback = save_tiff_started_callback ,
        running_callback = anonymous_69 ,
        finished_callback = save_tiff_finished_callback ,
        error_callback = error_callback
    )


def save_djvu( filename, uuids ) :
    
    # cd back to tempdir
    os.chdir( session.name)

    # Create the DjVu
    logger.debug(f"Started saving {filename}")
    ( signal, pid )=(None,None)
    options = {
        "set_timestamp"                       : SETTING["set_timestamp"],
        'convert whitespace to underscores' :
          SETTING['convert whitespace to underscores'],
    }
    if SETTING["post_save_hook"] :
        options["post_save_hook"] = SETTING["current_psh"]

    def anonymous_71(*argv):
        return update_tpbar(*argv)


    def save_djvu_started_callback( response ):
        pass
        # signal =  setup_tpbar( process, completed, total, pid )
        # if signal is not None:
        #     return True  


    def anonymous_73(*argv):
        return update_tpbar(*argv)


    def save_djvu_finished_callback( response ):
        filename = response.request.args[0]["path"]
        uuids = [x.uuid for x in response.request.args[0]["list_of_pages"]]
        # new_page, pending
        # if not pending :
        #     thbox.hide()
        # if  (signal is not None) :
        #     tcbutton.disconnect(signal)

        mark_pages(uuids)
        if  'view files toggle'  in SETTING                and SETTING['view files toggle']             :
            launch_default_for_file(filename)

        logger.debug(f"Finished saving {filename}")


    pid = slist.save_djvu(
        path          = filename,
        list_of_pages = uuids,
        options       = options,
        metadata      = collate_metadata(
            SETTING,datetime.datetime.now()),
        queued_callback = anonymous_71 ,
        started_callback = save_djvu_started_callback ,
        running_callback = anonymous_73 ,
        finished_callback = save_djvu_finished_callback ,
        error_callback = error_callback
    )


def save_text( filename, uuids ) :
    
    ( signal, pid, options )=(None,None,{})
    if SETTING["post_save_hook"] :
        options["post_save_hook"] = SETTING["current_psh"]

    def anonymous_75(*argv):
        return update_tpbar(*argv)


    def save_text_started_callback( response ):
        #thread, process, completed, total
        pass
        # signal = setup_tpbar( process, completed, total, pid )
        # if signal is not None:
        #     return True  


    def anonymous_77(*argv):
        return update_tpbar(*argv)


    def anonymous_78( new_page, pending ):
            
        if not pending :
            thbox.hide()
        if  (signal is not None) :
            tcbutton.disconnect(signal)

        mark_pages(uuids)
        if  'view files toggle'  in SETTING                and SETTING['view files toggle']             :
            launch_default_for_file(filename)

        logger.debug(f"Finished saving {filename}")


    pid = slist.save_text(
        path            = filename,
        list_of_pages   = uuids,
        options         = options,
        queued_callback = anonymous_75 ,
        started_callback = save_text_started_callback ,
        running_callback = anonymous_77 ,
        finished_callback = anonymous_78 ,
        error_callback = error_callback
    )


def save_hocr( filename, uuids ) :
    
    ( signal, pid, options )=(None,None,{})
    if SETTING["post_save_hook"] :
        options["post_save_hook"] = SETTING["current_psh"]

    def anonymous_79(*argv):
        return update_tpbar(*argv)


    def save_hocr_started_callback( response ):
        #thread, process, completed, total
        pass
        # signal = setup_tpbar( process, completed, total, pid )
        # if signal is not None:
        #     return True  


    def anonymous_81(*argv):
        return update_tpbar(*argv)


    def anonymous_82( new_page, pending ):
            
        if not pending :
            thbox.hide()
        if  (signal is not None) :
            tcbutton.disconnect(signal)

        mark_pages(uuids)
        if  'view files toggle'  in SETTING                and SETTING['view files toggle']             :
            launch_default_for_file(filename)

        logger.debug(f"Finished saving {filename}")


    pid = slist.save_hocr(
        path            = filename,
        list_of_pages   = uuids,
        options         = options,
        queued_callback = anonymous_79 ,
        started_callback = save_hocr_started_callback ,
        running_callback = anonymous_81 ,
        finished_callback = anonymous_82 ,
        error_callback = error_callback
    )


def email(_action):
    "Display page selector and email."
    if windowe is not None:
        windowe.present()
        return

    windowe = SaveDialog(
        transient_for  = window,
        title            = _('Email as PDF'),
        hide_on_delete = True,
        page_range     = SETTING['Page range'],
        include_time   = SETTING["use_time"],
        meta_datetime  = datetime.datetime.now()+SETTING['datetime offset'],
        select_datetime = bool( SETTING['datetime offset']),
        meta_title                = SETTING['title'],
        meta_title_suggestions    = SETTING['title-suggestions'],
        meta_author               = SETTING['author'],
        meta_author_suggestions   = SETTING['author-suggestions'],
        meta_subject              = SETTING['subject'],
        meta_subject_suggestions  = SETTING['subject-suggestions'],
        meta_keywords             = SETTING['keywords'],
        meta_keywords_suggestions = SETTING['keywords-suggestions'],
        jpeg_quality              = SETTING["quality"],
        downsample_dpi            = SETTING['downsample dpi'],
        downsample                  = SETTING["downsample"],
        pdf_compression           = SETTING['pdf compression'],
        text_position               = SETTING["text_position"],
        pdf_font                  = SETTING['pdf font'],
        can_encrypt_pdf           =  "pdftk"  in dependencies,
    )

    # Frame for page range
    windowe.add_page_range()

    # Metadata
    windowe.add_metadata()

    # PDF options
    vboxp, hboxp  = windowe.add_pdf_options()
    def email_callback():

            # Set options
        windowe.update_config_dict(SETTING)

            # Compile list of pages
        SETTING['Page range'] = windowe.page_range
        uuids = list_of_page_uuids()

            # dig out the compression
        SETTING["downsample"]        = windowe.downsample
        SETTING['downsample dpi']  = windowe.downsample_dpi
        SETTING['pdf compression'] = windowe.pdf_compression
        SETTING["quality"]           = windowe.jpeg_quality

            # Compile options
        options = {
                "compression"      : SETTING['pdf compression'],
                "downsample"       : SETTING["downsample"],
                'downsample dpi' : SETTING['downsample dpi'],
                "quality"          : SETTING["quality"],
                "text_position"    : SETTING["text_position"],
                "font"             : SETTING['pdf font'],
                'user-password'  : windowe.pdf_user_password,
            }
        filename = expand_metadata_pattern(
                template           = SETTING['default filename'],
                convert_whitespace =
                  SETTING['convert whitespace to underscores'],
                author        = SETTING["author"],
                title         = SETTING["title"],
                docdate       = windowe.meta_datetime,
                today_and_now = datetime.datetime.now(),
                extension     = 'pdf',
                subject       = SETTING["subject"],
                keywords      = SETTING["keywords"],
            )
        if   re.search(r"^\s+$",filename,re.MULTILINE|re.DOTALL|re.VERBOSE) :
            filename = 'document'
        pdf = f"{session}/{filename}.pdf"

            # Create the PDF
        ( signal, pid )=(None,None)
        def anonymous_84(*argv):
            return update_tpbar(*argv)


        def email_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal = setup_tpbar( process, completed, total,pid )
            # if signal is not None:
            #     return True  


        def anonymous_86(*argv):
            return update_tpbar(*argv)


        def anonymous_87( new_page, pending ):
                    
            if not pending :
                thbox.hide()
            if signal is not None :
                tcbutton.disconnect(signal)

            mark_pages(uuids)
            if  'view files toggle'  in SETTING                        and SETTING['view files toggle']                     :
                launch_default_for_file(pdf)

            status = exec_command(            [            'xdg-email', '--attach', pdf, 'x@y' ] )
            if status :
                show_message_dialog(
                            parent  = window,
                            message_type    = 'error',
                            buttons = Gtk.ButtonsType.CLOSE,
                            text    = _('Error creating email')
                        )

        pid = slist.save_pdf(
                path          = pdf,
                list_of_pages = uuids,
                metadata      = collate_metadata(
                    SETTING,datetime.datetime.now()
                ),
                options         = options,
                queued_callback = anonymous_84 ,
                started_callback = email_started_callback ,
                running_callback = anonymous_86 ,
                finished_callback = anonymous_87 ,
                error_callback = error_callback
            )
        windowe.hide()

    windowe.add_actions([
        ('gtk-ok',
        email_callback) ,
        ('gtk-cancel',
        lambda : windowe.hide())
    ])
    windowe.show_all()


def scan_dialog( action, hidden=False, scan=False ) :
    "Scan"
    global windows
    if windows :
        windows.show_all()
        update_postprocessing_options_callback(windows)
        return

    # If device not set by config and there is a default device, then set it
    if "device" not   in SETTING        and  'SANE_DEFAULT_DEVICE'  in os.environ     :
        SETTING["device"] = os.environ['SANE_DEFAULT_DEVICE']

    # scan dialog
    kwargs = {
        "transient_for"               : window,
        "title"                         : _('Scan Document'),
        "dir"                           : session,
        "hide_on_delete"              : True,
        "paper_formats"               : SETTING["Paper"],
        "allow_batch_flatbed"         : SETTING['allow-batch-flatbed'],
        "adf_defaults_scan_all_pages" :
          SETTING['adf-defaults-scan-all-pages'],
        "document"                   : slist,
        "ignore_duplex_capabilities" : SETTING['ignore-duplex-capabilities'],
        "cycle_sane_handle"    : SETTING['cycle sane handle'],
        "cancel_between_pages" : (
                    SETTING['allow-batch-flatbed']
                and SETTING['cancel-between-pages']
        ),
    }
    if SETTING["scan_window_width"]:
        kwargs["default_width"]= SETTING["scan_window_width"]
    if SETTING["scan_window_height"]:
        kwargs["default_height"]= SETTING["scan_window_height"]
    windows = SaneScanDialog(  **kwargs  )

    # Can't set the device when creating the window,
    # as the list does not exist then
    windows.connect(        'changed-device-list' , changed_device_list_callback )

    # Update default device
    windows.connect( 'changed-device' , changed_device_callback )
    windows.connect( 'changed-page-number-increment' ,          update_postprocessing_options_callback )
    windows.connect(        'changed-side-to-scan' , changed_side_to_scan_callback )
    signal=None

    def started_progress_callback( widget, message ):
        global spbar    
        global shbox
        global scbutton
        logger.debug(
                f"signal 'started-process' emitted with message: {message}")
        spbar.set_fraction(0)
        spbar.set_text(message)
        shbox.show_all()
        signal = scbutton.connect(                'clicked' , windows.cancel_scan             )

    windows.connect(        'started-process' , started_progress_callback     )
    windows.connect(        'changed-progress' , changed_progress_callback )
    windows.connect(        'finished-process' , finished_process_callback )
    windows.connect(        'process-error' , process_error_callback,        signal    )

    # Profiles
    for  profile in      SETTING["profile"].keys()   :
        windows._add_profile(
            profile,
            Profile(                SETTING["profile"][profile]            )
        )

    def changed_profile_callback( widget, profile ):
            
        SETTING['default profile'] = profile


    windows.connect('changed-profile' , changed_profile_callback)
    def added_profile_callback( widget, name, profile ):
            
        SETTING["profile"][name] = profile.get()


    windows.connect('added-profile' , added_profile_callback)
    def removed_profile_callback( widget, profile ):
            
        del(SETTING["profile"][profile]) 


    windows.connect('removed-profile' , removed_profile_callback)

    def changed_current_scan_options_callback( widget, profile, _uuid ):
        "Update the default profile when the scan options change"           
        SETTING['default-scan-options'] = profile.get()

    windows.connect(
        'changed-current-scan-options' , changed_current_scan_options_callback
    )
    def anonymous_96( widget, formats ):
            
        SETTING["Paper"] = formats


    windows.connect(
        'changed-paper-formats' , anonymous_96 
    )
    windows.connect( 'new-scan' , new_scan_callback )
    windows.connect(
        'changed-scan-option' , update_postprocessing_options_callback )
    add_postprocessing_options(windows)
    if not hidden :
        windows.show_all()
    update_postprocessing_options_callback(windows)
    logger.debug(f"before device {args.device}")
    if args.device :
        device_list=[]
        for d in         args.device :
            device_list.append(SimpleNamespace(name= d, label=d ))  

        windows.device_list=device_list
 
    elif not scan        and SETTING['cache-device-list']        and len( SETTING['device list'] )     :
        windows.device_list=SETTING['device list']
    else :
        windows.get_devices()


def changed_device_callback( widget, device ) :
        # $widget is $windows
    if  device != EMPTY :
        logger.info(f"signal 'changed-device' emitted with data: '{device}'")
        SETTING["device"] = device

        # Can't set the profile until the options have been loaded. This
        # should only be called the first time after loading the available
        # options
        widget.reloaded_signal = widget.connect(            'reloaded-scan-options' , reloaded_scan_options_callback )
 
    else :
        logger.info("signal 'changed-device' emitted with data: undef")


def changed_device_list_callback( widget, device_list ) :    # $widget is $windows
    
    logger.info( "signal 'changed-device-list' emitted with data: %s",device_list )
    if len(device_list) :

        # Apply the device blacklist
        if  'device blacklist'  in SETTING            and SETTING['device blacklist'] not in [None, ""]         :
            device_list = device_list
            i           = 0
            while i < len(device_list) :
                if                      re.search(device_list[i].name, SETTING['device blacklist'],re.MULTILINE|re.DOTALL|re.VERBOSE)                 :
                    logger.info(f"Blacklisting device {device_list[i].name}")
                    del(device_list[i])   
 
                else :
                    i+=1

            if len(device_list) < len(device_list) :
                widget.device_list=device_list
                return

        if SETTING['cache-device-list'] :
            SETTING['device list'] = device_list

       # Only set default device if it hasn't been specified on the command line
       # and it is in the the device list
        if  "device"  in SETTING  :
            for d in              device_list  :
                if SETTING["device"] == d.name :
                    widget.device=SETTING["device"]
                    return

        widget.device=device_list[0].name
 
    else :
        global windows
        windows=None


def changed_side_to_scan_callback( widget, _arg ) :
    logger.debug(f"changed_side_to_scan_callback( {widget, _arg} )")
    if len( slist.data )-1 > EMPTY_LIST :
        widget.page_number_start=slist.data[ len( slist.data )-1 ][0]+1
    else :
        widget.page_number_start=1


def reloaded_scan_options_callback( widget ) :
    """This should only be called the first time after loading the available options"""        # $widget is $windows
    widget.disconnect( widget.reloaded_signal )
    profiles = SETTING["profile"].keys() 
    if  'default profile'  in SETTING :
        widget.profile=SETTING['default profile']
 
    elif  'default-scan-options'  in SETTING :
        widget.set_current_scan_options(
            Profile(                SETTING['default-scan-options']            )
        )
 
    elif profiles :
        widget.profile=profiles[0]

    update_postprocessing_options_callback(widget)


def changed_progress_callback( widget, progress, message ) :
    
    global spbar    
    if  (progress is not None) and progress >= 0 and progress <= 1 :
        spbar.set_fraction(progress)
 
    else :
        spbar.pulse()

    if  message is not None :
        spbar.set_text(message)
    return


def import_scan_started_callback( response ):
    logger.debug(f"import_scan_started_callback( {response} )")
    if response.info:
        process, completed, total = response.info
        signal =               setup_tpbar( process, completed, total, pid )
        if signal is not None:
            return True  


def import_scan_finished_callback( response ):
    logger.debug(f"import_scan_finished_callback( {response} )")
    # new_page, pending
    # if not pending :
    #     thbox.hide()
    # if  signal is not None :
    #     tcbutton.disconnect(signal)

    # slist.save_session()


def new_scan_callback( self, image_object, page_number, xresolution, yresolution ) :
    
    # Update undo/redo buffers
    take_snapshot()
    rotate =          SETTING['rotate facing'] if page_number%2  else SETTING['rotate reverse']
    signal, pid=None,None
    options = {
        "page"            : page_number,
        "dir"             : session.name,
        "to_png"          : SETTING["to_png"],
        "rotate"          : rotate,
        "ocr"             : SETTING['OCR on scan'],
        "engine"          : SETTING['ocr engine'],
        "language"        : SETTING['ocr language'],
        "queued_callback" : update_tpbar ,
        "started_callback" : import_scan_started_callback ,
        "finished_callback" : import_scan_finished_callback ,
        "error_callback" : error_callback,
        "image_object"    : image_object,
        "resolution": (xresolution, yresolution, "PixelsPerInch"),
    }
    if SETTING['unpaper on scan'] :
        options["unpaper"] = unpaper

    if SETTING['threshold-before-ocr'] :
        options["threshold"] = SETTING['threshold tool']

    if SETTING["udt_on_scan"] :
        options["udt"] = SETTING["current_udt"]

    logger.info(
        f"Importing scan with resolution={xresolution},{yresolution}")

    slist.import_scan(**options)


def process_error_callback( widget, process, msg, signal ) :
    
    logger.info(f"signal 'process-error' emitted with data: {process} {msg}")
    if  signal is not None :
        global scbutton
        scbutton.disconnect(signal)

    global shbox
    shbox.hide()
    if process == 'open_device'        and   re.search(r"(Invalid[ ]argument|Device[ ]busy)",msg,re.MULTILINE|re.DOTALL|re.VERBOSE)     :
        error_name = 'error opening device'
        response=None
        if  error_name  in SETTING["message"]            and SETTING["message"][error_name]["response"] == 'ignore'         :
            response = SETTING["message"][error_name]["response"]
 
        else :
            dialog =               Gtk.MessageDialog( parent=window,destroy_with_parent=True,modal=True,
                message_type='question',
                buttons=Gtk.ButtonsType.OK )
            dialog.set_title( _('Error opening the last device used.') )
            area  = dialog.get_message_area()
            label = Gtk.Label(
                label=_('There was an error opening the last device used.') )
            area.add(label)
            radio1 = Gtk.RadioButton.new_with_label( None,
                label=_('Whoops! I forgot to turn it on. Try again now.') )
            area.add(radio1)
            radio2 = Gtk.RadioButton.new_with_label_from_widget( radio1,
                label=_('Rescan for devices') )
            area.add(radio2)
            radio3 = Gtk.RadioButton.new_with_label_from_widget( radio1,
                label=_('Restart gscan2pdf.') )
            area.add(radio3)
            radio4 = Gtk.RadioButton.new_with_label_from_widget( radio1,
                label=_("Just ignore the error. I don't need the scanner yet.") )
            area.add(radio4)
            cb_cache_device_list =               Gtk.CheckButton.new_with_label( _('Cache device list') )
            cb_cache_device_list.set_active( SETTING['cache-device-list'] )
            area.add(cb_cache_device_list)
            cb = Gtk.CheckButton.new_with_label(
                label=_("Don't show this message again") )
            area.add(cb)
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            if response != 'ok' or radio4.get_active() :
                response = 'ignore'
 
            elif radio1.get_active() :
                response = 'reopen' 
            elif radio3.get_active() :
                response = 'restart' 
            else                          :
                response = 'rescan'
            if cb.get_active() :
                SETTING["message"][error_name]["response"] = response

        global windows
        windows=None    # force scan dialog to be rebuilt
        if response == 'reopen' :
            scan_dialog()
 
        elif response == 'rescan' :
            scan_dialog( None, None, True )
 
        elif response == 'restart' :
            restart()

        # for ignore, we do nothing

        return

    show_message_dialog(
        parent           = widget,
        message_type             = 'error',
        buttons          = Gtk.ButtonsType.CLOSE,
        page             = EMPTY,
        process          = process,
        text             = msg,
        store_response = True
    )


def finished_process_callback( widget, process, button_signal=None ) :
    
    logger.debug(f"signal 'finished-process' emitted with data: {process}")
    if  button_signal is not None :
        global scbutton
        scbutton.disconnect(button_signal)

    global shbox
    shbox.hide()
    global windows
    if process == 'scan_pages'        and windows.sided == 'double'     :
        def anonymous_100():
            ( message, next )=(None,None)
            if windows.side_to_scan == 'facing' :
                message =                       _('Finished scanning facing pages. Scan reverse pages?')
                next = 'reverse'
 
            else :
                message =                       _('Finished scanning reverse pages. Scan facing pages?')
                next = 'facing'

            response = ask_question(
                    parent             = windows,
                    type               = 'question',
                    buttons            = Gtk.ButtonsType.OK_CANCEL,
                    text               = message,
                    default_response = Gtk.ResponseType.OK,
                    store_response   = True,
                    stored_responses = [Gtk.ResponseType.OK]
                )
            if response == Gtk.ResponseType.OK :
                windows.side_to_scan=next

        GLib.idle_add(anonymous_100)


def restart() :
    quit()
    os.execv(sys.executable, *sys.argv)


def update_postprocessing_options_callback(widget, _option_name=None, _option_val=None, _uuid=None) :
                                        # widget is windows
    options   = widget.available_scan_options
    increment = widget.page_number_increment
    global rotate_side_cmbx
    global rotate_side_cmbx2
    if  options is not None :
        if increment != 1 or options.can_duplex() :
            rotate_side_cmbx.show()
            rotate_side_cmbx2.show()
 
        else :
            rotate_side_cmbx.hide()
            rotate_side_cmbx2.hide()


def add_postprocessing_rotate(vbox) :
    
    hboxr = Gtk.HBox()
    vbox.pack_start( hboxr, False, False, 0 )
    rbutton = Gtk.CheckButton( label=_('Rotate') )
    rbutton.set_tooltip_text( _('Rotate image after scanning') )
    hboxr.pack_start( rbutton, True, True, 0 )
    side = [
    [
    'both',    _('Both sides'),   _('Both sides.') ],         [
    'facing',  _('Facing side'),  _('Facing side.') ],         [
    'reverse', _('Reverse side'), _('Reverse side.') ],
    ]
    global rotate_side_cmbx
    global rotate_side_cmbx2
    rotate_side_cmbx = ComboBoxText(data=side)
    rotate_side_cmbx.set_tooltip_text( _('Select side to rotate') )
    hboxr.pack_start( rotate_side_cmbx, True, True, 0 )
    rotate = [
    [
    _90_DEGREES,  _('90'),  _('Rotate image 90 degrees clockwise.') ],         [
    _180_DEGREES, _('180'), _('Rotate image 180 degrees clockwise.') ],         [
    _270_DEGREES, _('270'),             _('Rotate image 90 degrees anticlockwise.')
        ],
    ]
    comboboxr = ComboBoxText(data=rotate)
    comboboxr.set_tooltip_text( _('Select direction of rotation') )
    hboxr.pack_end( comboboxr, True, True, 0 )
    hboxr = Gtk.HBox()
    vbox.pack_start( hboxr, False, False, 0 )
    r2button = Gtk.CheckButton( label=_('Rotate') )
    r2button.set_tooltip_text( _('Rotate image after scanning') )
    hboxr.pack_start( r2button, True, True, 0 )
    side2=[]
    rotate_side_cmbx2 = Gtk.ComboBoxText()
    rotate_side_cmbx2.set_tooltip_text( _('Select side to rotate') )
    hboxr.pack_start( rotate_side_cmbx2, True, True, 0 )
    comboboxr2 = ComboBoxText(data=rotate)
    comboboxr2.set_tooltip_text( _('Select direction of rotation') )
    hboxr.pack_end( comboboxr2, True, True, 0 )

    def anonymous_101():
        if rbutton.get_active() :
            if side[ rotate_side_cmbx.get_active() ][0] != 'both' :
                hboxr.set_sensitive(True)
        else :
            hboxr.set_sensitive(False)

    rbutton.connect(
        'toggled' , anonymous_101 
    )

    def anonymous_102(arg):
        if side[ rotate_side_cmbx.get_active() ][0] == 'both' :
            hboxr.set_sensitive(False)
            r2button.set_active(False) 
        else :
            if rbutton.get_active() :
                hboxr.set_sensitive(True)

                # Empty combobox
            while rotate_side_cmbx2.get_active() >EMPTY_LIST  :
                rotate_side_cmbx2.remove(0)
                rotate_side_cmbx2.set_active(0)

            side2 = []
            for s in             side :
                if s[0] != 'both'                        and s[0] !=                        side[ rotate_side_cmbx.get_active() ][0]                     :
                    side2.append(s)  

            rotate_side_cmbx2.append_text( side2[0][1] )
            rotate_side_cmbx2.set_active(0)

    rotate_side_cmbx.connect(        'changed' , anonymous_102     )

    # In case it isn't set elsewhere
    comboboxr2.set_active_index(_90_DEGREES)
    if SETTING['rotate facing'] or SETTING['rotate reverse'] :
        rbutton.set_active(True)

    if SETTING['rotate facing'] == SETTING['rotate reverse'] :
        rotate_side_cmbx.set_active_index('both')
        comboboxr.set_active_index( SETTING['rotate facing'] )
 
    elif SETTING['rotate facing'] :
        rotate_side_cmbx.set_active_index('facing')
        comboboxr.set_active_index( SETTING['rotate facing'] )
        if SETTING['rotate reverse'] :
            r2button.set_active(True)
            rotate_side_cmbx2.set_active_index('reverse')
            comboboxr2.set_active_index( SETTING['rotate reverse'] )

 
    else :
        rotate_side_cmbx.set_active_index('reverse')
        comboboxr.set_active_index( SETTING['rotate reverse'] )

    return ( rotate, side, side2, rbutton, r2button,
        comboboxr, comboboxr2 )


def add_postprocessing_udt(vboxp) :
    
    hboxudt = Gtk.HBox()
    vboxp.pack_start( hboxudt, False, False, 0 )
    udtbutton =       Gtk.CheckButton( label=_('Process with user-defined tool') )
    udtbutton.set_tooltip_text(
        _('Process scanned images with user-defined tool') )
    hboxudt.pack_start( udtbutton, True, True, 0 )
    if not SETTING["user_defined_tools"] :
        hboxudt.set_sensitive(False)
        udtbutton.set_active(False)
 
    elif SETTING["udt_on_scan"] :
        udtbutton.set_active(True)

    return udtbutton, add_udt_combobox(hboxudt)


def add_udt_combobox(hbox) :
    
    toolarray=[]
    for t in      SETTING["user_defined_tools"]  :
        toolarray.append([        t, t ]) 

    combobox = ComboBoxText(data=toolarray)
    combobox.set_active_index( SETTING["current_udt"] )
    hbox.pack_start( combobox, True, True, 0 )
    return combobox


def add_postprocessing_ocr(vbox) :
    
    hboxo = Gtk.HBox()
    vbox.pack_start( hboxo, False, False, 0 )
    obutton = Gtk.CheckButton( label=_('OCR scanned pages') )
    obutton.set_tooltip_text( _('OCR scanned pages') )
    if not dependencies["ocr"] :
        hboxo.set_sensitive(False)
        obutton.set_active(False)
 
    elif SETTING['OCR on scan'] :
        obutton.set_active(True)

    hboxo.pack_start( obutton, True, True, 0 )
    comboboxe = ComboBoxText(data=ocr_engine)
    comboboxe.set_tooltip_text( _('Select OCR engine') )
    hboxo.pack_end( comboboxe, True, True, 0 )
    comboboxtl, hboxtl, tesslang=None,None,[]

    if dependencies["tesseract"] :
        hboxtl, comboboxtl, tesslang = add_tess_languages(vbox)

        def ocr_engine_changed_callback(comboboxe):
            if comboboxe.get_active_text() == 'tesseract' :
                hboxtl.show_all() 
            else :
                hboxtl.hide()

        comboboxe.connect(            'changed' , ocr_engine_changed_callback         )
        if not obutton.get_active() :
            hboxtl.set_sensitive(False)

        obutton.connect(            'toggled' , lambda x: hboxtl.set_sensitive(x.get_active())         )

    comboboxe.set_active_index( SETTING['ocr engine'] )
    if len(ocr_engine) > 0 and comboboxe.get_active_index() is None :
        comboboxe.set_active(0)

    # Checkbox & SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox.pack_start( hboxt, False, True, 0 )
    cbto = Gtk.CheckButton( label=_('Threshold before OCR') )
    cbto.set_tooltip_text(
        _(
                'Threshold the image before performing OCR. '
              + 'This only affects the image passed to the OCR engine, and not the image stored.'
        )
    )
    cbto.set_active( SETTING['threshold-before-ocr'] )
    hboxt.pack_start( cbto, False, True, 0 )
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end( labelp, False, True, 0 )
    spinbutton = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbutton.set_value( SETTING['threshold tool'] )
    spinbutton.set_sensitive( cbto.get_active() )
    hboxt.pack_end( spinbutton, False, True, 0 )
    def anonymous_106():
        spinbutton.set_sensitive( cbto.get_active() )


    cbto.connect(
        'toggled' , anonymous_106 
    )
    return (
        obutton,    comboboxe, hboxtl,  comboboxtl, 
        tesslang, cbto,       spinbutton,
    )


def add_postprocessing_options(self) :
    
    scwin = Gtk.ScrolledWindow()
    self.notebook       .append_page( scwin, Gtk.Label( label=_('Postprocessing') ) )
    scwin.set_policy( Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC )
    vboxp = Gtk.VBox()
    vboxp.set_border_width( self.get_border_width() )
    scwin.add(vboxp)

    # Rotate
    rotate, side, side2, rbutton, r2button, comboboxr, comboboxr2        = add_postprocessing_rotate(vboxp)

    # CheckButton for unpaper
    hboxu = Gtk.HBox()
    vboxp.pack_start( hboxu, False, False, 0 )
    ubutton = Gtk.CheckButton( label=_('Clean up images') )
    ubutton.set_tooltip_text( _('Clean up scanned images with unpaper') )
    hboxu.pack_start( ubutton, True, True, 0 )
    if not dependencies["unpaper"] :
        ubutton.set_sensitive(False)
        ubutton.set_active(False)
 
    elif SETTING['unpaper on scan'] :
        ubutton.set_active(True)

    button = Gtk.Button( label=_('Options') )
    button.set_tooltip_text( _('Set unpaper options') )
    hboxu.pack_end( button, True, True, 0 )
    def anonymous_107():
        windowuo = Dialog(
                transient_for = window,
                title           = _('unpaper options'),
            )
        unpaper.add_options( windowuo.get_content_area() )
        def unpaper_options_callback():

                    # Update $SETTING
            SETTING['unpaper options'] = unpaper.get_options()
            windowuo.destroy()

        windowuo.add_actions([
                ('gtk-ok',
                unpaper_options_callback) ,
                ('gtk-cancel',
                lambda : windowuo.destroy())])
        windowuo.show_all()

    button.connect(        'clicked' , anonymous_107     )
        # CheckButton for user-defined tool
    udtbutton, self.comboboxudt = add_postprocessing_udt(vboxp)
    (
        obutton,    comboboxe, hboxtl, comboboxtl,
        tesslang,  tbutton,    tsb
    ) = add_postprocessing_ocr(vboxp)
    def clicked_scan_button_cb(w):
        SETTING['rotate facing']  = 0
        SETTING['rotate reverse'] = 0
        global rotate_side_cmbx
        global rotate_side_cmbx2
        if rbutton.get_active() :
            if rotate_side_cmbx.get_active_index() =='both'  :
                SETTING['rotate facing']  = comboboxr.get_active_index()
                SETTING['rotate reverse'] = SETTING['rotate facing']
 
            elif rotate_side_cmbx.get_active_index() =='facing'  :
                SETTING['rotate facing'] = comboboxr.get_active_index()
 
            else :
                SETTING['rotate reverse'] = comboboxr.get_active_index()

            if r2button.get_active() :
                if rotate_side_cmbx2.get_active_index()  =='facing' :
                    SETTING['rotate facing'] =                           comboboxr2.get_active_index()
 
                else :
                    SETTING['rotate reverse'] =                           comboboxr2.get_active_index()

        logger.info(f"rotate facing {SETTING['rotate facing']}")
        logger.info(f"rotate reverse {SETTING['rotate reverse']}")
        SETTING['unpaper on scan'] = ubutton.get_active()
        logger.info(f"unpaper {SETTING['unpaper on scan']}")
        SETTING["udt_on_scan"] = udtbutton.get_active()
        SETTING["current_udt"] = self.comboboxudt.get_active_text()
        logger.info(f"UDT {SETTING['udt_on_scan']}")
        if  "current_udt"  in SETTING :
            logger.info(f"Current UDT {SETTING['current_udt']}")

        SETTING['OCR on scan'] = obutton.get_active()
        logger.info(f"OCR {SETTING['OCR on scan']}")
        if SETTING['OCR on scan'] :
            SETTING['ocr engine'] = comboboxe.get_active_index()
            if SETTING['ocr engine'] is None :
                SETTING['ocr engine'] = ocr_engine[0][0]
            logger.info(f"ocr engine {SETTING['ocr engine']}")
            if SETTING['ocr engine'] == 'tesseract' :
                SETTING['ocr language'] = comboboxtl.get_active_index()
                logger.info(f"ocr language {SETTING['ocr language']}")

            SETTING['threshold-before-ocr'] = tbutton.get_active()
            logger.info(
                    f"threshold-before-ocr {SETTING['threshold-before-ocr']}")
            SETTING['threshold tool'] = tsb.get_value()

    self.connect(        'clicked-scan-button' , clicked_scan_button_cb     )
    def show_callback(w):
        i = comboboxe.get_active()
        if  i > -1 and hboxtl is not None                and                ocr_engine[ i ][0] != 'tesseract'             :
            hboxtl.hide()

    self.connect(        'show' , show_callback     )
    #$self->{notebook}->get_nth_page(1)->show_all;


def print_dialog(_action):
    "print"
    os.chdir( SETTING["cwd"])
    print_op = Gtk.PrintOperation()
    if print_settings is not None:
        print_op.set_print_settings(print_settings)

    def anonymous_112( op, context ):
            
        settings = op.get_print_settings()
        pages    = settings.print_pages
        page_list=[]
        if pages == 'ranges' :
            page_set = Set.IntSpan()
            ranges   = settings.page_ranges
            for i in              re.split(r",",ranges)    :
                page_set.I(i)

            for i in              range(len( slist.data ))    :
                if page_set.member( slist.data[i][0] ) :
                    page_list.append(i)  
        else :
            page_list = [ range(len( slist.data ))   ]

        op.set_n_pages( len(page_list)  )


    print_op.connect(
        'begin-print' , anonymous_112 
    )
    def anonymous_113( op, context, page_number ):
            
        page = slist.data[page_number][2]
        cr = context.get_cairo_context()

            # Context dimensions
        pwidth  = context.get_width()
        pheight = context.get_height()

            # Image dimensions
            # quotes required to prevent File::Temp object being clobbered

        pixbuf  = Gdk.Pixbuf.new_from_file(f"{page}->{filename}")
        ratio   = page["xresolution"] / page["yresolution"]
        iwidth  = pixbuf.get_width()
        iheight = pixbuf.get_height()

            # Scale context to fit image

        scale = pwidth / iwidth * ratio
        if pheight / iheight < scale :
            scale = pheight / iheight
        cr.scale( scale / ratio, scale )

            # Set source pixbuf
        Gdk.cairo_set_source_pixbuf( cr, pixbuf, 0, 0 )

            # Paint
        cr.paint()
        return


    print_op.connect       (   # FIXME: check print preview works for pages with ratios other than 1.
        'draw-page' , anonymous_113 
      )
    res = print_op.run( 'print-dialog', window )
    if res == 'apply' :
        print_settings = print_op.get_print_settings()
    os.chdir( session.name)


def cut_selection() :
    """Cut the selection"""
    clipboard = slist.cut_selection()



def copy_selection() :
    """Copy the selection"""
    clipboard = slist.copy_selection(True)



def paste_selection() :
    """Paste the selection"""
    if   (clipboard is None) :
        return
    pages = slist.get_selected_indices()
    if pages :
        slist.paste_selection( clipboard, pages[-1], 'after', True )
 
    else :
        slist.paste_selection( clipboard, None, None, True )


def delete_selection() :
    "Delete the selected scans"
    # Update undo/redo buffers
    take_snapshot()
    slist.delete_selection_extra()

    # Reset start page in scan dialog
    global windows
    if windows :
        windows.reset_start_page()


def select_all() :
    "Select all scans"
    # if ($textview -> has_focus) {
    #  my ($start, $end) = $textbuffer->get_bounds;
    #  $textbuffer->select_range ($start, $end);
    # }
    # else {

    slist.get_selection().select_all()

    # }



def select_odd_even(odd) :
    """Select all odd(0) or even(1) scans"""    
    selection=[]
    for i in      range(len( slist.data ))    :
        if slist.data[i][0] % 2 ^ odd :
            selection.append(i)  

    slist.get_selection().unselect_all()
    slist.select(selection)



def select_invert() :
    """Invert selection"""
    selection = slist.get_selected_indices()
    inverted = []
    for i in      range(len( slist.data ))    :
        if i not in selection :
            inverted.append(_)  
    slist.get_selection().unselect_all()
    slist.select(inverted)


def select_modified_since_ocr() :
    selection=[]
    for  page in      range(len( slist.data ))    :
        dirty_time = slist.data[page][2]["dirty_time"]
        ocr_flag   = slist.data[page][2]["ocr_flag"]
        ocr_time   = slist.data[page][2]["ocr_time"]
        dirty_time =   dirty_time if (dirty_time is not None)  else 0
        ocr_time   =     ocr_time if (ocr_time is not None)    else 0
        if ocr_flag and ( ocr_time <= dirty_time ) :
            selection.append(_)  


    slist.get_selection().unselect_all()
    slist.select(selection)
    return



def select_no_ocr() :
    "Select pages with no ocr output"
    selection=[]
    for i in      range(len( slist.data ))    :
        if  not   hasattr(slist.data[i][2],'text_layer') :
            selection.append(i)  

    slist.get_selection().unselect_all()
    slist.select(selection)


def clear_ocr() :
    "Clear the OCR output from selected pages"
    # Update undo/redo buffers
    take_snapshot()

    # Clear the existing canvas
    global canvas
    canvas.clear_text()
    selection = slist.get_selected_indices()
    for i in     selection :
        slist.data[i][2].text_layer = None

    slist.save_session()


def analyse_select_blank() :
    "Analyse and select blank pages"
    analyse( 1, 0 )


def select_blank_pages() :
    "Select blank pages"
    for  page in      range(len( slist.data ))    :

        # compare Std Dev to threshold
        if slist.data[page][2]["std_dev"] <= SETTING['Blank threshold']         :
            slist.select(page)
            logger.info('Selecting blank page')
 
        else :
            slist.unselect(page)
            logger.info('Unselecting non-blank page')

        logger.info( 'StdDev: '
              + slist.data[page][2]["std_dev"]
              + ' threshold: '
              + SETTING['Blank threshold'] )

    return



def analyse_select_dark() :
    """Analyse and select dark pages
"""
    analyse( 0, 1 )
    return



def select_dark_pages() :
    """Select dark pages
"""
    for  page in      range(len( slist.data ))    :

        #compare Mean to threshold

        if slist.data[page][2]["mean"] <= SETTING['Dark threshold'] :
            slist.select(page)
            logger.info('Selecting dark page')
 
        else :
            slist.unselect(page)
            logger.info('Unselecting non-dark page')

        logger.info( 'mean: '
              + slist.data[page][2]["mean"]
              + ' threshold: '
              + SETTING['Dark threshold'] )

    return



def about(_action):
    "Display about dialog"    
    about = Gtk.AboutDialog()

    # Gtk.AboutDialog->set_url_hook ($func, $data=undef);
    # Gtk.AboutDialog->set_email_hook ($func, $data=undef);

    about.set_program_name(prog_name)
    about.set_version(VERSION)
    authors = [
    'Frederik Elwert',         'Klaus Ethgen',         'Andy Fingerhut',         'Leon Fisk',         'John Goerzen',         'Alistair Grant',         'David Hampton',         'Sascha Hunold',         'Jason Kankiewicz',         'Matthijs Kooijman',         'Peter Marschall',         'Chris Mayo',         'Hiroshi Miura',         'Petr Písař',         'Pablo Saratxaga',         'Torsten Schönfeld',         'Roy Shahbazian',         'Jarl Stefansson',         'Wikinaut',         'Jakub Wilk',         'Sean Dreilinger',
    ]
    about.set_authors(
    [
    'Jeff Ratcliffe'] )
    about.add_credit_section( 'Patches gratefully received from', authors )
    about.set_comments( _('To aid the scan-to-PDF process') )
    about.set_copyright( _('Copyright 2006--2022 Jeffrey Ratcliffe') )
    licence = """gscan2pdf --- to aid the scan to PDF or DjVu process
Copyright 2006 -- 2022 Jeffrey Ratcliffe <jffry@posteo.net>

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
    about.set_website('http://gscan2pdf.sf.net')
    translators =       """Yuri Chornoivan
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
""" # inverted commas required around EOS because of UTF-8 in $translators
    about.set_translator_credits(translators)
    about.set_artists(
    [
    'lodp, Andreas E.'] )
    about.set_logo(
        Gdk.Pixbuf.new_from_file(f"{iconpath}/gscan2pdf.svg") )
    about.set_transient_for(window)
    about.run()
    about.destroy()
    return



def renumber_dialog(_action):
    "Dialog for renumber"
    if windowrn is not None:
        windowrn.present()
        return

    windowrn = Dialog.Renumber(
        transient_for  = window,
        document         = slist,
        logger           = logger,
        hide_on_delete = False,
    )

    def anonymous_114():
        """    # Update undo/redo buffers
"""
        take_snapshot()


    windowrn.connect(
        'before-renumber' , anonymous_114 
    )
    def anonymous_115(msg):
            
        show_message_dialog(
                parent  = windowrn,
                message_type    = 'error',
                buttons = Gtk.ButtonsType.CLOSE,
                text    = msg
            )


    windowrn.connect(
        'error' , anonymous_115 
    )
    windowrn.show_all()


def indices2pages(indices) :
    "Helper function to convert an array of indices into an array of Gscan2pdf::Page objects"    
    pages=[]
    for i in     indices :
        pages.append(slist.data[i][2].uuid)  

    return pages


def rotate( angle, pagelist, callback ) :
    """Rotate selected images"""    

    # Update undo/redo buffers
    take_snapshot()
    for  page in      pagelist  :
        ( signal, pid )=(None,None)
        def anonymous_116(*argv):
            return update_tpbar(*argv)


        def rotate_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal =  setup_tpbar( process, completed, total, pid )
            if signal is not None:
                return True  


        def anonymous_118( new_page, pending ):
                
            if callback      :
                callback(new_page)
            if not pending :
                thbox.hide()
            if  (signal is not None) :
                tcbutton.disconnect(signal)

            slist.save_session()


        pid = slist.rotate(
            angle           = angle,
            page            = page,
            queued_callback = anonymous_116 ,
            started_callback = rotate_started_callback ,
            finished_callback = anonymous_118 ,
            error_callback   = error_callback,
            display_callback = display_callback ,
        )


def analyse( select_blank, select_dark ) :
    "Analyse selected images"    

    # Update undo/redo buffers
    take_snapshot()
    pages_to_analyse=[]
    for  i in      range(len( slist.data ))    :
        dirty_time   = slist.data[i][2]["dirty_time"]
        analyse_time = slist.data[i][2]["analyse_time"]
        dirty_time   =     dirty_time if (dirty_time is not None)    else 0
        analyse_time =   analyse_time if (analyse_time is not None)  else 0
        if analyse_time <= dirty_time :
            logger.info(
f"Updating: {slist}->{data}[{i}][0] analyse_time: {analyse_time} dirty_time: {dirty_time}"
            )
            pages_to_analyse.append(slist.data[i][2].uuid)  


    if len(pages_to_analyse) > 0 :
        ( signal, pid )=(None,None)
        def anonymous_120(*argv):
            return update_tpbar(*argv)


        def analyse_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal = setup_tpbar( process, completed, total, pid )
            # if signal is not None:
            #     return True  


        def anonymous_122(*argv):
            return update_tpbar(*argv)


        def anonymous_123( new_page, pending ):
                
            if not pending :
                thbox.hide()
            if  (signal is not None) :
                tcbutton.disconnect(signal)

            if select_blank :
                select_blank_pages()
            if select_dark  :
                select_dark_pages()
            slist.save_session()


        pid = slist.analyse(
            list_of_pages   = pages_to_analyse,
            queued_callback = anonymous_120 ,
            started_callback = analyse_started_callback ,
            running_callback = anonymous_122 ,
            finished_callback = anonymous_123 ,
            error_callback = error_callback,
        )
 
    else :
        if select_blank :
            select_blank_pages()
        if select_dark  :
            select_dark_pages()


def handle_clicks( widget, event ) :
    "Handle right-clicks"    
    global uimanager
    if event.button == 3 :#RIGHT_MOUSE_BUTTON      
        if isinstance(widget, ImageView) :    # main image
            uimanager.get_widget('/Detail_Popup')               .popup_at_pointer( event )
 
        else :                                      # Thumbnail simplelist
            SETTING['Page range'] = 'selected'
            uimanager.get_widget('/Thumb_Popup')               .popup_at_pointer( event )

        # block event propagation
        return True

    # allow event propagation
    return False


def threshold(_action) :
    "Display page selector and on apply threshold accordingly"
    windowt = Dialog(
        transient_for = window,
        title           = _('Threshold'),
    )

    # Frame for page range
    windowt.add_page_range()

    # SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox  = windowt.get_content_area()
    vbox.pack_start( hboxt, False, True, 0 )
    label = Gtk.Label( label=_('Threshold') )
    hboxt.pack_start( label, False, True, 0 )
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end( labelp, False, True, 0 )
    spinbutton = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbutton.set_value( SETTING['threshold tool'] )
    hboxt.pack_end( spinbutton, False, True, 0 )

    def threshold_apply_callback():
            # HBox for buttons
            # Update undo/redo buffers
        take_snapshot()
        SETTING['threshold tool'] = spinbutton.get_value()
        SETTING['Page range']     = windowt.page_range
        pagelist =               slist.get_page_index( SETTING['Page range'],
                error_callback )
        if not pagelist :
            return
        page = 0
        for  i in         pagelist :
            page+=1
            ( signal, pid )=(None,None)
            def anonymous_125(*argv):
                return update_tpbar(*argv)


            def threshold_started_callback( response ):
                #thread, process, completed, total
                pass
                        
                # signal = setup_tpbar( process, completed, total,                            pid )
                # if signal is not None:
                #     return True  


            def threshold_finished_callback( response ):
                #new_page, pending
                pass
                # if not pending :
                #     thbox.hide()
                # if signal is not None :
                #     tcbutton.disconnect(signal)

                #slist.save_session()

            pid = slist.threshold(
                    threshold       = SETTING['threshold tool'],
                    page            = slist.data[i][2].uuid,
                    queued_callback = anonymous_125 ,
                    started_callback = threshold_started_callback ,
                    finished_callback = threshold_finished_callback ,
                    error_callback   = error_callback,
                    display_callback = display_callback ,
                )

    windowt.add_actions([(
        'gtk-apply',
        threshold_apply_callback) ,
        ('gtk-cancel',
        lambda : windowt.destroy())
    ])
    windowt.show_all()


def brightness_contrast(_action) :
    "Display page selector and on apply brightness & contrast accordingly"
    windowt = Dialog(
        transient_for = window,
        title           = _('Brightness / Contrast'),
    )
    hbox, label =None,None

    # Frame for page range
    windowt.add_page_range()

    # SpinButton for brightness
    hbox = Gtk.HBox()
    vbox = windowt.get_content_area()
    vbox.pack_start( hbox, False, True, 0 )
    label = Gtk.Label( label=_('Brightness') )
    hbox.pack_start( label, False, True, 0 )
    label = Gtk.Label(label=PERCENT)
    hbox.pack_end( label, False, True, 0 )
    spinbuttonb = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbuttonb.set_value( SETTING['brightness tool'] )
    hbox.pack_end( spinbuttonb, False, True, 0 )

    # SpinButton for contrast
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, False, True, 0 )
    label = Gtk.Label( label=_('Contrast') )
    hbox.pack_start( label, False, True, 0 )
    label = Gtk.Label(label=PERCENT)
    hbox.pack_end( label, False, True, 0 )
    spinbuttonc = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbuttonc.set_value( SETTING['contrast tool'] )
    hbox.pack_end( spinbuttonc, False, True, 0 )

    def brightness_contrast_callback():
            # HBox for buttons
            # Update undo/redo buffers
        take_snapshot()
        SETTING['brightness tool'] = spinbuttonb.get_value()
        SETTING['contrast tool']   = spinbuttonc.get_value()
        SETTING['Page range']      = windowt.page_range
        pagelist =               slist.get_page_index( SETTING['Page range'],
                error_callback )
        if not pagelist :
            return
        for  i in         pagelist :
            ( signal, pid )=(None,None)
            def anonymous_131(*argv):
                return update_tpbar(*argv)


            def brightness_contrast_started_callback( response ):
                #thread, process, completed, total
                pass
                        
                # signal = setup_tpbar( process, completed, total, pid )
                # if signal is not None:
                #     return True  


            def anonymous_133( new_page, pending ):
                        
                if not pending :
                    thbox.hide()
                if signal is not None :
                    tcbutton.disconnect(signal)

                slist.save_session()

            pid = slist.brightness_contrast(
                    brightness      = SETTING['brightness tool'],
                    contrast        = SETTING['contrast tool'],
                    page            = slist.data[i][2].uuid,
                    queued_callback = anonymous_131 ,
                    started_callback = brightness_contrast_started_callback ,
                    finished_callback = anonymous_133 ,
                    error_callback   = error_callback,
                    display_callback = display_callback ,
                )

    windowt.add_actions([
        ('gtk-apply',
        brightness_contrast_callback) ,
        ('gtk-cancel',
        lambda : windowt.destroy())
    ])
    windowt.show_all()


def negate(_action) :
    "Display page selector and on apply negate accordingly"
    windowt = Dialog(
        transient_for = window,
        title           = _('Negate'),
    )

    # Frame for page range
    windowt.add_page_range()

    def negate_callback():
            # HBox for buttons
            # Update undo/redo buffers
        take_snapshot()
        SETTING['Page range'] = windowt.page_range
        pagelist = slist.get_page_index( SETTING['Page range'], error_callback )
        if not pagelist :
            return
        for i in pagelist:
            signal, pid = None, None
            def anonymous_137(*argv):
                return update_tpbar(*argv)


            def negate_started_callback( response ):#TODO: all these started callbacks are identical
                #thread, process, completed, total
                pass
                        
                # signal = setup_tpbar( process, completed, total, pid )
                # if signal is not None:
                #     return True  


            def negate_finished_callback( response ):
                # new_page, pending                        
                # if not pending :
                #     thbox.hide()
                # if signal is not None :
                #     tcbutton.disconnect(signal)
                # slist.save_session()
                pass


            pid = slist.negate(
                    page            = slist.data[i][2].uuid,
                    queued_callback = anonymous_137 ,
                    started_callback = negate_started_callback ,
                    finished_callback = negate_finished_callback ,
                    error_callback   = error_callback,
                    display_callback = display_callback ,
                )

    windowt.add_actions([
        ('gtk-apply',
        negate_callback) ,
        ('gtk-cancel',
        lambda : windowt.destroy())
    ])
    windowt.show_all()


def unsharp(_action) :
    "Display page selector and on apply unsharp accordingly"
    windowum = Dialog(
        transient_for = window,
        title           = _('Unsharp mask'),
    )

    # Frame for page range

    windowum.add_page_range()
    spinbuttonr = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbuttons =       Gtk.SpinButton.new_with_range( 0, MAX_SIGMA, SIGMA_STEP )
    spinbuttong = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbuttont =       Gtk.SpinButton.new_with_range( 0, 1, UNIT_SLIDER_STEP )
    layout = [
    [
    _('Radius'),             spinbuttonr,             _('pixels'),             SETTING['unsharp radius'],             _(
'The radius of the Gaussian, in pixels, not counting the center pixel (0 = automatic).'
            ),
        ],         [
    _('Sigma'), spinbuttons, _('pixels'),             SETTING['unsharp sigma'],             _('The standard deviation of the Gaussian.'),
        ],         [
    _('Gain'),             spinbuttong,             PERCENT,             SETTING['unsharp gain'],             _(
'The percentage of the difference between the original and the blur image that is added back into the original.'
            ),
        ],         [
    _('Threshold'),             spinbuttont,             None,             SETTING['unsharp threshold'],             _(
'The threshold, as a fraction of QuantumRange, needed to apply the difference amount.'
            ),
        ],
    ]

    # grid for layout
    grid = Gtk.Grid()
    vbox = windowum.get_content_area()
    vbox.pack_start( grid, True, True, 0 )
    for  row in      range(len(layout))    :
        col   = 0
        hbox  = Gtk.HBox()
        label = Gtk.Label( label=layout[row][col] )
        grid.attach( hbox, col, row, 1, 1)
        col+=1 
        hbox.pack_start( label, False, True, 0 )
        hbox = Gtk.HBox()
        hbox.pack_end( layout[row][col], True, True, 0 )
        grid.attach( hbox, col, row, 1, 1 )
        col+=1 
        if    col    in layout[row] :
            hbox = Gtk.HBox()
            grid.attach( hbox, col, row, 1, 1 )
            label = Gtk.Label( label=layout[row][col] )
            hbox.pack_start( label, False, True, 0 )

        col+=1 
        if    col    in layout[row] :
            layout[row][1].set_value( layout[row][col] )

        col+=1 
        layout[row][1].set_tooltip_text( layout[row][ col ] )


    def unsharp_callback():
            # HBox for buttons
            # Update undo/redo buffers
        take_snapshot()
        SETTING['unsharp radius']    = spinbuttonr.get_value()
        SETTING['unsharp sigma']     = spinbuttons.get_value()
        SETTING['unsharp gain']      = spinbuttong.get_value()
        SETTING['unsharp threshold'] = spinbuttont.get_value()
        SETTING['Page range']        = windowum.page_range
        pagelist =               slist.get_page_index( SETTING['Page range'],
                error_callback )
        if not pagelist :
            return
        for  i in         pagelist :
            ( signal, pid )=(None,None)
            def anonymous_143(*argv):
                return update_tpbar(*argv)


            def unsharp_started_callback( response ):
                #thread, process, completed, total
                pass
                        
                # signal = setup_tpbar( process, completed, total,pid )
                # if signal is not None:
                #     return True  


            def anonymous_145( new_page, pending ):
                        
                if not pending :
                    thbox.hide()
                if signal is not None :
                    tcbutton.disconnect(signal)

                slist.save_session()

            pid = slist.unsharp(
                    page            = slist.data[i][2].uuid,
                    radius          = SETTING['unsharp radius'],
                    sigma           = SETTING['unsharp sigma'],
                    gain            = SETTING['unsharp gain'],
                    threshold       = SETTING['unsharp threshold'],
                    queued_callback = anonymous_143 ,
                    started_callback = unsharp_started_callback ,
                    finished_callback = anonymous_145 ,
                    error_callback   = error_callback,
                    display_callback = display_callback ,
                )

    windowum.add_actions([
        ('gtk-apply',
        unsharp_callback) ,
        ('gtk-cancel',
        lambda : windowum.destroy())
    ])
    windowum.show_all()


def change_image_tool_cb( action, current ) :
    "Callback for tool-changed signal ImageView"    
    value = current.get_current_value()
    global view
    tool = Selector(view)
    if value == DRAGGER_TOOL :
        tool = Dragger(view)
 
    elif value == SELECTORDRAGGER_TOOL :
        tool = SelectorDragger(view)

    view.set_tool(tool)
    if value == SELECTOR_TOOL        or value == SELECTORDRAGGER_TOOL and  "selection"  in SETTING     :
        view.handler_block( view["selection_changed_signal"] )
        view.set_selection( SETTING["selection"] )
        view.handler_unblock( view["selection_changed_signal"] )

    SETTING["image_control_tool"] = value


def change_view_cb( action, current ) :
    "Callback to switch between tabbed and split views"    
    global vnotebook
    global view
    global canvas
    global a_canvas
    global vpaned
    global hpanei

    # SETTING["viewer_tools"] still has old value
    if SETTING["viewer_tools"] == TABBED_VIEW :
        vpaned.remove(vnotebook)
        vnotebook.remove(view)
        vnotebook.remove(canvas)
 
    elif SETTING["viewer_tools"] == SPLIT_VIEW_H :
        vpaned.remove(hpanei)
        hpanei.remove(view)
        hpanei.remove(canvas)
 
    else :    # $SPLIT_VIEW_V
        vpaned.remove(vpanei)
        vpanei.remove(view)
        vpanei.remove(canvas)
        vpanei.remove(a_canvas)

    # Update $SETTING{viewer_tools}
    SETTING["viewer_tools"] = current.get_current_value()
    pack_viewer_tools()


def crop_dialog(action) :
    "Display page selector and on apply crop accordingly"    
    if  (windowc is not None) :
        windowc.present()
        return

    windowc = Dialog(
        transient_for  = window,
        title            = _('Crop'),
        hide_on_delete = True,
    )

    # Frame for page range

    windowc.add_page_range()
    ( width, height ) = current_page.get_size()
    sb_selector_x = Gtk.SpinButton.new_with_range( 0, width,  1 )
    sb_selector_y = Gtk.SpinButton.new_with_range( 0, height, 1 )
    sb_selector_w = Gtk.SpinButton.new_with_range( 0, width,  1 )
    sb_selector_h = Gtk.SpinButton.new_with_range( 0, height, 1 )
    layout = [
    [
    _('x'),             sb_selector_x,             _('The x-position of the left hand edge of the crop.'),
        ],         [
    _('y'), sb_selector_y,             _('The y-position of the top edge of the crop.'),
        ],         [
    _('Width'),  sb_selector_w, _('The width of the crop.'), ],         [
    _('Height'), sb_selector_h, _('The height of the crop.'), ],
    ]

    # grid for layout
    grid = Gtk.Grid()
    vbox = windowc.get_content_area()
    vbox.pack_start( grid, True, True, 0 )
    for  row in      range(len(layout))    :
        col   = 0
        hbox  = Gtk.HBox()
        label = Gtk.Label( label=layout[row][col] )
        col+=1
        grid.attach( hbox, col, row, 1, 1 )
        hbox.pack_start( label, False, True, 0 )
        hbox = Gtk.HBox()
        hbox.pack_end( layout[row][col], True, True, 0 )
        grid.attach( hbox, col, row, 1, 1 )
        hbox = Gtk.HBox()
        col+=1
        grid.attach( hbox, col, row, 1, 1 )
        label = Gtk.Label( label=_('pixels') )
        hbox.pack_start( label, False, True, 0 )
        layout[row][1].set_tooltip_text( layout[row][col] )


    def anonymous_148():
        # Callbacks if the spinbuttons change
        SETTING["selection"]["x"] = sb_selector_x.get_value()
        sb_selector_w.set_range( 0, width - SETTING["selection"]["x"] )
        update_selector()


    sb_selector_x.connect(
        'value-changed' , anonymous_148 
    )
    def anonymous_149():
        SETTING["selection"]["y"] = sb_selector_y.get_value()
        sb_selector_h.set_range( 0, height - SETTING["selection"]["y"] )
        update_selector()


    sb_selector_y.connect(
        'value-changed' , anonymous_149 
    )
    def anonymous_150():
        SETTING["selection"]["width"] = sb_selector_w.get_value()
        sb_selector_x.set_range( 0, width - SETTING["selection"]["width"] )
        update_selector()


    sb_selector_w.connect(
        'value-changed' , anonymous_150 
    )
    def anonymous_151():
        SETTING["selection"]["height"] = sb_selector_h.get_value()
        sb_selector_y.set_range( 0,
                height - SETTING["selection"]["height"] )
        update_selector()


    sb_selector_h.connect(
        'value-changed' , anonymous_151 
    )
    if  "x"  in SETTING["selection"] :
        sb_selector_x.set_value( SETTING["selection"]["x"] )

    if  "y"  in SETTING["selection"] :
        sb_selector_y.set_value( SETTING["selection"]["y"] )

    if  "width"  in SETTING["selection"] :
        sb_selector_w.set_value( SETTING["selection"]["width"] )

    if  "height"  in SETTING["selection"] :
        sb_selector_h.set_value( SETTING["selection"]["height"] )

    def crop_callback():
        SETTING['Page range'] = windowc.page_range
        crop_selection(
                action,
                slist.get_page_index(
                    SETTING['Page range'], error_callback
                )
            )

    windowc.add_actions([
        ('gtk-apply',
        crop_callback) ,
        ('gtk-cancel',
        lambda : windowc.hide())
    ])
    windowc.show_all()


def update_selector() :
    global view
    sel = view.get_selection()
    view.handler_block( view["selection_changed_signal"] )
    if  (sel is not None) :
        view.set_selection( SETTING["selection"] )

    view.handler_unblock( view["selection_changed_signal"] )
    return


def crop_selection( action, pagelist ) :
    
    if not SETTING["selection"] :
        return

    # Update undo/redo buffers

    take_snapshot()
    if not pagelist or 0 not   in pagelist :
        pagelist = slist.get_selected_indices()

    if not pagelist :
        return
    for  i in     pagelist :
        ( signal, pid )=(None,None)
        def anonymous_154(*argv):
            return update_tpbar(*argv)


        def crop_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal = setup_tpbar( process, completed, total, pid )
            # if signal is not None:
            #     return True  


        def anonymous_156( new_page, pending ):
                
            if not pending :
                thbox.hide()
            if signal is not None :
                tcbutton.disconnect(signal)

            slist.save_session()


        pid = slist.crop(
            page            = slist.data[i][2].uuid,
            x               = SETTING["selection"]["x"],
            y               = SETTING["selection"]["y"],
            w               = SETTING["selection"]["width"],
            h               = SETTING["selection"]["height"],
            queued_callback = anonymous_154 ,
            started_callback = crop_started_callback ,
            finished_callback = anonymous_156 ,
            error_callback   = error_callback,
            display_callback = display_callback ,
        )


def split_dialog(action) :
    """Display page selector and on apply crop accordingly"""    

    # Until we have a separate tool for the divider, kill the whole
    #        sub { $windowsp->hide }
    #    if ( defined $windowsp ) {
    #        $windowsp->present;
    #        return;
    #    }

    windowsp = Dialog(
        transient_for  = window,
        title            = _('Split'),
        hide_on_delete = True,
    )

    # Frame for page range

    windowsp.add_page_range()
    hbox = Gtk.HBox()
    vbox = windowsp.get_content_area()
    vbox.pack_start( hbox, False, False, 0 )
    label = Gtk.Label( label=_('Direction') )
    hbox.pack_start( label, False, True, 0 )
    direction = [
    [
    'v', _('Vertically'),             _('Split the page vertically into left and right pages.')
        ],         [
    'h', _('Horizontally'),             _('Split the page horizontally into top and bottom pages.')
        ],
    ]
    combob = ComboBoxText(data=direction)
    ( width, height ) = current_page.get_size()
    sb_pos = Gtk.SpinButton.new_with_range( 0, width, 1 )
    def anonymous_158():
        if direction[ combob.get_active() ][0] == 'v' :
            sb_pos.set_range( 0, width )
 
        else :
            sb_pos.set_range( 0, height )

        update_view_position( direction[ combob.get_active() ][0],
                sb_pos.get_value(), width, height )


    combob.connect(
        'changed' , anonymous_158 
    )
    combob.set_active_index('v')
    hbox.pack_end( combob, False, True, 0 )

    # SpinButton for position

    hbox = Gtk.HBox()
    vbox.pack_start( hbox, False, True, 0 )
    label = Gtk.Label( label=_('Position') )
    hbox.pack_start( label, False, True, 0 )
    hbox.pack_end( sb_pos, False, True, 0 )

    def anonymous_159():
        """    # Callback if the spinbutton changes
"""
        update_view_position( direction[ combob.get_active() ][0],
                sb_pos.get_value(), width, height )


    sb_pos.connect(
        'value-changed' , anonymous_159 
    )
    sb_pos.set_value( width / 2 )

    def anonymous_160( widget, sel ):
        """    # Callback if the selection changes
"""            
        if  (sel is not None) :
            if direction[ combob.get_active() ][0] == 'v' :
                sb_pos.set_value( sel["x"] + sel["width"] )
 
            else :
                sb_pos.set_value( sel["y"] + sel["height"] )




    global view
    view.position_changed_signal = view.connect(        'selection-changed' , anonymous_160     )
    def split_apply_callback():

        # Update undo/redo buffers
        take_snapshot()
        SETTING['split-direction'] =               direction[ combob.get_active() ][0]
        SETTING['split-position'] = sb_pos.get_value()
        SETTING['Page range'] = windowsp.page_range
        pagelist =               slist.get_page_index( SETTING['Page range'],
                error_callback )
        if not pagelist :
            return
        page = 0
        for  i in         pagelist :
            page+=1
            ( signal, pid )=(None,None)
            def anonymous_162(*argv):
                return update_tpbar(*argv)


            def split_started_callback( response ):
                #thread, process, completed, total
                pass
                # signal = setup_tpbar( process, completed, total,pid )
                if signal is not None:
                    return True  


            def anonymous_164( new_page, pending ):
                        
                if not pending :
                    thbox.hide()
                if signal is not None :
                    tcbutton.disconnect(signal)

                slist.save_session()


            pid = slist.split_page(
                    direction       = SETTING['split-direction'],
                    position        = SETTING['split-position'],
                    page            = slist.data[i][2].uuid,
                    queued_callback = anonymous_162 ,
                    started_callback = split_started_callback ,
                    finished_callback = anonymous_164 ,
                    error_callback   = error_callback,
                    display_callback = display_callback ,
                )


    def split_cancel_callback():
        global view
        view.disconnect(
                view["position_changed_signal"] )
        windowsp.destroy()


    windowsp.add_actions([
        ('gtk-apply',
        split_apply_callback) ,
        ('gtk-cancel',

        # Until we have a separate tool for the divider, kill the whole
        #        sub { $windowsp->hide }
        split_cancel_callback) 
    ])
    windowsp.show_all()


def update_view_position( direction, position, width, height ) :
    
    selection = { "x" : 0, "y" : 0 }
    if direction == 'v' :
        selection["width"]  = position
        selection["height"] = height
 
    else :
        selection["width"]  = width
        selection["height"] = position

    global view
    view.set_selection( selection )


def user_defined_dialog(_action):
    if windowudt is not None:
        windowudt.present()
        return

    windowudt = Dialog(
        transient_for = window,
        title            = _('User-defined tools'),
        hide_on_delete = True,
    )

    # Frame for page range

    windowudt.add_page_range()
    hbox = Gtk.HBox()
    vbox = windowudt.get_content_area()
    vbox.pack_start( hbox, False, False, 0 )
    label = Gtk.Label( label=_('Selected tool') )
    hbox.pack_start( label, False, True, 0 )
    comboboxudt = add_udt_combobox(hbox)
    def udt_apply_callback():
        SETTING['Page range'] = windowudt.page_range
        pagelist = indices2pages(
                slist.get_page_index(
                    SETTING['Page range'], error_callback
                )
            )
        if not pagelist :
            return
        SETTING["current_udt"] = comboboxudt.get_active_text()
        user_defined_tool( pagelist, SETTING["current_udt"] )
        windowudt.hide()


    windowudt.add_actions([
        ('gtk-ok',
        udt_apply_callback) ,
        ('gtk-cancel',
            lambda : windowudt.hide())
    ])
    windowudt.show_all()


def user_defined_tool( pages, cmd ) :
    "Run a user-defined tool on the selected images"    

    # Update undo/redo buffers
    take_snapshot()
    for  page in      pages  :
        ( signal, pid )=(None,None)
        def anonymous_169(*argv):
            return update_tpbar(*argv)


        def user_defined_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal = setup_tpbar( process, completed, total, pid )
            # if signal is not None:
            #     return True  


        def anonymous_171( new_page, pending ):
                
            if not pending :
                thbox.hide()
            if signal is not None :
                tcbutton.disconnect(signal)

            slist.save_session()


        pid = slist.user_defined(
            page            = page,
            command         = cmd,
            queued_callback = anonymous_169 ,
            started_callback = user_defined_started_callback ,
            finished_callback = anonymous_171 ,
            error_callback   = error_callback,
            display_callback = display_callback ,
        )


def unpaper_page( pages, options, callback ) :
    "queue $page to be processed by unpaper"    
    if   (options is None) :
        options = EMPTY

    # Update undo/redo buffers

    take_snapshot()
    for  pageobject in      pages  :
        ( signal, pid )=(None,None)
        def anonymous_173(*argv):
            return update_tpbar(*argv)


        def unpaper_started_callback( response ):
            #thread, process, completed, total
            pass
            # signal = setup_tpbar( process, completed, total, pid )
            # if signal is not None:
            #     return True  


        def anonymous_175( new_page, pending ):
                
            if not pending :
                thbox.hide()
            if signal is not None :
                tcbutton.disconnect(signal)

            slist.save_session()


        def anonymous_176(new_page):
                
            display_image(new_page)
            if callback :
                callback(new_page)


        pid = slist.unpaper(
            page            = pageobject,
            options         = options,
            queued_callback = anonymous_173 ,
            started_callback = unpaper_started_callback ,
            finished_callback = anonymous_175 ,
            error_callback   = error_callback,
            display_callback = anonymous_176 ,
        )


def unpaper(_action):
    "Run unpaper to clean up scan."
    if  windowu is not None :
        windowu.present()
        return

    windowu = Dialog(
        transient_for  = window,
        title            = _('unpaper'),
        hide_on_delete = True,
    )

    # Frame for page range
    windowu.add_page_range()

    # add unpaper options
    vbox = windowu.get_content_area()
    unpaper.add_options(vbox)
    def unpaper_apply_callback():

        # Update $SETTING
        SETTING['unpaper options'] = unpaper.get_options()
        SETTING['Page range']      = windowu.page_range

        # run unpaper
        pagelist = indices2pages(
                slist.get_page_index(
                    SETTING['Page range'], error_callback
                )
            )
        if not pagelist :
            return
        unpaper_page(
                pagelist,
                {
                    "command"   : unpaper.get_cmdline(),
                    "direction" : unpaper.get_option('direction')
                }
            )
        windowu.hide()


    windowu.add_actions([
        ('gtk-ok',
        unpaper_apply_callback) ,
        ('gtk-cancel',
            lambda : windowu.hide())
    ])
    windowu.show_all()


def add_tess_languages(vbox) :
    "Add hbox for tesseract languages"    
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, False, False, 0 )
    label = Gtk.Label( label=_('Language to recognise') )
    hbox.pack_start( label, False, True, 0 )

    # Tesseract language files
    tesslang=[]
    tesscodes=get_tesseract_codes()
    langs=languages(tesscodes)
    for lang in      sorted(tesscodes)     :
        tesslang.append([lang, langs[lang]  ])  

    combobox = ComboBoxText(data=tesslang)
    combobox.set_active_index( SETTING['ocr language'] )
    if not combobox.get_active_index():
        combobox.set_active( 0 )
    hbox.pack_end( combobox, False, True, 0 )
    return hbox, combobox, tesslang


def ocr_dialog(_action) :
    "Run OCR on current page and display result"
    if  windowo is not None :
        windowo.present()
        return

    windowo = Dialog(
        transient_for  = window,
        title            = _('OCR'),
        hide_on_delete = True,
    )

    # Frame for page range
    windowo.add_page_range()

    # OCR engine selection
    hboxe = Gtk.HBox()
    vbox  = windowo.get_content_area()
    vbox.pack_start( hboxe, False, True, 0 )
    label = Gtk.Label( label=_('OCR Engine') )
    hboxe.pack_start( label, False, True, 0 )
    combobe = ComboBoxText(data=ocr_engine)
    combobe.set_active_index( SETTING['ocr engine'] )
    hboxe.pack_end( combobe, False, True, 0 )
    comboboxtl, hboxtl, tesslang, comboboxcl, hboxcl, cflang =None,None,[],None,None,[]
    if dependencies["tesseract"] :
        hboxtl, comboboxtl, tesslang  = add_tess_languages(vbox)
        def anonymous_179():
            if ocr_engine[ combobe.get_active() ][0] == 'tesseract' :
                hboxtl.show_all()
 
            else :
                hboxtl.hide()

        combobe.connect( 'changed' , anonymous_179  )

    # Checkbox & SpinButton for threshold
    hboxt = Gtk.HBox()
    vbox.pack_start( hboxt, False, True, 0 )
    cbto = Gtk.CheckButton( label=_('Threshold before OCR') )
    cbto.set_tooltip_text(
        _(
                'Threshold the image before performing OCR. '
              + 'This only affects the image passed to the OCR engine, and not the image stored.'
        )
    )
    if  'threshold-before-ocr'  in SETTING :
        cbto.set_active( SETTING['threshold-before-ocr'] )

    hboxt.pack_start( cbto, False, True, 0 )
    labelp = Gtk.Label(label=PERCENT)
    hboxt.pack_end( labelp, False, True, 0 )
    spinbutton = Gtk.SpinButton.new_with_range( 0, _100_PERCENT, 1 )
    spinbutton.set_value( SETTING['threshold tool'] )
    spinbutton.set_sensitive( cbto.get_active() )
    hboxt.pack_end( spinbutton, False, True, 0 )
    def anonymous_181():
        spinbutton.set_sensitive( cbto.get_active() )


    cbto.connect(
        'toggled' , anonymous_181 
    )
    def ocr_apply_callback():
        tesslang =None
        if  comboboxtl is not None :
            tesslang = tesslang[ comboboxtl.get_active() ][0]

        run_ocr( ocr_engine[ combobe.get_active() ][0],
                tesslang, cbto.get_active(), spinbutton.get_value() )

    windowo.add_actions([
        ('gtk-ok',
        ocr_apply_callback) ,
        ('gtk-cancel',
            lambda : windowo.hide())
    ])
    windowo.show_all()
    if  hboxtl is not None and ocr_engine[ combobe.get_active() ][0] != 'tesseract' :
        hboxtl.hide()


def anonymous_184(*argv):
    return update_tpbar(*argv)


def ocr_started_callback( response ):
    #thread, process, completed, total
    pass
    # signal =               setup_tpbar( process, completed, total, pid )
    # if signal is not None:
    #     return True  


def anonymous_186( new_page, pending ):
            
    if not pending :
        thbox.hide()
    if signal is not None :
        tcbutton.disconnect(signal)

    slist.save_session()


def anonymous_187(new_page):
            
    page = slist.get_selected_indices()
    if page and new_page == slist.data[ page[0] ][2] :
        create_txt_canvas(new_page)


def run_ocr( engine, tesslang, threshold_flag, threshold ) :
    
    if engine == 'tesseract' :
        SETTING['ocr language'] = tesslang

    signal, pid =None,None
    options = {
        "queued_callback" : anonymous_184 ,
        "started_callback" : ocr_started_callback ,
        "finished_callback" : anonymous_186 ,
        "error_callback"   : error_callback,
        "display_callback" : anonymous_187 ,
        "engine"   : engine,
        "language" : SETTING['ocr language'],
    }
    SETTING['ocr engine']           = engine
    SETTING['threshold-before-ocr'] = threshold_flag
    if threshold_flag :
        SETTING['threshold tool'] = threshold
        options["threshold"]        = threshold

    # fill pagelist with filenames
    # depending on which radiobutton is active
    SETTING['Page range'] = windowo.page_range
    pagelist = indices2pages(
        slist.get_page_index( SETTING['Page range'], error_callback ) )
    if not pagelist :
        return
    slist.ocr_pages( pagelist, options )
    windowo.hide()


def quit() :
    "Remove temporary files, note window state, save settings and quit."
    if not scans_saved(
            _("Some pages have not been saved.\nDo you really want to quit?")
        )     :
        return

    # Make sure that we are back in the start directory,
    # otherwise we can't delete the temp dir.
    os.chdir( SETTING["cwd"])

    # Remove temporary files
    for file in glob.glob(session.name+"/*"):
        os.remove(file) 
    os.rmdir(session.name) 
        # Write window state to settings
    global window
    global hpaned
    SETTING["window_width"], SETTING["window_height"]  = window.get_size()
    SETTING["window_x"],     SETTING["window_y"]       = window.get_position()
    SETTING['thumb panel'] = hpaned.get_position()
    global windows
    if windows :
        SETTING["scan_window_width"], SETTING["scan_window_height"]  =           windows.get_size()
        logger.info('Killing Sane thread(s)')
        windows.thread.quit()

    # Write config file
    config.write_config( rc, SETTING )
    logger.info('Killing document thread(s)')
    slist.thread.quit()
    logger.debug('Quitting')

    # compress log file if we have xz
    if args.log and dependencies["xz"] :
        exec_command(        [        'xz', '-f', args.log ] )

    return True


def view_html() :
    "Perhaps we should use gtk and mallard for this in the future"
    # At the moment, we have no translations,
    # but when we do, replace C with $locale

    uri = f"/usr/share/help/C/{prog_name}/documentation.html"
    if not pathlib.Path(uri).exists()  :
        uri = 'http://gscan2pdf.sf.net'
 
    else :
        uri = GLib.filename_to_uri( uri, None )    # undef => no hostname

    logger.info(f"Opening {uri} via default launcher")
    context = Gio.AppLaunchContext()
    Gio.AppInfo.launch_default_for_uri( uri, context )
    return


def take_snapshot() :
    "Update undo/redo buffers before doing something"
    global undo_buffer
    logger.debug(f"take_snapshot: {undo_buffer}")
    old_undo_files = list(map(lambda x: x[2].uuid ,undo_buffer)  )

    # Deep copy the tied data. Otherwise, very bad things happen.
    undo_buffer    = slist.data.copy()
    undo_selection = slist.get_selected_indices()
    logger.debug(  "Undo buffer %s", undo_buffer  )

    # Clean up files that fall off the undo buffer
    undo_files={}
    for i in     undo_buffer :
        undo_files[i[2].uuid] = True

    delete_files=[]
    for  file in     old_undo_files :
        if not undo_files[file] :
            delete_files.append(file)  

    if delete_files :
        logger.info("Cleaning up delete_files")
        os.remove(delete_files) 

    # Unghost Undo/redo
    uimanager.get_widget('/MenuBar/Edit/Undo').set_sensitive(True)
    uimanager.get_widget('/ToolBar/Undo').set_sensitive(True)

    # Check free space in session directory
    df = shutil.disk_usage(session.name)
    if  df :
        df = df.free/1024/1024
        logger.debug(
f"Free space in {session.name} (Mb): {df} (warning at {SETTING['available-tmp-warning']})"
        )
        global window
        if df < SETTING['available-tmp-warning'] :
            text = _('%dMb free in %s.') % (df,session.name)   
            show_message_dialog(
                parent  = window,
                message_type    = 'warning',
                buttons = Gtk.ButtonsType.CLOSE,
                text    = text
            )


def undo() :
    "Put things back to last snapshot after updating redo buffer"
    logger.info('Undoing')

    # Deep copy the tied data. Otherwise, very bad things happen.
    redo_buffer    = map(lambda x:  [
    x ] ,len( slist.data ))  
    redo_selection = slist.get_selected_indices()
    logger.debug('redo_selection, undo_selection:')
    logger.debug( Dumper( redo_selection, undo_selection ) )
    logger.debug('redo_buffer, undo_buffer:')
    logger.debug( Dumper( redo_buffer, undo_buffer ) )

    # Block slist signals whilst updating
    slist.get_model().handler_block( slist.row_changed_signal )
    slist.get_selection().handler_block(slist.selection_changed_signal )
    slist.data = undo_buffer

    # Unblock slist signals now finished
    slist.get_selection().handler_unblock(slist.selection_changed_signal )
    slist.get_model().handler_unblock( slist.row_changed_signal )

    # Reselect the pages to display the detail view
    slist.select(undo_selection)

    # Update menus/buttons
    update_uimanager()
    global uimanager
    uimanager.get_widget('/MenuBar/Edit/Undo').set_sensitive(False)
    uimanager.get_widget('/MenuBar/Edit/Redo').set_sensitive(True)
    uimanager.get_widget('/ToolBar/Undo').set_sensitive(False)
    uimanager.get_widget('/ToolBar/Redo').set_sensitive(True)


def unundo() :
    "Put things back to last snapshot after updating redo buffer"
    logger.info('Redoing')

    # Deep copy the tied data. Otherwise, very bad things happen.
    undo_buffer    = map(lambda x:  [
    x ] ,len( slist.data ))  
    undo_selection = slist.get_selected_indices()
    logger.debug('redo_selection, undo_selection:')
    logger.debug( Dumper( redo_selection, undo_selection ) )
    logger.debug('redo_buffer, undo_buffer:')
    logger.debug( Dumper( redo_buffer, undo_buffer ) )

    # Block slist signals whilst updating
    slist.get_model().handler_block( slist.row_changed_signal )
    slist.data = redo_buffer

    # Unblock slist signals now finished
    slist.get_model().handler_unblock( slist.row_changed_signal )

    # Reselect the pages to display the detail view
    slist.select(redo_selection)

    # Update menus/buttons
    update_uimanager()
    global uimanager
    uimanager.get_widget('/MenuBar/Edit/Undo').set_sensitive(True)
    uimanager.get_widget('/MenuBar/Edit/Redo').set_sensitive(False)
    uimanager.get_widget('/ToolBar/Undo').set_sensitive(True)
    uimanager.get_widget('/ToolBar/Redo').set_sensitive(False)


def init_icons(icons) :
    "Initialise iconfactory"    
    iconfactory = Gtk.IconFactory()
    for icon in     icons :
        register_icon(iconfactory, *icon )


def register_icon( iconfactory, stock_id, path ) :
    "Add icons"    
    # try :
    icon = GdkPixbuf.Pixbuf.new_from_file(path) 
    print(f"icon {icon}")
    if  icon is None :
        logger.warning("Unable to load icon `%s'", path)
    else:
        iconfactory.add( stock_id, Gtk.IconSet.new_from_pixbuf(icon) )
    # except as err:
    #     logger.warning(f"Unable to load icon `%s': %s", path, err)


def mark_pages(pages) :
    "marked page list as saved"    
    slist.get_model().handler_block( slist.row_changed_signal )
    for p in      pages  :
        i = slist.find_page_by_uuid(p)
        if  i is not None :
            slist.data[i][2].saved = True

    slist.get_model().handler_unblock( slist.row_changed_signal )


def preferences(arg) :
    "Preferences dialog"
    global windows
    global windowr
    if  windowr is not None :
        windowr.present()
        return

    global window
    windowr = Dialog(
        transient_for  = window,
        title            = _('Preferences'),
        hide_on_delete = True,
    )
    vbox = windowr.get_content_area()

    # Notebook for scan and general options
    notebook = Gtk.Notebook()
    vbox.pack_start( notebook, True, True, 0 )
    (
        vbox1,               frontends,
        cbo,
        blacklist,           cbcsh,            cb_batch_flatbed,
        cb_cancel_btw_pages, cb_adf_all_pages, cb_cache_device_list,
        cb_ignore_duplex
      )       = _preferences_scan_options( windowr.get_border_width()) 
    notebook.append_page( vbox1, Gtk.Label( label=_('Scan options') ) )
    (
        vbox2,       fileentry,   cbw,         cbtz,
        cbtm,        cbts,        cbtp,        tmpentry,
        spinbuttonw, spinbuttonb, spinbuttond, ocr_function,
        comboo,      cbv,         cbb,         vboxt
      )       = _preferences_general_options(windowr.get_border_width() )
    notebook.append_page( vbox2, Gtk.Label( label=_('General options') ) )
    def preferences_apply_callback():
        windowr.hide()
        if SETTING["frontend"] != combob.get_active_index() :
            SETTING["frontend"] = combob.get_active_index()
            logger.info(f"Switched frontend to {SETTING['frontend']}")
            if windows :
                Gscan2pdf.Frontend.Image_Sane.close_device()
                windows.hide()
                windows=None
 
        else :
            SETTING['visible-scan-options'] = ()
            SETTING['scan-reload-triggers'] = ()
            for i in              option_visibility_list.data  :
                SETTING['visible-scan-options'][ i[0] ] = i[2]
                if i[3] :
                    SETTING['scan-reload-triggers'].append(i[0])  

        SETTING['auto-open-scan-dialog'] = cbo.get_active()
        try :
            text = blacklist.get_text()
            re.search(text,'dummy_device',re.MULTILINE|re.DOTALL|re.VERBOSE)
 
        except :
            msg =                   _(
                    "Invalid regex. Try without special characters such as '*'"
                  )
            logger.warning(msg)
            show_message_dialog(
                    parent           = windowr,
                    message_type             = 'error',
                    buttons          = Gtk.ButtonsType.CLOSE,
                    text             = msg,
                    store_response = True
                )
            blacklist.set_text( SETTING['device blacklist'] )

        SETTING['device blacklist'] = blacklist.get_text()
        SETTING['cycle sane handle']    = cbcsh.get_active()
        SETTING['allow-batch-flatbed']  = cb_batch_flatbed.get_active()
        SETTING['cancel-between-pages'] = cb_cancel_btw_pages.get_active()
        SETTING['adf-defaults-scan-all-pages'] =               cb_adf_all_pages.get_active()
        SETTING['cache-device-list'] = cb_cache_device_list.get_active()
        SETTING['ignore-duplex-capabilities'] =               cb_ignore_duplex.get_active()
        SETTING['default filename'] = fileentry.get_text()
        SETTING['restore window']   = cbw.get_active()
        SETTING["use_timezone"]       = cbtz.get_active()
        SETTING["use_time"]           = cbtm.get_active()
        SETTING["set_timestamp"]      = cbts.get_active()
        SETTING["to_png"]             = cbtp.get_active()
        SETTING['convert whitespace to underscores'] = cbb.get_active()
        if windows :
            windows.cycle_sane_handle=SETTING['cycle sane handle']
            windows.cancel_between_pages=SETTING['cancel-between-pages']
            windows.allow_batch_flatbed=SETTING['allow-batch-flatbed']
            windows.ignore_duplex_capabilities=SETTING['ignore-duplex-capabilities']

        if  windowi is not None :
            windowi.include_time=SETTING["use_time"]

        SETTING['available-tmp-warning'] = spinbuttonw.get_value()
        SETTING['Blank threshold']       = spinbuttonb.get_value()
        SETTING['Dark threshold']        = spinbuttond.get_value()
        SETTING['OCR output']            = comboo.get_active_index()

            # Store viewer preferences
        SETTING['view files toggle'] = cbv.get_active()
        update_list_user_defined_tools( vboxt,
                [
        comboboxudt, windows.comboboxudt ] )
        tmpdirs = File.Spec.splitdir(session)
        tmpdirs.pop()     # Remove the top level
        tmp = File.Spec.catdir(tmpdirs)

            # Expand tildes in the filename
        newdir = get_tmp_dir(
                pathlib.Path( tmpentry.get_text() ).expanduser(),
                r'gscan2pdf-\w\w\w\w' )
        if newdir != tmp :
            SETTING["TMPDIR"] = newdir
            global window
            response = ask_question(
                    parent  = window,
                    type    = 'question',
                    buttons = Gtk.ButtonsType.OK_CANCEL,
                    text    = _(
'Changes will only take effect after restarting gscan2pdf.'
                      )
                      + SPACE
                      + _('Restart gscan2pdf now?')
                )
            if response == Gtk.ResponseType.OK :
                restart()

    windowr.add_actions([
        ('gtk-ok',
        preferences_apply_callback) ,
        ('gtk-cancel',
            lambda : windowr.hide())
    ])
    windowr.show_all()


def _preferences_scan_options(border_width) :
    global windows
    
    vbox = Gtk.VBox()
    vbox.set_border_width(border_width)
    cbo =       Gtk.CheckButton( label=_('Open scanner at program start') )
    cbo.set_tooltip_text(
        _(
'Automatically open the scan dialog in the background at program start. '
              + 'This saves time clicking the scan button and waiting for the program to find the list of scanners'
        )
    )
    if  'auto-open-scan-dialog'  in SETTING :
        cbo.set_active( SETTING['auto-open-scan-dialog'] )

    vbox.pack_start( cbo, True, True, 0 )

    # Frontends
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, False, False, 0 )
    label = Gtk.Label( label=_('Frontend') )
    hbox.pack_start( label, False, False, 0 )
    frontends = [
    [
    'libimage-sane-perl',             _('libimage-sane-perl'),             _('Scan using the Perl bindings for SANE.')
        ],     
    ]

    # Device blacklist
    hboxb = Gtk.HBox()
    vbox.pack_start( hboxb, False, False, 0 )
    label = Gtk.Label( label=_('Device blacklist') )
    hboxb.pack_start( label, False, False, 0 )
    blacklist = Gtk.Entry()
    hboxb.add(blacklist)
    hboxb.set_tooltip_text( _('Device blacklist (regular expression)') )
    if  'device blacklist'  in SETTING :
        blacklist.set_text( SETTING['device blacklist'] )

    # Cycle SANE handle after scan
    cbcsh =       Gtk.CheckButton( label=_('Cycle SANE handle after scan') )
    cbcsh.set_tooltip_text(
        _('Some ADFs do not feed out the last page if this is not enabled') )
    if  'cycle sane handle'  in SETTING :
        cbcsh.set_active( SETTING['cycle sane handle'] )

    vbox.pack_start( cbcsh, False, False, 0 )

    # Allow batch scanning from flatbed
    cb_batch_flatbed =       Gtk.CheckButton(
        label=_('Allow batch scanning from flatbed') )
    cb_batch_flatbed.set_tooltip_text(
        _(
'If not set, switching to a flatbed scanner will force # pages to 1 and single-sided mode.'
        )
    )
    cb_batch_flatbed.set_active( SETTING['allow-batch-flatbed'] )
    vbox.pack_start( cb_batch_flatbed, False, False, 0 )

    # Ignore duplex capabilities
    cb_ignore_duplex =       Gtk.CheckButton(
        label=_('Ignore duplex capabilities of scanner') )
    cb_ignore_duplex.set_tooltip_text(
        _(
'If set, any duplex capabilities are ignored, and facing/reverse widgets are displayed to allow manual interleaving of pages.'
        )
    )
    cb_ignore_duplex.set_active( SETTING['ignore-duplex-capabilities'] )
    vbox.pack_start( cb_ignore_duplex, False, False, 0 )

    # Force new scan job between pages
    cb_cancel_btw_pages =       Gtk.CheckButton(
        label=_('Force new scan job between pages') )
    cb_cancel_btw_pages.set_tooltip_text(
        _(
'Otherwise, some Brother scanners report out of documents, despite scanning from flatbed.'
        )
    )
    cb_cancel_btw_pages.set_active( SETTING['cancel-between-pages'] )
    vbox.pack_start( cb_cancel_btw_pages, False, False, 0 )
    cb_cancel_btw_pages.set_sensitive( SETTING['allow-batch-flatbed'] )
    def anonymous_194():
        cb_cancel_btw_pages.set_sensitive(
                cb_batch_flatbed.get_active() )

    cb_batch_flatbed.connect(
        'toggled' , anonymous_194 
    )

    # Select num-pages = all on selecting ADF
    cb_adf_all_pages =       Gtk.CheckButton(
        label=_('Select # pages = all on selecting ADF') )
    cb_adf_all_pages.set_tooltip_text(
        _(
'If this option is enabled, when switching to source=ADF, # pages = all is selected'
        )
    )
    cb_adf_all_pages.set_active( SETTING['adf-defaults-scan-all-pages'] )
    vbox.pack_start( cb_adf_all_pages, False, False, 0 )

    # Cache device list
    cb_cache_device_list =       Gtk.CheckButton( label=_('Cache device list') )
    cb_cache_device_list.set_tooltip_text(
        _(
'If this option is enabled, opening the scanner is quicker, as gscan2pdf does not first search for available devices.'
          )
          + _(
'This is only effective if the device names do not change between sessions.'
          )
    )
    cb_cache_device_list.set_active( SETTING['cache-device-list'] )
    vbox.pack_start( cb_cache_device_list, False, False, 0 )

    return vbox, frontends, cbo, blacklist,       cbcsh, cb_batch_flatbed, cb_cancel_btw_pages, cb_adf_all_pages,       cb_cache_device_list, cb_ignore_duplex


def _preferences_general_options(border_width) :
    
    vbox = Gtk.VBox()
    vbox.set_border_width(border_width)

    # Restore window setting
    cbw = Gtk.CheckButton(
        label=_('Restore window settings on startup') )
    cbw.set_active( SETTING['restore window'] )
    vbox.pack_start( cbw, True, True, 0 )

    # View saved files
    cbv = Gtk.CheckButton( label=_('View files on saving') )
    cbv.set_active( SETTING['view files toggle'] )
    vbox.pack_start( cbv, True, True, 0 )

    # Default filename
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('Default PDF & DjVu filename') )
    hbox.pack_start( label, False, False, 0 )
    fileentry = Gtk.Entry()
    fileentry.set_tooltip_text(
        _("""strftime codes, e.g.:
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
""")
    )
    hbox.add(fileentry)
    fileentry.set_text( SETTING['default filename'] )

    # Replace whitespace in filenames with underscores
    cbb = Gtk.CheckButton.new_with_label(
        _('Replace whitespace in filenames with underscores') )
    cbb.set_active( SETTING['convert whitespace to underscores'] )
    vbox.pack_start( cbb, True, True, 0 )

    # Timezone
    cbtz =       Gtk.CheckButton.new_with_label( _('Use timezone from locale') )
    cbtz.set_active( SETTING["use_timezone"] )
    vbox.pack_start( cbtz, True, True, 0 )

    # Time
    cbtm =       Gtk.CheckButton.new_with_label( _('Specify time as well as date') )
    cbtm.set_active( SETTING["use_time"] )
    vbox.pack_start( cbtm, True, True, 0 )

    # Set file timestamp with metadata
    cbts = Gtk.CheckButton.new_with_label(
        _('Set access and modification times to metadata date') )
    cbts.set_active( SETTING["set_timestamp"] )
    vbox.pack_start( cbts, True, True, 0 )

    # Convert scans from PNM to PNG
    cbtp = Gtk.CheckButton.new_with_label(
        _('Convert scanned images to PNG before further processing') )
    cbtp.set_active( SETTING["to_png"] )
    vbox.pack_start( cbtp, True, True, 0 )

    # Temporary directory settings
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('Temporary directory') )
    hbox.pack_start( label, False, False, 0 )
    tmpentry = Gtk.Entry()
    hbox.add(tmpentry)
    tmpentry.set_text( os.path.dirname(session.name) )
    button = Gtk.Button( label=_('Browse') )
    global windowr
    def anonymous_200():
        file_chooser = Gtk.FileChooserDialog(
                title=_('Select temporary directory'),
                parent=windowr, 
                action=Gtk.FileChooserAction.SELECT_FOLDER,
            )
        file_chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK)
        file_chooser.set_current_folder( tmpentry.get_text() )
        if file_chooser.run() == Gtk.ResponseType.OK:
            tmpentry.set_text(
                    get_tmp_dir(
                        file_chooser.get_filename(),
                        r'gscan2pdf-\w\w\w\w'
                    )
                )

        file_chooser.destroy()


    button.connect(
        'clicked' , anonymous_200 
    )
    hbox.pack_end( button, True, True, 0 )

    # Available space in temporary directory
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('Warn if available space less than (Mb)') )
    hbox.pack_start( label, False, False, 0 )
    spinbuttonw = Gtk.SpinButton.new_with_range( 0, _100_000MB, 1 )
    spinbuttonw.set_value( SETTING['available-tmp-warning'] )
    spinbuttonw.set_tooltip_text(
        _(
'Warn if the available space in the temporary directory is less than this value'
        )
    )
    hbox.add(spinbuttonw)

    # Blank page standard deviation threshold
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('Blank threshold') )
    hbox.pack_start( label, False, False, 0 )
    spinbuttonb =       Gtk.SpinButton.new_with_range( 0, 1, UNIT_SLIDER_STEP )
    spinbuttonb.set_value( SETTING['Blank threshold'] )
    spinbuttonb.set_tooltip_text(
        _('Threshold used for selecting blank pages') )
    hbox.add(spinbuttonb)

    # Dark page mean threshold
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('Dark threshold') )
    hbox.pack_start( label, False, False, 0 )
    spinbuttond =       Gtk.SpinButton.new_with_range( 0, 1, UNIT_SLIDER_STEP )
    spinbuttond.set_value( SETTING['Dark threshold'] )
    spinbuttond.set_tooltip_text(
        _('Threshold used for selecting dark pages') )
    hbox.add(spinbuttond)

    # OCR output
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=_('OCR output') )
    hbox.pack_start( label, False, False, 0 )
    ocr_function = [
    [
    'replace',             _('Replace'),             _(
'Replace the contents of the text buffer with that from the OCR output.'
            )
        ],         [
    'prepend', _('Prepend'),             _('Prepend the OCR output to the text buffer.')
        ],         [
    'append', _('Append'),             _('Append the OCR output to the text buffer.')
        ],
    ]
    comboo = ComboBoxText(data=ocr_function)
    comboo.set_active_index( SETTING['OCR output'] )
    hbox.pack_end( comboo, True, True, 0 )

    # Manage user-defined tools
    frame = Gtk.Frame( label=_('Manage user-defined tools') )
    vbox.pack_start( frame, True, True, 0 )
    vboxt = Gtk.VBox()
    vboxt.set_border_width(border_width)
    frame.add(vboxt)
    for  tool in      SETTING["user_defined_tools"]  :
        add_user_defined_tool_entry( vboxt, [], tool )

    abutton = Gtk.Button()
    abutton.set_image(
        Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
    vboxt.pack_start( abutton, True, True, 0 )
    def anonymous_201():
        add_user_defined_tool_entry(
                vboxt,
                [
        comboboxudt, windows.comboboxudt ],
                'my-tool %i %o'
            )
        vboxt.reorder_child( abutton, EMPTY_LIST )
        update_list_user_defined_tools( vboxt,
                [
        comboboxudt, windows.comboboxudt ] )


    abutton.connect(
        'clicked' , anonymous_201 
    )
    return vbox, fileentry, cbw, cbtz, cbtm, cbts, cbtp, tmpentry,       spinbuttonw,       spinbuttonb, spinbuttond, ocr_function, comboo, cbv, cbb, vboxt


def _cb_array_append( combobox_array, text ) :
    
    for  combobox in      combobox_array  :
        if  (combobox is not None) :
            combobox.append_text(text)


def update_list_user_defined_tools( vbox, combobox_array ) :
    """Update list of user-defined tools"""    
    (list)=([])
    for  combobox in      combobox_array  :
        if  (combobox is not None) :
            while combobox.get_num_rows() >0  :
                combobox.remove(0)

    for  hbox in      vbox.get_children()  :
        if isinstance(hbox,Gtk.HBox) :
            for  widget in              hbox.get_children()  :
                if isinstance(widget,Gtk.Entry) :
                    text = widget.get_text()
                    list.append(text)  
                    _cb_array_append( combobox_array, text )

    SETTING["user_defined_tools"] = list
    update_post_save_hooks()
    for  combobox in      combobox_array  :
        if  (combobox is not None) :
            combobox.set_active_by_text( SETTING["current_udt"] )


def add_user_defined_tool_entry( vbox, combobox_array, tool ) :
    "Add user-defined tool entry"    
    _cb_array_append( combobox_array, tool )
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    entry = Gtk.Entry()
    entry.set_text(tool)
    entry.set_tooltip_text(
        _(
"""Use %i and %o for the input and output filenames respectively, or a single %i if the image is to be modified in-place.

The other variable available is:

%r resolution"""
        )
    )
    hbox.pack_start( entry, True, True, 0 )
    button = Gtk.Button(label=_("_Delete"))
    def anonymous_202():
        hbox.destroy()
        update_list_user_defined_tools( vbox, combobox_array )


    button.connect(
        'clicked' , anonymous_202 
    )
    hbox.pack_end( button, False, False, 0 )
    hbox.show_all()
    return


def update_post_save_hooks() :
    if  windowi is not None :
        if  hasattr(windowi,"comboboxpsh"):

            # empty combobox
            for i in              range(1,windowi.comboboxpsh.get_num_rows()+1)    :
                windowi.comboboxpsh.remove(0)

        else :
            # create it
            windowi.comboboxpsh = ComboBoxText()

        # fill it again
        for  tool in          SETTING["user_defined_tools"]  :
            if   not re.search(r"%o",tool,re.MULTILINE|re.DOTALL|re.VERBOSE) :
                windowi.comboboxpsh.append_text(tool)


        windowi.comboboxpsh.set_active_by_text( SETTING["current_psh"] )


def properties() :
    if  windowp is not None :
        windowp.present()
        return

    global window
    windowp = Dialog(
        transient_for  = window,
        title            = _('Properties'),
        hide_on_delete = True,
    )
    vbox = windowp.get_content_area()
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=d_sane("X Resolution") )
    hbox.pack_start( label, False, False, 0 )
    xspinbutton = Gtk.SpinButton.new_with_range( 0, MAX_DPI, 1 )
    xspinbutton.set_digits(1)
    hbox.pack_start( xspinbutton, True, True, 0 )
    label = Gtk.Label( label=_('dpi') )
    hbox.pack_end( label, False, False, 0 )
    hbox = Gtk.HBox()
    vbox.pack_start( hbox, True, True, 0 )
    label = Gtk.Label( label=d_sane("Y Resolution") )
    hbox.pack_start( label, False, False, 0 )
    yspinbutton = Gtk.SpinButton.new_with_range( 0, MAX_DPI, 1 )
    yspinbutton.set_digits(1)
    hbox.pack_start( yspinbutton, True, True, 0 )
    label = Gtk.Label( label=_('dpi') )
    hbox.pack_end( label, False, False, 0 )
    ( xresolution, yresolution ) = get_selected_properties()
    logger.debug(
        f"get_selected_properties returned {xresolution},{yresolution}")
    xspinbutton.set_value(xresolution)
    yspinbutton.set_value(yresolution)
    def anonymous_203():
        ( xresolution, yresolution ) = get_selected_properties()
        logger.debug(
                f"get_selected_properties returned {xresolution},{yresolution}")
        xspinbutton.set_value(xresolution)
        yspinbutton.set_value(yresolution)


    slist.get_selection().connect(
        'changed' , anonymous_203 
    )
    def properties_apply_callback():
        windowp.hide()
        xresolution = xspinbutton.get_value()
        yresolution = yspinbutton.get_value()
        slist.get_model().handler_block(                slist.row_changed_signal )
        for i in          slist.get_selected_indices()  :
            logger.debug(
f"setting resolution {xresolution},{yresolution} for page {slist.data[i][0]}"
                )
            slist.data[i][2].xresolution = xresolution
            slist.data[i][2].yresolution = yresolution

        slist.get_model().handler_unblock(                slist.row_changed_signal )

    windowp.add_actions([
        ('gtk-ok',
        properties_apply_callback) ,
        ('gtk-cancel',
            lambda : windowp.hide())
    ])
    windowp.show_all()


def get_selected_properties() :
    "Helper function for properties()"
    page        = slist.get_selected_indices()
    xresolution = EMPTY
    yresolution = EMPTY
    if len(page) > 0 :
        page =  page.pop(0)
        xresolution = slist.data[page][2]["xresolution"]
        yresolution = slist.data[page][2]["yresolution"]
        logger.debug(
f"Page {slist}->{data}[{page}][0] has resolutions {xresolution},{yresolution}"
        )

    for i in     page :
        if slist.data[i][2].xresolution != xresolution :
            xresolution = EMPTY
            break

    for i in     page :
        if slist.data[i][2].yresolution != yresolution :
            yresolution = EMPTY
            break

    # round the value to a sensible number of significant figures
    return    0 if xresolution==EMPTY  else '%.1g' % (  xresolution ),          0 if yresolution==EMPTY  else '%.1g' % (yresolution)  


def ask_question(**kwargs) :
    "Helper function to display a message dialog, wait for a response, and return it"    

    # replace any numbers with metacharacters to compare to filter
    text =       filter_message( kwargs["text"] )
    if response_stored(
            text, SETTING["message"]
        )     :
        logger.debug( f"Skipped MessageDialog with '{kwargs['text']}', "
              + f"automatically replying '{SETTING['message'][text]['response']}'" )
        return SETTING["message"][text]["response"]

    cb=None
    dialog =       Gtk.MessageDialog( parent=kwargs["parent"],
    modal=True, destroy_with_parent=True ,
        message_type=kwargs["type"], buttons=kwargs["buttons"], text=kwargs["text"] )
    logger.debug(f"Displayed MessageDialog with '{kwargs['text']}'")
    if 'store-response' in kwargs :
        cb = Gtk.CheckButton.new_with_label(
            _("Don't show this message again") )
        dialog.get_message_area().add(cb)

    if  'default-response'  in kwargs :
        dialog.set_default_response( kwargs['default-response'] )

    dialog.show_all()
    response = dialog.run()
    dialog.destroy()
    if 'store-response' in kwargs and cb.get_active() :
        filter = True
        if kwargs['stored-responses'] :
            filter = False
            for i in              kwargs['stored-responses']  :
                if i == response :
                    filter = True
                    break

        if filter :
            SETTING["message"][text]["response"] = response

    logger.debug(f"Replied '{response}'")
    return response


def show_message_dialog(**options) :
    global message_dialog
    if   message_dialog is None :
        message_dialog = MultipleMessage(
            title           = _('Messages'),
            transient_for = options["parent"]
        )
        message_dialog.set_default_size( SETTING["message_window_width"],
            SETTING["message_window_height"] )

    options["responses"] = SETTING["message"]
    message_dialog.add_message(options)
    response=None
    if message_dialog.grid_rows > 1 :
        message_dialog.show_all()
        response = message_dialog.run()

    if  message_dialog is not None :    # could be undefined for multiple calls
        message_dialog.store_responses( response, SETTING["message"] )
        SETTING["message_window_width"], SETTING["message_window_height"]  =           message_dialog.get_size()
        message_dialog.destroy()
        message_dialog=None


def recursive_slurp(files):
    for file in     files :
        if os.path.isdir(file):
            recursive_slurp(glob.glob(f'{file}/*') )
        else:
            output = slurp(file)
            if  output is not None :
                output=output.rstrip() 
                logger.info(output)


def pre_flight():
    global args
    global rc
    global SETTING
    global iconpath
    args = parse_arguments()

    # Catch and log Python warnings
    logging.captureWarnings(True)

    rc, SETTING = read_config()
    if SETTING["cwd"] is None:
        SETTING["cwd"] = os.getcwd()
    SETTING["version"] = VERSION

    logger.info(f"Operating system: {sys.platform}")
    if sys.platform == 'linux' :
        recursive_slurp(glob.glob('/etc/*-release') )

    logger.info(f"Python version {sys.version_info}")
    logger.info(f"GLib VERSION_MIN_REQUIRED {GLib.VERSION_MIN_REQUIRED}")
    logger.info(f"GLib._version {GLib._version}")
    logger.info(    f"gi.__version__ {gi.__version__}")
    logger.info(    f"gi.version_info {gi.version_info}")
    logger.info(f"Gtk._version {Gtk._version}")
    logger.info( 'Built for GTK %s.%s.%s', Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION )
    logger.info(
        'Running with GTK %s.%s.%s', Gtk.get_major_version(), Gtk.get_minor_version(),
            Gtk.get_micro_version())
    logger.info( 'sane.__version__ %s',sane.__version__)   
    logger.info( 'sane.init() %s',sane.init())   

    if debug :
        logger.debug( Dumper( SETTING ) )

    SETTING["version"] = VERSION

    # Create icons for rotate buttons
    iconpath=None
    if os.path.isdir('/usr/share/gscan2pdf') :
        iconpath = '/usr/share/gscan2pdf'
    else :
        iconpath = 'icons'

    init_icons([
    ('rotate90',    f"{iconpath}/stock-rotate-90.svg"),     
    ('rotate180',   f"{iconpath}/180_degree.svg"),     
    ('rotate270',   f"{iconpath}/stock-rotate-270.svg") ,     
    #('scanner',     f"{iconpath}/scanner.svg") ,     
    ('pdf',         f"{iconpath}/pdf.svg") ,     
    ('selection',   f"{iconpath}/stock-selection-all-16.png") ,     
    ('hand-tool',   f"{iconpath}/hand-tool.svg") ,     
    ('mail-attach', f"{iconpath}/mail-attach.svg") ,     
    ('crop',        f"{iconpath}/crop.svg") ,
    ])


class ApplicationWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pre_flight()

        # # This will be in the windows group and have the "win" prefix
        # max_action = Gio.SimpleAction.new_stateful(
        #     "maximize", None, GLib.Variant.new_boolean(False)
        # )
        # max_action.connect("change-state", self.on_maximize_toggle)
        # self.add_action(max_action)

        # # Keep it in sync with the actual state
        # self.connect(
        #     "notify::is-maximized",
        #     lambda obj, pspec: max_action.set_state(
        #         GLib.Variant.new_boolean(obj.props.is_maximized)
        #     ),
        # )

        # lbl_variant = GLib.Variant.new_string("String 1")
        # lbl_action = Gio.SimpleAction.new_stateful(
        #     "change_label", lbl_variant.get_type(), lbl_variant
        # )
        # lbl_action.connect("change-state", self.on_change_label_state)
        # self.add_action(lbl_action)

        # self.label = Gtk.Label(label=lbl_variant.get_string(), margin=30)
        # self.add(self.label)
        # self.label.show()

        self.connect(            'delete-event' , lambda w, e: not quit()         )

        def anonymous_33( w, event ):
            "Note when the window is maximised or not"            
            SETTING['window_maximize'] = bool( event.new_window_state & Gdk.WindowState.MAXIMIZED )  

        self.connect(            'window-state-event' , anonymous_33         )

        # If defined in the config file, set the window state, size and position
        if SETTING['restore window'] :
            self.set_default_size( SETTING["window_width"],
                SETTING["window_height"] )
            if  "window_x"  in SETTING and  "window_y"  in SETTING :
                self.move( SETTING["window_x"], SETTING["window_y"] )

            if SETTING["window_maximize"] :
                self.maximize()

        try :
            self.set_icon_from_file(f"{iconpath}/gscan2pdf.svg") 
        except :
            logger.warning(
                f"Unable to load icon `{iconpath}/gscan2pdf.svg': {EVAL_ERROR}")

        # app.add_window(window)
        self.populate_main_window()

    def on_change_label_state(self, action, value):
        action.set_state(value)
        self.label.set_text(value.get_string())

    def on_maximize_toggle(self, action, value):
        action.set_state(value)
        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()

    def populate_main_window(self) :
        global slist
        main_vbox = Gtk.VBox()
        self.add(main_vbox)

        # Set up a SimpleList
        slist = Document()

        # Update list in Document so that it can be used by get_resolution()
        slist.set_paper_sizes( SETTING["Paper"] )

        # The temp directory has to be available before we start checking for
        # dependencies in order to be used for the pdftk check.
        create_temp_directory()

        # Create the menu bar
        menubar, toolbar = self.create_menu_bar()
        main_vbox.pack_start( menubar, False, True,  0 )
        main_vbox.pack_start( toolbar, False, False, 0 )

        # HPaned for thumbnails and detail view
        global hpaned
        hpaned = Gtk.HPaned()
        hpaned.set_position( SETTING['thumb panel'] )
        main_vbox.pack_start( hpaned, True, True, 0 )

        # Scrolled window for thumbnails
        scwin_thumbs = Gtk.ScrolledWindow()

        # resize = FALSE to stop the panel expanding on being resized
        # (Debian #507032)
        hpaned.pack1( scwin_thumbs, False, True )
        scwin_thumbs.set_policy( Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC )
        scwin_thumbs.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        # If dragged below the bottom of the window, scroll it.
        slist.connect( 'drag-motion' , drag_motion_callback )

        # Set up callback for right mouse clicks.
        slist.connect( 'button-press-event'   , handle_clicks )
        slist.connect( 'button-release-event' , handle_clicks )
        scwin_thumbs.add(slist)

        # Notebook, split panes for detail view and OCR output
        global vnotebook
        vnotebook = Gtk.Notebook()
        global hpanei
        hpanei    = Gtk.HPaned()
        vpanei    = Gtk.VPaned()
        hpanei.show()
        vpanei.show()

        # ImageView for detail view
        global view
        view = ImageView()
        if SETTING["image_control_tool"] == SELECTOR_TOOL :
            view.set_tool( Selector(view) )
    
        elif SETTING["image_control_tool"] == DRAGGER_TOOL :
            view.set_tool( Dragger(view) )
    
        else :
            view.set_tool(SelectorDragger(view) )

        view.connect(            'button-press-event' , handle_clicks        )
        view.connect( 'button-release-event' , handle_clicks )
        def view_zoom_changed_callback(view, zoom):
            global canvas
            if  canvas is not None :
                canvas.handler_block( canvas.zoom_changed_signal )
                canvas.set_scale( zoom )
                canvas.handler_unblock(canvas.zoom_changed_signal )

        view.zoom_changed_signal = view.connect(            'zoom-changed' , view_zoom_changed_callback         )
        def view_offset_changed_callback(view, x, y):
            global canvas
            if  canvas is not None :
                canvas.handler_block(canvas.offset_changed_signal )
                canvas.set_offset( x, y )
                canvas.handler_unblock(canvas.offset_changed_signal )

        view.offset_changed_signal = view.connect(            'offset-changed' , view_offset_changed_callback         )

        def view_selection_changed_callback( view, sel ):
            "Callback if the selection changes"            
            if  sel is not None :
                SETTING["selection"] = sel
                if  (sb_selector_x is not None) :
                    sb_selector_x.set_value( SETTING["selection"]["x"] )
                    sb_selector_y.set_value( SETTING["selection"]["y"] )
                    sb_selector_w.set_value( SETTING["selection"]["width"] )
                    sb_selector_h.set_value( SETTING["selection"]["height"] )

        view.selection_changed_signal = view.connect(            'selection-changed' , view_selection_changed_callback         )

        # Goo.Canvas for text layer
        global canvas
        canvas = Canvas()
        def canvas_zoom_changed_callback(canvas, zoom):
            view.handler_block( view.zoom_changed_signal )
            view.set_zoom( canvas.get_scale() )
            view.handler_unblock( view.zoom_changed_signal )

        canvas.zoom_changed_signal = canvas.connect(            'zoom-changed' , canvas_zoom_changed_callback         )
        def anonymous_06():
            view.handler_block( view.offset_changed_signal )
            offset = canvas.get_offset()
            view.set_offset( offset["x"], offset["y"] )
            view.handler_unblock( view.offset_changed_signal )

        canvas.offset_changed_signal = canvas.connect(            'offset-changed' , anonymous_06         )

        # Goo.Canvas for annotation layer
        global a_canvas
        a_canvas = Canvas()
        def anonymous_07():
            view.handler_block( view.zoom_changed_signal )
            view.set_zoom( a_canvas.get_scale() )
            view.handler_unblock( view.zoom_changed_signal )

        a_canvas.zoom_changed_signal = a_canvas.connect(            'zoom-changed' , anonymous_07         )
        def anonymous_08():
            view.handler_block( view.offset_changed_signal )
            offset = a_canvas.get_offset()
            view.set_offset( offset["x"], offset["y"] )
            view.handler_unblock( view.offset_changed_signal )

        a_canvas.offset_changed_signal = a_canvas.connect(            'offset-changed' , anonymous_08         )

        # split panes for detail view/text layer canvas and text layer dialog
        global vpaned
        vpaned = Gtk.VPaned()
        hpaned.pack2( vpaned, True, True )
        vpaned.show()
        ocr_text_hbox = Gtk.HBox()
        edit_vbox = Gtk.HBox()
        vpaned.pack2( edit_vbox, False, True )
        edit_vbox.pack_start( ocr_text_hbox, True, True, 0 )
        ocr_textview = Gtk.TextView()
        ocr_textview.set_tooltip_text( _('Text layer') )
        ocr_textbuffer = ocr_textview.get_buffer()
        ocr_text_fbutton = Gtk.Button()
        ocr_text_fbutton.set_image(
            Gtk.Image.new_from_icon_name("go-first", Gtk.IconSize.BUTTON))
        ocr_text_fbutton.set_tooltip_text( _('Go to least confident text') )
        def anonymous_09():
            edit_ocr_text( canvas.get_first_bbox() )

        ocr_text_fbutton.connect(
            'clicked' , anonymous_09  )
        ocr_text_pbutton = Gtk.Button()
        ocr_text_pbutton.set_image(
            Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON))
        ocr_text_pbutton.set_tooltip_text( _('Go to previous text') )
        def anonymous_10():
            edit_ocr_text( canvas.get_previous_bbox() )

        ocr_text_pbutton.connect(
            'clicked' , anonymous_10  )
        ocr_index = [
        [
        'confidence',             _('Sort by confidence'),             _('Sort OCR text boxes by confidence.')
            ],         [
        'position', _('Sort by position'),             _('Sort OCR text boxes by position.')
            ],
        ]
        ocr_text_scmbx = ComboBoxText(data=ocr_index)
        ocr_text_scmbx.set_tooltip_text( _('Select sort method for OCR boxes') )
        def anonymous_11(arg):
            global canvas
            if ocr_index[ ocr_text_scmbx.get_active() ][0] == 'confidence'             :
                canvas.sort_by_confidence()
    
            else :
                canvas.sort_by_position()

        ocr_text_scmbx.connect(            'changed' , anonymous_11         )
        ocr_text_scmbx.set_active(0)
        ocr_text_nbutton = Gtk.Button()
        ocr_text_nbutton.set_image(
            Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        ocr_text_nbutton.set_tooltip_text( _('Go to next text') )
        def anonymous_12():
            global canvas
            edit_ocr_text( canvas.get_next_bbox() )

        ocr_text_nbutton.connect(
            'clicked' , anonymous_12  )
        ocr_text_lbutton = Gtk.Button()
        ocr_text_lbutton.set_image(
            Gtk.Image.new_from_icon_name("go-last", Gtk.IconSize.BUTTON))
        ocr_text_lbutton.set_tooltip_text( _('Go to most confident text') )
        def anonymous_13():
            global canvas
            edit_ocr_text( canvas.get_last_bbox() )

        ocr_text_lbutton.connect(
            'clicked' , anonymous_13  )
        ocr_text_obutton = Gtk.Button(label=_("_OK"))
        ocr_text_obutton.set_tooltip_text( _('Accept corrections') )
        def anonymous_14():
            take_snapshot()
            text = ocr_textbuffer.text
            logger.info(
                    "Corrected '" + ocr_bbox.text + f"'->'{text}'" )
            ocr_bbox.update_box( text, view.get_selection() )
            global canvas
            current_page.import_hocr( canvas.hocr() )
            edit_ocr_text(ocr_bbox)


        ocr_text_obutton.connect(
            'clicked' , anonymous_14 
        )
        ocr_text_cbutton = Gtk.Button(label=_("_Cancel"))
        ocr_text_cbutton.set_tooltip_text( _('Cancel corrections') )
        def anonymous_15():
            ocr_text_hbox.hide()


        ocr_text_cbutton.connect(
            'clicked' , anonymous_15 
        )
        ocr_text_ubutton = Gtk.Button(label=_("_Copy"))
        ocr_text_ubutton.set_tooltip_text( _('Duplicate text') )
        def anonymous_16():
            global canvas
            ocr_bbox = canvas.add_box( ocr_textbuffer.text,
                    view.get_selection() )
            current_page.import_hocr( canvas.hocr() )
            edit_ocr_text(ocr_bbox)


        ocr_text_ubutton.connect(
            'clicked' , anonymous_16 
        )
        ocr_text_abutton = Gtk.Button()
        ocr_text_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
        ocr_text_abutton.set_tooltip_text( _('Add text') )
        def anonymous_17():
            global canvas
            take_snapshot()
            text = ocr_textbuffer.text
            if   (text is None) or text == EMPTY :
                text = _('my-new-word')

            # If we don't yet have a canvas, create one
            selection = view.get_selection()
            if  hasattr(current_page,'text_layer') :
                logger.info(f"Added '{text}'")
                ocr_bbox = canvas.add_box( text, view.get_selection() )
                current_page.import_hocr( canvas.hocr() )
                edit_ocr_text(ocr_bbox)
    
            else :
                logger.info(f"Creating new text layer with '{text}'")
                current_page.text_layer =                   '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]' % (current_page["width"],current_page["height"],selection["x"],selection["y"],selection["x"]+selection["width"],selection["y"]+selection["height"],text)                                                                                           
                def anonymous_18():
                    ocr_bbox = canvas.get_first_bbox()
                    edit_ocr_text(ocr_bbox)


                create_txt_canvas(
                        current_page,
                        anonymous_18 
                    )



        ocr_text_abutton.connect(
            'clicked' , anonymous_17 
        )
        ocr_text_dbutton = Gtk.Button(label=_("_Delete"))
        ocr_text_dbutton.set_tooltip_text( _('Delete text') )
        def anonymous_19():
            ocr_bbox.delete_box()
            current_page.import_hocr( canvas.hocr() )
            edit_ocr_text( canvas.get_current_bbox() )

        ocr_text_dbutton.connect(            'clicked' , anonymous_19         )
        ocr_text_hbox.pack_start( ocr_text_fbutton, False, False, 0 )
        ocr_text_hbox.pack_start( ocr_text_pbutton, False, False, 0 )
        ocr_text_hbox.pack_start( ocr_text_scmbx,   False, False, 0 )
        ocr_text_hbox.pack_start( ocr_text_nbutton, False, False, 0 )
        ocr_text_hbox.pack_start( ocr_text_lbutton, False, False, 0 )
        ocr_text_hbox.pack_start( ocr_textview,     False, False, 0 )
        ocr_text_hbox.pack_end( ocr_text_dbutton, False, False, 0 )
        ocr_text_hbox.pack_end( ocr_text_cbutton, False, False, 0 )
        ocr_text_hbox.pack_end( ocr_text_obutton, False, False, 0 )
        ocr_text_hbox.pack_end( ocr_text_ubutton, False, False, 0 )
        ocr_text_hbox.pack_end( ocr_text_abutton, False, False, 0 )

        # split panes for detail view/text layer canvas and text layer dialog
        ann_hbox = Gtk.HBox()
        edit_vbox.pack_start( ann_hbox, True, True, 0 )
        ann_textview = Gtk.TextView()
        ann_textview.set_tooltip_text( _('Annotations') )
        ann_textbuffer = ann_textview.get_buffer()
        ann_obutton = Gtk.Button(label=_("_Ok"))
        ann_obutton.set_tooltip_text( _('Accept corrections') )
        def anonymous_20():
            text = ann_textbuffer.text
            logger.info(
                    "Corrected '" + ann_bbox.text + f"'->'{text}'" )
            ann_bbox.update_box( text, view.get_selection() )
            current_page.import_annotations( a_canvas.hocr() )
            edit_annotation(ann_bbox)

        ann_obutton.connect(            'clicked' , anonymous_20         )
        ann_cbutton = Gtk.Button(label=_("_Cancel"))
        ann_cbutton.set_tooltip_text( _('Cancel corrections') )
        ann_cbutton.connect(            'clicked' , ann_hbox.hide         )
        ann_abutton = Gtk.Button()
        ann_abutton.set_image(
            Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
        ann_abutton.set_tooltip_text( _('Add annotation') )
        def anonymous_22():
            text = ann_textbuffer.text
            if   (text is None) or text == EMPTY :
                text = _('my-new-annotation')

                # If we don't yet have a canvas, create one
            selection = view.get_selection()
            if  hasattr(current_page,'text_layer') :
                logger.info(f"Added '{ann_textbuffer.text}'" )
                ann_bbox = a_canvas.add_box( text, view.get_selection() )
                current_page.import_annotations( a_canvas.hocr() )
                edit_annotation(ann_bbox)
    
            else :
                logger.info(f"Creating new annotation canvas with '{text}'")
                current_page["annotations"] =                   '[{"type":"page","bbox":[0,0,%d,%d],"depth":0},{"type":"word","bbox":[%d,%d,%d,%d],"text":"%s","depth":1}]' % (current_page["width"],current_page["height"],selection["x"],selection["y"],selection["x"]+selection["width"],selection["y"]+selection["height"],text)                                                                                           
                def anonymous_23():
                    ann_bbox = a_canvas.get_first_bbox()
                    edit_annotation(ann_bbox)


                create_ann_canvas(
                        current_page,
                        anonymous_23 
                    )

        ann_abutton.connect(            'clicked' , anonymous_22         )
        ann_dbutton = Gtk.Button(label=_("_Delete"))
        ann_dbutton.set_tooltip_text( _('Delete annotation') )
        def anonymous_24():
            ann_bbox.delete_box()
            current_page.import_hocr( a_canvas.hocr() )
            edit_annotation( canvas.get_bbox_by_index() )

        ann_dbutton.connect(            'clicked' , anonymous_24         )
        ann_hbox.pack_start( ann_textview, False, False, 0 )
        ann_hbox.pack_end( ann_dbutton, False, False, 0 )
        ann_hbox.pack_end( ann_cbutton, False, False, 0 )
        ann_hbox.pack_end( ann_obutton, False, False, 0 )
        ann_hbox.pack_end( ann_abutton, False, False, 0 )
        pack_viewer_tools()

        # Set up call back for list selection to update detail view
        slist.selection_changed_signal = slist.get_selection().connect(
            'changed' , selection_changed_callback )

        # Without these, the imageviewer and page list steal -/+/ctrl x/c/v keys
        # from the OCR textview
        self.connect(            'key-press-event' , Gtk.Window.propagate_key_event )
        self.connect(            'key-release-event' , Gtk.Window.propagate_key_event )

        def anonymous_25( widget, event ):
            """    # _after ensures that Editables get first bite"""            

                # Let the keypress propagate
            if event.keyval!=Gdk.KEY_Delete   :
                return False
            delete_selection()
            return True


        self.connect_after(            'key-press-event' , anonymous_25         )

        # If defined in the config file, set the current directory
        if 'cwd' not   in SETTING :
            SETTING['cwd'] = getcwd
        unpaper = Unpaper( SETTING['unpaper options'] )
        update_uimanager()
        self.show_all()

        # Progress bars below window
        phbox = Gtk.HBox()
        main_vbox.pack_end( phbox, False, False, 0 )
        phbox.show()
        global shbox
        shbox = Gtk.HBox()
        phbox.add(shbox)
        global spbar    
        spbar = Gtk.ProgressBar()
        spbar.set_show_text(True)
        shbox.add(spbar)
        global scbutton
        scbutton = Gtk.Button(label=_("_Cancel"))
        shbox.pack_end( scbutton, False, False, 0 )
        global thbox
        thbox = Gtk.HBox()
        phbox.add(thbox)
        tpbar = Gtk.ProgressBar()
        tpbar.set_show_text(True)
        thbox.add(tpbar)
        tcbutton = Gtk.Button(label=_("_Cancel"))
        thbox.pack_end( tcbutton, False, False, 0 )
        ocr_text_hbox.show()
        ann_hbox.hide()

        # Open scan dialog in background
        if SETTING['auto-open-scan-dialog'] :
            scan_dialog( None, True )

        # Deal with --import command line option
        if  args.import_files is not None     :
            import_files(args.import_files)
        if  args.import_all is not None :
            import_files( args.import_all, True )


    def create_menu_bar(self) :
        "Create the menu bar, initialize its menus, and return the menu bar"
        global uimanager
        uimanager = Gtk.UIManager()

        def anonymous_34(w):
            if quit() :
                app.quit()

        def anonymous_35(w):
            select_odd_even(0)

        def anonymous_36(w):
            select_odd_even(1)

        def anonymous_37(w):
            view.set_zoom(1.0)

        def anonymous_38(w):
            view.zoom_to_fit()

        def anonymous_39(w):
            view.zoom_in()

        def anonymous_40(w):
            view.zoom_out()

        def anonymous_41(w):
            rotate( _90_DEGREES,
                        [
            indices2pages( slist.get_selected_indices() ) ] )

        def anonymous_42(w):
            rotate( _180_DEGREES,
                        [
            indices2pages( slist.get_selected_indices() ) ] )

        def anonymous_43(w):
            rotate( _270_DEGREES,
                        [
            indices2pages( slist.get_selected_indices() ) ] )

        # extract the accelgroup and add it to the window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        action_items = [
                # Fields for each action item:
            # [name, stock_id, value, label, accelerator, tooltip, callback]
            # File menu
            [
        'File', None, _('_File') ],         [
        'New',                  'gtk-new',             _('_New'),             '<control>n',             _('Clears all pages'), new
            ],         [
        'Open',                   'gtk-open',             _('_Open'),              '<control>o',             _('Open image file(s)'), open_dialog
            ],         [
        'Open crashed session',      None,             _('Open c_rashed session'), None,             _('Open crashed session'),  open_session_action
            ],         [
        'Scan',              'scanner',             _('S_can'),         '<control>g',             _('Scan document'), scan_dialog
            ],         [
        'Save',     'gtk-save', _('Save'), '<control>s',             _('Save'), save_dialog
            ],         [
        'Email as PDF',                     'mail-attach',             _('_Email as PDF'),                '<control>e',             _('Attach as PDF to a new email'), email
            ],         [
        'Print',     'gtk-print', _('_Print'), '<control>p',             _('Print'), print_dialog
            ],         [
        'Quit',             'gtk-quit',             _('_Quit'),             '<control>q',             _('Quit'),             anonymous_34 
            ],          # Edit menu
            [
        'Edit', None, _('_Edit') ],         [
        'Undo', 'gtk-undo', _('_Undo'), '<control>z', _('Undo'), undo ],         [
        'Redo',      'gtk-redo',             _('_Redo'), '<shift><control>z',             _('Redo'),  unundo
            ],         [
        'Cut',               'gtk-cut',             _('Cu_t'),          '<control>x',             _('Cut selection'), cut_selection
            ],         [
        'Copy',               'gtk-copy',             _('_Copy'),          '<control>c',             _('Copy selection'), copy_selection
            ],         [
        'Paste',               'gtk-paste',             _('_Paste'),          '<control>v',             _('Paste selection'), paste_selection
            ],         [
        'Delete',                    'gtk-delete',             _('_Delete'),               None,             _('Delete selected pages'), delete_selection
            ],         [
        'Renumber',           'gtk-sort-ascending',             _('_Renumber'),      '<control>r',             _('Renumber pages'), renumber_dialog
            ],         [
        'Select', None, _('_Select') ],         [
        'Select All',           'gtk-select-all',             _('_All'),             '<control>a',             _('Select all pages'), select_all
            ],         [
        'Select Odd', None, _('_Odd'), '<control>1',             _('Select all odd-numbered pages'),             anonymous_35 
            ],         [
        'Select Even', None, _('_Even'), '<control>2',             _('Select all evenly-numbered pages'),             anonymous_36 
            ],         [
        'Invert selection',     None,             _('_Invert'),          '<control>i',             _('Invert selection'), select_invert
            ],         [
        'Select Blank',             'gtk-select-blank',             _('_Blank'),             '<control>b',             _('Select pages with low standard deviation'),             analyse_select_blank
            ],         [
        'Select Dark',           'gtk-select-blank',             _('_Dark'),             '<control>d',             _('Select dark pages'), analyse_select_dark
            ],         [
        'Select Modified',             'gtk-select-modified',             _('_Modified'),             '<control>m',             _('Select modified pages since last OCR'),             select_modified_since_ocr
            ],         [
        'Select No OCR',                       None,             _('_No OCR'),                         None,             _('Select pages with no OCR output'), select_no_ocr
            ],         [
        'Clear OCR',                                'gtk-clear',             _('_Clear OCR'),                           None,             _('Clear OCR output from selected pages'), clear_ocr
            ],         [
        'Properties',                'gtk-properties',             _('Propert_ies'),           None,             _('Edit image properties'), properties
            ],         [
        'Preferences',          'gtk-preferences',             _('Prefere_nces'),     None,             _('Edit preferences'), preferences
            ],          # View menu
            [
        'View', None, _('_View') ],         [
        'Zoom 100',         'gtk-zoom-100',             _('Zoom _100%'),   None,             _('Zoom to 100%'), anonymous_37 
            ],         [
        'Zoom to fit',      'gtk-zoom-fit',             _('Zoom to _fit'), None,             _('Zoom to fit'),  anonymous_38 
            ],         [
        'Zoom in',      'gtk-zoom-in',             _('Zoom _in'), 'plus',             _('Zoom in'),  anonymous_39 
            ],         [
        'Zoom out',      'gtk-zoom-out',             _('Zoom _out'), 'minus',             _('Zoom out'),  anonymous_40 
            ],         [
        'Rotate 90',             'rotate90',             _('Rotate 90° clockwise'),             '<control><shift>R',             _('Rotate 90° clockwise'),             anonymous_41 
            ],         [
        'Rotate 180',             'rotate180',             _('Rotate 180°'),             '<control><shift>F',             _('Rotate 180°'),             anonymous_42 
            ],         [
        'Rotate 270',             'rotate270',             _('Rotate 90° anticlockwise'),             '<control><shift>C',             _('Rotate 90° anticlockwise'),             anonymous_43 
            ],          # Tools menu
            [
        'Tools', None, _('_Tools') ],         [
        'Threshold', None, _('_Threshold'), None,             _('Change each pixel above this threshold to black'),             threshold
            ],         [
        'BrightnessContrast',               None,             _('_Brightness / Contrast'),       None,             _('Change brightness & contrast'), brightness_contrast
            ],         [
        'Negate', None, _('_Negate'), None,             _('Converts black to white and vice versa'), negate
            ],         [
        'Unsharp',                   None,             _('_Unsharp Mask'),         None,             _('Apply an unsharp mask'), unsharp
            ],         [
        'CropDialog',     'GTK_STOCK_LEAVE_FULLSCREEN',             _('_Crop'),      None,             _('Crop pages'), crop_dialog
            ],         [
        'CropSelection',      'crop',             _('_Crop'),          None,             _('Crop selection'), crop_selection
            ],         [
        'unpaper', None, _('_Clean up'), None,             _('Clean up scanned images with unpaper'), unpaper
            ],         [
        'split', None, _('_Split'), None,             _('Split pages horizontally or vertically'),             split_dialog
            ],         [
        'OCR', None, _('_OCR'), None,             _('Optical Character Recognition'),             ocr_dialog
            ],         [
        'User-defined', None, _('U_ser-defined'), None,             _('Process images with user-defined tool'),             user_defined_dialog
            ],          # Help menu
            [
        'Help menu', None, _('_Help') ],         [
        'Help',     'gtk-help', _('_Help'), '<control>h',             _('Help'), view_html
            ],         [
        'About', 'gtk-about', _('_About'), None, _('_About'), about ],
        ]
        image_tools = [
        [
        'DraggerTool',          'hand-tool',             _('_Pan'),             None,             _('Use the pan tool'), DRAGGER_TOOL
            ],         [
        'SelectorTool',                           'selection',             _('_Select'),                            None,             _('Use the rectangular selection tool'), SELECTOR_TOOL
            ],         [
        'SelectorDraggerTool',                      'gtk-media-play',             _('_Select & pan'),                        None,             _('Use the combined select and pan tool'), SELECTORDRAGGER_TOOL
            ],
        ]
        viewer_tools = [
        [
        'Tabbed', None, _('_Tabbed'), None,             _('Arrange image and OCR viewers in tabs'), TABBED_VIEW
            ],         [
        'SplitH', None, _('_Split horizontally'),             None,             _('Arrange image and OCR viewers in horizontally split screen'),             SPLIT_VIEW_H
            ],         [
        'SplitV', None, _('_Split vertically'), None,             _('Arrange image and OCR viewers in vertically split screen'),             SPLIT_VIEW_V
            ],
        ]
        ocr_tools = [
        [
        'Edit text layer',                       'gtk-edit',             _('Edit text layer'),                   None,             _('Show editing tools for text layer'), EDIT_TEXT
            ],         [
        'Edit annotations',             'error-correct-symbolic',             _('Edit annotations'),             None,             _('Show editing tools for annotations'),             EDIT_ANNOTATION
            ],
        ]
        ui = """<ui>
    <menubar name='MenuBar'>
    <menu action='File'>
    <menuitem action='New'/>
    <menuitem action='Open'/>
    <menuitem action='Open crashed session'/>
    <menuitem action='Scan'/>
    <menuitem action='Save'/>
    <menuitem action='Email as PDF'/>
    <menuitem action='Print'/>
    <separator/>
    <menuitem action='Compress'/>
    <separator/>
    <menuitem action='Quit'/>
    </menu>
    <menu action='Edit'>
    <menuitem action='Undo'/>
    <menuitem action='Redo'/>
    <separator/>
    <menuitem action='Cut'/>
    <menuitem action='Copy'/>
    <menuitem action='Paste'/>
    <menuitem action='Delete'/>
    <separator/>
    <menuitem action='Renumber'/>
    <menu action='Select'>
        <menuitem action='Select All'/>
        <menuitem action='Select Odd'/>
        <menuitem action='Select Even'/>
        <menuitem action='Invert selection'/>
        <menuitem action='Select Blank'/>
        <menuitem action='Select Dark'/>
        <menuitem action='Select Modified'/>
        <menuitem action='Select No OCR'/>
    </menu>
    <menuitem action='Clear OCR'/>
    <separator/>
    <menuitem action='Properties'/>
    <separator/>
    <menuitem action='Preferences'/>
    </menu>
    <menu action='View'>
    <menuitem action='DraggerTool'/>
    <menuitem action='SelectorTool'/>
    <menuitem action='SelectorDraggerTool'/>
    <separator/>
    <menuitem action='Tabbed'/>
    <menuitem action='SplitH'/>
    <menuitem action='SplitV'/>
    <separator/>
    <menuitem action='Zoom 100'/>
    <menuitem action='Zoom to fit'/>
    <menuitem action='Zoom in'/>
    <menuitem action='Zoom out'/>
    <separator/>
    <menuitem action='Rotate 90'/>
    <menuitem action='Rotate 180'/>
    <menuitem action='Rotate 270'/>
    <separator/>
    <menuitem action='Edit text layer'/>
    <menuitem action='Edit annotations'/>
    </menu>
    <menu action='Tools'>
    <menuitem action='Threshold'/>
    <menuitem action='BrightnessContrast'/>
    <menuitem action='Negate'/>
    <menuitem action='Unsharp'/>
    <menuitem action='CropDialog'/>
    <separator/>
    <menuitem action='split'/>
    <menuitem action='unpaper'/>
    <menuitem action='OCR'/>
    <separator/>
    <menuitem action='User-defined'/>
    </menu>
    <menu action='Help menu'>
    <menuitem action='Help'/>
    <menuitem action='About'/>
    </menu>
    </menubar>
    <toolbar name='ToolBar'>
    <toolitem action='New'/>
    <toolitem action='Open'/>
    <toolitem action='Scan'/>
    <toolitem action='Save'/>
    <toolitem action='Email as PDF'/>
    <toolitem action='Print'/>
    <separator/>
    <toolitem action='Undo'/>
    <toolitem action='Redo'/>
    <separator/>
    <toolitem action='Cut'/>
    <toolitem action='Copy'/>
    <toolitem action='Paste'/>
    <toolitem action='Delete'/>
    <separator/>
    <toolitem action='Renumber'/>
    <toolitem action='Select All'/>
    <separator/>
    <toolitem action='DraggerTool'/>
    <toolitem action='SelectorTool'/>
    <toolitem action='SelectorDraggerTool'/>
    <separator/>
    <toolitem action='Zoom 100'/>
    <toolitem action='Zoom to fit'/>
    <toolitem action='Zoom in'/>
    <toolitem action='Zoom out'/>
    <separator/>
    <toolitem action='Rotate 90'/>
    <toolitem action='Rotate 180'/>
    <toolitem action='Rotate 270'/>
    <separator/>
    <toolitem action='Edit text layer'/>
    <toolitem action='Edit annotations'/>
    <separator/>
    <toolitem action='CropSelection'/>
    <separator/>
    <toolitem action='Help'/>
    <toolitem action='Quit'/>
    </toolbar>
    <popup name='Detail_Popup'>
    <menuitem action='DraggerTool'/>
    <menuitem action='SelectorTool'/>
    <menuitem action='SelectorDraggerTool'/>
    <separator/>
    <menuitem action='Zoom 100'/>
    <menuitem action='Zoom to fit'/>
    <menuitem action='Zoom in'/>
    <menuitem action='Zoom out'/>
    <separator/>
    <menuitem action='Rotate 90'/>
    <menuitem action='Rotate 180'/>
    <menuitem action='Rotate 270'/>
    <separator/>
    <menuitem action='Edit text layer'/>
    <menuitem action='Edit annotations'/>
    <separator/>
    <menuitem action='CropSelection'/>
    <separator/>
    <menuitem action='Cut'/>
    <menuitem action='Copy'/>
    <menuitem action='Paste'/>
    <menuitem action='Delete'/>
    <separator/>
    <menuitem action='Properties'/>
    </popup>
    <popup name='Thumb_Popup'>
    <menuitem action='Save'/>
    <menuitem action='Email as PDF'/>
    <menuitem action='Print'/>
    <separator/>
    <menuitem action='Renumber'/>
    <menuitem action='Select All'/>
    <menuitem action='Select Odd'/>
    <menuitem action='Select Even'/>
    <menuitem action='Invert selection'/>
    <separator/>
    <menuitem action='Rotate 90'/>
    <menuitem action='Rotate 180'/>
    <menuitem action='Rotate 270'/>
    <separator/>
    <menuitem action='CropSelection'/>
    <separator/>
    <menuitem action='Cut'/>
    <menuitem action='Copy'/>
    <menuitem action='Paste'/>
    <menuitem action='Delete'/>
    <separator/>
    <menuitem action='Clear OCR'/>
    <separator/>
    <menuitem action='Properties'/>
    </popup>
    </ui>
    """

        # Create the basic Gtk.ActionGroup instance
        # and fill it with Gtk.Action instances
        actions_basic = Gtk.ActionGroup('actions_basic')
        actions_basic.add_actions( action_items, None )
        actions_basic.add_radio_actions( image_tools,
            SETTING["image_control_tool"],
            change_image_tool_cb )
        actions_basic.add_radio_actions( viewer_tools, SETTING["viewer_tools"],
            change_view_cb )
        actions_basic.add_radio_actions( ocr_tools, EDIT_TEXT,
            edit_tools_callback )

        # Add the actiongroup to the uimanager
        uimanager.insert_action_group( actions_basic, 0 )

        # add the basic XML description of the GUI
        uimanager.add_ui_from_string(ui)

        # extract the menubar
        menubar = uimanager.get_widget('/MenuBar')

        # Check for presence of various packages
        check_dependencies()

        # Ghost save image item if imagemagick not available
        msg = EMPTY
        if not dependencies["imagemagick"] :
            msg += _("Save image and Save as PDF both require imagemagick\n")

        # Ghost save image item if libtiff not available
        if not dependencies["libtiff"] :
            msg += _("Save image requires libtiff\n")

        # Ghost djvu item if cjb2 not available
        if not dependencies["djvu"] :
            msg += _("Save as DjVu requires djvulibre-bin\n")

        # Ghost email item if xdg-email not available
        if not dependencies["xdg"] :
            msg += _("Email as PDF requires xdg-email\n")

        # Undo/redo start off ghosted anyway-
        uimanager.get_widget('/MenuBar/Edit/Undo').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Edit/Redo').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Undo').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Redo').set_sensitive(False)

        # save * start off ghosted anyway-
        uimanager.get_widget('/MenuBar/File/Save').set_sensitive(False)
        uimanager.get_widget('/MenuBar/File/Email as PDF').set_sensitive(False)
        uimanager.get_widget('/MenuBar/File/Print').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Save').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Email as PDF').set_sensitive(False)
        uimanager.get_widget('/ToolBar/Print').set_sensitive(False)
        uimanager.get_widget('/Thumb_Popup/Save').set_sensitive(False)
        uimanager.get_widget('/Thumb_Popup/Email as PDF').set_sensitive(False)
        uimanager.get_widget('/Thumb_Popup/Print').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/Threshold').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/BrightnessContrast')       .set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/Negate').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/Unsharp').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/CropDialog').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/User-defined').set_sensitive(False)
        uimanager.get_widget('/MenuBar/Tools/split').set_sensitive(False)

        if not dependencies["unpaper"] :
            msg += _("unpaper missing\n")

        dependencies["ocr"] = dependencies["tesseract"]
        if not dependencies["ocr"] :
            msg += _("OCR requires tesseract\n")

        if dependencies["tesseract"] :
            lc_messages = locale.setlocale(locale.LC_MESSAGES)
            lang_msg    = locale_installed(lc_messages, get_tesseract_codes())
            if lang_msg == "":
                logger.info(
    f"Using GUI language {lc_messages}, for which a tesseract language package is present"
                )
            else :
                logger.warning(lang_msg)
                msg += lang_msg 

        if not dependencies["pdftk"] :
            msg += _("PDF encryption requires pdftk\n")

        # Put up warning if needed
        if msg != EMPTY :
            msg = _('Warning: missing packages') + f"\n{msg}"
            show_message_dialog(
                parent           = self,
                message_type             = 'warning',
                buttons          = Gtk.ButtonsType.OK,
                text             = msg,
                store_response = True
            )

        # extract the toolbar
        toolbar = uimanager.get_widget('/ToolBar')

        # turn off labels
        settings = toolbar.get_settings()
        settings.gtk_toolbar_style='icons'    # only icons
        return menubar, toolbar


class Application(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.gscan2pdf",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
            **kwargs
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


    def do_startup(self):
        Gtk.Application.do_startup(self)

        # action = Gio.SimpleAction.new("about", None)
        # action.connect("activate", self.on_about)
        # self.add_action(action)

        # action = Gio.SimpleAction.new("quit", None)
        # action.connect("activate", self.on_quit)

        # self.add_action(action)
        # builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        # self.set_app_menu(builder.get_object("app-menu"))

    def do_activate(self):
        "only allow a single window and raise any existing ones"

        # Windows are associated with the application
        # until the last one is closed and the application shuts down
        if not self.window:
            self.window = ApplicationWindow(application=self, title=f"{prog_name} v{VERSION}")
            global window
            window=self.window
        self.window.present()

    # def do_command_line(self, command_line):
    #     options = command_line.get_options_dict()

    #     # convert GVariantDict -> GVariant -> dict
    #     options = options.end().unpack()

    #     if "test" in options:
    #         # This is printed on the main instance
    #         print("Test argument recieved: %s" % options["test"])

    #     self.activate()
    #     return 0

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.quit()

if __name__ == "__main__":
    app = Application()
    # app.run(sys.argv)
    app.run()

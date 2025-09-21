"main application"

# TODO:
# profile not set on startup
# adding a tool in preferences doesn't show in the scan window until a restart
# when adding udf tools to the scan window, check they are executable (and therefore also exist)
# change page numbering to always run from 1-n with no gaps
# fix readme
# hook ocrmypdf progress into the GUI
# package for Debian
# package pytest-black for Debian
# lint
# fail tests that hit mainloop timeouts
# use pathlib for all paths
# refactor methods using self.slist.clipboard
# refactor ocr & annotation manipulation into single class
# various improvements from StackOverflow
# add type hints and turn on type checks in tox.ini
# migrate to Gtk4
# remaining FIXMEs and TODOs

# gscan2pdf --- to aid the scan to PDF or DjVu process

# Release procedure:
#    Use
#      pytest -vv
#    immediately before release so as not to affect any patches
#    in between, and then consistently before each commit afterwards.
# 0. Test scan in lineart, greyscale and colour.
# 1. New screendump required? Print screen creates screenshot.png in Desktop.
#    Download new translations (https://translations.launchpad.net/gscan2pdf)
#    Update translators in credits (https://launchpad.net/gscan2pdf/+topcontributors)
#    Update VERSION
#    Make appropriate updates to debian/changelog
# 2.  perl Makefile.PL
#     Upload .pot
# 3.  make remote-html
# 4. Build .deb for sf
#     python3 -m build --sdist
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
#       pytest -vv

import argparse
import atexit
import gettext
import locale
import logging
import lzma
import os
import re
import shutil
import sys
import warnings

# check for pyinstaller
if hasattr(sys, "frozen"):
    base_dir = sys._MEIPASS  # pylint: disable=protected-access
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

# pylint: disable=wrong-import-position
from app_window import ApplicationWindow
from const import SPACE, VERSION, PROG_NAME
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import (
    Gtk,
    Gio,
)

# pylint: enable=wrong-import-position


class Application(Gtk.Application):
    "Application class"

    def __init__(self, *args, **kwargs):
        self.args = kwargs.pop("cmdline", None) or []
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
            iconpath = "/usr/share/gscan2pdf"
        else:
            iconpath = "icons"
        Gtk.IconTheme.get_default().prepend_search_path(iconpath)

    def do_startup(self, *args, **kwargs):
        Gtk.Application.do_startup(self)

    def do_activate(self, *args, **kwargs):
        "only allow a single window and raise any existing ones"

        # Windows are associated with the application
        # until the last one is closed and the application shuts down
        if not self.window:
            self.window = ApplicationWindow(application=self)
        self.window.present()


def _parse_arguments():
    "parse command line arguments"
    parser = argparse.ArgumentParser(
        prog=PROG_NAME, description="What the program does"
    )
    parser.add_argument("--device", nargs="+")
    parser.add_argument("--import", nargs="+", dest="import_files")
    parser.add_argument("--import-all", nargs="+")
    parser.add_argument("--locale")
    parser.add_argument("--log", type=str)
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument(
        "--debug",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
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
        args.log = os.path.abspath(args.log)
        if args.log_level is None:
            args.log_level = logging.DEBUG
        logging.basicConfig(filename=args.log, filemode="w", level=args.log_level)

        def compress_log():
            try:
                with open(args.log, "rb") as f_in, lzma.open(
                    args.log + ".xz", "wb"
                ) as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(args.log)
            except (OSError, lzma.LZMAError) as e:
                logging.getLogger(__name__).error("Failed to compress log: %s", e)

        atexit.register(compress_log)
    else:
        if args.log_level is None:
            args.log_level = logging.WARNING
        logging.basicConfig(level=args.log_level)

    logger = logging.getLogger(__name__)

    # if help is not None:
    #     try:
    #         subprocess.run([f"perldoc {PROGRAM_NAME}"]) == 0
    #     except:
    #         raise _('Error displaying help'), "\n"
    logger.info("Starting %s %s", PROG_NAME, VERSION)
    logger.info("Called with %s", SPACE.join([sys.executable] + sys.argv))

    # make sure argv has absolute paths in case we change directories
    # and then restart the program
    sys.argv = [os.path.abspath(path) for path in sys.argv if os.path.isfile(path)]

    logger.info("Log level %s", args.log_level)
    if args.locale is None:
        gettext.bindtextdomain(f"{PROG_NAME}")
    else:
        if re.search(r"^\/", args.locale, re.MULTILINE | re.DOTALL | re.VERBOSE):
            gettext.bindtextdomain(f"{PROG_NAME}", locale)
        else:
            gettext.bindtextdomain(f"{PROG_NAME}", os.getcwd() + f"/{locale}")
    gettext.textdomain(PROG_NAME)

    logger.info("Using %s locale", locale.setlocale(locale.LC_CTYPE))
    logger.info("Startup LC_NUMERIC %s", locale.setlocale(locale.LC_NUMERIC))

    # Catch and log Python warnings
    logging.captureWarnings(True)

    # Suppress Warning: g_value_get_int: assertion 'G_VALUE_HOLDS_INT (value)' failed
    # from dialog.save.Save._meta_datetime_widget.set_text()
    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    return args


def main():
    "main"
    app = Application(cmdline=_parse_arguments())
    app.run()


if __name__ == "__main__":
    main()

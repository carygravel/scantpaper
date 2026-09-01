"scantpaper --- to aid the scan to PDF or DjVu process"

# TODO:
# use pathlib for all paths
# refactor methods using self.slist.clipboard
# refactor ocr & annotation manipulation into single class
# various improvements from StackOverflow
# add type hints and turn on type checks in tox.ini
# migrate to Gtk4
# remaining FIXMEs and TODOs

import argparse
import atexit
import gettext
import locale
import logging
import lzma
import pathlib
import re
import shutil
import sys
import warnings

# check for pyinstaller
if hasattr(sys, "frozen"):
    BASE_DIR = getattr(sys, "_MEIPASS", str(pathlib.Path(__file__).resolve().parent))
else:
    BASE_DIR = str(pathlib.Path(__file__).resolve().parent)
sys.path.insert(0, BASE_DIR)

# pylint: disable=wrong-import-position
import gi
from app_window import ApplicationWindow
from const import LOCAL_DOCS_URI, PROG_NAME, SPACE, VERSION
from i18n import log_i18n_status

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    Gio,
    Gtk,
)

# pylint: enable=wrong-import-position


class Application(Gtk.Application):
    "Application class"

    def __init__(self, *args, **kwargs):
        self.args = kwargs.pop("cmdline", None) or []
        super().__init__(
            *args,
            application_id="org.scantpaper",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
            **kwargs,
        )
        self.window = None

        # Add extra icons early to be available for Gtk.Builder
        # Check for icons in the package first, then fallback to system icons.
        iconpath = str((pathlib.Path(__file__).parent / "icons").resolve())
        if not pathlib.Path(iconpath).is_dir():
            iconpath = "/usr/share/scantpaper/icons"
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


def _handle_exception(exc_type, exc_value, exc_traceback):
    "handle uncaught exceptions by logging them"
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.getLogger().critical(
        "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = _handle_exception


def _parse_arguments():
    "parse command line arguments"
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description="A GUI to produce PDFs or DjVus from scanned documents",
        epilog=f"Please see {LOCAL_DOCS_URI} for more detail",
    )
    parser.add_argument("--device", action="extend", nargs="+")
    parser.add_argument("--import", action="extend", nargs="+", dest="import_files")
    parser.add_argument("--import-all", action="extend", nargs="+")
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
        args.log = str(pathlib.Path(args.log).resolve())
        if args.log_level is None:
            args.log_level = logging.DEBUG
        logging.basicConfig(filename=args.log, filemode="w", level=args.log_level)

        def compress_log():
            try:
                with (
                    pathlib.Path(args.log).open("rb") as f_in,
                    lzma.open(str(args.log) + ".xz", "wb") as f_out,
                ):
                    shutil.copyfileobj(f_in, f_out)
                pathlib.Path(args.log).unlink()
            except (OSError, lzma.LZMAError):
                logging.getLogger(__name__).exception("Failed to compress log")

        atexit.register(compress_log)
    else:
        if args.log_level is None:
            args.log_level = logging.WARNING
        logging.basicConfig(level=args.log_level)

    log_i18n_status()  # log the messages from i18n during import
    logger = logging.getLogger(__name__)
    logger.info("Starting %s %s", PROG_NAME, VERSION)
    logger.info("Called with %s", SPACE.join([sys.executable, *sys.argv]))

    # make sure argv has absolute paths in case we change directories
    # and then restart the program
    sys.argv = [
        str(pathlib.Path(path).resolve())
        for path in sys.argv
        if pathlib.Path(path).is_file()
    ]

    logger.info("Log level %s", args.log_level)
    if args.locale is None:
        gettext.bindtextdomain(f"{PROG_NAME}")
    elif re.search(r"^\/", args.locale, re.MULTILINE | re.DOTALL | re.VERBOSE):
        gettext.bindtextdomain(f"{PROG_NAME}", args.locale)
    else:
        gettext.bindtextdomain(
            f"{PROG_NAME}", str(pathlib.Path.cwd()) + f"/{args.locale}"
        )
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

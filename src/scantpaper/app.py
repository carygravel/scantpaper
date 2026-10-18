"""scantpaper --- to aid the scan to PDF or DjVu process."""

# Roadmap and wishlist:
# JBIG2 (G4) should threshold if necessary
# improve translations, including those in org.scantpaper.desktop.metainfo.xml
# look again at translating docs
# + scan profile viewer/editor
# + mutmut
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
from types import TracebackType
from typing import cast

# check for pyinstaller
if hasattr(sys, "frozen"):
    BASE_DIR = getattr(sys, "_MEIPASS", str(pathlib.Path(__file__).resolve().parent))
else:
    BASE_DIR = str(pathlib.Path(__file__).resolve().parent)

import gi

from scantpaper.app_window import ApplicationWindow
from scantpaper.const import LOCAL_DOCS_URI, PROG_NAME, SPACE, VERSION
from scantpaper.i18n import log_i18n_status

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    Gio,
    Gtk,
)


class Application(Gtk.Application):
    """Application class."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise Application."""
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
        iconpath = str((pathlib.Path(BASE_DIR) / "icons").resolve())
        if not pathlib.Path(iconpath).is_dir():
            iconpath = "/usr/share/scantpaper/icons"
        # GTK4: the icon theme is per-display (Gtk.IconTheme.get_default() and
        # prepend_search_path() are gone). Prepend the application's icon
        # directory, keeping the system search path.
        display = Gdk.Display.get_default()
        if display is not None:
            theme = Gtk.IconTheme.get_for_display(display)
            theme.set_search_path(
                [iconpath, *cast("list[str]", theme.get_search_path())]
            )

    def do_startup(self, *_args: object, **_kwargs: object) -> None:
        """Do startup."""
        Gtk.Application.do_startup(self)
        self._setup_accelerators()

    def _setup_accelerators(self) -> None:
        """Register the keyboard shortcuts formerly declared in the menu model.

        GTK4 does not honour ``accel`` attributes inside a GMenuModel, so the
        shortcuts are registered here against the window actions.
        """
        accels: dict[str, list[str]] = {
            "win.new": ["<Primary>n"],
            "win.open": ["<Primary>o"],
            "win.scan": ["<Primary>g"],
            "win.save": ["<Primary>s"],
            "win.email": ["<Primary>e"],
            "win.print": ["<Primary>p"],
            "win.quit": ["<Primary>q"],
            "win.undo": ["<Primary>z"],
            "win.redo": ["<Primary><Shift>z"],
            "win.cut": ["<Primary>x"],
            "win.copy": ["<Primary>c"],
            "win.paste": ["<Primary>v"],
            "win.select-all": ["<Primary>a"],
            "win.select-odd": ["<Primary>1"],
            "win.select-even": ["<Primary>2"],
            "win.select-invert": ["<Primary>i"],
            "win.select-blank": ["<Primary>b"],
            "win.select-dark": ["<Primary>d"],
            "win.select-modified": ["<Primary>m"],
            "win.zoom-in": ["plus"],
            "win.zoom-out": ["minus"],
            "win.rotate-90": ["<Primary><Shift>r"],
            "win.rotate-180": ["<Primary><Shift>f"],
            "win.rotate-270": ["<Primary><Shift>c"],
            "win.help": ["<Primary>h"],
        }
        for action, shortcuts in accels.items():
            self.set_accels_for_action(action, shortcuts)

    def do_activate(self, *_args: object, **_kwargs: object) -> None:
        """Only allow a single window and raise any existing ones."""
        # Windows are associated with the application
        # until the last one is closed and the application shuts down
        if not self.window:
            self.window = ApplicationWindow(application=self)
        self.window.present()


def _handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Handle uncaught exceptions by logging them."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.getLogger().critical(
        "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = _handle_exception


def _parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
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

        def compress_log() -> None:
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

    # captureWarnings() does not accept keyword arguments.
    logging.captureWarnings(True)  # noqa: FBT003

    # Suppress Warning: g_value_get_int: assertion 'G_VALUE_HOLDS_INT (value)' failed
    # from dialog.save.Save._meta_datetime_widget.set_text()
    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    return args


def main() -> None:
    """Run the application."""
    app = Application(cmdline=_parse_arguments())
    app.run()


if __name__ == "__main__":
    main()

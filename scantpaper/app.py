"main application"

# TODO:
# rotate icons wrong way round
# save_pdf landscape squashes into portrait
# fix TypeErrors when dragging edges of selection
# fix panning text layer
# fix editing text layer
# deleting last page produces TypeError
# saving a scan profile produced TypeError
# fix importing tiff
# save text for page without text produces: can only concatenate str (not "NoneType") to str
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

import os
import logging
from app_window import ApplicationWindow
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gtk,
    GdkPixbuf,
    Gio,
)

SIGMA_STEP = 0.1
MAX_SIGMA = 5
EDIT_TEXT = 200
BITS_PER_BYTE = 8
HELP_WINDOW_WIDTH = 800
HELP_WINDOW_HEIGHT = 600
HELP_WINDOW_DIVIDER_POS = 200

EMPTY = ""
DOT = "."
logger = logging.getLogger(__name__)


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
            self.iconpath = "/usr/share/gscan2pdf"
        else:
            self.iconpath = "icons"
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

    def do_startup(self, *args, **kwargs):
        Gtk.Application.do_startup(self)

    def do_activate(self, *args, **kwargs):
        "only allow a single window and raise any existing ones"

        # Windows are associated with the application
        # until the last one is closed and the application shuts down
        if not self.window:
            self.window = ApplicationWindow(application=self)
        self.window.present()

    def _init_icons(self, icons):
        "Initialise iconfactory"
        iconfactory = Gtk.IconFactory()
        for iconname, filename in icons:
            register_icon(iconfactory, iconname, self.iconpath + "/" + filename)
        iconfactory.add_default()


if __name__ == "__main__":
    app = Application()
    # app.run(sys.argv)
    app.run()

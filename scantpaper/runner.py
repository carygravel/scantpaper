"main file"

import sys
import os
import tempfile
import sqlite3
import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    GLib,
    Gio,
    Gtk,
    GdkPixbuf,
)
from imageview import ImageView, Dragger, Selector, SelectorDragger, Tool


class Document(Gtk.ListStore):
    """Subclass the model in order to hook in an SQLite DB"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with tempfile.NamedTemporaryFile(delete=False) as dbf:
            self.dbf = dbf
            self.dbcon = sqlite3.connect(self.dbf.name)
            logging.warning("Document created at %s", self.dbf.name)
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE thumbs(number INT, pixbuf BLOB NOT NULL)")
            self.dbcur.execute("CREATE TABLE pages(number INT, image BLOB NOT NULL)")

    def append_page(self, filename):
        """dump the image to the pages table and the pixbuf to the thumbs"""
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, 100, 100, False)
        page_num = self.iter_n_children() + 1
        logging.warning("Inserting page %s", page_num)
        self.append([page_num, pixbuf])

        with open(filename, "rb") as file:
            blob = file.read()
        self.dbcur.execute(
            "INSERT INTO thumbs (number, pixbuf) VALUES (?, ?)",
            (page_num, pixbuf.get_pixels()),
        )
        self.dbcur.execute(
            "INSERT INTO pages (number, image) VALUES (?, ?)", (page_num, blob)
        )

    def get_pixbuf(self, treeiter):
        """given an iter, return a (fullsize) pixbuf of the page"""
        page_num = self[treeiter][0]
        self.dbcur.execute("SELECT image FROM pages WHERE number = ?", (page_num,))
        blob = self.dbcur.fetchone()[0]
        loader = GdkPixbuf.PixbufLoader()
        loader.write(blob)
        loader.close()
        return loader.get_pixbuf()


@Gtk.Template(filename="scantpaper/window.ui")
class AppWindow(Gtk.ApplicationWindow):
    """Application Window"""

    __gtype_name__ = "appwindow"

    page_list = Gtk.Template.Child()
    image_widget = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.document = Document(int, GdkPixbuf.Pixbuf)
        self.page_list.append_column(
            Gtk.TreeViewColumn("#", Gtk.CellRendererText(), text=0)
        )
        self.page_list.append_column(
            Gtk.TreeViewColumn("thumb", Gtk.CellRendererPixbuf(), pixbuf=1)
        )
        self.page_list.set_headers_visible(False)
        self.page_list.set_model(self.document)

        def on_tree_selection_changed(selection):
            model, treeiter = selection.get_selected()
            if treeiter is not None:
                self.image_widget.set_pixbuf(model.get_pixbuf(treeiter))

        select = self.page_list.get_selection()
        select.connect("changed", on_tree_selection_changed)

        self.show_all()


class Application(Gtk.Application):
    """Application"""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="com.gitlab.scantpaper",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs,
        )
        self.window = None

        self.add_main_option(
            "test",
            ord("t"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Command line test",
            None,
        )

    def do_startup(self):
        """startup"""
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("open", None)
        action.connect("activate", self.on_open)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        builder = Gtk.Builder.new_from_file("scantpaper/menu.ui")
        self.set_app_menu(builder.get_object("app-menu"))

    def do_activate(self):
        """activate"""
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = AppWindow(application=self, title="ScantPaper")

        self.window.present()

    def do_command_line(self, command_line):
        """handle command line args"""
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if "test" in options:
            # This is printed on the main instance
            print(f"Test argument received: {options['test']}")

        self.activate()
        return 0

    def on_open(self, _action, _param):
        """open"""
        window = self.get_active_window()
        dialog = Gtk.FileChooserDialog(
            title="Open image", parent=window, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            window.document.append_page(dialog.get_filename())
        dialog.destroy()

    def on_about(self, _action, _param):
        """about"""
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, _action, _param):
        """quit"""
        window = self.get_active_window()
        document = window.page_list.get_model()
        logging.warning("Cleaning up document at %s", document.dbf.name)
        os.remove(document.dbf.name)
        self.quit()


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)

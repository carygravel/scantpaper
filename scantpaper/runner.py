""" main file """

import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    GLib,
    Gio,
    Gtk,
    GdkPixbuf,
)


@Gtk.Template(filename="scantpaper/window.ui")
class AppWindow(Gtk.ApplicationWindow):
    """Application Window"""

    __gtype_name__ = "appwindow"

    page_list = Gtk.Template.Child()
    image_widget = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.model = Gtk.ListStore(int, GdkPixbuf.Pixbuf)
        self.page_list.append_column(
            Gtk.TreeViewColumn("#", Gtk.CellRendererText(), text=0)
        )
        self.page_list.append_column(
            Gtk.TreeViewColumn("thumb", Gtk.CellRendererPixbuf(), pixbuf=1)
        )
        self.page_list.set_headers_visible(False)
        self.page_list.set_model(self.model)

        def on_tree_selection_changed(selection):
            model, treeiter = selection.get_selected()
            if treeiter is not None:
                self.image_widget.set_from_pixbuf(model[treeiter][1])

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
            print(f"Test argument recieved: {options['test']}")

        self.activate()
        return 0

    def on_open(self, _action, _param):
        """open"""
        window = self.get_active_window()
        model = window.model
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
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                dialog.get_filename(), 100, 100, False
            )
            model.append([1, pixbuf])
        dialog.destroy()

    def on_about(self, _action, _param):
        """about"""
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, _action, _param):
        """quit"""
        self.quit()


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)

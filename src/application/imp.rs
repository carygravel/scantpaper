use gio::SimpleAction;
use glib::clone;
use gtk::gdk_pixbuf::Pixbuf;
use gtk::prelude::*;
use gtk::subclass::prelude::*;
use gtk::{
    gio, glib, ApplicationWindow, Builder, CellRenderer, CellRendererPixbuf, CellRendererText,
    FileChooserDialog, Image, ListStore, TreeView, TreeViewColumn,
};
use once_cell::unsync::OnceCell;

#[derive(Debug, Default)]
pub struct SpApplication {
    window: OnceCell<ApplicationWindow>,
}

#[glib::object_subclass]
impl ObjectSubclass for SpApplication {
    const NAME: &'static str = "SpApplication";
    type Type = super::SpApplication;
    type ParentType = gtk::Application;
}

impl ObjectImpl for SpApplication {}

/// When our application starts, the `startup` signal will be fired.
/// This gives us a chance to perform initialisation tasks that are not directly
/// related to showing a new window. After this, depending on how
/// the application is started, either `activate` or `open` will be called next.
impl ApplicationImpl for SpApplication {
    /// `gio::Application::activate` is what gets called when the
    /// application is launched by the desktop environment and
    /// aksed to present itself.
    fn activate(&self) {
        let window = self
            .window
            .get()
            .expect("Should always be initiliazed in gio_application_startup");
        window.show_all();
        window.present();
    }

    /// `gio::Application` is bit special. It does not get initialized
    /// when `new` is called and the object created, but rather
    /// once the `startup` signal is emitted and the `gio::Application::startup`
    /// is called.
    ///
    /// Due to this, we create and initialize other widgets
    /// here. Widgets can't be created before `startup` has been called.
    fn startup(&self) {
        self.parent_startup();
        let app = self.obj();

        let ui = include_str!("../../resources/scantpaper.ui");
        let builder = Builder::from_string(ui);

        let window: ApplicationWindow =
            builder.object("appwindow").expect("Couldn't get appwindow");
        app.add_window(&window);
        self.window
            .set(window.clone())
            .expect("Failed to initialize application window");

        let image_widget: Image = builder
            .object("image_widget")
            .expect("Couldn't get image_widget");
        let page_list: TreeView = builder.object("page_list").expect("Couldn't get page_list");

        let app_menu: gio::MenuModel = builder.object("app-menu").expect("Couldn't get app-menu");
        app.set_app_menu(Some(&app_menu));

        let model = ListStore::new(&[u32::static_type(), Pixbuf::static_type()]);

        // Add action "open" to `app` taking no parameter
        let action_open = SimpleAction::new("open", None);
        action_open.connect_activate(clone!(@weak window, @weak model => move |_, _| {
            let file_chooser = FileChooserDialog::with_buttons(
                Some("Open image"),
                Some(&window),
                gtk::FileChooserAction::Open,
                &[
                    ("_Cancel", gtk::ResponseType::Cancel),
                    ("_Open", gtk::ResponseType::Accept),
                ]);
            file_chooser.connect_response(move |file_chooser, response| {
                if response == gtk::ResponseType::Accept {
                    let file = file_chooser.file().expect("Couldn't get file");
                    let filename = file.path().expect("Couldn't get file path");
                    let pixbuf = Pixbuf::from_file_at_scale(filename, 100, 100, false).expect("Error loading pixbuf");
                    model.insert_with_values(None, &[(0, &1), (1, &pixbuf)]);
                }
                file_chooser.close();
            });
            file_chooser.show();
        }));
        app.add_action(&action_open);

        // Add action "close" to `window` taking no parameter
        let action_close = SimpleAction::new("close", None);
        action_close.connect_activate(clone!(@weak window => move |_, _| {
            window.close();
        }));
        app.add_action(&action_close);

        app.set_accels_for_action("app.new", &["<Ctrl>N"]);
        app.set_accels_for_action("app.open", &["<Ctrl>O"]);
        app.set_accels_for_action("app.scan", &["<Ctrl>G"]);
        app.set_accels_for_action("app.save", &["<Ctrl>S"]);
        app.set_accels_for_action("app.email", &["<Ctrl>E"]);
        app.set_accels_for_action("app.print", &["<Ctrl>P"]);
        app.set_accels_for_action("app.close", &["<Ctrl>Q"]);

        fn append_column(tree: &TreeView, attribute: &str, id: i32) {
            let column = TreeViewColumn::new();
            let cell: CellRenderer = match attribute {
                "text" => CellRendererText::new().upcast::<CellRenderer>(),
                "pixbuf" => CellRendererPixbuf::new().upcast::<CellRenderer>(),
                _ => panic!("Unexpected attribute"),
            };
            TreeViewColumnExt::pack_start(&column, &cell, true);
            TreeViewColumnExt::add_attribute(&column, &cell, attribute, id);
            tree.append_column(&column);
        }

        // Setting the model into the view.
        append_column(&page_list, "text", 0);
        append_column(&page_list, "pixbuf", 1);
        page_list.set_model(Some(&model));
        page_list.connect_cursor_changed(clone!(@weak image_widget => move |tree_view| {
            let selection = tree_view.selection();
            if let Some((model, iter)) = selection.selected() {
                let pixbuf = model
                    .value(&iter, 1)
                    .get::<Pixbuf>()
                    .expect("Treeview selection, column 1");
                image_widget.set_from_pixbuf(Some(&pixbuf));
            }
        }));
        window.show_all();
    }
}

impl GtkApplicationImpl for SpApplication {}

mod imp;

use gio::ApplicationFlags;
use gtk::{gio, glib};

glib::wrapper! {
    pub struct SpApplication(ObjectSubclass<imp::SpApplication>)
        @extends gio::Application, gtk::Application, @implements gio::ActionMap;
}

impl SpApplication {
    #[allow(clippy::new_without_default)]
    pub fn new() -> Self {
        glib::Object::new(&[
            ("application-id", &"com.gitlab.scantpaper"),
            ("flags", &ApplicationFlags::empty()),
        ])
    }
}

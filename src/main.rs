pub mod application;

use gtk::prelude::*;

fn main() {
    gtk::init().expect("Failed to initialize gtk");
    application::SpApplication::new().run();
}

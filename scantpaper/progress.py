"HBox with progress bar and cancel button."

from i18n import _
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # pylint: disable=wrong-import-position


class Progress(Gtk.HBox):
    "HBox with progress bar and cancel button"

    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pbar = Gtk.ProgressBar()
        self._pbar.set_show_text(True)
        self.add(self._pbar)
        self._button = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        self._button.connect("clicked", self._on_button_clicked)
        self.pack_end(self._button, False, False, 0)

    def _on_button_clicked(self, _button):
        self.emit("clicked")

    def set_fraction(self, fraction):
        "Set progress bar fraction"
        self._pbar.set_fraction(fraction)

    def set_text(self, text):
        "Set progress bar text"
        self._pbar.set_text(text)

    def pulse(self):
        "Pulse progress bar"
        self._pbar.pulse()

"HBox with progress bar and cancel button."

import gi
from basethread import ResponseType
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position


class Progress(Gtk.Box):
    "HBox with progress bar and cancel button"

    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._signal = None
        self._pbar = Gtk.ProgressBar()
        self._pbar.set_show_text(True)
        self._pbar.set_hexpand(True)
        self.pack_start(self._pbar, True, True, 0)
        self._pbar.show()
        self._button = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        self._button.connect("clicked", self._on_button_clicked)
        self.pack_end(self._button, False, False, 0)
        self._button.show()

    def _on_button_clicked(self, _button):
        self.emit("clicked")

    def set_fraction(self, fraction):
        "Set progress bar fraction"
        self._pbar.set_fraction(min(1.0, max(0.0, fraction)))

    def set_text(self, text):
        "Set progress bar text"
        self._pbar.set_text(text)

    def pulse(self):
        "Pulse progress bar"
        self._pbar.pulse()

    def queued(self, response):  # , pid
        "Helper function to set up progress bar"
        process_name, num_completed, total = (
            response.request.process,
            response.num_completed_jobs,
            response.total_jobs,
        )
        if total and process_name is not None:
            self.set_text(
                _("Process %i of %i (%s)") % (num_completed + 1, total, process_name)
            )
            self.set_fraction(min(1.0, (num_completed + 0.5) / total))
            self.show()

            def cancel_process(_widget):
                """Pass the signal back to:
                1. be able to cancel it when the process has finished
                2. flag that the progress bar has been set up
                and avoid the race condition where the callback is
                entered before the num_completed and total variables have caught up"""
                # slist.cancel([pid])
                self.hide()

            self._signal = self.connect("clicked", cancel_process)

    def update(self, response):
        "Helper function to update progress bar"
        if not response:
            return
        if response.type == ResponseType.DATA:
            if isinstance(response.info, str):
                self.set_text(response.info)
                self.show()
                return
            if isinstance(response.info, float):
                self.set_fraction(response.info)
                self.show()
                return
            return
        if response.total_jobs:
            if response.request.process:
                self.set_text(
                    _("Process %i of %i (%s)")
                    % (
                        response.num_completed_jobs + 1,
                        response.total_jobs,
                        response.request.process,
                    )
                )
            else:
                self.set_text(
                    _("Process %i of %i")
                    % (response.num_completed_jobs + 1, response.total_jobs)
                )
            self.set_fraction(
                min(1.0, (response.num_completed_jobs + 0.5) / response.total_jobs)
            )
            self.show()

    def finish(self, response):
        "Helper function to hide progress bar and disconnect signals"
        if not response or not response.pending:
            self.hide()
        if self._signal is not None:
            self.disconnect(self._signal)
            self._signal = None

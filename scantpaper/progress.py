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
        self._signal = None
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
            self.set_fraction((num_completed + 0.5) / total)
            self.show_all()

            def cancel_process():
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
        if response and response.total_jobs:
            if response.request.process:
                # if  "message"  in options :
                #     options["process"] += f" - {options['message']}"
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

            # if  "progress"  in options :
            #     tpbar.set_fraction(
            #     ( options["jobs_completed"] + options["progress"] ) / options["jobs_total"] )
            # else :
            self.set_fraction((response.num_completed_jobs + 0.5) / response.total_jobs)
            self.show_all()

    def finish(self, response):
        "Helper function to hide progress bar and disconnect signals"
        if not response or not response.pending:
            self.hide()
        if self._signal is not None:
            self.disconnect(self._signal)

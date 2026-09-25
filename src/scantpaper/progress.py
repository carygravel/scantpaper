"""HBox with progress bar and cancel button."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.basethread import Response, ResponseType
from scantpaper.i18n import _

if TYPE_CHECKING:
    from typing import ClassVar

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    GObject,
    Gtk,
)

_PULSE_MIN_INTERVAL = 0.1  # seconds


class Progress(Gtk.Box):
    """HBox with progress bar and cancel button."""

    __gsignals__: ClassVar[dict] = {
        "clicked": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise Progress."""
        super().__init__(*args, **kwargs)
        self.cancel_callback = None
        self._signal = None
        self._last_pulse = 0.0
        self._pbar = Gtk.ProgressBar()
        self._pbar.set_show_text(True)
        self._pbar.set_hexpand(True)
        self.pack_start(self._pbar, expand=True, fill=True, padding=0)
        self._pbar.show()
        self._button = Gtk.Button.new_with_mnemonic(label=_("_Cancel"))
        self._button.connect("clicked", self._on_button_clicked)
        self.pack_end(self._button, expand=False, fill=False, padding=0)
        self._button.show()

    def _on_button_clicked(self, _button: Gtk.Button) -> None:
        self.emit("clicked")

    def set_fraction(self, fraction: float) -> None:
        """Set progress bar fraction."""
        self._pbar.set_fraction(min(1.0, max(0.0, fraction)))

    def set_text(self, text: str) -> None:
        """Set progress bar text."""
        self._pbar.set_text(text)

    def pulse(self) -> None:
        """Pulse progress bar."""
        now = time.monotonic()
        if now - self._last_pulse < _PULSE_MIN_INTERVAL:
            return
        self._last_pulse = now
        self._pbar.pulse()

    def queued(self, response: Response) -> None:  # , pid
        """Set up progress bar from queued response."""
        process_name, num_completed, total = (
            response.request.process,
            cast("int", response.num_completed_jobs),
            cast("int", response.total_jobs),
        )
        if total and cast("str | None", process_name) is not None:
            self.set_text(
                _("Process %i of %i (%s)") % (num_completed + 1, total, process_name)
            )
            self.set_fraction(min(1.0, (num_completed + 0.5) / total))
            self.show()

            def cancel_process(_widget: Gtk.Widget) -> None:
                """Pass the signal back.

                1. be able to cancel it when the process has finished
                2. flag that the progress bar has been set up
                and avoid the race condition where the callback is
                entered before the num_completed and total variables have caught up
                """
                if self.cancel_callback is not None:
                    self.cancel_callback()
                self.hide()

            self._signal = self.connect("clicked", cancel_process)

    def update(self, response: Response | None) -> None:
        """Update progress bar from response."""
        if not response:
            return
        if response.type == ResponseType.DATA:
            if isinstance(response.info, str):
                self.set_text(response.info)
                self.show()
            elif isinstance(response.info, float):
                self.set_fraction(response.info)
                self.show()
            return
        if response.total_jobs:
            if response.request.process:
                self.set_text(
                    _("Process %i of %i (%s)")
                    % (
                        cast("int", response.num_completed_jobs) + 1,
                        response.total_jobs,
                        response.request.process,
                    )
                )
            else:
                self.set_text(
                    _("Process %i of %i")
                    % (
                        cast("int", response.num_completed_jobs) + 1,
                        response.total_jobs,
                    )
                )
            self.set_fraction(
                min(
                    1.0,
                    (cast("float", response.num_completed_jobs) + 0.5)
                    / cast("float", response.total_jobs),
                )
            )
            self.show()

    def finish(self, response: Response | None) -> None:
        """Hide progress bar and disconnect signals."""
        if not response or not response.pending:
            self.hide()
        if self._signal is not None:
            self.disconnect(self._signal)
            self._signal = None

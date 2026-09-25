"""test scan dialog."""

from __future__ import annotations

import json
import logging
import pathlib
import tempfile
from typing import TYPE_CHECKING, cast

from scantpaper.config import read_config, write_config
from scantpaper.scanner.profile import Profile

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import SimpleNamespace

    import pytest
    from gi.repository import Gtk

    from scantpaper.dialog.sane import SaneScanDialog
    from scantpaper.loop_helpers import _MainLoopWrapper

logger = logging.getLogger(__name__)


def test_reloads_in_profile(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
    sane_scan_mocks: SimpleNamespace,
) -> None:
    """Given a profile of scan options that trigger multiple reloads.

    Check the changed-profile signal is only emitted once.
    """
    sane_scan_mocks.patch_all(mocker)
    dialog = sane_scan_dialog
    set_device_wait_reload(dialog, "mock_name")
    callbacks = 0
    loop = mainloop_with_timeout()

    def added_profile_cb(_widget: Gtk.Widget, name: str, _profile: object) -> None:
        assert name == "my profile", "added-profile signal emitted"
        nonlocal callbacks
        callbacks += 1

    dialog.connect("added-profile", added_profile_cb)
    dialog._add_profile(
        "my profile",
        Profile(
            backend=[
                ("br-x", 210.0),
                ("br-y", 297.0),
                ("source", "Automatic Document Feeder"),
                ("scan-area", "A4"),
                ("y-resolution", 150),
                ("x-resolution", 150),
                ("brightness", 10),
                ("contrast", 10),
            ]
        ),
    )

    def changed_profile_cb(_widget: Gtk.Widget, profile: str) -> None:
        assert profile == "my profile", "changed-profile"
        assert dict(
            cast("dict[str, object]", dialog.current_scan_options.get()["backend"])
        ) == {
            "y-resolution": 150,
            "source": "Automatic Document Feeder",
            "x-resolution": 150,
            "brightness": 10,
            "scan-area": "A4",
            "contrast": 10,
        }, "profile with multiple reloads; reverted br-x and br-y are dropped"
        loop.quit()
        nonlocal callbacks
        callbacks += 1

    dialog.connect("changed-profile", changed_profile_cb)
    dialog.profile = "my profile"
    loop.run()

    assert callbacks == 2, "changed-profile only called once"


def test_legacy_default_scan_options_applied_and_saved(
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """A backend-only legacy default-scan-options rc is applied and round-trips.

    Mirrors the startup path: read the config, hand the normalised default
    scan options to the dialog (as _reloaded_scan_options_callback does), then
    write the applied options back and check both profile keys survive.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        rc.write_text(
            '{"default-scan-options": '
            '{"backend": [{"mode": "Color"}, {"resolution": 600}]}}',
            encoding="utf-8",
        )
        settings = read_config(cast("str", rc))

        assert "frontend" in settings["default-scan-options"], (
            "legacy scan options gain a frontend key on load"
        )

        expected = Profile(backend=[("mode", "Color"), ("resolution", 600)])
        dialog = sane_scan_dialog
        set_device_wait_reload(dialog, "test:0")
        callbacks = 0
        settled = False
        loop = mainloop_with_timeout()

        def changed_current_scan_options_cb(
            _widget: Gtk.Widget, _profile: object, _uuid: str
        ) -> None:
            nonlocal callbacks, settled
            callbacks += 1
            # Setting mode makes the backend reload its options, which resets
            # the widgets to the device defaults before the profile finishes
            # applying. Wait for an emission where the profile has settled.
            if (
                dialog.current_scan_options == expected
                and dialog.option_widgets["resolution"].get_value() == 600
            ):
                settled = True
                loop.quit()

        dialog.connect("changed-current-scan-options", changed_current_scan_options_cb)
        # This is what scan_menu_item_mixins._reloaded_scan_options_callback
        # does.
        dialog.set_current_scan_options(Profile(settings["default-scan-options"]))
        loop.run()

        assert settled, (
            "profile application completed; got {} changed-current-scan-options "
            "emissions (current_scan_options={}, resolution={})".format(
                callbacks,
                dialog.current_scan_options.get(),
                dialog.option_widgets["resolution"].get_value(),
            )
        )
        assert dialog.current_scan_options == expected, (
            "stored options are the current scan options"
        )

        settings["default-scan-options"] = dialog.current_scan_options.get()
        write_config(cast("str", rc), settings)
        saved = json.loads(rc.read_text(encoding="utf-8"))
        assert set(saved["default-scan-options"]) == {"frontend", "backend"}, (
            "saved scan options keep both keys"
        )
        assert saved["default-scan-options"]["backend"] == [
            ["mode", "Color"],
            ["resolution", 600],
        ], "applied option values are written back"

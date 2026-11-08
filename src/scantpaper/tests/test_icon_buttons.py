"""Tests for identifiable buttons in the audited dialogs."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi
import pytest

from scantpaper.config import DEFAULTS
from scantpaper.dialog import Dialog
from scantpaper.dialog.preferences import PreferencesDialog
from scantpaper.dialog.save import Save
from scantpaper.dialog.scan import _build_profile_table
from scantpaper.helpers import icon_button, labelled_icon_button
from scantpaper.i18n import _
from scantpaper.scanner.profile import Profile

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from scantpaper.dialog.sane import SaneScanDialog
    from scantpaper.scanner.options import Options

AUDITED_ICONS = (
    "document-save-symbolic",
    "document-properties-symbolic",
    "edit-delete-symbolic",
    "list-add-symbolic",
    "list-remove-symbolic",
)


def _walk(widget: Gtk.Widget) -> Iterator[Gtk.Widget]:
    yield widget
    child = widget.get_first_child()
    while child is not None:
        yield from _walk(child)
        child = child.get_next_sibling()


def _icon_buttons(widget: Gtk.Widget) -> list[Gtk.Button]:
    return [
        w
        for w in _walk(widget)
        if type(w) is Gtk.Button and isinstance(w.get_child(), Gtk.Image)
    ]


def _labelled_parts(button: Gtk.Button) -> tuple[str, str]:
    box = cast("Gtk.Box", button.get_child())
    image = cast("Gtk.Image", box.get_first_child())
    label = cast("Gtk.Label", box.get_last_child())
    return cast("str", image.get_icon_name()), cast("str", label.get_text())


def _spy_accessible_names(mocker: pytest.MockerFixture) -> MagicMock:
    return cast("MagicMock", mocker.patch.object(Gtk.Button, "update_property"))


def _assert_accessible_names(update: MagicMock, expected: list[str]) -> None:
    assert [call.args[1][0] for call in update.call_args_list] == expected


def test_icon_button_sets_tooltip_and_accessible_name(
    mocker: pytest.MockerFixture,
) -> None:
    """The icon-only helper explains the action and names it for assistive tech."""
    update = _spy_accessible_names(mocker)
    button = icon_button("list-add-symbolic", "Add a paper size")

    assert button.get_tooltip_text() == "Add a paper size"
    image = cast("Gtk.Image", button.get_child())
    assert image.get_icon_name() == "list-add-symbolic"
    _assert_accessible_names(update, ["Add a paper size"])


def test_labelled_icon_button_shows_text_and_accessible_name(
    mocker: pytest.MockerFixture,
) -> None:
    """The labelled helper shows the word and names the button with it."""
    update = _spy_accessible_names(mocker)
    button = labelled_icon_button("document-properties-symbolic", "Edit")

    assert _labelled_parts(button) == ("document-properties-symbolic", "Edit")
    _assert_accessible_names(update, ["Edit"])


def test_scan_profile_buttons_are_labelled(sane_scan_dialog: SaneScanDialog) -> None:
    """Save, Edit and Delete show their words instead of only an icon."""
    frame = next(
        w
        for w in _walk(sane_scan_dialog)
        if isinstance(w, Gtk.Frame) and w.get_label() == _("Scan profiles")
    )
    buttons = [w for w in _walk(frame) if type(w) is Gtk.Button]

    assert [_labelled_parts(button) for button in buttons] == [
        ("document-save-symbolic", _("Save")),
        ("document-properties-symbolic", _("Edit")),
        ("edit-delete-symbolic", _("Delete")),
    ]


def test_paper_editor_buttons_have_tooltips(
    sane_scan_dialog: SaneScanDialog, mocker: pytest.MockerFixture
) -> None:
    """The add and remove buttons in Edit paper size explain themselves."""
    created: list[Dialog] = []

    class RecordingDialog(Dialog):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

    mocker.patch("scantpaper.dialog.scan.Dialog", RecordingDialog)
    update = _spy_accessible_names(mocker)

    sane_scan_dialog._edit_paper()

    assert len(created) == 1
    buttons = _icon_buttons(created[0])
    tooltips = [_("Add a paper size"), _("Remove the selected paper size")]
    assert [button.get_tooltip_text() for button in buttons] == tooltips
    _assert_accessible_names(update, tooltips)
    created[0].destroy()


def test_profile_row_delete_buttons_have_tooltips(
    mocker: pytest.MockerFixture,
) -> None:
    """Each option row's delete button names the option it removes."""

    class _Option:
        title = "Resolution"

    class _Options:
        def by_name(self, _name: str) -> _Option:
            return _Option()

    update = _spy_accessible_names(mocker)
    vbox = Gtk.Box()

    _build_profile_table(
        Profile(frontend={"paper": "A4"}, backend=[("resolution", 300)]),
        cast("Options", _Options()),
        vbox,
    )

    expected = [
        _("Remove %(option)s from the profile") % {"option": "Resolution"},
        _("Remove %(option)s from the profile") % {"option": "paper"},
    ]
    buttons = _icon_buttons(vbox)
    assert [button.get_tooltip_text() for button in buttons] == expected
    _assert_accessible_names(update, expected)


def test_preferences_add_tool_button_has_tooltip(
    mocker: pytest.MockerFixture,
) -> None:
    """The add button for user-defined tools explains itself."""
    settings = DEFAULTS.copy()
    settings["TMPDIR"] = "/tmp"
    update = _spy_accessible_names(mocker)

    dialog = PreferencesDialog(settings=settings)

    buttons = [
        button
        for button in _icon_buttons(dialog)
        if cast("Gtk.Image", button.get_child()).get_icon_name() == "list-add-symbolic"
    ]
    assert len(buttons) == 1
    assert buttons[0].get_tooltip_text() == _("Add a user-defined tool")
    _assert_accessible_names(update, [_("Add a user-defined tool")])


def test_save_calendar_button_has_tooltip(mocker: pytest.MockerFixture) -> None:
    """The calendar-edit button keeps its tooltip after the icon change."""
    update = _spy_accessible_names(mocker)
    dialog = Save(transient_for=Gtk.Window())

    button = next(
        button
        for button in _icon_buttons(dialog)
        if cast("Gtk.Image", button.get_child()).get_icon_name()
        == "document-properties-symbolic"
    )

    assert button.get_tooltip_text() == _("Select date with calendar")
    _assert_accessible_names(update, [_("Select date with calendar")])


def _theme_state(theme: Gtk.IconTheme) -> str:
    settings = Gtk.Settings.get_default()
    settings_name = (
        settings.get_property("gtk-icon-theme-name") if settings is not None else None
    )
    path = theme.get_search_path() or []
    return (
        f"theme={theme.get_theme_name()!r} settings={settings_name!r} "
        f"paths={len(path)} first={path[:2]}"
    )


def test_document_properties_icon_resolves() -> None:
    """The replacement edit icon exists in the test theme."""
    display = cast("Gdk.Display", Gdk.Display.get_default())
    theme = Gtk.IconTheme.get_for_display(display)

    state = _theme_state(theme)
    assert theme.has_icon("document-properties-symbolic"), state


@pytest.mark.parametrize("icon_name", AUDITED_ICONS)
def test_audited_icon_names_resolve(icon_name: str) -> None:
    """Every icon named by an audited button exists in the test theme."""
    display = cast("Gdk.Display", Gdk.Display.get_default())
    theme = Gtk.IconTheme.get_for_display(display)

    assert theme.has_icon(icon_name), f"{icon_name}: {_theme_state(theme)}"

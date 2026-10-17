"""Tests for dialog action button labels."""

from __future__ import annotations

import pathlib

from scantpaper.dialog import Dialog
from scantpaper.i18n import _


def _production_sources() -> list[pathlib.Path]:
    """Return every production Python source in the package."""
    return [
        path
        for path in sorted(pathlib.Path(__file__).parent.parent.rglob("*.py"))
        if "tests" not in path.parts
    ]


def _stock_id_offenders(paths: list[pathlib.Path]) -> list[str]:
    """Return file:line for every GTK stock ID used as a literal.

    GTK4 removed stock IDs, so a literal such as "gtk-close" is displayed
    verbatim as the button text.
    """
    offenders = []
    for path in paths:
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if '"gtk-' in line:
                offenders.append(f"{path.name}:{i}")
    return offenders


def test_no_stock_id_button_labels_in_production() -> None:
    """Production code must not use GTK stock IDs as button labels."""
    assert _stock_id_offenders(_production_sources()) == []


def test_stock_id_guard_detects_offenders(tmp_path: pathlib.Path) -> None:
    """The guard scanner recognises stock-ID literals (self-check)."""
    source = tmp_path / "fake.py"
    source.write_text('button = dialog.add_button("gtk-close", 0)\n')

    assert _stock_id_offenders([source]) == [f"{source.name}:1"]


def test_add_actions_buttons_carry_mnemonic_labels() -> None:
    """Dialog.add_actions passes labels through and keeps their mnemonics."""
    dialog = Dialog()
    buttons = dialog.add_actions(
        [(_("_OK"), lambda: None), (_("_Cancel"), lambda: None)]
    )

    assert [button.get_label() for button in buttons] == ["_OK", "_Cancel"]
    assert all(button.get_use_underline() for button in buttons), "mnemonics work"

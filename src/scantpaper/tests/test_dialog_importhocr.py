"""Tests for the hOCR import dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import gi

from scantpaper.dialog.importhocr import ImportHocrDialog

if TYPE_CHECKING:
    import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def test_import_hocr_dialog_starts_without_a_file() -> None:
    """The OK button is disabled until a file is chosen."""
    dialog = ImportHocrDialog(page_range="all", cwd="/tmp")

    assert dialog.page_range == "all"
    assert dialog._entry.get_text() == ""
    assert dialog._ok.get_sensitive() is False


def test_import_hocr_dialog_accepts_chosen_file(
    mocker: pytest.MockerFixture,
) -> None:
    """Choosing a file enables OK and passes the path and page range on."""
    on_accept = MagicMock()
    dialog = ImportHocrDialog(
        page_range="selected",
        cwd="/tmp",
        on_accept=on_accept,
    )
    mocker.patch(
        "scantpaper.dialog.importhocr.run_dialog",
        return_value=Gtk.ResponseType.OK,
    )
    mocker.patch(
        "scantpaper.dialog.importhocr.chooser_path",
        return_value="/tmp/page.hocr",
    )

    dialog._choose_file(MagicMock())

    assert dialog._entry.get_text() == "/tmp/page.hocr"
    assert dialog._ok.get_sensitive() is True

    dialog._accept()
    on_accept.assert_called_once_with("/tmp/page.hocr", "selected")


def test_import_hocr_dialog_accepts_without_callback(
    mocker: pytest.MockerFixture,
) -> None:
    """Accepting a file is harmless when no callback was supplied."""
    dialog = ImportHocrDialog()
    mocker.patch(
        "scantpaper.dialog.importhocr.run_dialog",
        return_value=Gtk.ResponseType.OK,
    )
    mocker.patch(
        "scantpaper.dialog.importhocr.chooser_path",
        return_value="/tmp/page.hocr",
    )

    dialog._choose_file(MagicMock())
    dialog._accept()

    assert dialog._entry.get_text() == "/tmp/page.hocr"


def test_import_hocr_dialog_rejects_empty_path() -> None:
    """Accepting without a chosen file does nothing."""
    on_accept = MagicMock()
    dialog = ImportHocrDialog(on_accept=on_accept)

    dialog._accept()

    on_accept.assert_not_called()
    assert dialog._ok.get_sensitive() is False


def test_import_hocr_dialog_cancel_keeps_ok_disabled(
    mocker: pytest.MockerFixture,
) -> None:
    """Cancelling the file chooser leaves the dialog without a file."""
    dialog = ImportHocrDialog()
    mocker.patch(
        "scantpaper.dialog.importhocr.run_dialog",
        return_value=Gtk.ResponseType.CANCEL,
    )

    dialog._choose_file(MagicMock())

    assert dialog._entry.get_text() == ""
    assert dialog._ok.get_sensitive() is False

"""End-to-end tests for the crashed-session lifecycle."""

from __future__ import annotations

import pathlib
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from scantpaper.docthread import DocThread
from scantpaper.document import Document
from scantpaper.file_menu_mixins import FileMenuMixins
from scantpaper.loop_helpers import safe_mainloop
from scantpaper.page import Page
from scantpaper.session_mixins import SessionMixins


class _DiscoveryWindow(SessionMixins):
    """Minimal host for the discovery helper."""

    def __init__(self) -> None:
        self.settings = {"TMPDIR": "/tmp"}
        self.session = None
        self._crashed_session_locks: list[object] = []


def _make_snapshot(path: pathlib.Path) -> None:
    """Create a valid session database with one page."""
    thread = DocThread(db=str(path))
    thread._write_tid = threading.get_native_id()
    thread.add_page(Page(image_object=Image.new("RGB", (10, 10), "white")))
    thread.quit()


def _restore(slist: Document, snapshot: pathlib.Path) -> None:
    """Restore a snapshot and wait for the async chain to finish."""
    loop = safe_mainloop(5000)
    finished = Mock(side_effect=lambda _response: loop.quit())
    errors = Mock()

    slist.restore_session(
        db=str(snapshot),
        error_callback=errors,
        finished_callback=finished,
    )
    loop.run()
    finished.assert_called_once()
    errors.assert_not_called()


def test_restore_consumes_snapshot_and_quit_cleans_temporary_session(
    tmp_path: pathlib.Path,
) -> None:
    """Restored work is temporary and is gone after a normal exit."""
    snapshot = tmp_path / "scantpaper-crashx.sdb"
    snapshot_dir = tmp_path / "scantpaper-crashx"
    snapshot_dir.mkdir()
    _make_snapshot(snapshot)

    current = tmp_path / "scantpaper-currentx"
    current.mkdir()
    slist = Document(dir=str(current), db=f"{current}.sdb")
    try:
        _restore(slist, snapshot)

        assert len(slist.data) == 1
        assert not snapshot.exists()
        assert not snapshot_dir.exists()
        assert slist.thread.db_is_temporary() is True

        # The normal quit path removes the current session directory and the
        # scratch database it now contains.
        slist.thread.quit()
        (current / "artifact").write_text("temporary", encoding="utf-8")
        cleanup = FileMenuMixins()
        cleanup.session = SimpleNamespace(name=str(current))
        cleanup._remove_session_files()
        assert not current.exists()
        assert not pathlib.Path(f"{current}.sdb").exists()

        discovery = _DiscoveryWindow()
        discovery.settings["TMPDIR"] = str(tmp_path)
        discovery.session = type("Session", (), {"name": str(current)})()
        assert discovery._find_crashed_sessions() == []
    finally:
        slist.thread.quit()


def test_restore_failure_leaves_snapshot(tmp_path: pathlib.Path) -> None:
    """A failed restore reports an error and leaves the snapshot in place."""
    snapshot = tmp_path / "scantpaper-brokenx.sdb"
    snapshot.write_text("not a database", encoding="utf-8")
    current = tmp_path / "scantpaper-currentx"
    current.mkdir()
    slist = Document(dir=str(current), db=f"{current}.sdb")
    loop = safe_mainloop(5000)
    errors = Mock(side_effect=lambda *_args: loop.quit())
    finished = Mock()

    try:
        slist.restore_session(
            db=str(snapshot),
            error_callback=errors,
            finished_callback=finished,
        )
        loop.run()
        errors.assert_called_once()
        finished.assert_not_called()
        assert snapshot.exists()
    finally:
        slist.thread.quit()


def test_crash_after_restore_offers_temporary_copy_once(
    tmp_path: pathlib.Path,
) -> None:
    """A crash after restore offers the temporary copy, not the snapshot."""
    snapshot = tmp_path / "scantpaper-crashx.sdb"
    snapshot_dir = tmp_path / "scantpaper-crashx"
    snapshot_dir.mkdir()
    _make_snapshot(snapshot)

    current = tmp_path / "scantpaper-currentx"
    current.mkdir()
    slist = Document(dir=str(current), db=f"{current}.sdb")
    try:
        _restore(slist, snapshot)
        assert not snapshot.exists()

        discovery = _DiscoveryWindow()
        discovery.settings["TMPDIR"] = str(tmp_path)
        discovery.session = type(
            "Session", (), {"name": str(tmp_path / "scantpaper-newxxxx")}
        )()
        crashed = discovery._find_crashed_sessions()
        try:
            assert crashed == [f"{current}.sdb"]
        finally:
            discovery._release_crashed_session_locks()
    finally:
        slist.thread.quit()

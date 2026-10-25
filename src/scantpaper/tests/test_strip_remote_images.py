"""Tests for dev/strip_remote_images.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "dev" / "strip_remote_images.py"


def _run(html: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the helper on ``html`` and return its result and rewritten text."""
    path = tmp_path / "documentation.html"
    path.write_text(html, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result, path.read_text(encoding="utf-8")


def test_remote_image_is_removed(tmp_path: Path) -> None:
    """Drop an image loaded from an https host."""
    html = '<p><img src="https://img.shields.io/badge.svg" alt="badge" /></p>\n'

    result, text = _run(html, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert text == "<p></p>\n"


def test_protocol_relative_image_is_removed(tmp_path: Path) -> None:
    """Drop an image loaded from a protocol-relative host."""
    html = '<img src="//example.com/image.png" alt="remote">\n'

    result, text = _run(html, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert text == "\n"


def test_local_image_is_kept(tmp_path: Path) -> None:
    """Leave a local image untouched."""
    html = '<img src="screenshot.png" alt="screenshot" />\n'

    result, text = _run(html, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert text == html


def test_missing_file_reports_an_error(tmp_path: Path) -> None:
    """Fail with an error when the file cannot be read."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "absent.html")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "error" in (result.stdout + result.stderr).lower()

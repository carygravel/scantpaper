"""Ensure shipped markdown files respect the max line-length convention.

Lintian fails the package build when a source file contains a line longer
than 512 characters. The OpenSpec change records are written by an LLM and
have historically produced unwrapped prose that trips this check, so guard
against regression here across all markdown files shipped in the source
package, excluding vendored/untracked directories.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MAX_LINE_LENGTH = 512

# Directories that are not part of the shipped source package.
_EXCLUDED_DIRS = {".git", ".opencode", "node_modules", ".pytest_cache"}


def test_markdown_line_length() -> None:
    """No shipped markdown line may exceed 512 characters."""
    long_lines = []

    for path in _iter_shipped_markdown():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if len(line) > MAX_LINE_LENGTH:
                long_lines.append(f"{path}:{lineno}: {len(line)} chars")

    assert not long_lines, (
        "Lines exceed the lintian max of 512 characters:\n" + "\n".join(long_lines)
    )


def test_markdown_line_length_detects_long_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The checker flags a markdown file containing an over-long line."""
    md_file = tmp_path / "long.md"
    md_file.write_text("x" * (MAX_LINE_LENGTH + 1) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        "scantpaper.tests.test_markdown_line_length._iter_shipped_markdown",
        lambda: [md_file],
    )
    with pytest.raises(AssertionError, match=r"long\.md"):
        test_markdown_line_length()


def _iter_shipped_markdown() -> Generator[Path, None, None]:
    return (
        path
        for path in REPO_ROOT.rglob("*.md")
        if not any(part in _EXCLUDED_DIRS for part in path.parts)
    )

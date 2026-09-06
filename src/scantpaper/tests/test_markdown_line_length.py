"""Ensure shipped markdown files respect the max line-length convention.

Lintian fails the package build when a source file contains a line longer
than 512 characters. The OpenSpec change records are written by an LLM and
have historically produced unwrapped prose that trips this check, so guard
against regression here across all markdown files shipped in the source
package, excluding vendored/untracked directories.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MAX_LINE_LENGTH = 512

# Directories that are not part of the shipped source package.
_EXCLUDED_DIRS = {".git", ".opencode", "node_modules", ".pytest_cache"}


def test_markdown_line_length():
    """No shipped markdown line may exceed 512 characters."""
    long_lines = []

    for path in _iter_shipped_markdown():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if len(line) > MAX_LINE_LENGTH:
                long_lines.append(f"{path}:{lineno}: {len(line)} chars")

    assert not long_lines, (
        "Lines exceed the lintian max of 512 characters:\n" + "\n".join(long_lines)
    )


def _iter_shipped_markdown():
    return (
        path
        for path in REPO_ROOT.rglob("*.md")
        if not any(part in _EXCLUDED_DIRS for part in path.parts)
    )

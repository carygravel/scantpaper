"""The packaging builds must pass the split approval ledger."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGING_FILES = (
    REPO_ROOT / "packaging" / "debian" / "rules",
    REPO_ROOT / "packaging" / "fedora" / "scantpaper.spec",
    REPO_ROOT / "packaging" / "opensuse" / "scantpaper.spec",
)


def test_packaging_uses_split_approval_ledger() -> None:
    """Every package build points compile_mo at po/approvals."""
    for path in PACKAGING_FILES:
        text = path.read_text(encoding="utf-8")
        assert "--approvals po/approvals" in text, path
        assert "translation-approvals.json" not in text, path


def test_packaging_generates_template_before_compiling() -> None:
    """The gitignored pot is regenerated inside the packaging build."""
    for path in PACKAGING_FILES:
        text = path.read_text(encoding="utf-8")
        assert "dev/generate_pot.py" in text, path
        assert text.index("dev/generate_pot.py") < text.index("dev/compile_mo.py"), path


def test_packaging_joins_metadata_after_compiling() -> None:
    """Every package build generates the installed metadata from the catalogs."""
    for path in PACKAGING_FILES:
        text = path.read_text(encoding="utf-8")
        assert "dev/join_metadata.py" in text, path
        assert "--mo" in text, path
        assert "--out-dir" in text, path
        assert text.index("dev/join_metadata.py") > text.index("dev/compile_mo.py"), (
            path
        )

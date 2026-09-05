"""Tests for compiling translation .po files."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_compile_po_files(tmp_path):
    """All .po files compile cleanly to .mo, as done in CI."""
    src = REPO_ROOT / "po"
    out = tmp_path / "locale"

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "dev" / "compile_mo.py"),
            "--src",
            str(src),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

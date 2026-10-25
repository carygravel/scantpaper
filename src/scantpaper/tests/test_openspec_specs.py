"""Validate the OpenSpec specs with the openspec CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OPENSPEC_DIR = REPO_ROOT / "openspec"
OPENSPEC = shutil.which("openspec")

pytestmark = pytest.mark.skipif(
    OPENSPEC is None or not OPENSPEC_DIR.is_dir(),
    reason="requires an openspec source tree and the openspec CLI",
)


def test_specs_validate_strictly() -> None:
    """Every spec passes `openspec validate --specs --strict`."""
    assert OPENSPEC is not None
    result = subprocess.run(
        [OPENSPEC, "validate", "--specs", "--strict", "--no-interactive"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

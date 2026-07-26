"Tests for AppStream metadata files"

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_appstream_validate():
    "Validate AppStream metadata with appstreamcli"
    filepath = REPO_ROOT / "org.scantpaper.desktop.metainfo.xml"

    result = subprocess.run(
        ["appstreamcli", "validate", "--no-net", str(filepath)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

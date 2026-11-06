"""CI must never carry a Launchpad or model credential."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
GATE = REPO_ROOT / "dev" / "translation_gate.py"

FORBIDDEN = (
    "LAUNCHPAD_TOKEN",
    "LAUNCHPAD_CONSUMER_KEY",
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "MISTRAL_API_KEY",
    "launchpadlib",
    "oauth_token",
)


def test_workflows_carry_no_launchpad_or_model_credential() -> None:
    """No workflow names a model key or a Launchpad token."""
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))
    )
    for forbidden in FORBIDDEN:
        assert forbidden not in text


def test_gate_validation_needs_no_environment() -> None:
    """Configuration validation runs with an empty credential environment."""
    result = subprocess.run(
        ["env", "-i", "PATH=/usr/bin:/bin", "python3", str(GATE), "validate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "valid:" in result.stdout

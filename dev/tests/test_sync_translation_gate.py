"""Tests for the OpenCode-to-gate sync in dev/sync_translation_gate.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
SYNC_PATH = DEV_DIR / "sync_translation_gate.py"

sys.path.insert(0, str(DEV_DIR))


def _load_sync() -> ModuleType:
    """Import dev/sync_translation_gate.py with its siblings."""
    spec = importlib.util.spec_from_file_location(
        "sync_translation_gate", str(SYNC_PATH)
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_translation_gate"] = module
    spec.loader.exec_module(module)
    return module


SYNC = _load_sync()


def _opencode(*, v2: bool = True) -> dict[str, object]:
    """Build an OpenCode config with three independent model families."""
    provider: dict[str, object] = {
        "package": "@opencode/ai/providers/openai-compatible",
        "settings": {"baseURL": "https://acme.example/v1"},
        "env": ["ACME_KEY"],
        "models": {},
    }
    if not v2:
        provider = {
            "npm": "@ai-sdk/openai-compatible",
            "api": "https://acme.example/v1",
            "env": ["ACME_KEY"],
            "models": {},
        }
    models = {
        "a": {
            "modelID": "a-model",
            "family": "family-a",
            "releaseDate": "2026-01-01",
            "cost": {"input": 1.0, "output": 2.0, "cache_read": 0.5},
            "limit": {"context": 1000, "output": 100},
        },
        "b": {
            "modelID": "b-model",
            "family": "family-b",
            "releaseDate": "2026-02-01",
        },
        "c": {
            "modelID": "c-model",
            "family": "family-c",
            "releaseDate": "2026-03-01",
        },
    }
    provider["models"] = models
    key = "providers" if v2 else "provider"
    return {key: {"acme": provider}}


def _roles(path: Path) -> Path:
    """Write a valid role policy."""
    path.write_text(
        json.dumps(
            {
                "proposers": ["acme/a", "acme/b"],
                "judge": "acme/c",
            }
        ),
        encoding="utf-8",
    )
    return path


def _write(path: Path, data: object) -> Path:
    """Write JSON data."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_jsonc_normaliser_keeps_comment_like_text_in_strings() -> None:
    """Comments and trailing commas outside strings are removed."""
    text = """
    {
      // a comment
      "url": "https://example.invalid/a//b",
      "items": [1, 2,],
      /* block */
    }
    """
    normalized = SYNC.normalise_jsonc(text)
    data = json.loads(normalized)
    assert data["url"] == "https://example.invalid/a//b"
    assert data["items"] == [1, 2]


def test_imports_v2_and_legacy_providers(tmp_path: Path) -> None:
    """Both provider table shapes produce a valid gate config."""
    roles = SYNC.load_roles(_roles(tmp_path / "roles.json"))
    for v2 in (True, False):
        config = SYNC.build_gate_config(_opencode(v2=v2), roles)
        deployments = config["deployments"]
        assert isinstance(deployments, dict)
        assert "acme/a" in deployments
        assert deployments["acme/a"]["cost"]["input"] == 1.0
        assert deployments["acme/a"]["limits"]["context"] == 1000


def test_legacy_release_date_is_used(tmp_path: Path) -> None:
    """The legacy release_date field supplies the revision."""
    data = _opencode(v2=False)
    providers = data["provider"]
    assert isinstance(providers, dict)
    models = providers["acme"]["models"]
    assert isinstance(models, dict)
    models["a"].pop("releaseDate")
    models["a"]["release_date"] = "2026-09-10"
    config = SYNC.build_gate_config(
        data, SYNC.load_roles(_roles(tmp_path / "roles.json"))
    )
    releases = config["releases"]
    assert isinstance(releases, dict)
    assert any(release.endswith("@2026-09-10") for release in releases)


def test_incompatible_provider_is_skipped(tmp_path: Path) -> None:
    """A non-OpenAI-compatible provider is not imported."""
    data = _opencode()
    providers = data["providers"]
    assert isinstance(providers, dict)
    providers["native"] = {
        "package": "@opencode/ai/providers/anthropic",
        "settings": {"baseURL": "https://native.example"},
        "env": ["NATIVE_KEY"],
        "models": {"x": {"family": "native"}},
    }
    config = SYNC.build_gate_config(
        data, SYNC.load_roles(_roles(tmp_path / "roles.json"))
    )
    deployments = config["deployments"]
    assert isinstance(deployments, dict)
    assert all(not key.startswith("native/") for key in deployments)


def test_literal_key_provider_is_skipped(tmp_path: Path) -> None:
    """A literal apiKey is never copied into the gate config."""
    data = _opencode()
    providers = data["providers"]
    assert isinstance(providers, dict)
    providers["leaky"] = {
        "package": "@opencode/ai/providers/openai-compatible",
        "settings": {
            "baseURL": "https://leaky.example",
            "apiKey": "super-secret-value",
        },
        "env": ["LEAKY_KEY"],
        "models": {"x": {"family": "leaky"}},
    }
    config = SYNC.build_gate_config(
        data, SYNC.load_roles(_roles(tmp_path / "roles.json"))
    )
    serialized = json.dumps(config)
    assert "super-secret-value" not in serialized
    assert "leaky/x" not in cast_dict(config["deployments"])


def cast_dict(value: object) -> dict[str, object]:
    """Narrow a JSON object for assertions."""
    assert isinstance(value, dict)
    return cast("dict[str, object]", value)


def test_reimport_preserves_manual_fields_and_force_replaces(
    tmp_path: Path,
) -> None:
    """A normal import keeps manual serving fields; --force replaces them."""
    roles = SYNC.load_roles(_roles(tmp_path / "roles.json"))
    first = SYNC.build_gate_config(_opencode(), roles)
    deployments = cast_dict(first["deployments"])
    manual = cast_dict(deployments["acme/a"])
    manual["quantization"] = "q4"
    manual["prompt_hash"] = "sha256:manual"
    manual["decoding"] = {"temperature": 0.5}

    second = SYNC.build_gate_config(_opencode(), roles, first)
    kept = cast_dict(cast_dict(second["deployments"])["acme/a"])
    assert kept["quantization"] == "q4"
    assert kept["prompt_hash"] == "sha256:manual"
    assert SYNC.serialise(second) == SYNC.serialise(
        SYNC.build_gate_config(_opencode(), roles, second)
    )

    forced = SYNC.build_gate_config(_opencode(), roles, first, force=True)
    replaced = cast_dict(cast_dict(forced["deployments"])["acme/a"])
    assert replaced["quantization"] == "unknown"
    assert replaced["prompt_hash"] == SYNC.PROMPT_HASH


def test_invalid_roles_are_rejected(tmp_path: Path) -> None:
    """A judge from a proposer family is refused before writing."""
    roles_path = tmp_path / "roles.json"
    roles_path.write_text(
        json.dumps({"proposers": ["acme/a", "acme/b"], "judge": "acme/a"}),
        encoding="utf-8",
    )
    with pytest.raises(SYNC.SyncError, match="judge family"):
        SYNC.build_gate_config(_opencode(), SYNC.load_roles(roles_path))


def test_cli_dry_run_and_apply(tmp_path: Path) -> None:
    """Dry run leaves the output alone; apply writes a valid config."""
    opencode = _write(tmp_path / "opencode.json", _opencode())
    roles = _roles(tmp_path / "roles.json")
    output = tmp_path / "translation-gate.json"
    args = [
        "--opencode",
        str(opencode),
        "--roles",
        str(roles),
        "--output",
        str(output),
        "--dry-run",
    ]
    assert SYNC.main(args) == 0
    assert not output.exists()
    assert SYNC.main([arg for arg in args if arg != "--dry-run"]) == 0
    assert output.exists()
    assert SYNC.load_config(output).deployments["acme/a"].cost is not None

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


def _api_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    """Write saved model, provider and integration responses."""
    models = {
        "data": [
            {
                "id": "deepseek-v4.1-flash",
                "modelID": "deepseek-v4.1-flash",
                "providerID": "opencode",
                "family": "deepseek-flash",
                "package": "@opencode/ai/providers/openai-compatible",
                "settings": {"baseURL": "https://opencode.ai/inference/openai/v1"},
                "headers": {"x-opencode-org-id": "org-1"},
                "time": {"released": 1788998400000},
                "cost": [
                    {
                        "input": 0.3,
                        "output": 1.2,
                        "cache": {"read": 0.006, "write": 0},
                    },
                    {
                        "tier": {"type": "context", "size": 272000},
                        "input": 0.6,
                        "output": 1.8,
                        "cache": {"read": 0.012, "write": 0},
                    },
                ],
                "limit": {"context": 1000000, "output": 384000},
                "status": "active",
                "enabled": True,
            },
            {
                "id": "qwen3.8-flash",
                "providerID": "opencode",
                "family": "qwen",
                "package": "@opencode/ai/providers/openai-compatible",
                "time": {"released": 1787702400000},
                "cost": [{"input": 0.15, "output": 0.47, "cache": {"read": 0}}],
                "limit": {"context": 256000, "output": 32768},
                "status": "active",
                "enabled": True,
            },
            {
                "id": "glm-5.3",
                "providerID": "opencode",
                "family": "glm",
                "package": "@opencode/ai/providers/openai-compatible",
                "time": {"released": 1786665600000},
                "cost": [{"input": 1.4, "output": 4.4, "cache": {"read": 0.26}}],
                "limit": {"context": 256000, "output": 32768},
                "status": "active",
                "enabled": True,
            },
            {
                "id": "native-gpt",
                "providerID": "opencode",
                "family": "gpt",
                "package": "@opencode/ai/providers/openai",
                "time": {"released": 1790640000000},
                "cost": [{"input": 2, "output": 10, "cache": {"read": 0.1}}],
                "limit": {"context": 200000, "output": 8192},
                "status": "active",
                "enabled": True,
            },
        ]
    }
    providers = {
        "data": [
            {
                "id": "opencode",
                "integrationID": "opencode",
                "package": "@opencode/ai/providers/openai-compatible",
                "settings": {"baseURL": "https://opencode.ai/inference/openai/v1"},
                "headers": {"x-opencode-org-id": "org-1"},
            }
        ]
    }
    integrations = tmp_path / "integrations"
    integrations.mkdir()
    _write(
        integrations / "opencode.json",
        {
            "data": {
                "id": "opencode",
                "methods": [
                    {"type": "key"},
                    {"type": "env", "names": ["OPENCODE_API_KEY"]},
                ],
            }
        },
    )
    models_path = _write(tmp_path / "models.json", models)
    providers_path = _write(tmp_path / "providers.json", providers)
    roles_path = tmp_path / "api-roles.json"
    roles_path.write_text(
        json.dumps(
            {
                "proposers": [
                    "opencode/deepseek-v4.1-flash",
                    "opencode/qwen3.8-flash",
                ],
                "judge": "opencode/glm-5.3",
            }
        ),
        encoding="utf-8",
    )
    return models_path, providers_path, integrations, roles_path


def test_api_import_maps_default_model_metadata(tmp_path: Path) -> None:
    """The API source maps identity, headers, cost tiers and limits."""
    models, providers, integrations, roles = _api_fixture(tmp_path)
    request = SYNC.ApiImportRequest(
        models=SYNC._object_list(SYNC._load_saved_payload(models), str(models)),
        providers=SYNC._object_list(
            SYNC._load_saved_payload(providers), str(providers)
        ),
        integrations=SYNC._load_integrations(integrations),
        roles=SYNC.load_roles(roles),
    )
    config = SYNC.build_gate_config_from_api(request)
    deployment = config["deployments"]["opencode/deepseek-v4.1-flash"]
    assert deployment["endpoint"] == (
        "https://opencode.ai/inference/openai/v1/chat/completions"
    )
    assert deployment["key_env"] == "OPENCODE_API_KEY"
    assert deployment["headers"] == {"x-opencode-org-id": "org-1"}
    assert deployment["cost"]["tiers"][0]["context"] == 272000
    assert deployment["limits"]["context"] == 1000000
    assert "opencode/native-gpt" not in config["deployments"]


def test_api_import_cli_is_offline_and_deterministic(tmp_path: Path) -> None:
    """Saved responses import without a server; a second run is identical."""
    models, providers, integrations, roles = _api_fixture(tmp_path)
    output = tmp_path / "gate.json"
    args = [
        "--from-api",
        "--models-json",
        str(models),
        "--providers-json",
        str(providers),
        "--integrations-json",
        str(integrations),
        "--roles",
        str(roles),
        "--output",
        str(output),
    ]
    assert SYNC.main([*args, "--dry-run"]) == 0
    assert not output.exists()
    assert SYNC.main(args) == 0
    first = output.read_text(encoding="utf-8")
    assert SYNC.main(args) == 0
    assert output.read_text(encoding="utf-8") == first


def test_oauth_only_provider_is_skipped_or_overridden(tmp_path: Path) -> None:
    """OAuth-only providers need an explicit key variable."""
    models, providers, integrations, roles = _api_fixture(tmp_path)
    integration_path = integrations / "opencode.json"
    integration_path.write_text(
        json.dumps(
            {
                "data": {
                    "id": "opencode",
                    "methods": [{"type": "oauth", "id": "device"}],
                }
            }
        ),
        encoding="utf-8",
    )
    request = SYNC.ApiImportRequest(
        models=SYNC._object_list(SYNC._load_saved_payload(models), str(models)),
        providers=SYNC._object_list(
            SYNC._load_saved_payload(providers), str(providers)
        ),
        integrations=SYNC._load_integrations(integrations),
        roles=SYNC.load_roles(roles),
    )
    with pytest.raises(SYNC.SyncError, match="no OpenAI-compatible"):
        SYNC.build_gate_config_from_api(request)

    overridden = SYNC.ApiImportRequest(
        models=request.models,
        providers=request.providers,
        integrations=request.integrations,
        roles=request.roles,
        key_env_overrides={"opencode": "OPENCODE_API_KEY"},
    )
    config = SYNC.build_gate_config_from_api(overridden)
    assert config["deployments"]["opencode/deepseek-v4.1-flash"]["key_env"] == (
        "OPENCODE_API_KEY"
    )


def test_authorization_headers_are_not_copied(tmp_path: Path) -> None:
    """A catalog Authorization header never reaches the local config."""
    models, providers, integrations, roles = _api_fixture(tmp_path)
    provider_payload = SYNC._load_saved_payload(providers)
    assert isinstance(provider_payload, list)
    provider_payload[0]["headers"]["Authorization"] = "secret"
    providers.write_text(json.dumps({"data": provider_payload}), encoding="utf-8")
    config = SYNC.build_gate_config_from_api(
        SYNC.ApiImportRequest(
            models=SYNC._object_list(SYNC._load_saved_payload(models), str(models)),
            providers=SYNC._object_list(provider_payload, str(providers)),
            integrations=SYNC._load_integrations(integrations),
            roles=SYNC.load_roles(roles),
        )
    )
    assert (
        "Authorization"
        not in config["deployments"]["opencode/deepseek-v4.1-flash"]["headers"]
    )
    assert "secret" not in json.dumps(config)


def test_api_source_invokes_the_opencode_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live source calls the documented OpenCode API routes."""
    models, providers, integrations, roles = _api_fixture(tmp_path)
    model_data = SYNC._load_saved_payload(models)
    provider_data = SYNC._load_saved_payload(providers)
    integration_data = SYNC._load_saved_payload(integrations / "opencode.json")
    calls: list[str] = []

    class FakeResult:
        returncode = 0
        stderr = ""

        def __init__(self, payload: object) -> None:
            self.stdout = json.dumps({"data": payload})

    def fake_run(command: list[str], **_kwargs: object) -> FakeResult:
        path = command[-1]
        calls.append(path)
        if path == "/api/model":
            return FakeResult(model_data)
        if path == "/api/provider":
            return FakeResult(provider_data)
        return FakeResult(integration_data)

    monkeypatch.setattr(SYNC.subprocess, "run", fake_run)
    output = tmp_path / "gate.json"
    status = SYNC.main(
        [
            "--from-api",
            "--roles",
            str(roles),
            "--output",
            str(output),
        ]
    )
    assert status == 0
    assert output.exists()
    assert "/api/model" in calls
    assert "/api/provider" in calls
    assert "/api/integration/opencode" in calls


def test_missing_api_response_writes_nothing(tmp_path: Path) -> None:
    """An unreadable saved response fails before writing."""
    output = tmp_path / "gate.json"
    status = SYNC.main(
        [
            "--from-api",
            "--models-json",
            str(tmp_path / "missing.json"),
            "--providers-json",
            str(tmp_path / "also-missing.json"),
            "--output",
            str(output),
        ]
    )
    assert status == 1
    assert not output.exists()

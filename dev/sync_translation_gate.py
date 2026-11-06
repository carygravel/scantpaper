"""Generate or update the gate config from an OpenCode configuration.

OpenCode already describes OpenAI-compatible providers, model families,
release dates, token limits and prices. This tool imports those facts into
``po/translation-gate.json`` and leaves the independence roles to
``po/translation-gate.roles.json``.

A normal import preserves existing thresholds and hand-edited deployment
fields. ``--force`` replaces the deployment fields, ``--dry-run`` prints the
diff, and the result is validated with the gate loader before writing. A
literal API key in the OpenCode config is never copied; a provider without an
environment variable name is skipped.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, cast

from translation_gate import (
    DEFAULT_CONFIG,
    DEFAULT_ROLES,
    PROMPT_HASH,
    GateConfig,
    GateError,
    RolePolicy,
    load_config,
    load_roles,
    validate_roles,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THRESHOLDS = {
    "qualification": 0.8,
    "drift": 0.75,
    "defect_rate": 0.05,
    "sample_size": 20.0,
    "backtranslation": 0.6,
    "chars_per_token": 4.0,
}
OPENCODE_NAMES = ("opencode.jsonc", "opencode.json")
API_MODEL_PATH = "/api/model"
API_PROVIDER_PATH = "/api/provider"
SECRET_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie"}


class SyncError(Exception):
    """An OpenCode config that cannot be imported safely."""


def _copy_string(text: str, index: int, result: list[str]) -> int:
    """Copy one JSON string literal, including escapes, and return its end."""
    result.append('"')
    index += 1
    while index < len(text):
        char = text[index]
        result.append(char)
        if char == "\\":
            index += 1
            if index < len(text):
                result.append(text[index])
        elif char == '"':
            return index + 1
        index += 1
    return index


def _strip_comments(text: str) -> str:
    """Remove JSONC comments outside strings."""
    result: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            index = _copy_string(text, index, result)
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            index = text.find("\n", index)
            if index == -1:
                break
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            if end == -1:
                msg = "unterminated JSONC comment"
                raise SyncError(msg)
            index = end + 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _strip_trailing_commas(text: str) -> str:
    """Remove commas that directly precede a closing bracket or brace."""
    result: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            index = _copy_string(text, index, result)
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue
        result.append(char)
        index += 1
    return "".join(result)


def normalise_jsonc(text: str) -> str:
    """Remove JSONC comments and trailing commas outside strings."""
    return _strip_trailing_commas(_strip_comments(text))


def load_opencode(path: Path) -> dict[str, object]:
    """Load an OpenCode JSON or JSONC config."""
    try:
        text = path.read_text(encoding="utf-8")
        normalized = normalise_jsonc(text)
        data = json.loads(normalized)
    except (OSError, json.JSONDecodeError, SyncError) as error:
        msg = f"cannot read OpenCode config {path}: {error}"
        raise SyncError(msg) from error
    if not isinstance(data, dict):
        msg = f"{path} is not a JSON object"
        raise SyncError(msg)
    return cast("dict[str, object]", data)


def find_opencode(explicit: Path | None) -> Path:
    """Return the explicit OpenCode config or the first standard one found."""
    if explicit is not None:
        return explicit
    candidates = [
        *(Path.cwd() / name for name in OPENCODE_NAMES),
        *(Path.cwd() / ".opencode" / name for name in OPENCODE_NAMES),
        *(Path.home() / ".config" / "opencode" / name for name in OPENCODE_NAMES),
        *(Path("/etc/opencode") / name for name in OPENCODE_NAMES),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    msg = "no OpenCode config found; pass --opencode"
    raise SyncError(msg)


def _provider_table(data: Mapping[str, object]) -> Mapping[str, object]:
    """Return the V2 or legacy provider table."""
    table = data.get("providers", data.get("provider"))
    if not isinstance(table, dict):
        msg = "OpenCode config has no providers/provider table"
        raise SyncError(msg)
    return cast("Mapping[str, object]", table)


def _package_name(provider: Mapping[str, object]) -> str:
    """Return the runtime package name for a provider."""
    package = provider.get("package", provider.get("npm"))
    if not isinstance(package, str) or not package:
        msg = "provider has no package"
        raise SyncError(msg)
    return package


def _base_url(provider: Mapping[str, object]) -> str:
    """Return a provider's base URL."""
    settings = provider.get("settings")
    if isinstance(settings, dict):
        base = settings.get("baseURL")
        if isinstance(base, str) and base:
            return base
    api = provider.get("api")
    if isinstance(api, str) and api:
        return api
    msg = "provider has no base URL"
    raise SyncError(msg)


def _endpoint(base_url: str) -> str:
    """Return an OpenAI-compatible chat-completions endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _environment(provider: Mapping[str, object]) -> str:
    """Return the first credential environment variable name."""
    env = provider.get("env")
    if not isinstance(env, list):
        msg = "provider has no env list"
        raise SyncError(msg)
    for name in env:
        if isinstance(name, str) and name:
            return name
    msg = "provider has no non-empty env name"
    raise SyncError(msg)


def _has_literal_secret(provider: Mapping[str, object]) -> bool:
    """Return whether a provider embeds a literal credential."""
    settings = provider.get("settings")
    if isinstance(settings, dict):
        value = settings.get("apiKey")
        if isinstance(value, str) and value:
            return True
    options = provider.get("options")
    if isinstance(options, dict):
        value = options.get("apiKey")
        if isinstance(value, str) and value:
            return True
    headers = provider.get("headers")
    if isinstance(headers, dict):
        for key, value in headers.items():
            if (
                isinstance(key, str)
                and key.lower() == "authorization"
                and isinstance(value, str)
                and value
            ):
                return True
    return False


def _cost(model: Mapping[str, object]) -> dict[str, object] | None:
    """Map an OpenCode model cost block to the gate cost block."""
    raw = model.get("cost")
    if not isinstance(raw, dict):
        return None
    cost: dict[str, object] = {
        "currency": "USD",
        "unit": "per_million_tokens",
    }
    for name in ("input", "output", "cache_read", "cache_write"):
        value = raw.get(name)
        if isinstance(value, int | float) and not isinstance(value, bool):
            cost[name] = float(value)
    if any(name in cost for name in ("input", "output", "cache_read", "cache_write")):
        return cost
    return None


def _limits(model: Mapping[str, object]) -> dict[str, int] | None:
    """Map an OpenCode model limit block to the gate limits block."""
    raw = model.get("limit")
    if not isinstance(raw, dict):
        return None
    limits: dict[str, int] = {}
    for name in ("context", "output"):
        value = raw.get(name)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            limits[name] = value
    return limits or None


def _model_record(
    provider_id: str,
    model_key: str,
    model: Mapping[str, object],
    endpoint: str,
    key_env: str,
) -> dict[str, object] | None:
    """Map one OpenCode model to an import record."""
    model_id = model.get("modelID", model_key)
    if not isinstance(model_id, str) or not model_id:
        return None
    family = model.get("family", provider_id)
    if not isinstance(family, str) or not family:
        family = provider_id
    revision = model.get("releaseDate", model.get("release_date"))
    if not isinstance(revision, str) or not revision:
        digest = hashlib.sha256(model_id.encode()).hexdigest()[:8]
        revision = f"unknown-{digest}"
    return {
        "provider": provider_id,
        "model_key": model_key,
        "model": model_id,
        "family": family,
        "revision": revision,
        "endpoint": endpoint,
        "key_env": key_env,
        "cost": _cost(model),
        "limits": _limits(model),
    }


def _provider_records(
    provider_id: str,
    provider: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    """Return model records and skips for one provider."""
    try:
        package = _package_name(provider)
    except SyncError as error:
        return [], [f"{provider_id}: {error}"]
    if "openai-compatible" not in package and "openai" not in package:
        return [], [f"{provider_id}: not OpenAI-compatible ({package})"]
    if _has_literal_secret(provider):
        return [], [f"{provider_id}: literal credential refused"]
    try:
        endpoint = _endpoint(_base_url(provider))
        key_env = _environment(provider)
    except SyncError as error:
        return [], [f"{provider_id}: {error}"]
    models = provider.get("models")
    if not isinstance(models, dict):
        return [], [f"{provider_id}: no models"]
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    for model_key, model in models.items():
        if not isinstance(model_key, str) or not isinstance(model, dict):
            skipped.append(f"{provider_id}: malformed model")
            continue
        record = _model_record(provider_id, model_key, model, endpoint, key_env)
        if record is None:
            skipped.append(f"{provider_id}/{model_key}: no model id")
        else:
            records.append(record)
    return records, skipped


def _model_entries(
    providers: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    """Return imported model records and skip reasons."""
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    for provider_id, provider in providers.items():
        if not isinstance(provider, dict):
            skipped.append("malformed provider")
            continue
        provider_records, provider_skips = _provider_records(provider_id, provider)
        records.extend(provider_records)
        skipped.extend(provider_skips)
    return records, skipped


def _api_payload(path: str) -> object:
    """Run `opencode api get` and return its parsed data."""
    result = subprocess.run(
        ["opencode", "api", "get", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"opencode api get {path} failed: {result.stderr.strip()}"
        raise SyncError(msg)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        msg = f"opencode api get {path} returned unreadable JSON: {error}"
        raise SyncError(msg) from error
    if not isinstance(payload, dict) or "data" not in payload:
        msg = f"opencode api get {path} returned no data"
        raise SyncError(msg)
    return payload["data"]


def _load_saved_payload(path: Path) -> object:
    """Load a saved API response or a bare list."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read saved response {path}: {error}"
        raise SyncError(msg) from error
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _object_list(value: object, where: str) -> list[dict[str, object]]:
    """Validate a list of JSON objects."""
    if not isinstance(value, list):
        msg = f"{where} is not a list"
        raise SyncError(msg)
    return [cast("dict[str, object]", item) for item in value if isinstance(item, dict)]


def _load_integrations(path: Path | None) -> dict[str, dict[str, object]]:
    """Load saved integration responses keyed by integration id."""
    if path is None:
        return {}
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    integrations: dict[str, dict[str, object]] = {}
    for file_path in files:
        payload = _load_saved_payload(file_path)
        items = payload if isinstance(payload, list) else [payload]
        for item in _object_list(items, str(file_path)):
            integration_id = item.get("id")
            if isinstance(integration_id, str):
                integrations[integration_id] = item
    return integrations


def _integration_env(integration: Mapping[str, object] | None) -> str | None:
    """Return the first environment variable name declared by an integration."""
    if integration is None:
        return None
    methods = integration.get("methods")
    if not isinstance(methods, list):
        return None
    for method in methods:
        if not isinstance(method, dict) or method.get("type") != "env":
            continue
        names = method.get("names")
        if not isinstance(names, list):
            continue
        for name in names:
            if isinstance(name, str) and name:
                return name
    return None


def _api_price_block(raw: Mapping[str, object]) -> dict[str, object]:
    """Map one OpenCode cost entry to gate price fields."""
    block: dict[str, object] = {}
    for source, target in (("input", "input"), ("output", "output")):
        value = raw.get(source)
        if isinstance(value, int | float) and not isinstance(value, bool):
            block[target] = float(value)
    cache = raw.get("cache")
    if isinstance(cache, dict):
        read = cache.get("read")
        write = cache.get("write")
        if isinstance(read, int | float) and not isinstance(read, bool):
            block["cache_read"] = float(read)
        if isinstance(write, int | float) and not isinstance(write, bool):
            block["cache_write"] = float(write)
    return block


def _api_cost(model: Mapping[str, object]) -> dict[str, object] | None:
    """Map an OpenCode cost array to a base price and context tiers."""
    raw = model.get("cost")
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
        return None
    base = _api_price_block(cast("dict[str, object]", raw[0]))
    cost: dict[str, object] = {
        "currency": "USD",
        "unit": "per_million_tokens",
        **base,
    }
    tiers: list[dict[str, object]] = []
    for item in raw[1:]:
        if not isinstance(item, dict):
            continue
        tier = item.get("tier")
        if not isinstance(tier, dict) or tier.get("type") != "context":
            continue
        size = tier.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            continue
        tiers.append({"context": size, **_api_price_block(item)})
    if tiers:
        cost["tiers"] = tiers
    price_fields = {"input", "output", "cache_read", "cache_write"}
    if not (price_fields & set(cost)) and not tiers:
        return None
    return cost


def _api_limits(model: Mapping[str, object]) -> dict[str, int] | None:
    """Map an OpenCode limit block to gate limits."""
    raw = model.get("limit")
    if not isinstance(raw, dict):
        return None
    limits: dict[str, int] = {}
    for name in ("context", "output"):
        value = raw.get(name)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            limits[name] = value
    return limits or None


def _api_revision(model: Mapping[str, object]) -> str:
    """Return a release date or a short model hash."""
    time_block = model.get("time")
    released = time_block.get("released") if isinstance(time_block, dict) else None
    if isinstance(released, int) and not isinstance(released, bool) and released > 0:
        moment = datetime.fromtimestamp(released / 1000, tz=timezone.utc)
        return moment.date().isoformat()
    model_id = model.get("modelID", model.get("id", ""))
    return f"unknown-{hashlib.sha256(str(model_id).encode()).hexdigest()[:8]}"


def _safe_headers(
    provider: Mapping[str, object], model: Mapping[str, object]
) -> dict[str, str] | None:
    """Merge provider and model metadata headers, excluding credentials."""
    headers: dict[str, str] = {}
    for source in (provider.get("headers"), model.get("headers")):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            if key.lower() in SECRET_HEADERS:
                continue
            headers[key] = value
    return headers or None


def _api_base_url(
    model: Mapping[str, object], provider: Mapping[str, object]
) -> str | None:
    """Return the model or provider base URL."""
    settings = model.get("settings")
    base_url = settings.get("baseURL") if isinstance(settings, dict) else None
    if isinstance(base_url, str) and base_url:
        return base_url
    provider_settings = provider.get("settings")
    provider_url = (
        provider_settings.get("baseURL")
        if isinstance(provider_settings, dict)
        else None
    )
    return provider_url if isinstance(provider_url, str) and provider_url else None


def _api_key_env(
    provider_id: str,
    provider: Mapping[str, object],
    integrations: Mapping[str, dict[str, object]],
    overrides: Mapping[str, str],
) -> str | None:
    """Resolve a provider's credential variable, without reading its value."""
    override = overrides.get(provider_id)
    if override is not None:
        return override
    integration_id = provider.get("integrationID", provider_id)
    return _integration_env(integrations.get(str(integration_id)))


def _api_identity(
    model: Mapping[str, object], provider_id: str
) -> tuple[str, str] | None:
    """Return model id and family, or None when the model id is unusable."""
    model_id = model.get("modelID", model.get("id"))
    if not isinstance(model_id, str) or not model_id:
        return None
    family = model.get("family", provider_id)
    if not isinstance(family, str) or not family:
        family = provider_id
    return model_id, family


def _api_record(
    model: Mapping[str, object],
    provider_id: str,
    provider: Mapping[str, object],
    integrations: Mapping[str, dict[str, object]],
    overrides: Mapping[str, str],
) -> tuple[dict[str, object] | None, str | None]:
    """Map one API model, returning a record or a skip reason."""
    model_key = model.get("id", "")
    reason: str | None = None
    if not isinstance(model_key, str) or not model_key:
        reason = "malformed API model"
    elif not isinstance(
        model.get("package", provider.get("package")), str
    ) or "openai-compatible" not in str(model.get("package", provider.get("package"))):
        reason = f"{provider_id}/{model_key}: not OpenAI-compatible"
    elif model.get("enabled") is False or model.get("status") == "deprecated":
        reason = f"{provider_id}/{model_key}: disabled or deprecated"
    else:
        base_url = _api_base_url(model, provider)
        key_env = _api_key_env(provider_id, provider, integrations, overrides)
        identity = _api_identity(model, provider_id)
        if base_url is None:
            reason = f"{provider_id}/{model_key}: no base URL"
        elif key_env is None or key_env == "":
            reason = f"{provider_id}/{model_key}: no environment credential"
        elif identity is None:
            reason = f"{provider_id}/{model_key}: no model id"
        else:
            model_id, family = identity
            return (
                {
                    "provider": provider_id,
                    "model_key": model_key,
                    "model": model_id,
                    "family": family,
                    "revision": _api_revision(model),
                    "endpoint": _endpoint(base_url),
                    "key_env": key_env,
                    "cost": _api_cost(model),
                    "limits": _api_limits(model),
                    "headers": _safe_headers(provider, model),
                },
                None,
            )
    return None, reason


def _api_records(
    models: list[dict[str, object]],
    providers: list[dict[str, object]],
    integrations: Mapping[str, dict[str, object]],
    provider_filter: set[str],
    key_env_overrides: Mapping[str, str],
) -> tuple[list[dict[str, object]], list[str]]:
    """Map resolved OpenCode models to import records."""
    providers_by_id = {
        provider["id"]: provider
        for provider in providers
        if isinstance(provider.get("id"), str)
    }
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    for model in models:
        provider_id = model.get("providerID")
        if not isinstance(provider_id, str):
            skipped.append("malformed API model")
            continue
        if provider_filter and provider_id not in provider_filter:
            continue
        record, reason = _api_record(
            model,
            provider_id,
            providers_by_id.get(provider_id, {}),
            integrations,
            key_env_overrides,
        )
        if record is not None:
            records.append(record)
        elif reason is not None:
            skipped.append(reason)
    return records, skipped


def _assemble_gate_config(
    records: list[dict[str, object]],
    skipped: list[str],
    roles: RolePolicy,
    existing: Mapping[str, object] | None,
    *,
    force: bool,
) -> dict[str, object]:
    """Merge import records into a validated gate config."""
    if not records:
        msg = "no OpenAI-compatible models found: " + "; ".join(skipped)
        raise SyncError(msg)
    base: dict[str, object] = dict(existing) if existing is not None else {}
    releases = dict(cast("dict[str, object]", base.get("releases", {})))
    deployments = dict(cast("dict[str, object]", base.get("deployments", {})))
    existing_deployments = {
        key: value for key, value in deployments.items() if isinstance(value, dict)
    }

    role_ids = set(roles.proposers) | {roles.judge}
    imported_ids: set[str] = set()
    for record in records:
        deployment_id = _deployment_id(record)
        imported_ids.add(deployment_id)
        releases[_release_id(record)] = {
            "family": record["family"],
            "model": record["model"],
            "revision": record["revision"],
        }
        deployments[deployment_id] = _deployment_from_record(
            record,
            roles,
            existing_deployments.get(deployment_id, {}),
            force=force,
        )

    base["version"] = 1
    base.setdefault("thresholds", dict(DEFAULT_THRESHOLDS))
    base["releases"] = releases
    base["deployments"] = deployments
    for deployment_id, deployment in deployments.items():
        if deployment_id in imported_ids or not isinstance(deployment, dict):
            continue
        if deployment_id in role_ids:
            deployment["proposer"] = deployment_id in roles.proposers
            deployment["judge"] = deployment_id == roles.judge

    config = _validate(base)
    validate_roles(config, roles)
    if skipped:
        print("skipped: " + "; ".join(skipped), file=sys.stderr)
    return base


def build_gate_config(
    opencode: Mapping[str, object],
    roles: RolePolicy,
    existing: Mapping[str, object] | None = None,
    *,
    force: bool = False,
) -> dict[str, object]:
    """Build a gate config from an OpenCode config file."""
    provider_table = _provider_table(opencode)
    records, skipped = _model_entries(provider_table)
    return _assemble_gate_config(records, skipped, roles, existing, force=force)


@dataclass(frozen=True)
class ApiImportRequest:
    """Inputs for an import from resolved OpenCode API responses."""

    models: list[dict[str, object]]
    providers: list[dict[str, object]]
    integrations: Mapping[str, dict[str, object]]
    roles: RolePolicy
    existing: Mapping[str, object] | None = None
    force: bool = False
    provider_filter: tuple[str, ...] = ()
    key_env_overrides: Mapping[str, str] = field(default_factory=dict)


def build_gate_config_from_api(request: ApiImportRequest) -> dict[str, object]:
    """Build a gate config from resolved OpenCode API responses."""
    records, skipped = _api_records(
        request.models,
        request.providers,
        request.integrations,
        set(request.provider_filter),
        request.key_env_overrides,
    )
    return _assemble_gate_config(
        records, skipped, request.roles, request.existing, force=request.force
    )


def _release_id(record: Mapping[str, object]) -> str:
    """Return the stable release id for an imported record."""
    return f"{record['family']}/{record['model']}@{record['revision']}"


def _deployment_id(record: Mapping[str, object]) -> str:
    """Return the stable deployment id for an imported record."""
    return f"{record['provider']}/{record['model_key']}"


def _deployment_from_record(
    record: Mapping[str, object],
    roles: RolePolicy,
    previous: Mapping[str, object],
    *,
    force: bool,
) -> dict[str, object]:
    """Build one deployment from an import record."""
    deployment_id = _deployment_id(record)
    deployment: dict[str, object] = {
        "release": _release_id(record),
        "provider": record["provider"],
        "endpoint": record["endpoint"],
        "quantization": "unknown",
        "prompt_hash": PROMPT_HASH,
        "decoding": {"temperature": 0.0, "top_p": 1.0},
        "key_env": record["key_env"],
        "proposer": deployment_id in roles.proposers,
        "judge": deployment_id == roles.judge,
    }
    if record["cost"] is not None:
        deployment["cost"] = record["cost"]
    if record["limits"] is not None:
        deployment["limits"] = record["limits"]
    if record.get("headers") is not None:
        deployment["headers"] = record["headers"]
    if not force:
        for field in ("quantization", "prompt_hash", "decoding"):
            if field in previous:
                deployment[field] = previous[field]
    return deployment


def _validate(data: Mapping[str, object]) -> GateConfig:
    """Validate gate data by writing it to a temporary file."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", encoding="utf-8", delete=False
    ) as handle:
        json.dump(data, handle, ensure_ascii=False)
        name = handle.name
    try:
        return load_config(Path(name))
    except GateError as error:
        msg = f"imported config is invalid: {error}"
        raise SyncError(msg) from error
    finally:
        Path(name).unlink(missing_ok=True)


def serialise(data: Mapping[str, object]) -> str:
    """Serialise a gate config deterministically."""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _parse_key_env(values: Iterable[str]) -> dict[str, str]:
    """Parse repeated `provider=ENV` overrides."""
    overrides: dict[str, str] = {}
    for value in values:
        provider, separator, name = value.partition("=")
        if not separator or not provider or not name:
            msg = f"invalid --key-env {value!r}; expected provider=ENV"
            raise SyncError(msg)
        overrides[provider] = name
    return overrides


def _api_sources(
    args: argparse.Namespace,
) -> tuple[
    list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, object]]
]:
    """Load API responses from saved files or the running OpenCode server."""
    if args.models_json is not None:
        models = _object_list(
            _load_saved_payload(args.models_json), str(args.models_json)
        )
    else:
        models = _object_list(_api_payload(API_MODEL_PATH), API_MODEL_PATH)
    if args.providers_json is not None:
        providers = _object_list(
            _load_saved_payload(args.providers_json), str(args.providers_json)
        )
    else:
        providers = _object_list(_api_payload(API_PROVIDER_PATH), API_PROVIDER_PATH)
    integrations = _load_integrations(args.integrations_json)
    if (
        args.from_api
        and args.models_json is None
        and args.providers_json is None
        and args.integrations_json is None
    ):
        for provider in providers:
            integration_id = provider.get("integrationID", provider.get("id"))
            if not isinstance(integration_id, str) or integration_id in integrations:
                continue
            try:
                data = _api_payload(f"/api/integration/{integration_id}")
            except SyncError:
                continue
            if isinstance(data, dict):
                integrations[integration_id] = data
    return models, providers, integrations


def main(argv: Iterable[str] | None = None) -> int:
    """Run the OpenCode-to-gate sync command."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--opencode", type=Path)
    source.add_argument(
        "--from-api",
        action="store_true",
        help="read the resolved catalog from the running OpenCode server",
    )
    parser.add_argument("--models-json", type=Path)
    parser.add_argument("--providers-json", type=Path)
    parser.add_argument("--integrations-json", type=Path)
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--key-env", action="append", default=[])
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    api_mode = args.from_api or args.models_json or args.providers_json
    try:
        roles = load_roles(args.roles)
        existing = (
            json.loads(args.output.read_text(encoding="utf-8"))
            if args.output.exists()
            else None
        )
        if api_mode:
            models, providers, integrations = _api_sources(args)
            result = build_gate_config_from_api(
                ApiImportRequest(
                    models=models,
                    providers=providers,
                    integrations=integrations,
                    roles=roles,
                    existing=existing,
                    force=args.force,
                    provider_filter=tuple(args.provider),
                    key_env_overrides=_parse_key_env(args.key_env),
                )
            )
        else:
            opencode_path = find_opencode(args.opencode)
            opencode = load_opencode(opencode_path)
            result = build_gate_config(opencode, roles, existing, force=args.force)
    except (OSError, json.JSONDecodeError, SyncError, GateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    old = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    new = serialise(result)
    if args.dry_run:
        diff = difflib.unified_diff(
            old.splitlines(), new.splitlines(), fromfile=str(args.output), tofile="new"
        )
        print("\n".join(diff) or "no changes")
        return 0
    args.output.write_text(new, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

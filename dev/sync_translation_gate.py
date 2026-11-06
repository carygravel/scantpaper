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
import sys
import tempfile
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
    for field in ("input", "output", "cache_read", "cache_write"):
        value = raw.get(field)
        if isinstance(value, int | float) and not isinstance(value, bool):
            cost[field] = float(value)
    if any(field in cost for field in ("input", "output", "cache_read", "cache_write")):
        return cost
    return None


def _limits(model: Mapping[str, object]) -> dict[str, int] | None:
    """Map an OpenCode model limit block to the gate limits block."""
    raw = model.get("limit")
    if not isinstance(raw, dict):
        return None
    limits: dict[str, int] = {}
    for field in ("context", "output"):
        value = raw.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            limits[field] = value
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


def _deployment_id(record: Mapping[str, object]) -> str:
    """Return the stable deployment id for an imported record."""
    return f"{record['provider']}/{record['model_key']}"


def _release_id(record: Mapping[str, object]) -> str:
    """Return the stable release id for an imported record."""
    return f"{record['family']}/{record['model']}@{record['revision']}"


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
    if not force:
        for field in ("quantization", "prompt_hash", "decoding"):
            if field in previous:
                deployment[field] = previous[field]
    return deployment


def build_gate_config(
    opencode: Mapping[str, object],
    roles: RolePolicy,
    existing: Mapping[str, object] | None = None,
    *,
    force: bool = False,
) -> dict[str, object]:
    """Build a gate config from OpenCode data and a role policy."""
    provider_table = _provider_table(opencode)
    records, skipped = _model_entries(provider_table)
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


def main(argv: Iterable[str] | None = None) -> int:
    """Run the OpenCode-to-gate sync command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencode", type=Path)
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        opencode_path = find_opencode(args.opencode)
        opencode = load_opencode(opencode_path)
        roles = load_roles(args.roles)
        existing = (
            json.loads(args.output.read_text(encoding="utf-8"))
            if args.output.exists()
            else None
        )
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

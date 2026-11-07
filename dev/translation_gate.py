"""Evidence-based gate for machine-produced translations.

The gate separates three questions:

* **Can this model do this language?** A release (family, model, revision) is
  qualified per language against held-out human approvals.
* **Can this deployment serve the release?** A deployment (provider,
  endpoint, quantization, prompt hash and decoding) inherits a release
  qualification only after a conformance probe.
* **May this string ship?** Two independent families propose, a third family
  judges blindly, deterministic checks run, and a sentence is back-translated.
  Any missing or failing piece of evidence produces an abstention.

The module also records drift excursions, a per-language capability report,
revocations, a random audit sample and a false-positive defect rate. It never
reads a model credential until a request is made, and never prints one.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlparse

import polib
from tm_index import dominant_match
from translation_ledger import (
    LEDGER_PATH as DEFAULT_LEDGER_PATH,
)
from translation_ledger import (
    ApprovalContext,
    ApprovalRecord,
    LedgerError,
    add_section_record,
    approvals,
    load_ledger,
    make_record,
    section,
    write_ledger,
)
from translation_policy import (
    MACHINE_PROVENANCE_CLASSES,
    has_spaced_printf,
    is_high_impact,
    is_mechanical_rebase,
    placeholder_tokens,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "po" / "translation-gate.json"
EXAMPLE_CONFIG = REPO_ROOT / "po" / "translation-gate.example.json"
DEFAULT_ROLES = REPO_ROOT / "po" / "translation-gate.roles.json"
EXAMPLE_ROLES = REPO_ROOT / "po" / "translation-gate.roles.example.json"
DEFAULT_PROBE_DIR = REPO_ROOT / "po" / "drift-probe"
CONFIG_VERSION = 1
DEFAULT_HIGH_IMPACT_MIN_PROJECTS = 2
MIN_PROPOSER_FAMILIES = 2
_SHORT_LABEL_CHARS = 20
_SENTENCE_CHARS = 25
PROMPT_VERSION = "2026-11-01"
DEFAULT_CHARS_PER_TOKEN = 4.0


def _prompt_hash(version: str = PROMPT_VERSION) -> str:
    """Return the deployment-facing hash of a prompt version."""
    return "sha256:" + hashlib.sha256(version.encode()).hexdigest()[:16]


PROMPT_HASH = _prompt_hash()


def _today() -> str:
    """Return today's UTC date in ISO form."""
    return datetime.now(timezone.utc).date().isoformat()


class GateError(Exception):
    """A gate input, configuration or model failure."""


class CredentialError(GateError):
    """A credential environment variable is missing."""


class ModelError(GateError):
    """A model deployment could not produce a usable answer."""


class BudgetExceededError(GateError):
    """A pre-action estimate exceeds the configured maximum cost."""


@dataclass(frozen=True)
class Release:
    """A model release: family, model id and revision."""

    id: str
    family: str
    model: str
    revision: str


@dataclass(frozen=True)
class CostTier:
    """One context-tiered price band for a deployment."""

    context: int
    input: float | None
    output: float | None
    cache_read: float | None
    cache_write: float | None


@dataclass(frozen=True)
class CostRates:
    """Token prices for one deployment, per million tokens."""

    currency: str
    unit: str
    input: float | None
    output: float | None
    cache_read: float | None
    cache_write: float | None
    tiers: tuple[CostTier, ...] = ()


@dataclass(frozen=True)
class TokenLimits:
    """Context and output token limits for one deployment."""

    context: int | None
    output: int | None


@dataclass(frozen=True)
class Usage:
    """Provider-reported token usage for one call."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cached_tokens: int | None
    cache_write_tokens: int | None
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Completion:
    """One model answer with its usage, latency and cost."""

    text: str
    deployment: str
    release: str
    model: str
    usage: Usage | None
    latency_ms: float
    cost_usd: float | None = None
    cost_reason: str | None = None
    cost_tier: int | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready call record."""
        usage = None
        if self.usage is not None:
            usage = {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
                "cached_tokens": self.usage.cached_tokens,
                "cache_write_tokens": self.usage.cache_write_tokens,
            }
        return {
            "deployment": self.deployment,
            "release": self.release,
            "model": self.model,
            "usage": usage,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "cost_reason": self.cost_reason,
            "cost_tier": self.cost_tier,
        }


@dataclass(frozen=True)
class Proposal:
    """One proposer's answer and the call that produced it."""

    deployment: str
    release: str
    family: str
    text: str
    completion: Completion

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready proposal record."""
        return {
            "deployment": self.deployment,
            "release": self.release,
            "family": self.family,
            "text": self.text,
            "call": self.completion.as_dict(),
        }


@dataclass(frozen=True)
class Deployment:
    """One serving configuration of a release."""

    id: str
    release: str
    model: str
    provider: str
    endpoint: str
    quantization: str
    prompt_hash: str
    decoding: dict[str, object]
    key_env: str
    proposer: bool
    judge: bool
    cost: CostRates | None = None
    limits: TokenLimits | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class GateConfig:
    """The validated contents of ``po/translation-gate.json``."""

    releases: dict[str, Release]
    deployments: dict[str, Deployment]
    thresholds: dict[str, float]

    @property
    def proposers(self) -> list[Deployment]:
        """Return the deployments allowed to propose."""
        return [d for d in self.deployments.values() if d.proposer]

    @property
    def judges(self) -> list[Deployment]:
        """Return the deployments allowed to judge."""
        return [d for d in self.deployments.values() if d.judge]

    def release_for(self, deployment: Deployment) -> Release:
        """Return the release a deployment serves."""
        release = self.releases.get(deployment.release)
        if release is None:
            msg = f"deployment {deployment.id!r} serves unknown release"
            raise GateError(msg)
        return release

    def deployments_for(self, release_id: str) -> list[Deployment]:
        """Return every configured deployment of a release."""
        return [d for d in self.deployments.values() if d.release == release_id]


@dataclass(frozen=True)
class RolePolicy:
    """Proposer and judge assignment kept outside the provider config."""

    proposers: tuple[str, ...]
    judge: str


@dataclass(frozen=True)
class GateDecision:
    """The outcome of one gate run."""

    approved: bool
    reason: str
    translation: str | None = None
    record: ApprovalRecord | None = None
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GateOptions:
    """Optional inputs for a gate run."""

    context: str = ""
    occurrences: tuple[object, ...] = ()
    tm_db: Path | None = None


@dataclass(frozen=True)
class DeploymentEstimate:
    """Estimated tokens and cost for one deployment."""

    deployment: str
    release: str
    calls: int
    input_tokens: int
    output_tokens: int
    low_cost_usd: float | None
    high_cost_usd: float | None
    currency: str
    price_known: bool

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready estimate."""
        return cast("dict[str, object]", asdict(self))


@dataclass(frozen=True)
class ActionEstimate:
    """Estimated tokens and cost for one action."""

    action: str
    language: str
    deployments: tuple[DeploymentEstimate, ...]
    low_cost_usd: float | None
    high_cost_usd: float | None
    assumptions: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready action estimate."""
        return {
            "action": self.action,
            "language": self.language,
            "deployments": [item.as_dict() for item in self.deployments],
            "low_cost_usd": self.low_cost_usd,
            "high_cost_usd": self.high_cost_usd,
            "assumptions": self.assumptions,
        }


@dataclass(frozen=True)
class QualificationRequest:
    """One release/language qualification request."""

    release: str
    language: str
    entries: Sequence[polib.POEntry]
    approval_date: str | None = None
    budget_usd: float | None = None


@dataclass(frozen=True)
class ConformanceRequest:
    """One deployment conformance request."""

    deployment_id: str
    release: str
    probe_score: float
    approval_date: str | None = None


@dataclass(frozen=True)
class DriftRequest:
    """One drift-probe request."""

    release: str
    deployment_id: str
    language: str
    probe: Sequence[Mapping[str, str]]
    budget_usd: float | None = None


def _string(mapping: Mapping[str, object], field: str, where: str) -> str:
    """Return a required non-empty string field."""
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        msg = f"{where} has no non-empty {field!r}"
        raise GateError(msg)
    return value


def _load_releases(data: Mapping[str, object], path: Path) -> dict[str, Release]:
    """Parse the release table."""
    releases_data = data.get("releases")
    if not isinstance(releases_data, dict):
        msg = f"{path} needs a 'releases' object"
        raise GateError(msg)
    releases: dict[str, Release] = {}
    for release_id, release in releases_data.items():
        if not isinstance(release_id, str) or not isinstance(release, dict):
            msg = f"{path} has a malformed release"
            raise GateError(msg)
        releases[release_id] = Release(
            id=release_id,
            family=_string(release, "family", release_id),
            model=_string(release, "model", release_id),
            revision=_string(release, "revision", release_id),
        )
    return releases


def _optional_number(
    mapping: Mapping[str, object], field: str, where: str
) -> float | None:
    """Return a non-negative optional number."""
    value = mapping.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        msg = f"{where} field {field!r} must be a non-negative number"
        raise GateError(msg)
    return float(value)


def _load_cost_tier(raw: object, where: str) -> CostTier:
    """Parse one context tier."""
    if not isinstance(raw, dict):
        msg = f"{where} cost tier must be an object"
        raise GateError(msg)
    context = raw.get("context")
    if isinstance(context, bool) or not isinstance(context, int) or context <= 0:
        msg = f"{where} cost tier context must be a positive integer"
        raise GateError(msg)
    return CostTier(
        context=context,
        input=_optional_number(raw, "input", where),
        output=_optional_number(raw, "output", where),
        cache_read=_optional_number(raw, "cache_read", where),
        cache_write=_optional_number(raw, "cache_write", where),
    )


def _load_cost(deployment: Mapping[str, object], where: str) -> CostRates | None:
    """Parse an optional deployment cost block."""
    raw = deployment.get("cost")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        msg = f"{where} cost must be an object"
        raise GateError(msg)
    currency = raw.get("currency", "USD")
    unit = raw.get("unit", "per_million_tokens")
    if not isinstance(currency, str) or not currency:
        msg = f"{where} cost currency must be a non-empty string"
        raise GateError(msg)
    if not isinstance(unit, str) or not unit:
        msg = f"{where} cost unit must be a non-empty string"
        raise GateError(msg)
    if unit != "per_million_tokens":
        msg = f"{where} cost unit must be 'per_million_tokens'"
        raise GateError(msg)
    raw_tiers = raw.get("tiers", [])
    if not isinstance(raw_tiers, list):
        msg = f"{where} cost tiers must be a list"
        raise GateError(msg)
    tiers = tuple(
        sorted(
            (_load_cost_tier(item, where) for item in raw_tiers),
            key=lambda item: item.context,
        )
    )
    return CostRates(
        currency=currency,
        unit=unit,
        input=_optional_number(raw, "input", where),
        output=_optional_number(raw, "output", where),
        cache_read=_optional_number(raw, "cache_read", where),
        cache_write=_optional_number(raw, "cache_write", where),
        tiers=tiers,
    )


def _load_limits(deployment: Mapping[str, object], where: str) -> TokenLimits | None:
    """Parse an optional deployment token-limit block."""
    raw = deployment.get("limits")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        msg = f"{where} limits must be an object"
        raise GateError(msg)
    values: dict[str, int | None] = {}
    for name in ("context", "output"):
        value = raw.get(name)
        if value is None:
            values[name] = None
        elif isinstance(value, bool) or not isinstance(value, int) or value < 0:
            msg = f"{where} limits.{name} must be a non-negative integer"
            raise GateError(msg)
        else:
            values[name] = value
    return TokenLimits(context=values["context"], output=values["output"])


def _load_headers(
    deployment: Mapping[str, object], where: str
) -> dict[str, str] | None:
    """Parse optional non-empty string headers."""
    raw = deployment.get("headers")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        msg = f"{where} headers must be an object"
        raise GateError(msg)
    headers: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            msg = f"{where} has an invalid header name"
            raise GateError(msg)
        if not isinstance(value, str):
            msg = f"{where} header {key!r} must be a string"
            raise GateError(msg)
        headers[key] = value
    return headers


def _load_deployments(
    data: Mapping[str, object],
    releases: Mapping[str, Release],
    path: Path,
) -> dict[str, Deployment]:
    """Parse the deployment table."""
    deployments_data = data.get("deployments")
    if not isinstance(deployments_data, dict):
        msg = f"{path} needs a 'deployments' object"
        raise GateError(msg)
    deployments: dict[str, Deployment] = {}
    for deployment_id, deployment in deployments_data.items():
        if not isinstance(deployment_id, str) or not isinstance(deployment, dict):
            msg = f"{path} has a malformed deployment"
            raise GateError(msg)
        release_id = _string(deployment, "release", deployment_id)
        if release_id not in releases:
            msg = f"deployment {deployment_id!r} serves unknown release {release_id!r}"
            raise GateError(msg)
        decoding = deployment.get("decoding", {})
        if not isinstance(decoding, dict):
            msg = f"deployment {deployment_id!r} decoding must be an object"
            raise GateError(msg)
        deployments[deployment_id] = Deployment(
            id=deployment_id,
            release=release_id,
            model=releases[release_id].model,
            provider=_string(deployment, "provider", deployment_id),
            endpoint=_string(deployment, "endpoint", deployment_id),
            quantization=_string(deployment, "quantization", deployment_id),
            prompt_hash=_string(deployment, "prompt_hash", deployment_id),
            decoding=dict(decoding),
            key_env=_string(deployment, "key_env", deployment_id),
            proposer=bool(deployment.get("proposer", False)),
            judge=bool(deployment.get("judge", False)),
            cost=_load_cost(deployment, deployment_id),
            limits=_load_limits(deployment, deployment_id),
            headers=_load_headers(deployment, deployment_id),
        )
    return deployments


def _load_thresholds(data: Mapping[str, object], path: Path) -> dict[str, float]:
    """Parse numeric thresholds."""
    raw = data.get("thresholds", {})
    if not isinstance(raw, dict):
        msg = f"{path} thresholds must be an object"
        raise GateError(msg)
    return {
        name: float(value)
        for name, value in raw.items()
        if isinstance(value, int | float)
    }


def load_config(path: Path = DEFAULT_CONFIG) -> GateConfig:
    """Load and validate the gate configuration."""
    if path == DEFAULT_CONFIG and not path.exists() and EXAMPLE_CONFIG.exists():
        path = EXAMPLE_CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read {path}: {error}"
        raise GateError(msg) from error
    if not isinstance(data, dict) or data.get("version") != CONFIG_VERSION:
        msg = f"{path} is not a version-{CONFIG_VERSION} gate configuration"
        raise GateError(msg)

    releases = _load_releases(data, path)
    deployments = _load_deployments(data, releases, path)
    thresholds = _load_thresholds(data, path)
    thresholds.setdefault("chars_per_token", DEFAULT_CHARS_PER_TOKEN)
    if thresholds["chars_per_token"] <= 0:
        msg = f"{path} chars_per_token must be positive"
        raise GateError(msg)
    config = GateConfig(
        releases=releases,
        deployments=deployments,
        thresholds=thresholds,
    )
    validate_config(config)
    return config


def validate_config(config: GateConfig) -> None:
    """Refuse a configuration without independent proposers and a third judge."""
    if len(config.proposers) < MIN_PROPOSER_FAMILIES:
        msg = "the gate needs at least two proposer deployments"
        raise GateError(msg)
    proposer_families = {
        config.release_for(deployment).family for deployment in config.proposers
    }
    if len(proposer_families) < MIN_PROPOSER_FAMILIES:
        msg = (
            "proposers must represent at least two model families; "
            "two deployments of one release count once"
        )
        raise GateError(msg)
    if not config.judges:
        msg = "the gate needs a judge deployment"
        raise GateError(msg)
    judge_families = {
        config.release_for(deployment).family for deployment in config.judges
    }
    if judge_families & proposer_families:
        msg = "the judge family must differ from every proposer family"
        raise GateError(msg)


def load_roles(path: Path = DEFAULT_ROLES) -> RolePolicy:
    """Load the proposer and judge role policy."""
    if path == DEFAULT_ROLES and not path.exists() and EXAMPLE_ROLES.exists():
        path = EXAMPLE_ROLES
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read role policy {path}: {error}"
        raise GateError(msg) from error
    if not isinstance(data, dict):
        msg = f"{path} is not a JSON object"
        raise GateError(msg)
    proposers = data.get("proposers")
    judge = data.get("judge")
    if (
        not isinstance(proposers, list)
        or not all(isinstance(item, str) and item for item in proposers)
        or len(proposers) < MIN_PROPOSER_FAMILIES
    ):
        msg = f"{path} needs at least two non-empty proposer deployment ids"
        raise GateError(msg)
    if not isinstance(judge, str) or not judge:
        msg = f"{path} needs a non-empty judge deployment id"
        raise GateError(msg)
    return RolePolicy(proposers=tuple(proposers), judge=judge)


def validate_roles(config: GateConfig, roles: RolePolicy) -> None:
    """Check that a role policy names existing, independent deployments."""
    unknown = [
        deployment_id
        for deployment_id in (*roles.proposers, roles.judge)
        if deployment_id not in config.deployments
    ]
    if unknown:
        msg = f"role policy names unknown deployment(s): {', '.join(unknown)}"
        raise GateError(msg)
    proposer_families = {
        config.release_for(config.deployments[deployment_id]).family
        for deployment_id in roles.proposers
    }
    if len(proposer_families) < MIN_PROPOSER_FAMILIES:
        msg = "proposer role ids must represent at least two families"
        raise GateError(msg)
    judge_family = config.release_for(config.deployments[roles.judge]).family
    if judge_family in proposer_families:
        msg = "judge role must differ from every proposer family"
        raise GateError(msg)


def deployment_identity(deployment: Deployment) -> str:
    """Return the content hash that changes when serving config changes."""
    payload = {
        "provider": deployment.provider,
        "endpoint": deployment.endpoint,
        "quantization": deployment.quantization,
        "prompt_hash": deployment.prompt_hash,
        "decoding": deployment.decoding,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _token_count(value: object) -> int | None:
    """Return a non-negative token count, or None for an unusable value."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def parse_usage(data: object) -> Usage | None:
    """Parse an OpenAI-compatible usage object from a response."""
    if not isinstance(data, dict) or not data:
        return None
    details = data.get("prompt_tokens_details")
    cached = None
    if isinstance(details, dict):
        cached = _token_count(details.get("cached_tokens"))
    if cached is None:
        cached = _token_count(data.get("cached_tokens"))
    if cached is None:
        cached = _token_count(data.get("cache_read_input_tokens"))
    cache_write = _token_count(data.get("cache_creation_input_tokens"))
    prompt = _token_count(data.get("prompt_tokens"))
    completion = _token_count(data.get("completion_tokens"))
    total = _token_count(data.get("total_tokens"))
    if prompt is None and completion is None and total is None:
        return None
    return Usage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        cached_tokens=cached,
        cache_write_tokens=cache_write,
        raw=dict(data),
    )


def select_cost_tier(usage: Usage | None, cost: CostRates | None) -> CostTier | None:
    """Return the highest context tier applicable to a call, if any."""
    if usage is None or cost is None or usage.prompt_tokens is None:
        return None
    selected: CostTier | None = None
    for tier in cost.tiers:
        if tier.context <= usage.prompt_tokens:
            selected = tier
        else:
            break
    return selected


def compute_cost(
    usage: Usage | None, cost: CostRates | None
) -> tuple[float | None, str | None]:
    """Return (cost, reason) for one call; cost is None when unknown."""
    if usage is None:
        return None, "usage missing"
    if cost is None:
        return None, "price missing"
    active = select_cost_tier(usage, cost) or cost
    if (
        usage.prompt_tokens is None
        or usage.completion_tokens is None
        or active.input is None
        or active.output is None
    ):
        return None, "input or output token price missing"
    cached = usage.cached_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    if cached and active.cache_read is None:
        return None, "cache_read price missing"
    if cache_write and active.cache_write is None:
        return None, "cache_write price missing"
    uncached = max(0, usage.prompt_tokens - cached)
    total = (
        uncached * active.input
        + cached * (active.cache_read or 0.0)
        + cache_write * (active.cache_write or 0.0)
        + usage.completion_tokens * active.output
    )
    return round(total / 1_000_000, 6), None


class ModelClient(Protocol):
    """The model interface the gate needs."""

    def complete(self, deployment: Deployment, prompt: str) -> Completion:
        """Return one completion for a deployment."""


class OpenAICompatibleClient:
    """A minimal OpenAI-compatible chat-completions client.

    The constructor does not touch the environment. A missing key is reported
    by name only, never by value.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        """Store the request timeout without reading any credential."""
        self.timeout = timeout

    def complete(self, deployment: Deployment, prompt: str) -> Completion:
        """Send one chat completion and return its text, usage and cost."""
        key = os.environ.get(deployment.key_env)
        if key is None or key == "":
            msg = f"missing environment variable {deployment.key_env}"
            raise CredentialError(msg)
        parsed = urlparse(deployment.endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.hostname == ""
        ):
            msg = f"deployment {deployment.id!r} has an unusable endpoint"
            raise ModelError(msg)
        payload = {
            "model": deployment.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": deployment.decoding.get("temperature", 0.0),
            "top_p": deployment.decoding.get("top_p", 1.0),
        }
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        connection_class = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_class(
            parsed.hostname, parsed.port, timeout=self.timeout
        )
        request_headers = dict(deployment.headers or {})
        request_headers["Content-Type"] = "application/json"
        request_headers["Authorization"] = f"Bearer {key}"
        started = time.perf_counter()
        try:
            connection.request(
                "POST",
                path,
                body=json.dumps(payload).encode(),
                headers=request_headers,
            )
            response = connection.getresponse()
            raw = response.read()
        except (OSError, http.client.HTTPException) as error:
            msg = f"model request failed for {deployment.id}: {error}"
            raise ModelError(msg) from error
        finally:
            connection.close()
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            msg = f"model {deployment.id} returned an unreadable answer"
            raise ModelError(msg) from error
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            msg = f"model {deployment.id} returned an unexpected payload"
            raise ModelError(msg) from error
        if not isinstance(content, str):
            msg = f"model {deployment.id} returned a non-text answer"
            raise ModelError(msg)
        usage = parse_usage(data.get("usage") if isinstance(data, dict) else None)
        cost_usd, cost_reason = compute_cost(usage, deployment.cost)
        tier = select_cost_tier(usage, deployment.cost)
        return Completion(
            text=cast("str", content).strip(),
            deployment=deployment.id,
            release=deployment.release,
            model=deployment.model,
            usage=usage,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            cost_reason=cost_reason,
            cost_tier=tier.context if tier is not None else None,
        )


def prompt_for(
    action: str,
    language: str,
    source: str,
    context: str = "",
) -> str:
    """Build a provider-neutral prompt for one task."""
    suffix = f"\nContext: {context}" if context else ""
    if action == "translate":
        return (
            f"Translate the following UI string into {language}. "
            "Return only the translation, preserving every placeholder, "
            "mnemonic and line break."
            f"\nSource: {source}{suffix}"
        )
    if action == "backtranslate":
        return (
            f"Translate this {language} UI string back into English. "
            "Return only the English text."
            f"\nSource: {source}{suffix}"
        )
    return f"{action}: {source}"


def _normalise(text: str) -> str:
    """Normalise a translation for exact-match comparison."""
    return " ".join(text.replace("_", "").casefold().split())


def _format_fields(text: str) -> list[str] | None:
    """Return the str.format field names, or None for unbalanced braces."""
    if text.count("{") != text.count("}"):
        return None
    return cast("list[str]", re.findall(r"(?<!\{)\{([^{}]*)\}(?!\})", text))


def deterministic_checks(source: str, translation: str) -> list[str]:
    """Return every deterministic defect in a proposed translation."""
    defects: list[str] = []
    if has_spaced_printf(translation):
        defects.append("printf token split by space")
    if sorted(placeholder_tokens(source)) != sorted(placeholder_tokens(translation)):
        defects.append("placeholders changed")
    expected = _format_fields(source)
    got = _format_fields(translation)
    if expected is not None and got is not None and sorted(expected) != sorted(got):
        defects.append("str.format fields changed")
    if expected is not None and got is None:
        defects.append("malformed braces")
    if not translation.strip():
        defects.append("empty translation")
    return defects


def propose(
    source: str,
    language: str,
    config: GateConfig,
    client: ModelClient,
    *,
    context: str = "",
) -> list[Proposal]:
    """Return one proposal from every proposer deployment."""
    proposals: list[Proposal] = []
    for deployment in config.proposers:
        completion = client.complete(
            deployment, prompt_for("translate", language, source, context)
        )
        proposals.append(
            Proposal(
                deployment=deployment.id,
                release=deployment.release,
                family=config.release_for(deployment).family,
                text=completion.text,
                completion=completion,
            )
        )
    return proposals


def blind_judge(
    source: str,
    language: str,
    proposals: Sequence[Proposal],
    config: GateConfig,
    client: ModelClient,
) -> tuple[int | None, str, Completion | None]:
    """Ask a third family to choose a proposal without seeing its origin."""
    if not proposals:
        return None, "no proposals", None
    labels = [chr(ord("A") + index) for index in range(len(proposals))]
    listing = "\n".join(
        f"{label}: {proposal.text}"
        for label, proposal in zip(labels, proposals, strict=True)
    )
    prompt = (
        f"Choose the best {language} translation of this source string. "
        "Answer with the letter only, or ABSTAIN.\n"
        f"Source: {source}\n{listing}"
    )
    judge = config.judges[0]
    completion = client.complete(judge, prompt)
    answer = completion.text.strip().upper()
    for index, label in enumerate(labels):
        if answer.startswith(label):
            return index, answer, completion
    return None, answer, completion


def back_translation_preserves(
    source: str,
    translation: str,
    language: str,
    config: GateConfig,
    client: ModelClient,
) -> tuple[bool, Completion]:
    """Return whether a back-translation keeps the source meaning."""
    judge = config.judges[0]
    completion = client.complete(
        judge, prompt_for("backtranslate", language, translation)
    )
    back = completion.text
    if _normalise(back) == _normalise(source):
        return True, completion
    threshold = config.thresholds.get("backtranslation", 0.6)
    preserved = (
        SequenceMatcher(None, _normalise(back), _normalise(source)).ratio() >= threshold
    )
    return preserved, completion


def summarize_calls(calls: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Return aggregate cost and latency for a list of call records."""
    total_cost = 0.0
    total_latency = 0.0
    unknown_cost = False
    for call in calls:
        cost = call.get("cost_usd")
        if isinstance(cost, int | float) and not isinstance(cost, bool):
            total_cost += float(cost)
        else:
            unknown_cost = True
        latency = call.get("latency_ms")
        if isinstance(latency, int | float) and not isinstance(latency, bool):
            total_latency += float(latency)
    return {
        "call_count": len(calls),
        "total_cost_usd": None if unknown_cost else round(total_cost, 6),
        "latency_ms": round(total_latency, 3),
    }


def _independent_families(proposals: Sequence[Proposal]) -> bool:
    """Return whether the proposals come from at least two families."""
    families = {proposal.family for proposal in proposals}
    return len(families) >= MIN_PROPOSER_FAMILIES


def classify_evidence(
    source: str,
    language: str,
    previous: str,
    current: str,
    *,
    tm_db: Path | None = None,
) -> str | None:
    """Return the strongest provenance class for existing evidence.

    Unchanged pre-2026 text is ``human-historical``; a mnemonic or placeholder
    rebase is ``in-project-rebase``; a dominant cross-project match that also
    passes the deterministic checks is ``tm-consensus``. No evidence returns
    None, which leaves the string English until the gate approves it.
    """
    if previous == current:
        return "human-historical"
    if is_mechanical_rebase(previous, current):
        return "in-project-rebase"
    if (
        tm_db is not None
        and dominant_match(tm_db, source, language) == current
        and not deterministic_checks(source, current)
    ):
        return "tm-consensus"
    return None


def run_gate(
    source: str,
    language: str,
    config: GateConfig,
    client: ModelClient,
    *,
    options: GateOptions | None = None,
) -> GateDecision:
    """Run proposal, checks, blind judging and back-translation."""
    options = options or GateOptions()
    proposals = propose(source, language, config, client, context=options.context)
    proposal_records = [proposal.as_dict() for proposal in proposals]
    calls = [
        {**proposal.completion.as_dict(), "role": "proposer"} for proposal in proposals
    ]
    if not _independent_families(proposals):
        return GateDecision(
            approved=False,
            reason="fewer than two independent model families proposed",
            evidence={"proposals": proposal_records, "calls": calls},
        )

    checks = {
        proposal.deployment: deterministic_checks(source, proposal.text)
        for proposal in proposals
    }
    passing = [proposal for proposal in proposals if not checks[proposal.deployment]]
    if not passing:
        return GateDecision(
            approved=False,
            reason="every proposal failed a deterministic check",
            evidence={
                "proposals": proposal_records,
                "checks": checks,
                "calls": calls,
            },
        )

    index, verdict, judge_completion = blind_judge(
        source, language, passing, config, client
    )
    if judge_completion is not None:
        calls.append({**judge_completion.as_dict(), "role": "judge"})
    if index is None:
        return GateDecision(
            approved=False,
            reason="judge abstained or returned no usable choice",
            evidence={
                "proposals": proposal_records,
                "checks": checks,
                "verdict": verdict,
                "calls": calls,
            },
        )
    preferred = passing[index]
    preferred_text = preferred.text

    backtranslation: bool | None = None
    if len(source) >= _SENTENCE_CHARS and " " in source:
        backtranslation, back_completion = back_translation_preserves(
            source,
            preferred_text,
            language,
            config,
            client,
        )
        calls.append({**back_completion.as_dict(), "role": "backtranslation"})
        if not backtranslation:
            return GateDecision(
                approved=False,
                reason="back-translation changed the meaning",
                evidence={
                    "proposals": proposal_records,
                    "checks": checks,
                    "verdict": verdict,
                    "backtranslation": False,
                    "calls": calls,
                },
            )

    high_impact = is_high_impact(source, options.occurrences)
    evidence: dict[str, object] = {
        "proposals": proposal_records,
        "checks": checks,
        "judge": {"deployment": config.judges[0].id, "verdict": verdict},
        "backtranslation": backtranslation,
        "high_impact": high_impact,
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": PROMPT_HASH,
        "calls": calls,
    }
    deployment = preferred.deployment
    release = preferred.release
    provenance_class = "machine-strong"
    if (
        options.tm_db is not None
        and dominant_match(options.tm_db, source, language) == preferred_text
    ):
        provenance_class = "tm-consensus"
        evidence["tm_dominant"] = True
    record = make_record(
        language,
        _entry_for(source, preferred_text),
        provenance_class,
        context=ApprovalContext(
            approval_date=_today(),
            evidence=evidence,
            model_release=release,
            deployment=deployment,
        ),
    )
    return GateDecision(
        approved=True,
        reason="every check and the judge agree",
        translation=preferred_text,
        record=record,
        evidence=evidence,
    )


def record_gate_run(
    ledger: dict[str, object],
    decision: GateDecision,
    language: str,
    *,
    action: str = "gate",
    timestamp: str | None = None,
) -> dict[str, object]:
    """Append one gate outcome, including abstentions, to the ledger."""
    calls = decision.evidence.get("calls", [])
    call_records = (
        [cast("dict[str, object]", call) for call in calls]
        if isinstance(calls, list)
        else []
    )
    proposers = sorted(
        {
            str(call.get("deployment"))
            for call in call_records
            if call.get("role") == "proposer"
        }
    )
    record: dict[str, object] = {
        "action": action,
        "language": language,
        "outcome": "approved" if decision.approved else "abstained",
        "reason": decision.reason,
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "winning_deployment": (
            decision.record.get("deployment") if decision.record is not None else None
        ),
        "winning_release": (
            decision.record.get("model_release")
            if decision.record is not None
            else None
        ),
        "proposers": proposers,
        "calls": call_records,
        **summarize_calls(call_records),
    }
    add_section_record(ledger, "gate_runs", record)
    return record


def _entry_for(source: str, translation: str) -> polib.POEntry:
    """Build a throwaway catalog entry for record hashing."""
    return polib.POEntry(msgid=source, msgstr=translation)


def _qualified(
    ledger: Mapping[str, object],
    release: str,
    language: str,
) -> dict[str, object] | None:
    """Return a qualified release record, if one exists."""
    for record in section(ledger, "qualifications"):
        if (
            record.get("release") == release
            and record.get("language") == language
            and record.get("qualified") is True
        ):
            return record
    return None


def qualify_release(
    ledger: dict[str, object],
    config: GateConfig,
    request: QualificationRequest,
    client: ModelClient,
) -> dict[str, object]:
    """Qualify a release for a language against held-out human entries."""
    release = request.release
    deployments = config.deployments_for(release)
    if release not in config.releases or not deployments:
        msg = f"release {release!r} is not configured"
        raise GateError(msg)
    tolerance = config.thresholds.get("qualification", 0.8)
    ensure_budget(estimate_qualification(config, request), request.budget_usd)
    if not request.entries:
        record: dict[str, object] = {
            "release": release,
            "language": request.language,
            "metric": "exact-match",
            "tolerance": tolerance,
            "score": 0.0,
            "baseline_size": 0,
            "drift_baseline": 0.0,
            "qualified": False,
            "date": request.approval_date or _today(),
            "reason": "no held-out human entries",
            "calls": [],
            "call_count": 0,
            "total_cost_usd": 0.0,
            "latency_ms": 0.0,
        }
    else:
        deployment = deployments[0]
        matches = 0
        calls: list[dict[str, object]] = []
        for entry in request.entries:
            completion = client.complete(
                deployment, prompt_for("translate", request.language, entry.msgid)
            )
            calls.append({**completion.as_dict(), "role": "qualification"})
            if _normalise(completion.text) == _normalise(entry.msgstr):
                matches += 1
        score = matches / len(request.entries)
        summary = summarize_calls(calls)
        record = {
            "release": release,
            "language": request.language,
            "metric": "exact-match",
            "tolerance": tolerance,
            "score": score,
            "baseline_size": len(request.entries),
            "drift_baseline": score,
            "qualified": score >= tolerance,
            "date": request.approval_date or _today(),
            "deployment": deployment.id,
            "calls": calls,
            **summary,
        }
    _replace_section(
        ledger,
        "qualifications",
        record,
        key_fields=("release", "language"),
    )
    return record


def _replace_section(
    ledger: dict[str, object],
    name: str,
    record: Mapping[str, object],
    *,
    key_fields: Sequence[str],
) -> None:
    """Insert or replace one record in an optional ledger section."""
    wanted = tuple(record.get(field) for field in key_fields)
    current = [
        item
        for item in section(ledger, name)
        if tuple(item.get(field) for field in key_fields) != wanted
    ]
    current.append(dict(record))
    ledger[name] = current


def _held_out(
    ledger: Mapping[str, object],
    catalog: polib.POFile,
    language: str,
    size: int,
) -> list[polib.POEntry]:
    """Return deterministic held-out human-approved entries."""
    by_key = {_entry_key(entry): entry for entry in catalog if not entry.obsolete}
    candidates: list[polib.POEntry] = []
    for record in approvals(ledger):
        if record.get("language") != language:
            continue
        if record.get("provenance_class") not in {
            "human-historical",
            "human-review",
            "in-project-rebase",
        }:
            continue
        entry = by_key.get(
            (
                cast("str", record.get("msgctxt") or ""),
                cast("str", record.get("msgid")),
                cast("str", record.get("msgid_plural") or ""),
            )
        )
        if entry is not None:
            candidates.append(entry)
    candidates.sort(key=lambda entry: entry.msgid)
    if len(candidates) <= size:
        return candidates
    step = len(candidates) / size
    return [candidates[int(index * step)] for index in range(size)]


def _entry_key(entry: polib.POEntry) -> tuple[str, str, str]:
    """Return the source-side key of an entry."""
    return (entry.msgctxt or "", entry.msgid, entry.msgid_plural or "")


def conform_deployment(
    ledger: dict[str, object],
    config: GateConfig,
    request: ConformanceRequest,
) -> dict[str, object]:
    """Conform a deployment of a qualified release after a probe."""
    deployment = config.deployments.get(request.deployment_id)
    if deployment is None:
        msg = f"deployment {request.deployment_id!r} is not configured"
        raise GateError(msg)
    exact_identity = deployment.release == request.release
    qualified_languages = {
        str(record.get("language"))
        for record in section(ledger, "qualifications")
        if record.get("release") == request.release and record.get("qualified") is True
    }
    threshold = config.thresholds.get("drift", 0.75)
    conformed = (
        exact_identity
        and bool(qualified_languages)
        and request.probe_score >= threshold
    )
    record: dict[str, object] = {
        "deployment": request.deployment_id,
        "release": request.release,
        "score": request.probe_score,
        "threshold": threshold,
        "qualified": conformed,
        "date": request.approval_date or _today(),
        "reason": (
            "exact release identity and a passing probe"
            if conformed
            else "release identity or probe does not conform"
        ),
    }
    _replace_section(
        ledger,
        "conformances",
        record,
        key_fields=("deployment", "release"),
    )
    return record


def drift_probe(
    config: GateConfig,
    request: DriftRequest,
    client: ModelClient,
) -> dict[str, object]:
    """Run the fixed drift probe and report a score drop."""
    deployment = config.deployments.get(request.deployment_id)
    if deployment is None:
        msg = f"deployment {request.deployment_id!r} is not configured"
        raise GateError(msg)
    ensure_budget(estimate_drift(config, request), request.budget_usd)
    matches = 0
    calls: list[dict[str, object]] = []
    for item in request.probe:
        completion = client.complete(
            deployment, prompt_for("translate", request.language, item["msgid"])
        )
        calls.append({**completion.as_dict(), "role": "drift"})
        if _normalise(completion.text) == _normalise(item["msgstr"]):
            matches += 1
    score = matches / len(request.probe) if request.probe else 0.0
    threshold = config.thresholds.get("drift", 0.75)
    dropped = score < threshold
    return {
        "release": request.release,
        "deployment": request.deployment_id,
        "language": request.language,
        "score": score,
        "threshold": threshold,
        "paused": dropped,
        "calls": calls,
        **summarize_calls(calls),
    }


def record_drift_excursion(
    ledger: dict[str, object],
    result: Mapping[str, object],
    *,
    since: str,
) -> None:
    """Record a paused drift excursion without demoting any approval."""
    add_section_record(
        ledger,
        "drift_excursions",
        {
            "release": result["release"],
            "deployment": result["deployment"],
            "language": result["language"],
            "score": result["score"],
            "threshold": result["threshold"],
            "since": since,
            "status": "paused",
            "queued_for_audit": True,
            "calls": result.get("calls", []),
            "total_cost_usd": result.get("total_cost_usd"),
            "latency_ms": result.get("latency_ms"),
        },
    )


def is_paused(ledger: Mapping[str, object], release: str, language: str) -> bool:
    """Return whether a release and language are paused for drift."""
    return any(
        record.get("release") == release
        and record.get("language") == language
        and record.get("status") == "paused"
        for record in section(ledger, "drift_excursions")
    )


@dataclass
class CostBucket:
    """Synthetic spend and quality counts for one deployment."""

    release: str = ""
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    unknown_cost_calls: int = 0
    latency_ms: float = 0.0
    proposed: int = 0
    selected: int = 0
    abstentions: int = 0
    approvals: int = 0
    defects: int = 0
    approval_rate: float | None = None
    cost_per_approval: float | None = None
    qualification_score: float | None = None
    qualification_cost_usd: float | None = None
    drift_score: float | None = None
    drift_cost_usd: float | None = None
    defect_rate: float | None = None

    def add_call(self, call: Mapping[str, object]) -> None:
        """Accumulate one call."""
        self.calls += 1
        usage = call.get("usage")
        if isinstance(usage, dict):
            prompt = usage.get("prompt_tokens")
            if isinstance(prompt, int) and not isinstance(prompt, bool):
                self.input_tokens += prompt
            completion = usage.get("completion_tokens")
            if isinstance(completion, int) and not isinstance(completion, bool):
                self.output_tokens += completion
            cached = usage.get("cached_tokens")
            if isinstance(cached, int) and not isinstance(cached, bool):
                self.cached_tokens += cached
            cache_write = usage.get("cache_write_tokens")
            if isinstance(cache_write, int) and not isinstance(cache_write, bool):
                self.cache_write_tokens += cache_write
        cost = call.get("cost_usd")
        if isinstance(cost, int | float) and not isinstance(cost, bool):
            self.cost_usd = round(self.cost_usd + float(cost), 6)
        else:
            self.unknown_cost_calls += 1
        latency = call.get("latency_ms")
        if isinstance(latency, int | float) and not isinstance(latency, bool):
            self.latency_ms = round(self.latency_ms + float(latency), 3)

    def finish(
        self,
        *,
        proposed: int,
        selected: int,
        abstained: int,
    ) -> None:
        """Finalize derived rates."""
        self.proposed = proposed
        self.selected = selected
        self.abstentions = abstained
        self.approval_rate = round(selected / proposed, 4) if proposed else None
        self.cost_per_approval = (
            round(self.cost_usd / selected, 6)
            if selected and not self.unknown_cost_calls
            else None
        )
        self.defect_rate = (
            round(self.defects / self.approvals, 4) if self.approvals else None
        )

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready bucket."""
        return cast("dict[str, object]", asdict(self))


def _bucket_for(
    result: dict[str, dict[str, CostBucket]],
    language: str,
    deployment: str,
    release: str,
) -> CostBucket:
    """Return or create a bucket for a language and deployment."""
    return result.setdefault(language, {}).setdefault(
        deployment, CostBucket(release=release)
    )


def _add_qualification(
    result: dict[str, dict[str, CostBucket]], record: Mapping[str, object]
) -> None:
    """Accumulate one qualification record."""
    deployment = record.get("deployment")
    if not isinstance(deployment, str) or not deployment:
        return
    bucket = _bucket_for(
        result,
        str(record.get("language", "")),
        deployment,
        str(record.get("release") or ""),
    )
    score = record.get("score")
    if isinstance(score, int | float) and not isinstance(score, bool):
        bucket.qualification_score = float(score)
    cost = record.get("total_cost_usd")
    if isinstance(cost, int | float) and not isinstance(cost, bool):
        bucket.qualification_cost_usd = float(cost)
    calls = record.get("calls")
    if isinstance(calls, list):
        for call in calls:
            if isinstance(call, dict):
                bucket.add_call(call)


def _add_drift(
    result: dict[str, dict[str, CostBucket]], record: Mapping[str, object]
) -> None:
    """Accumulate one drift excursion."""
    deployment = record.get("deployment")
    if not isinstance(deployment, str) or not deployment:
        return
    bucket = _bucket_for(
        result,
        str(record.get("language", "")),
        deployment,
        str(record.get("release") or ""),
    )
    score = record.get("score")
    if isinstance(score, int | float) and not isinstance(score, bool):
        bucket.drift_score = float(score)
    cost = record.get("total_cost_usd")
    if isinstance(cost, int | float) and not isinstance(cost, bool):
        bucket.drift_cost_usd = float(cost)
    calls = record.get("calls")
    if isinstance(calls, list):
        for call in calls:
            if isinstance(call, dict):
                bucket.add_call(call)


def _add_approval(
    result: dict[str, dict[str, CostBucket]], record: Mapping[str, object]
) -> None:
    """Count one machine approval."""
    deployment = record.get("deployment")
    if not isinstance(deployment, str) or not deployment:
        return
    bucket = _bucket_for(
        result,
        str(record.get("language", "")),
        deployment,
        str(record.get("model_release") or ""),
    )
    bucket.approvals += 1


def _add_false_positive(
    result: dict[str, dict[str, CostBucket]], record: Mapping[str, object]
) -> None:
    """Count one recorded false positive."""
    deployment = record.get("deployment")
    if not isinstance(deployment, str) or not deployment:
        return
    bucket = _bucket_for(
        result,
        str(record.get("language", "")),
        deployment,
        str(record.get("model_release") or ""),
    )
    bucket.defects += 1


def estimate_tokens(text: str, chars_per_token: float) -> int:
    """Estimate a token count from a character count."""
    return max(1, math.ceil(len(text) / chars_per_token))


def _output_range(source_tokens: int, deployment: Deployment) -> tuple[int, int]:
    """Return a low/high completion-token estimate."""
    low = max(1, source_tokens)
    high = max(low * 2, low + 8)
    if deployment.limits is not None and deployment.limits.output is not None:
        high = min(high, deployment.limits.output)
    return low, high


@dataclass
class _EstimateAccumulator:
    """Mutable estimate for one deployment."""

    deployment: str
    release: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    low_cost_usd: float = 0.0
    high_cost_usd: float = 0.0
    price_known: bool = True
    currency: str = "USD"

    def add(
        self,
        deployment: Deployment,
        input_tokens: int,
        low_output: int,
        high_output: int,
    ) -> None:
        """Add one estimated call."""
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += high_output
        usage_low = Usage(
            prompt_tokens=input_tokens,
            completion_tokens=low_output,
            total_tokens=input_tokens + low_output,
            cached_tokens=0,
            cache_write_tokens=0,
        )
        usage_high = Usage(
            prompt_tokens=input_tokens,
            completion_tokens=high_output,
            total_tokens=input_tokens + high_output,
            cached_tokens=0,
            cache_write_tokens=0,
        )
        low_cost, _ = compute_cost(usage_low, deployment.cost)
        high_cost, _ = compute_cost(usage_high, deployment.cost)
        if low_cost is None or high_cost is None:
            self.price_known = False
        else:
            self.low_cost_usd += low_cost
            self.high_cost_usd += high_cost
        if deployment.cost is not None:
            self.currency = deployment.cost.currency

    def result(self) -> DeploymentEstimate:
        """Return an immutable estimate."""
        return DeploymentEstimate(
            deployment=self.deployment,
            release=self.release,
            calls=self.calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            low_cost_usd=(round(self.low_cost_usd, 6) if self.price_known else None),
            high_cost_usd=(round(self.high_cost_usd, 6) if self.price_known else None),
            currency=self.currency,
            price_known=self.price_known,
        )


def _finish_estimate(
    action: str,
    language: str,
    accumulators: Mapping[str, _EstimateAccumulator],
    *,
    chars_per_token: float,
    sources: int,
) -> ActionEstimate:
    """Build an action estimate from per-deployment accumulators."""
    deployments = tuple(item.result() for item in accumulators.values())
    known = [item for item in deployments if item.price_known]
    low = (
        round(sum(item.low_cost_usd or 0.0 for item in known), 6)
        if len(known) == len(deployments)
        else None
    )
    high = (
        round(sum(item.high_cost_usd or 0.0 for item in known), 6)
        if len(known) == len(deployments)
        else None
    )
    return ActionEstimate(
        action=action,
        language=language,
        deployments=deployments,
        low_cost_usd=low,
        high_cost_usd=high,
        assumptions={
            "method": "characters / chars_per_token",
            "chars_per_token": chars_per_token,
            "sources": sources,
            "authoritative": "provider-reported usage after the call",
        },
    )


def estimate_gate(
    config: GateConfig,
    language: str,
    sources: Sequence[str],
    *,
    context: str = "",
    chars_per_token: float | None = None,
) -> ActionEstimate:
    """Estimate the cost of gating a set of strings."""
    chars = chars_per_token or config.thresholds.get(
        "chars_per_token", DEFAULT_CHARS_PER_TOKEN
    )
    accumulators: dict[str, _EstimateAccumulator] = {}

    def accumulator(deployment: Deployment) -> _EstimateAccumulator:
        return accumulators.setdefault(
            deployment.id,
            _EstimateAccumulator(deployment.id, deployment.release),
        )

    for source in sources:
        source_tokens = estimate_tokens(source, chars)
        for deployment in config.proposers:
            prompt = prompt_for("translate", language, source, context)
            low, high = _output_range(source_tokens, deployment)
            accumulator(deployment).add(
                deployment, estimate_tokens(prompt, chars), low, high
            )
        judge = config.judges[0]
        judge_prompt = (
            f"Choose the best {language} translation of this source string.\n"
            f"Source: {source}\nA: proposal\nB: proposal"
        )
        high_output = _output_range(source_tokens, config.proposers[0])[1]
        accumulator(judge).add(
            judge,
            estimate_tokens(judge_prompt, chars) + 2 * high_output,
            1,
            1,
        )
        if len(source) >= _SENTENCE_CHARS and " " in source:
            back_prompt = prompt_for("backtranslate", language, source)
            low, high = _output_range(source_tokens, judge)
            accumulator(judge).add(
                judge,
                estimate_tokens(back_prompt, chars) + high,
                low,
                high,
            )
    return _finish_estimate(
        "gate", language, accumulators, chars_per_token=chars, sources=len(sources)
    )


def estimate_qualification(
    config: GateConfig,
    request: QualificationRequest,
    *,
    chars_per_token: float | None = None,
) -> ActionEstimate:
    """Estimate the cost of qualifying a release for a language."""
    chars = chars_per_token or config.thresholds.get(
        "chars_per_token", DEFAULT_CHARS_PER_TOKEN
    )
    deployments = config.deployments_for(request.release)
    accumulators: dict[str, _EstimateAccumulator] = {}
    if deployments:
        deployment = deployments[0]
        accumulator = _EstimateAccumulator(deployment.id, deployment.release)
        accumulators[deployment.id] = accumulator
        for entry in request.entries:
            source_tokens = estimate_tokens(entry.msgid, chars)
            prompt = prompt_for("translate", request.language, entry.msgid)
            low, high = _output_range(source_tokens, deployment)
            accumulator.add(deployment, estimate_tokens(prompt, chars), low, high)
    return _finish_estimate(
        "qualification",
        request.language,
        accumulators,
        chars_per_token=chars,
        sources=len(request.entries),
    )


def estimate_drift(
    config: GateConfig,
    request: DriftRequest,
    *,
    chars_per_token: float | None = None,
) -> ActionEstimate:
    """Estimate the cost of a drift probe."""
    chars = chars_per_token or config.thresholds.get(
        "chars_per_token", DEFAULT_CHARS_PER_TOKEN
    )
    deployment = config.deployments.get(request.deployment_id)
    accumulators: dict[str, _EstimateAccumulator] = {}
    if deployment is not None:
        accumulator = _EstimateAccumulator(deployment.id, deployment.release)
        accumulators[deployment.id] = accumulator
        for item in request.probe:
            source_tokens = estimate_tokens(item["msgid"], chars)
            prompt = prompt_for("translate", request.language, item["msgid"])
            low, high = _output_range(source_tokens, deployment)
            accumulator.add(deployment, estimate_tokens(prompt, chars), low, high)
    return _finish_estimate(
        "drift",
        request.language,
        accumulators,
        chars_per_token=chars,
        sources=len(request.probe),
    )


def ensure_budget(estimate: ActionEstimate, maximum: float | None) -> None:
    """Refuse an action whose high estimate exceeds the budget."""
    if maximum is None:
        return
    if estimate.high_cost_usd is None:
        msg = (
            f"cannot enforce a {maximum} budget: the estimate is unknown; "
            "add prices to the deployments"
        )
        raise BudgetExceededError(msg)
    if estimate.high_cost_usd <= maximum:
        return
    over = [
        item.deployment
        for item in estimate.deployments
        if item.high_cost_usd is not None and item.high_cost_usd > maximum
    ]
    msg = f"estimated cost {estimate.high_cost_usd} exceeds budget {maximum}" + (
        f" for {', '.join(over)}" if over else ""
    )
    raise BudgetExceededError(msg)


def _print_estimate(estimate: ActionEstimate) -> None:
    """Print a compact estimate."""
    print(
        f"{estimate.action} {estimate.language}: "
        f"low {estimate.low_cost_usd} high {estimate.high_cost_usd}"
    )
    for item in estimate.deployments:
        print(
            f"  {item.deployment:<24} {item.release:<28} "
            f"calls {item.calls:>4} input {item.input_tokens:>8} "
            f"output {item.output_tokens:>8} low {item.low_cost_usd} "
            f"high {item.high_cost_usd}"
        )
    print(f"  assumption: {estimate.assumptions['method']}")


def _print_qualification(record: Mapping[str, object]) -> None:
    """Print a compact qualification result."""
    release = record.get("release")
    language = record.get("language")
    reason = record.get("reason")
    if record.get("qualified") is True:
        outcome = "qualified"
    elif isinstance(reason, str) and reason:
        outcome = f"ineligible: {reason}"
    else:
        outcome = "not qualified"
    parts = [
        f"score {record.get('score')}",
        f"tolerance {record.get('tolerance')}",
        f"baseline {record.get('baseline_size')}",
    ]
    deployment = record.get("deployment")
    if isinstance(deployment, str) and deployment:
        parts.append(f"deployment {deployment}")
    parts.append(f"cost {record.get('total_cost_usd')}")
    print(f"qualification {language} ({release}): {outcome} ({', '.join(parts)})")


def _process_gate_call(
    call: Mapping[str, object],
    language: str,
    result: dict[str, dict[str, CostBucket]],
    proposed: dict[tuple[str, str], set[int]],
    run_index: int,
) -> None:
    """Accumulate one call from a gate run."""
    deployment = call.get("deployment")
    if not isinstance(deployment, str) or not deployment:
        return
    bucket = _bucket_for(result, language, deployment, str(call.get("release") or ""))
    bucket.add_call(call)
    if call.get("role") == "proposer":
        proposed.setdefault((language, deployment), set()).add(run_index)


@dataclass
class RunIndexes:
    """Run-level index sets used by the cost report."""

    proposed: dict[tuple[str, str], set[int]] = field(default_factory=dict)
    selected: dict[tuple[str, str], set[int]] = field(default_factory=dict)
    abstained: dict[tuple[str, str], set[int]] = field(default_factory=dict)


def _process_gate_run(
    run_index: int,
    run: Mapping[str, object],
    result: dict[str, dict[str, CostBucket]],
    indexes: RunIndexes,
) -> None:
    """Accumulate one gate run and its outcome."""
    language = str(run.get("language", ""))
    calls = run.get("calls")
    if isinstance(calls, list):
        for call in calls:
            if isinstance(call, dict):
                _process_gate_call(call, language, result, indexes.proposed, run_index)
    winning = run.get("winning_deployment")
    if isinstance(winning, str):
        indexes.selected.setdefault((language, winning), set()).add(run_index)
    if run.get("outcome") != "abstained":
        return
    proposers = run.get("proposers")
    if isinstance(proposers, list):
        for deployment in proposers:
            if isinstance(deployment, str):
                indexes.abstained.setdefault((language, deployment), set()).add(
                    run_index
                )


def costs_report(
    ledger: Mapping[str, object],
    *,
    languages: Iterable[str] = (),
) -> dict[str, object]:
    """Aggregate spend and quality by language and deployment."""
    result: dict[str, dict[str, CostBucket]] = {language: {} for language in languages}
    indexes = RunIndexes()

    for run_index, run in enumerate(section(ledger, "gate_runs")):
        _process_gate_run(run_index, run, result, indexes)
    for record in section(ledger, "qualifications"):
        _add_qualification(result, record)
    for record in section(ledger, "drift_excursions"):
        _add_drift(result, record)
    for record in approvals(ledger):
        if record.get("provenance_class") in MACHINE_PROVENANCE_CLASSES:
            _add_approval(result, record)
    for record in section(ledger, "false_positives"):
        _add_false_positive(result, record)

    for language, deployments in result.items():
        for deployment, bucket in deployments.items():
            bucket.finish(
                proposed=len(indexes.proposed.get((language, deployment), set())),
                selected=len(indexes.selected.get((language, deployment), set())),
                abstained=len(indexes.abstained.get((language, deployment), set())),
            )
    return {
        "languages": {
            language: {
                deployment: bucket.as_dict()
                for deployment, bucket in deployments.items()
            }
            for language, deployments in result.items()
        }
    }


def _print_costs(payload: Mapping[str, object]) -> None:
    """Print a compact cost/performance table."""
    languages = payload["languages"]
    if not isinstance(languages, dict):
        return
    print(
        "language  deployment  calls  cost_usd  approvals  abstentions  "
        "approval_rate  cost/approval"
    )
    for language in sorted(languages):
        deployments = languages[language]
        if not isinstance(deployments, dict):
            continue
        for deployment in sorted(deployments):
            bucket = deployments[deployment]
            if not isinstance(bucket, dict):
                continue
            print(
                f"{language:<8}  {deployment:<24}  {bucket['calls']:>5}  "
                f"{bucket['cost_usd']!s:>8}  {bucket['approvals']:>9}  "
                f"{bucket['abstentions']:>11}  {bucket['approval_rate']!s:>13}  "
                f"{bucket['cost_per_approval']!s:>13}"
            )


def capability_report(
    ledger: Mapping[str, object],
    config: GateConfig,
    *,
    languages: Iterable[str] = (),
) -> dict[str, object]:
    """Report qualified releases and deployments per language."""
    all_languages: dict[str, dict[str, object]] = {}
    known_languages = (
        set(languages)
        | {
            str(record.get("language"))
            for record in approvals(ledger)
            if record.get("language") is not None and record.get("language") != ""
        }
        | {
            str(record.get("language"))
            for record in section(ledger, "qualifications")
            if record.get("language") is not None and record.get("language") != ""
        }
    )
    for language in known_languages:
        all_languages[language] = {
            "releases": [],
            "deployments": [],
            "retired_releases": [],
        }

    for record in section(ledger, "qualifications"):
        language = str(record.get("language"))
        bucket = all_languages.setdefault(
            language,
            {"releases": [], "deployments": [], "retired_releases": []},
        )
        if record.get("qualified") is not True:
            continue
        release = str(record.get("release"))
        bucket["releases"].append(release)
        if release not in config.releases:
            bucket["retired_releases"].append(release)
        for conformance in section(ledger, "conformances"):
            if (
                conformance.get("release") == release
                and conformance.get("qualified") is True
            ):
                bucket["deployments"].append(conformance.get("deployment"))

    for bucket in all_languages.values():
        qualified = cast("list[str]", bucket["releases"])
        bucket["machine_path"] = any(
            release in config.releases for release in qualified
        )
    no_machine_path = [
        language
        for language, bucket in all_languages.items()
        if not bucket["machine_path"]
    ]
    return {
        "languages": all_languages,
        "no_machine_path": sorted(no_machine_path),
    }


def random_sample(
    ledger: Mapping[str, object],
    language: str,
    size: int,
    seed: int,
) -> list[ApprovalRecord]:
    """Return a deterministic pseudo-random sample of machine approvals."""
    candidates = [
        record
        for record in approvals(ledger)
        if record.get("language") == language
        and record.get("provenance_class") in MACHINE_PROVENANCE_CLASSES
    ]
    ordered = sorted(
        candidates,
        key=lambda record: hashlib.sha256(
            f"{seed}:{record.get('msgid')}:{record.get('msgctxt')}".encode()
        ).hexdigest(),
    )
    return ordered[: min(size, len(ordered))]


def record_false_positive(
    ledger: dict[str, object],
    record: Mapping[str, object],
    *,
    note: str,
    approval_date: str | None = None,
) -> None:
    """Record a human correction of a machine-approved string."""
    add_section_record(
        ledger,
        "false_positives",
        {
            "language": record.get("language"),
            "msgctxt": record.get("msgctxt"),
            "msgid": record.get("msgid"),
            "msgid_plural": record.get("msgid_plural"),
            "provenance_class": record.get("provenance_class"),
            "model_release": record.get("model_release"),
            "deployment": record.get("deployment"),
            "note": note,
            "date": approval_date or _today(),
        },
    )


def defect_rate(ledger: Mapping[str, object], language: str) -> float:
    """Return false positives divided by machine approvals for a language."""
    machine = [
        record
        for record in approvals(ledger)
        if record.get("language") == language
        and record.get("provenance_class") in MACHINE_PROVENANCE_CLASSES
    ]
    if not machine:
        return 0.0
    keys = {
        (
            str(record.get("msgctxt") or ""),
            str(record.get("msgid")),
            str(record.get("msgid_plural") or ""),
        )
        for record in section(ledger, "false_positives")
        if record.get("language") == language
    }
    hits = sum(
        1
        for record in machine
        if (
            str(record.get("msgctxt") or ""),
            str(record.get("msgid")),
            str(record.get("msgid_plural") or ""),
        )
        in keys
    )
    return hits / len(machine)


def demote_if_over_threshold(
    ledger: dict[str, object],
    language: str,
    threshold: float,
    *,
    approval_date: str | None = None,
) -> bool:
    """Revoke a language's machine approvals when its defect rate is too high."""
    if defect_rate(ledger, language) <= threshold:
        return False
    add_section_record(
        ledger,
        "revocations",
        {
            "scope": "language",
            "value": language,
            "reason": "defect rate above threshold",
            "date": approval_date or _today(),
        },
    )
    return True


def revoke(
    ledger_path: Path,
    scope: str,
    value: str,
    *,
    reason: str = "manual revocation",
    approval_date: str | None = None,
) -> None:
    """Record a language, deployment or release revocation."""
    if scope not in {"language", "deployment", "release"}:
        msg = f"unknown revocation scope {scope!r}"
        raise GateError(msg)
    ledger = load_ledger(ledger_path)
    add_section_record(
        ledger,
        "revocations",
        {
            "scope": scope,
            "value": value,
            "reason": reason,
            "date": approval_date or _today(),
        },
    )
    write_ledger(ledger, ledger_path)


def approve_decision(
    catalog_path: Path,
    ledger_path: Path,
    msgid: str,
    decision: GateDecision,
) -> None:
    """Clear fuzzy on an approved entry and record the approval."""
    if not decision.approved or decision.record is None:
        msg = "cannot approve an abstained decision"
        raise GateError(msg)
    catalog = polib.pofile(str(catalog_path))
    entry = catalog.find(msgid)
    if entry is None:
        msg = f"{msgid!r} is not in {catalog_path}"
        raise GateError(msg)
    entry.flags = [flag for flag in entry.flags if flag != "fuzzy"]
    catalog.save(str(catalog_path))
    ledger = load_ledger(ledger_path)
    _replace_section(
        ledger,
        "approvals",
        decision.record,
        key_fields=("language", "msgctxt", "msgid", "msgid_plural"),
    )
    write_ledger(ledger, ledger_path)


def _probe_item(entry: polib.POEntry) -> tuple[str, dict[str, str]]:
    """Return the stratum and item for one human entry."""
    target = entry.msgstr
    if entry.msgid_plural:
        stratum = "plural"
        target = next(
            (value for value in (entry.msgstr_plural or {}).values() if value.strip()),
            "",
        )
    elif "%" in entry.msgid or "{" in entry.msgid:
        stratum = "placeholder"
    elif is_high_impact(entry.msgid, entry.occurrences):
        stratum = "high-impact"
    elif len(entry.msgid) <= _SHORT_LABEL_CHARS:
        stratum = "short"
    else:
        stratum = "sentence"
    return stratum, {"msgid": entry.msgid, "msgstr": target}


def _probe_strata(
    ledger: Mapping[str, object],
    language: str,
    catalog: polib.POFile,
) -> dict[str, list[dict[str, str]]]:
    """Collect human historical entries into probe strata."""
    by_key = {_entry_key(entry): entry for entry in catalog if not entry.obsolete}
    strata: dict[str, list[dict[str, str]]] = {
        "short": [],
        "sentence": [],
        "placeholder": [],
        "plural": [],
        "high-impact": [],
    }
    seen: set[tuple[str, str, str]] = set()
    for record in approvals(ledger):
        if record.get("language") != language:
            continue
        if record.get("provenance_class") != "human-historical":
            continue
        key = (
            str(record.get("msgctxt") or ""),
            str(record.get("msgid")),
            str(record.get("msgid_plural") or ""),
        )
        entry = by_key.get(key)
        if entry is None or key in seen:
            continue
        seen.add(key)
        stratum, item = _probe_item(entry)
        strata[stratum].append(item)
    return strata


def _select_probe(
    strata: Mapping[str, Sequence[dict[str, str]]],
    size: int,
) -> list[dict[str, str]]:
    """Round-robin the strata so short labels and sentences both appear."""
    chosen: list[dict[str, str]] = []
    index = 0
    while len(chosen) < size:
        added = False
        for items in strata.values():
            if index < len(items):
                chosen.append(items[index])
                added = True
                if len(chosen) == size:
                    break
        if not added:
            break
        index += 1
    return chosen


def build_probes(
    ledger: Mapping[str, object],
    catalogs: Mapping[str, polib.POFile],
    output_dir: Path,
    *,
    size: int = 40,
) -> dict[str, int]:
    """Write a stratified human-translation probe per language."""
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for language, catalog in catalogs.items():
        chosen = _select_probe(_probe_strata(ledger, language, catalog), size)
        payload = {"language": language, "version": 1, "items": chosen}
        (output_dir / f"{language}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        counts[language] = len(chosen)
    return counts


def load_probe(path: Path) -> list[dict[str, str]]:
    """Load one drift-probe file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read probe {path}: {error}"
        raise GateError(msg) from error
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        msg = f"{path} has no 'items' list"
        raise GateError(msg)
    return [cast("dict[str, str]", item) for item in items]


def _catalogs_from_directory(directory: Path) -> dict[str, polib.POFile]:
    """Load every ``<language>.po`` catalog in a directory."""
    return {
        path.stem: polib.pofile(str(path)) for path in sorted(directory.glob("*.po"))
    }


def _command_validate(args: argparse.Namespace, config: GateConfig) -> int:
    """Print the validated configuration size."""
    roles = load_roles(args.roles)
    validate_roles(config, roles)
    print(
        f"valid: {len(config.releases)} releases, {len(config.deployments)} deployments"
    )
    return 0


def _command_capability(args: argparse.Namespace, config: GateConfig) -> int:
    """Print the capability report."""
    ledger = load_ledger(args.ledger)
    languages = [
        path.stem for path in sorted((REPO_ROOT / "po" / "scantpaper").glob("*.po"))
    ]
    print(
        json.dumps(
            capability_report(ledger, config, languages=languages),
            indent=2,
        )
    )
    return 0


def _command_costs(args: argparse.Namespace, _config: GateConfig) -> int:
    """Print the cost/performance report."""
    ledger = load_ledger(args.ledger)
    languages = [args.language] if args.language else []
    payload = costs_report(ledger, languages=languages)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_costs(payload)
    return 0


def _command_estimate(args: argparse.Namespace, config: GateConfig) -> int:
    """Estimate the cost of a qualification, drift probe or gate action."""
    language = args.language
    try:
        if args.action == "qualification":
            if not args.release:
                print(
                    "error: qualification estimate needs --release",
                    file=sys.stderr,
                )
                return 1
            ledger = load_ledger(args.ledger)
            catalog_path = args.catalog or (
                REPO_ROOT / "po" / "scantpaper" / f"{language}.po"
            )
            catalog = polib.pofile(str(catalog_path))
            entries = _held_out(ledger, catalog, language, args.count or 20)
            estimate = estimate_qualification(
                config,
                QualificationRequest(
                    args.release,
                    language,
                    entries,
                    budget_usd=args.max_cost,
                ),
                chars_per_token=args.chars_per_token,
            )
        elif args.action == "drift":
            if not args.deployment:
                print(
                    "error: drift estimate needs --deployment",
                    file=sys.stderr,
                )
                return 1
            probe_path = args.probe or (DEFAULT_PROBE_DIR / f"{language}.json")
            estimate = estimate_drift(
                config,
                DriftRequest(
                    args.release or "",
                    args.deployment,
                    language,
                    load_probe(probe_path),
                    budget_usd=args.max_cost,
                ),
                chars_per_token=args.chars_per_token,
            )
        else:
            sources = args.msgid or ["A source string"] * (args.count or 1)
            estimate = estimate_gate(
                config,
                language,
                sources,
                chars_per_token=args.chars_per_token,
            )
        ensure_budget(estimate, args.max_cost)
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(estimate.as_dict(), ensure_ascii=False, indent=2))
    else:
        _print_estimate(estimate)
    return 0


def _command_qualify(args: argparse.Namespace, config: GateConfig) -> int:
    """Qualify one release for one language and record the result."""
    if args.count <= 0:
        print("error: --count must be positive", file=sys.stderr)
        return 1
    if args.release not in config.releases or not config.deployments_for(args.release):
        print(
            f"error: release {args.release!r} is not configured",
            file=sys.stderr,
        )
        return 1
    catalog_path = args.catalog or (
        REPO_ROOT / "po" / "scantpaper" / f"{args.language}.po"
    )
    try:
        catalog = polib.pofile(str(catalog_path))
    except OSError as error:
        print(
            f"error: cannot read catalog {catalog_path}: {error}",
            file=sys.stderr,
        )
        return 1
    ledger = load_ledger(args.ledger)
    entries = _held_out(ledger, catalog, args.language, args.count)
    request = QualificationRequest(
        args.release,
        args.language,
        entries,
        budget_usd=args.max_cost,
    )
    try:
        record = qualify_release(
            ledger,
            config,
            request,
            OpenAICompatibleClient(),
        )
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        write_ledger(ledger, args.ledger)
    except (LedgerError, OSError) as error:
        print(
            f"error: cannot write ledger {args.ledger}: {error}",
            file=sys.stderr,
        )
        return 1
    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        _print_qualification(record)
    return 0


def _command_revoke(args: argparse.Namespace, _config: GateConfig) -> int:
    """Record a revocation."""
    revoke(args.ledger, args.scope, args.value)
    print(f"revoked {args.scope} {args.value}")
    return 0


def _command_sample(args: argparse.Namespace, _config: GateConfig) -> int:
    """Print a sample of machine approvals."""
    ledger = load_ledger(args.ledger)
    records = random_sample(ledger, args.language, args.size, args.seed)
    print(
        json.dumps(
            [
                {
                    "msgid": record.get("msgid"),
                    "msgstr": record.get("msgstr"),
                    "release": record.get("model_release"),
                    "deployment": record.get("deployment"),
                }
                for record in records
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _command_build_probes(args: argparse.Namespace, _config: GateConfig) -> int:
    """Regenerate the drift-probe directory."""
    ledger = load_ledger(args.ledger)
    counts = build_probes(
        ledger,
        _catalogs_from_directory(REPO_ROOT / "po" / "scantpaper"),
        args.probe_dir,
    )
    print(f"wrote {len(counts)} probes")
    return 0


def _command_gate(args: argparse.Namespace, config: GateConfig) -> int:
    """Run the gate for one string and write its decision."""
    try:
        estimate = estimate_gate(
            config,
            args.language,
            [args.msgid],
            context=args.context,
        )
        ensure_budget(estimate, args.max_cost)
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    decision = run_gate(
        args.msgid,
        args.language,
        config,
        OpenAICompatibleClient(),
        options=GateOptions(context=args.context),
    )
    ledger = load_ledger(args.ledger)
    record_gate_run(ledger, decision, args.language)
    write_ledger(ledger, args.ledger)
    payload = {
        "approved": decision.approved,
        "reason": decision.reason,
        "translation": decision.translation,
        "record": decision.record,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


def _command_approve(args: argparse.Namespace, _config: GateConfig) -> int:
    """Apply a saved approved decision to a catalog and the ledger."""
    payload = json.loads(args.decision.read_text(encoding="utf-8"))
    record = payload.get("record") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        print("error: the decision was not approved", file=sys.stderr)
        return 1
    if not isinstance(record, dict):
        print("error: the decision has no approval record", file=sys.stderr)
        return 1
    decision = GateDecision(
        approved=True,
        reason=str(payload.get("reason", "")),
        translation=payload.get("translation"),
        record=cast("ApprovalRecord", record),
    )
    approve_decision(args.catalog, args.ledger, args.msgid, decision)
    print(f"approved {args.msgid!r}")
    return 0


def _dispatch(args: argparse.Namespace, config: GateConfig) -> int:
    """Route one subcommand to its handler."""
    handlers = {
        "validate": lambda: _command_validate(args, config),
        "capability": lambda: _command_capability(args, config),
        "costs": lambda: _command_costs(args, config),
        "estimate": lambda: _command_estimate(args, config),
        "qualify": lambda: _command_qualify(args, config),
        "revoke": lambda: _command_revoke(args, config),
        "sample": lambda: _command_sample(args, config),
        "build-probes": lambda: _command_build_probes(args, config),
        "gate": lambda: _command_gate(args, config),
        "approve": lambda: _command_approve(args, config),
    }
    handler = handlers.get(args.command)
    if handler is None:
        msg = f"unknown command {args.command!r}"
        raise GateError(msg)
    return handler()


def _build_parser() -> argparse.ArgumentParser:
    """Build the gate command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--probe-dir", type=Path, default=DEFAULT_PROBE_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Validate the configuration")
    sub.add_parser("capability", help="Report per-language machine capability")
    costs_parser = sub.add_parser("costs", help="Report spend and quality")
    costs_parser.add_argument("--language")
    costs_parser.add_argument("--json", action="store_true")
    estimate_parser = sub.add_parser("estimate", help="Estimate an action cost")
    estimate_parser.add_argument(
        "--action", choices=("qualification", "drift", "gate"), required=True
    )
    estimate_parser.add_argument("--language", required=True)
    estimate_parser.add_argument("--release")
    estimate_parser.add_argument("--deployment")
    estimate_parser.add_argument("--catalog", type=Path)
    estimate_parser.add_argument("--probe", type=Path)
    estimate_parser.add_argument("--msgid", action="append", default=[])
    estimate_parser.add_argument("--count", type=int)
    estimate_parser.add_argument("--chars-per-token", type=float)
    estimate_parser.add_argument("--max-cost", type=float)
    estimate_parser.add_argument("--json", action="store_true")
    qualify_parser = sub.add_parser("qualify", help="Qualify a release for a language")
    qualify_parser.add_argument("--release", required=True)
    qualify_parser.add_argument("--language", required=True)
    qualify_parser.add_argument("--catalog", type=Path)
    qualify_parser.add_argument("--count", type=int, default=20)
    qualify_parser.add_argument("--max-cost", type=float)
    qualify_parser.add_argument("--json", action="store_true")
    sub.add_parser("build-probes", help="Regenerate the drift-probe files")
    gate_parser = sub.add_parser("gate", help="Gate one string")
    gate_parser.add_argument("--language", required=True)
    gate_parser.add_argument("--msgid", required=True)
    gate_parser.add_argument("--context", default="")
    gate_parser.add_argument("--output", type=Path)
    gate_parser.add_argument("--max-cost", type=float)
    approve_parser = sub.add_parser("approve", help="Apply an approved decision")
    approve_parser.add_argument("--catalog", type=Path, required=True)
    approve_parser.add_argument("--msgid", required=True)
    approve_parser.add_argument("--decision", type=Path, required=True)
    revoke_parser = sub.add_parser("revoke", help="Revoke approvals")
    revoke_parser.add_argument("--scope", required=True)
    revoke_parser.add_argument("--value", required=True)
    sample_parser = sub.add_parser("sample", help="Sample machine approvals")
    sample_parser.add_argument("--language", required=True)
    sample_parser.add_argument("--size", type=int, default=20)
    sample_parser.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the gate command."""
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        config = load_config(args.config)
        return _dispatch(args, config)
    except (GateError, LedgerError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

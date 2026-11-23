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
import contextlib
import hashlib
import http.client
import json
import math
import os
import re
import shlex
import socket
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlparse

import polib
from tm_index import dominant_match
from translation_ledger import (
    EVIDENCE_PATH,
    ApprovalContext,
    ApprovalRecord,
    LedgerError,
    add_section_record,
    approvals,
    compact_evidence,
    compact_operational_record,
    load_gate_run_calls,
    load_language_ledger,
    load_ledger,
    make_record,
    section,
    write_evidence,
    write_global_ledger,
    write_language_ledger,
    write_ledger,
)
from translation_ledger import (
    LEDGER_PATH as DEFAULT_LEDGER_PATH,
)
from translation_policy import (
    MACHINE_PROVENANCE_CLASSES,
    has_spaced_printf,
    is_high_impact,
    is_mechanical_rebase,
    placeholder_tokens,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from datetime import tzinfo
    from typing import TextIO

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
PLURAL_PROMPT_VERSION = "2026-11-08"
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_SECONDS_PER_ENTRY = 18.0
LOCAL_OVERHEAD_SECONDS = 0.1
ETA_WINDOW = 20
ETA_ROUND_SECONDS = 300.0
ETA_PRIOR_SPREAD = 0.25
MINUTE_SECONDS = 60.0
STALL_FACTOR = 2.0
STALL_FLOOR_SECONDS = 60.0
STATUS_RECENT_SECONDS = 24 * 60 * 60
STATUS_SESSION_GAP_SECONDS = 120.0
STATUS_ABANDONED_AFTER_SECONDS = 600.0
DEFAULT_JUDGE_TIMEOUT_SECONDS = 20.0
PROGRESS_MODES = ("auto", "line", "none")
PRIOR_MIN_SAMPLES = 3
_PROC_STAT_MIN_FIELDS = 3
STATE_DIR = REPO_ROOT / ".cache" / "translate"
CATALOGS_DIR = REPO_ROOT / "po" / "scantpaper"


class Clock(Protocol):
    """Wall-clock and monotonic time sources, injectable for tests."""

    def now(self) -> datetime:
        """Return the current UTC wall time."""

    def monotonic(self) -> float:
        """Return a monotonically increasing seconds counter."""

    def local_tz(self) -> tzinfo:
        """Return the operator's local time zone."""


class SystemClock:
    """The production clock: UTC wall time, monotonic seconds, local tz."""

    def now(self) -> datetime:
        """Return the current UTC wall time."""
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        """Return a monotonic second counter."""
        return time.monotonic()

    def local_tz(self) -> tzinfo:
        """Return the operator's local time zone."""
        return datetime.now().astimezone().tzinfo or timezone.utc


_status_clock: Clock = SystemClock()
_batch_clock: Clock = SystemClock()


def _prompt_hash(version: str = PROMPT_VERSION) -> str:
    """Return the deployment-facing hash of a prompt version."""
    return "sha256:" + hashlib.sha256(version.encode()).hexdigest()[:16]


PROMPT_HASH = _prompt_hash()
PLURAL_PROMPT_HASH = _prompt_hash(PLURAL_PROMPT_VERSION)


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
    forms: dict[int, str] | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready proposal record."""
        record: dict[str, object] = {
            "deployment": self.deployment,
            "release": self.release,
            "family": self.family,
            "text": self.text,
            "call": self.completion.as_dict(),
        }
        if self.forms is not None:
            record["forms"] = {
                str(index): self.forms[index] for index in sorted(self.forms)
            }
        return record


@dataclass(frozen=True)
class PluralSource:
    """One plural entry's source forms and declared plural rule."""

    msgid: str
    msgid_plural: str
    nplurals: int
    plural_expression: str

    def source_forms(self) -> tuple[str, ...]:
        """Return the source text for each form index."""
        return (self.msgid, *((self.msgid_plural,) * (self.nplurals - 1)))


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
    language_thresholds: dict[str, dict[str, float]] = field(default_factory=dict)

    def threshold(
        self,
        name: str,
        *,
        language: str | None = None,
        default: float,
    ) -> float:
        """Return a threshold, preferring a language-specific override."""
        if language is not None:
            override = self.language_thresholds.get(language, {})
            if name in override:
                return override[name]
        return self.thresholds.get(name, default)

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
    forms: dict[int, str] | None = None
    record: ApprovalRecord | None = None
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GateOptions:
    """Optional inputs for a gate run."""

    context: str = ""
    occurrences: tuple[object, ...] = ()
    tm_db: Path | None = None
    evidence_path: Path | None = None


@dataclass(frozen=True)
class GateRunOptions:
    """Optional metadata for one recorded gate run."""

    action: str = "gate"
    timestamp: str | None = None
    evidence_path: Path | None = None


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
    evidence_path: Path | None = None


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


def _load_language_thresholds(
    data: Mapping[str, object], path: Path
) -> dict[str, dict[str, float]]:
    """Parse per-language threshold overrides."""
    raw = data.get("language_thresholds", {})
    if not isinstance(raw, dict):
        msg = f"{path} language_thresholds must be an object"
        raise GateError(msg)
    overrides: dict[str, dict[str, float]] = {}
    for language, values in raw.items():
        if not isinstance(language, str) or not language:
            msg = f"{path} language_thresholds has an invalid language"
            raise GateError(msg)
        if not isinstance(values, dict):
            msg = f"{path} language_thresholds[{language!r}] must be an object"
            raise GateError(msg)
        parsed: dict[str, float] = {}
        for name, value in values.items():
            if not isinstance(name, str) or not isinstance(value, int | float):
                msg = (
                    f"{path} language_thresholds[{language!r}] "
                    "must map names to numbers"
                )
                raise GateError(msg)
            if name in {"qualification", "drift"} and not 0 <= float(value) <= 1:
                msg = (
                    f"{path} language_thresholds[{language!r}][{name!r}] "
                    "must be between 0 and 1"
                )
                raise GateError(msg)
            parsed[name] = float(value)
        overrides[language] = parsed
    return overrides


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
        language_thresholds=_load_language_thresholds(data, path),
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

    def complete(
        self,
        deployment: Deployment,
        prompt: str,
        *,
        timeout: float | None = None,
    ) -> Completion:
        """Return one completion for a deployment.

        ``timeout`` overrides the client's transport timeout for this call
        only; ``None`` keeps the transport default.
        """


class OpenAICompatibleClient:
    """A minimal OpenAI-compatible chat-completions client.

    The constructor does not touch the environment. A missing key is reported
    by name only, never by value.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        """Store the request timeout without reading any credential."""
        self.timeout = timeout

    def complete(
        self,
        deployment: Deployment,
        prompt: str,
        *,
        timeout: float | None = None,
    ) -> Completion:
        """Send one chat completion and return its text, usage and cost.

        ``timeout`` overrides ``self.timeout`` for this call only.
        """
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
            parsed.hostname,
            parsed.port,
            timeout=self.timeout if timeout is None else timeout,
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


_PLURAL_NPLURALS_RE = re.compile(r"nplurals\s*=\s*(\d+)")
_PLURAL_RULE_RE = re.compile(r"plural\s*=\s*([^;]+)")
_PLURAL_FORM_LINE_RE = re.compile(r"^\s*(\d+)\s*[:.)]\s?(.*)$")


def catalog_plural_info(catalog: polib.POFile) -> tuple[int | None, str]:
    """Return the declared plural form count and rule from a catalog."""
    header = catalog.metadata.get("Plural-Forms", "")
    count = _PLURAL_NPLURALS_RE.search(header)
    rule = _PLURAL_RULE_RE.search(header)
    expression = str(rule.group(1)).strip() if rule is not None else ""
    return (
        int(count.group(1)) if count is not None else None,
        expression,
    )


def prompt_for_plural(
    language: str,
    source: PluralSource,
    context: str = "",
) -> str:
    """Build a provider-neutral prompt for a plural form set."""
    suffix = f"\nContext: {context}" if context else ""
    rule = (
        f"\nPlural rule: {source.plural_expression}" if source.plural_expression else ""
    )
    return (
        f"Translate the following UI string into {language}. "
        f"It has {source.nplurals} plural forms. Return exactly "
        f"{source.nplurals} lines, each prefixed with its form index, "
        "for example `0: ...`. Preserve every placeholder, mnemonic and "
        "line break in every form."
        f"{rule}"
        f"\nSource (singular): {source.msgid}"
        f"\nSource (plural): {source.msgid_plural}{suffix}"
    )


def parse_plural_response(text: str, nplurals: int) -> dict[int, str] | None:
    """Parse indexed plural forms, or return None for an unusable answer."""
    if nplurals <= 0:
        return None
    forms: dict[int, str] = {}
    current: int | None = None
    for line in text.splitlines():
        match = _PLURAL_FORM_LINE_RE.match(line)
        if match is not None:
            index = int(match.group(1))
            if index in forms:
                return None
            forms[index] = match.group(2)
            current = index
        elif current is not None:
            forms[current] = f"{forms[current]}\n{line}"
        elif line.strip():
            return None
    if set(forms) != set(range(nplurals)):
        return None
    if any(not value.strip() for value in forms.values()):
        return None
    return forms


def _plural_listing(forms: Mapping[int, str]) -> str:
    """Render one ordered form set for a prompt or judge listing."""
    return "\n".join(f"{index}: {forms[index]}" for index in sorted(forms))


def _normalise(text: str) -> str:
    """Normalise a translation for exact-match comparison."""
    return " ".join(text.replace("_", "").casefold().split())


def _format_fields(text: str) -> list[str] | None:
    """Return the str.format field names, or None for unbalanced braces."""
    if text.count("{") != text.count("}"):
        return None
    return cast("list[str]", re.findall(r"(?<!\{)\{([^{}]*)\}(?!\})", text))


def _edge_newlines(text: str) -> tuple[int, int]:
    """Return the number of leading and trailing newlines."""
    return len(text) - len(text.lstrip("\n")), len(text) - len(text.rstrip("\n"))


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
    source_leading, source_trailing = _edge_newlines(source)
    translation_leading, translation_trailing = _edge_newlines(translation)
    if source_leading != translation_leading:
        defects.append("leading newline changed")
    if source_trailing != translation_trailing:
        defects.append("trailing newline changed")
    if not translation.strip():
        defects.append("empty translation")
    return defects


def deterministic_plural_checks(
    source: PluralSource,
    forms: Mapping[int, str] | None,
) -> list[str]:
    """Return every deterministic defect in a plural form set."""
    if forms is None:
        return ["wrong number of forms or unparseable response"]
    if set(forms) != set(range(source.nplurals)):
        return ["wrong number of forms"]
    defects: list[str] = []
    for index, source_text in enumerate(source.source_forms()):
        defects.extend(
            f"form {index}: {defect}"
            for defect in deterministic_checks(source_text, forms[index])
        )
    return defects


def _classify_role(prompt: str) -> str:
    """Return the gate role a prompt belongs to."""
    if "back into English" in prompt:
        return "backtranslation"
    if prompt.startswith("Choose the best"):
        return "judge"
    return "proposer"


def _concurrent_map(
    worker: Callable[[Deployment], Completion],
    items: Sequence[Deployment],
    *,
    max_workers: int,
) -> list[Completion]:
    """Run ``worker`` over ``items`` concurrently, preserving input order.

    A single item runs inline so a one-deployment configuration never pays
    for a pool; a pool is only built when there is real parallelism to win.
    Raising workers propagate the first exception, matching serial semantics,
    and the pool waits for every started worker on exit.
    """
    if len(items) <= 1:
        return [worker(item) for item in items]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(worker, items))


class ObservedClient:
    """Wrap a model client, reporting each call in flight to a reporter."""

    def __init__(
        self,
        client: ModelClient,
        reporter: ProgressReporter,
        *,
        judge_timeout: float | None = None,
    ) -> None:
        """Keep the wrapped client, the reporter and the judge deadline."""
        self._client = client
        self._reporter = reporter
        self._judge_timeout = judge_timeout

    def complete(
        self,
        deployment: Deployment,
        prompt: str,
        *,
        timeout: float | None = None,
    ) -> Completion:
        """Run one completion, reporting the call around it.

        A judge prompt is sent with the configured judge deadline when one is
        set (a ``judge_timeout`` of ``0`` leaves the transport default); every
        other role keeps the given ``timeout`` or its transport default.
        """
        role = _classify_role(prompt)
        self._reporter.begin_call(role, deployment.id)
        try:
            deadline: float | None = timeout
            if role == "judge" and self._judge_timeout not in (None, 0):
                deadline = self._judge_timeout
            return self._client.complete(deployment, prompt, timeout=deadline)
        finally:
            self._reporter.end_call()


def propose(
    source: str,
    language: str,
    config: GateConfig,
    client: ModelClient,
    *,
    context: str = "",
) -> list[Proposal]:
    """Return one proposal from every proposer deployment."""
    completions = _concurrent_map(
        lambda deployment: client.complete(
            deployment, prompt_for("translate", language, source, context)
        ),
        config.proposers,
        max_workers=len(config.proposers),
    )
    return [
        Proposal(
            deployment=deployment.id,
            release=deployment.release,
            family=config.release_for(deployment).family,
            text=completion.text,
            completion=completion,
        )
        for deployment, completion in zip(config.proposers, completions, strict=True)
    ]


def propose_plural(
    source: PluralSource,
    language: str,
    config: GateConfig,
    client: ModelClient,
    *,
    context: str = "",
) -> list[Proposal]:
    """Return one complete plural proposal from every proposer deployment."""
    completions = _concurrent_map(
        lambda deployment: client.complete(
            deployment, prompt_for_plural(language, source, context)
        ),
        config.proposers,
        max_workers=len(config.proposers),
    )
    return [
        Proposal(
            deployment=deployment.id,
            release=deployment.release,
            family=config.release_for(deployment).family,
            text=completion.text,
            completion=completion,
            forms=parse_plural_response(completion.text, source.nplurals),
        )
        for deployment, completion in zip(config.proposers, completions, strict=True)
    ]


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
    try:
        completion = client.complete(judge, prompt)
    except ModelError:
        return None, "TIMEOUT", None
    answer = completion.text.strip().upper()
    if answer.startswith("ABSTAIN"):
        return None, answer, completion
    for index, label in enumerate(labels):
        if answer.startswith(label):
            return index, answer, completion
    return None, answer, completion


def blind_judge_plural(
    source: PluralSource,
    language: str,
    proposals: Sequence[Proposal],
    config: GateConfig,
    client: ModelClient,
) -> tuple[int | None, str, Completion | None]:
    """Ask a third family to choose one complete plural form set."""
    if not proposals:
        return None, "no proposals", None
    labels = [chr(ord("A") + index) for index in range(len(proposals))]
    listing = "\n".join(
        f"{label}:\n{_plural_listing(cast('dict[int, str]', proposal.forms))}"
        for label, proposal in zip(labels, proposals, strict=True)
    )
    prompt = (
        f"Choose the best {language} plural translation of this source string. "
        f"Each proposal gives all {source.nplurals} forms. "
        "Answer with the letter only, or ABSTAIN.\n"
        f"Source (singular): {source.msgid}\n"
        f"Source (plural): {source.msgid_plural}\n{listing}"
    )
    judge = config.judges[0]
    try:
        completion = client.complete(judge, prompt)
    except ModelError:
        return None, "TIMEOUT", None
    answer = completion.text.strip().upper()
    if answer.startswith("ABSTAIN"):
        return None, answer, completion
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
    proposals = propose(
        source,
        language,
        config,
        client,
        context=options.context,
    )
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

    texts = {proposal.text.strip() for proposal in passing}
    families = {proposal.family for proposal in passing}
    if len(texts) == 1 and len(families) >= MIN_PROPOSER_FAMILIES:
        preferred = passing[0]
        judge_evidence: dict[str, object] = {
            "tie": True,
            "verdict": "identical",
            "families": sorted(families),
        }
    else:
        index, verdict, judge_completion = blind_judge(
            source,
            language,
            passing,
            config,
            client,
        )
        if judge_completion is not None:
            calls.append({**judge_completion.as_dict(), "role": "judge"})
        if index is None:
            return GateDecision(
                approved=False,
                reason=(
                    "judge timed out"
                    if verdict == "TIMEOUT"
                    else "judge abstained or returned no usable choice"
                ),
                evidence={
                    "proposals": proposal_records,
                    "checks": checks,
                    "verdict": verdict,
                    "calls": calls,
                },
            )
        preferred = passing[index]
        judge_evidence = {
            "deployment": config.judges[0].id,
            "verdict": verdict,
        }
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
                    "judge": judge_evidence,
                    "backtranslation": False,
                    "calls": calls,
                },
            )

    high_impact = is_high_impact(source, options.occurrences)
    evidence: dict[str, object] = {
        "proposals": proposal_records,
        "checks": checks,
        "judge": judge_evidence,
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
    evidence_summary = evidence
    evidence_sha256: str | None = None
    if options.evidence_path is not None:
        evidence_sha256 = write_evidence(
            evidence,
            options.evidence_path,
            kind="approval",
            language=language,
        )
        evidence_summary = compact_evidence(evidence)
    record = make_record(
        language,
        _entry_for(source, preferred_text),
        provenance_class,
        context=ApprovalContext(
            approval_date=_today(),
            evidence=evidence_summary,
            evidence_sha256=evidence_sha256,
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


def run_plural_gate(
    source: PluralSource,
    language: str,
    config: GateConfig,
    client: ModelClient,
    *,
    options: GateOptions | None = None,
) -> GateDecision:
    """Run proposal, checks, blind judging and back-translation for a form set."""
    options = options or GateOptions()
    proposals = propose_plural(
        source,
        language,
        config,
        client,
        context=options.context,
    )
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
        proposal.deployment: deterministic_plural_checks(source, proposal.forms)
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

    form_sets = {
        tuple(
            cast("dict[int, str]", proposal.forms)[index]
            for index in range(source.nplurals)
        )
        for proposal in passing
    }
    families = {proposal.family for proposal in passing}
    if len(form_sets) == 1 and len(families) >= MIN_PROPOSER_FAMILIES:
        preferred = passing[0]
        judge_evidence: dict[str, object] = {
            "tie": True,
            "verdict": "identical",
            "families": sorted(families),
        }
    else:
        index, verdict, judge_completion = blind_judge_plural(
            source,
            language,
            passing,
            config,
            client,
        )
        if judge_completion is not None:
            calls.append({**judge_completion.as_dict(), "role": "judge"})
        if index is None:
            return GateDecision(
                approved=False,
                reason=(
                    "judge timed out"
                    if verdict == "TIMEOUT"
                    else "judge abstained or returned no usable choice"
                ),
                evidence={
                    "proposals": proposal_records,
                    "checks": checks,
                    "verdict": verdict,
                    "calls": calls,
                },
            )
        preferred = passing[index]
        judge_evidence = {
            "deployment": config.judges[0].id,
            "verdict": verdict,
        }
    forms = cast("dict[int, str]", preferred.forms)

    backtranslation: dict[str, bool] = {}
    for form_index, source_text in enumerate(source.source_forms()):
        if len(source_text) < _SENTENCE_CHARS or " " not in source_text:
            continue
        preserved, back_completion = back_translation_preserves(
            source_text,
            forms[form_index],
            language,
            config,
            client,
        )
        calls.append({**back_completion.as_dict(), "role": "backtranslation"})
        backtranslation[str(form_index)] = preserved
        if not preserved:
            return GateDecision(
                approved=False,
                reason="back-translation changed the meaning",
                evidence={
                    "proposals": proposal_records,
                    "checks": checks,
                    "judge": judge_evidence,
                    "backtranslation": backtranslation,
                    "calls": calls,
                },
            )

    high_impact = any(
        is_high_impact(text, options.occurrences) for text in source.source_forms()
    )
    evidence: dict[str, object] = {
        "proposals": proposal_records,
        "checks": checks,
        "judge": judge_evidence,
        "backtranslation": backtranslation,
        "high_impact": high_impact,
        "plural": True,
        "plural_prompt_version": PLURAL_PROMPT_VERSION,
        "prompt_hash": PLURAL_PROMPT_HASH,
        "calls": calls,
    }
    evidence_summary = evidence
    evidence_sha256: str | None = None
    if options.evidence_path is not None:
        evidence_sha256 = write_evidence(
            evidence,
            options.evidence_path,
            kind="approval",
            language=language,
        )
        evidence_summary = compact_evidence(evidence)
    record = make_record(
        language,
        _entry_for_plural(source, forms),
        "machine-strong",
        context=ApprovalContext(
            approval_date=_today(),
            evidence=evidence_summary,
            evidence_sha256=evidence_sha256,
            model_release=preferred.release,
            deployment=preferred.deployment,
        ),
    )
    return GateDecision(
        approved=True,
        reason="every check and the judge agree",
        forms={index: forms[index] for index in sorted(forms)},
        record=record,
        evidence=evidence,
    )


def record_gate_run(
    ledger: dict[str, object],
    decision: GateDecision,
    language: str,
    *,
    options: GateRunOptions | None = None,
) -> dict[str, object]:
    """Append one gate outcome, including abstentions, to the ledger."""
    options = options or GateRunOptions()
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
        "action": options.action,
        "language": language,
        "outcome": "approved" if decision.approved else "abstained",
        "reason": decision.reason,
        "timestamp": options.timestamp
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
    if options.evidence_path is not None:
        compact_operational_record(record, options.evidence_path, kind="gate_run")
    add_section_record(ledger, "gate_runs", record)
    return record


def _entry_for(
    source: str,
    translation: str,
    *,
    msgid_plural: str | None = None,
    forms: Mapping[int, str] | None = None,
) -> polib.POEntry:
    """Build a throwaway catalog entry for record hashing."""
    if msgid_plural is not None:
        plural_forms = forms or {}
        return polib.POEntry(
            msgid=source,
            msgid_plural=msgid_plural,
            msgstr_plural={
                index: plural_forms[index] for index in sorted(plural_forms)
            },
        )
    return polib.POEntry(msgid=source, msgstr=translation)


def _entry_for_plural(
    source: PluralSource,
    forms: Mapping[int, str],
) -> polib.POEntry:
    """Build a throwaway plural catalog entry for record hashing."""
    return _entry_for(
        source.msgid,
        "",
        msgid_plural=source.msgid_plural,
        forms=forms,
    )


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
    tolerance = config.threshold(
        "qualification", language=request.language, default=0.8
    )
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
    if request.evidence_path is not None:
        compact_operational_record(record, request.evidence_path, kind="qualification")
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
    threshold = config.threshold("drift", language=request.language, default=0.75)
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
    record: dict[str, object] = {
        "release": result["release"],
        "deployment": result["deployment"],
        "language": result["language"],
        "score": result["score"],
        "threshold": result["threshold"],
        "since": since,
        "status": "paused",
        "queued_for_audit": True,
        "total_cost_usd": result.get("total_cost_usd"),
        "latency_ms": result.get("latency_ms"),
    }
    if "calls" in result:
        record["calls"] = result["calls"]
    if "evidence_sha256" in result:
        record["evidence_sha256"] = result["evidence_sha256"]
    add_section_record(ledger, "drift_excursions", record)


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
    sources: Sequence[str | PluralSource],
    *,
    context: str = "",
    chars_per_token: float | None = None,
) -> ActionEstimate:
    """Estimate the cost of gating a set of strings or plural form sets."""
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
        if isinstance(source, PluralSource):
            source_tokens = max(
                1,
                sum(estimate_tokens(text, chars) for text in source.source_forms()),
            )
            for deployment in config.proposers:
                prompt = prompt_for_plural(language, source, context)
                low, high = _output_range(source_tokens, deployment)
                accumulator(deployment).add(
                    deployment, estimate_tokens(prompt, chars), low, high
                )
            judge = config.judges[0]
            placeholder = dict.fromkeys(range(source.nplurals), "proposal")
            judge_prompt = (
                f"Choose the best {language} plural translation of this "
                f"source string.\nSource (singular): {source.msgid}\n"
                f"Source (plural): {source.msgid_plural}\n"
                f"A:\n{_plural_listing(placeholder)}\n"
                f"B:\n{_plural_listing(placeholder)}"
            )
            high_output = _output_range(source_tokens, config.proposers[0])[1]
            accumulator(judge).add(
                judge,
                estimate_tokens(judge_prompt, chars) + 2 * high_output,
                1,
                1,
            )
            for text in source.source_forms():
                if len(text) >= _SENTENCE_CHARS and " " in text:
                    back_prompt = prompt_for("backtranslate", language, text)
                    low, high = _output_range(estimate_tokens(text, chars), judge)
                    accumulator(judge).add(
                        judge,
                        estimate_tokens(back_prompt, chars) + high,
                        low,
                        high,
                    )
            continue
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


def _print_drift(result: Mapping[str, object]) -> None:
    """Print a compact drift-probe result."""
    outcome = "paused" if result.get("paused") is True else "ok"
    print(
        f"drift {result.get('language')} {result.get('deployment')} "
        f"({result.get('release')}): {outcome} "
        f"(score {result.get('score')}, threshold {result.get('threshold')}, "
        f"calls {result.get('call_count')}, cost {result.get('total_cost_usd')})"
    )


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
    *,
    evidence_path: Path | None = None,
) -> None:
    """Accumulate one gate run and its outcome."""
    language = str(run.get("language", ""))
    calls = (
        load_gate_run_calls(run, evidence_path)
        if evidence_path is not None
        else run.get("calls")
    )
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
    evidence_path: Path | None = None,
) -> dict[str, object]:
    """Aggregate spend and quality by language and deployment."""
    result: dict[str, dict[str, CostBucket]] = {language: {} for language in languages}
    indexes = RunIndexes()

    for run_index, run in enumerate(section(ledger, "gate_runs")):
        _process_gate_run(
            run_index,
            run,
            result,
            indexes,
            evidence_path=evidence_path,
        )
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
    if _ledger_is_dir(ledger_path):
        write_global_ledger(ledger, ledger_path)
    else:
        write_ledger(ledger, ledger_path)


def _apply_decision(
    ledger: dict[str, object],
    entry: polib.POEntry,
    decision: GateDecision,
) -> None:
    """Write an approved translation into a catalog entry and the ledger."""
    if not decision.approved or decision.record is None:
        msg = "cannot approve an abstained decision"
        raise GateError(msg)
    if entry.msgid_plural:
        forms = decision.forms
        if forms is None or not forms:
            msg = "approved decision has no plural forms"
            raise GateError(msg)
        expected = {int(key) for key in (entry.msgstr_plural or {})}
        if expected and set(forms) != expected:
            msg = "approved plural forms do not match the entry"
            raise GateError(msg)
        entry.msgstr = ""
        entry.msgstr_plural = {index: forms[index] for index in sorted(forms)}
    else:
        translation = decision.translation
        if translation is None or not translation.strip():
            msg = "approved decision has no translation"
            raise GateError(msg)
        entry.msgstr = translation
    entry.flags = [flag for flag in entry.flags if flag != "fuzzy"]
    _replace_section(
        ledger,
        "approvals",
        decision.record,
        key_fields=("language", "msgctxt", "msgid", "msgid_plural"),
    )


def approve_decision(
    catalog_path: Path,
    ledger_path: Path,
    msgid: str,
    decision: GateDecision,
) -> None:
    """Write an approved translation and record the approval."""
    if not decision.approved or decision.record is None:
        msg = "cannot approve an abstained decision"
        raise GateError(msg)
    if decision.forms is None and (
        decision.translation is None or not decision.translation.strip()
    ):
        msg = "approved decision has no translation"
        raise GateError(msg)
    if decision.forms is not None and not decision.forms:
        msg = "approved decision has no plural forms"
        raise GateError(msg)
    catalog = polib.pofile(str(catalog_path))
    entry = catalog.find(msgid)
    if entry is None:
        msg = f"{msgid!r} is not in {catalog_path}"
        raise GateError(msg)
    language = decision.record.get("language")
    if _ledger_is_dir(ledger_path):
        if not isinstance(language, str) or not language:
            msg = "the decision has no language for the split ledger"
            raise GateError(msg)
        ledger = load_language_ledger(ledger_path, language)
        _apply_decision(ledger, entry, decision)
        write_language_ledger(ledger, ledger_path, language)
    else:
        ledger = load_ledger(ledger_path)
        _apply_decision(ledger, entry, decision)
        write_ledger(ledger, ledger_path)
    catalog.save(str(catalog_path))


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
    payload = costs_report(
        ledger,
        languages=languages,
        evidence_path=args.evidence,
    )
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
    ledger = _load_ledger_for(args.ledger, args.language)
    entries = _held_out(ledger, catalog, args.language, args.count)
    request = QualificationRequest(
        args.release,
        args.language,
        entries,
        budget_usd=args.max_cost,
        evidence_path=args.evidence,
    )
    try:
        record = qualify_release(
            ledger,
            config,
            request,
            OpenAICompatibleClient(timeout=args.timeout),
        )
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        _write_ledger_for(ledger, args.ledger, args.language)
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


def _command_drift(args: argparse.Namespace, config: GateConfig) -> int:
    """Run one fixed drift probe and record a pause when it drops."""
    deployment = config.deployments.get(args.deployment)
    if deployment is None:
        print(
            f"error: deployment {args.deployment!r} is not configured",
            file=sys.stderr,
        )
        return 1
    probe_path = args.probe or (DEFAULT_PROBE_DIR / f"{args.language}.json")
    try:
        probe = load_probe(probe_path)
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if not probe:
        print(f"error: probe {probe_path} has no items", file=sys.stderr)
        return 1
    ledger = _load_ledger_for(args.ledger, args.language)
    request = DriftRequest(
        deployment.release,
        args.deployment,
        args.language,
        probe,
        budget_usd=args.max_cost,
    )
    try:
        result = drift_probe(
            config, request, OpenAICompatibleClient(timeout=args.timeout)
        )
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if result.get("paused") is True and not args.dry_run:
        if args.evidence is not None:
            compact_operational_record(result, args.evidence, kind="drift")
        record_drift_excursion(ledger, result, since=args.since or _today())
        try:
            _write_ledger_for(ledger, args.ledger, args.language)
        except (LedgerError, OSError) as error:
            print(
                f"error: cannot write ledger {args.ledger}: {error}",
                file=sys.stderr,
            )
            return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_drift(result)
    return 0


@dataclass(frozen=True)
class BatchSelection:
    """Entries selected for one catalog batch."""

    selected: tuple[polib.POEntry, ...]
    unsupported: tuple[tuple[polib.POEntry, str], ...]
    skipped: int


@dataclass(frozen=True)
class BatchRun:
    """Inputs for one catalog batch."""

    config: GateConfig
    catalog: polib.POFile
    ledger: dict[str, object]
    catalog_path: Path
    ledger_path: Path
    language: str
    entries: tuple[polib.POEntry, ...]
    client: ModelClient
    max_cost: float | None
    tm_db: Path | None
    evidence_path: Path | None = None
    max_time: float | None = None
    weights: tuple[float, ...] = ()
    reporter: ProgressReporter | None = None
    judge_timeout: float | None = None


@dataclass(frozen=True)
class BatchReport:
    """One completed catalog batch."""

    language: str
    catalog: str
    dry_run: bool
    selected: int
    approved: tuple[dict[str, object], ...]
    abstained: tuple[dict[str, object], ...]
    skipped: int
    unsupported: tuple[dict[str, str], ...]
    spent_usd: float
    remaining: int
    stopped: str | None
    blockers: tuple[str, ...]
    estimate: ActionEstimate
    over_budget: bool
    elapsed_seconds: float = 0.0
    entries_per_hour: float | None = None
    judge_abstained: int = 0

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready report."""
        return {
            "language": self.language,
            "catalog": self.catalog,
            "dry_run": self.dry_run,
            "selected": self.selected,
            "approved": list(self.approved),
            "abstained": list(self.abstained),
            "skipped": self.skipped,
            "unsupported": list(self.unsupported),
            "spent_usd": round(self.spent_usd, 6),
            "remaining": self.remaining,
            "stopped": self.stopped,
            "blockers": list(self.blockers),
            "estimate": self.estimate.as_dict(),
            "over_budget": self.over_budget,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "entries_per_hour": self.entries_per_hour,
            "judge_abstained": self.judge_abstained,
            "ready": not self.blockers and not self.over_budget,
        }


def _percentile(values: Sequence[float], fraction: float) -> float:
    """Return the interpolated percentile of a sequence, for fraction in [0,1]."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _format_duration(seconds: float) -> str:
    """Format a duration compactly as hours and minutes."""
    total = max(0, round(seconds))
    hours, rest = divmod(total, 3600)
    minutes = round(rest / MINUTE_SECONDS)
    if minutes == MINUTE_SECONDS:
        hours += 1
        minutes = 0
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m"
    return "<1m"


def _round_band(seconds: float) -> tuple[float, float]:
    """Round a seconds estimate inwards and outwards to five minutes."""
    low = math.floor(seconds / ETA_ROUND_SECONDS) * ETA_ROUND_SECONDS
    high = math.ceil(seconds / ETA_ROUND_SECONDS) * ETA_ROUND_SECONDS
    return max(0, low), max(low, high)


def _money(value: float | None) -> str:
    """Format a dollar value, or a dash when it is unknown."""
    if value is None:
        return "-"
    return f"${value:.4f}"


def _money_range(low: float | None, high: float | None) -> str:
    """Format a dollar range, or a dash when both bounds are unknown."""
    if low is None and high is None:
        return "-"
    return f"{_money(low)}-{_money(high)}"


def _eta_display(
    low: float,
    high: float,
    now: datetime,
    local_tz: tzinfo,
) -> str:
    """Describe a completion estimate as a rounded band in local time."""
    low_rounded, _ = _round_band(low)
    _, high_rounded = _round_band(high)
    high_rounded = max(high_rounded, low_rounded)
    low_time = (now + timedelta(seconds=low_rounded)).astimezone(local_tz)
    high_time = (now + timedelta(seconds=high_rounded)).astimezone(local_tz)
    return (
        f"{_format_duration(low_rounded)}-{_format_duration(high_rounded)} "
        f"({low_time:%H:%M}-{high_time:%H:%M})"
    )


def _entry_weight(high_cost_usd: float | None) -> float:
    """Return a per-entry progress weight, falling back to one per entry."""
    if high_cost_usd is None or high_cost_usd <= 0:
        return 1.0
    return high_cost_usd


def _selection_weights(
    config: GateConfig,
    entries: Sequence[polib.POEntry],
    language: str,
    nplurals: int | None,
    plural_expression: str,
) -> list[float]:
    """Return one progress weight per entry, zero for unusable sources."""
    weights: list[float] = []
    for entry in entries:
        source = _batch_source(entry, nplurals, plural_expression)
        if source is None:
            weights.append(0.0)
        else:
            weights.append(
                _entry_weight(estimate_gate(config, language, [source]).high_cost_usd)
            )
    return weights


def _entry_durations(
    ledger: Mapping[str, object],
    language: str | None,
    limit: int = 200,
) -> list[float]:
    """Return recent per-entry wall durations from the ledger, in seconds."""
    runs = [
        run
        for run in section(ledger, "gate_runs")
        if language is None or run.get("language") == language
    ]
    durations: list[float] = []
    for run in runs[-limit:]:
        latency = run.get("latency_ms")
        if isinstance(latency, int | float) and not isinstance(latency, bool):
            durations.append(float(latency) / 1000.0)
    return durations


def _duration_prior(
    ledger: Mapping[str, object],
    language: str,
) -> tuple[float, str]:
    """Return seconds-per-entry for a batch and the prior's basis name."""
    own = _entry_durations(ledger, language)
    if len(own) >= PRIOR_MIN_SAMPLES:
        return statistics.median(own) + LOCAL_OVERHEAD_SECONDS, "language history"
    cross = _entry_durations(ledger, None)
    if len(cross) >= PRIOR_MIN_SAMPLES:
        return statistics.median(
            cross
        ) + LOCAL_OVERHEAD_SECONDS, "cross-language history"
    return DEFAULT_SECONDS_PER_ENTRY, "default"


@dataclass(frozen=True)
class ProgressInfo:
    """The static facts of one batch, fixed before its first call."""

    language: str = ""
    catalog_path: Path | None = None
    state_path: Path | None = None
    selection: int = 0
    skipped: int = 0
    unsupported: int = 0
    weights: tuple[float, ...] = ()
    estimate: ActionEstimate | None = None
    prior: tuple[float, str] = (DEFAULT_SECONDS_PER_ENTRY, "default")
    max_cost: float | None = None
    pid: int | None = None
    host: str | None = None


class ProgressReporter:
    """Report a batch run to stderr lines and a per-language state file.

    The report is purely visual; missing or unwritable state never changes a
    batch's outcome (see the design's ``advisory`` property). The clock is
    injected so tests assert exact strings without sleeping.
    """

    def __init__(
        self,
        *,
        info: ProgressInfo,
        mode: str = "none",
        stream: TextIO | None = None,
        clock: Clock | None = None,
        started_at: datetime | None = None,
    ) -> None:
        """Record the batch facts and the optional runtime seams."""
        self._info = info
        self._weights = list(info.weights)
        self._weight_total = float(sum(info.weights))
        self._mode = mode
        self._stream = stream if stream is not None else sys.stderr
        self._clock = clock if clock is not None else SystemClock()
        self._pid = info.pid if info.pid is not None else os.getpid()
        self._host = info.host if info.host is not None else socket.gethostname()
        self._start_wall = started_at if started_at is not None else self._clock.now()
        self._start_mono = self._clock.monotonic()
        self._done = 0
        self._approved = 0
        self._abstained = 0
        self._spent = 0.0
        self._weight_done = 0.0
        self._samples: list[tuple[float, float]] = []
        self._waiting: dict[str, object] | None = None
        self._waiting_lock = threading.Lock()
        self._stopped: str | None = None

    @property
    def done(self) -> int:
        """Return the number of entries completed so far."""
        return self._done

    @property
    def spent(self) -> float:
        """Return the spend recorded so far."""
        return self._spent

    @property
    def started(self) -> datetime:
        """Return the UTC wall time the batch started."""
        return self._start_wall

    @property
    def stopped(self) -> str | None:
        """Return the recorded stop reason, if any."""
        return self._stopped

    def now(self) -> datetime:
        """Return the current UTC wall time from the injected clock."""
        return self._clock.now()

    def monotonic(self) -> float:
        """Return the current monotonic seconds from the injected clock."""
        return self._clock.monotonic()

    def elapsed(self) -> float:
        """Return the seconds elapsed since the batch started."""
        return self._clock.monotonic() - self._start_mono

    def deadline_reached(self, budget: float) -> bool:
        """Return whether a wall-clock budget has been exhausted."""
        return self._clock.monotonic() - self._start_mono >= budget

    def rate_seconds_per_entry(self) -> float:
        """Return the median observed seconds per completed entry."""
        if not self._samples:
            return 0.0
        return statistics.median(seconds for _, seconds in self._samples)

    def _remaining(self) -> tuple[float, int]:
        """Return remaining weight and remaining entry count."""
        remaining_weight = self._weight_total - self._weight_done
        remaining_count = self._info.selection - self._done
        return remaining_weight, remaining_count

    def _estimate_eta(self) -> tuple[float, float, float]:
        """Return the (point, low, high) completion estimate in seconds."""
        remaining_weight, remaining_count = self._remaining()
        if self._samples:
            ratios = [
                (elapsed / weight) if weight else elapsed
                for weight, elapsed in self._samples
            ]
            point = remaining_weight * statistics.median(ratios)
            low = remaining_weight * _percentile(ratios, 0.1)
            high = remaining_weight * _percentile(ratios, 0.9)
        else:
            point = remaining_count * self._info.prior[0]
            low = point * (1 - ETA_PRIOR_SPREAD)
            high = point * (1 + ETA_PRIOR_SPREAD)
        return point, max(0.0, low), max(0.0, high)

    def banner(self) -> None:
        """Emit the start banner and persist the initial state."""
        self._persist()
        if self._mode != "line":
            return
        _, low, high = self._estimate_eta()
        estimate_text = (
            _money_range(
                self._info.estimate.low_cost_usd,
                self._info.estimate.high_cost_usd,
            )
            if self._info.estimate is not None
            else "-"
        )
        self._write(
            f"start translate {self._info.language}: "
            f"selected {self._info.selection} "
            f"skipped {self._info.skipped} unsupported {self._info.unsupported} "
            f"estimate {estimate_text} "
            f"eta {_eta_display(low, high, self._clock.now(), self._clock.local_tz())} "
            f"prior {self._info.prior[1]}"
        )

    def begin_call(self, role: str, deployment: str) -> None:
        """Record the model call now in flight."""
        with self._waiting_lock:
            self._waiting = {
                "role": role,
                "deployment": deployment,
                "since": self._clock.now().isoformat(timespec="seconds"),
            }
            self._persist()

    def end_call(self) -> None:
        """Clear the in-flight call marker."""
        with self._waiting_lock:
            self._waiting = None
            self._persist()

    def entry_done(
        self,
        *,
        weight: float,
        approved: bool,
        cost: float,
        elapsed: float,
    ) -> None:
        """Record one completed entry, persist and report the line."""
        self._done += 1
        self._weight_done += weight
        if approved:
            self._approved += 1
        else:
            self._abstained += 1
        self._spent += cost
        self._samples.append((weight, elapsed))
        if len(self._samples) > ETA_WINDOW:
            del self._samples[0]
        self._persist()
        if self._mode != "line":
            return
        _, low, high = self._estimate_eta()
        self._write(
            f"entry {self._done}/{self._info.selection} approved {self._approved} "
            f"abstained {self._abstained} spent {_money(self._spent)} "
            f"rate {self.rate_seconds_per_entry():.1f}s/entry "
            f"eta {_eta_display(low, high, self._clock.now(), self._clock.local_tz())}"
        )

    def stop(self, reason: str) -> None:
        """Record the batch's stop reason once."""
        if self._stopped is None:
            self._stopped = reason
            self._persist()

    def as_dict(self) -> dict[str, object]:
        """Return the JSON-ready batch state."""
        point, low, high = self._estimate_eta()
        _, remaining_count = self._remaining()
        if remaining_count <= 0:
            point = low = high = 0.0
        eta = round(point, 1) if remaining_count else None
        eta_low = round(low, 1) if remaining_count else None
        eta_high = round(high, 1) if remaining_count else None
        return {
            "pid": self._pid,
            "host": self._host,
            "started_at": self._start_wall.isoformat(timespec="seconds"),
            "updated_at": self._clock.now().isoformat(timespec="seconds"),
            "language": self._info.language,
            "catalog": (
                str(self._info.catalog_path)
                if self._info.catalog_path is not None
                else None
            ),
            "selection": self._info.selection,
            "done": self._done,
            "approved": self._approved,
            "abstained": self._abstained,
            "spent_usd": round(self._spent, 6),
            "rate_seconds_per_entry": (
                round(self.rate_seconds_per_entry(), 3) if self._samples else None
            ),
            "weight_total": round(self._weight_total, 6),
            "weight_done": round(self._weight_done, 6),
            "eta_seconds": eta,
            "eta_low_seconds": eta_low,
            "eta_high_seconds": eta_high,
            "waiting": self._waiting,
            "stopped": self._stopped,
        }

    def _persist(self) -> None:
        """Write the state file, ignoring an unwritable cache."""
        if self._info.state_path is None:
            return
        with contextlib.suppress(OSError):
            _write_state(self._info.state_path, self.as_dict())

    def _write(self, line: str) -> None:
        """Write one progress line to the report stream."""
        print(line, file=self._stream)


def _write_state(path: Path, data: Mapping[str, object]) -> None:
    """Atomically replace a JSON state file at path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _plural_disposition(
    entry: polib.POEntry,
    nplurals: int | None,
    *,
    include_fuzzy: bool,
) -> tuple[str, str]:
    """Return one plural entry's disposition and unsupported reason."""
    if nplurals is None:
        return "unsupported", "catalog does not declare nplurals"
    forms = {
        int(key): (value or "") for key, value in (entry.msgstr_plural or {}).items()
    }
    if set(forms) != set(range(nplurals)):
        return "unsupported", f"plural forms do not match nplurals={nplurals}"
    translated = all(forms[index].strip() for index in range(nplurals))
    if "fuzzy" in entry.flags:
        if translated and not include_fuzzy:
            return "skipped", ""
        return "selected", ""
    if not translated:
        return "selected", ""
    return "skipped", ""


def _select_batch_entries(
    catalog: polib.POFile,
    *,
    include_fuzzy: bool,
    limit: int | None,
) -> BatchSelection:
    """Select missing entries and report unsupported and skipped ones."""
    selected: list[polib.POEntry] = []
    unsupported: list[tuple[polib.POEntry, str]] = []
    skipped = 0
    nplurals, _ = catalog_plural_info(catalog)
    ordered = sorted(
        (entry for entry in catalog if not entry.obsolete),
        key=lambda entry: (entry.msgctxt or "", entry.msgid),
    )
    for entry in ordered:
        if bool(entry.msgctxt):
            unsupported.append((entry, "message context is not supported"))
            continue
        if entry.msgid_plural:
            disposition, reason = _plural_disposition(
                entry, nplurals, include_fuzzy=include_fuzzy
            )
            if disposition == "unsupported":
                unsupported.append((entry, reason))
            elif disposition == "selected":
                selected.append(entry)
            else:
                skipped += 1
            continue
        if "fuzzy" in entry.flags:
            if (entry.msgstr or "").strip() and not include_fuzzy:
                skipped += 1
                continue
            selected.append(entry)
            continue
        if not (entry.msgstr or "").strip():
            selected.append(entry)
        else:
            skipped += 1
    if limit is not None:
        selected = selected[:limit]
    return BatchSelection(tuple(selected), tuple(unsupported), skipped)


def _batch_blockers(
    config: GateConfig,
    ledger: Mapping[str, object],
    roles: RolePolicy,
    language: str,
) -> list[str]:
    """Return the qualification and pause blockers for a batch."""
    releases = dict.fromkeys(
        config.deployments[deployment_id].release
        for deployment_id in (*roles.proposers, roles.judge)
    )
    blockers: list[str] = []
    for release in releases:
        if _qualified(ledger, release, language) is None:
            blockers.append(f"{release} is not qualified for {language}; run qualify")
        if is_paused(ledger, release, language):
            blockers.append(f"{release} is paused for {language}; re-qualify and audit")
    return blockers


def _decision_cost(decision: GateDecision) -> float:
    """Return the recorded cost of one gate decision."""
    calls = decision.evidence.get("calls", [])
    if not isinstance(calls, list):
        return 0.0
    summary = summarize_calls(
        [cast("dict[str, object]", call) for call in calls if isinstance(call, dict)]
    )
    cost = summary.get("total_cost_usd")
    if isinstance(cost, int | float) and not isinstance(cost, bool):
        return float(cost)
    return 0.0


def _remaining_missing(catalog: polib.POFile) -> int:
    """Return the number of non-obsolete entries without a translation."""
    missing = 0
    for entry in catalog:
        if entry.obsolete:
            continue
        if entry.msgid_plural:
            forms = entry.msgstr_plural or {}
            if not forms or any(not (value or "").strip() for value in forms.values()):
                missing += 1
            continue
        if not (entry.msgstr or "").strip():
            missing += 1
    return missing


def _batch_source(
    entry: polib.POEntry,
    nplurals: int | None,
    plural_expression: str,
) -> str | PluralSource | None:
    """Return the gate source for one batch entry."""
    if entry.msgid_plural:
        if nplurals is None:
            return None
        return PluralSource(
            entry.msgid,
            entry.msgid_plural,
            nplurals,
            plural_expression,
        )
    return entry.msgid


def _run_batch(
    run: BatchRun,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    str | None,
    float,
    int,
]:
    """Run the gate over one batch and persist each outcome."""
    reporter = run.reporter or ProgressReporter(info=ProgressInfo(), mode="none")
    client = ObservedClient(run.client, reporter, judge_timeout=run.judge_timeout)
    approved: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    spent = 0.0
    stopped: str | None = None
    nplurals, plural_expression = catalog_plural_info(run.catalog)
    for position, entry in enumerate(run.entries, start=1):
        weight = run.weights[position - 1] if position <= len(run.weights) else 1.0
        if run.max_time is not None and reporter.deadline_reached(run.max_time):
            stopped = "time"
            reporter.stop("time")
            break
        source = _batch_source(entry, nplurals, plural_expression)
        if source is None:
            abstained.append(
                {
                    "msgid": entry.msgid,
                    "reason": "plural form count changed during the batch",
                    "cost_usd": 0.0,
                }
            )
            reporter.entry_done(
                weight=weight,
                approved=False,
                cost=0.0,
                elapsed=0.0,
            )
            continue
        if run.max_cost is not None:
            high = estimate_gate(run.config, run.language, [source]).high_cost_usd
            if high is not None and spent + high > run.max_cost:
                stopped = "budget"
                reporter.stop("budget")
                break
        options = GateOptions(
            occurrences=tuple(entry.occurrences),
            tm_db=run.tm_db,
            evidence_path=run.evidence_path,
        )
        entry_started = reporter.monotonic()
        if isinstance(source, PluralSource):
            decision = run_plural_gate(
                source,
                run.language,
                run.config,
                client,
                options=options,
            )
        else:
            decision = run_gate(
                source,
                run.language,
                run.config,
                client,
                options=options,
            )
        entry_seconds = reporter.monotonic() - entry_started
        record_gate_run(
            run.ledger,
            decision,
            run.language,
            options=GateRunOptions(evidence_path=run.evidence_path),
        )
        cost = _decision_cost(decision)
        spent += cost
        if decision.approved:
            _apply_decision(run.ledger, entry, decision)
            if decision.forms is not None:
                approved.append(
                    {
                        "msgid": entry.msgid,
                        "msgid_plural": entry.msgid_plural,
                        "forms": {
                            str(index): decision.forms[index]
                            for index in sorted(decision.forms)
                        },
                        "cost_usd": cost,
                    }
                )
            else:
                approved.append(
                    {
                        "msgid": entry.msgid,
                        "translation": decision.translation,
                        "cost_usd": cost,
                    }
                )
        else:
            abstained.append(
                {
                    "msgid": entry.msgid,
                    "reason": decision.reason,
                    "cost_usd": cost,
                }
            )
        _write_ledger_for(run.ledger, run.ledger_path, run.language)
        if decision.approved:
            run.catalog.save(str(run.catalog_path))
        reporter.entry_done(
            weight=weight,
            approved=decision.approved,
            cost=cost,
            elapsed=entry_seconds,
        )
    reporter.stop("complete")
    judge_abstained = sum(
        1 for record in abstained if record["reason"] == "judge timed out"
    )
    return approved, abstained, stopped, spent, judge_abstained


def _ledger_is_dir(path: Path) -> bool:
    """Return whether a ledger path is the split directory form."""
    return path.is_dir() or path.suffix != ".json"


def _load_ledger_for(
    path: Path,
    language: str | None = None,
) -> dict[str, object]:
    """Load a merged ledger or one language file, depending on the path."""
    if _ledger_is_dir(path) and language is not None:
        return load_language_ledger(path, language)
    return load_ledger(path)


def _write_ledger_for(
    data: Mapping[str, object],
    path: Path,
    language: str | None = None,
) -> None:
    """Write a merged ledger or one language file, depending on the path."""
    if _ledger_is_dir(path) and language is not None:
        write_language_ledger(data, path, language)
    else:
        write_ledger(data, path)


def _print_batch(report: BatchReport) -> None:
    """Print a batch summary."""
    if report.dry_run:
        estimate = report.estimate
        print(
            f"translate {report.language} dry run: "
            f"selected {report.selected} skipped {report.skipped} "
            f"unsupported {len(report.unsupported)} "
            f"estimate {estimate.low_cost_usd}-{estimate.high_cost_usd}"
        )
    else:
        processed = len(report.approved) + len(report.abstained)
        print(
            f"translate {report.language}: approved {len(report.approved)} "
            f"abstained {len(report.abstained)} skipped {report.skipped} "
            f"unsupported {len(report.unsupported)} "
            f"spent {round(report.spent_usd, 6)} "
            f"remaining {report.remaining} "
            f"processed {processed}/{report.selected} "
            f"elapsed {_format_duration(report.elapsed_seconds)}"
        )
        if report.entries_per_hour is not None:
            print(f"  rate {report.entries_per_hour:.1f} entries/hour")
        if report.stopped is not None:
            print(
                f"  stopped: {report.stopped}: completed {processed} of "
                f"{report.selected}"
            )
        if len(report.abstained):
            print("  note: abstained entries are retried by a later batch")
    if report.judge_abstained:
        print(
            f"judge timeout abstained {report.judge_abstained} "
            "(retried by a later batch)"
        )
    for blocker in report.blockers:
        print(f"  blocker: {blocker}")
    if report.over_budget:
        print("  blocker: the estimate exceeds --max-cost")


def _print_batch_json(report: BatchReport, *, as_json: bool) -> None:
    """Print a batch report in the requested form."""
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        _print_batch(report)


def _batch_catalog(path: Path) -> polib.POFile:
    """Load a catalog, reporting an unreadable file as a gate error."""
    try:
        return polib.pofile(str(path))
    except OSError as error:
        msg = f"cannot read catalog {path}: {error}"
        raise GateError(msg) from error


def _require_batch_ready(blockers: Sequence[str]) -> None:
    """Raise the combined precondition blockers for a batch."""
    if blockers:
        msg = "\n".join(blockers)
        raise GateError(msg)


def _parse_iso(value: object) -> datetime | None:
    """Parse an ISO timestamp, treating naive values as UTC."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_state(path: Path) -> dict[str, object] | None:
    """Load a batch state file, tolerating a missing or malformed one."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return cast("dict[str, object]", data)


def _pid_alive(pid: object, host: object) -> bool:
    """Return whether a recorded process is alive on this host."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if isinstance(host, str) and host and host != socket.gethostname():
        return False
    try:
        contents = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    except OSError:
        return False
    fields = contents.split()
    if len(fields) < _PROC_STAT_MIN_FIELDS:
        return False
    return fields[2] not in ("Z", "X")


def _is_recent_run(run: Mapping[str, object], now: datetime) -> bool:
    """Return whether a gate run's timestamp is within the status window."""
    timestamp = _parse_iso(run.get("timestamp"))
    if timestamp is None:
        return False
    return (now - timestamp).total_seconds() <= STATUS_RECENT_SECONDS


def _status_languages(
    ledger: Mapping[str, object],
    now: datetime,
    language: str | None,
) -> list[str]:
    """Return the languages to report, from state files or recent runs."""
    if language is not None:
        return [language]
    found: set[str] = set()
    for path in STATE_DIR.glob("*.json"):
        language = path.stem
        state = _load_state(path)
        if state is not None:
            parsed = state.get("language")
            if isinstance(parsed, str) and parsed:
                language = parsed
        found.add(language)
    for run in section(ledger, "gate_runs"):
        lang = run.get("language")
        if isinstance(lang, str) and lang and _is_recent_run(run, now):
            found.add(lang)
    return sorted(found)


def _waiting_seconds(waiting: Mapping[str, object], now: datetime) -> float:
    """Return how long the recorded in-flight call has waited."""
    since = _parse_iso(waiting.get("since"))
    if since is None:
        return 0.0
    return (now - since).total_seconds()


def _stall_threshold(rate: object) -> float:
    """Return the seconds a waiting call needs to count as a stall."""
    if isinstance(rate, int | float) and not isinstance(rate, bool) and rate > 0:
        return max(STALL_FACTOR * float(rate), STALL_FLOOR_SECONDS)
    return STALL_FLOOR_SECONDS


def _stall_reason(waiting: Mapping[str, object], now: datetime) -> str:
    """Describe a stalled call by its role and wait."""
    seconds = _waiting_seconds(waiting, now)
    role = str(waiting.get("role") or "model")
    return f"waiting {int(seconds)}s on {role}"


def _stalled(waiting: Mapping[str, object], rate: object, now: datetime) -> bool:
    """Return whether a waiting call exceeds the stall threshold."""
    return _waiting_seconds(waiting, now) > _stall_threshold(rate)


def _live_record(
    language: str,
    state: Mapping[str, object],
    now: datetime,
) -> dict[str, object]:
    """Build a status record from a live batch state file."""
    updated = _parse_iso(state.get("updated_at"))
    age = (now - updated).total_seconds() if updated is not None else None
    waiting = state.get("waiting")
    waiting_map = waiting if isinstance(waiting, dict) else None
    live = _pid_alive(state.get("pid"), state.get("host"))
    if not live and age is not None:
        live = age <= STATUS_SESSION_GAP_SECONDS
    rate = state.get("rate_seconds_per_entry")
    stopped_text = state.get("stopped")
    if stopped_text == "complete":
        state_name = "done"
    elif live and waiting_map is not None and _stalled(waiting_map, rate, now):
        state_name = "stalled"
    elif live:
        state_name = "running"
    elif age is not None and age > STATUS_ABANDONED_AFTER_SECONDS:
        state_name = "abandoned"
    else:
        state_name = "idle"
    abandoned = state_name == "abandoned"
    return {
        "language": language,
        "source": "live",
        "state": state_name,
        "catalog": state.get("catalog"),
        "selection": state.get("selection"),
        "done": state.get("done"),
        "approved": state.get("approved"),
        "abstained": state.get("abstained"),
        "spent_usd": state.get("spent_usd"),
        "rate_seconds_per_entry": rate,
        "eta_seconds": None if abandoned else state.get("eta_seconds"),
        "eta_low_seconds": None if abandoned else state.get("eta_low_seconds"),
        "eta_high_seconds": None if abandoned else state.get("eta_high_seconds"),
        "updated_age_seconds": round(age, 1) if age is not None else None,
        "waiting": waiting_map,
        "stall_reason": (
            _stall_reason(waiting_map, now)
            if state_name == "stalled" and waiting_map is not None
            else None
        ),
    }


def _inferred_record(
    language: str,
    ledger: Mapping[str, object],
    now: datetime,
) -> dict[str, object]:
    """Build a status record from recent ledger gate runs."""
    runs = [
        run
        for run in section(ledger, "gate_runs")
        if run.get("language") == language and _is_recent_run(run, now)
    ]
    selection: int | None = None
    catalog_text: str | None = None
    catalog_path = CATALOGS_DIR / f"{language}.po"
    if catalog_path.exists():
        try:
            catalog = polib.pofile(str(catalog_path))
        except OSError:
            catalog = None
        if catalog is not None:
            selection = len(
                _select_batch_entries(catalog, include_fuzzy=False, limit=None).selected
            )
            catalog_text = str(catalog_path)
    if not runs:
        return {
            "language": language,
            "source": "inferred",
            "state": "idle",
            "catalog": catalog_text,
            "selection": selection,
            "done": 0,
            "approved": None,
            "abstained": None,
            "spent_usd": 0.0,
            "rate_seconds_per_entry": None,
            "eta_seconds": None,
            "eta_low_seconds": None,
            "eta_high_seconds": None,
            "updated_age_seconds": None,
            "waiting": None,
            "stall_reason": None,
        }
    durations: list[float] = []
    spent = 0.0
    for run in runs:
        latency = run.get("latency_ms")
        if isinstance(latency, int | float) and not isinstance(latency, bool):
            durations.append(float(latency) / 1000.0)
        cost = run.get("total_cost_usd")
        if isinstance(cost, int | float) and not isinstance(cost, bool):
            spent += float(cost)
    rate = statistics.median(durations) if durations else None
    last_ts = _parse_iso(runs[-1].get("timestamp"))
    return {
        "language": language,
        "source": "inferred",
        "state": "idle",
        "catalog": catalog_text,
        "selection": selection,
        "done": len(runs),
        "approved": None,
        "abstained": None,
        "spent_usd": round(spent, 6),
        "rate_seconds_per_entry": (round(rate, 3) if rate is not None else None),
        "eta_seconds": None,
        "eta_low_seconds": None,
        "eta_high_seconds": None,
        "updated_age_seconds": (
            round((now - last_ts).total_seconds(), 1) if last_ts is not None else None
        ),
        "waiting": None,
        "stall_reason": None,
    }


def _print_status(records: Sequence[Mapping[str, object]]) -> None:
    """Print one compact line per status record."""
    now = _status_clock.now()
    local_tz = _status_clock.local_tz()
    for record in records:
        language = str(record["language"])
        state = str(record["state"])
        source = str(record["source"])
        line = f"{language}: {state} {source}"
        done = record.get("done")
        selection = record.get("selection")
        done_text = (
            f"{done or 0}/{selection}" if selection is not None else f"{done or 0}"
        )
        line += f"  done {done_text}"
        approved = record.get("approved")
        if approved is not None:
            line += f"  approved {approved}  abstained {record.get('abstained')}"
        spent = record.get("spent_usd")
        if isinstance(spent, int | float) and not isinstance(spent, bool):
            line += f"  spent {_money(float(spent))}"
        rate = record.get("rate_seconds_per_entry")
        if isinstance(rate, int | float) and not isinstance(rate, bool):
            line += f"  rate {float(rate):.1f}s/entry"
        low = record.get("eta_low_seconds")
        high = record.get("eta_high_seconds")
        if (
            isinstance(low, int | float)
            and not isinstance(low, bool)
            and isinstance(high, int | float)
            and not isinstance(high, bool)
        ):
            line += f"  eta {_eta_display(float(low), float(high), now, local_tz)}"
        age = record.get("updated_age_seconds")
        if isinstance(age, int | float) and not isinstance(age, bool):
            line += f"  age {int(age)}s"
        reason = record.get("stall_reason")
        if reason:
            line += f"  ({reason})"
        print(line)


def _command_status(args: argparse.Namespace) -> int:
    """Report every language with a live batch or recent gate activity."""
    now = _status_clock.now()
    try:
        ledger = load_ledger(args.ledger)
    except (GateError, LedgerError, OSError):
        ledger = {}
    records: list[dict[str, object]] = []
    for language in _status_languages(ledger, now, getattr(args, "language", None)):
        state = _load_state(STATE_DIR / f"{language}.json")
        if state is not None:
            records.append(_live_record(language, state, now))
        else:
            records.append(_inferred_record(language, ledger, now))
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        _print_status(records)
    return 0


def _entries_per_hour(entries: int, seconds: float) -> float | None:
    """Return processed entries per hour, or None before any elapsed time."""
    if seconds <= 0:
        return None
    return entries * 3600.0 / seconds


def _resolve_progress_mode(mode: str, *, stderr_isatty: bool) -> str:
    """Resolve --progress auto against whether stderr is a terminal."""
    if mode == "auto":
        return "line" if stderr_isatty else "none"
    return mode


def _resume_command(args: argparse.Namespace) -> str:
    """Return the exact command line that resumes the batch."""
    raw = cast("list[str]", getattr(args, "argv", []))
    return " ".join(
        shlex.quote(word) for word in ("python3", "dev/translation_gate.py", *raw)
    )


def _command_translate(args: argparse.Namespace, config: GateConfig) -> int:
    """Translate and apply missing entries in one catalog."""
    if args.limit is not None and args.limit <= 0:
        print("error: --limit must be positive", file=sys.stderr)
        return 1
    if args.tm is not None and not args.tm.exists():
        print(f"error: cannot read TM database {args.tm}", file=sys.stderr)
        return 1
    catalog_path = args.catalog or (
        REPO_ROOT / "po" / "scantpaper" / f"{args.language}.po"
    )
    try:
        catalog = _batch_catalog(catalog_path)
        ledger = _load_ledger_for(args.ledger, args.language)
        selection = _select_batch_entries(
            catalog,
            include_fuzzy=args.include_fuzzy,
            limit=args.limit,
        )
        roles = load_roles(args.roles)
        validate_roles(config, roles)
        nplurals, plural_expression = catalog_plural_info(catalog)
        sources: list[str | PluralSource] = []
        for entry in selection.selected:
            source = _batch_source(entry, nplurals, plural_expression)
            if source is not None:
                sources.append(source)
        estimate = estimate_gate(config, args.language, sources)
        blockers = _batch_blockers(config, ledger, roles, args.language)
        over_budget = (
            args.max_cost is not None
            and estimate.high_cost_usd is not None
            and estimate.high_cost_usd > args.max_cost
        )
        unsupported = tuple(
            {"msgid": entry.msgid, "reason": reason}
            for entry, reason in selection.unsupported
        )
        if args.dry_run:
            report = BatchReport(
                language=args.language,
                catalog=str(catalog_path),
                dry_run=True,
                selected=len(selection.selected),
                approved=(),
                abstained=(),
                skipped=selection.skipped,
                unsupported=unsupported,
                spent_usd=0.0,
                remaining=_remaining_missing(catalog),
                stopped=None,
                blockers=tuple(blockers),
                estimate=estimate,
                over_budget=over_budget,
            )
            _print_batch_json(report, as_json=args.json)
        else:
            _require_batch_ready(blockers)
            ensure_budget(estimate, args.max_cost)
            weights = _selection_weights(
                config,
                selection.selected,
                args.language,
                nplurals,
                plural_expression,
            )
            progress_mode = _resolve_progress_mode(
                args.progress, stderr_isatty=sys.stderr.isatty()
            )
            reporter = ProgressReporter(
                info=ProgressInfo(
                    language=args.language,
                    catalog_path=catalog_path,
                    state_path=STATE_DIR / f"{args.language}.json",
                    selection=len(selection.selected),
                    skipped=selection.skipped,
                    unsupported=len(selection.unsupported),
                    weights=tuple(weights),
                    estimate=estimate,
                    prior=_duration_prior(ledger, args.language),
                    max_cost=args.max_cost,
                ),
                mode=progress_mode,
                clock=_batch_clock,
            )
            reporter.banner()
            try:
                approved, abstained, stopped, spent, judge_abstained = _run_batch(
                    BatchRun(
                        config=config,
                        catalog=catalog,
                        ledger=ledger,
                        catalog_path=catalog_path,
                        ledger_path=args.ledger,
                        language=args.language,
                        entries=selection.selected,
                        client=OpenAICompatibleClient(timeout=args.timeout),
                        max_cost=args.max_cost,
                        max_time=args.max_time,
                        judge_timeout=args.judge_timeout,
                        tm_db=args.tm,
                        evidence_path=args.evidence,
                        weights=tuple(weights),
                        reporter=reporter,
                    )
                )
            except KeyboardInterrupt:
                reporter.stop("interrupt")
                remaining = len(selection.selected) - reporter.done
                print(
                    f"interrupted translate {args.language}: "
                    f"completed {reporter.done} remaining {remaining} "
                    f"spent {round(reporter.spent, 6)}",
                    file=sys.stderr,
                )
                print(f"resume: {_resume_command(args)}", file=sys.stderr)
                return 130
            report = BatchReport(
                language=args.language,
                catalog=str(catalog_path),
                dry_run=False,
                selected=len(selection.selected),
                approved=tuple(approved),
                abstained=tuple(abstained),
                skipped=selection.skipped,
                unsupported=unsupported,
                spent_usd=spent,
                remaining=_remaining_missing(catalog),
                stopped=stopped,
                blockers=(),
                estimate=estimate,
                over_budget=False,
                elapsed_seconds=reporter.elapsed(),
                entries_per_hour=_entries_per_hour(reporter.done, reporter.elapsed()),
                judge_abstained=judge_abstained,
            )
            _print_batch_json(report, as_json=args.json)
    except (GateError, LedgerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
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
        OpenAICompatibleClient(timeout=args.timeout),
        options=GateOptions(
            context=args.context,
            evidence_path=args.evidence,
        ),
    )
    ledger = _load_ledger_for(args.ledger, args.language)
    record_gate_run(
        ledger,
        decision,
        args.language,
        options=GateRunOptions(evidence_path=args.evidence),
    )
    _write_ledger_for(ledger, args.ledger, args.language)
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
        "drift": lambda: _command_drift(args, config),
        "translate": lambda: _command_translate(args, config),
        "status": lambda: _command_status(args),
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


class _SubParser(Protocol):
    """The subparser action used while building the command line."""

    def add_parser(
        self,
        name: str,
        **kwargs: object,
    ) -> argparse.ArgumentParser:
        """Add and return one subcommand parser."""


def _add_qualify_drift_parsers(sub: _SubParser) -> None:
    """Add the qualify and drift subcommands."""
    qualify_parser = sub.add_parser("qualify", help="Qualify a release for a language")
    qualify_parser.add_argument("--release", required=True)
    qualify_parser.add_argument("--language", required=True)
    qualify_parser.add_argument("--catalog", type=Path)
    qualify_parser.add_argument("--count", type=int, default=20)
    qualify_parser.add_argument("--max-cost", type=float)
    qualify_parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request model timeout in seconds (default: 60)",
    )
    qualify_parser.add_argument("--json", action="store_true")
    drift_parser = sub.add_parser("drift", help="Run the fixed drift probe")
    drift_parser.add_argument("--deployment", required=True)
    drift_parser.add_argument("--language", required=True)
    drift_parser.add_argument("--probe", type=Path)
    drift_parser.add_argument("--max-cost", type=float)
    drift_parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request model timeout in seconds (default: 60)",
    )
    drift_parser.add_argument("--since")
    drift_parser.add_argument("--dry-run", action="store_true")
    drift_parser.add_argument("--json", action="store_true")


def _add_translate_parser(sub: _SubParser) -> None:
    """Add the catalog batch translation subcommand."""
    translate_parser = sub.add_parser(
        "translate", help="Translate missing catalog entries"
    )
    translate_parser.add_argument("--language", required=True)
    translate_parser.add_argument("--catalog", type=Path)
    translate_parser.add_argument("--limit", type=int)
    translate_parser.add_argument("--include-fuzzy", action="store_true")
    translate_parser.add_argument("--max-cost", type=float)
    translate_parser.add_argument("--max-time", type=float)
    translate_parser.add_argument(
        "--judge-timeout",
        type=float,
        default=DEFAULT_JUDGE_TIMEOUT_SECONDS,
        help=(
            "Judge call deadline in seconds; 0 disables it "
            f"(default: {DEFAULT_JUDGE_TIMEOUT_SECONDS})"
        ),
    )
    translate_parser.add_argument(
        "--progress",
        choices=PROGRESS_MODES,
        default="auto",
        help="Per-entry lines: auto (tty only), line, or none (default: auto)",
    )
    translate_parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request model timeout in seconds (default: 60)",
    )
    translate_parser.add_argument("--tm", type=Path)
    translate_parser.add_argument("--dry-run", action="store_true")
    translate_parser.add_argument("--json", action="store_true")


def _build_parser() -> argparse.ArgumentParser:
    """Build the gate command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--evidence", type=Path)
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
    _add_qualify_drift_parsers(cast("_SubParser", sub))
    _add_translate_parser(cast("_SubParser", sub))
    sub.add_parser("build-probes", help="Regenerate the drift-probe files")
    status_parser = sub.add_parser(
        "status", help="Report live or recent translation batches"
    )
    status_parser.add_argument("--language")
    status_parser.add_argument("--json", action="store_true")
    gate_parser = sub.add_parser("gate", help="Gate one string")
    gate_parser.add_argument("--language", required=True)
    gate_parser.add_argument("--msgid", required=True)
    gate_parser.add_argument("--context", default="")
    gate_parser.add_argument("--output", type=Path)
    gate_parser.add_argument("--max-cost", type=float)
    gate_parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request model timeout in seconds (default: 60)",
    )
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
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = _build_parser().parse_args(raw)
    args.argv = raw
    if args.evidence is None and _ledger_is_dir(args.ledger):
        args.evidence = EVIDENCE_PATH
    if args.command == "status":
        return _command_status(args)
    try:
        config = load_config(args.config)
        return _dispatch(args, config)
    except (GateError, LedgerError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

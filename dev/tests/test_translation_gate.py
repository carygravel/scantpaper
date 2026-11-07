"""Tests for the machine gate in dev/translation_gate.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import polib
import pytest

if TYPE_CHECKING:
    from types import ModuleType

    from translation_gate import GateConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "dev"
GATE_PATH = DEV_DIR / "translation_gate.py"

sys.path.insert(0, str(DEV_DIR))


def _load_gate() -> ModuleType:
    """Import dev/translation_gate.py with its sibling modules."""
    spec = importlib.util.spec_from_file_location("translation_gate", str(GATE_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["translation_gate"] = module
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()
LEDGER = sys.modules["translation_ledger"]


class FakeClient:
    """A deterministic stand-in for an OpenAI-compatible deployment."""

    def __init__(
        self,
        answers: dict[str, str] | None = None,
        *,
        judge: str = "A",
        backtranslation: str | None = None,
    ) -> None:
        """Store the canned proposal, judge and back-translation answers."""
        self.answers = answers or {}
        self.judge = judge
        self.backtranslation = backtranslation

    def complete(self, deployment: object, prompt: str) -> object:
        """Answer a proposal, judge or back-translation prompt."""
        if prompt.startswith("Choose the best"):
            text = self.judge
        elif "back into English" in prompt:
            text = self.backtranslation or ""
        else:
            deployment_id = str(vars(deployment)["id"])
            text = self.answers.get(str(deployment_id), "translated")
        return GATE.Completion(
            text=text,
            deployment=str(vars(deployment)["id"]),
            release=str(vars(deployment)["release"]),
            model=str(vars(deployment)["model"]),
            usage=GATE.Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cached_tokens=0,
                cache_write_tokens=0,
            ),
            latency_ms=1.0,
        )


def _config_data(
    *,
    proposers: tuple[tuple[str, str], ...] = (("p1", "r1"), ("p2", "r2")),
    judge: tuple[str, str] = ("j", "r3"),
    extra: tuple[tuple[str, str], ...] = (),
    key_env: str = "SCANTPAPER_TEST_KEY",
) -> dict[str, object]:
    """Build a valid three-family configuration."""
    releases = {
        "r1": {"family": "family-a", "model": "a", "revision": "1"},
        "r2": {"family": "family-b", "model": "b", "revision": "1"},
        "r3": {"family": "family-c", "model": "c", "revision": "1"},
    }
    deployments: dict[str, object] = {}
    for deployment_id, release in proposers:
        deployments[deployment_id] = {
            "release": release,
            "provider": deployment_id,
            "endpoint": "https://example.invalid/v1/chat/completions",
            "quantization": "fp16",
            "prompt_hash": "sha256:test",
            "decoding": {"temperature": 0.0},
            "key_env": key_env,
            "proposer": True,
            "judge": False,
        }
    judge_id, judge_release = judge
    deployments[judge_id] = {
        "release": judge_release,
        "provider": judge_id,
        "endpoint": "https://example.invalid/v1/chat/completions",
        "quantization": "fp16",
        "prompt_hash": "sha256:test",
        "decoding": {"temperature": 0.0},
        "key_env": key_env,
        "proposer": False,
        "judge": True,
    }
    for deployment_id, release in extra:
        deployments[deployment_id] = {
            "release": release,
            "provider": deployment_id,
            "endpoint": "https://example.invalid/v1/chat/completions",
            "quantization": "fp16",
            "prompt_hash": "sha256:test",
            "decoding": {"temperature": 0.0},
            "key_env": key_env,
            "proposer": False,
            "judge": False,
        }
    return {
        "version": 1,
        "thresholds": {
            "qualification": 0.8,
            "drift": 0.75,
            "defect_rate": 0.05,
            "backtranslation": 0.6,
        },
        "releases": releases,
        "deployments": deployments,
    }


def _write_config(tmp_path: Path, data: dict[str, object]) -> Path:
    """Write a gate configuration."""
    path = tmp_path / "translation-gate.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _ledger(*approvals: dict[str, object]) -> dict[str, object]:
    """Build a valid ledger document."""
    return {"version": 1, "snapshot": "a" * 40, "approvals": list(approvals)}


def _machine_record(
    language: str,
    msgid: str,
    release: str,
    deployment: str,
    msgstr: str = "Löschen",
) -> dict[str, object]:
    """Build one machine approval."""
    entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
    return cast(
        "dict[str, object]",
        LEDGER.make_record(
            language,
            entry,
            "machine-strong",
            context=LEDGER.ApprovalContext(
                approval_date="2026-01-01",
                evidence={},
                model_release=release,
                deployment=deployment,
            ),
        ),
    )


def _write_ledger(path: Path, data: dict[str, object]) -> Path:
    """Write a ledger document."""
    LEDGER.write_ledger(data, path)
    return path


def test_config_accepts_three_independent_families(tmp_path: Path) -> None:
    """Two proposer families and a third judge are valid."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    assert len(config.releases) == 3
    assert len(config.proposers) == 2


def test_optional_cost_and_limits_load(tmp_path: Path) -> None:
    """Cost and limits are optional and validated when present."""
    data = _config_data()
    deployments = cast("dict[str, dict[str, object]]", data["deployments"])
    deployments["p1"]["cost"] = {
        "currency": "USD",
        "unit": "per_million_tokens",
        "input": 0.6,
        "output": 1.8,
        "cache_read": 0.12,
    }
    deployments["p1"]["limits"] = {"context": 256000, "output": 32768}
    config = GATE.load_config(_write_config(tmp_path, data))
    deployment = config.deployments["p1"]
    assert deployment.cost is not None
    assert deployment.cost.input == 0.6
    assert deployment.limits is not None
    assert deployment.limits.output == 32768


def test_optional_headers_load_and_reject_non_strings(tmp_path: Path) -> None:
    """Deployment headers are optional strings."""
    data = _config_data()
    deployments = cast("dict[str, dict[str, object]]", data["deployments"])
    deployments["p1"]["headers"] = {"x-test": "value"}
    config = GATE.load_config(_write_config(tmp_path, data))
    assert config.deployments["p1"].headers == {"x-test": "value"}

    deployments["p1"]["headers"] = {"x-test": 1}
    with pytest.raises(GATE.GateError, match="must be a string"):
        GATE.load_config(_write_config(tmp_path, data))


def test_negative_price_or_limit_is_rejected(tmp_path: Path) -> None:
    """A negative price or limit is a configuration error."""
    data = _config_data()
    deployments = cast("dict[str, dict[str, object]]", data["deployments"])
    deployments["p1"]["cost"] = {"input": -1}
    with pytest.raises(GATE.GateError, match="non-negative"):
        GATE.load_config(_write_config(tmp_path, data))


def test_prompt_version_changes_deployment_identity(tmp_path: Path) -> None:
    """A pinned prompt version produces a stable hash used by identity."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    deployment = config.deployments["p1"]
    other_hash = GATE._prompt_hash("another-version")
    other = GATE.Deployment(
        id=deployment.id,
        release=deployment.release,
        model=deployment.model,
        provider=deployment.provider,
        endpoint=deployment.endpoint,
        quantization=deployment.quantization,
        prompt_hash=other_hash,
        decoding=deployment.decoding,
        key_env=deployment.key_env,
        proposer=deployment.proposer,
        judge=deployment.judge,
    )
    assert GATE._prompt_hash() == GATE.PROMPT_HASH
    assert GATE.deployment_identity(deployment) != GATE.deployment_identity(other)


def test_usage_parser_accepts_common_shapes() -> None:
    """Cached tokens are read from the common provider fields."""
    usage = GATE.parse_usage(
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {"cached_tokens": 40},
            "cache_creation_input_tokens": 10,
        }
    )
    assert usage is not None
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 20
    assert usage.cached_tokens == 40
    assert usage.cache_write_tokens == 10


def test_missing_usage_is_unknown() -> None:
    """A response without usage does not invent token counts."""
    assert GATE.parse_usage(None) is None
    assert GATE.parse_usage({}) is None


def test_cost_prices_cached_tokens_separately() -> None:
    """Cached and cache-write tokens use their own prices."""
    usage = GATE.Usage(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        cached_tokens=40,
        cache_write_tokens=10,
    )
    cost = GATE.CostRates(
        currency="USD",
        unit="per_million_tokens",
        input=1.0,
        output=2.0,
        cache_read=0.5,
        cache_write=1.5,
    )
    value, reason = GATE.compute_cost(usage, cost)
    assert reason is None
    assert value == pytest.approx(0.000135)


def test_missing_price_is_unknown_not_zero() -> None:
    """A deployment without prices has an unknown cost."""
    usage = GATE.Usage(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        cached_tokens=None,
        cache_write_tokens=None,
    )
    value, reason = GATE.compute_cost(usage, None)
    assert value is None
    assert reason == "price missing"


def test_tiered_prices_select_the_context_band() -> None:
    """A prompt above a tier threshold uses that tier's prices."""
    usage = GATE.Usage(
        prompt_tokens=300_000,
        completion_tokens=20,
        total_tokens=300_020,
        cached_tokens=0,
        cache_write_tokens=0,
    )
    cost = GATE.CostRates(
        currency="USD",
        unit="per_million_tokens",
        input=2.0,
        output=10.0,
        cache_read=0.1,
        cache_write=None,
        tiers=(
            GATE.CostTier(
                context=272_000,
                input=4.0,
                output=15.0,
                cache_read=0.2,
                cache_write=None,
            ),
        ),
    )
    tier = GATE.select_cost_tier(usage, cost)
    assert tier is not None
    assert tier.context == 272_000
    value, reason = GATE.compute_cost(usage, cost)
    assert reason is None
    assert value == pytest.approx(1.2003)


def test_base_price_applies_below_a_tier() -> None:
    """A short prompt uses the base price, not a context tier."""
    usage = GATE.Usage(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        cached_tokens=0,
        cache_write_tokens=0,
    )
    cost = GATE.CostRates(
        currency="USD",
        unit="per_million_tokens",
        input=1.0,
        output=2.0,
        cache_read=None,
        cache_write=None,
        tiers=(
            GATE.CostTier(
                context=100_000,
                input=4.0,
                output=8.0,
                cache_read=None,
                cache_write=None,
            ),
        ),
    )
    assert GATE.select_cost_tier(usage, cost) is None
    value, reason = GATE.compute_cost(usage, cost)
    assert reason is None
    assert value == pytest.approx(0.00014)


def test_missing_tier_price_is_unknown() -> None:
    """A selected tier without an output price is unknown, not zero."""
    usage = GATE.Usage(
        prompt_tokens=200_000,
        completion_tokens=20,
        total_tokens=200_020,
        cached_tokens=0,
        cache_write_tokens=0,
    )
    cost = GATE.CostRates(
        currency="USD",
        unit="per_million_tokens",
        input=1.0,
        output=2.0,
        cache_read=None,
        cache_write=None,
        tiers=(
            GATE.CostTier(
                context=100_000,
                input=4.0,
                output=None,
                cache_read=None,
                cache_write=None,
            ),
        ),
    )
    value, reason = GATE.compute_cost(usage, cost)
    assert value is None
    assert reason == "input or output token price missing"


def test_client_parses_usage_and_computes_cost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mocked OpenAI-compatible response records usage and cost."""
    data = _config_data()
    deployments = cast("dict[str, dict[str, object]]", data["deployments"])
    deployments["p1"]["cost"] = {
        "currency": "USD",
        "unit": "per_million_tokens",
        "input": 1.0,
        "output": 2.0,
        "cache_read": 0.5,
    }
    deployments["p1"]["headers"] = {"x-opencode-org-id": "test-org"}
    config = GATE.load_config(_write_config(tmp_path, data))
    deployment = config.deployments["p1"]
    monkeypatch.setenv(deployment.key_env, "test-key")
    captured: dict[str, str] = {}

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [{"message": {"content": "Löschen"}}],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "total_tokens": 120,
                        "prompt_tokens_details": {"cached_tokens": 40},
                    },
                }
            ).encode()

    class FakeConnection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **kwargs: object) -> None:
            captured.update(cast("dict[str, str]", kwargs.get("headers", {})))

        def getresponse(self) -> FakeResponse:
            return FakeResponse()

        def close(self) -> None:
            pass

    monkeypatch.setattr(GATE.http.client, "HTTPSConnection", FakeConnection)
    completion = GATE.OpenAICompatibleClient().complete(deployment, "hello")
    assert completion.text == "Löschen"
    assert completion.usage is not None
    assert completion.usage.cached_tokens == 40
    assert completion.cost_usd == pytest.approx(0.00012)
    assert completion.latency_ms >= 0
    assert captured["x-opencode-org-id"] == "test-org"
    assert captured["Authorization"] == "Bearer test-key"


def test_role_policy_must_name_independent_deployments(tmp_path: Path) -> None:
    """Roles must exist and represent independent families."""
    data = _config_data(extra=(("p3", "r1"),))
    config = GATE.load_config(_write_config(tmp_path, data))
    roles = tmp_path / "roles.json"
    roles.write_text(
        json.dumps({"proposers": ["p1", "p2"], "judge": "j"}), encoding="utf-8"
    )
    GATE.validate_roles(config, GATE.load_roles(roles))

    unknown = tmp_path / "unknown.json"
    unknown.write_text(
        json.dumps({"proposers": ["p1", "missing"], "judge": "j"}),
        encoding="utf-8",
    )
    with pytest.raises(GATE.GateError, match="unknown deployment"):
        GATE.validate_roles(config, GATE.load_roles(unknown))

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        json.dumps({"proposers": ["p1", "p3"], "judge": "j"}), encoding="utf-8"
    )
    with pytest.raises(GATE.GateError, match="at least two families"):
        GATE.validate_roles(config, GATE.load_roles(duplicate))


def test_config_rejects_two_deployments_of_one_release(tmp_path: Path) -> None:
    """Two providers of one release count as one family."""
    data = _config_data(proposers=(("p1", "r1"), ("p2", "r1")))
    with pytest.raises(GATE.GateError, match="at least two model families"):
        GATE.load_config(_write_config(tmp_path, data))


def test_config_rejects_a_judge_from_a_proposer_family(tmp_path: Path) -> None:
    """The judge must not share a family with a proposer."""
    data = _config_data(judge=("j", "r1"))
    with pytest.raises(GATE.GateError, match="judge family"):
        GATE.load_config(_write_config(tmp_path, data))


def test_deployment_identity_changes_with_configuration() -> None:
    """A quantization change produces a different deployment identity."""
    config = GATE.load_config(_write_config(Path("/tmp"), _config_data()))
    deployment = config.deployments["p1"]
    changed = GATE.Deployment(
        id=deployment.id,
        release=deployment.release,
        model=deployment.model,
        provider=deployment.provider,
        endpoint=deployment.endpoint,
        quantization="q4",
        prompt_hash=deployment.prompt_hash,
        decoding=deployment.decoding,
        key_env=deployment.key_env,
        proposer=deployment.proposer,
        judge=deployment.judge,
    )
    assert GATE.deployment_identity(deployment) != GATE.deployment_identity(changed)


def test_qualification_passes_and_a_different_release_does_not_inherit(
    tmp_path: Path,
) -> None:
    """A passing release is eligible; another release is not."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    entries = [polib.POEntry(msgid="Delete", msgstr="Löschen")]
    ledger: dict[str, object] = _ledger()
    client = FakeClient({"p1": "Löschen"})
    record = GATE.qualify_release(
        ledger,
        config,
        GATE.QualificationRequest("r1", "de", entries),
        client,
    )
    assert record["qualified"] is True
    assert record["score"] == 1.0
    assert record["metric"] == "exact-match"
    assert GATE._qualified(ledger, "r2", "de") is None


def test_qualification_without_a_baseline_is_ineligible(tmp_path: Path) -> None:
    """A language with no held-out human entries stays ineligible."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    ledger: dict[str, object] = _ledger()
    record = GATE.qualify_release(
        ledger,
        config,
        GATE.QualificationRequest("r1", "ab", []),
        FakeClient(),
    )
    assert record["qualified"] is False
    assert record["reason"] == "no held-out human entries"


def test_qualification_records_its_calls(tmp_path: Path) -> None:
    """A qualification stores call count, calls and aggregate cost."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    ledger: dict[str, object] = _ledger()
    record = GATE.qualify_release(
        ledger,
        config,
        GATE.QualificationRequest(
            "r1", "de", [polib.POEntry(msgid="Delete", msgstr="Löschen")]
        ),
        FakeClient({"p1": "Löschen"}),
    )
    assert record["call_count"] == 1
    calls = record["calls"]
    assert isinstance(calls, list)
    assert calls
    assert record["total_cost_usd"] is None


def test_conformance_inherits_and_failed_probe_does_not(tmp_path: Path) -> None:
    """A second deployment inherits only after a passing probe."""
    config = GATE.load_config(
        _write_config(tmp_path, _config_data(extra=(("p1b", "r1"), ("similar", "r2"))))
    )
    ledger: dict[str, object] = _ledger()
    GATE.qualify_release(
        ledger,
        config,
        GATE.QualificationRequest(
            "r1", "de", [polib.POEntry(msgid="Delete", msgstr="Löschen")]
        ),
        FakeClient({"p1": "Löschen"}),
    )
    good = GATE.conform_deployment(
        ledger, config, GATE.ConformanceRequest("p1b", "r1", 0.9)
    )
    bad = GATE.conform_deployment(
        ledger, config, GATE.ConformanceRequest("p1b", "r1", 0.1)
    )
    other = GATE.conform_deployment(
        ledger, config, GATE.ConformanceRequest("similar", "r1", 0.9)
    )
    assert good["qualified"] is True
    assert bad["qualified"] is False
    assert other["qualified"] is False


def test_drift_probe_pauses_without_demoting(tmp_path: Path) -> None:
    """A score drop pauses approvals but leaves them intact."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    ledger = _ledger(_machine_record("de", "Delete", "r1", "p1"))
    before = len(LEDGER.approvals(ledger))
    probe = [{"msgid": "Delete", "msgstr": "Löschen"}]
    result = GATE.drift_probe(
        config,
        GATE.DriftRequest("r1", "p1", "de", probe),
        FakeClient({"p1": "Entfernen"}),
    )
    assert result["paused"] is True
    GATE.record_drift_excursion(ledger, result, since="2026-01-01")
    assert GATE.is_paused(ledger, "r1", "de")
    assert len(LEDGER.approvals(ledger)) == before


def test_capability_report_names_no_machine_path_and_retired_release(
    tmp_path: Path,
) -> None:
    """A retired release keeps approvals and loses only future capacity."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    ledger = _ledger(
        _machine_record("de", "Delete", "r1", "p1"),
        _machine_record("fr", "Delete", "old", "p1"),
        _machine_record("es", "Delete", "r1", "p1"),
    )
    GATE._replace_section(
        ledger,
        "qualifications",
        {"release": "r1", "language": "de", "qualified": True},
        key_fields=("release", "language"),
    )
    GATE._replace_section(
        ledger,
        "qualifications",
        {"release": "old", "language": "fr", "qualified": True},
        key_fields=("release", "language"),
    )
    report = GATE.capability_report(ledger, config)
    languages = cast("dict[str, dict[str, object]]", report["languages"])
    assert languages["de"]["machine_path"] is True
    assert languages["fr"]["retired_releases"] == ["old"]
    assert languages["fr"]["machine_path"] is False
    assert "fr" in cast("list[str]", report["no_machine_path"])
    assert "es" in cast("list[str]", report["no_machine_path"])


def test_gate_approves_when_every_check_and_the_judge_agree(
    tmp_path: Path,
) -> None:
    """Two families propose, the third judges, and the string is approved."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    decision = GATE.run_gate(
        "Delete",
        "de",
        config,
        FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    assert decision.approved is True
    assert decision.record is not None
    assert decision.record["provenance_class"] == "machine-strong"
    assert decision.record["model_release"] == "r1"
    assert decision.record["deployment"] == "p1"
    assert decision.evidence["prompt_version"] == GATE.PROMPT_VERSION


def test_gate_abstains_without_two_families(tmp_path: Path) -> None:
    """One family cannot supply the independent second opinion."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    only_one = GATE.GateConfig(
        releases=config.releases,
        deployments={"p1": config.deployments["p1"], "j": config.deployments["j"]},
        thresholds=config.thresholds,
    )
    decision = GATE.run_gate("Delete", "de", only_one, FakeClient({"p1": "Löschen"}))
    assert decision.approved is False
    assert "independent" in decision.reason


def test_abstained_gate_run_is_measurable(tmp_path: Path) -> None:
    """An abstention is recorded with its calls and outcome."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    only_one = GATE.GateConfig(
        releases=config.releases,
        deployments={"p1": config.deployments["p1"], "j": config.deployments["j"]},
        thresholds=config.thresholds,
    )
    ledger: dict[str, object] = _ledger()
    decision = GATE.run_gate("Delete", "de", only_one, FakeClient({"p1": "Löschen"}))
    record = GATE.record_gate_run(ledger, decision, "de")
    assert record["outcome"] == "abstained"
    assert record["call_count"] == 1
    assert LEDGER.section(ledger, "gate_runs") == [record]


def _gate_run(
    ledger: dict[str, object],
    deployment: str,
    *,
    language: str,
    outcome: str,
    winning: str | None,
    cost: float | None,
) -> None:
    """Append a synthetic gate run for the cost report."""
    LEDGER.add_section_record(
        ledger,
        "gate_runs",
        {
            "action": "gate",
            "language": language,
            "outcome": outcome,
            "reason": "test",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "winning_deployment": winning,
            "proposers": [deployment],
            "calls": [
                {
                    "deployment": deployment,
                    "release": "r1",
                    "role": "proposer",
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 10,
                        "total_tokens": 110,
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "cost_usd": cost,
                    "latency_ms": 2.0,
                }
            ],
        },
    )


def test_cost_report_compares_spend_and_approval_rate() -> None:
    """A cheap model that abstains is not presented as better."""
    ledger = _ledger(
        _machine_record("de", "One", "r1", "p1"),
        _machine_record("de", "Two", "r1", "p1"),
        _machine_record("de", "Three", "r1", "p2"),
    )
    _gate_run(
        ledger,
        "p1",
        language="de",
        outcome="approved",
        winning="p1",
        cost=0.02,
    )
    _gate_run(
        ledger,
        "p1",
        language="de",
        outcome="approved",
        winning="p1",
        cost=0.02,
    )
    _gate_run(
        ledger,
        "p2",
        language="de",
        outcome="abstained",
        winning=None,
        cost=0.005,
    )
    _gate_run(
        ledger,
        "p2",
        language="de",
        outcome="abstained",
        winning=None,
        cost=0.005,
    )
    report = GATE.costs_report(ledger)
    languages = cast("dict[str, dict[str, dict[str, object]]]", report["languages"])
    first = languages["de"]["p1"]
    second = languages["de"]["p2"]
    assert first["approval_rate"] == 1.0
    assert first["cost_per_approval"] == pytest.approx(0.02)
    assert second["approval_rate"] == 0.0
    assert second["abstentions"] == 2
    assert second["cost_per_approval"] is None


def test_cost_report_marks_unknown_cost() -> None:
    """A call without a price is listed, not treated as free."""
    ledger = _ledger(_machine_record("de", "One", "r1", "p1"))
    _gate_run(
        ledger,
        "p1",
        language="de",
        outcome="approved",
        winning="p1",
        cost=None,
    )
    report = GATE.costs_report(ledger)
    languages = cast("dict[str, dict[str, dict[str, object]]]", report["languages"])
    bucket = languages["de"]["p1"]
    assert bucket["unknown_cost_calls"] == 1
    assert bucket["cost_per_approval"] is None


def _costed_config(tmp_path: Path) -> GateConfig:
    """Load a config whose deployments all carry prices."""
    data = _config_data()
    deployments = cast("dict[str, dict[str, object]]", data["deployments"])
    for deployment in deployments.values():
        deployment["cost"] = {
            "currency": "USD",
            "unit": "per_million_tokens",
            "input": 1.0,
            "output": 2.0,
            "cache_read": 0.5,
        }
    return cast("GateConfig", GATE.load_config(_write_config(tmp_path, data)))


def _qualification_setup(
    tmp_path: Path, *, costed: bool = False
) -> tuple[Path, Path, Path]:
    """Write a config, a human approval and a matching catalog."""
    data = _config_data()
    if costed:
        deployments = cast("dict[str, dict[str, object]]", data["deployments"])
        for deployment in deployments.values():
            deployment["cost"] = {
                "currency": "USD",
                "unit": "per_million_tokens",
                "input": 1.0,
                "output": 2.0,
                "cache_read": 0.5,
            }
    config_path = _write_config(tmp_path, data)
    entry = polib.POEntry(msgid="Delete", msgstr="Löschen")
    record = cast(
        "dict[str, object]",
        LEDGER.make_record(
            "de",
            entry,
            "human-review",
            context=LEDGER.ApprovalContext(approval_date="2026-01-01"),
        ),
    )
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger(record))
    catalog_path = tmp_path / "de.po"
    catalog = polib.POFile()
    catalog.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    catalog.append(entry)
    catalog.save(str(catalog_path))
    return config_path, ledger_path, catalog_path


def _drift_setup(
    tmp_path: Path,
    *,
    costed: bool = False,
    items: list[dict[str, str]] | None = None,
    approvals: tuple[dict[str, object], ...] = (),
) -> tuple[Path, Path, Path]:
    """Write a config, a ledger and a drift probe."""
    data = _config_data()
    if costed:
        deployments = cast("dict[str, dict[str, object]]", data["deployments"])
        for deployment in deployments.values():
            deployment["cost"] = {
                "currency": "USD",
                "unit": "per_million_tokens",
                "input": 1.0,
                "output": 2.0,
                "cache_read": 0.5,
            }
    config_path = _write_config(tmp_path, data)
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger(*approvals))
    probe_path = tmp_path / "de.json"
    probe_path.write_text(
        json.dumps(
            {
                "language": "de",
                "version": 1,
                "items": items
                if items is not None
                else [{"msgid": "Delete", "msgstr": "Löschen"}],
            }
        ),
        encoding="utf-8",
    )
    return config_path, ledger_path, probe_path


def _completion(text: str) -> object:
    """Build one deterministic completion for a probe client."""
    return GATE.Completion(
        text=text,
        deployment="p1",
        release="r1",
        model="a",
        usage=GATE.Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_tokens=0,
            cache_write_tokens=0,
        ),
        latency_ms=1.0,
    )


def test_estimate_tokens_and_output_bounds() -> None:
    """The heuristic is configurable and the output range is bounded."""
    assert GATE.estimate_tokens("12345678", 4.0) == 2
    assert GATE.estimate_tokens("x", 4.0) == 1


def test_gate_estimate_includes_proposers_judge_and_backtranslation(
    tmp_path: Path,
) -> None:
    """A sentence estimate includes two proposers, judge and back-translation."""
    config = _costed_config(tmp_path)
    estimate = GATE.estimate_gate(
        config,
        "de",
        ["This is a sufficiently long sentence for back translation."],
    )
    deployments = {item.deployment: item for item in estimate.deployments}
    assert set(deployments) == {"p1", "p2", "j"}
    assert deployments["p1"].calls == 1
    assert deployments["p2"].calls == 1
    assert deployments["j"].calls == 2
    assert estimate.high_cost_usd is not None
    assert estimate.high_cost_usd > 0


def test_qualification_and_drift_estimates(tmp_path: Path) -> None:
    """Qualification and drift use their entry and probe counts."""
    config = _costed_config(tmp_path)
    entries = [
        polib.POEntry(msgid="Delete", msgstr="Löschen"),
        polib.POEntry(msgid="Open", msgstr="Öffnen"),
    ]
    qualification = GATE.estimate_qualification(
        config, GATE.QualificationRequest("r1", "de", entries)
    )
    assert qualification.deployments[0].calls == 2
    drift = GATE.estimate_drift(
        config,
        GATE.DriftRequest(
            "r1",
            "p1",
            "de",
            [{"msgid": "Delete", "msgstr": "Löschen"}],
        ),
    )
    assert drift.deployments[0].calls == 1


def test_budget_blocks_qualification_before_any_call(tmp_path: Path) -> None:
    """An over-budget qualification makes no model request."""
    config = _costed_config(tmp_path)
    ledger: dict[str, object] = _ledger()

    client = Mock()
    client.complete.side_effect = AssertionError("no request expected")
    with pytest.raises(GATE.BudgetExceededError):
        GATE.qualify_release(
            ledger,
            config,
            GATE.QualificationRequest(
                "r1",
                "de",
                [polib.POEntry(msgid="Delete", msgstr="Löschen")],
                budget_usd=0.0,
            ),
            client,
        )
    client.complete.assert_not_called()


def test_gate_max_cost_stops_before_a_request(tmp_path: Path) -> None:
    """The gate command exits non-zero on an over-budget estimate."""
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger())
    status = GATE.main(
        [
            "--ledger",
            str(ledger_path),
            "gate",
            "--language",
            "de",
            "--msgid",
            "Delete",
            "--max-cost",
            "0",
        ]
    )
    assert status == 1


def test_estimate_cli_reports_a_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The estimate command emits the per-deployment range as JSON."""
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger())
    status = GATE.main(
        [
            "--ledger",
            str(ledger_path),
            "estimate",
            "--action",
            "gate",
            "--language",
            "de",
            "--msgid",
            "Delete",
            "--json",
        ]
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "gate"
    assert len(payload["deployments"]) == 3
    assert payload["high_cost_usd"] is not None


def test_qualify_cli_records_a_passing_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A matching proposal writes a qualified record and a summary."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
        ]
    )
    assert status == 0
    records = LEDGER.section(LEDGER.load_ledger(ledger_path), "qualifications")
    assert len(records) == 1
    assert records[0]["qualified"] is True
    assert records[0]["score"] == 1.0
    assert records[0]["baseline_size"] == 1
    out = capsys.readouterr().out
    assert "qualification de" in out
    assert "qualified" in out
    assert "score 1.0" in out


def test_qualify_cli_reports_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The JSON form prints the stored record."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
            "--json",
        ]
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["release"] == "r1"
    assert payload["language"] == "de"
    assert payload["qualified"] is True
    assert payload["score"] == 1.0


def test_qualify_cli_records_a_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A proposal below the tolerance is recorded as not qualified."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Falsch"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
        ]
    )
    assert status == 0
    records = LEDGER.section(LEDGER.load_ledger(ledger_path), "qualifications")
    assert len(records) == 1
    assert records[0]["qualified"] is False
    assert records[0]["score"] == 0.0
    assert "not qualified" in capsys.readouterr().out


def test_qualify_cli_records_no_baseline_without_a_model_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty baseline records the reason and makes no request."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    _write_ledger(ledger_path, _ledger())
    client = Mock()
    client.complete.side_effect = AssertionError("no request expected")
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
        ]
    )
    assert status == 0
    records = LEDGER.section(LEDGER.load_ledger(ledger_path), "qualifications")
    assert len(records) == 1
    assert records[0]["qualified"] is False
    assert records[0]["reason"] == "no held-out human entries"
    client.complete.assert_not_called()
    assert "ineligible" in capsys.readouterr().out


def test_qualify_cli_rejects_an_unknown_release(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown release fails before reading the ledger or catalog."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "missing",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
        ]
    )
    assert status == 1
    assert "not configured" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_qualify_cli_rejects_an_unreadable_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable catalog leaves the ledger unchanged."""
    config_path, ledger_path, _catalog_path = _qualification_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(tmp_path / "missing.po"),
        ]
    )
    assert status == 1
    assert "cannot read catalog" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_qualify_cli_reports_a_missing_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing key variable is named and no record is written."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    monkeypatch.delenv("SCANTPAPER_TEST_KEY", raising=False)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
        ]
    )
    assert status == 1
    err = capsys.readouterr().err
    assert "SCANTPAPER_TEST_KEY" in err
    assert "Bearer" not in err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_qualify_cli_rejects_a_non_positive_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A zero count is rejected before selecting entries."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "0",
        ]
    )
    assert status == 1
    assert "must be positive" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_qualify_cli_stops_before_a_request_when_over_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An over-budget estimate makes no call and writes no record."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path, costed=True)
    client = Mock()
    client.complete.side_effect = AssertionError("no request expected")
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "qualify",
            "--release",
            "r1",
            "--language",
            "de",
            "--catalog",
            str(catalog_path),
            "--count",
            "1",
            "--max-cost",
            "0",
        ]
    )
    assert status == 1
    client.complete.assert_not_called()
    assert LEDGER.section(LEDGER.load_ledger(ledger_path), "qualifications") == []
    assert "exceeds budget" in capsys.readouterr().err


def test_qualify_cli_replaces_an_earlier_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second run updates the one record for the release and language."""
    config_path, ledger_path, catalog_path = _qualification_setup(tmp_path)
    clients = [FakeClient({"p1": "Löschen"}), FakeClient({"p1": "Falsch"})]
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: clients.pop(0))
    args = [
        "--config",
        str(config_path),
        "--ledger",
        str(ledger_path),
        "qualify",
        "--release",
        "r1",
        "--language",
        "de",
        "--catalog",
        str(catalog_path),
        "--count",
        "1",
    ]
    assert GATE.main(args) == 0
    assert GATE.main(args) == 0
    records = LEDGER.section(LEDGER.load_ledger(ledger_path), "qualifications")
    assert len(records) == 1
    assert records[0]["qualified"] is False
    assert records[0]["score"] == 0.0


def test_drift_cli_reports_a_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A probe above the threshold reports and writes no pause."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path)
    client = Mock(wraps=FakeClient({"p1": "Löschen"}))
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 0
    assert client.complete.call_count == 1
    ledger = LEDGER.load_ledger(ledger_path)
    assert LEDGER.section(ledger, "drift_excursions") == []
    out = capsys.readouterr().out
    assert "drift de p1 (r1)" in out
    assert "score 1.0" in out
    assert "ok" in out


def test_drift_cli_makes_one_call_per_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe sends one request for every item."""
    items = [
        {"msgid": "Delete", "msgstr": "Löschen"},
        {"msgid": "Open", "msgstr": "Öffnen"},
    ]
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, items=items)
    client = Mock()
    client.complete.side_effect = [_completion("Löschen"), _completion("Öffnen")]
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 0
    assert client.complete.call_count == 2
    assert LEDGER.section(LEDGER.load_ledger(ledger_path), "drift_excursions") == []


def test_drift_cli_records_a_pause_without_demoting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A below-threshold probe pauses and leaves approvals untouched."""
    approval = _machine_record("de", "Delete", "r1", "p1")
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, approvals=(approval,))
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Falsch"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
            "--since",
            "2026-01-01",
        ]
    )
    assert status == 0
    ledger = LEDGER.load_ledger(ledger_path)
    excursions = LEDGER.section(ledger, "drift_excursions")
    assert len(excursions) == 1
    assert excursions[0]["release"] == "r1"
    assert excursions[0]["deployment"] == "p1"
    assert excursions[0]["language"] == "de"
    assert excursions[0]["since"] == "2026-01-01"
    assert excursions[0]["status"] == "paused"
    assert len(LEDGER.approvals(ledger)) == 1
    assert "paused" in capsys.readouterr().out


def test_drift_cli_defaults_since_to_today(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recorded pause without --since uses the run date."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Falsch"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 0
    excursions = LEDGER.section(LEDGER.load_ledger(ledger_path), "drift_excursions")
    assert excursions[0]["since"] == GATE._today()


def test_drift_cli_uses_the_default_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default path is the language file under the probe directory."""
    config_path, ledger_path, _probe_path = _drift_setup(tmp_path)
    monkeypatch.setattr(GATE, "DEFAULT_PROBE_DIR", tmp_path)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
        ]
    )
    assert status == 0


def test_drift_cli_dry_run_does_not_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run reports a pause without writing it."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Falsch"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
            "--dry-run",
        ]
    )
    assert status == 0
    assert ledger_path.read_text(encoding="utf-8") == before
    assert "paused" in capsys.readouterr().out


def test_drift_cli_rejects_an_unknown_deployment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown deployment fails before reading the probe."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "missing",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 1
    assert "not configured" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_drift_cli_rejects_an_empty_probe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty probe is an error, not a false pause."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, items=[])
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 1
    assert "has no items" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_drift_cli_rejects_an_unreadable_probe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable probe leaves the ledger unchanged."""
    config_path, ledger_path, _probe_path = _drift_setup(tmp_path)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(tmp_path / "missing.json"),
        ]
    )
    assert status == 1
    assert "cannot read probe" in capsys.readouterr().err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_drift_cli_reports_a_missing_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing key variable is named and no pause is written."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path)
    monkeypatch.delenv("SCANTPAPER_TEST_KEY", raising=False)
    before = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
        ]
    )
    assert status == 1
    err = capsys.readouterr().err
    assert "SCANTPAPER_TEST_KEY" in err
    assert "Bearer" not in err
    assert ledger_path.read_text(encoding="utf-8") == before


def test_drift_cli_stops_before_a_request_when_over_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An over-budget probe makes no call and writes no pause."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, costed=True)
    client = Mock()
    client.complete.side_effect = AssertionError("no request expected")
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
            "--max-cost",
            "0",
        ]
    )
    assert status == 1
    client.complete.assert_not_called()
    assert LEDGER.section(LEDGER.load_ledger(ledger_path), "drift_excursions") == []
    assert "exceeds budget" in capsys.readouterr().err


def test_drift_cli_reports_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The JSON form carries the inferred release and probe result."""
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, costed=True)
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(ledger_path),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe_path),
            "--json",
        ]
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["release"] == "r1"
    assert payload["score"] == 1.0
    assert payload["threshold"] == 0.75
    assert payload["paused"] is False
    assert payload["call_count"] == 1
    assert "total_cost_usd" in payload


def test_drift_cli_repeated_failure_keeps_the_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second failing run leaves the language paused."""
    approval = _machine_record("de", "Delete", "r1", "p1")
    config_path, ledger_path, probe_path = _drift_setup(tmp_path, approvals=(approval,))
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Falsch"}),
    )
    args = [
        "--config",
        str(config_path),
        "--ledger",
        str(ledger_path),
        "drift",
        "--deployment",
        "p1",
        "--language",
        "de",
        "--probe",
        str(probe_path),
    ]
    assert GATE.main(args) == 0
    assert GATE.main(args) == 0
    ledger = LEDGER.load_ledger(ledger_path)
    assert GATE.is_paused(ledger, "r1", "de")
    assert len(LEDGER.approvals(ledger)) == 1


def test_costs_cli_reports_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The costs command emits the report as JSON."""
    ledger: dict[str, object] = _ledger(_machine_record("de", "One", "r1", "p1"))
    _gate_run(
        ledger,
        "p1",
        language="de",
        outcome="approved",
        winning="p1",
        cost=0.01,
    )
    ledger_path = _write_ledger(tmp_path / "ledger.json", ledger)
    status = GATE.main(["--ledger", str(ledger_path), "costs", "--json"])
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["languages"]["de"]["p1"]["calls"] == 1


def test_deterministic_checks_reject_a_placeholder_change() -> None:
    """A placeholder change blocks a proposal before judging."""
    defects = GATE.deterministic_checks("Open file: %s", "Apri file: %d")
    assert "placeholders changed" in defects


def test_gate_abstains_when_backtranslation_changes_meaning(
    tmp_path: Path,
) -> None:
    """A sentence whose back-translation differs is not approved."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = "This is a sufficiently long sentence for a back translation."
    decision = GATE.run_gate(
        source,
        "de",
        config,
        FakeClient(
            {
                "p1": "Ein ausreichend langer Satz.",
                "p2": "Ein ausreichend langer Satz.",
            },
            backtranslation="Something completely unrelated.",
        ),
    )
    assert decision.approved is False
    assert "back-translation" in decision.reason


def test_gate_accepts_an_unchanged_backtranslation(tmp_path: Path) -> None:
    """A default back-translation that returns the source preserves meaning."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = "This is a sufficiently long sentence for a back translation."
    decision = GATE.run_gate(
        source,
        "de",
        config,
        FakeClient(
            {"p1": "Ein langer Satz.", "p2": "Ein langer Satz."},
            backtranslation=source,
        ),
    )
    assert decision.approved is True


def test_approve_clears_fuzzy_and_records_the_approval(tmp_path: Path) -> None:
    """Only an approved decision clears the fuzzy flag."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    catalog_path = tmp_path / "de.po"
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    entry = polib.POEntry(msgid="Delete", msgstr="Löschen")
    entry.flags.append("fuzzy")
    po.append(entry)
    po.save(str(catalog_path))
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger())

    decision = GATE.run_gate(
        "Delete",
        "de",
        config,
        FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    GATE.approve_decision(catalog_path, ledger_path, "Delete", decision)

    saved = polib.pofile(str(catalog_path)).find("Delete")
    assert saved is not None
    assert "fuzzy" not in saved.flags
    assert len(LEDGER.approvals(LEDGER.load_ledger(ledger_path))) == 1


def test_language_revocation_demotes_only_that_language(tmp_path: Path) -> None:
    """A language revocation leaves other languages valid."""
    ledger_path = tmp_path / "ledger.json"
    _write_ledger(
        ledger_path,
        _ledger(
            _machine_record("de", "Delete", "r1", "p1"),
            _machine_record("fr", "Delete", "r1", "p1"),
        ),
    )
    GATE.revoke(ledger_path, "language", "de")
    index = LEDGER.approval_index(LEDGER.load_ledger(ledger_path))
    assert set(index) == {("fr", "", "Delete", "")}


def test_deployment_and_release_revocations_have_their_own_scope(
    tmp_path: Path,
) -> None:
    """Deployment and release revocations demote only their own approvals."""
    deployment_ledger = tmp_path / "deployment.json"
    _write_ledger(
        deployment_ledger,
        _ledger(
            _machine_record("de", "Delete", "r1", "p1"),
            _machine_record("fr", "Delete", "r1", "p2"),
        ),
    )
    GATE.revoke(deployment_ledger, "deployment", "p1")
    assert set(LEDGER.approval_index(LEDGER.load_ledger(deployment_ledger))) == {
        ("fr", "", "Delete", "")
    }

    release_ledger = tmp_path / "release.json"
    _write_ledger(
        release_ledger,
        _ledger(
            _machine_record("de", "Delete", "r1", "p1"),
            _machine_record("fr", "Delete", "r1", "p2"),
            _machine_record("de", "Other", "r2", "p3"),
        ),
    )
    GATE.revoke(release_ledger, "release", "r1")
    assert set(LEDGER.approval_index(LEDGER.load_ledger(release_ledger))) == {
        ("de", "", "Other", "")
    }


def test_sample_reports_a_rate_and_a_high_rate_demotes() -> None:
    """A sample changes no approval; an excessive rate revokes the language."""
    ledger: dict[str, object] = _ledger(
        _machine_record("de", "One", "r1", "p1"),
        _machine_record("de", "Two", "r1", "p1", msgstr="Zwei"),
    )
    before = len(LEDGER.approvals(ledger))
    sample = GATE.random_sample(ledger, "de", 10, 7)
    assert len(sample) == 2
    assert len(LEDGER.approvals(ledger)) == before

    GATE.record_false_positive(ledger, sample[0], note="wrong")
    assert GATE.defect_rate(ledger, "de") == 0.5
    assert GATE.demote_if_over_threshold(ledger, "de", 0.6) is False
    assert GATE.demote_if_over_threshold(ledger, "de", 0.4) is True
    assert any(
        record.get("scope") == "language" and record.get("value") == "de"
        for record in LEDGER.section(ledger, "revocations")
    )


def test_missing_credential_names_the_variable_without_a_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing key is reported by name and never reads or prints it."""
    config = GATE.load_config(
        _write_config(tmp_path, _config_data(key_env="SCANTPAPER_MISSING_KEY"))
    )
    monkeypatch.delenv("SCANTPAPER_MISSING_KEY", raising=False)
    with pytest.raises(GATE.CredentialError) as raised:
        GATE.OpenAICompatibleClient().complete(config.deployments["p1"], "hello")
    message = str(raised.value)
    assert "SCANTPAPER_MISSING_KEY" in message
    assert "Bearer" not in message


def _write_mo(path: Path, msgid: str, msgstr: str) -> None:
    """Write a compiled one-entry catalog."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save_as_mofile(str(path))


def _tm_database(tmp_path: Path) -> Path:
    """Build a two-project translation memory that agrees on Löschen."""
    tm = sys.modules["tm_index"]
    locale = tmp_path / "locale"
    for project in ("one", "two"):
        _write_mo(locale / "de" / "LC_MESSAGES" / f"{project}.mo", "Delete", "Löschen")
    manifest = tmp_path / "tm-sources.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "project": project,
                        "language": "*",
                        "license": "BSD-3-Clause",
                        "origin": "test",
                    }
                    for project in ("one", "two")
                ],
            }
        ),
        encoding="utf-8",
    )
    sources, skipped = tm.resolve_sources(
        tm.load_manifest(manifest), locale_root=locale
    )
    db = tmp_path / "tm.sqlite3"
    tm.build_index(db, sources, skipped)
    return db


def test_evidence_ladder_has_all_three_classes(tmp_path: Path) -> None:
    """Unchanged, mechanical rebase and dominant TM each get their class."""
    db = _tm_database(tmp_path)
    assert (
        GATE.classify_evidence("Delete", "de", "Löschen", "Löschen")
        == "human-historical"
    )
    assert (
        GATE.classify_evidence("Error: %s", "de", "Fehler:% s", "Fehler: %s")
        == "in-project-rebase"
    )
    assert (
        GATE.classify_evidence("Delete", "de", "Entfernen", "Löschen", tm_db=db)
        == "tm-consensus"
    )
    assert GATE.classify_evidence("Delete", "de", "Entfernen", "Weg", tm_db=db) is None


def test_tm_match_alone_does_not_approve(tmp_path: Path) -> None:
    """A dominant match without the gate's evidence is not an approval."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    db = _tm_database(tmp_path)
    only_one = GATE.GateConfig(
        releases=config.releases,
        deployments={"p1": config.deployments["p1"], "j": config.deployments["j"]},
        thresholds=config.thresholds,
    )
    decision = GATE.run_gate(
        "Delete",
        "de",
        only_one,
        FakeClient({"p1": "Löschen"}),
        options=GATE.GateOptions(tm_db=db),
    )
    assert decision.approved is False


def test_dominant_tm_match_completes_the_evidence(tmp_path: Path) -> None:
    """A matching dominant TM entry yields tm-consensus, not machine-strong."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    db = _tm_database(tmp_path)
    decision = GATE.run_gate(
        "Delete",
        "de",
        config,
        FakeClient({"p1": "Löschen", "p2": "Löschen"}),
        options=GATE.GateOptions(tm_db=db),
    )
    assert decision.approved is True
    assert decision.record is not None
    assert decision.record["provenance_class"] == "tm-consensus"


def test_high_impact_string_cannot_be_approved_from_one_weak_proposal(
    tmp_path: Path,
) -> None:
    """A menu action needs the full independent-family evidence."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    only_one = GATE.GateConfig(
        releases=config.releases,
        deployments={"p1": config.deployments["p1"], "j": config.deployments["j"]},
        thresholds=config.thresholds,
    )
    assert GATE.is_high_impact("Delete")
    decision = GATE.run_gate("Delete", "de", only_one, FakeClient({"p1": "Löschen"}))
    assert decision.approved is False

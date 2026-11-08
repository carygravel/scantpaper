"""Tests for the machine gate in dev/translation_gate.py."""

from __future__ import annotations

import gettext
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

    from translation_gate import GateConfig, GateDecision

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


def _load_compile_mo() -> ModuleType:
    """Import dev/compile_mo.py with its sibling modules."""
    spec = importlib.util.spec_from_file_location(
        "compile_mo", str(DEV_DIR / "compile_mo.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["compile_mo"] = module
    spec.loader.exec_module(module)
    return module


class FakeClient:
    """A deterministic stand-in for an OpenAI-compatible deployment."""

    def __init__(
        self,
        answers: dict[str, str] | None = None,
        *,
        judge: str = "A",
        backtranslation: str | None = None,
        plural_answers: dict[str, str] | None = None,
        backtranslations: list[str] | None = None,
        cost_usd: float | None = None,
    ) -> None:
        """Store the canned proposal, judge and back-translation answers."""
        self.answers = answers or {}
        self.judge = judge
        self.backtranslation = backtranslation
        self.plural_answers = plural_answers
        self.backtranslations = backtranslations
        self.cost_usd = cost_usd
        self._back_index = 0

    def complete(self, deployment: object, prompt: str) -> object:
        """Answer a proposal, judge or back-translation prompt."""
        if prompt.startswith("Choose the best"):
            text = self.judge
        elif "back into English" in prompt:
            if self.backtranslations is not None:
                text = self.backtranslations[
                    self._back_index % len(self.backtranslations)
                ]
                self._back_index += 1
            else:
                text = self.backtranslation or ""
        elif "plural forms" in prompt and "It has" in prompt:
            deployment_id = str(vars(deployment)["id"])
            answers = self.plural_answers or self.answers
            text = answers.get(deployment_id, "translated")
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
            cost_usd=self.cost_usd,
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


def test_language_threshold_overrides_qualification(tmp_path: Path) -> None:
    """A per-language tolerance replaces the global qualification threshold."""
    data = _config_data()
    data["language_thresholds"] = {"de": {"qualification": 0.35}}
    config = GATE.load_config(_write_config(tmp_path, data))
    entries = [
        polib.POEntry(msgid="Delete", msgstr="Löschen"),
        polib.POEntry(msgid="Open", msgstr="Öffnen"),
    ]
    record = GATE.qualify_release(
        _ledger(),
        config,
        GATE.QualificationRequest("r1", "de", entries),
        FakeClient({"p1": "Löschen"}),
    )
    assert record["score"] == 0.5
    assert record["tolerance"] == 0.35
    assert record["qualified"] is True


def test_language_threshold_overrides_drift(tmp_path: Path) -> None:
    """A per-language drift threshold replaces the global one."""
    data = _config_data()
    data["language_thresholds"] = {"de": {"drift": 0.3}}
    config = GATE.load_config(_write_config(tmp_path, data))
    probe = [
        {"msgid": "Delete", "msgstr": "Löschen"},
        {"msgid": "Open", "msgstr": "Öffnen"},
    ]
    result = GATE.drift_probe(
        config,
        GATE.DriftRequest("r1", "p1", "de", probe),
        FakeClient({"p1": "Löschen"}),
    )
    assert result["score"] == 0.5
    assert result["threshold"] == 0.3
    assert result["paused"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        [],
        {"de": []},
        {"de": {"qualification": "high"}},
        {"de": {"qualification": 1.5}},
        {"": {"drift": 0.3}},
    ],
)
def test_invalid_language_thresholds_are_rejected(
    tmp_path: Path, overrides: object
) -> None:
    """Malformed per-language thresholds fail validation."""
    data = _config_data()
    data["language_thresholds"] = overrides
    with pytest.raises(GATE.GateError, match="language_thresholds"):
        GATE.load_config(_write_config(tmp_path, data))


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
        FakeClient({"p1": "Löschen", "p2": "Entfernen"}),
    )
    assert decision.approved is True
    assert decision.record is not None
    assert decision.record["provenance_class"] == "machine-strong"
    assert decision.record["model_release"] == "r1"
    assert decision.record["deployment"] == "p1"
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["deployment"] == "j"
    assert judge["verdict"] == "A"
    assert decision.evidence["prompt_version"] == GATE.PROMPT_VERSION


def test_gate_approves_an_identical_tie_without_the_judge(
    tmp_path: Path,
) -> None:
    """Two independent families agreeing is a tie and never calls the judge."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    client = Mock(wraps=FakeClient({"p1": "Löschen", "p2": "Löschen"}))
    decision = GATE.run_gate("Delete", "de", config, client)
    assert decision.approved is True
    assert client.complete.call_count == 2
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["tie"] is True
    assert judge["verdict"] == "identical"
    assert judge["families"] == ["family-a", "family-b"]
    assert "deployment" not in judge
    assert decision.record is not None
    assert decision.record["provenance_class"] == "machine-strong"

    ledger: dict[str, object] = _ledger()
    GATE.record_gate_run(ledger, decision, "de")
    runs = LEDGER.section(ledger, "gate_runs")
    assert len(runs) == 1
    calls = cast("list[dict[str, object]]", runs[0]["calls"])
    assert [call.get("role") for call in calls] == ["proposer", "proposer"]
    assert runs[0]["call_count"] == 2


def test_gate_judges_differing_proposals(tmp_path: Path) -> None:
    """Differing proposals still go through the blind judge."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    client = Mock(wraps=FakeClient({"p1": "Löschen", "p2": "Entfernen"}, judge="B"))
    decision = GATE.run_gate("Delete", "de", config, client)
    assert decision.approved is True
    assert client.complete.call_count == 3
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["deployment"] == "j"
    assert judge["verdict"] == "B"
    assert "tie" not in judge
    assert decision.record is not None
    assert decision.record["deployment"] == "p2"


def test_gate_judges_a_single_passing_proposal(tmp_path: Path) -> None:
    """A single passing proposal is not a tie and still uses the judge."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    client = Mock(wraps=FakeClient({"p1": "Offen %d", "p2": "Öffnen %s"}, judge="A"))
    decision = GATE.run_gate("Open %s", "de", config, client)
    assert decision.approved is True
    assert client.complete.call_count == 3
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["deployment"] == "j"
    assert judge["verdict"] == "A"


def test_gate_abstains_when_every_proposal_fails_a_check(
    tmp_path: Path,
) -> None:
    """No passing proposal means no tie and no judge call."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    client = Mock(wraps=FakeClient({"p1": "Offen %d", "p2": "Offen %d"}))
    decision = GATE.run_gate("Open %s", "de", config, client)
    assert decision.approved is False
    assert "failed a deterministic check" in decision.reason
    assert client.complete.call_count == 2


def test_gate_sentence_tie_still_backtranslates(tmp_path: Path) -> None:
    """A sentence tie still spends the back-translation call."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = "This is a sufficiently long sentence for back translation."
    client = Mock(
        wraps=FakeClient(
            {
                "p1": "Ein ausreichend langer Satz.",
                "p2": "Ein ausreichend langer Satz.",
            },
            backtranslation=source,
        )
    )
    decision = GATE.run_gate(source, "de", config, client)
    assert decision.approved is True
    assert client.complete.call_count == 3
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["tie"] is True


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


def _write_catalog(
    path: Path,
    entries: tuple[polib.POEntry, ...],
    *,
    plural_forms: str | None = None,
) -> Path:
    """Write a catalog with the standard test metadata."""
    catalog = polib.POFile()
    catalog.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
    }
    if plural_forms is not None:
        catalog.metadata["Plural-Forms"] = plural_forms
    for entry in entries:
        catalog.append(entry)
    catalog.save(str(path))
    return path


def _batch_entry(
    msgid: str,
    msgstr: str = "",
    *,
    fuzzy: bool = False,
    plural: bool = False,
    plural_msgid: str | None = None,
    plural_forms: dict[int, str] | None = None,
    context: str | None = None,
) -> polib.POEntry:
    """Build one entry for a batch test."""
    entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
    if fuzzy:
        entry.flags.append("fuzzy")
    if plural:
        entry.msgid_plural = plural_msgid or f"{msgid}s"
        entry.msgstr_plural = (
            dict(plural_forms) if plural_forms is not None else {0: "", 1: ""}
        )
    if context is not None:
        entry.msgctxt = context
    return entry


def _batch_decision(msgid: str, translation: str | None = "Löschen") -> GateDecision:
    """Build an approved decision for one entry."""
    entry = polib.POEntry(msgid=msgid, msgstr=translation or "")
    record = LEDGER.make_record(
        "de",
        entry,
        "machine-strong",
        context=LEDGER.ApprovalContext(
            approval_date="2026-01-01",
            model_release="r1",
            deployment="p1",
        ),
    )
    return cast(
        "GateDecision",
        GATE.GateDecision(
            approved=True,
            reason="every check and the judge agree",
            translation=translation,
            record=record,
        ),
    )


def _batch_setup(
    tmp_path: Path,
    *,
    costed: bool = False,
    qualified: bool = True,
    paused: bool = False,
    entries: tuple[polib.POEntry, ...] = (),
    plural_forms: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Write a config, roles, ledger and catalog for a batch test."""
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
    roles_path = tmp_path / "roles.json"
    roles_path.write_text(
        json.dumps({"proposers": ["p1", "p2"], "judge": "j"}),
        encoding="utf-8",
    )
    ledger = _ledger()
    if qualified:
        for release in ("r1", "r2", "r3"):
            GATE._replace_section(
                ledger,
                "qualifications",
                {"release": release, "language": "de", "qualified": True},
                key_fields=("release", "language"),
            )
    if paused:
        GATE.record_drift_excursion(
            ledger,
            {
                "release": "r1",
                "deployment": "p1",
                "language": "de",
                "score": 0.1,
                "threshold": 0.75,
                "calls": [],
                "total_cost_usd": 0.0,
                "latency_ms": 0.0,
            },
            since="2026-01-01",
        )
    ledger_path = _write_ledger(tmp_path / "ledger.json", ledger)
    catalog_path = _write_catalog(
        tmp_path / "de.po", entries, plural_forms=plural_forms
    )
    return config_path, ledger_path, catalog_path, roles_path


def _batch_args(
    config_path: Path,
    ledger_path: Path,
    catalog_path: Path,
    roles_path: Path,
    *extra: str,
) -> list[str]:
    """Build the common CLI arguments for a batch test."""
    return [
        "--config",
        str(config_path),
        "--roles",
        str(roles_path),
        "--ledger",
        str(ledger_path),
        "translate",
        "--language",
        "de",
        "--catalog",
        str(catalog_path),
        *extra,
    ]


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


def test_apply_decision_fills_and_replaces() -> None:
    """An approved decision writes the text and clears fuzzy."""
    ledger: dict[str, object] = _ledger()
    entry = _batch_entry("Delete", fuzzy=True)
    GATE._apply_decision(ledger, entry, _batch_decision("Delete"))
    assert entry.msgstr == "Löschen"
    assert "fuzzy" not in entry.flags
    assert len(LEDGER.approvals(ledger)) == 1

    entry.msgstr = "Alt"
    entry.flags.append("fuzzy")
    GATE._apply_decision(ledger, entry, _batch_decision("Delete", "Neu"))
    assert entry.msgstr == "Neu"
    assert "fuzzy" not in entry.flags
    assert len(LEDGER.approvals(ledger)) == 1


def test_apply_decision_rejects_missing_translation() -> None:
    """A decision without text leaves the catalog and ledger alone."""
    ledger: dict[str, object] = _ledger()
    entry = _batch_entry("Delete")
    with pytest.raises(GATE.GateError, match="no translation"):
        GATE._apply_decision(ledger, entry, _batch_decision("Delete", None))
    assert entry.msgstr == ""
    assert LEDGER.approvals(ledger) == []


def test_approve_decision_fills_empty_entry(tmp_path: Path) -> None:
    """The single-string approve path writes the translation too."""
    catalog_path = _write_catalog(tmp_path / "de.po", (_batch_entry("Delete"),))
    ledger_path = _write_ledger(tmp_path / "ledger.json", _ledger())
    GATE.approve_decision(
        catalog_path, ledger_path, "Delete", _batch_decision("Delete")
    )
    saved = polib.pofile(str(catalog_path)).find("Delete")
    assert saved is not None
    assert saved.msgstr == "Löschen"
    assert "fuzzy" not in saved.flags
    assert len(LEDGER.approvals(LEDGER.load_ledger(ledger_path))) == 1


def test_select_batch_entries_defaults_and_opt_in() -> None:
    """Empty entries are selected; fuzzy proposals and unsupported entries differ."""
    catalog = polib.POFile()
    for entry in (
        _batch_entry("Delete"),
        _batch_entry("Open", fuzzy=True),
        _batch_entry("Close", "Schließen", fuzzy=True),
        _batch_entry("Save", "Speichern"),
        _batch_entry("File", plural=True),
        _batch_entry("Cut", context="menu"),
    ):
        catalog.append(entry)

    selection = GATE._select_batch_entries(catalog, include_fuzzy=False, limit=None)
    assert [entry.msgid for entry in selection.selected] == ["Delete", "Open"]
    assert {entry.msgid for entry, _ in selection.unsupported} == {"Cut", "File"}
    assert selection.skipped == 2

    included = GATE._select_batch_entries(catalog, include_fuzzy=True, limit=None)
    assert [entry.msgid for entry in included.selected] == [
        "Close",
        "Delete",
        "Open",
    ]
    assert included.skipped == 1

    limited = GATE._select_batch_entries(catalog, include_fuzzy=False, limit=1)
    assert [entry.msgid for entry in limited.selected] == ["Delete"]


def test_translate_cli_approves_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A batch fills empty entries and reports skipped and unsupported ones."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(
            _batch_entry("Delete"),
            _batch_entry("Open", fuzzy=True),
            _batch_entry("Save", "Speichern"),
            _batch_entry("File", plural=True),
            _batch_entry("Cut", context="menu"),
        ),
    )
    client = Mock(wraps=FakeClient({"p1": "Löschen", "p2": "Entfernen"}))
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 0
    assert client.complete.call_count == 6
    catalog = polib.pofile(str(catalog_path))
    delete = catalog.find("Delete")
    opened = catalog.find("Open")
    assert delete is not None
    assert delete.msgstr == "Löschen"
    assert opened is not None
    assert opened.msgstr == "Löschen"
    assert "fuzzy" not in opened.flags
    ledger = LEDGER.load_ledger(ledger_path)
    assert len(LEDGER.approvals(ledger)) == 2
    assert len(LEDGER.section(ledger, "gate_runs")) == 2
    out = capsys.readouterr().out
    assert "approved 2" in out
    assert "abstained 0" in out
    assert "unsupported 2" in out
    assert "skipped 1" in out


def test_translate_cli_backtranslates_a_sentence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentence entry uses the proposer, judge and back-translation calls."""
    source = "This is a sufficiently long sentence for back translation."
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(_batch_entry(source),),
    )
    client = Mock(
        wraps=FakeClient(
            {"p1": "Löschen", "p2": "Entfernen"},
            backtranslation=source,
        )
    )
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 0
    assert client.complete.call_count == 4
    saved = polib.pofile(str(catalog_path)).find(source)
    assert saved is not None
    assert saved.msgstr == "Löschen"


def test_translate_cli_abstains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An abstention leaves the fuzzy entry unchanged."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(_batch_entry("Delete", fuzzy=True),),
    )
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen", "p2": "Entfernen"}, judge="ABSTAIN"),
    )
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 0
    saved = polib.pofile(str(catalog_path)).find("Delete")
    assert saved is not None
    assert saved.msgstr == ""
    assert "fuzzy" in saved.flags
    ledger = LEDGER.load_ledger(ledger_path)
    assert LEDGER.approvals(ledger) == []
    assert len(LEDGER.section(ledger, "gate_runs")) == 1
    assert "abstained 1" in capsys.readouterr().out


def test_translate_cli_reports_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The JSON report carries the applied translation and counts."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(_batch_entry("Delete"),),
    )
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    status = GATE.main(
        _batch_args(config_path, ledger_path, catalog_path, roles_path, "--json")
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected"] == 1
    assert payload["approved"][0]["msgid"] == "Delete"
    assert payload["approved"][0]["translation"] == "Löschen"
    assert payload["abstained"] == []
    assert payload["unsupported"] == []
    assert payload["remaining"] == 0
    assert payload["ready"] is True


def test_translate_cli_requires_qualification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unqualified release blocks the run and is reported by a dry run."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        qualified=False,
        entries=(_batch_entry("Delete"),),
    )
    client = Mock()
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    before_catalog = catalog_path.read_text(encoding="utf-8")
    before_ledger = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 1
    assert "not qualified" in capsys.readouterr().err
    client.complete.assert_not_called()
    assert catalog_path.read_text(encoding="utf-8") == before_catalog
    assert ledger_path.read_text(encoding="utf-8") == before_ledger

    status = GATE.main(
        _batch_args(
            config_path,
            ledger_path,
            catalog_path,
            roles_path,
            "--dry-run",
            "--json",
        )
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is False
    assert any("not qualified" in item for item in payload["blockers"])
    client.complete.assert_not_called()


def test_translate_cli_requires_unpaused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A paused language blocks the run and makes no call."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        paused=True,
        entries=(_batch_entry("Delete"),),
    )
    client = Mock()
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    before_catalog = catalog_path.read_text(encoding="utf-8")
    before_ledger = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 1
    assert "paused" in capsys.readouterr().err
    client.complete.assert_not_called()
    assert catalog_path.read_text(encoding="utf-8") == before_catalog
    assert ledger_path.read_text(encoding="utf-8") == before_ledger


def test_translate_cli_preflight_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An over-budget pre-estimate makes no call and writes nothing."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        costed=True,
        entries=(_batch_entry("Delete"), _batch_entry("Open")),
    )
    client = Mock()
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    before_catalog = catalog_path.read_text(encoding="utf-8")
    before_ledger = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        _batch_args(
            config_path,
            ledger_path,
            catalog_path,
            roles_path,
            "--max-cost",
            "0",
        )
    )
    assert status == 1
    assert "exceeds budget" in capsys.readouterr().err
    client.complete.assert_not_called()
    assert catalog_path.read_text(encoding="utf-8") == before_catalog
    assert ledger_path.read_text(encoding="utf-8") == before_ledger


def test_run_batch_stops_at_budget(tmp_path: Path) -> None:
    """A batch stops before the entry that would exceed the cap."""
    config_path, ledger_path, catalog_path, _roles_path = _batch_setup(
        tmp_path,
        costed=True,
        entries=(_batch_entry("Delete"), _batch_entry("Open")),
    )
    config = GATE.load_config(config_path)
    ledger = LEDGER.load_ledger(ledger_path)
    catalog = polib.pofile(str(catalog_path))
    high = GATE.estimate_gate(config, "de", ["Delete"]).high_cost_usd
    assert high is not None
    client = FakeClient({"p1": "Löschen", "p2": "Entfernen"}, cost_usd=0.001)
    approved, abstained, stopped, spent = GATE._run_batch(
        GATE.BatchRun(
            config=config,
            catalog=catalog,
            ledger=ledger,
            catalog_path=catalog_path,
            ledger_path=ledger_path,
            language="de",
            entries=tuple(catalog),
            client=client,
            max_cost=high + 0.001,
            tm_db=None,
        )
    )
    assert stopped == "budget"
    assert len(approved) == 1
    assert approved[0]["msgid"] == "Delete"
    assert abstained == []
    assert spent == pytest.approx(0.003)
    saved = polib.pofile(str(catalog_path))
    delete = saved.find("Delete")
    opened = saved.find("Open")
    assert delete is not None
    assert delete.msgstr == "Löschen"
    assert opened is not None
    assert opened.msgstr == ""
    ledger = LEDGER.load_ledger(ledger_path)
    assert len(LEDGER.approvals(ledger)) == 1
    assert len(LEDGER.section(ledger, "gate_runs")) == 1


def test_translate_cli_dry_run_lists_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run lists unsupported entries and writes nothing."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(
            _batch_entry("Delete"),
            _batch_entry("File", plural=True),
            _batch_entry("Cut", context="menu"),
        ),
    )
    client = Mock()
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    before_catalog = catalog_path.read_text(encoding="utf-8")
    before_ledger = ledger_path.read_text(encoding="utf-8")
    status = GATE.main(
        _batch_args(
            config_path,
            ledger_path,
            catalog_path,
            roles_path,
            "--dry-run",
            "--json",
        )
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected"] == 1
    assert {item["msgid"] for item in payload["unsupported"]} == {
        "Cut",
        "File",
    }
    assert payload["ready"] is True
    client.complete.assert_not_called()
    assert catalog_path.read_text(encoding="utf-8") == before_catalog
    assert ledger_path.read_text(encoding="utf-8") == before_ledger


def test_translate_cli_include_fuzzy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fuzzy proposal is skipped by default and replaced when requested."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        entries=(_batch_entry("Close", "Alt", fuzzy=True),),
    )
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    status = GATE.main(_batch_args(config_path, ledger_path, catalog_path, roles_path))
    assert status == 0
    saved = polib.pofile(str(catalog_path)).find("Close")
    assert saved is not None
    assert saved.msgstr == "Alt"

    status = GATE.main(
        _batch_args(
            config_path,
            ledger_path,
            catalog_path,
            roles_path,
            "--include-fuzzy",
        )
    )
    assert status == 0
    saved = polib.pofile(str(catalog_path)).find("Close")
    assert saved is not None
    assert saved.msgstr == "Löschen"
    assert "fuzzy" not in saved.flags
    assert len(LEDGER.approvals(LEDGER.load_ledger(ledger_path))) == 1


def test_catalog_plural_info_reads_the_header() -> None:
    """The declared count and rule are read from the catalog header."""
    catalog = polib.POFile()
    catalog.metadata = {"Plural-Forms": "nplurals=3; plural=(n > 1);"}
    assert GATE.catalog_plural_info(catalog) == (3, "(n > 1)")
    assert GATE.catalog_plural_info(polib.POFile()) == (None, "")


def test_select_batch_entries_handles_plural_forms() -> None:
    """Empty plural forms are selected, full ones skipped and mismatches rejected."""
    catalog = polib.POFile()
    catalog.metadata = {"Plural-Forms": "nplurals=2; plural=(n != 1);"}
    catalog.append(_batch_entry("Empty", plural=True))
    catalog.append(
        _batch_entry(
            "Full",
            plural=True,
            plural_forms={0: "Eins", 1: "Viele"},
        )
    )
    catalog.append(
        _batch_entry(
            "FuzzyFull",
            plural=True,
            plural_forms={0: "Eins", 1: "Viele"},
            fuzzy=True,
        )
    )
    catalog.append(
        _batch_entry(
            "Wrong",
            plural=True,
            plural_forms={0: "", 1: "", 2: ""},
        )
    )
    selection = GATE._select_batch_entries(catalog, include_fuzzy=False, limit=None)
    assert [entry.msgid for entry in selection.selected] == ["Empty"]
    assert {entry.msgid for entry, _ in selection.unsupported} == {"Wrong"}
    assert selection.skipped == 2

    included = GATE._select_batch_entries(catalog, include_fuzzy=True, limit=None)
    assert [entry.msgid for entry in included.selected] == ["Empty", "FuzzyFull"]
    assert included.skipped == 1


def test_select_batch_entries_accepts_three_forms() -> None:
    """A three-form catalog selects an entry with three forms."""
    catalog = polib.POFile()
    catalog.metadata = {"Plural-Forms": "nplurals=3; plural=(n > 1);"}
    catalog.append(
        _batch_entry(
            "File",
            plural=True,
            plural_forms={0: "", 1: "", 2: ""},
        )
    )
    selection = GATE._select_batch_entries(catalog, include_fuzzy=False, limit=None)
    assert [entry.msgid for entry in selection.selected] == ["File"]
    assert selection.unsupported == ()


def test_select_batch_entries_reports_a_plural_without_a_header() -> None:
    """A plural entry without nplurals is unsupported."""
    catalog = polib.POFile()
    catalog.append(_batch_entry("File", plural=True))
    selection = GATE._select_batch_entries(catalog, include_fuzzy=False, limit=None)
    assert selection.selected == ()
    assert "does not declare nplurals" in selection.unsupported[0][1]


def test_prompt_for_plural_has_both_sources_and_rule() -> None:
    """The plural prompt carries the count, rule and both source forms."""
    source = GATE.PluralSource("One", "Many", 2, "n != 1")
    prompt = GATE.prompt_for_plural("de", source)
    assert "2 plural forms" in prompt
    assert "Plural rule: n != 1" in prompt
    assert "Source (singular): One" in prompt
    assert "Source (plural): Many" in prompt


@pytest.mark.parametrize("nplurals", [2, 3])
def test_parse_plural_response_accepts_a_complete_set(nplurals: int) -> None:
    """A complete indexed response parses into every form."""
    text = "\n".join(f"{index}: Form {index}" for index in range(nplurals))
    assert GATE.parse_plural_response(text, nplurals) == {
        index: f"Form {index}" for index in range(nplurals)
    }


@pytest.mark.parametrize(
    "text",
    [
        "0: Eins",
        "0: Eins\n2: Zwei",
        "0: Eins\n0: Zwei",
        "Here are the forms:\n0: Eins\n1: Zwei",
        "0: \n1: Zwei",
    ],
)
def test_parse_plural_response_rejects_bad_answers(text: str) -> None:
    """A wrong count, missing index, duplicate or preamble is unusable."""
    assert GATE.parse_plural_response(text, 2) is None


def test_deterministic_plural_checks_cover_every_form() -> None:
    """A defect in any form fails the whole set."""
    source = GATE.PluralSource("One: %(name)s", "Many: %(name)s", 2, "n != 1")
    assert (
        GATE.deterministic_plural_checks(
            source,
            {0: "Eins: %(name)s", 1: "Viele: %(name)s"},
        )
        == []
    )
    assert "form 1: placeholders changed" in GATE.deterministic_plural_checks(
        source, {0: "Eins: %(name)s", 1: "Viele: Text"}
    )
    assert "form 1: empty translation" in GATE.deterministic_plural_checks(
        source, {0: "Eins", 1: ""}
    )
    assert GATE.deterministic_plural_checks(
        source, {0: "Eins: %(name)s\n", 1: "Viele: %(name)s"}
    ) == ["form 0: trailing newline changed"]
    assert GATE.deterministic_plural_checks(source, {0: "Eins"}) == [
        "wrong number of forms"
    ]
    assert GATE.deterministic_plural_checks(source, None) == [
        "wrong number of forms or unparseable response"
    ]


def test_estimate_gate_scales_for_plural_forms(tmp_path: Path) -> None:
    """A plural form set estimates more output than the singular source."""
    config_path, _ledger_path, _catalog_path, _roles_path = _batch_setup(
        tmp_path, costed=True
    )
    config = GATE.load_config(config_path)
    singular = GATE.estimate_gate(config, "de", ["One"]).high_cost_usd
    plural = GATE.estimate_gate(
        config,
        "de",
        [GATE.PluralSource("One", "Many", 2, "n != 1")],
    ).high_cost_usd
    assert singular is not None
    assert plural is not None
    assert plural > singular


def test_run_plural_gate_judges_complete_sets(tmp_path: Path) -> None:
    """The judge sees complete form sets and its chosen set is approved."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = GATE.PluralSource("One file", "Many files", 2, "n != 1")
    client = Mock(
        wraps=FakeClient(
            plural_answers={
                "p1": "0: Eine Datei\n1: Viele Dateien",
                "p2": "0: Ein File\n1: Viele Files",
            },
            judge="B",
        )
    )
    decision = GATE.run_plural_gate(source, "de", config, client)
    assert decision.approved is True
    assert decision.translation is None
    assert decision.forms == {0: "Ein File", 1: "Viele Files"}
    assert decision.record is not None
    assert set(decision.record["msgstr_plural"]) == {"0", "1"}
    assert client.complete.call_count == 3
    judge_prompt = client.complete.call_args_list[-1].args[1]
    assert "0: Eine Datei" in judge_prompt
    assert "0: Ein File" in judge_prompt


def test_run_plural_gate_identical_sets_are_a_tie(tmp_path: Path) -> None:
    """Identical form tuples skip the judge."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = GATE.PluralSource("One file", "Many files", 2, "n != 1")
    answer = "0: Eine Datei\n1: Viele Dateien"
    client = Mock(wraps=FakeClient(plural_answers={"p1": answer, "p2": answer}))
    decision = GATE.run_plural_gate(source, "de", config, client)
    assert decision.approved is True
    assert decision.evidence["judge"]["tie"] is True
    assert client.complete.call_count == 2


def test_run_plural_gate_backtranslates_each_sentence_form(
    tmp_path: Path,
) -> None:
    """Every sentence form is back-translated and recorded."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = GATE.PluralSource(
        "This is a long singular sentence for the test.",
        "These are long plural sentences for the test.",
        2,
        "n != 1",
    )
    answer = "0: Dies ist ein langer Satz.\n1: Dies sind lange Sätze."
    client = Mock(
        wraps=FakeClient(
            plural_answers={"p1": answer, "p2": answer},
            backtranslations=[source.msgid, source.msgid_plural],
        )
    )
    decision = GATE.run_plural_gate(source, "de", config, client)
    assert decision.approved is True
    assert decision.evidence["backtranslation"] == {"0": True, "1": True}
    assert client.complete.call_count == 4


def test_run_plural_gate_rejects_a_bad_second_form(tmp_path: Path) -> None:
    """A meaning change in form 1 blocks the whole set."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = GATE.PluralSource(
        "This is a long singular sentence for the test.",
        "These are long plural sentences for the test.",
        2,
        "n != 1",
    )
    answer = "0: Dies ist ein langer Satz.\n1: Dies sind lange Sätze."
    client = Mock(
        wraps=FakeClient(
            plural_answers={"p1": answer, "p2": answer},
            backtranslations=[source.msgid, "Something unrelated."],
        )
    )
    decision = GATE.run_plural_gate(source, "de", config, client)
    assert decision.approved is False
    assert "back-translation" in decision.reason
    assert decision.evidence["backtranslation"]["1"] is False


def test_run_plural_gate_rejects_a_wrong_form_count(tmp_path: Path) -> None:
    """A proposal with the wrong number of forms cannot be approved."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = GATE.PluralSource("One file", "Many files", 2, "n != 1")
    client = Mock(wraps=FakeClient(plural_answers={"p1": "0: only", "p2": "0: only"}))
    decision = GATE.run_plural_gate(source, "de", config, client)
    assert decision.approved is False
    assert "deterministic check" in decision.reason


def test_apply_plural_decision_writes_every_form() -> None:
    """Applying a plural decision fills msgstr_plural and clears fuzzy."""
    entry = _batch_entry("File", plural=True, fuzzy=True)
    ledger = _ledger()
    source = GATE.PluralSource("File", "Files", 2, "n != 1")
    forms = {0: "Datei", 1: "Dateien"}
    record = LEDGER.make_record(
        "de",
        GATE._entry_for_plural(source, forms),
        "machine-strong",
        context=LEDGER.ApprovalContext(
            approval_date="2026-01-01",
            model_release="r1",
            deployment="p1",
        ),
    )
    decision = GATE.GateDecision(
        approved=True,
        reason="every check and the judge agree",
        forms=forms,
        record=record,
    )
    GATE._apply_decision(ledger, entry, decision)
    assert entry.msgstr == ""
    assert entry.msgstr_plural == {0: "Datei", 1: "Dateien"}
    assert "fuzzy" not in entry.flags
    assert len(LEDGER.approvals(ledger)) == 1

    with pytest.raises(GATE.GateError, match="do not match"):
        GATE._apply_decision(
            _ledger(),
            _batch_entry("File", plural=True),
            GATE.GateDecision(
                approved=True,
                reason="every check and the judge agree",
                forms={0: "Datei"},
                record=record,
            ),
        )


def test_plural_apply_compiles_every_form(tmp_path: Path) -> None:
    """A catalog round trip through compile_mo renders both forms."""
    compile_module = _load_compile_mo()
    catalog_path = tmp_path / "de.po"
    catalog = polib.POFile()
    catalog.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    }
    entry = _batch_entry("File", plural=True)
    catalog.append(entry)
    catalog.save(str(catalog_path))
    source = GATE.PluralSource("File", "Files", 2, "n != 1")
    forms = {0: "Datei", 1: "Dateien"}
    record = LEDGER.make_record(
        "de",
        GATE._entry_for_plural(source, forms),
        "machine-strong",
        context=LEDGER.ApprovalContext(
            approval_date="2026-01-01",
            model_release="r1",
            deployment="p1",
        ),
    )
    GATE._apply_decision(
        _ledger(),
        entry,
        GATE.GateDecision(
            approved=True,
            reason="every check and the judge agree",
            forms=forms,
            record=record,
        ),
    )
    catalog.save(str(catalog_path))
    out = tmp_path / "out"
    lang, stats = compile_module.compile_catalog(
        catalog_path, None, set(), out, "scantpaper"
    )
    assert lang == "de"
    assert stats is None
    translation = gettext.translation(
        "scantpaper", localedir=str(out), languages=["de"]
    )
    assert translation.ngettext("File", "Files", 1) == "Datei"
    assert translation.ngettext("File", "Files", 2) == "Dateien"


@pytest.mark.parametrize("nplurals", [2, 3])
def test_translate_cli_applies_plural_forms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nplurals: int,
) -> None:
    """A two-form and a three-form entry are selected, gated and applied."""
    rule = (
        "nplurals=2; plural=(n != 1);"
        if nplurals == 2
        else "nplurals=3; plural=(n > 1);"
    )
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        plural_forms=rule,
        entries=(
            _batch_entry(
                "File",
                plural=True,
                plural_forms=dict.fromkeys(range(nplurals), ""),
            ),
        ),
    )
    answer = "\n".join(f"{index}: Form {index}" for index in range(nplurals))
    client = Mock(wraps=FakeClient(plural_answers={"p1": answer, "p2": answer}))
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        _batch_args(config_path, ledger_path, catalog_path, roles_path, "--json")
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["approved"][0]["forms"] == {
        str(index): f"Form {index}" for index in range(nplurals)
    }
    saved = polib.pofile(str(catalog_path)).find("File")
    assert saved is not None
    assert saved.msgstr == ""
    assert saved.msgstr_plural == {index: f"Form {index}" for index in range(nplurals)}
    assert payload["remaining"] == 0


def test_translate_cli_plural_abstention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A wrong form count abstains and leaves the plural forms empty."""
    config_path, ledger_path, catalog_path, roles_path = _batch_setup(
        tmp_path,
        plural_forms="nplurals=2; plural=(n != 1);",
        entries=(_batch_entry("File", plural=True),),
    )
    client = Mock(wraps=FakeClient(plural_answers={"p1": "0: only", "p2": "0: only"}))
    monkeypatch.setattr(GATE, "OpenAICompatibleClient", lambda: client)
    status = GATE.main(
        _batch_args(config_path, ledger_path, catalog_path, roles_path, "--json")
    )
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["approved"] == []
    assert payload["abstained"][0]["reason"] == (
        "every proposal failed a deterministic check"
    )
    assert payload["remaining"] == 1
    saved = polib.pofile(str(catalog_path)).find("File")
    assert saved is not None
    assert saved.msgstr_plural == {0: "", 1: ""}


def _split_ledger(tmp_path: Path, languages: tuple[str, ...] = ("de", "en_GB")) -> Path:
    """Write a split ledger with one historical approval per language."""
    records = []
    for language in languages:
        entry = polib.POEntry(msgid=f"{language}-old", msgstr="old")
        records.append(
            LEDGER.make_record(
                language,
                entry,
                "human-historical",
                context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
            )
        )
    data: dict[str, object] = {
        "version": 1,
        "snapshot": "a" * 40,
        "approvals": records,
    }
    directory = tmp_path / "approvals"
    LEDGER.write_ledger(data, directory)
    return directory


def _split_config(tmp_path: Path) -> Path:
    """Write a gate config for split-ledger tests."""
    return _write_config(tmp_path, _config_data())


def test_gate_with_split_ledger_writes_one_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gate run writes only its language file and the evidence sidecar."""
    directory = _split_ledger(tmp_path)
    config_path = _split_config(tmp_path)
    sidecar = tmp_path / "evidence.ndjson"
    before_en = (directory / "en_GB.json").read_text(encoding="utf-8")
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(directory),
            "--evidence",
            str(sidecar),
            "gate",
            "--language",
            "de",
            "--msgid",
            "Delete",
        ]
    )
    assert status == 0
    de_data = LEDGER.load_language_ledger(directory, "de")
    runs = LEDGER.section(de_data, "gate_runs")
    assert len(runs) == 1
    assert "calls" not in runs[0]
    assert runs[0]["evidence_sha256"]
    assert sidecar.exists()
    assert (directory / "en_GB.json").read_text(encoding="utf-8") == before_en


def test_costs_resolves_compact_gate_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The cost report resolves calls from the sidecar."""
    directory = _split_ledger(tmp_path)
    config_path = _split_config(tmp_path)
    sidecar = tmp_path / "evidence.ndjson"
    monkeypatch.setattr(
        GATE,
        "OpenAICompatibleClient",
        lambda: FakeClient({"p1": "Löschen", "p2": "Löschen"}),
    )
    assert (
        GATE.main(
            [
                "--config",
                str(config_path),
                "--ledger",
                str(directory),
                "--evidence",
                str(sidecar),
                "gate",
                "--language",
                "de",
                "--msgid",
                "Delete",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        GATE.main(
            [
                "--ledger",
                str(directory),
                "--evidence",
                str(sidecar),
                "costs",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["languages"]["de"]["p1"]["calls"] == 1


def test_approve_with_split_ledger_writes_one_language(tmp_path: Path) -> None:
    """Approving a decision writes only the decision's language file."""
    directory = _split_ledger(tmp_path)
    config_path = _split_config(tmp_path)
    catalog_path = _write_catalog(tmp_path / "de.po", (_batch_entry("Delete"),))
    before_en = (directory / "en_GB.json").read_text(encoding="utf-8")
    decision = _batch_decision("Delete")
    decision_path = tmp_path / "decision.json"
    decision_path.write_text(
        json.dumps(
            {
                "approved": True,
                "reason": decision.reason,
                "translation": decision.translation,
                "record": decision.record,
            }
        ),
        encoding="utf-8",
    )
    status = GATE.main(
        [
            "--config",
            str(config_path),
            "--ledger",
            str(directory),
            "approve",
            "--catalog",
            str(catalog_path),
            "--msgid",
            "Delete",
            "--decision",
            str(decision_path),
        ]
    )
    assert status == 0
    saved = polib.pofile(str(catalog_path)).find("Delete")
    assert saved is not None
    assert saved.msgstr == "Löschen"
    assert (directory / "en_GB.json").read_text(encoding="utf-8") == before_en
    de_data = LEDGER.load_language_ledger(directory, "de")
    assert len(LEDGER.approvals(de_data)) == 2


def test_revoke_with_split_ledger_writes_global_only(tmp_path: Path) -> None:
    """A revocation updates global.json without rewriting language files."""
    directory = _split_ledger(tmp_path)
    before_de = (directory / "de.json").read_text(encoding="utf-8")
    before_en = (directory / "en_GB.json").read_text(encoding="utf-8")
    status = GATE.main(
        [
            "--ledger",
            str(directory),
            "revoke",
            "--scope",
            "language",
            "--value",
            "de",
        ]
    )
    assert status == 0
    global_data = LEDGER.load_global_ledger(directory)
    assert LEDGER.section(global_data, "revocations")[0]["value"] == "de"
    assert (directory / "de.json").read_text(encoding="utf-8") == before_de
    assert (directory / "en_GB.json").read_text(encoding="utf-8") == before_en


def test_qualify_with_split_ledger_compacts_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A qualification writes only its language file and compacts calls."""
    de_entry = polib.POEntry(msgid="Delete", msgstr="Löschen")
    records = [
        LEDGER.make_record(
            "de",
            de_entry,
            "human-historical",
            context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
        ),
        LEDGER.make_record(
            "en_GB",
            polib.POEntry(msgid="old", msgstr="old"),
            "human-historical",
            context=LEDGER.ApprovalContext(approval_date="2026-02-28"),
        ),
    ]
    directory = tmp_path / "approvals"
    LEDGER.write_ledger(
        {"version": 1, "snapshot": "a" * 40, "approvals": records},
        directory,
    )
    config_path = _split_config(tmp_path)
    catalog_path = _write_catalog(
        tmp_path / "de.po", (_batch_entry("Delete", "Löschen"),)
    )
    sidecar = tmp_path / "evidence.ndjson"
    before_en = (directory / "en_GB.json").read_text(encoding="utf-8")
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
            str(directory),
            "--evidence",
            str(sidecar),
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
    de_data = LEDGER.load_language_ledger(directory, "de")
    qualifications = LEDGER.section(de_data, "qualifications")
    assert len(qualifications) == 1
    assert "calls" not in qualifications[0]
    assert qualifications[0]["evidence_sha256"]
    assert sidecar.exists()
    assert (directory / "en_GB.json").read_text(encoding="utf-8") == before_en


def test_drift_with_split_ledger_compacts_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A paused drift probe writes only its language file and sidecar."""
    directory = _split_ledger(tmp_path)
    config_path = _split_config(tmp_path)
    probe = tmp_path / "de.json"
    probe.write_text(
        json.dumps(
            {
                "language": "de",
                "version": 1,
                "items": [{"msgid": "Delete", "msgstr": "Löschen"}],
            }
        ),
        encoding="utf-8",
    )
    sidecar = tmp_path / "evidence.ndjson"
    before_en = (directory / "en_GB.json").read_text(encoding="utf-8")
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
            str(directory),
            "--evidence",
            str(sidecar),
            "drift",
            "--deployment",
            "p1",
            "--language",
            "de",
            "--probe",
            str(probe),
        ]
    )
    assert status == 0
    de_data = LEDGER.load_language_ledger(directory, "de")
    excursions = LEDGER.section(de_data, "drift_excursions")
    assert len(excursions) == 1
    assert "calls" not in excursions[0]
    assert excursions[0]["evidence_sha256"]
    assert sidecar.exists()
    assert (directory / "en_GB.json").read_text(encoding="utf-8") == before_en


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


def test_deterministic_checks_preserve_line_structure() -> None:
    """Leading and trailing newlines must survive translation."""
    assert GATE.deterministic_checks("Line\n", "Zeile\n") == []
    assert "trailing newline changed" in GATE.deterministic_checks("Line\n", "Zeile")
    assert "trailing newline changed" in GATE.deterministic_checks(
        "Line\n\n", "Zeile\n"
    )
    assert "leading newline changed" in GATE.deterministic_checks("Line", "\nZeile")


def test_gate_abstains_when_a_newline_is_dropped(tmp_path: Path) -> None:
    """A proposal that would fail msgfmt on a newline cannot be approved."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    client = FakeClient(
        {
            "p1": "Die folgenden Werkzeuge wurden nicht gefunden:",
            "p2": "Die folgenden Werkzeuge wurden nicht gefunden:",
        }
    )
    decision = GATE.run_gate(
        "The following tools were not found:\n", "de", config, client
    )
    assert decision.approved is False
    assert decision.reason == "every proposal failed a deterministic check"
    checks = cast("dict[str, object]", decision.evidence["checks"])
    assert checks["p1"] == ["trailing newline changed"]
    assert checks["p2"] == ["trailing newline changed"]


def test_gate_abstains_when_backtranslation_changes_meaning(
    tmp_path: Path,
) -> None:
    """A sentence tie still abstains when the back-translation differs."""
    config = GATE.load_config(_write_config(tmp_path, _config_data()))
    source = "This is a sufficiently long sentence for a back translation."
    client = Mock(
        wraps=FakeClient(
            {
                "p1": "Ein ausreichend langer Satz.",
                "p2": "Ein ausreichend langer Satz.",
            },
            backtranslation="Something completely unrelated.",
        )
    )
    decision = GATE.run_gate(source, "de", config, client)
    assert decision.approved is False
    assert "back-translation" in decision.reason
    assert client.complete.call_count == 3
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["tie"] is True


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
    judge = cast("dict[str, object]", decision.evidence["judge"])
    assert judge["tie"] is True


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

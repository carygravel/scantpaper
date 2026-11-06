"""Read, validate and apply the translation approval ledger.

The ledger is the source of truth for whether a translated entry may ship.
It is deliberately separate from the ``.po`` files so that an approval survives
a merge and a catalog edit never silently keeps an old approval.

An approval is keyed by ``(language, msgctxt, msgid, msgid_plural)`` and binds
the exact translation text through ``translation_sha256``. Editing the source
or the translation therefore invalidates the approval. The digest covers the
canonical JSON serialization of the singular ``msgstr`` or of every plural
form, including whitespace, so a cosmetic edit is also a new approval.

Schema overview::

    {
      "version": 1,
      "snapshot": "<pre-2026 commit hash>",
      "approvals": [
        {
          "language": "de",
          "msgctxt": null,
          "msgid": "Delete",
          "msgid_plural": null,
          "msgstr": "Löschen",
          "translation_sha256": "<64 hex characters>",
          "provenance_class": "human-historical",
          "evidence": {},
          "model_release": null,
          "deployment": null,
          "approval_date": "2026-02-28"
        }
      ]
    }
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from translation_policy import (
    MACHINE_PROVENANCE_CLASSES,
    PROVENANCE_CLASSES,
    validate_provenance_class,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import polib

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = REPO_ROOT / "po" / "translation-approvals.json"

LEDGER_VERSION = 1
DIGEST_HEX_LENGTH = 64
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class LedgerError(ValueError):
    """A ledger that cannot be trusted as an approval source."""


SECTION_NAMES = (
    "qualifications",
    "conformances",
    "revocations",
    "false_positives",
    "drift_excursions",
    "audit_samples",
    "gate_runs",
)


@dataclass(frozen=True)
class ApprovalContext:
    """The audit fields shared by every approval record."""

    approval_date: str
    evidence: dict[str, object] | None = None
    model_release: str | None = None
    deployment: str | None = None


class ApprovalRecord(TypedDict, total=False):
    """One approved translation, as stored in the ledger."""

    language: str
    msgctxt: str | None
    msgid: str
    msgid_plural: str | None
    msgstr: str
    msgstr_plural: dict[str, str]
    translation_sha256: str
    provenance_class: str
    evidence: dict[str, object]
    model_release: str | None
    deployment: str | None
    approval_date: str


def canonical_translation(
    msgstr: str,
    msgstr_plural: Mapping[str, str] | None = None,
) -> str:
    """Return the canonical text a translation digest is computed over.

    A type marker keeps a singular translation from colliding with a plural
    form that happens to contain the same text. Plural keys are sorted
    numerically first so the same forms always serialize identically.
    """
    if msgstr_plural is None:
        payload: dict[str, object] = {"singular": msgstr}
    else:
        ordered = dict(sorted(msgstr_plural.items(), key=lambda item: int(item[0])))
        payload = {"plural": ordered}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def translation_digest(
    msgstr: str,
    msgstr_plural: Mapping[str, str] | None = None,
) -> str:
    """Return the SHA-256 digest of a translation."""
    canonical = canonical_translation(msgstr, msgstr_plural)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def entry_translation(entry: polib.POEntry) -> tuple[str, dict[str, str] | None]:
    """Return the singular or plural translation stored on a catalog entry."""
    if entry.msgid_plural:
        forms = cast("dict[str, str]", entry.msgstr_plural or {})
        return entry.msgstr, dict(forms)
    return entry.msgstr, None


def entry_digest(entry: polib.POEntry) -> str:
    """Return the digest of a catalog entry's translation."""
    msgstr, msgstr_plural = entry_translation(entry)
    return translation_digest(msgstr, msgstr_plural)


def approval_key(
    language: str,
    msgctxt: str | None,
    msgid: str,
    msgid_plural: str | None,
) -> tuple[str, str, str, str]:
    """Return the content key that identifies one approval."""
    return (language, msgctxt or "", msgid, msgid_plural or "")


def make_record(
    language: str,
    entry: polib.POEntry,
    provenance_class: str,
    *,
    context: ApprovalContext,
) -> ApprovalRecord:
    """Build one approval record for a catalog entry."""
    validate_provenance_class(provenance_class)
    msgstr, msgstr_plural = entry_translation(entry)
    record: ApprovalRecord = {
        "language": language,
        "msgctxt": entry.msgctxt or None,
        "msgid": entry.msgid,
        "msgid_plural": entry.msgid_plural or None,
        "translation_sha256": translation_digest(msgstr, msgstr_plural),
        "provenance_class": provenance_class,
        "evidence": dict(context.evidence or {}),
        "model_release": context.model_release,
        "deployment": context.deployment,
        "approval_date": context.approval_date,
    }
    if msgstr_plural is None:
        record["msgstr"] = msgstr
    else:
        record["msgstr_plural"] = msgstr_plural
    return record


def write_ledger(data: Mapping[str, object], path: Path = LEDGER_PATH) -> None:
    """Validate and write the ledger deterministically."""
    validated = validate_ledger(data, source=str(path))
    text = json.dumps(validated, ensure_ascii=False, indent=2)
    path.write_text(f"{text}\n", encoding="utf-8")


def entry_key(
    language: str,
    entry: polib.POEntry,
) -> tuple[str, str, str, str]:
    """Return the content key that identifies one catalog entry."""
    return approval_key(language, entry.msgctxt, entry.msgid, entry.msgid_plural)


def record_key(record: Mapping[str, object]) -> tuple[str, str, str, str]:
    """Return the content key of a ledger record."""
    return approval_key(
        _string(record, "language"),
        _optional_string(record, "msgctxt"),
        _string(record, "msgid"),
        _optional_string(record, "msgid_plural"),
    )


def _string(record: Mapping[str, object], field: str) -> str:
    """Return a required string field, raising when it is absent."""
    value = record.get(field)
    if not isinstance(value, str) or not value:
        msg = f"approval is missing a non-empty {field!r}"
        raise LedgerError(msg)
    return value


def _optional_string(record: Mapping[str, object], field: str) -> str:
    """Return an optional string field, treating null as absent."""
    value = record.get(field)
    if value is None:
        return ""
    if not isinstance(value, str):
        msg = f"approval field {field!r} must be a string or null"
        raise LedgerError(msg)
    return value


def _record_translation(
    record: Mapping[str, object],
) -> tuple[str, dict[str, str] | None]:
    """Return the stored translation, validating its shape."""
    plural = record.get("msgstr_plural")
    if plural is not None:
        if not isinstance(plural, dict):
            msg = "approval field 'msgstr_plural' must be an object"
            raise LedgerError(msg)
        forms: dict[str, str] = {}
        for key, value in plural.items():
            if not isinstance(key, str) or not isinstance(value, str):
                msg = "approval field 'msgstr_plural' must map strings to strings"
                raise LedgerError(msg)
            forms[key] = value
        return "", forms

    msgstr = record.get("msgstr")
    if not isinstance(msgstr, str):
        msg = "approval is missing a string 'msgstr'"
        raise LedgerError(msg)
    return msgstr, None


def _validate_record_identity(record: dict[str, object], where: str) -> str:
    """Validate the fields that identify an approval and return its class."""
    _string(record, "language")
    _string(record, "msgid")
    _optional_string(record, "msgctxt")
    _optional_string(record, "msgid_plural")

    provenance_class = record.get("provenance_class")
    if not isinstance(provenance_class, str):
        msg = f"{where} has no provenance_class"
        raise LedgerError(msg)
    try:
        validate_provenance_class(provenance_class)
    except ValueError as error:
        raise LedgerError(str(error)) from error
    return provenance_class


def _validate_record_digest(record: dict[str, object], where: str) -> None:
    """Validate the digest and make sure it covers the stored translation."""
    digest = record.get("translation_sha256")
    if digest is None:
        msg = f"{where} has no translation_sha256"
        raise LedgerError(msg)
    if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
        msg = f"{where} has a malformed translation_sha256"
        raise LedgerError(msg)

    msgstr, msgstr_plural = _record_translation(record)
    if translation_digest(msgstr, msgstr_plural) != digest:
        msg = f"{where} translation_sha256 does not match its stored translation"
        raise LedgerError(msg)


def _validate_record_metadata(
    record: dict[str, object],
    where: str,
    provenance_class: str,
) -> None:
    """Validate the audit fields and the machine-origin fields."""
    approval_date = record.get("approval_date")
    if not isinstance(approval_date, str) or not approval_date:
        msg = f"{where} is missing a non-empty approval_date"
        raise LedgerError(msg)

    evidence = record.get("evidence")
    if evidence is not None and not isinstance(evidence, dict):
        msg = f"{where} field 'evidence' must be an object"
        raise LedgerError(msg)

    if provenance_class in MACHINE_PROVENANCE_CLASSES:
        for field in ("model_release", "deployment"):
            value = record.get(field)
            if not isinstance(value, str) or not value:
                msg = f"{where} is machine-origin but has no {field}"
                raise LedgerError(msg)


def validate_record(record: object, *, index: int) -> dict[str, object]:
    """Validate one approval record, raising on the first problem.

    The stored translation must match ``translation_sha256``; this catches a
    hand-edited ledger before it is mistaken for an approval.
    """
    where = f"approval {index}"
    if not isinstance(record, dict):
        msg = f"{where} is not an object"
        raise LedgerError(msg)

    provenance_class = _validate_record_identity(record, where)
    _validate_record_digest(record, where)
    _validate_record_metadata(record, where, provenance_class)

    return cast("dict[str, object]", record)


def validate_ledger(data: object, *, source: str = "ledger") -> dict[str, object]:
    """Validate the ledger document and return it as a typed mapping."""
    if not isinstance(data, dict):
        msg = f"{source} is not a JSON object"
        raise LedgerError(msg)

    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        msg = f"{source} has no integer 'version'"
        raise LedgerError(msg)
    if version != LEDGER_VERSION:
        msg = f"{source} has unsupported version {version}"
        raise LedgerError(msg)

    snapshot = data.get("snapshot")
    if not isinstance(snapshot, str) or not snapshot:
        msg = f"{source} has no non-empty 'snapshot'"
        raise LedgerError(msg)

    approvals_list = data.get("approvals")
    if not isinstance(approvals_list, list):
        msg = f"{source} has no 'approvals' list"
        raise LedgerError(msg)

    for section_name in SECTION_NAMES:
        if section_name in data and not isinstance(data[section_name], list):
            msg = f"{source} section {section_name!r} must be a list"
            raise LedgerError(msg)

    seen: set[tuple[str, str, str, str]] = set()
    for index, record in enumerate(approvals_list):
        validated = validate_record(record, index=index)
        key = record_key(validated)
        if key in seen:
            msg = f"{source} has duplicate approval for {key!r}"
            raise LedgerError(msg)
        seen.add(key)

    return cast("dict[str, object]", data)


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, object]:
    """Load and validate the ledger at ``path``."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        msg = f"cannot read ledger {path}: {error}"
        raise LedgerError(msg) from error

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        msg = f"cannot parse ledger {path}: {error}"
        raise LedgerError(msg) from error

    return validate_ledger(data, source=str(path))


def approvals(data: Mapping[str, object]) -> list[ApprovalRecord]:
    """Return the approval records, narrowed to the record type."""
    records = data.get("approvals", [])
    if not isinstance(records, list):
        msg = "ledger 'approvals' must be a list"
        raise LedgerError(msg)
    return [cast("ApprovalRecord", record) for record in records]


def section(data: Mapping[str, object], name: str) -> list[dict[str, object]]:
    """Return one optional ledger section, or an empty list when absent."""
    value = data.get(name, [])
    if not isinstance(value, list):
        msg = f"ledger section {name!r} must be a list"
        raise LedgerError(msg)
    return [cast("dict[str, object]", item) for item in value]


def add_section_record(
    data: dict[str, object],
    name: str,
    record: Mapping[str, object],
) -> None:
    """Append a record to an optional ledger section."""
    value = data.setdefault(name, [])
    if not isinstance(value, list):
        msg = f"ledger section {name!r} must be a list"
        raise LedgerError(msg)
    value.append(dict(record))


def is_revoked(
    record: Mapping[str, object],
    revocations: Iterable[Mapping[str, object]],
) -> bool:
    """Return whether a machine approval is covered by a revocation."""
    if record.get("provenance_class") not in MACHINE_PROVENANCE_CLASSES:
        return False
    for revocation in revocations:
        scope = revocation.get("scope")
        value = revocation.get("value")
        if not isinstance(scope, str) or not isinstance(value, str):
            continue
        field = {
            "language": "language",
            "deployment": "deployment",
            "release": "model_release",
        }.get(scope)
        if field is None:
            continue
        if record.get(field) == value:
            return True
    return False


def approval_index(
    data: Mapping[str, object],
    *,
    include_revoked: bool = False,
) -> dict[tuple[str, str, str, str], ApprovalRecord]:
    """Index the approvals by content key for catalog lookups."""
    revocations = [] if include_revoked else section(data, "revocations")
    return {
        record_key(record): record
        for record in approvals(data)
        if include_revoked or not is_revoked(record, revocations)
    }


def approval_for_entry(
    data: Mapping[str, object],
    language: str,
    entry: polib.POEntry,
) -> ApprovalRecord | None:
    """Return the valid approval for ``entry``, or None.

    A record approves an entry only when the language, context, msgid and
    plural msgid match and the recorded digest equals the entry's current
    translation digest.
    """
    record = approval_index(data).get(entry_key(language, entry))
    if record is None:
        return None
    digest = record.get("translation_sha256")
    if digest != entry_digest(entry):
        return None
    return record


def active_entries(po: polib.POFile) -> list[polib.POEntry]:
    """Return the non-obsolete entries that carry a msgid."""
    return [entry for entry in po if not entry.obsolete and entry.msgid]


def validate_against_catalog(
    data: Mapping[str, object],
    language: str,
    po: polib.POFile,
) -> list[str]:
    """Report every approval that cannot bind to an entry in ``po``.

    A mismatched language, context, msgid or translation digest is reported;
    such a record never approves the entry. Records for other languages are
    ignored because one ledger covers every catalog.
    """
    by_key = {entry_key(language, entry): entry for entry in active_entries(po)}
    problems: list[str] = []
    for record in approvals(data):
        key = record_key(record)
        if key[0] != language:
            continue
        entry = by_key.get(key)
        if entry is None:
            problems.append(
                f"{language}: approval for {key[2]!r} does not match an active entry"
            )
            continue
        if record.get("translation_sha256") != entry_digest(entry):
            problems.append(
                f"{language}: approval for {key[2]!r} has a stale translation digest"
            )
    return problems


def validate_catalogs(
    data: Mapping[str, object],
    catalogs: Iterable[tuple[str, polib.POFile]],
) -> list[str]:
    """Report unbound approvals across several ``(language, catalog)`` pairs."""
    problems: list[str] = []
    for language, po in catalogs:
        problems.extend(validate_against_catalog(data, language, po))
    return problems


def provenance_classes() -> tuple[str, ...]:
    """Expose the accepted classes for callers that build a report."""
    return PROVENANCE_CLASSES

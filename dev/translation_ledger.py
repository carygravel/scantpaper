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
APPROVALS_DIR = REPO_ROOT / "po" / "approvals"
LEGACY_LEDGER_PATH = REPO_ROOT / "po" / "translation-approvals.json"
LEDGER_PATH = APPROVALS_DIR
EVIDENCE_PATH = REPO_ROOT / ".cache" / "translation-evidence.ndjson"
MANIFEST_NAME = "manifest.json"
GLOBAL_NAME = "global.json"

_EVIDENCE_DIGESTS: dict[Path, set[str]] = {}
_EVIDENCE_PAYLOADS: dict[Path, dict[str, dict[str, object]]] = {}

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

LANGUAGE_SECTIONS = (
    "qualifications",
    "false_positives",
    "drift_excursions",
    "audit_samples",
    "gate_runs",
)

GLOBAL_SECTIONS = ("conformances", "revocations")


@dataclass(frozen=True)
class ApprovalContext:
    """The audit fields shared by every approval record."""

    approval_date: str
    evidence: dict[str, object] | None = None
    model_release: str | None = None
    deployment: str | None = None
    evidence_sha256: str | None = None


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
    evidence_sha256: str
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


def canonical_evidence(payload: Mapping[str, object]) -> str:
    """Return the canonical JSON serialization used for evidence hashes."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def evidence_digest(payload: Mapping[str, object]) -> str:
    """Return the SHA-256 digest of an evidence payload."""
    return hashlib.sha256(canonical_evidence(payload).encode("utf-8")).hexdigest()


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
    evidence = dict(context.evidence or {})
    record: ApprovalRecord = {
        "language": language,
        "msgctxt": entry.msgctxt or None,
        "msgid": entry.msgid,
        "msgid_plural": entry.msgid_plural or None,
        "translation_sha256": translation_digest(msgstr, msgstr_plural),
        "provenance_class": provenance_class,
        "evidence": evidence,
        "evidence_sha256": context.evidence_sha256 or evidence_digest(evidence),
        "model_release": context.model_release,
        "deployment": context.deployment,
        "approval_date": context.approval_date,
    }
    if msgstr_plural is None:
        record["msgstr"] = msgstr
    else:
        record["msgstr_plural"] = msgstr_plural
    return record


def _validate_header(data: object, source: str) -> dict[str, object]:
    """Validate the common ledger header and return the mapping."""
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
    return cast("dict[str, object]", data)


def validate_manifest(data: object, *, source: str = "manifest") -> dict[str, object]:
    """Validate the approvals manifest."""
    validated = _validate_header(data, source)
    languages = validated.get("languages")
    if not isinstance(languages, list) or not all(
        isinstance(language, str) and language for language in languages
    ):
        msg = f"{source} has no 'languages' list"
        raise LedgerError(msg)
    if len(set(languages)) != len(languages):
        msg = f"{source} has duplicate languages"
        raise LedgerError(msg)
    return validated


def _validate_language_sections(validated: dict[str, object], source: str) -> None:
    """Validate the section shapes allowed in a language file."""
    for section_name in GLOBAL_SECTIONS:
        if section_name in validated:
            msg = f"{source} section {section_name!r} belongs in {GLOBAL_NAME}"
            raise LedgerError(msg)
    for section_name in LANGUAGE_SECTIONS:
        if section_name in validated and not isinstance(validated[section_name], list):
            msg = f"{source} section {section_name!r} must be a list"
            raise LedgerError(msg)


def _validate_language_approvals(
    approvals_list: list[object],
    file_language: str,
    source: str,
) -> None:
    """Validate and deduplicate approvals in one language file."""
    seen: set[tuple[str, str, str, str]] = set()
    for index, record in enumerate(approvals_list):
        validated_record = validate_record(record, index=index)
        if validated_record.get("language") != file_language:
            msg = f"{source} approval {index} is for another language"
            raise LedgerError(msg)
        key = record_key(validated_record)
        if key in seen:
            msg = f"{source} has duplicate approval for {key!r}"
            raise LedgerError(msg)
        seen.add(key)


def validate_language_ledger(
    data: object,
    *,
    source: str = "language ledger",
    language: str | None = None,
) -> dict[str, object]:
    """Validate one per-language ledger file."""
    validated = _validate_header(data, source)
    file_language = validated.get("language")
    if not isinstance(file_language, str) or not file_language:
        msg = f"{source} has no non-empty 'language'"
        raise LedgerError(msg)
    if language is not None and file_language != language:
        msg = f"{source} is for {file_language!r}, not {language!r}"
        raise LedgerError(msg)
    _validate_language_sections(validated, source)
    approvals_list = validated.get("approvals")
    if not isinstance(approvals_list, list):
        msg = f"{source} has no 'approvals' list"
        raise LedgerError(msg)
    _validate_language_approvals(approvals_list, file_language, source)
    return validated


def validate_global_ledger(
    data: object, *, source: str = "global ledger"
) -> dict[str, object]:
    """Validate the global conformances and revocations file."""
    validated = _validate_header(data, source)
    for section_name in GLOBAL_SECTIONS:
        if section_name in validated and not isinstance(validated[section_name], list):
            msg = f"{source} section {section_name!r} must be a list"
            raise LedgerError(msg)
    return validated


def _read_json(path: Path) -> object:
    """Read one JSON document with a ledger-shaped error."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        msg = f"cannot read ledger {path}: {error}"
        raise LedgerError(msg) from error
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        msg = f"cannot parse ledger {path}: {error}"
        raise LedgerError(msg) from error


def _write_json(path: Path, data: Mapping[str, object]) -> None:
    """Write one JSON document deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(f"{text}\n", encoding="utf-8")


def load_manifest(directory: Path = APPROVALS_DIR) -> dict[str, object]:
    """Load and validate the approvals manifest."""
    path = directory / MANIFEST_NAME
    return validate_manifest(_read_json(path), source=str(path))


def load_global_ledger(directory: Path = APPROVALS_DIR) -> dict[str, object]:
    """Load and validate the global conformances and revocations file."""
    path = directory / GLOBAL_NAME
    return validate_global_ledger(_read_json(path), source=str(path))


def load_language_ledger(
    directory: Path,
    language: str,
) -> dict[str, object]:
    """Load one language file, or an empty one when it does not exist yet."""
    path = directory / f"{language}.json"
    if path.exists():
        return validate_language_ledger(
            _read_json(path), source=str(path), language=language
        )
    manifest = load_manifest(directory)
    data = {
        "version": manifest["version"],
        "snapshot": manifest["snapshot"],
        "language": language,
        "approvals": [],
    }
    return validate_language_ledger(data, source=str(path), language=language)


def _write_manifest(
    directory: Path,
    version: object,
    snapshot: object,
    languages: Iterable[str],
) -> None:
    """Write the manifest with the sorted language list."""
    _write_json(
        directory / MANIFEST_NAME,
        {
            "version": version,
            "snapshot": snapshot,
            "languages": sorted(set(languages)),
        },
    )


def _manifest_languages(directory: Path) -> list[str]:
    """Return the manifest languages, or an empty list when absent."""
    path = directory / MANIFEST_NAME
    if not path.exists():
        return []
    manifest = load_manifest(directory)
    return cast("list[str]", manifest["languages"])


def write_language_ledger(
    data: Mapping[str, object],
    directory: Path = APPROVALS_DIR,
    language: str | None = None,
) -> None:
    """Write one language file and update the manifest."""
    file_language = language or data.get("language")
    if not isinstance(file_language, str) or not file_language:
        msg = "language ledger write needs a language"
        raise LedgerError(msg)
    manifest_languages = _manifest_languages(directory)
    manifest = (
        load_manifest(directory) if (directory / MANIFEST_NAME).exists() else None
    )
    version = data.get(
        "version", manifest["version"] if manifest is not None else LEDGER_VERSION
    )
    snapshot = data.get(
        "snapshot", manifest["snapshot"] if manifest is not None else None
    )
    approvals_list = data.get("approvals", [])
    if not isinstance(approvals_list, list):
        msg = "ledger 'approvals' must be a list"
        raise LedgerError(msg)
    payload: dict[str, object] = {
        "version": version,
        "snapshot": snapshot,
        "language": file_language,
        "approvals": [
            record
            for record in approvals_list
            if isinstance(record, dict) and record.get("language") == file_language
        ],
    }
    for section_name in LANGUAGE_SECTIONS:
        records = data.get(section_name, [])
        if not isinstance(records, list):
            msg = f"ledger section {section_name!r} must be a list"
            raise LedgerError(msg)
        payload[section_name] = [
            record
            for record in records
            if isinstance(record, dict) and record.get("language") == file_language
        ]
    validated = validate_language_ledger(
        payload,
        source=str(directory / f"{file_language}.json"),
        language=file_language,
    )
    _write_json(directory / f"{file_language}.json", validated)
    _write_manifest(
        directory,
        version,
        snapshot,
        [*manifest_languages, file_language],
    )


def write_global_ledger(
    data: Mapping[str, object],
    directory: Path = APPROVALS_DIR,
) -> None:
    """Write the global conformances and revocations file."""
    manifest = (
        load_manifest(directory) if (directory / MANIFEST_NAME).exists() else None
    )
    payload = {
        "version": data.get(
            "version",
            manifest["version"] if manifest is not None else LEDGER_VERSION,
        ),
        "snapshot": data.get(
            "snapshot", manifest["snapshot"] if manifest is not None else None
        ),
        "conformances": data.get("conformances", []),
        "revocations": data.get("revocations", []),
    }
    _write_json(
        directory / GLOBAL_NAME,
        validate_global_ledger(payload, source=str(directory / GLOBAL_NAME)),
    )


def _load_ledger_dir(directory: Path) -> dict[str, object]:
    """Load and merge the manifest, global file and language files."""
    manifest = load_manifest(directory)
    languages = cast("list[str]", manifest["languages"])
    global_data = (
        load_global_ledger(directory)
        if (directory / GLOBAL_NAME).exists()
        else {"conformances": [], "revocations": []}
    )
    approvals_list: list[ApprovalRecord] = []
    sections: dict[str, list[dict[str, object]]] = {
        name: [] for name in LANGUAGE_SECTIONS
    }
    for language in languages:
        data = load_language_ledger(directory, language)
        if data.get("snapshot") != manifest.get("snapshot"):
            msg = f"language ledger {language!r} has a different snapshot"
            raise LedgerError(msg)
        approvals_list.extend(approvals(data))
        for section_name in LANGUAGE_SECTIONS:
            sections[section_name].extend(section(data, section_name))
    seen: set[tuple[str, str, str, str]] = set()
    for record in approvals_list:
        key = record_key(record)
        if key in seen:
            msg = f"approval {key!r} appears in more than one language file"
            raise LedgerError(msg)
        seen.add(key)
    merged: dict[str, object] = {
        "version": manifest["version"],
        "snapshot": manifest["snapshot"],
        "approvals": sorted(approvals_list, key=record_key),
    }
    merged.update(sections)
    merged["conformances"] = section(global_data, "conformances")
    merged["revocations"] = section(global_data, "revocations")
    return merged


def _write_ledger_dir(data: Mapping[str, object], directory: Path) -> None:
    """Write a merged ledger as one file per language."""
    languages: set[str] = set()
    for section_name in ("approvals", *LANGUAGE_SECTIONS):
        records = data.get(section_name, [])
        if not isinstance(records, list):
            msg = f"ledger section {section_name!r} must be a list"
            raise LedgerError(msg)
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("language"), str):
                languages.add(cast("str", record["language"]))
    existing = _manifest_languages(directory)
    languages.update(existing)
    manifest = (
        load_manifest(directory) if (directory / MANIFEST_NAME).exists() else None
    )
    version = data.get(
        "version", manifest["version"] if manifest is not None else LEDGER_VERSION
    )
    snapshot = data.get(
        "snapshot", manifest["snapshot"] if manifest is not None else None
    )
    for language in sorted(languages):
        write_language_ledger(data, directory, language)
    write_global_ledger(data, directory)
    _write_manifest(directory, version, snapshot, languages)


def write_ledger(data: Mapping[str, object], path: Path = LEDGER_PATH) -> None:
    """Validate and write a single ledger file or the split directory."""
    if path.is_dir() or path.suffix != ".json":
        _write_ledger_dir(data, path)
        return
    validated = validate_ledger(data, source=str(path))
    _write_json(path, validated)


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

    evidence_sha256 = record.get("evidence_sha256")
    if evidence_sha256 is not None and (
        not isinstance(evidence_sha256, str)
        or not _DIGEST_RE.fullmatch(evidence_sha256)
    ):
        msg = f"{where} has a malformed evidence_sha256"
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


def write_evidence(
    payload: Mapping[str, object],
    path: Path = EVIDENCE_PATH,
    *,
    kind: str = "",
    language: str = "",
) -> str:
    """Write one content-addressed evidence payload and return its digest."""
    digest = evidence_digest(payload)
    digests = _EVIDENCE_DIGESTS.get(path)
    if digests is None:
        digests = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    msg = f"cannot parse evidence store {path}: {error}"
                    raise LedgerError(msg) from error
                if isinstance(record, dict) and isinstance(record.get("sha256"), str):
                    digests.add(cast("str", record["sha256"]))
        _EVIDENCE_DIGESTS[path] = digests
    if digest in digests:
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "sha256": digest,
        "kind": kind,
        "language": language,
        "payload": dict(payload),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    digests.add(digest)
    return digest


def load_evidence(
    digest: str,
    path: Path = EVIDENCE_PATH,
) -> dict[str, object] | None:
    """Return the payload for an evidence digest, or None when unavailable."""
    payloads = _EVIDENCE_PAYLOADS.get(path)
    if payloads is None:
        payloads = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    msg = f"cannot parse evidence store {path}: {error}"
                    raise LedgerError(msg) from error
                if not isinstance(record, dict):
                    continue
                sha = record.get("sha256")
                payload = record.get("payload")
                if isinstance(sha, str) and isinstance(payload, dict):
                    payloads[sha] = cast("dict[str, object]", payload)
        _EVIDENCE_PAYLOADS[path] = payloads
    return payloads.get(digest)


def compact_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    """Return the compact summary stored beside an evidence digest."""
    summary: dict[str, object] = {}
    proposals = evidence.get("proposals")
    if isinstance(proposals, list) and proposals:
        summary["proposals"] = [
            {
                "deployment": proposal.get("deployment"),
                "family": proposal.get("family"),
            }
            for proposal in proposals
            if isinstance(proposal, dict)
        ]
    for field in (
        "judge",
        "checks",
        "backtranslation",
        "high_impact",
        "prompt_version",
        "prompt_hash",
    ):
        value = evidence.get(field)
        if value is not None:
            summary[field] = value
    if evidence.get("tm_dominant") is True:
        summary["tm_dominant"] = True
    return summary


def compact_approval_record(
    record: dict[str, object],
    path: Path = EVIDENCE_PATH,
) -> None:
    """Move one approval's full evidence into the sidecar."""
    evidence = record.get("evidence")
    full = dict(evidence) if isinstance(evidence, dict) else {}
    record["evidence_sha256"] = write_evidence(
        full,
        path,
        kind="approval",
        language=str(record.get("language") or ""),
    )
    record["evidence"] = compact_evidence(full)


def compact_operational_record(
    record: dict[str, object],
    path: Path = EVIDENCE_PATH,
    *,
    kind: str,
) -> None:
    """Move one operational record's calls into the sidecar."""
    calls = record.get("calls", [])
    payload = {"calls": calls if isinstance(calls, list) else []}
    record["evidence_sha256"] = write_evidence(
        payload,
        path,
        kind=kind,
        language=str(record.get("language") or ""),
    )
    record.pop("calls", None)


def load_gate_run_calls(
    record: Mapping[str, object],
    path: Path = EVIDENCE_PATH,
) -> list[dict[str, object]]:
    """Resolve a gate run's calls from the sidecar when they are compacted."""
    calls = record.get("calls")
    if isinstance(calls, list):
        return [
            cast("dict[str, object]", call) for call in calls if isinstance(call, dict)
        ]
    digest = record.get("evidence_sha256")
    if not isinstance(digest, str):
        return []
    payload = load_evidence(digest, path)
    if payload is None:
        return []
    resolved = payload.get("calls")
    if not isinstance(resolved, list):
        return []
    return [
        cast("dict[str, object]", call) for call in resolved if isinstance(call, dict)
    ]


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, object]:
    """Load and validate a single-file or split ledger."""
    if path.is_dir() or path.suffix != ".json":
        return _load_ledger_dir(path)
    return validate_ledger(_read_json(path), source=str(path))


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

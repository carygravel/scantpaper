## Context

The 3.0.18 release (`2026-09-11-fix-legacy-profile-load`) repaired named
profiles written by gscan2pdf 2.x but explicitly assumed `default-scan-options`
is always the well-formed output of `Profile.get()`. A legacy
`default-scan-options = {"backend": [{"mode": "Binary"}, ...]}` (no `frontend`
key) contradicts that assumption: `Profile.__init__` only treats a dict as a
combined frontend+backend shape when it has a `"frontend"` key
(`scanner/profile.py:20`), so a backend-only dict is treated as an unindexable
frontend dict and its `backend` is discarded. None of the saved options reach
the scan dialog, and at the end of the session the empty profile is written
back, permanently destroying the user's stored options.

The rest of the pipeline already converges on the fix: once `backend` is
reachable, `Profile` coerces legacy single-key dict pairs `{name: value}` to
`(name, value)` tuples (`scanner/profile.py:40-44`). The fix therefore belongs
in the same config-migration layer as the named-profile fix
(`_normalise_profiles`), so every downstream consumer — dialog load and save
alike — sees the canonical `{"frontend": ..., "backend": [...]}` shape.
See proposal.md `Why` for the user-visible report.

## Goals / Non-Goals

**Goals:**
- A legacy backend-only `default-scan-options` is parsed, applied to the scan
  dialog, and serialised back in the canonical empty-frontend shape.
- The normalisation is shared with the named-profile logic (DRY) and lives in
  config migration, exactly where the prior fix lives.
- Coverage for the load path, the corrupted-serialisation path, and the
  well-formed round-trip (spec scenarios in
  `specs/config-loading/spec.md`).

**Non-Goals:**
- Recovering scan options already wiped by an earlier buggy run — that data is
  gone and cannot be reconstructed.
- Migrating option values that the target scanner cannot apply (e.g. gscan2pdf
  `quick-format`, `scan-area`): such options are dropped by the dialog's
  normal apply path today and stay dropped.
- Changing how newly created scan options are stored.

## Decisions

### D1: Normalise `default-scan-options` in the config migration

Extend the migration in `config.py` so that after `_normalise_profiles` runs,
the `default-scan-options` value is also brought to the canonical shape.
Implement by factoring the per-dict repair out of `_normalise_profiles` into a
helper, e.g. `_normalise_scan_options(value)`, applied to each named profile
and to `config["default-scan-options"]`. The helper repairs:

- **Shape A (gscan2pdf 2.x source):** dict with no `frontend` key
  (`{"backend": [...]}`) → `setdefault("frontend", {})`,
  `setdefault("backend", [])`.
- **Shape B (corruption produced by a buggy round):**
  `{"frontend": {"backend": [...]}, "backend": []}` — the serialised, misparsed
  legacy profile. Detected when `frontend` itself contains a `backend` key
  that `backend` does not; hoist it: `backend = frontend.pop("backend")`.

Alternative considered: normalising only Shape A. Rejected because Shape B is
the actual on-disk serialisation of the misparsed legacy value (as reproduced
during exploration via `Profile(legacy).get()`), so users who ran the buggy
build can be sitting on it and it would otherwise stay broken.

Alternative considered: fixing only `Profile.__init__`. Rejected because the
config migration is the single choke point the prior fix established; fixing
only the constructor would leave the corrupted write-back in place.

### D2: Leave `Profile.__init__`'s combined-dict branch as the single decoder

The constructor keeps doing one job: decoding the canonical profile dict / CLI
dict pairs to tuples and applying CLI mapping. Config normalisation guarantees
the input is canonical, so no decoder change is required for the fix. The
existing frontend-dict path stays exactly as is.

### D3: No tolerance added for options the scanner cannot apply

`quick-format`/`scan-area`-style gscan2pdf options were never applied by
pre-3 versions either and are dropped when `current_scan_options` is rebuilt.
The fix preserves every option the scanner accepts; the spec's round-trip
scenario is worded accordingly (only applied values are guaranteed back).
Alternative considered: keeping unknown options verbatim in
`default-scan-options`; rejected as scope creep and behaviour the dialog cannot
reason about on reload.

## Risks / Trade-offs

- [Shape B hoisting heuristics] → The detection is narrow (spurious `backend`
  inside `frontend` with an empty outer `backend`); it can only trigger on
  values that misparse today, so it cannot alter a well-formed profile.
- [Legacy options that cannot be applied are still dropped] → This matches
  pre-existing behaviour for every profile type; no user-visible regression.
- [Log 2 from exploration shows options being applied at startup despite the
  parse analysis] → Not fully reconciled during exploration; re-test with a
  clean `--log` run on a legacy rc after this fix lands and before release. See
  Open Questions.

## Migration Plan

- Ship as a normal version bump; the migration is in-place at config load, so
  the user's next start with a legacy `default-scan-options` repairs the value
  on the first run.
- No rollback path needed beyond reverting the commit: a repaired rc is
  canonical, which every released version since 3.0 can read.

## Open Questions

- Whether the exploration wrinkle (Log 2 applying options at startup without
  an rc file) indicates a second, separate load path for `default-scan-options`
  (e.g. pull-scan/PVS settings). If a re-test proves a second path exists, it
  is very likely already covered by the same fixed config value; if not, it
  deserves its own follow-up change. Deferred: does not change the approach,
  the specs, or the task breakdown.
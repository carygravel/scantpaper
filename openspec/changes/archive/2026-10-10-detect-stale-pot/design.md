## Context

`dev/check_launchpad.py` already detects the upstream→local direction by
snapshotting Launchpad's public state into `po/launchpad-state.json` and
diffing against it. That tool owns the baseline file, the HTTP/CLI conventions
(`--json`, advisory zero-exit, a distinct `--update` stamping action) and the
scheduled `translations-check` workflow. This change adds the reverse,
local→upstream direction to the same tool and baseline. See proposal.md for
motivation and specs/translations/spec.md for the behaviour contract.

## Goals / Non-Goals

**Goals:**
- Reuse the existing tool, baseline file and workflow conventions.
- Compare the locally generated message set against a recorded record of the
  last uploaded pot, entirely from local state (Launchpad's message set is not
  readable without authentication).
- Make the signal robust to changes that do not alter the message set.

**Non-Goals:**
- Reading or downloading Launchpad's pot (requires auth; explicitly out).
- Actually performing the upload — the tool only detects and reminds.
- Changing the upstream→local direction's behaviour.

## Decisions

### D1. Fingerprint the sorted, unique msgid set
Extract every `msgid` from the generated template, dedupe, sort, and use that
ordered list as the message-set fingerprint (a digest is derived from it for
cheap comparison). Rationale: verified in exploration that `xgettext`/`msgcat`
output order is deterministic for fixed inputs, but changes when a string
moves between source files (a pure refactor) or when a gettext version
reorders output — neither alters the translatable surface. The msgid *set* is
authoritative, matching how Launchpad keys its template.

**Alternatives considered:** hashing the raw `.pot` file — rejected because the
volatile header (`POT-Creation-Date`, `Project-Id-Version`) changes on every
regeneration and would always signal a false change; ordered msgid list —
rejected for the false positives above.

### D2. Store the sorted msgid list, not just a digest
Persist the sorted list of msgids (plus a derived digest and count) in the
baseline, so the report can name which strings were added and removed, making
the CI issue actionable. 550 strings is small enough to store comfortably.

### D3. Extend `check_launchpad.py` rather than add a new tool
It already owns the baseline, CLI and workflow plumbing. The new signal is
computed locally, so it fits as an additional report section and a `--json`
field with no new network requests.

### D4. A distinct `--record-pot` stamping action
Mirrors the existing `--update`: after a pot is actually uploaded, the
maintainer runs `check_launchpad.py --record-pot` to record the fingerprint of
the pot just pushed. This keeps the baseline a record of *what was uploaded*,
not merely the latest state observed, matching the upstream design's
philosophy. Refuses to stamp when the pot cannot be read, like `--update`.

### D5. Share pot generation with `generate_pot.py`
Refactor `generate_pot.py` to expose a `generate_template()` helper returning
the template text (the CLI writes it to the default path as today). The check
imports this helper so the local fingerprint always reflects the current
source and CI needs no committed pot. `check_launchpad.py` already runs with
`PYTHONPATH=src` in the workflows.

**Alternatives considered:** a `--pot <path>` option reading an existing file —
kept as a fallback for ad-hoc runs, but generation-on-demand is the default so
the scheduled check is self-contained.

### D6. Report the two directions separately
The report and JSON payload gain a `local_pot_changed` signal (and a `local_pot`
section with `added`/`removed`/`msgid_count`) alongside the existing upstream
signals. The scheduled workflow files a separate "new strings ready to upload"
issue, so each direction has its own living reminder and closing one does not
dismiss the other.

## Risks / Trade-offs

- **msgid parsing complexity** (multi-line `msgid`, `msgid_plural`,
  `msgctxt`) → use a small regex parser that reads each `msgid "…"`/`msgid ""`
  quoted continuation block fully; the same parser is unit-tested against the
  real generated template.
- **Missing `--record-pot` discipline** → advisory: a forgotten stamp just
  keeps reporting "stale" (zero exit by default), consistent with the
  upstream check; it never blocks a release.
- **CI needs gettext** → already required by `check_po.py`; `xgettext` is
  available on `ubuntu-latest`.
- **Baseline schema addition** → purely additive; a pre-existing baseline
  without `uploaded_pot` yields "not determined" for the local signal until
  `--record-pot` is first run, which is safe rather than a false "unchanged".

## Migration Plan

- Baseline: additive only; no rewrite of the existing `template`/`languages`
  sections. Old baselines remain valid and upgrade on the next `--record-pot`.
- Release: rollback is reverting the tool changes; an untouched baseline
  carries no `uploaded_pot` section until it is stamped, so nothing corrupts.

## Open Questions

None that would change the approach or task breakdown.

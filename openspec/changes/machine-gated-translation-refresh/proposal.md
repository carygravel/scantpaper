# Proposal

## Why

Scantpaper's translation tooling prevents corrupt catalogs but does not keep
them current. Coverage is measured against each catalog's own entries, so a
catalog that is 131 strings behind the current template still reports 98%
coverage; measured against the template, the strongest languages are at about
79%. Every feature adds fuzzy strings that never reach users, and fuzzy entries
skip `msgfmt --check`, so a proposal can carry a runtime fault that stays
invisible until someone clears the flag.

Only English and German have a live human review path. The other 42 do not,
but they are not without human evidence: 9,908 of the 13,615 shipped entries
are unchanged from the pre-2026 Launchpad exports, and 15 languages still ship
only human-origin text. The missing piece is not human authority but a way to
recognise, preserve and extend it. The project needs a workflow that refreshes
catalogs mechanically, uses models to fill the gap, and ships only what clears
an explicit, auditable quality gate, leaving English fallback in place when the
evidence is not there.

## What Changes

- **Measure against the template.** Coverage reports compare each catalog with
  the current `.pot` and report shipped, fuzzy, missing, stale and obsolete
  entries per language. The denominator is the current source, not the catalog.
- **Merge as a deterministic step.** A maintained command regenerates the
  template and updates every catalog, records the previous msgid for every
  changed entry, and does not silently adopt `msgmerge` fuzzy matches. A
  refresh is reviewable as one diff.
- **Validate proposals as if shipped.** Fuzzy entries receive the same
  placeholder, plural, markup and render checks as non-fuzzy entries. A
  test-only compiled catalog formats every message with generated arguments to
  catch Python `%` errors before a proposal can be cleared.
- **Give translators context.** `TRANSLATORS:` comments, widget and action
  context, and a glossary travel with the template, so short labels such as
  "Select" or "Pan" are unambiguous to a human or a model.
- **Add a machine gate.** Two independent model families propose; a separate
  family judges both blind; back-translation checks meaning for sentences. The
  gate may approve a string only when the deterministic checks pass and the
  semantic evidence agrees.
- **Abstain by default.** A string that does not clear the gate stays fuzzy and
  falls back to English. "Not translated" is a valid, reported outcome, never
  an invitation to clear the flag to improve a number.
- **Record provenance and make approvals provisional.** A ledger keyed by
  language, context, msgid and msgstr records who or what approved a string,
  with evidence, model release and deployment, using the classes
  `human-historical`, `human-review`, `in-project-rebase`, `tm-consensus`,
  `machine-strong` and `machine-weak`. A change to either text invalidates
  the approval; machine approvals are revocable per language, deployment or
  model release.
- **Qualify models per language and release.** A qualification attaches to a
  model release, not to one provider: a deployment of the same release
  inherits it after a small conformance probe, while a genuinely different
  model must qualify on its own. A provider serving the same release is the
  same family and cannot supply the independent second opinion. A model that
  disappears keeps its approvals; retirement removes a future translation
  path, not past work.
- **Detect drift with a fixed probe.** A small, versioned set of
  human-translated strings is re-run before a batch. A drop pauses new
  approvals and triggers re-qualification, but does not demote existing
  translations; demotion needs audit evidence.
- **Use a cross-project translation memory as evidence.** Index GPL-compatible
  free-software catalogs with project, language and license provenance. Exact
  and dominant matches help with generic action labels, terminology and model
  qualification, but a match is evidence, not permission: 25-35% of dominant
  matches disagree with scantpaper's own human translation, so the TM feeds the
  gate rather than clearing a string on its own. The bulk corpus comes from
  public Ubuntu language packs and upstream or distro catalogs; the installed
  system catalogs are a usable proxy while that index is built.
- **Keep Rosetta an optional, authenticated source.** Launchpad has no API key
  and no bulk cross-project export: its web service uses OAuth 1.0a, and a
  catalog is a one-off, logged-in download per project and language. A sync
  may therefore use a locally authorized read-only token, but it is never a
  CI dependency, and Rosetta is not the only evidence source. Rosetta's own
  scantpaper template is also stale (544 strings against the current 665), so
  it cannot supply the newest strings and does not replace the pre-2026
  snapshot or the cross-project TM.
- **Require human-origin evidence for high-impact strings, not a live
  reviewer.** Menu actions, destructive verbs and data-loss errors may ship
  when the translation is an unchanged pre-2026 Launchpad translation, a
  mechanical rebase of one, a dominant cross-project match, or English/German
  review. If none of those exist, the strict machine gate may still ship the
  string as provisional, with a user-report kill switch. The absolute human
  gate is removed; the machine-only path remains limited to a few new strings
  per language and carries a stricter evidence bar.
- **Audit and demote.** A human correction of a machine-approved string is
  recorded as a false positive. A random native sample estimates the true error
  rate; a language whose reported defect rate exceeds a threshold has its
  machine approvals demoted and rebuilt with English fallback.
- **Policy change.** `AGENTS.md` currently requires every clearance to be an
  explicit per-string human decision. This change replaces that with a
  standing, maintainer-approved policy: the gate may clear fuzzy only within
  the classes and languages the policy names, and every clearance is recorded
  in the ledger. The policy is reviewed once; it is not a per-string
  permission.
- **Recover the frozen human core.** Import the pre-2026 Launchpad snapshot as
  `human-historical` approvals. The 2,240 entries the 2026 work added and the
  1,467 it changed are provisional: the changed ones are compared with the old
  human text, and the added ones are re-checked, before either is
  grandfathered. The first release with the gate must not turn a model rewrite
  into a historical approval by accident.

## Capabilities

### New Capabilities

- `machine-translation-gate`: the approval behavior for machine-produced
  translations: independent proposal and judging roles, per-language and
  per-release model qualification, deployment conformance and drift probes,
  abstention, provenance classes and revocation, high-impact strings, evidence
  from the historical Rosetta core and the cross-project translation memory,
  and the human-correction audit loop.

### Modified Capabilities

- `translations`: coverage measured against the current template; a
  deterministic merge step that preserves the pre-2026 snapshot; mechanical
  validation of fuzzy proposals and a test-only render check; translator
  context in the template; release builds that report real coverage and
  include only approved entries. The existing fuzzy fallback, Rosetta flow and
  mechanical validation requirements remain.

## Impact

- **Tooling:** `dev/generate_pot.py`, `dev/summarise_po.py`,
  `dev/check_po.py` and `dev/compile_mo.py`; a new `dev/` command set for
  merge, coverage report, translation-memory indexing, propose, verify,
  approve, drift probe, capability report and audit.
- **Catalogs:** every `po/scantpaper/*.po` is merged; the pre-2026 snapshot is
  preserved as the human reference; the template gains translator comments; a
  new approval ledger and a provenance-tracked translation-memory index live
  beside the catalogs.
- **Audit:** the 1,467 entries the 2026 review changed are compared with the
  pre-2026 human text before they are grandfathered; the 2,240 model-added
  entries are re-checked by the gate.
- **Source:** `TRANSLATORS:` comments and, where needed, `msgctxt` for
  ambiguous strings; no change to runtime behavior.
- **Release:** the build continues to exclude fuzzy entries and adds the
  approval condition; it reports per-language coverage and the number of
  English fallbacks.
- **CI:** deterministic checks run in CI. Model calls are maintainer-run and
  are never a CI dependency or a source of committed credentials; any model
  credential or Launchpad OAuth token comes from the environment or a local
  credential store, never from the repository.
- **Docs and policy:** `AGENTS.md`, `README.md` and the `translations` spec are
  updated to describe the gate, the abstention rule and the audit loop.
- **Dependencies:** no new runtime dependency; the development tooling uses
  the Python standard library for HTTP and the existing `polib`/gettext stack.
- **Licensing:** the translation-memory index records project, language and
  license, and includes only GPL-compatible catalogs. Launchpad's terms make
  individual string translations BSD (revised, without advertising clause),
  but a group of strings from one project that forms a derivative work stays
  under that project's licence, and upstream imports keep their original
  licence. Bulk ingestion is therefore checked per project rather than assumed
  to be BSD; the 9,908 pre-2026 scantpaper entries are already under the
  project's GPL-3.0-only license.
- **Risks:** model quality for low-resource languages, correlated errors
  across families, false confidence from consensus, silent model drift, model
  retirement, provider diversity being mistaken for family independence, and
  the fact that historical provenance is inferred from the pre-2026 snapshot
  and header dates rather than attested per entry. The wider corpus agrees
  with scantpaper's human translations only 65-77% of the time, so a dominant
  TM match is evidence, not proof. Mitigations are the per-language and
  per-release qualification, deployment conformance, the drift probe, the
  capability report, the abstention default, the high-impact rule, the judge
  audit, the licensing and provenance record, and provisional and revocable
  approvals. The largest residual risk is that no human ever audits a
  machine-approved language; the proposal makes that risk explicit rather
  than hiding it behind a fuzzy flag.

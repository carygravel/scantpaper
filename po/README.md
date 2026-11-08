# Translation workflow

This is the maintainer documentation for scantpaper's translations: setup,
catalog refresh, coverage, validation, the approval ledger, translation
memory, Rosetta import and the machine gate.

`po/TRANSLATION-FINDINGS.md` is a historical record of the first 2026 review
pass. It is not the current workflow.

## Setup

Work from a checkout with the development dependencies installed:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

The tooling also needs GNU gettext (`xgettext`, `msgcat`, `msgmerge` and
`msgfmt`) on `PATH`. `polib` comes from the test extra.

Some scripts import `scantpaper.const`, so run them with `PYTHONPATH=src`:

```sh
PYTHONPATH=src python3 dev/generate_pot.py
PYTHONPATH=src python3 dev/merge_po.py
```

The Rosetta OAuth option needs `launchpadlib`. Model access needs the
environment variables named in `po/translation-gate.json`; no key belongs in
the repository or in CI.

The layout is:

```text
po/scantpaper/<language>.po     catalogs, one per language
po/scantpaper/scantpaper.pot    generated template (git-ignored)
po/approvals/manifest.json      approval ledger manifest
po/approvals/global.json        global conformances and revocations
po/approvals/<language>.json    per-language approvals and summaries
po/translation-audit.json       human-core audit report
po/translation-gate.json        model releases and deployments
po/translation-gate.roles.json  proposer and judge roles
po/translation-gate.example.json  generic fallback config
po/translation-gate.roles.example.json  generic fallback roles
po/tm-sources.json              translation-memory licence manifest
po/drift-probe/<language>.json  fixed human-translation probe
po/fuzzy-defect-baseline.json   ratcheted known-defect baseline
```

Quick checks:

```sh
python3 dev/check_po.py
python3 dev/translation_gate.py validate
```

To validate the committed generic example pair:

```sh
python3 dev/translation_gate.py \
    --config po/translation-gate.example.json \
    --roles po/translation-gate.roles.example.json validate
```

The real `po/translation-gate.json` and `po/translation-gate.roles.json` are
local and git-ignored, because they can name private providers. The committed
`*.example.json` files are generic fallbacks for validation and templates. Use
`dev/sync_translation_gate.py` to generate the real files.

## Refresh the catalogs

Regenerate the template and merge every catalog in one deterministic step:

```sh
PYTHONPATH=src python3 dev/merge_po.py
```

The merge uses `msgmerge --previous --no-fuzzy-matching`. It keeps existing
fuzzy flags, records a changed msgid's predecessor as `#| msgid`, does not
adopt a fuzzy match, and preserves header dates. A second run on unchanged
inputs produces no diff. The pre-2026 snapshot is git commit `1a303718`; the
merge never rewrites it or the approval ledger.

New strings are seeded as `#, fuzzy` proposals and fall back to English.

## Measure coverage

Coverage is measured against the current template, not the catalog's own entry
count:

```sh
python3 dev/summarise_po.py --pot po/scantpaper/scantpaper.pot
python3 dev/summarise_po.py --pot po/scantpaper/scantpaper.pot --json
```

A catalog with 549 shipped entries out of 558 entries in a 665-message
template reports `549 of 665`, plus separate `missing`, `stale` and `obsolete`
counts.

## Validate catalogs and proposals

```sh
python3 dev/check_po.py
pytest src/scantpaper/tests/test_rendered_catalogs.py
```

`dev/check_po.py` runs `msgfmt --check`, validates `Plural-Forms` against CLDR,
and checks every non-obsolete entry, fuzzy included. It reads plural forms from
`msgstr_plural`, checks printf and `str.format` placeholders, and reports
source-side translation hazards as advisories.

The render check clears fuzzy on a temporary copy, compiles it with `msgfmt`,
and formats every message with generated arguments through gettext. A Python
`%` or `str.format` fault therefore fails before approval.

Known pre-existing defects are listed in `po/fuzzy-defect-baseline.json`. A
new defect fails; a fixed one can be removed from the baseline. The current
baseline is empty.

## Human translations and Rosetta

Translations may be contributed through
[Launchpad Rosetta](https://translations.launchpad.net/scantpaper), a merge
request or an issue with a `.po` attachment. Only confirmed translations
reach users; a fuzzy entry always falls back to English.

Upload the template directory as-is:

```sh
python3 dev/rosetta_tarball.py
```

### Downloading a Rosetta export

Launchpad has no bulk export API and no API key. A catalog is a one-off,
logged-in download from its per-language `+export` URL:

```text
https://translations.launchpad.net/scantpaper/trunk/+pots/scantpaper/de/+export
```

Then validate and merge it offline:

```sh
python3 dev/rosetta_import.py --import ~/Downloads/de.po \
    --language de --apply
```

The command uses `po/scantpaper/scantpaper.pot` and
`po/scantpaper/<language>.po` by default, accepts a whole language-pack tree,
and rejects an export whose msgids are not in the current template. It never
contacts Launchpad.

For a read-only automated sync, `launchpadlib` handles Launchpad's OAuth 1.0a
login; the export remains a web GET rather than a web-service method:

```python
from launchpadlib.launchpad import Launchpad

launchpad = Launchpad.login_with(
    "scantpaper translation export",
    "production",
    version="devel",
)
# launchpadlib keeps the OAuth token in its local credential store.
# With the signed session, GET the +export URL and save the .po.
```

No token or key belongs in the repository or CI, and CI never authenticates.

## The approval ledger

`po/approvals/` is the source of truth for whether a translation may ship.
The directory holds a small `manifest.json`, a `global.json` for conformances
and revocations, and one file per language. It is separate from the `#, fuzzy`
flag, and the two answer different questions:

- `fuzzy` is a gettext proposal state. A fuzzy entry is never compiled into a
  released catalog, whatever the ledger says.
- An approval says that the exact translation text may ship. A non-fuzzy
  entry without a valid approval falls back to English in a release build.

Each approval carries an `evidence_sha256`. The full proposal, check and call
payloads are stored in `.cache/translation-evidence.ndjson`, a
content-addressed, git-ignored sidecar. Archive that file with the release
artifacts. A checkout without it can still build a release; `costs` reports
the summary totals, and a deep audit reports the evidence as unavailable.

The one-time migration is:

```sh
python3 dev/split_translation_ledger.py --write
```

It verifies every approval key and translation digest before removing the old
single file. The sidecar is append-only; archive it, do not commit it.

The ledger is keyed by `(language, msgctxt, msgid, msgid_plural)` plus the
SHA-256 of the canonical translation text. Editing the source string, the
context or the translation invalidates the approval. An old approval cannot
stick to new text.

Every approval names exactly one class:

| class | meaning |
| --- | --- |
| `human-historical` | unchanged pre-2026 Launchpad text |
| `human-review` | current text reviewed by a human |
| `in-project-rebase` | mechanical rebase of a human translation |
| `tm-consensus` | dominant cross-project match plus evidence |
| `machine-strong` | strict machine gate, provisional |
| `machine-weak` | lower-confidence machine evidence, provisional |

Only the two `machine-*` classes are revocable without editing catalogs.

A minimal human record, ready to validate with `dev.translation_ledger`:

```json
{
  "version": 1,
  "snapshot": "1a3037183eadc10004f7f4d6228bd7f9192aa2ec",
  "approvals": [
    {
      "language": "de",
      "msgctxt": null,
      "msgid": "Delete",
      "msgid_plural": null,
      "msgstr": "Löschen",
      "translation_sha256":
        "1e055a9ac96177d84fb5ff714484667ebdb73dfbf6b5732ab26c95e4bc08faa5",
      "provenance_class": "human-historical",
      "evidence": {},
      "model_release": null,
      "deployment": null,
      "approval_date": "2026-02-28"
    }
  ]
}
```

The example round-trips through the helpers in
`dev/tests/test_translation_ledger.py`.

A new human-reviewed string needs a `human-review` record. The current
`dev/translation_gate.py approve` command applies a machine-gate decision;
human-review records are created with the ledger helpers until a dedicated
command exists.

### The human-core audit

`dev/audit_human_core.py` compares each shipped entry with commit `1a303718`.
Unchanged text becomes `human-historical`; a placeholder-only change becomes
`in-project-rebase`; a model rewrite is restored to the old human text and
parked for review. Entries with no human text stay pending for the gate.

```sh
python3 dev/audit_human_core.py            # dry run
python3 dev/audit_human_core.py --apply    # write ledger and report
python3 dev/audit_human_core.py --apply --language es
```

`po/translation-audit.json` lists every shipped entry that is approved or
pending. A scoped run with `--language` (repeatable) merges the selected
languages' blocks, pending entries and parked entries into the existing
report, recomputes the totals and notes, and rewrites only the selected
languages' ledger files. Every other language stays exactly as it was, so a
per-language run can be committed on its own.

## Translation memory

Build a local index from installed `.mo` catalogs:

```sh
python3 dev/tm_index.py
python3 dev/tm_index.py --stats
```

The index is `.cache/translation-memory.sqlite3`, git-ignored and reproducible.
`po/tm-sources.json` records each project's language, licence and origin; a
catalog with no licence in the manifest, or with an incompatible one such as
`GPL-2.0-only`, is refused instead of indexed. BSD, `GPL-2.0-or-later` and
`GPL-3.0-or-later` sources are accepted.

Import an upstream or Ubuntu language-pack tree:

```sh
python3 dev/tm_index.py --import /path/to/po \
    --project sane-backends --language de --license GPL-2.0-or-later
```

Dominance counts distinct source projects, not raw occurrences, so one large
catalog cannot outvote several projects that agree. A match is evidence, not
permission; a dominant match alone never approves a string.

## The machine gate

The gate obtains two proposals from independent model families, judges them
blindly with a third family, checks determinism, and back-translates
sentences. Any missing or failing evidence means abstention.

When every passing proposal has the same trimmed text and at least two
independent families produced it, the agreement is the semantic verdict. The
gate records the tie and does not call the judge; a sentence is still
back-translated. This avoids paying a reasoning judge to return `ABSTAIN` when
it has no choice to make. The two-family requirement and the deterministic
checks still apply.

### Releases and deployments

`po/translation-gate.json` separates a **release** from a **deployment**:

```json
"releases": {
  "qwen/3.8@2026-09": {
    "family": "qwen",
    "model": "qwen-3.8",
    "revision": "2026-09"
  }
},
"deployments": {
  "qwen-a": {
    "release": "qwen/3.8@2026-09",
    "provider": "provider-b",
    "endpoint": "https://api.example.invalid/v1/chat/completions",
    "quantization": "fp16",
    "prompt_hash": "sha256:qwen-prompt-v1",
    "decoding": {"temperature": 0.0, "top_p": 1.0},
    "key_env": "QWEN_API_KEY",
    "proposer": true,
    "judge": false
  }
}
```

A qualification attaches to `(release, language)`. A deployment of the same
release inherits it only after a conformance probe. Changing the provider,
endpoint, quantization, prompt hash or decoding produces a different
deployment and requires conformance again. Two deployments of one release are
one family for independence, however many providers serve it.

`dev/translation_gate.py validate` refuses duplicate proposer families,
a judge from a proposer family, and two deployments of one release used as
the two independent voices.

### Qualification, conformance and drift

Qualification reproduces held-out human approvals for a language and records
the metric, tolerance, release and drift baseline in the ledger. A language
with no human baseline stays ineligible.

Run one qualification from the command line:

```sh
python3 dev/translation_gate.py estimate --action qualification \
    --release qwen/3.8@2026-09 --language de
python3 dev/translation_gate.py qualify \
    --release qwen/3.8@2026-09 --language de --max-cost 0.01
```

`qualify` selects up to `--count` (default 20) held-out human approvals,
records the score, tolerance, baseline size, deployment and cost in the
ledger, and prints them. `--catalog` overrides the default
`po/scantpaper/<language>.po`, and `--json` prints the whole record.

`thresholds` holds the global defaults. A language whose reviewed translations
reproduce less exactly can record a calibrated override under
`language_thresholds`:

```json
"language_thresholds": {
  "de": {"qualification": 0.35, "drift": 0.3}
}
```

The override replaces the global `qualification` or `drift` value for that
language only; every other language keeps the default. Calibrate it from a
real qualification and drift run, not from a single string, and record the
measured scores with the change that introduces it. The exact-match metric is
generous to English variants, whose target often equals the source, and strict
for a genuine translation, so the two cannot share one tolerance.

A language with no human baseline is recorded as ineligible with the reason
`no held-out human entries` and makes no model call. A score below the
tolerance is recorded with `qualified: false`. Both write a record and exit
successfully. An unknown release, unreadable catalog, missing credential or
over-budget estimate exits non-zero without writing one.

Conformance admits a deployment of an already-qualified release after a
passing probe. A merely similar model does not inherit and needs full
qualification.

`po/drift-probe/<language>.json` holds a fixed, versioned set of human
translations stratified across short labels, sentences, placeholders, plurals
and high-impact actions. A score below the drift threshold pauses new
approvals for that release and language and queues the window for audit. It
does not demote existing approvals; only confirmed defects do that.

Run a probe with:

```sh
python3 dev/translation_gate.py estimate --action drift \
    --deployment qwen-a --language de
python3 dev/translation_gate.py drift \
    --deployment qwen-a --language de --max-cost 0.01
```

`drift` infers the release from the deployment and reads
`po/drift-probe/<language>.json` by default. `--probe` overrides the file,
`--since` sets the audit-window start stored with a pause (default today), and
`--json` prints the full result. A passing probe writes nothing. A failing
probe appends a `drift_excursions` record and pauses new approvals; it does
not demote existing approvals.

Use `--dry-run` to screen a new model without pausing anything. Nine
languages currently have no probe items (`ab`, `af`, `ar`, `en_US`, `hi`,
`id`, `ro`, `sr`, `vi`); the command rejects an empty probe instead of
recording a false pause. There is no resume command yet: resolving a pause
requires re-qualification and audit.

### Running the gate

```sh
python3 dev/translation_gate.py validate
python3 dev/translation_gate.py capability
python3 dev/translation_gate.py gate --language de --msgid "Delete" \
    --output decision.json
python3 dev/translation_gate.py approve --catalog po/scantpaper/de.po \
    --msgid "Delete" --decision decision.json
python3 dev/translation_gate.py sample --language de
```

`gate` uses the model credentials only when it makes a request. A missing
variable is reported by name, never by value. `approve` writes the decision's
translation into the catalog before clearing fuzzy, so it can fill an empty
entry.

Machine approvals are provisional. Revoke them by language, deployment or
release; the next build applies the revocation:

```sh
python3 dev/translation_gate.py revoke --scope language --value de
python3 dev/translation_gate.py revoke --scope deployment --value qwen-a
python3 dev/translation_gate.py revoke --scope release \
    --value qwen/3.8@2026-09
```

A random audit sample estimates the error rate per language and class.
Recording a false positive through the ledger helpers and exceeding the
defect-rate threshold demotes that language's machine approvals:

```sh
python3 dev/translation_gate.py sample --language de --size 20 --seed 7
```

### Translating missing entries

The first targets are the English and German catalogs: `en_GB`, `en_US` and
`de`. There is no `en.po`.

Refresh the catalogs, qualify each role release, run a drift probe, then
translate a small batch:

```sh
PYTHONPATH=src python3 dev/merge_po.py
python3 dev/translation_gate.py qualify \
    --release qwen/3.8@2026-09 --language de --count 100
python3 dev/translation_gate.py drift \
    --deployment qwen-a --language de
python3 dev/translation_gate.py translate --language de --limit 10 \
    --max-cost 0.05
```

`translate` selects entries with an empty `msgstr`, or a plural entry with an
empty form in `msgstr_plural`, writes each approved translation into the
catalog, clears fuzzy and records the approval.
`--include-fuzzy` also reconsiders entries that already have a fuzzy proposal
and replaces them. `--language` defaults the catalog to
`po/scantpaper/<language>.po`; `--catalog` overrides it. `--max-cost` caps the
whole batch, `--limit` caps the number of entries, `--tm` adds translation-
memory evidence, and `--dry-run` reports the selection and estimate without
writing.

The command refuses a language when a proposer or judge release is not
qualified or when the language is paused for drift.

Plural entries are translated as a complete form set when the catalog header
declares `nplurals` and `msgstr_plural` has that many forms. Each proposer
returns all forms in one indexed response (`0: ...`, `1: ...`); every form
passes the deterministic checks, and the judge compares complete sets. A
sentence form is back-translated like a singular sentence. A missing header or
a form-count mismatch is reported as unsupported, as are context (`msgctxt`)
entries; both are left unchanged.

`machine-strong` is accepted for high-impact menu and destructive strings;
the batch does not add a separate human-review gate.

### High-impact strings

Menu actions, destructive verbs and data-loss error messages need human-origin
evidence or a `machine-strong` approval. Human-origin evidence is unchanged
pre-2026 text, a mechanical rebase, a dominant cross-project match, or
English/German review. Without it the string remains English.

A translation-memory match alone never approves a string. It contributes
evidence, and only with the remaining gate evidence may the class be
`tm-consensus`.

### Generating the gate config from OpenCode

OpenCode already carries provider URLs, model families, release dates, token
limits and prices. Import them instead of typing the gate config:

```sh
python3 dev/sync_translation_gate.py \
    --opencode ~/.config/opencode/opencode.jsonc \
    --roles po/translation-gate.roles.json \
    --dry-run
```

Drop `--dry-run` to write `po/translation-gate.json`. The importer supports
V2 `providers` and legacy `provider`, JSON and JSONC, and only imports
OpenAI-compatible packages. It validates the result with the gate loader
before writing.

The OpenCode config lists only providers you added. Import the resolved
catalog, including the default `opencode` models, with:

```sh
python3 dev/sync_translation_gate.py \
    --from-api \
    --roles po/translation-gate.roles.json \
    --dry-run
```

That calls `opencode api get` for `/api/model`, `/api/provider` and
`/api/integration/<id>`. The command reads only the local API, so it does not
need a provider key. For offline review or tests, save the responses and pass
them explicitly:

```sh
python3 dev/sync_translation_gate.py \
    --from-api \
    --models-json models.json \
    --providers-json providers.json \
    --integrations-json integrations/ \
    --roles po/translation-gate.roles.json \
    --dry-run
```

The API source maps:

| OpenCode API | Gate |
| --- | --- |
| `providerID` | deployment `provider` |
| `env` name from integration | deployment `key_env` |
| `settings.baseURL` | deployment `endpoint` and chat path |
| model id, or `modelID` | release `model` and deployment model id |
| model `family` | release `family` for independence |
| `time.released` | release `revision` as an ISO date |
| model `cost` | deployment base price and context tiers |
| model `limit` | deployment `limits` |
| provider/model `headers` | deployment `headers` |

Only OpenAI-compatible chat packages are imported. Responses/native packages
are skipped because the gate client uses `/chat/completions`.

Credentials come from the integration's environment method, for example
`OPENCODE_API_KEY`. A provider that offers only OAuth is skipped; use
`--key-env provider=ENV` to supply a key variable explicitly. No key value is
read or copied.

Provider metadata headers such as `x-opencode-org-id` are stored in the local
config and sent with each request. `Authorization`, proxy authorization and
cookie headers are never copied.

The config-file source remains available:

```sh
python3 dev/sync_translation_gate.py \
    --opencode ~/.config/opencode/opencode.jsonc \
    --roles po/translation-gate.roles.json \
    --dry-run
```

Both sources preserve `thresholds`, `quantization`, `prompt_hash`, `decoding`
and unknown top-level keys. `--force` replaces the deployment fields. The
mapping is:

| OpenCode config | Gate |
| --- | --- |
| provider id | deployment `provider` |
| `env[0]` | deployment `key_env` |
| `api` or `settings.baseURL` | deployment `endpoint` and chat path |
| model map key, or `modelID` | release `model` and deployment model id |
| model `family` | release `family` for independence |
| model `releaseDate` | release `revision` |
| model `cost` | deployment `cost` |
| model `limit` | deployment `limits` |

The OpenCode config does not say which model proposes or judges, so the role
policy is separate. For example:

```json
{
  "proposers": [
    "opencode/deepseek-v4.1-flash",
    "opencode/qwen3.8-27b"
  ],
  "judge": "opencode/glm-5.3"
}
```

A normal import preserves `thresholds`, `quantization`, `prompt_hash`,
`decoding` and unknown top-level keys. `--force` replaces the deployment
fields. The importer never copies a literal `apiKey` or authorization header;
a provider without an environment variable name is skipped. The `env` array
holds variable names, never values.

### Cost and performance

Each deployment may carry per-million-token prices and token limits:

```json
"cost": {
  "currency": "USD",
  "unit": "per_million_tokens",
  "input": 0.6,
  "output": 3.3,
  "cache_read": 0.12,
  "cache_write": null,
  "tiers": [
    {
      "context": 272000,
      "input": 4.0,
      "output": 15.0,
      "cache_read": 0.2,
      "cache_write": 5.0
    }
  ]
},
"limits": {
  "context": 256000,
  "output": 32768
}
```

The base price applies below the first tier. A prompt above a tier's context
size uses that tier's prices, and the selected tier is recorded with the call.

Every model call records the provider's usage, latency and computed cost in
the ledger. A call with no usage or no price is recorded as unknown, never as
free. `gate_runs` also records abstentions, so a model that mostly abstains
cannot look cheap.

Compare models with:

```sh
python3 dev/translation_gate.py costs
python3 dev/translation_gate.py costs --language de --json
```

The report groups calls by language and deployment and shows spend, tokens,
approval rate, cost per approval, qualification and drift scores, and the
observed defect rate.

Estimate an action before spending:

```sh
python3 dev/translation_gate.py estimate --action qualification \
    --release qwen/3.8@2026-09 --language de
python3 dev/translation_gate.py estimate --action drift \
    --deployment qwen-a --language de
python3 dev/translation_gate.py estimate --action gate \
    --language de --msgid "Delete" --msgid "Open file: %s"
```

The estimate uses a configurable `chars_per_token` heuristic (default 4) and
the model's output limit, reports a low/high range per deployment, and states
that provider-reported usage after the call is authoritative. Add
`--max-cost` to the gate action or to an estimate to stop before any request:

```sh
python3 dev/translation_gate.py gate --language de --msgid "Delete" \
    --max-cost 0.05
```

## Release build

Packaging compiles only approved entries and writes a coverage report:

```sh
python3 dev/compile_mo.py \
    --src po/scantpaper \
    --out src/scantpaper/locale \
    --domain scantpaper \
    --approvals po/approvals \
    --pot po/scantpaper/scantpaper.pot \
    --report translation-report.json
```

The report gives, per language, approved entries, English fallbacks, and
missing/stale counts. Without `--approvals`, every non-fuzzy entry compiles,
which is useful for a local preview only.

To preview locally:

```sh
python3 dev/compile_mo.py --src po/scantpaper \
    --out src/scantpaper/locale --domain scantpaper
PYTHONPATH=src python3 -m scantpaper.app --log=log --locale=locale
```

Set locale variables as needed, e.g. for Russian:

```sh
LC_ALL=ru_RU.utf8 LC_MESSAGES=ru_RU.utf8 LC_CTYPE=ru_RU.utf8 \
LANG=ru_RU.utf8 LANGUAGE=ru_RU.utf8 PYTHONPATH=src \
python3 -m scantpaper.app --log=log --locale=locale
```

## Checking for upstream translations

```sh
python3 dev/check_launchpad.py
```

This reports whether the template or any language has moved on Launchpad
since the committed baseline `po/launchpad-state.json`, and whether the local
template is stale relative to the last pot uploaded. It is advisory and never
downloads a catalog. Use `--fail-on-change` to make a detected change
non-zero, and:

```sh
python3 dev/check_launchpad.py --update
python3 dev/check_launchpad.py --record-pot
```

The scheduled `translations-check` workflow runs the same check daily.

## CI and credentials

CI runs only deterministic checks. It never authenticates to Launchpad, never
downloads a catalog, and never needs a model credential. Rosetta export and
model calls are maintainer-run. Keys come from the environment, never from the
repository.

## Current state

The committed ledger has 9,922 approvals: 9,908 `human-historical` and 14
`in-project-rebase`. Another 4,241 entries are pending, mostly model-added or
model-changed text with no approval, so they fall back to English in a release
build.

No model release is currently qualified for future work; the capability
report names all 44 languages as having no machine path until a release is
qualified and a deployment conformed.

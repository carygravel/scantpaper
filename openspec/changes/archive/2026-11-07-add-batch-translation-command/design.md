# Design

## Context

See `proposal.md` - Why.

The gate already has everything needed for one entry:

- `run_gate()` returns a `GateDecision` with the approved translation, the
  approval record and the call evidence.
- `record_gate_run()` appends the decision to the ledger's `gate_runs`.
- `approve_decision()` clears the fuzzy flag and records the approval, but it
  does not write the decision translation into `msgstr`.
- `GateOptions` carries `occurrences` and `tm_db`, but the `gate` CLI passes
  only `context`.
- `_qualified()` and `is_paused()` expose the qualification and drift state.
- `estimate_gate()` prices one or more sources, and `ensure_budget()` refuses
  an over-budget action.

The first catalogs are `en_GB`, `en_US` and `de`; there is no `en.po`. After
`merge_po.py`, each has 131 new fuzzy entries with an empty `msgstr`. The
template also has two plural entries and no contexts.

## Goals / Non-Goals

**Goals:**

- Fill empty catalog entries from the gate in one repeatable command.
- Write the approved text, not just clear fuzzy.
- Refuse an unqualified or paused language before spending.
- Enforce a total budget and remain resumable.
- Keep high-impact detection and translation-memory evidence intact.

**Non-Goals:**

- Translating plural forms or entries with a `msgctxt`.
- Automatically qualifying a release or running a drift probe.
- Changing the gate's evidence rules or the `machine-strong` policy.
- Adding Wikipedia or Wikidata sources to the translation memory.

## Decisions

### A `translate` subcommand

`translate` reads a catalog and applies the gate to its missing entries. A
separate command keeps `gate` single-string and lets the batch own selection,
budget and reporting. The alternative, a loop in a shell script around
`gate`/`approve`, would not fix the empty-entry write, the qualification
guard or the total budget.

### Selection

By default the command selects non-obsolete entries whose `msgstr` and
`msgstr_plural` are empty. That is the state `merge_po.py` leaves a new
template msgid in. `--include-fuzzy` also selects entries that already carry a
non-empty fuzzy proposal; this is opt-in because it replaces a proposal.
Entries with a non-fuzzy translation are skipped. Selection is deterministic:
sort by `(msgctxt or "", msgid)`, then apply `--limit`.

Entries with a `msgctxt` or `msgid_plural` are reported as unsupported and are
not selected. The current template has no contexts and two plural entries;
leaving one missing plural is a known limitation, not a silent skip.

### Write the approved text

A shared `apply_decision(catalog, ledger, entry, decision)` helper:

1. rejects a decision without a translation;
2. sets `entry.msgstr` to the decision translation;
3. removes the fuzzy flag;
4. records the approval in the ledger;
5. leaves the caller to persist the ledger and catalog.

`approve_decision()` is reworked to use the helper, so the single-string
`approve` command also fills an empty entry. The batch uses the same helper
against the catalog it already loaded.

The ledger is written before the catalog. If the catalog save fails, an
approval exists for a still-fuzzy entry; the release falls back to English and
a re-run can apply it. The reverse order could leave a non-fuzzy entry with no
approval, which would silently lose the audit trail.

### Qualification and drift guards

The handler loads the role policy, validates it, and checks every proposer and
judge release with `_qualified(ledger, release, language)`. It also checks
`is_paused(ledger, release, language)`. A real run refuses with the missing
release names and the `qualify`/`drift` command that resolves them. A dry run
reports the same blockers but makes no call.

The `gate` command still does not enforce qualification; the batch does. That
keeps the new production path safe without changing the existing single-string
behaviour.

### Budget

The handler estimates the whole selection with `estimate_gate()` and calls
`ensure_budget()` before the first request. It also estimates each entry and
tracks the actual cost from the decision's calls. Before an entry, if the
spent amount plus that entry's high estimate exceeds `--max-cost`, it stops
and reports the remaining entries as fuzzy. A pre-flight over-budget refusal
exits non-zero; a mid-run stop is a completed partial batch and exits zero
with a `stopped: budget` report.

The estimate assumes the configured `chars_per_token` and the deployment's
output limit; the provider-reported cost after each call is authoritative.

### Occurrences, TM and high-impact strings

The gate is called with:

```python
GateOptions(
    context=entry.msgctxt or "",
    occurrences=entry.occurrences,
    tm_db=args.tm,
)
```

Passing occurrences makes `is_high_impact()` see menu and dialog locations.
The project accepts `machine-strong` for high-impact menu and destructive
strings, so the batch does not add a separate human-review gate; it relies on
the existing evidence ladder. `--tm` enables `tm-consensus` when the index is
available, but it is optional.

### Dry run, output and exit status

A dry run selects entries, applies the guards, prices the batch and prints the
selection, skips and blockers. It writes nothing and makes no model call; a
blocked dry run exits zero with `ready: false`.

A real batch prints one line per entry and a final summary. `--json` prints
the per-entry outcomes, counts, spend and `stopped` reason. It exits zero when
the batch completes, even with abstentions or a budget stop, and non-zero on
an unqualified/paused precondition, an unreadable catalog, a missing
credential, a pre-flight budget refusal or a write failure.

### First targets

There is no `en.po`; the English catalogs are `en_GB` and `en_US`. The first
runs are `en_GB` and `de`, with `en_US` following the same path. The command is
language-agnostic; the first targets live in the documentation, not in code.

## Risks / Trade-offs

- **Partial write** -> the ledger is written before the catalog; a failure
  leaves a fuzzy entry with an approval, which is safe and re-runnable.
- **Small evidence** -> `machine-strong` can approve a high-impact string
  without human review, per project policy. The classification still requires
  two independent families, a third judge, deterministic checks and
  back-translation.
- **Plural/context gap** -> two plural entries and no contexts are affected
  today. The report names them; a follow-up can add plural support.
- **Cost drift** -> the pre-estimate uses a character heuristic; the actual
  provider cost is recorded and the batch checks it against the cap.
- **Rate limits** -> a failed request stops the batch; re-running skips
  non-fuzzy entries and continues. No retry/backoff is added in this change.
- **Approval overwrite** -> `--include-fuzzy` deliberately replaces an
  existing proposal; it is off by default.

## Migration Plan

No migration. The command is additive and the catalog/ledger formats already
support the write and the approval. Rollback is removing the subparser and the
apply helper; catalog edits made by a run remain valid.

## Open Questions

None.

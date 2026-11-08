# Design

## Context

See `proposal.md` - Why.

`dev/translation_gate.py` currently treats a translation as one string:
`prompt_for("translate", ...)` asks for one answer, `deterministic_checks`
compares one source to one translation, `blind_judge` ranks single texts, and
`_apply_decision` writes `entry.msgstr`. `_select_batch_entries` explicitly
rejects every `msgid_plural`.

The rest of the stack is already plural-ready: `make_record` and
`translation_digest` accept `msgstr_plural`, `approval_for_entry` and
`validate_against_catalog` handle plural approvals, `compile_mo` compiles the
forms, and `check_po.py` already parses `nplurals` and validates plural bodies.

## Goals / Non-Goals

**Goals:**

- Make a plural entry batch-eligible when its catalog declares its form count.
- Ask for, check, judge, back-translate and apply a complete form set.
- Keep every singular path and every existing approval unchanged.
- Keep the budget estimate honest for multi-form output.

**Non-Goals:**

- Supporting `msgctxt` entries.
- Extending the drift probe, qualification baseline or capability report to
  plural forms. They continue to exercise the singular path.
- Adding CLDR category names for languages with more than two forms. The first
  version uses indices plus the catalog's own `plural=` expression.
- Changing the qualification tolerance, judge thresholds or provenance classes.

## Decisions

### One call per entry for the whole form set

Each proposer receives both source forms and the declared count, and returns
all forms in one response. This keeps the forms grammatically coherent and
costs one proposal per entry instead of one per form.

Alternative: one call per form. Rejected because the model cannot see the
other forms, consistency is left to chance, and a three-form language triples
the proposal count and judge work.

### Strict structured parsing

The response is parsed into a mapping from form index to text. A response is
usable only when it has exactly `nplurals` indices, each non-empty and in
range. A missing, extra or duplicated index fails that proposer's proposal;
it does not fall back to positional guessing.

The prompt includes the catalog's `Plural-Forms: plural=...` expression so a
model can tell which counts map to which form, without the gate shipping a
CLDR category table.

### A separate plural prompt version

`PROMPT_VERSION` and `PROMPT_HASH` describe the singular prompt; both stay
unchanged. A new `PLURAL_PROMPT_VERSION` (and hash) describes the plural
template, and the evidence records `plural_prompt_version`.

Alternative: bump the shared prompt version. Rejected because it would imply
that every existing singular qualification and conformance was produced by a
different prompt, forcing a re-qualification for no behavioral reason. The
plural prompt is a new action, not a change to the serving configuration of
the singular action.

### Check and judge the set, not loose strings

`deterministic_checks` runs once per form, comparing placeholders and format
fields against the source set. A proposal passes only if every form passes.
The judge sees each proposal as an ordered block (`A: 0: ... 1: ...`) and
chooses one complete set. The identical-proposal tie compares the tuple of
forms.

Alternative: judge each form independently. Rejected because it can select
form 0 from one model and form 1 from another, producing an inconsistent set.

### Back-translate every sentence form

A form whose source is a sentence is back-translated and compared with its
source. Any meaning change blocks the whole set. Short labels and form-only
strings keep the existing no-back-translation behavior.

### Apply to `msgstr_plural`

`_apply_decision` writes `entry.msgstr_plural` and leaves `entry.msgstr`
empty for a plural entry. `_entry_for` accepts the plural source and the form
mapping so the approval key and digest cover the whole set. `make_record`
normalizes polib's integer form keys to strings before the ledger validates
the record.

### Estimate from the declared form count

`estimate_gate` adds the plural source to the prompt and scales the expected
output by the form count. The budget loop still treats an entry as one gated
unit.

## Risks / Trade-offs

- **A model returns the wrong number of forms** → strict parsing rejects the
  proposal and the entry abstains rather than writing a partial set.
- **Index-only prompts are ambiguous for 3-6 form languages** → the prompt
  carries the catalog's `plural=` expression; category names are a later
  addition if the index proves insufficient.
- **Longer outputs raise cost and latency** → the estimate scales with the
  form count, and the existing budget stop applies per entry.
- **Plural drift is not probed** → the existing singular drift probe still
  gates new approvals; plural-specific strata stay a follow-up.
- **A plural entry has a malformed `msgstr_plural`** → it is reported as
  unsupported and left unchanged, never guessed.

## Migration Plan

No data migration. Existing singular approvals and catalogs are untouched.
The first plural batch writes ordinary `msgstr_plural` text and ordinary
plural approvals, which the current compiler and ledger already validate.
Rollback is a code revert; no catalog needs restoring unless a plural batch
was actually run.

## Open Questions

None.

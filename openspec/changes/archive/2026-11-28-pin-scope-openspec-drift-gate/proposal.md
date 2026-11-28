# Proposal

## Why

The drift gate added in `4211066c` fails on every clean runner. The CLI reports
its global configuration as `~/.config/openspec/config.json`; the containment
check in `dev/check_generated_instructions.py` does not expand `~`, so the path
is joined to the repository root and the gate reports a file "inside" it. CI
is red while the tracked instruction files are correct, and the archived
spec's scenario "The global configuration is ignored" is violated.

The gate also never reads `dev/openspec-version`, although its message says
"behind the pinned CLI". It measures whatever `openspec` is on `PATH`. That
gives a false red on a machine with an older CLI (2.0.0 here against a 2.2.0
pin), a false green after `openspec update` runs with that older CLI, and a
deadlock in the scheduled check: the gate is replayed against a candidate
release, so every future bump that changes generated files would be reported
"blocked", with instructions that say not to bump until the gate passes.

## What Changes

- **Fix the path check first.** Expand `~` before deciding whether a planned
  path is absolute or repository-relative, and cover a tilde path with an
  isolated `HOME`. This is the trivial bug fix and lands before the rest.
- **Pin-scope the gate.** Read `dev/openspec-version` and compare it with
  `openspec --version`. When they differ, report "cannot judge" (exit 2) and
  name both versions, instead of a stale or current verdict.
- **Stop treating the gate as a candidate validation.** Remove it from
  `DEFAULT_VALIDATE_COMMANDS` and render it in the adoption block after
  `openspec update`, so the scheduled check no longer evaluates a pin-relative
  property against a candidate release. It stays a push gate in `test.yml`.
- **State the split in the spec.** Candidate validation covers the candidate's
  own rules; the generated-file check is verified after adoption, against the
  pin.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `openspec-cli-version`: the generated-files requirement gains the pin
  identity check, the home-relative path rule, and the "cannot judge" outcome;
  the candidate-validation requirement distinguishes candidate validation from
  post-adoption verification.

## Impact

- `dev/check_generated_instructions.py` and
  `dev/tests/test_generated_instructions.py`: `expanduser`, a pin comparison,
  a new exit-2 state, and version-aware stubs.
- `dev/check_openspec.py` and `dev/tests/test_openspec.py`: `ADOPT_COMMANDS`
  gains the gate, `DEFAULT_VALIDATE_COMMANDS` loses it, and the ordering test
  covers the refresh-then-verify sequence.
- `openspec/specs/openspec-cli-version/spec.md` via the delta.
- `AGENTS.md`: the bump procedure says the gate requires the pinned CLI.
- No application code, dependency, data model or user-visible change.

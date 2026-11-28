# Design

## Context

See `proposal.md` - Why. The facts that shape the approach, all measured on
the current tree:

- `.opencode/commands/opsx-*.md` and `.opencode/skills/**` are marked
  `generatedBy: "1.10.0"` and dated 2026-10-03. The pin is 2.2.0.
- `openspec update --dry-run --json` under 2.2.0 plans 24 changes: add
  `.agents/skills/**` (12 files), delete the 6 `.opencode/commands` files and
  the 6 `.opencode/skills` files, and update the CLI's global config.
- `.agents/skills/.openspec-target` records `opencode`, which is what makes
  the tool set stable across machines.
- After the refresh, a second dry run reports **zero** changes when the global
  config already exists, and exactly **one** change when it does not - an
  entry whose path is outside the repository, the CLI's own
  `$XDG_CONFIG_HOME/openspec/config.json`.
- `.opencode/.gitignore` ignores `node_modules`, `package.json`,
  `package-lock.json`, `bun.lock` and itself; the `commands/` and `skills/`
  directories are not ignored, they were simply never added to git.
- Generating for extra workflows is a global preference: the CLI's config
  records `profile: core` and the six workflow names this repository uses.

## Goals / Non-Goals

**Goals:**

- The instruction files the pinned CLI generates are part of the repository,
  so a bump that forgets them is visible and reviewable.
- CI fails on that drift, naming each repository file that would change.
- The adoption instructions the scheduled check writes name the refresh step.

**Non-Goals:**

- Pinning the CLI's global profile or workflow list. Those are machine
  preferences, and the tool pin already lives in `.openspec-target`.
- Generating instruction files for agent tools this repository does not use
  (`.claude/` stays a local matter).
- Changing how a release is validated; the existing validation commands keep
  their meaning and must stay non-mutating.

## Decisions

### D1 - Track `.agents/skills/**`, not `.opencode/**`

That is the layout 2.2.0 generates, and `.openspec-target` already pins the
tool as `opencode`, so nothing is lost. Keeping `.opencode/commands` would
mean pinning an obsolete layout and a gate that can never be green.

Consequence: `openspec update` deletes `opsx-apply.md` and its siblings, so
the slash commands become skills. `AGENTS.md` already refers to them as
skills, and the migration is verified before it is committed.

Consequence: `test_markdown_line_length` excludes `.agents` alongside
`.opencode`. That test guards lintian's 512-character limit on files the
source package ships, and these files are neither shipped nor hand-editable -
the CLI writes their lines verbatim, so wrapping one would make the drift gate
fail on every run. Excluding them keeps the two gates from contradicting each
other; the markdown the repository does author stays covered.

### D2 - The drift gate is a tested `dev/` script

`dev/check_generated_instructions.py` runs
`openspec update --dry-run --json`, keeps the planned changes whose path is
inside the repository, and exits non-zero naming them. It takes the CLI
command and the repository root as options, so tests substitute a stub and
fixtures, exactly like `dev/check_change_archive.py`.

- Alternative: `test -z "$(openspec update --dry-run --json)"` in the
  workflow. Rejected - that is non-empty even on a clean runner, because of
  the global config entry, so it fails the build for the wrong reason.
- Alternative: compare a committed manifest of expected files. Rejected -
  a new CLI release legitimately adds files, and the manifest would need its
  own bump.

### D3 - Filter by path containment, never by tool or action

The global config entry carries `tool: "openspec"`, the same value as the
repository's additions, so filtering on `tool` is wrong; filtering on `action`
is wrong for the same reason. Only "is this path inside the repository
root" answers the question the gate is asking. Both relative and absolute
paths are resolved before comparison, because the CLI emits both.

### D4 - Do not pin the global profile

The marker file pins the tool; the workflow list is a preference. A developer
who enables the six extra workflows generates extra files, commits them, and
CI under `core` does not report them as deletions - verified. The gate
therefore catches staleness of the files it knows about, which is the failure
that happened here.

### D5 - The refresh step is an adoption step, not a validation command

`openspec update` writes files, and the existing spec requires a candidate
validation to leave the repository untouched. So it must not go into
`DEFAULT_VALIDATE_COMMANDS`. A second recorded constant,
`ADOPT_COMMANDS`, holds the steps that are part of adopting a release but not
part of validating one, and the issue body renders from it. The drift gate
itself *is* a validation command - it only reads - so it joins
`DEFAULT_VALIDATE_COMMANDS` and the scheduled check replays it against a
candidate release.

### D6 - Rollout order

Refresh and commit the generated files first, then add the gate. Landing the
gate first would fail on its own first run, and the gate cannot see a tree
that has not been migrated.

## Risks / Trade-offs

- [`openspec update` deletes the `/opsx-*` slash commands] -> Verify the
  skills are discoverable after the migration before committing; the deleted
  directory is a local backup if the tool turns out not to read
  `.agents/skills`.
- [~14 generated files change on every bump] -> That is the point: the diff is
  reviewed with the pin that caused it, instead of accumulating unseen.
- [A developer with extra workflows enabled commits files CI does not
  generate] -> Accepted; the gate does not treat unknown files as drift, and
  a maintainer who enables extra workflows knows they are adding files.
- [Windows checkouts could rewrite line endings in the generated files] ->
  The files are generated by Node with LF; if a Windows contribution appears,
  add a `.gitattributes` rule for `.agents/skills/**`.
- [The gate runs the CLI with `--dry-run`, which could still touch the global
  config on some version] -> The script compares the repository only and never
  reads the global config, so such a write cannot turn the gate green or red.

## Migration Plan

1. Run `openspec update` with the pinned CLI; confirm it reports the same 24
   changes the dry run described.
2. Confirm the skills are discoverable and that all four CI commands pass.
3. Commit `.agents/skills/**` and the removal of `.opencode/{commands,skills}`.
4. Add `dev/check_generated_instructions.py`, its tests, the workflow step,
   the `ADOPT_COMMANDS` constant, and the `AGENTS.md` paragraph.
5. Confirm the gate reports no changes on the committed tree.
6. Rollback is restoring `.opencode` and deleting `.agents`; the gate step is
   independent and can be dropped on its own.

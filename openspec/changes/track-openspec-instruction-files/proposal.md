# Proposal

## Why

The OpenSpec CLI pin has moved six times, from 1.16.0 to 2.2.0, but the
instruction files the CLI generates for this repository have not been refreshed
once: every file under `.opencode/commands/` and `.opencode/skills/` is marked
`generatedBy: "1.10.0"` and dated 2026-10-03, older than the first bump. The
issue the scheduled check files says how to write the pin and install the
release, but never mentions `openspec update`, and because those files are not
tracked by git, no gate can see that they are stale.

The cost is not cosmetic. The shipped apply, archive and explore skills differ
from the repository's copies by 37, 83 and 181 changed lines respectively - the
current archive skill counts tasks through `openspec list --json` instead of
reading `tasks.md`, and handles a project root that is not set up. Those are
exactly the steps a hand-run checklist misses.

## What Changes

- **Refresh the generated files and adopt the current layout.**
  **BREAKING** for the developer's workflow: `openspec update` under 2.2.0
  deletes `.opencode/commands/opsx-*.md` and `.opencode/skills/**` and writes
  the same workflows to `.agents/skills/**`. The slash commands therefore
  become skills, which is how `AGENTS.md` already refers to them.
- **Track the generated instruction files.** Commit `.agents/skills/**` so the
  files the CLI generates are part of the repository, while the dependency
  manifests that `.opencode/.gitignore` already covers stay ignored.
- **Gate the drift.** Add a CI step that fails when
  `openspec update --dry-run --json` reports any planned change, so a pin bump
  that leaves the generated files behind cannot pass. This is the same rule the
  change archive now enforces for specs: the artefact and the thing it
  describes move together.
- **Tell the adopter.** Add `openspec update` to the "To adopt it" block in
  `dev/check_openspec.py` and to the bump procedure in `AGENTS.md`, and extend
  the existing workflow-drift test to cover it.

The gate is only meaningful once the files are tracked; until then a clean
checkout reports all of them as additions and every run would fail.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `openspec-cli-version`: adopting a release now also refreshes the generated
  instruction files in the same commit, and CI fails while those files differ
  from what the pinned CLI would write.

## Impact

- `.agents/skills/**` (new, tracked), `.opencode/{commands,skills}` (removed),
  `.opencode/.gitignore`.
- `dev/check_openspec.py` and `dev/tests/test_openspec.py`: the adoption
  instructions gain the refresh command and the test that guards them.
- `.github/workflows/test.yml`: the drift gate, in the jobs that install the
  CLI.
- `AGENTS.md`: the bump procedure and the gate.
- `openspec/specs/openspec-cli-version/spec.md`: one added requirement.
- No application code, dependency or data-model change, and no change to what
  a scantpaper user sees.

One thing the design must settle: `openspec update` generates files for the
tools the machine is configured for, so the CI gate is only deterministic if
the tool set is the same in CI as in a developer's checkout. If it cannot be
pinned, the gate has to run only when it can prove the set.

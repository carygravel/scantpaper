# Proposal

## Why

`dev/build_ppa.py` prints a `Next steps:` header and one `dput` command
immediately after each series finishes. With `--all`, those blocks are
interleaved with the per-series "built" lines, so the commands end up
scattered across the output and cannot be copied as one block. The tool
should collect every remaining command and print it once, after the selected
series have been processed.

## What Changes

- The PPA tool collects the `.changes` path for each successfully prepared
  or built series instead of printing `Next steps:` inside the per-series
  loop.
- After the loop it prints a single `Next steps:` block with one
  `dput <target> <changes>` line per series, in selection order.
- If a later series fails, the commands for series that finished before the
  failure are still printed, the failing series is omitted, and the process
  still exits non-zero with the existing error on stderr.
- If no series finishes, no `Next steps:` block is printed.
- `--dry-run` gets the same single block; its predicted `.changes` paths are
  collected exactly as today.
- Per-series progress lines (`<series>: built ...` / `prepared ...`), the
  exit status, signing, and the rule that `dput` is printed but never run are
  unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `packaging-release`: the PPA tool's next-steps output is consolidated into
  one block, and commands for series that completed before a mid-run failure
  are still printed.

## Impact

- `dev/build_ppa.py`: the reporting path that collects and prints the
  remaining commands.
- `dev/tests/test_build_ppa.py`: coverage for one header across several
  series, selection order, and partial-failure output.
- `release_procedure.md`: optional wording update to say the commands are
  printed together at the end (`README.md` does not document this tool).
- No new dependencies, no change to the suite matrix, packaging files, or
  upload steps.

# Tasks

## 1. Sign in the build

- [x] 1.1 Run `debuild -S -sa` without `-us -uc` in `_build`, remove
  `debsign` from `_print_commands`, and update the module docstring; verify a
  dry run prints only `dput`
- [x] 1.2 Add a fake `debuild` first in `PATH` that records its arguments and
  creates the expected `.changes`, and a test asserting `-S -sa` was used,
  `-us`/`-uc` were not, and no `debsign` is printed; verify it passes with no
  GPG key available
- [x] 1.3 Update the Ubuntu step in `release_procedure.md` to say the tool
  signs each source package and only `dput` is left to the maintainer; verify
  the documented commands match the tool output

## 2. Verification

- [x] 2.1 Run `pytest`, `ruff format --check`, `ruff check` and `ty check .`;
  verify all pass and coverage stays at or above the gate

## Workflow follow-up

- Run the PPA tool on the next release with an unlocked signing key and
  confirm the uploaded sources are signed.
- Sync and archive the change after the project's review requirements.

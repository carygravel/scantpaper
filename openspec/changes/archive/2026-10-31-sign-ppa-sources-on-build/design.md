# Design

## Context

See `proposal.md` - Why. `debuild -S -sa` already signs in the Debian step;
`dev/build_ppa.py` currently passes `-us -uc` and prints `debsign`. gpg-agent
supplies the passphrase when it is unlocked.

## Goals / Non-Goals

**Goals:**

- Sign every series' `.dsc` and `.changes` while building it.
- Keep the tests runnable without a GPG key.
- Keep the upload printed and manual.

**Non-Goals:**

- Choosing or configuring a signing key; the changelog signer and the user's
  GPG setup decide that.
- Uploading, committing, tagging or pushing.
- Changing the source package contents.

## Decisions

### Decision: sign through `debuild`, not a separate `debsign`

`_build` runs `debuild -S -sa` without `-us`/`-uc`, so signing happens in the
same step as the build and a signing failure fails the series before any
`dput` line is printed. A separate `debsign` call would add a second command
and a second failure mode for the same outcome.

The consequence is that the tool now needs a usable key and passphrase. That
is the point of the change; `dput` would reject an unsigned upload anyway.

### Decision: test with a fake `debuild` on `PATH`

The tests run the tool as a subprocess, so the signing step is replaced by a
small executable placed first in `PATH`. It records its arguments to a file and
creates `../scantpaper_<version>_source.changes`, which is all the tool needs
to continue. The test asserts `-S -sa` was passed, `-us`/`-uc` were not, and
only `dput` is printed. Dry-run tests never invoke it.

This keeps CI independent of any GPG key while still exercising the build
branch, including the `.changes` discovery and tree removal.

## Risks / Trade-offs

- [Non-interactive runs fail at signing] -> Expected; a signing step needs a
  key. Run it in a terminal or with an unlocked agent.
- [The changelog signer has no matching key] -> `debuild` fails with its own
  message, and the tool reports the build output.
- [A fake `debuild` could hide a real command change] -> The test records and
  asserts the exact flags, so a change to the invocation is caught.

## Migration Plan

1. Change the build command and the printed commands; update the procedure.
2. Add the fake-`debuild` test and adjust the dry-run assertion.
3. Run the gates. Rollback is a revert; the next run returns to printing
   `debsign`.

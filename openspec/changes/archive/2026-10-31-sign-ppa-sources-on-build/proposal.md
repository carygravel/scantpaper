# Proposal

## Why

The PPA step still stops and prints `debsign` for every series, so signing is
one more manual step per source package, after the build, and easy to skip or
run in the wrong order. The Debian step already signs as part of
`debuild -S -sa`, and the PPA tool can do the same: signing belongs to building
the source package, while uploading stays deliberate.

## What Changes

- `dev/build_ppa.py` builds each series with `debuild -S -sa`, letting
  dpkg/debsign use the changelog signer and gpg-agent, instead of
  `-us -uc`. It prints only the `dput` command; the docstring and the procedure
  no longer mention `debsign`.
- The tests use a fake `debuild` placed first in `PATH` that records its
  arguments and creates the expected `.changes`, so no GPG key is needed in
  CI. A test asserts that signing is enabled and that no `debsign` command is
  printed.
- `release_procedure.md`: the Ubuntu block says the tool signs each source
  package and only asks the maintainer to `dput` it.
- `packaging-release`: the requirement that signing and uploads stay manual is
  replaced by one where signing happens in the build and only the upload is
  manual.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `packaging-release`: the PPA build signs each source package and prints only
  `dput`; commit, tag, push and upload stay manual.

## Impact

- `dev/build_ppa.py`, `src/scantpaper/tests/test_build_ppa.py`,
  `release_procedure.md`.
- Running the PPA tool now needs a usable GPG key and passphrase (or an
  unlocked agent); a non-interactive run without one fails at signing, as
  intended.
- No change to the application, packaging content, suite matrix, or uploads.

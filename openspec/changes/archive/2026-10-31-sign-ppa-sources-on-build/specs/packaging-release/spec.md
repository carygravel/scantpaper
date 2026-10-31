# Spec Delta

## REMOVED Requirements

### Requirement: Signing and uploads stay manual

**Reason**: Signing moves into the PPA build, so only the upload stays manual.

**Migration**: Run `dev/build_ppa.py` with an unlocked signing key. It signs
each source package as it builds it and prints only `dput`.

## ADDED Requirements

### Requirement: Signing happens in the build; uploads stay manual

The sync tool SHALL NOT commit, tag, push or upload. The PPA tool SHALL sign
each source package as part of its build and SHALL NOT upload it. Both SHALL
print the remaining commands for the maintainer to run.

#### Scenario: Sync stops before history

- **WHEN** the sync has written `debian/` and the changelog draft
- **THEN** it prints the build, test, commit and upload commands and creates no
  commit or tag

#### Scenario: PPA sources are signed and not uploaded

- **WHEN** the PPA tool has built a source package
- **THEN** its `.dsc` and `.changes` are signed, nothing has been uploaded, and
  the tool prints only `dput`

#### Scenario: Signing failure stops the build

- **WHEN** signing fails, for example because no usable key or passphrase is
  available
- **THEN** the build fails and no `dput` command is printed for that series

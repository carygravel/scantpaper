## ADDED Requirements

### Requirement: Local message template staleness is detected against a baseline
The check SHALL also report when the locally generated message template (the
`.pot` regenerated from source) has moved relative to the message set of the
last pot uploaded to Launchpad, so the maintainer knows a new pot is ready to
push up. This is the reverse of the existing upstream-change check, and SHALL
be answered entirely from local state: the baseline records the fingerprint of
the last uploaded pot, and the check compares the freshly generated message set
against that fingerprint. It SHALL NOT attempt to read the pot's message set
from Launchpad, which would require authentication.

The fingerprint SHALL be derived from the message set only: the sorted, unique
`msgid` strings extracted from the generated template, ignoring the template's
volatile header (creation date, package version) and the `#: file:line`
reference comments. A difference that leaves the message set unchanged — for
example a string moved between source files, or a different gettext version
reordering output — SHALL NOT count as a change.

The baseline SHALL record the fingerprint of the last uploaded pot, and SHALL
be advanced only by a distinct, explicit stamping action taken after a pot has
actually been uploaded, mirroring the upstream `--update` action. When no pot
has been recorded yet, the check SHALL report the local state as not
determined rather than as unchanged.

#### Scenario: New source strings are ready to upload
- **WHEN** the locally generated message set contains an `msgid` that is
  absent from the recorded uploaded-pot fingerprint
- **THEN** the check reports that the local template is stale, names the
  change, and exits successfully

#### Scenario: Only line references moved
- **WHEN** a string is moved between source files so its `#: file:line`
  reference changes but the set of `msgid` strings is unchanged
- **THEN** the check reports no local template change

#### Scenario: Only volatile headers changed
- **WHEN** regenerating the template changes its creation date or package
  version header but the set of `msgid` strings is unchanged
- **THEN** the check reports no local template change

#### Scenario: Reordering is ignored
- **WHEN** a different gettext version emits the same `msgid` set in a
  different order
- **THEN** the check reports no local template change, because the sorted
  fingerprint is unchanged

#### Scenario: Local fingerprint is stamped after an upload
- **WHEN** the check runs with the explicit stamp-after-upload option after a
  new pot has been uploaded
- **THEN** the baseline records the fingerprint of the uploaded pot, and a
  subsequent run reports no local template change

#### Scenario: No pot recorded yet is not unchanged
- **WHEN** the baseline contains no recorded uploaded-pot fingerprint and the
  check runs
- **THEN** the check reports the local template state as not determined rather
  than as unchanged

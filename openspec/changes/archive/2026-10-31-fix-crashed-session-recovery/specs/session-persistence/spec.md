# Spec Delta

## ADDED Requirements

### Requirement: Restoring a crashed session consumes its snapshot

Restoring a crashed session SHALL copy its data into the document's current
temporary session and SHALL open that temporary database. The snapshot
database, its sidecars and its session directory SHALL be removed only after
the restored document has opened successfully. If the copy or open fails, the
snapshot SHALL remain intact and SHALL be offered again. Restored work SHALL be
treated as unsaved temporary work until it is written to a file.

#### Scenario: A successful restore consumes the snapshot

- **WHEN** the user restores a crashed snapshot
- **AND** the restored document opens successfully
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  be removed
- **AND** the restored pages SHALL be shown
- **AND** the next start SHALL NOT offer that snapshot again

#### Scenario: A failed restore preserves the snapshot

- **WHEN** the user restores a crashed snapshot
- **AND** the snapshot cannot be copied or the restored database cannot be
  opened
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  remain intact
- **AND** the next start SHALL offer it again

#### Scenario: Restored work is removed on a normal exit

- **WHEN** the user restores a crashed snapshot and quits normally without
  writing the work to a file
- **THEN** the temporary session containing the restored work SHALL be removed
- **AND** the next start SHALL NOT offer the restored work for recovery

#### Scenario: A crash after restoring offers the restored work once

- **WHEN** the user restores a crashed snapshot and the application crashes
  again before the work is written to a file
- **THEN** the next start SHALL offer the current temporary session, including
  the restored work
- **AND** the original snapshot SHALL NOT be offered separately

#### Scenario: Save As keeps restored work in the saved file

- **WHEN** the user restores a crashed snapshot and chooses Save As with a
  filename
- **THEN** the restored session SHALL be written to that file
- **AND** a normal quit SHALL remove the temporary session
- **AND** the saved file SHALL remain

### Requirement: Crashed snapshots can be discarded

The crashed-session picker SHALL let the user discard one or more listed
snapshots without restoring them. Discarding SHALL require confirmation and,
once confirmed, SHALL remove the selected snapshot database, its sidecars and
its session directory. A snapshot in use by a running instance SHALL NOT be
discarded.

#### Scenario: Discarding a selected snapshot removes it

- **WHEN** the user selects a crashed snapshot and chooses Discard
- **AND** confirms the discard
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  be removed
- **AND** the next start SHALL NOT offer it again

#### Scenario: Cancelling a discard leaves the snapshot

- **WHEN** the user chooses Discard and cancels the confirmation
- **THEN** the snapshot SHALL remain unchanged
- **AND** it SHALL still be listed

#### Scenario: Discarding several snapshots removes each one

- **WHEN** the user selects several crashed snapshots and confirms Discard
- **THEN** every selected snapshot database, its sidecars and its session
  directory SHALL be removed

#### Scenario: A running session cannot be discarded

- **WHEN** a snapshot belongs to a session in use by another instance
- **THEN** it SHALL NOT be listed for discard

### Requirement: Crashed-session discovery and the picker are shared

Crashed-session discovery SHALL list the snapshot databases found in the
configured temporary directory that are not in use by a running instance. The
same picker SHALL be shown at startup and from **File → Open crashed session**,
and it SHALL offer Restore, Discard and Cancel. The File menu action SHALL NOT
use a folder chooser, and it SHALL report when no snapshots are found.

#### Scenario: Startup lists detected snapshots

- **WHEN** the application starts
- **AND** a crashed snapshot exists in the configured temporary directory
- **THEN** the picker SHALL list it

#### Scenario: The File menu shows the same picker

- **WHEN** the user chooses **File → Open crashed session**
- **THEN** the picker SHALL list the snapshots detected at that moment
- **AND** it SHALL offer Restore, Discard and Cancel

#### Scenario: The current session is not listed

- **WHEN** the picker is shown
- **AND** the current application's session database is in the temporary
  directory
- **THEN** the current session SHALL NOT be listed

#### Scenario: An orphaned snapshot is still listed

- **WHEN** a snapshot database exists without its session directory
- **THEN** the picker SHALL list it
- **AND** it SHALL be possible to restore or discard it

#### Scenario: No snapshots are found

- **WHEN** the user chooses **File → Open crashed session**
- **AND** no crashed snapshot exists
- **THEN** the application SHALL report that no crashed sessions were found
- **AND** no empty picker SHALL be left open

#### Scenario: Startup is silent when nothing is found

- **WHEN** the application starts
- **AND** no crashed snapshot exists
- **THEN** no picker SHALL be shown

### Requirement: Listed crashed snapshots are reserved for the picker

While the crashed-session picker is open, each listed snapshot SHALL be
reserved so that another instance does not list or restore it. A snapshot
already reserved by another instance SHALL NOT be listed. Reserving a snapshot
SHALL NOT block waiting for the other instance.

#### Scenario: Another instance skips a reserved snapshot

- **WHEN** a snapshot is reserved by an open picker
- **AND** another instance opens its picker
- **THEN** the other instance SHALL NOT list that snapshot

#### Scenario: Reservation does not block startup

- **WHEN** a snapshot is locked by another running instance
- **THEN** discovery SHALL skip it without waiting
- **AND** the application SHALL continue starting

#### Scenario: Reservation is released after the picker closes

- **WHEN** the picker is closed by Restore, Discard or Cancel
- **THEN** the reservations held by that picker SHALL be released

### Requirement: Empty crashed snapshots remain available

The picker SHALL list a crashed snapshot even when its latest recorded action
contains no pages. Restoring such a snapshot SHALL open an empty document, and
discarding it SHALL remove it.

#### Scenario: A cleared snapshot is listed

- **WHEN** a crashed snapshot's latest recorded action removed every page
- **THEN** the picker SHALL list it

#### Scenario: A cleared snapshot restores empty

- **WHEN** the user restores a crashed snapshot whose latest action removed
  every page
- **THEN** the document SHALL show no pages
- **AND** the snapshot SHALL be consumed

#### Scenario: A cleared snapshot can be discarded

- **WHEN** the user discards a crashed snapshot whose latest action removed
  every page
- **THEN** the snapshot SHALL be removed

# Spec Delta

## Purpose

The Scan Document dialog remembers the size the user set so it opens at that
size again when it is reopened, including across application restarts.

## ADDED Requirements

### Requirement: Reopen the scan dialog at its last size

When a size was saved for the scan dialog, the application SHALL open the scan
dialog at that saved size on the next launch. When no size was saved, the
dialog SHALL open at the toolkit's default size.

#### Scenario: A resized dialog is reopened after a restart

- **WHEN** the user resizes the scan dialog, closes it, and later quits and
  restarts the application
- **THEN** the scan dialog opens at the size the user set before closing it

#### Scenario: No saved size means the default size

- **WHEN** the user opens the scan dialog and no size was saved for it
- **THEN** the dialog opens at the toolkit's default size

### Requirement: Record the size when the scan dialog closes

When the user closes a shown scan dialog by any of its close controls — the
window close button, the `_Close` button, or the Escape key — the application
SHALL record the dialog's current size at that moment, and SHALL persist that
recorded size to the configuration when the application quits.

#### Scenario: Closing with the window close button preserves the size

- **WHEN** the user resizes the scan dialog and closes it with the window close
  button, then quits the application
- **THEN** the recorded size is written to the configuration on quit
- **AND** the dialog reopens at that size on the next launch

#### Scenario: Closing with the Close button or Escape behaves the same

- **WHEN** the user resizes the scan dialog and closes it with the `_Close`
  button or the Escape key, then quits the application
- **THEN** the recorded size is written to the configuration on quit
- **AND** the dialog reopens at that size on the next launch

### Requirement: Persist the live size when quitting with the dialog open

When the application quits while the scan dialog is still shown, the
application SHALL persist the dialog's current size at quit time, so a resize
made in that session is not lost just because the dialog was never closed.

#### Scenario: Resizing and quitting without closing the dialog

- **WHEN** the user resizes the scan dialog and quits the application without
  closing the dialog first
- **THEN** the current size is written to the configuration on quit
- **AND** the dialog reopens at that size on the next launch

### Requirement: A dialog never shown does not erase the saved size

When the scan dialog is created in the background and never shown during a
session, the application SHALL NOT overwrite the previously saved size with an
empty value when it quits; the size saved by an earlier session SHALL remain in
effect.

#### Scenario: Background auto-opened dialog is quit, then reopened later

- **WHEN** the application auto-opens the scan dialog in the background, the
  dialog is never shown in that session, and the user quits
- **THEN** the size saved in an earlier session is still used the next time the
  scan dialog is shown

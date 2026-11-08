# Proposal

## Why

The three controls in the scan dialog's **Scan profiles** frame are icon-only
and carry no tooltip or accessible name, so nothing explains what they do.
The Edit button is worse: its icon name, `document-edit`, is not provided by
common icon themes and resolves to `image-missing`. Next to an empty profile
list, the frame reads as disabled rather than ready to use.

The same unlabelled icon-button pattern appears in the paper-size and profile
editors and in Preferences. The `dialog-buttons` capability covers dialog
action buttons only, so content buttons like these have no requirement to
meet and no test to fail.

## What Changes

- Give every icon-only button an accessible name plus a tooltip, or a visible
  text label, following the existing `layer._make_icon_button` convention.
- Replace `document-edit` with an icon name that resolves in the shipped
  themes, or bundle the icon with the application, so no button renders the
  `image-missing` placeholder.
- Apply this to the buttons found in the audit: Save/Edit/Delete in the Scan
  profiles frame, add/remove in **Edit paper size**, the per-row delete
  buttons in **Edit profile**, the add button for user-defined tools in
  Preferences, and the calendar-edit button in the Save dialog that shares the
  broken icon.
- Add tests that assert each button's label or tooltip and that the icon name
  resolves in the test theme.
- Regenerate the translation template if new tooltip strings are introduced.

## Capabilities

### New Capabilities

- `icon-only-buttons`: buttons whose only visible content is an icon remain
  understandable and accessible. Each has an accessible name and a tooltip or
  visible label, and names an icon that renders in the active theme.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/dialog/scan.py`, `src/scantpaper/dialog/preferences.py` and
  `src/scantpaper/dialog/save.py`.
- `src/scantpaper/tests/` for the affected dialogs.
- `po/scantpaper/scantpaper.pot` and the `.po` catalogs, if the tooltips
  introduce new msgids.
- `src/scantpaper/icons/hicolor/` if the edit icon is bundled instead of
  renamed.
- `README.md` if the profile controls gain visible labels worth documenting.
- `changelog.md`.

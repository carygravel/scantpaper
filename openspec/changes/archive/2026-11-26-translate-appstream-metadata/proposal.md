# Proposal

## Why

The AppStream metainfo and the FreeDesktop desktop entry contain translatable
text, but their translations are maintained by hand as inline `xml:lang` and
`Comment[xx]` entries. They are incomplete (the metainfo has only Czech; the
desktop entry has only German, French and Russian), already stale (the English
metainfo says `libimage-sane-perl` while its `en_GB` copy still says
`libsane-perl`), and invisible to Rosetta and the approval ledger.

AppStream does not translate a component from the `<translation type="gettext">`
tag: clients read the inline `xml:lang` entries, and `appstream-compose` uses
the tag only to compute translation coverage. The strings must therefore be
generated from the same approved catalogs as the application's `.mo` files,
which is how AppStream itself produces its own metadata.

## What Changes

- Make the source metainfo English-only: remove every inline `xml:lang`
  element, mark the brand name and the developer name `translate="no"`, and
  split the 275-character description paragraph at its sentence boundary so it
  does not add another over-long msgid.
- Make the source desktop entry English-only: remove `Comment[de]`,
  `Comment[fr]` and `Comment[ru]`. `Name` and `Keywords` stay untranslated.
- Extract the metainfo strings with a vendored `metainfo.its`, and the desktop
  `Comment` with gettext's Desktop parser, into the existing `scantpaper`
  template. `Name` and `Keywords` are excluded from the desktop extraction.
- Migrate the existing human translations into the catalogs: the six Czech
  metainfo strings (with the `libsane-perl` product name corrected) and the
  German, French and Russian desktop comments. Record each with a
  `human-review` approval so they keep shipping.
- Add `dev/join_metadata.py`, which turns the approval-gated `.mo` tree into
  the installed metainfo and desktop file using `msgunfmt` and
  `msgfmt --xml`/`--desktop`. Fuzzy and unapproved translations are absent, so
  they fall back to English exactly as they do in the application.
- Run the join in the Debian, Fedora and openSUSE builds, and install the
  generated files instead of the English-only sources.
- Extend the ITS drift check, the template tests, the packaging tests and the
  maintainer documentation to cover the new sources.

## Capabilities

### New Capabilities

- `desktop-metadata-translation`: how the installed AppStream metainfo and
  desktop entry carry translations generated from the approved catalogs, and
  the English-only shape their source files must keep.

### Modified Capabilities

- `translations`: the message template now also extracts the metainfo and
  desktop entry, the vendored ITS drift check covers the metainfo rules, and
  the pinned msgid set is the union of the Python, `.ui`, metainfo and desktop
  sources.

## Impact

- `org.scantpaper.desktop.metainfo.xml`, `org.scantpaper.desktop`
- `dev/generate_pot.py`, new `dev/join_metadata.py`, `dev/check_po.py`,
  `dev/its-rules.md`, new vendored `dev/metainfo.its` and `dev/metainfo.loc`
- `po/scantpaper/*.po` (new strings; `cs`, `de`, `fr` and `ru` gain
  translations), `po/approvals/cs.json`, `de.json`, `fr.json`, `ru.json`
- `packaging/debian/rules`, `packaging/fedora/scantpaper.spec`,
  `packaging/opensuse/scantpaper.spec` (the RPM recipes gain a build-time
  AppStream ITS package)
- `.github/workflows/test.yml` (adds `desktop-file-utils` for the join test)
- Tests: `src/scantpaper/tests/test_po_files.py`, `test_appdata.py`, new
  `dev/tests/test_join_metadata.py`, `dev/tests/test_packaging_ledger_path.py`
- Documentation: `README.md`, `po/README.md`, `AGENTS.md`, `changelog.md`
- No new runtime dependency. `gettext`, `polib` and `appstream` are already
  build or test dependencies on Debian; Fedora and openSUSE gain a build-time
  package for the system metainfo ITS rules, and CI gains
  `desktop-file-utils`. `itstool` is deliberately not used.

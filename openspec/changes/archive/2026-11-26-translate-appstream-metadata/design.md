# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- `dev/generate_pot.py` extracts Python strings with `xgettext` and `.ui`
  strings with a vendored `dev/gtkbuilder.its`, then merges the per-language
  templates with `msgcat`.
- `dev/compile_mo.py` compiles every `po/scantpaper/<lang>.po` to a `.mo`
  tree. With `--approvals` it blanks every non-fuzzy entry that has no valid
  ledger approval, so the `.mo` tree is already the gated view of the
  catalogs.
- All three packaging recipes run `generate_pot.py` and `compile_mo.py` in
  their build phase. Debian compiles into `debian/locale`; Fedora and openSUSE
  compile into `locale/`.
- AppStream clients read the inline `xml:lang` elements. The
  `<translation type="gettext">` tag only lets `appstream-compose` compute
  coverage from the `.mo` headers (`compose/asc-utils-l10n.c`); it does not
  translate anything.
- gettext 1.0's `msgfmt --xml --template=... -d <po-dir>` and
  `msgfmt --desktop --template=... -d <po-dir>` join every language listed in
  `<po-dir>/LINGUAS` into one file. Both read `.po` files, not `.mo` files.
- `msgfmt --xml` treats a translation as text: an inline `<em>` or `<code>` in
  the template is escaped, not preserved. It also drops the source comment and
  reformats the XML.
- `msgfmt --desktop` appends localized keys to the template; it does not
  replace existing `Comment[de]`-style keys.
- The installed `/usr/share/gettext/its/metainfo.its` comes from the
  `appstream` package, not gettext. Its rules cover the component name,
  summary, description, developer name, keywords, screenshots and release
  descriptions, and honour `translate="no"`.

## Goals / Non-Goals

**Goals:**

- One catalog and one approval ledger for the application, the metainfo and
  the desktop entry.
- Build-time generation of the installed metadata, so the repository keeps
  only the English source and no generated file can drift.
- Preserve the existing human translations (Czech metainfo, German/French/
  Russian desktop comments) without a visible regression.
- Keep the pipeline gettext-only; no `itstool`, no new runtime dependency.
- Keep every existing quality gate green: `ruff`, `ty`, `pytest`, the 99%
  coverage floor, `check_po.py`, `appstreamcli validate`.

**Non-Goals:**

- Translating release notes, screenshot captions or other metainfo elements
  that are not present today.
- Changing the application's source locale. `en_GB` stays a normal catalog;
  no `source_locale` attribute is added.
- Committing generated `.metainfo.xml` or `.desktop` files.
- Replacing the hand-maintained README or man page translations.

## Decisions

### D1: Reuse the `scantpaper` catalog and domain

The metadata strings join the existing `po/scantpaper/` template rather than a
separate domain. This reuses Rosetta, the approval ledger, the coverage report
and the `.mo` install with no new moving parts. A separate domain would need a
second template directory, a second Rosetta project and a second install path
for no benefit.

### D2: English-only sources, no `source_locale` change

The source metainfo drops every `xml:lang` element; the source desktop entry
drops `Comment[de]`, `Comment[fr]` and `Comment[ru]`. The metainfo marks the
brand and developer name `translate="no"`.

The `en_GB` metainfo entries are redundant: three of the four paragraphs and
the name/summary are byte-identical to the English source after whitespace
normalisation, and the second paragraph is a stale copy that still says
`libsane-perl` while the source says `libimage-sane-perl`. Dropping them loses
nothing: an `en_GB` client falls back to the English source, which is the same
text.

`source_locale="en_GB"` is deliberately not added. The project's source
strings are mixed ("recognise" in the metainfo, "gray" in the UI), and
`en_GB.po` carries British variants of a handful of strings, so the source
locale is closer to `en_US`. Adding the attribute would claim a source locale
the catalogs do not agree on. It can be revisited separately.

### D3: Extraction

`dev/generate_pot.py` gains two extractions:

- Metainfo: `xgettext --its=dev/metainfo.its`, run with the repository root as
  the working directory so references stay relative
  (`org.scantpaper.desktop.metainfo.xml:12`).
- Desktop entry: `xgettext --language=Desktop`, then a `polib` filter that
  removes entries whose occurrences are all `Name=` or `Keywords=` lines.
  Filtering by line number, not by msgid, keeps a `Comment` that happens to
  share its text with the brand or the keyword list.

The metainfo ITS pair is vendored exactly like `gtkbuilder.its`/`.loc`, and
`dev/check_po.py` compares both pairs against the installed copies. Vendoring
the extraction rules keeps the msgid set independent of the gettext/appstream
version on the generating machine.

`generate_pot.py` keeps using `subprocess` for `xgettext`/`msgcat` but imports
`polib` for the desktop filter. `polib` is already a build dependency in
Debian, Fedora and openSUSE because `compile_mo.py` uses it.

### D4: The join reads the gated `.mo` tree

New `dev/join_metadata.py`:

1. Find `<mo>/<lang>/LC_MESSAGES/<domain>.mo` for every language.
2. `msgunfmt` each `.mo` to `<tmp>/<lang>.po`, and write `<tmp>/LINGUAS`.
3. Guard the metainfo description: reject inline markup (`em`, `code`, `b`,
   `i`, `span`, `a`, or any child element inside a `p`/`li`) because
   `msgfmt --xml` would escape it.
4. `msgfmt --xml --template=<metainfo> -d <tmp> -o <out>`.
5. `msgfmt --desktop --template=<desktop> -d <tmp> -o <out>`, then restore
   `Name=` and `Keywords=` from the template and remove any localized variant
   of either, so a catalog entry cannot translate the brand.
6. Remove the temporary directory in a `finally`.

The join consumes the `.mo` tree, not the raw `.po` files, so the approval
ledger is applied exactly once, in `compile_mo.py`. There is no second
filtering path and no way for an unapproved translation to leak through the
metadata while the UI falls back.

`msgfmt --xml` uses the system ITS rules for the join (there is no `--its`
option), while extraction is pinned to the vendored copy. This is accepted:
the template is ours and only has summary/description elements, and the join
test asserts the expected elements are translated. The script checks that the
system `metainfo.its`/`.loc` are present and fails with an actionable message
when they are not, rather than silently emitting an English-only file.
Vendoring the join rules would require `itstool`, which is out of scope.

Because the join reads the system rules, Fedora gains
`BuildRequires: appstream` and openSUSE gains `BuildRequires: AppStream-devel`;
Debian already has `appstream` in `Build-Depends-Indep`. The test workflow
adds `desktop-file-utils` so `desktop-file-validate` runs in CI.

### D5: Packaging wiring

Each recipe generates the joined files in the build phase and installs those:

- **Debian**: `execute_after_dh_auto_build` runs the join after
  `compile_mo` into `debian/generated/`, and `execute_after_dh_install`
  copies the results over the staged source files.
- **Fedora**: `%build` runs the join after `compile_mo` into `generated/`,
  and `%install` installs from there.
- **openSUSE**: `%build` runs the join after `compile_mo` into `generated/`,
  and `%install` installs from there.

`dev/tests/test_packaging_ledger_path.py` already asserts that
`generate_pot.py` precedes `compile_mo.py`; it gains the same assertion for
`join_metadata.py` after `compile_mo.py`. That is the cheap regression guard
for a packaging path that forgets the join.

### D6: Translation migration and approvals

The existing human text moves into the catalogs and is approved as
`human-review`, which means "current text reviewed by a human". It does not
qualify as `human-historical`, which is reserved for unchanged pre-2026
Launchpad text: both the metainfo and desktop inline translations were
authored in the file, not in the catalogs.

- `cs.po`: six metainfo entries (summary, four paragraphs after the split).
  The scanner paragraph is split at its sentence boundary and its
  `libsane-perl` is corrected to `libimage-sane-perl` to match the source.
- `de.po`, `fr.po`, `ru.po`: one desktop `Comment` entry each.

The records are appended with `dev.translation_ledger.make_record` and
`write_language_ledger` after loading the existing language ledger, so the
qualifications, gate runs and other sections are preserved. The evidence
records the source commit (`873f6586` for the metainfo, the original desktop
file for the comments) and the maintainer's confirmation.

If the maintainer rejects a desktop comment during review, the entry is marked
fuzzy instead of approved and falls back to English; no code changes are
needed.

### D7: Split the long paragraph

The 275-character scanner paragraph becomes two `<p>` elements at the sentence
boundary:

1. `scantpaper can control regular or sheet-fed (ADF) scanners ... at once.`
2. `It presents a thumbnail view ... deleting pages.`

Both are under the 200-character advisory. This does not make the advisory
count zero — the source already has four over-long msgids — but it avoids
adding a fifth and gives translators two manageable units. The Czech text
splits at the same boundary.

### D8: Generated files are build artifacts

Nothing generated is committed. The source metainfo stays the file
`dev/release.py` edits to add a `<release>` entry, so the release tool is
unaffected; the installed file is generated from the edited source at package
build time.

## Risks / Trade-offs

- **Inline markup is escaped** → the join rejects `em`/`code`-style markup in
  the description and names the element. If rich markup is needed later, the
  documented upgrade is `itstool -i dev/metainfo.its -m *.mo`, which adds a
  build dependency.
- **The join uses the system ITS rules** → the template is fixed and the join
  test asserts the expected elements are translated. A future gettext/appstream
  rule change that alters the output is caught by the test rather than shipped
  silently.
- **`msgfmt --xml` drops the copyright comment and reformats** → only the
  installed copy is affected; the source keeps the comment and the release
  tool's edits.
- **`msgfmt --desktop` appends localized keys** → the source is stripped of
  them before generation, and the join restores `Name`/`Keywords` from the
  template as a second guarantee.
- **A packaging path forgets the join** → the packaging test asserts the call
  order, and the package CI builds the real recipes.
- **A Czech approval is invalidated by a text edit** → the records are written
  after the final text, including the `libimage-sane-perl` correction. The
  ledger digest covers the exact translation, so any later edit requires a new
  approval by design.
- **The first full merge refreshes stale catalogs** → it obsoletes strings
  that had already left the Python and `.ui` sources. The per-catalog obsolete
  ceilings and `po/translation-audit.json` were refreshed for the affected
  languages; no existing translated text changed.
- **Desktop comments are loose translations** → the maintainer reviews the
  diff; a rejected comment becomes fuzzy and falls back to English without a
  code change.
- **`msgfmt` requires `LINGUAS`** → the join writes a temporary one from the
  `.mo` directory names.

## Migration Plan

1. Regenerate the template, merge the catalogs, fill the migrated entries and
   record the approvals.
2. Switch the source metadata to English-only and add the vendored metainfo
   ITS pair.
3. Land the extraction, join, tests and packaging wiring together, so no
   commit ships a source file without the generated counterpart.
4. Rollback: point the packaging recipes back at the source files. The source
   files remain valid English metadata, so a rollback loses the translations
   but not the package.

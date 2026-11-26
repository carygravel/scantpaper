# Tasks

## 1. Make the source metadata English-only

- [x] 1.1 Edit `org.scantpaper.desktop.metainfo.xml`: remove every inline
  `xml:lang` element, add `translate="no"` to the brand `<name>` and the
  `<developer><name>`, and split the scanner paragraph into two `<p>`
  elements at the sentence boundary. Verify with
  `appstreamcli validate --no-net org.scantpaper.desktop.metainfo.xml` and
  confirm the file contains no `xml:lang`.
- [x] 1.2 Edit `org.scantpaper.desktop`: remove `Comment[de]`, `Comment[fr]`
  and `Comment[ru]`. Verify with
  `desktop-file-validate org.scantpaper.desktop` and confirm no localized
  key remains.
- [x] 1.3 Extend `src/scantpaper/tests/test_appdata.py` to assert that the
  source metainfo has no `xml:lang`, marks the brand and developer name
  `translate="no"`, and has no inline markup in the description. Verify with
  `pytest src/scantpaper/tests/test_appdata.py`.

## 2. Vendor the metainfo ITS rules and extract metadata strings

- [x] 2.1 Copy `/usr/share/gettext/its/metainfo.its` and `metainfo.loc` to
  `dev/`, and verify with `cmp` that each vendored file is byte-identical to
  the installed copy.
- [x] 2.2 Extend `dev/generate_pot.py` with a metainfo extraction that runs
  `xgettext --its=dev/metainfo.its` from the repository root, so references
  stay relative, and merges the result with `msgcat`. Verify that
  `PYTHONPATH=src python3 dev/generate_pot.py` emits the summary and all five
  description paragraphs, and no brand or developer name.
- [x] 2.3 Extend `dev/generate_pot.py` with a desktop extraction that runs
  `xgettext --language=Desktop`, then removes the entries whose occurrences
  are all `Name=` or `Keywords=` lines. Verify that the template contains
  `A GUI to aid the scan-to-PDF process` and neither `scantpaper` nor the
  keyword list as desktop msgids.
- [x] 2.4 Add `metainfo.its` and `metainfo.loc` to `ITS_RULE_NAMES` in
  `dev/check_po.py` and generalise its comment. Verify that
  `PYTHONPATH=src python3 dev/check_po.py` reports an advisory for both the
  GtkBuilder and metainfo pairs and still exits successfully.
- [x] 2.5 Update `dev/its-rules.md` with the metainfo pair's provenance
  (appstream 1.0.2, retrieved 2026-11-26) and its re-vendoring commands, and
  update the template section of `po/README.md` to name the metainfo and
  desktop sources. Verify that the documented `cp` commands reproduce the
  vendored files.
- [x] 2.6 Extend `src/scantpaper/tests/test_po_files.py` so `_source_msgids`
  covers the metainfo and desktop sources, and add assertions that the
  metainfo strings and the desktop `Comment` are present while the desktop
  `Name` and `Keywords` are absent. Extend the ITS drift tests to copy
  `metainfo.*`. Verify with
  `pytest src/scantpaper/tests/test_po_files.py`.

## 3. Merge the catalogs and migrate the human translations

- [x] 3.1 Run `python3 dev/merge_po.py` to regenerate the template and merge
  every catalog. Verify that the new metainfo and desktop msgids appear in
  the catalogs as untranslated entries with an empty `msgstr` and no adopted
  fuzzy match.
- [x] 3.2 Fill the six Czech metainfo entries in `po/scantpaper/cs.po` and the
  desktop `Comment` in `de.po`, `fr.po` and `ru.po`, correcting
  `libsane-perl` to `libimage-sane-perl` in the Czech scanner text. Verify
  that `msgfmt --check` passes and that no other catalog entry changed.
- [x] 3.3 Append a `human-review` approval for each migrated entry with
  `dev.translation_ledger.make_record` and `write_language_ledger`, loading
  each existing language ledger first so its sections are preserved. Verify
  that `load_ledger` accepts the result and that
  `python3 dev/compile_mo.py --src po/scantpaper --out /tmp/locale
  --domain scantpaper --approvals po/approvals
  --pot po/scantpaper/scantpaper.pot` reports the new entries as approved.
- [x] 3.4 Update the approval-ledger and migration notes in `po/README.md` to
  record that the Czech metainfo and the German/French/Russian desktop
  comments moved from inline metadata to `human-review` approvals. Verify
  that the quoted ledger snippet validates with `dev.translation_ledger`.

## 4. Implement the metadata join

- [x] 4.1 Implement `dev/join_metadata.py`: discover the `.mo` files under
  `--mo`, check that the system metainfo ITS rules are present, run
  `msgunfmt` into a temporary directory, write `LINGUAS`, reject inline
  description markup, run `msgfmt --xml` and `msgfmt --desktop`, and restore
  the desktop `Name` and `Keywords` from the template. Verify that
  `python3 dev/join_metadata.py --help` lists every option and that a run
  against a compiled tree writes both outputs.
- [x] 4.2 Add `dev/tests/test_join_metadata.py` covering an approved
  translation, an unapproved (blanked) entry, a fuzzy entry, the desktop
  `Name`/`Keywords` guarantee, the inline-markup guard, missing system ITS
  rules, a missing template, an empty `.mo` tree, and an `msgunfmt`/`msgfmt`
  failure. Verify with `pytest dev/tests/test_join_metadata.py`.
- [x] 4.3 Add a test that the joined metainfo passes
  `appstreamcli validate --no-net` and the joined desktop entry passes
  `desktop-file-validate`, skipping each when the tool is absent. Add
  `desktop-file-utils` to the apt list in `.github/workflows/test.yml` so the
  desktop check runs in CI. Verify with
  `pytest dev/tests/test_join_metadata.py`.
- [x] 4.4 Document the join in the compile step of `po/README.md` and in the
  translations bullet of `AGENTS.md`, naming `dev/join_metadata.py` and the
  `--mo` input. Verify that the documented command runs as written against a
  tree produced by `compile_mo.py`.

## 5. Wire the join into packaging

- [x] 5.1 Add the join to `packaging/debian/rules`: generate into
  `debian/generated/` in `execute_after_dh_auto_build` and copy over the
  staged files in `execute_after_dh_install`. Verify with
  `python3 dev/prepare_deb.py --source-ref HEAD --build-root /tmp/deb-render`
  and a review of the rendered `debian/rules`.
- [x] 5.2 Add the join to `packaging/fedora/scantpaper.spec`: generate into
  `generated/` in `%build` and install from there in `%install`, and add
  `BuildRequires: appstream` for the system metainfo ITS rules. Verify with
  `python3 dev/prepare_rpm.py --template packaging/fedora/scantpaper.spec
  --source-ref HEAD --spec-out /tmp/fedora.spec --sources-dir /tmp/fedora-src`
  and a review of the rendered spec.
- [x] 5.3 Add the join to `packaging/opensuse/scantpaper.spec` in the same
  way, with `BuildRequires: AppStream-devel` for the ITS rules. Verify with
  `python3 dev/prepare_rpm.py --template packaging/opensuse/scantpaper.spec
  --source-ref HEAD --spec-out /tmp/opensuse.spec
  --sources-dir /tmp/opensuse-src` and a review of the rendered spec.
- [x] 5.4 Extend `dev/tests/test_packaging_ledger_path.py` to assert that
  every recipe invokes `dev/join_metadata.py` after `dev/compile_mo.py`.
  Verify with `pytest dev/tests/test_packaging_ledger_path.py`.
- [x] 5.5 Update the Translations section of `README.md`, the translation
  steps of `release_procedure.md`, and the 4.0.5 bullet in `changelog.md` to
  say that the installed metainfo and desktop entry are generated from the
  approved catalogs. Verify that the commands in the updated procedure match
  the recipes.

## 6. Integration checks

- [x] 6.1 Run the full suite with `pytest -m "not slow"` and then
  `pytest -m slow`, and confirm the coverage floor and every canary pass.
- [x] 6.2 Run `ruff format --check .`, `ruff check .` and `ty check .` and
  confirm they report no diagnostics.
- [x] 6.3 Run `python3 dev/check_test_coverage.py` and confirm the new test
  modules add no unexecuted statements or partial branches.
- [x] 6.4 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive` and confirm both pass.
- [x] 6.5 Build the joined metadata from a real compiled tree and validate
  both outputs with `appstreamcli validate --no-net` and
  `desktop-file-validate`, confirming the Czech, German, French and Russian
  translations appear and the brand and keywords do not.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.

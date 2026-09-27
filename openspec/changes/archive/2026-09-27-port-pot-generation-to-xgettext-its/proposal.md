## Why

The translation-authoring checks added by the archived
`translation-authoring-checks` change generate the message template on demand
rather than reading a committed `.pot`, which is what makes the source-side
checks trustworthy. Doing so made `intltool-extract` a hard build dependency,
and CI failed on it: `intltool` is deprecated upstream, so it is not reliably
present in newer runner images. The dependency is also unnecessary, because GNU
gettext already ships `gtkbuilder.its` and a Glade `.ui` file *is* GtkBuilder
XML, so `xgettext --its` does the whole job.

## What Changes

- Extract `.ui` strings in `dev/generate_pot.py` with
  `xgettext --its=<rules>` instead of running `intltool-extract` and then
  re-extracting the generated `*.ui.h` as C. This removes the intermediate
  header, the temp `.pot` it needed, and the `intltool` dependency.
- Vendor `gtkbuilder.its` and `gtkbuilder.loc` under `dev/`, so extraction
  depends on neither the gettext version nor its install layout.
- Add a check comparing the vendored ITS rules against the copy installed on
  the system, so an upstream change to the rules is noticed rather than
  silently diverging.
- Add a regression test asserting that `.ui` msgids are actually present in
  the generated msgid set, so a future gettext that cannot resolve the rules
  fails loudly instead of quietly extracting zero strings from the three `.ui`
  files.
- Drop `intltool` from CI and from the documented development dependencies,
  reversing the workaround added for the CI failure.

The generated msgid set is unchanged. Measured over the current tree, the
existing pipeline and the `--its` pipeline both yield 549 msgids with no
msgid in either set that is absent from the other. Source references improve:
`Open images` is currently attributed to the throwaway `app.ui.h:71`, and
would be attributed to `app.ui:533`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `translations`: adds a requirement to the `translations` capability fixing
  how the on-demand msgid set is produced. *Catalog hygiene defects are
  reported* already requires that set to be generated rather than read from a
  committed file, and that behaviour is unchanged; what is new is that
  generation uses gettext's ITS rules for GtkBuilder XML taken from a copy
  vendored in the repository, that it no longer needs `intltool`, and that
  both the completeness of the `.ui` extraction and any divergence between
  the vendored rules and the installed ones are checked.

## Impact

- `dev/generate_pot.py`: replace the `intltool-extract` loop and the C-language
  `xgettext` pass with one `--its` pass over the `.ui` files.
- `dev/gtkbuilder.its`, `dev/gtkbuilder.loc`: new, vendored from gettext
  (24 and 6 lines respectively).
- `dev/check_po.py`: the generator's failure message stops naming
  `intltool-extract`, and the scratch-file cleanup no longer has a
  `*_c_tmp.pot` to remove.
- `src/scantpaper/tests/test_po_files.py`: a test that the vendored rules match
  the system copy, and a test that `.ui` msgids survive extraction.
- `.github/workflows/test.yml`: remove the `intltool` package added to the
  three test jobs.
- `README.md`: remove `intltool` from the development dependencies, leaving
  `gettext` as the only external requirement for the checks.
- Dependencies: one fewer (`intltool`); `gettext` remains. The vendored ITS
  rules become a file this project carries and must keep in step with gettext.

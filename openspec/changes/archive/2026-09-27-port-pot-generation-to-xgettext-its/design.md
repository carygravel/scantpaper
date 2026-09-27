## Context

`dev/generate_pot.py` currently extracts `.ui` strings in two stages: it runs
`intltool-extract --type=gettext/glade` over each `.ui` file, which writes a C
header (`*.ui.h`) next to it containing `_("...")` markers, and then runs
`xgettext --language=C` over those generated headers. The Python sources are
extracted separately and the two temporary catalogs are combined with `msgcat
--use-first`.

`dev/check_po.py` invokes that generator on every run, in a temporary
directory, to obtain the msgid set for the source-side checks. That is why a
missing `intltool-extract` fails the whole catalog check rather than just the
template build.

Three `.ui` files contribute 83 msgids: `app.ui`, `menu.ui` and `window.ui`.
None of them contains a `TRANSLATORS` comment, so there are no extracted
translator comments whose handling could differ between the two mechanisms.

## Goals / Non-Goals

**Goals:**

- Remove the `intltool` dependency from the catalog checks, leaving `gettext`
  as the only external requirement.
- Produce the same msgid set as today.
- Make the extraction independent of the installed gettext version and layout.
- Make divergence between the vendored rules and upstream visible, and make
  a silently empty `.ui` extraction impossible.

**Non-Goals:**

- Changing which strings are considered translatable. If a future gettext
  extends the ITS rules to cover a new attribute, adopting that is a separate,
  deliberate change, not a side effect of this port.
- Reordering or deduplicating the catalogs, and the obsolete-entry ceiling work
  already tracked in the archived `translation-authoring-checks` change.
- Reworking how `check_po.py` reports or fails.

## Decisions

### D1: Extract with `xgettext --its` instead of the header round-trip

A Glade `.ui` file is GtkBuilder XML, and gettext ships `gtkbuilder.its` to
describe which attributes are translatable. `xgettext --its=<rules>` consumes
the `.ui` files directly, so the intermediate header and the second extraction
pass both disappear.

*Alternative considered:* keep `intltool-extract` and just add the dependency
everywhere. Rejected: it leaves a deprecated package as a hard requirement of
the test suite, which is what broke CI.

*Verification already performed:* both pipelines were run over the current tree
and their msgid sets compared. Both yield 549 msgids, with no msgid present in
only one set. Source references improve, because the current pipeline
attributes `Open images` to the generated `app.ui.h:71` whereas the ITS pass
attributes it to `app.ui:533`.

### D2: Vendor `gtkbuilder.its` and `gtkbuilder.loc` rather than look them up

`xgettext --its` requires a filesystem path; the bare name `gtkbuilder` is not
resolved, and `pkg-config --variable=itsdir gettext` returns nothing on this
platform. Locating the rules at runtime would therefore mean hardcoding
`/usr/share/gettext/its/` with a fallback list, which still breaks if a
distribution relocates it or if the installed gettext predates the rules.

Vendoring sidesteps all of that. The two files are 24 and 6 lines, and they
are passed to `xgettext` by a path relative to `dev/`, so extraction behaves
identically everywhere.

*Alternative considered:* resolve the path at runtime, preferring the installed
copy. Rejected as the primary mechanism because it makes the generated msgid
set a function of the build host. The installed copy is still consulted, but
only to report drift.

*Trade-off accepted:* the project now carries a copy of a gettext data file.
That is the cost of hermeticity, and the drift check in D4 is what keeps the
copy honest.

### D3: Keep the two `xgettext` passes and the existing `msgcat` merge

The Python and UI extractions stay separate `xgettext` invocations merged by
`msgcat`, so the header substitutions, the `--use-first` precedence and the
`SOME DESCRIPTIVE TITLE` fixups in `generate_pot.py` are untouched. Only the
second input changes: a POT from the `.ui` files instead of a POT from the
generated headers.

The temporary catalog for the UI pass is renamed from `_c_tmp.pot` to
`_ui_tmp.pot`, since it is no longer a C-language extraction.

### D4: Report rule drift as an advisory, not a hard check

The check compares `dev/gtkbuilder.its` and `dev/gtkbuilder.loc` against the
installed copies, byte for byte, and prints the outcome. It does not affect the
exit status.

The reasoning is the same one that governs the rest of the project: a
condition that identifies no defect in shipped output does not block a
release. A differing installed copy means this project's copy may be behind
upstream, and the template generated from the vendored copy is still correct
and self-consistent. Failing the build would mean every gettext upgrade that
touches the rules breaks CI until someone re-vendors, which trains people to
re-vendor without reading.

The report distinguishes three outcomes, because "identical" and "nothing to
compare against" must not look the same:

- identical, reported as such;
- different, naming both paths and the first differing line;
- no installed copy found, reported as its own case.

The comparison is skipped silently if the vendored file is missing, since that
is a packaging mistake in this repository rather than upstream drift, and it is
caught by D5 instead.

The comparison is byte for byte, which has one consequence worth stating: the
vendored files must not be annotated. Adding a provenance comment to
`dev/gtkbuilder.its` would make it differ from upstream by construction and the
check would fire on every run. Provenance is recorded beside the files instead,
in `dev/its-rules.md`.

*Alternative considered:* fail the build on drift. Rejected for the reason
above. It stays available as a one-line change if drift turns out to be
routine in practice.

### D5: Fail if the `.ui` strings are absent from the generated set

The failure mode this port introduces is silent: if the ITS rules cannot be
resolved, or a future gettext changes the expected input, `xgettext` extracts
nothing from the `.ui` files, the msgid set loses 83 entries, and every
source-side check reports a clean result over an incomplete set.

The check is an assertion over the generated msgid set, not over the rules: it
requires that a known msgid which only exists in a `.ui` file is present.
Asserting on a specific msgid rather than on a count means an intentional
source change cannot cause a confusing failure, and it fails for the actual
reason rather than as a side effect of an unrelated count change.

This is deliberately separate from the drift check. Drift is upstream's
business and is advisory; an empty extraction is this project's problem and is
a hard failure.

## Risks / Trade-offs

- **Vendored rules drift from gettext** → the drift check reports it on every
  run, and re-vendoring is copying two files. The trade is a small maintenance
  duty in exchange for a msgid set that no longer depends on the build host.
- **A gettext upgrade changes what the ITS rules extract**, so the generated
  msgid set could legitimately change while the vendored copy stays the same
  → this cannot happen while the vendored copy is used, which is the point of
  D2. Adopting an upstream change is a deliberate re-vendor.
- **The drift check needs to find the installed copy**, which varies by
  distribution → it probes the known locations and reports "not found"
  otherwise. It never guesses a path it has not checked, and it is advisory, so
  a wrong guess cannot break the build.
- **The msgid set changing accidentally** → the port fixes the current set in
  a test, by asserting the known msgid count and the presence of a known
  `.ui`-only msgid, so an unintended change is caught before it reaches a
  catalog merge.

## Context

See `proposal.md` for the motivation and `specs/` for the behaviour contract.
The relevant environments are:

| Environment | GTK | PyGObject | Python |
| --- | --- | --- | --- |
| Ubuntu 22.04 (jammy) | 4.6.9 | 3.42.1 | 3.10 |
| Ubuntu 24.04 (noble) | 4.14.5 | 3.48.2 | 3.12 |
| Debian sid (maintainer) | 4.24.1 | 3.58.0 | 3.14 |

The CI failures were reproduced in `ubuntu:22.04` and `ubuntu:24.04`
containers. They are all explained by APIs whose availability starts after
the jammy floor. The first jammy triage found 13 failures and 3 errors; after
the menu, colour and dispose fixes, the full jammy log exposed 107 failures
and 61 errors, dominated by the thumbnail stylesheet and spin-button paths.
The port must stay on the jammy side of that line until 2027-06.

## Goals / Non-Goals

**Goals:**

- Make the current code and test suite pass on GTK 4.6/PyGObject 3.42 and on
  GTK 4.14/PyGObject 3.48, as well as on the maintainer's newer stack.
- Keep the jammy `oldest` CI job as the enforcement point.
- Make the rotated-text test accept the text-layer structure emitted by
  current OCRmyPDF without weakening the product requirement.

**Non-Goals:**

- Modernising widgets that are merely deprecated on jammy (that stays in the
  "When jammy is dropped" list in `release_procedure.md`).
- Raising the minimum Python, GTK or PyGObject version.
- Adding an upper bound on OCRmyPDF.
- Changing saved-document format or session data.

## Decisions

### Keep the jammy compatibility floor

Target GTK >= 4.6 and PyGObject >= 3.42 for the lifetime of jammy support.
Use only APIs available there, or feature-detect newer APIs with a fallback.

Alternative considered: raise the floor to noble (GTK 4.14/PyGObject 3.48).
Rejected because jammy remains a supported PPA target until 2027-06, and
because raising the floor still would not support the maintainer's newer
stack without additional work.

### Load the menu model from a top-level builder object

Move the nested `<menu>` in `app.ui` to a top-level `<menu id="...">` object
and point `GtkPopoverMenuBar` at it with a `menu-model` property whose value
is that id. GTK Builder can resolve a top-level `GMenu` on GTK 4.6, 4.14 and
4.24; the inline form used today is only accepted from GTK 4.17.5.

The menu contents and action links stay unchanged, so `main-menu` behaviour
is preserved. This was verified by loading the reworked UI in GTK 4.6.9,
4.14.5 and 4.24.1 and checking that the model still has five top-level menus.

Alternative considered: build the `Gio.Menu` in Python and assign it to the
menu bar. Rejected because it moves the menu definition out of `app.ui` and
duplicates the structure that the existing UI tests inspect.

### Construct `Gdk.RGBA` values by assigning components

Add a small helper that creates an empty `Gdk.RGBA()` and assigns `red`,
`green`, `blue` and `alpha`. Use it wherever a colour is produced, including
the HSV conversion used for confidence colours and drag feedback. Avoid
passing positional arguments to the boxed constructor entirely.

PyGObject only gained the GDK 4 positional `Gdk.RGBA` override in 3.52. On
3.42 and 3.48 the arguments are ignored with a deprecation warning, producing
transparent black. Field assignment works on every supported version.

Alternative considered: require PyGObject >= 3.52. Rejected because both LTS
runners are below that, and field assignment is a one-line-per-component fix.

### Clean up the scroll-idle timer from an unrealize hook

Move the timeout removal out of `do_dispose` and into `do_unrealize`, chaining
up with `Gtk.Widget.do_unrealize`. PyGObject does not invoke a Python
`do_dispose` override before 3.52, while the widget unrealize vfunc exists and
is called on both 3.42 and 3.58. Make the cleanup idempotent and guard the
idle callback against a view that has lost its root.

Alternative considered: rely on the timeout firing once and returning
`SOURCE_REMOVE`. This avoids the missing vfunc but leaves a live source and a
bound method after destruction; an explicit cleanup hook is clearer and keeps
the existing test intent.

### Traverse GSK containers with the GTK 4.0 API

In the thumbnail test helper, recurse with `get_n_children()` and
`get_child(index)` rather than `get_children()`. The indexed API exists at the
floor; the list-returning convenience method appears only in GTK 4.22.

Alternative considered: feature-detect `get_children` and fall back. Rejected
for a test helper because the indexed API is sufficient on every supported
version and avoids two code paths.

### Load the thumbnail stylesheet with the floor API

Use `Gtk.CssProvider.load_from_data()` with the UTF-8 CSS encoded to bytes.
`load_from_string()` was added in GTK 4.12, so it is absent on jammy.
`load_from_data()` exists at the floor and is only deprecated on newer GTK
releases, not removed. Return the provider so tests can inspect the installed
rule with `to_string()` on every supported PyGObject.

Alternative considered: branch on `hasattr(provider, "load_from_string")` and
fall back to `load_from_data`. Rejected because the older API is sufficient
everywhere and two paths would leave the jammy path untested on newer systems.

### Commit fractional spin values from a key controller

Install a `Gtk.EventControllerKey` on the spin button in the capture phase and
call the existing commit callback when the key is Return or KP_Enter. The
`Gtk.SpinButton::activate` signal was added in GTK 4.8, so connecting it raises
on jammy before the dialog can be used. The capture phase runs before the
embedded entry can consume the key. Tests emit `key-pressed` through the
controller, which works on 3.42 and 3.48 without relying on a signal that may
not exist.

Alternative considered: feature-detect the signal and connect only when
present. Rejected because the key controller covers every supported version
with one path and the same commit behaviour.

### Keep the paint assertion portable

PyGObject 3.42 cannot marshal `Gtk.Snapshot` through
`Gtk.Widget.snapshot_child`; the call corrupts the wrapper and the following
render-node traversal segfaults. The stylesheet-and-pixbuf test therefore runs
on every version, and the render-tree test is skipped when PyGObject is older
than 3.46. The product behaviour is covered at the floor by the CSS assertion;
newer versions retain the stronger painted-size check. Test helpers for the
render-node walk and the mainloop wait are exercised with mocks and direct
calls so they do not depend on the unsafe snapshot binding.

Alternative considered: skip the thumbnail test on jammy. Rejected because the
CSS rule is the regression under test and can be checked without snapshotting,
so no skip is needed.

### Recognise rotation in page and Form XObject content

Teach the rotated-text test to collect the page content stream and every
recursive Form XObject stream, then look for a rotated `Tm` or a rotated `cm`
in a text-bearing stream. OCRmyPDF 17.13 keeps the text layer in a Form
XObject and expresses the 90-degree rotation as `0 1 -1 0 ... cm` around the
text object; OCRmyPDF 17.10 and earlier expressed it on the page as a rotated
`Tm`. Both are valid renderings of the same text angle.

The test keeps its semantic assertions: the horizontal control must not be
rotated, the rotated page must contain a rotated text transform, and
`pdftotext` must still extract both words.

Alternative considered: pin `ocrmypdf<17.13`. Rejected because the generated
PDF is correct and the project already consumes OCRmyPDF's private hOCR
renderer; the test should follow the output rather than freeze the dependency.

### Keep the CI matrix and document the window

Leave `.github/workflows/test.yml` running `oldest` on Ubuntu 22.04 and
`latest`/`latest_w_ppa` on 24.04. Update `README.md` and
`release_procedure.md` to state that jammy is supported until 2027-06 and that
GTK 4.6/PyGObject 3.42 is the floor until then.

## Risks / Trade-offs

- **The menu failure masked the rest of the jammy suite.** Fixing it may
  reveal additional APIs that are newer than GTK 4.6. → Run the full suite in
  the jammy CI job and a local 22.04 container before release; fix any
  follow-ups under the same floor rule.
- **A top-level `GMenu` object could change how actions are linked.** → Keep
  the existing action strings and verify the five top-level labels and a
  representative `win.new` link in the existing UI tests on both LTS runners.
- **`do_unrealize` is a vfunc, not a public cleanup API.** → Chain up to
  `Gtk.Widget.do_unrealize`, make removal idempotent, and retain the guard in
  the idle callback so a missed hook cannot call into a destroyed view.
- **The OCR test still depends on OCRmyPDF's text-layer structure.** → Accept
  both `Tm` and `cm` encodings, keep the `pdftotext` extraction assertion, and
  inspect only Form XObjects rather than arbitrary page graphics.
- **`load_from_data` is deprecated on newer GTK.** → It remains available
  across the supported range; revisit when jammy support ends and the floor
  moves to GTK 4.14.
- **A key controller must not swallow Return for other widgets.** → Install it
  only on the fractional spin buttons and handle only Return/KP_Enter, leaving
  all other keys unconsumed.
- **The jammy paint assertion is weaker than the render-tree check.** → Keep
  the stronger check on PyGObject >= 3.46 and make the CSS assertion fail if
  the installed rule is missing or has the wrong size.
- **A future contributor may use a newer API again.** → Make the support
  window and the "feature-detect or fall back" rule explicit in the release
  procedure, and let the `oldest` job catch regressions.

## Migration Plan

No data migration is needed. The changes are source-only and affect the next
build. Roll back by reverting the change; no persisted state or file format is
altered. The release procedure update takes effect with the next release.

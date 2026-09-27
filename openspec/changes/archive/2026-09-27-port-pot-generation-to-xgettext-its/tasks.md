## 1. Vendor the ITS rule set

- [x] 1.1 Copy `/usr/share/gettext/its/gtkbuilder.its` and
  `gtkbuilder.loc` into `dev/` byte for byte, with no added comments, so the
  drift check in 3.4 compares like with like
- [x] 1.2 Record in `dev/its-rules.md` where the two files came from: the
  gettext version they were taken from, the upstream path, and the command to
  re-vendor them. Note in that file that editing the vendored copies defeats
  the drift check
- [x] 1.3 Confirm the two vendored files are byte-identical to the installed
  copies, so 3.4 starts from a clean state

## 2. Tests, written before the implementation

- [x] 2.1 Add a test that generation succeeds on a `PATH` carrying `xgettext`,
  `msgcat` and `msgfmt` but not `intltool-extract`, and that the msgid set it
  produces is complete. Build the restricted `PATH` from symlinks in a
  temporary directory so the test does not depend on what the host has
  installed
- [x] 2.2 Add a test asserting a msgid that exists only in a `.ui` file is
  present in the generated set. Use a real one from `app.ui`, so an
  unresolvable ITS rule set fails the build instead of quietly dropping the 83
  user-interface msgids (design D5)
- [x] 2.3 Fix the current msgid set as a baseline in the tests, so a later
  change to what is extracted is caught: assert the total count and, for the
  `.ui` contribution, the set of msgids the three `.ui` files produce
- [x] 2.4 Add tests for the drift check covering all three outcomes in design
  D4: identical, different, and no installed copy found. The third must be
  distinguishable from the first in the output

## 3. Implementation

- [x] 3.1 In `dev/generate_pot.py`, drop the `intltool-extract` loop and the
  `uih_sources` list, so no `*.ui.h` is generated
- [x] 3.2 Replace the C-language `xgettext` pass over the generated headers
  with a single pass over the `.ui` files using
  `--its=dev/gtkbuilder.its`, resolved relative to the script rather than the
  working directory
- [x] 3.3 Rename the temporary catalog from `_c_tmp.pot` to `_ui_tmp.pot`,
  since it is no longer a C extraction, and update
  `_clean_generator_temp_files` in `dev/check_po.py` to match
- [x] 3.4 Implement the drift check: compare `dev/gtkbuilder.its` and
  `dev/gtkbuilder.loc` against the installed copies, probe the known locations
  rather than guessing, and report the three outcomes distinctly. Advisory
  only, so the exit status is unchanged
- [x] 3.5 Update the generator failure message in `dev/check_po.py` to stop
  naming `intltool-extract`
- [x] 3.6 Update the module docstring of `dev/generate_pot.py`, which currently
  states "Requires gettext and intltool"

## 4. Revert the CI workaround

- [x] 4.1 Remove the `intltool` package from all three `apt-get install` blocks
  in `.github/workflows/test.yml`
- [x] 4.2 Remove the `intltool` entry from the development dependencies in
  `README.md`, leaving `gettext`, and mention the vendored ITS rules in the
  validation section so a contributor knows `intltool` is no longer needed
- [x] 4.3 Confirm the working tree contains no other reference to
  `intltool-extract`

## 5. Verification

- [x] 5.1 Generate the template both ways and confirm the msgid sets are equal,
  recording the result in the change. The expected result, measured before
  implementation, is 549 msgids in both with none unique to either
- [x] 5.2 Confirm `python3 dev/check_po.py` reports 44 catalogs and 0 errors,
  and that the advisory counts are unchanged from the archived
  `translation-authoring-checks` change: (e) 6, (f) 14, (i) 2, (j) 5, (k) 1,
  (l) 1, (m) 4
- [x] 5.3 `python3 -m pytest -q` passes with coverage not below 99.28%, and
  `ruff check`, `ruff format --check` and `ty check .` are clean
- [x] 5.4 Confirm no new uncovered or partially covered lines, and that
  `scantpaper.pot` is still ignored and no `*.ui.h` is left in the tree

## Verification record

Recorded on 2026-09-27, GNU gettext-tools 1.0 (Debian `1.0-5`).

- **5.1 msgid set unchanged (the load-bearing check).** The template was
  generated twice, once by the intltool pipeline at `d563f34` and once by the
  ITS pipeline here, and the two sets compared: 549 msgids each, with 0 unique
  to either side, so the sets are equal. Extraction is now 466 msgids from
  Python and 83 from the three `.ui` files, where the intltool pipeline
  produced the same 83 by way of a generated C header and an XML pass.
- **5.2 catalogs unchanged.** `python3 dev/check_po.py` reports
  `Checked 44 catalogs, 0 error(s)`, with the per-category advisory counts of
  the archived `translation-authoring-checks` change intact: (e) 6, (f) 14,
  (i) 2, (j) 5, (k) 1, (l) 1, (m) 4. Two advisory lines are new and expected,
  one per vendored rule, reporting a match against the installed copies.
- **5.3 gates.** `python3 -m pytest -q`: 1294 passed, 3 xfailed (up from 1286
  passed, 3 xfailed, from 8 new tests). Coverage 99.29%, up from 99.28%.
  `ruff check` and `ruff format --check` are clean, as is `ty check .`.
- **5.4 no regressions.** No file under `src/` other than the test module
  changed, so no source line can have become uncovered. `scantpaper.pot` is
  still ignored (`.gitignore:14`), and the tree contains no `*.ui.h`, no
  `_py_tmp.pot` and no `_ui_tmp.pot`. A test asserts that generating the
  template leaves the `.ui` sources byte-for-byte intact, because the
  generator's working directory is the source directory.

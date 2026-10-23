# Tasks

## 1. Lazy page construction

- [x] 1.1 In `src/scantpaper/page.py`, replace the `tobytes()` argument of
      the `New page size` log in `Page.__init__` with a size computed from
      `width * height * MODE2DEPTH[mode] // 8`; verify that constructing a
      page from stored bytes leaves PIL's core image undecoded (the image
      is not loaded) and that the logged size still matches the byte count
      of a known small image.
- [x] 1.2 Add a unit test (in `src/scantpaper/tests/test_04_page.py`) that a
      page created from stored bytes is not decoded at construction and is
      decoded on first pixel access, reusing the decoded data on a second
      access; verify it passes alongside the existing page tests.

## 2. One-page-at-a-time PDF save

- [x] 2.1 In `src/scantpaper/savethread.py`, move the hOCR sidecar writing
      into the per-page loop of `_assemble_pdf`, stop accumulating `Page`
      objects, and collect only the per-page resolutions needed by
      `img2pdf`'s `layout_fun`; verify `_assemble_pdf` returns no `Page`
      objects and the existing PDF-save tests still pass.
- [x] 2.2 Update `do_save_pdf` to remove the separate hOCR sidecar loop and
      consume the returned resolutions; verify a multi-page save produces
      an equivalent PDF with the searchable text layer intact by running
      the PDF save and text-layer round-trip tests
      (`test_1111_save_pdf.py`, `test_1162_save_multipage_pdf.py`,
      `test_1622_import_multipage_pdf.py`, and the save-searchable-text-
      layer scenarios).
- [x] 2.3 Add a regression test that a multi-page PDF save releases each
      page's image after that page's contribution is written (the save
      path holds at most the page being processed, not the document's
      pages); verify it passes and that the per-page image is released
      before the text-layer embedding phase.
- [x] 2.4 Document the fix in README.md (saving documents with many
      high-resolution pages no longer exhausts memory; page images are
      decoded on demand); verify the note reflects the user-visible
      behaviour change.

## 3. Integration verification

- [x] 3.1 Run the full test suite (`pytest`) and verify all tests pass with
      coverage thresholds met and no newly uncovered or partially covered
      lines beyond pre-existing `TYPE_CHECKING` imports.
- [x] 3.2 Run `ruff format --check`, `ruff check`, and `ty check .` and
      verify they report clean for the changed files and the project.

## Workflow follow-up

- Apply the change with `/opsx-apply-change` once the tasks are approved,
  implementing against this task list.
- Archive the change after the project's review requirements are
  satisfied (`/opsx-archive-change`).

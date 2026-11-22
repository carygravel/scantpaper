# Tasks

## 1. Baseline and probes

- [x] 1.1 Record the current baseline: `pytest --no-cov --durations=50` and
  `pytest --durations=50` (with coverage), saving the total and the ten
  slowest tests. Verify the totals are written down and the six codec tests
  appear in the slowest list.
- [x] 1.2 Add a Ghostscript version probe usable from tests, alongside the
  existing OCRmyPDF and JBIG2 probes, and unit-test it with a substituted
  version string. Verify the new unit test passes without invoking
  Ghostscript.

## 2. Environment-independent decision tests

- [x] 2.1 Extend the existing `TestOcrmypdfVersionGate` pattern with unit
  tests for every codec/compression selection branch (`_jbig2_requested`,
  `_pdfa_image_compression`, `resolve_pdf_codec`, the encoder-absent
  fallback). Verify `pytest src/scantpaper/tests/test_savethread.py` passes
  and starts no external tool.
- [x] 2.2 Unit-test the codec introspection helper against small in-memory
  pikepdf documents instead of a full save. Verify the test passes without
  Ghostscript, ocrmypdf or jbig2.

## 3. Fast save/import layer

- [x] 3.1 Add mocked save tests for `SaveThread` that patch
  `_embed_text_layer()` and call `do_save_pdf()` synchronously, covering
  sequencing, metadata, cancellation breakpoints and page handling. Verify
  the tests pass with `-m "not slow"` and no external tool process starts
  (assert on a `subprocess` spy or the absence of the tool in the log).
- [x] 3.3 Add unit tests for the bodies of `_convert_bilevel_images_to_jbig2`
  and `_restore_bilevel_g4` with the encoder and Ghostscript mocked, so their
  coverage does not depend on the six end-to-end tests. Verify
  `python3 dev/check_test_coverage.py` reports the same or fewer partial
  branches than the recorded baseline.

## 4. Real-toolchain canary

- [x] 4.1 Add the universal invariant canary: save a realistically sized
  bilevel page through the full pipeline and assert the image stream is
  Group 4 or JBIG2 and never Flate. Mark it `slow`. Verify it passes on
  noble and on an environment whose Ghostscript rewrites to Flate.
- [x] 4.2 Gate the encoder-specific assertions (`/JBIG2Decode`, `jb2 < g4`,
  explicit `jb2` request) on the JBIG2 encoder being present, and keep the
  encoder-absent fallback assertion. Verify the suite passes with the
  encoder present and with it simulated absent.
- [x] 4.3 Replace the six near-duplicate codec tests with the canary and
  the gated assertions, and confirm the replacement covers the same
  behaviours. Verify `pytest -m slow` passes and the fast run no longer
  executes them.

## 5. Synthetic images

- [x] 5.1 Replace per-test `convert` image generation in the codec tests with
  a session-scoped PIL-built fixture, including the large bilevel page used
  by the canary. Verify the canary still passes.

## 6. Probe-driven canary

- [x] 6.1 Make the canary assertions select themselves from the runtime
  probes (OCRmyPDF version, JBIG2 availability, Ghostscript version) and
  unit-test the selection. Verify the selection test passes for each
  capability combination.
- [x] 6.2 Update `AGENTS.md` and the testing section of `README.md` to
  describe the fast and canary layers and how to run each. Verify
  `pytest src/scantpaper/tests/test_markdown_line_length.py` passes.

## 7. Integration verification

- [x] 7.1 Re-run `pytest --no-cov --durations=50` and compare with the
  baseline from 1.1. Verify the total is lower and the six codec tests are no
  longer the slowest.
- [x] 7.2 Run the full `pytest` with coverage and verify the 99% gate and
  the test-code audit still pass.

## Follow-up

These are deliberately outside this change and tracked by follow-up changes.
They are prose, not tracked tasks, because the change is scoped to the
save-PDF codec hot spot.

- `mock-import-analysis-tests`: convert the import and analysis tests that
  only check chain callbacks or stored state to synchronous `do_*` calls with
  mocked externals, and verify each module's mainloop count drops. The
  `test_docthread.py` and `test_importthread.py` patterns are the model.
- `replace-convert-image-fixtures`: replace the remaining per-test
  ImageMagick image generation in the save and import modules with
  session-scoped PIL fixtures. Tests that deliberately run an external tool,
  such as user-defined tools and post-save hooks, keep their real invocation.
- Confirm the canary logs in the Ubuntu jobs and in the Debian autopkgtest.

## Workflow follow-up

- Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`.
- Archive the change after review.

# Design

## Context

See `proposal.md` for motivation. The measured profile on the current suite:

- 2,650 tests, 97 modules, 62.7 kLOC of test code; collection alone takes
  about 14 s because every module imports GTK4 and gi.
- A full run is 2 min 38 s with `--no-cov` (about 3.5 min under the coverage
  gate). Six codec tests account for 36.5 s, roughly a quarter of the 145 s
  spent executing tests.
- The async machinery is not the dominant tax: a synchronous
  `thread.do_save_pdf(request)` test takes 0.36 s against 0.38 s for the
  async equivalent. The time is in the external binaries both paths call.
- `SaveThread.do_save_pdf()` calls `_embed_text_layer()` unconditionally, so
  every save flow runs a real ocrmypdf → Ghostscript PDF/A conversion even
  when no page has a text layer.
- The six codec tests each build a 2480×3508 bilevel page, import it through
  a real `DocThread`, save it through the full pipeline, and then re-parse
  the output. The page size is deliberate: Ghostscript inlines very small
  images, leaving the JBIG2 pass nothing to convert.
- The suite already contains the target patterns: `test_docthread.py` has 0
  mainloops and calls `do_*` handlers directly; `TestOcrmypdfVersionGate` in
  `test_savethread.py` unit-tests the OCRmyPDF version boundary by
  substituting the version.
- Only `.github/workflows/test.yml` runs pytest. The Fedora and openSUSE
  workflows are packaging-only. Debian testing is covered by the autopkgtest
  step of the Debian package build, not by a separate pytest job.

### Toolchain matrix

| Env | Runner / image | Libs from | Ghostscript | OCRmyPDF | jbig2 |
|---|---|---|---|---|---|
| latest | `ubuntu-latest` (~26.04) | pip | 10.06 | PyPI ≥17.6 | yes |
| stonking | `ubuntu:26.10` container + PPA | apt/PPA | 10.07 | 17.10 | yes |
| resolute | `ubuntu-26.04` + PPA | apt/PPA | 10.06 | 17.10 | yes |
| noble | `ubuntu-24.04` + PPA | apt/PPA | 10.02 | 16.13 | yes |
| jammy | `ubuntu-22.04` + PPA | apt/PPA | 9.55 (inferred) | 16.13 | no |
| Debian testing | deb autopkgtest | Debian archive | probe | probe | probe |

The repository contradicts itself on the resolute/stonking OCRmyPDF version:
the `test.yml` comments (2026-11-08) say 16.13, while
`packaging/ubuntu/build_ppa_stack.sh` (2026-11-09) builds 17.10 for those
series. The newer build policy is the better guide, but the actual runtime
version is a probe question. The matrix above is therefore a map of the
*axes*, not a table to hardcode.

The axes that change the saved output are:

- **Ghostscript**: at 10.06 and later, PDF/A rewrites a bilevel page as
  Flate; at 10.02 and earlier it keeps Group 4. This is why
  `_restore_bilevel_g4()` exists.
- **OCRmyPDF**: at 17.6 and later the lossless PDF/A image request is always
  made; before that it is conditional. `_PDFA_LOSSLESS_VERSION` and
  `_pdfa_image_compression()` encode this.
- **JBIG2 encoder**: present everywhere except jammy.

Those axes collapse the five Ubuntu jobs to three or four behavioural
classes, not five.

## Goals / Non-Goals

**Goals:**

- Make the save-PDF codec layer fast enough to use as an edit loop, without
  weakening the coverage gate or the test-code audit.
- Keep a small, real end-to-end proof of the save pipeline that runs in every
  supported environment, so distro drift is still caught.
- Make canary selection follow the environment's own capabilities, so a new
  distribution needs no new hardcoded table entry.

**Non-Goals:**

- Making the whole default test run free of external tools. Many remaining
  tests are deliberately end to end, such as user-defined tools and
  post-save hooks; converting the import and save modules is a follow-up.
- Parallelising the suite with xdist. Xvfb and GTK global state make that a
  separate, riskier change.
- Replacing every verifier subprocess (for example `pdftotext`) in this
  change. That can follow once the save path is fast.
- Changing the 99% coverage gate, the partial-branch ratchet, or the
  `test-coverage` capability.
- Removing the distro matrix or its real-package coverage.

## Decisions

### D1: Two explicit layers, selected by the existing `slow` marker

The save-PDF codec path has two layers. The fast layer covers the decision
logic and the conversion bodies with substituted inputs; the canary runs the
real save pipeline and carries the `slow` marker that `pyproject.toml` already
declares. `pytest -m "not slow"` selects the fast layer, `pytest -m slow`
selects the canary, and the existing `pytest` invocation runs both. The Debian
job runs the two layers as separate steps.

Alternative considered: a separate test directory. Rejected because the
marker already exists and keeps a canary next to the behaviour it proves.

### D2: Mock at the external-tool boundary, call `do_*` synchronously

Tests that are about save sequencing, metadata, cancellation or page handling
mock `_embed_text_layer()` (or `ocrmypdf.api._hocr_to_ocr_pdf`) and call
`thread.do_save_pdf(Request(...))` directly instead of driving a mainloop.
`test_do_save_pdf` already demonstrates the shape.

Mocking at `_embed_text_layer()` rather than at `ocrmypdf` keeps
`do_save_pdf()`'s own orchestration, progress reporting and cancellation
breakpoints real, so their coverage is retained.

Alternative considered: mocking the whole `SaveThread`. Rejected because it
would stop covering the orchestration the tests exist to protect.

The pattern is established here for the codec decisions and the save
orchestration tests. Converting the remaining import and analysis modules to
the same shape is a follow-up; those tests are not on the measured hot spot.

### D3: One universal invariant canary instead of six duplicates

The shipped contract is "a bilevel page is saved as Group 4 or JBIG2, never
Flate", because `_restore_bilevel_g4()` normalises whatever Ghostscript did.
A single canary asserts that invariant on a realistically sized page and
therefore exercises both the Flate-rewriting and G4-native Ghostscript
classes. Encoder-specific assertions (`/JBIG2Decode`, `jb2 < g4`) stay gated
on the encoder being present.

Alternatives considered: one canary per behavioural class (3–4 tests, each
running in one job) and keeping six tests but shrinking the page. The
single-invariant canary is smaller and covers both Ghostscript classes in
one run; shrinking the page breaks the JBIG2 pass because Ghostscript inlines
small images.

### D4: Probe-driven canary selection

Canaries decide what to assert from `ocrmypdf.__version__`,
`jbig2_available()` and a Ghostscript version probe, using the same helpers
the application uses. No per-job table.

This is required by the contradiction in the repository: the workflow
comments and the PPA build script disagree, so only a runtime probe is
truthful. It also means adding Debian testing needs no new code.

### D5: Keep Debian testing in the deb build's autopkgtest

The Debian package build already runs the suite through its autopkgtest step,
so Debian testing is covered without a second container job. Adding one would
duplicate the same run, add a pip/apt install step to maintain, and make the
workflow slower for no extra coverage.

Alternative considered: add a `debian:testing` container job. Rejected
because the autopkgtest already exercises the Debian testing toolchain and the
canary runs there with the rest of `pytest`.

### D6: Keep the real pipeline in the matrix

The canary runs the real save pipeline in the Ubuntu matrix jobs through the
full `pytest` invocation, and in Debian testing through the deb build's
autopkgtest. The fast layer also runs everywhere. The coverage gate still
measures only the shipped package, so the unit tests do not move the reported
percentage.

## Risks / Trade-offs

- **Branch coverage in the rewritten tests** → the six codec tests currently
  execute the bodies of `_convert_bilevel_images_to_jbig2()` and
  `_restore_bilevel_g4()`. Add small mocked-install unit tests for those
  bodies before deleting the six tests, and watch the partial-branch
  ratchet.
- **Lost distro drift detection** → keep the universal invariant canary in
  every matrix job, so a Ghostscript change that breaks the restore path
  still fails on the distro that ships it.
- **Probe drift** → a probe that reports the wrong capability would select
  the wrong assertions. Cover the probe and selection functions with unit
  tests, as `TestOcrmypdfVersionGate` already does for the version gate.
- **The launchpad gate** → the four PPA-backed distro jobs skip when
  launchpad.net is unreachable. Debian testing is unaffected because it runs
  from the Debian archive in the package build, not from the PPA.
- **Over-mocking** → a fast test can pass while the real toolchain is broken.
  Mitigation is the canary layer, not more mocks.

## Migration Plan

1. Add the env-free decision-logic unit tests and the conversion-body tests;
   measure before and after.
2. Convert the six codec tests into the universal invariant canary plus
   encoder-gated assertions; keep the old tests until the canary proves
   equivalent.
3. Add the Ghostscript probe, the probe-driven selection and the session-scoped
   PIL bilevel page.
4. Document the two layers; Debian testing stays in the deb build's
   autopkgtest.

Rollback is per step: each step is an independent test-only change, so a
regression can be reverted without touching application code.

## Follow-up

- Replace the remaining per-test `convert` image generation in the save and
  import modules with session-scoped PIL fixtures.
- Convert the import and analysis tests that only check chain callbacks or
  stored state to synchronous `do_*` calls with mocked externals.
- Confirm the per-toolchain canary logs in the Ubuntu jobs and in the Debian
  autopkgtest.

## Open Questions

- The exact OCRmyPDF version the resolute and stonking PPA currently serves
  (16.13 or 17.10). The probe resolves it at runtime, so it does not change
  the design.
- Whether to add an in-process PDF text extractor to replace `pdftotext`
  verifier spawns. Deferred; it is a dependency decision, not part of this
  layering.
- Whether xdist is worth pursuing after the fast layer exists. Deferred.

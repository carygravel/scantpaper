# Proposal

## Why

A full local test run takes about 2 min 38 s without coverage (roughly 3.5 min
under the 99% coverage gate CI enforces), and about a quarter of that is six
near-duplicate JBIG2/codec tests that each run a real
img2pdf → ocrmypdf → Ghostscript → jbig2 pipeline over an A4-sized bilevel
page. The cost grew feature by feature: each PDF-save change added more
end-to-end coverage rather than unit coverage, and the save pipeline calls
real external binaries on every path.

## What Changes

- Split the save-PDF codec path into a fast layer and a small real-toolchain
  canary layer. The fast layer covers codec and compression decisions with
  substituted inputs and unit-tested conversion bodies; the canary runs the
  real save pipeline and carries the `slow` marker, so it is selected
  explicitly rather than by the fast layer.
- Cover codec and compression decision logic with unit tests that do not
  depend on the installed tool versions, extending the existing
  `TestOcrmypdfVersionGate` pattern.
- Replace the six near-duplicate real-pipeline codec tests with one universal
  invariant canary (a bilevel page is saved as Group 4 or JBIG2, never
  Flate) plus encoder-gated assertions, so the real save pipeline is still
  exercised end to end.
- Select canary assertions from runtime capability probes
  (`ocrmypdf.__version__`, `jbig2_available()`, Ghostscript version) rather
  than a hardcoded per-distribution table, because the repository's workflow
  comments and `packaging/ubuntu/build_ppa_stack.sh` disagree about which
  OCRmyPDF version each distribution runs.

Converting the rest of the suite's import and save modules to mocked `do_*`
tests and PIL fixtures is a follow-up, not part of this change. The codec
tests were the measured hot spot; the remaining external-tool tests cover
behaviour that is deliberately end to end, such as user-defined tools and
post-save hooks. Debian testing is already covered by the autopkgtest step of
the Debian package build, so no new matrix job is added.

## Capabilities

### New Capabilities

- `test-suite-layering`: how the save-PDF codec path separates a fast layer
  from a small real-toolchain canary and how the canary is selected.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/dependencies.py` — a Ghostscript version probe and a pure
  decision helper for the PDF/A bilevel rewrite boundary.
- `src/scantpaper/tests/test_1111_save_pdf.py` — the universal invariant
  canary, encoder-gated assertions, a probe-driven expectation helper and a
  session-scoped PIL-built bilevel page.
- `src/scantpaper/tests/test_savethread.py` and
  `src/scantpaper/tests/test_dependencies.py` — unit coverage for the
  conversion bodies, the probe and the codec decisions.
- `README.md` and `AGENTS.md` — how to run the fast layer and the canary.
- No user-visible behaviour change, no new CI job and no change to the
  coverage threshold or the test-code audit.

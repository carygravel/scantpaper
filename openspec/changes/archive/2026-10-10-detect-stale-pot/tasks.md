## 1. Template generation and fingerprint

- [x] 1.1 Refactor `dev/generate_pot.py` to expose a `generate_template()`
      helper that returns the template text, keeping the CLI writing to the
      default path unchanged.
- [x] 1.2 Add a `fingerprint_pot(pot_text: str) -> list[str]` function to
      `dev/check_launchpad.py` that returns the sorted, unique `msgid` strings
      from a generated template, correctly reading multi-line `msgid` and
      `msgid_plural` blocks and ignoring the header and `#:` reference comments.

## 2. Baseline and local-state signal

- [x] 2.1 Extend the baseline document with an `uploaded_pot` section holding
      the sorted msgid list, a derived digest, and a msgid count; treat an
      absent section as local state "not determined".
- [x] 2.2 Compute the local message set (via `--pot <path>` when given,
      otherwise `generate_template()`) and compare it against the baseline
      `uploaded_pot` section, producing a `local_pot_changed` signal plus the
      added/removed msgid lists.
- [x] 2.3 Add a `local_pot` section to the JSON payload (`changed`, `added`,
      `removed`, `msgid_count`) and a separate top-level `local_pot_changed`
      signal, plus the local signal in the human-readable report, keeping it
      distinct from the upstream `changed` signal so the two directions can
      be reported and filed separately.

## 3. Stamping action

- [x] 3.1 Add a `--record-pot` option that records the current pot's
      fingerprint into the baseline `uploaded_pot` section, refusing when the
      pot cannot be read, and honouring `--dry-run`.

## 4. Tests

- [x] 4.1 Unit-test `fingerprint_pot` against a fixture pot with multi-line
      msgids, plural forms, and `#:` reference comments.
- [x] 4.2 Extend `src/scantpaper/tests/test_launchpad.py` (hermetic
      `file://` fixtures + `--pot`) to cover: new strings reported as stale,
      moved strings / reordering / header-only changes reported as unchanged,
      `--record-pot` stamps then reports unchanged, and absent baseline section
      reported as not determined.
- [x] 4.3 Run `pytest`, `ruff check`, `ruff format` and `ty check` clean.

## 5. Scheduled workflow

- [x] 5.1 Update `.github/workflows/translations-check.yml` to generate the
      template and report local staleness, filing a distinct "new strings
      ready to upload" issue without closing the upstream-change issue.

## 6. Documentation

- [x] 6.1 Update `release_procedure.md` with the new check and `--record-pot`
      step, and `README.md` if any user-visible behaviour changed.
- [x] 6.2 Update `AGENTS.md`'s translation-workflow section if needed.

## 1. Test-first coverage for manual alternation

- [ ] 1.1 Add tests: toggle is visible with flatbed + `allow_batch_flatbed`
  + `num_pages == 1` (and still hidden for non-flatbed / no-batch)
- [ ] 1.2 Add tests: consecutive single-page scans with the toggle enabled
  alternate parity (odd, even, odd) without resetting between jobs
- [ ] 1.3 Add tests: parity resets to odd when the toggle is turned off and
  enabled again; multi-page batch start still resets to odd
- [ ] 1.4 Run the new tests and confirm they fail for the right reason

## 2. Gate split (D1)

- [ ] 2.1 Split `_flatbed_batch_active` into a source gate (flatbed +
  `allow_batch_flatbed`) and a batch gate (source gate + `num_pages > 1`)
- [ ] 2.2 Drive checkbox visibility and `_alternating_rotation_active` from
  the source gate; keep batch-only consumers on the batch gate

## 3. Parity reset semantics (D2)

- [ ] 3.1 Reset `_alternate_flatbed_count` in `clicked_scan_button_cb` only
  when `num_pages > 1`
- [ ] 3.2 Reset the counter when the alternating-rotation toggle is turned
  off (`toggled` signal), keeping it in-memory only (D3)

## 4. Documentation

- [ ] 4.1 Update README book-scan FAQ with the manual one-page-at-a-time
  workflow and the toggle-off reset rule
- [ ] 4.2 Add a changelog entry under the current unreleased section

## 5. Verification

- [ ] 5.1 Full `pytest` run passes with coverage at or above the configured
  threshold and no new uncovered lines
- [ ] 5.2 `ruff format` + `ruff check` and `ty check .` are clean
- [ ] 5.3 `openspec validate manual-alternating-rotation --type change
  --strict` passes; sync delta specs into
  `openspec/specs/flatbed-alternating-rotation/spec.md`

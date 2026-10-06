## Context

Alternating rotation currently keys everything off `_flatbed_batch_active`
(scan_menu_item_mixins.py), which requires flatbed + `allow_batch_flatbed` +
`num_pages > 1`. That helper gates both checkbox visibility and
`_alternating_rotation_active`, so single-page scanning can neither show the
toggle nor apply parity. Parity (`_alternate_flatbed_count`) is reset to 0 in
`clicked_scan_button_cb`, which fires at the start of every scan job, so it
would reset to odd even if the gate were relaxed. See proposal.md for
motivation.

## Goals / Non-Goals

**Goals:**
- Make the toggle visible and effective for flatbed scanning with
  `num_pages == 1`.
- Manual parity persists across consecutive scans and resets only when the
  user explicitly turns the toggle off.
- Keep multi-page batch behaviour (reset at batch start) and ADF/duplex
  behaviour identical to today.

**Non-Goals:**
- Persisting the parity counter across application restarts or sessions.
- Changing rotation timing relative to OCR/cleaning (already covered by
  `flatbed-alternating-rotation`).
- Alternation for ADF/duplex or non-flatbed sources.

## Decisions

**D1 — Split the flatbed gate into a source gate and a batch gate.**
Replace the single `_flatbed_batch_active` predicate with two: a source gate
(flatbed selected + `allow_batch_flatbed`) and a batch gate (source gate +
`num_pages > 1`). Visibility and `_alternating_rotation_active` use the
source gate; only batch-mode behaviours keep using the batch gate.
*Alternative:* add a `num_pages >= 1` special case to the existing helper —
rejected, it buries the manual-mode distinction in one predicate and forces
every caller to reason about which mode it means.

**D2 — Reset parity in two places only.**
1. In `clicked_scan_button_cb`, reset only when `num_pages > 1` (a real
   batch is starting), preserving the existing "second batch restarts with a
   front page" behaviour.
2. On the toggle's `toggled` signal, reset when it becomes inactive — the
   "explicitly turned off" rule.
In manual mode (`num_pages == 1`) the job-start reset is skipped, so the
counter keeps advancing across individual scans.
*Alternative:* reset on scan-dialog close or device change — rejected, the
spec fixes the reset trigger at explicit toggle-off; extra implicit resets
would surprise a user who briefly closes and reopens the dialog mid-book.

**D3 — Counter remains in-memory only**, as today (`getattr` default 0).
The setting `"alternate rotation"` persists; the counter deliberately does
not. A restarted app starts a manual sequence at an odd page.

## Risks / Trade-offs

- [Toggling off mid-book silently restarts parity at odd, which may flip the
  next page relative to expectation] → Acceptable and explicit: the spec
  documents the reset as the user's action; the toggle label and log line
  (`rotate facing`/`alternate rotation`) make it observable.
- [Parity carries over from a finished multi-page batch into the next
  manual scan (and vice versa: manual scans then a batch)] → Intended
  continuity for the manual workflow; batch starts still reset, so books
  scanned as batches are unaffected.
- [A hidden toggle (e.g. source switched to ADF) retains the counter, and
  returning to flatbed resumes parity] → Matches the "only explicit
  toggle-off resets" rule; adding an implicit reset would contradict the
  spec.
- [Tests may rely on the old per-job reset in single-page mode] → Update
  the existing parity tests alongside the new manual scenarios (tasks.md).

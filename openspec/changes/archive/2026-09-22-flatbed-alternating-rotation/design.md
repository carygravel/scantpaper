## Context

See `proposal.md` for motivation. The relevant current state:

- Flatbed batch scans are single-sided; `_insert_target()` in
  `dialog/scan.py` always yields `side = "facing"` for them, so rotation-on-scan
  always applies the `rotate facing` setting (`scan_menu_item_mixins.py:427`).
- Rotation happens first in the post-import chain (`document.py:265`,
  rotate → unpaper → UDT → OCR), so deciding the angle per page at scan time
  yields correctly rotated OCR, previews, and thumbnails.
- The user configures one rotation angle via `RotateControls`; the alternate
  physical requirement is always exactly that angle + 180° (mod 360°), because
  a flipped sheet aligned to the same straight edge is rotated 180° relative
  to its front.

## Goals / Non-Goals

**Goals:**

- One visible, opt-in control that alternates per-page rotation by parity in
  flatbed batch scans, without touching the duplex state machine
  (`_insert_target`, `max_pages`, batch interleave, the "scan reverse?"
  prompt).
- Use a single configured angle; derive the second automatically.
- Persist the toggle across sessions.

**Non-Goals:**

- No changes to ADF or duplex rotation semantics (spec: `page-numbering`).
- No new angle input UI (no `can_duplex` unblocking, no second angle row).
- No two-pass/stack-flip workflow; single-batch alternation only.
- No change to page ordering or insertion logic.

## Decisions

### 1. Second angle is derived, not stored
Even pages rotate by `(facing_angle + 180) % 360`. This is physically exact
for the targeted workflow, keeps a single source of truth for the angle, and
avoids making the two `RotateControls` angle rows contradict each other.
> Alternative rejected: reuse the `rotate reverse` setting for even pages.
> It would require exposing the side/angle rows on flatbed-only devices
> (currently hidden when `can_duplex()` is False, `postprocess_controls.py:106`)
> and re-purposes canonical duplex terminology in a non-duplex context, for a
> pair of angles that can never actually differ by anything but 180° here.

### 2. Parity is derived in `_new_scan_callback`, not in the scan dialog
`scan_menu_item_mixins._new_scan_callback` already chooses the angle right
before `import_scan`. Add a batch-local counter there:

```
rotate = settings["rotate facing"]
if side == "reverse":
    rotate = settings["rotate reverse"]
elif alternating_active:          # toggle on AND flatbed batch conditions
    count += 1
    if count even: rotate = (rotate + 180) % 360
```

- The counter resets to 0 in the existing `clicked_scan_button_cb`, which fires
  at the start of every `scan()` (`dialog/scan.py:547`) — no new signal needed.
- `alternating_active` re-checks the dialog's dynamic state at emit time:
  `flatbed_selected()` AND `allow_batch_flatbed` AND `num_pages > 1`, so the
  toggle cannot leak into ADF/duplex or single-page scans even if the source
  changes after the user enabled it.
- The `side == "reverse"` branch is untouched, keeping duplex behaviour intact
  even though it is unreachable in flatbed.
> Alternative rejected: extend the `new-scan` signal to carry the batch index.
> Cleaner in principle, but churns the public signal contract and its many test
> connections for no behavioural gain; the counter lives entirely inside one
> existing handler and its existing start hook.

### 3. Toggle lives next to `RotateControls` in the Postprocessing tab
A `Gtk.CheckButton` ("Alternate rotation every 2nd page" / book-scanning
tooltip) is added in `add_postprocessing_options()`, bound to a new setting.
Visibility is driven from the same refresh path that today recomputes
`RotateControls.can_duplex` (`_update_postprocessing_options_callback`),
extended to consult `flatbed_selected()` + `allow_batch_flatbed` + `num_pages`
and to listen to `changed-num-pages` as well as `changed-scan-option`.
> This keeps the toggle out of sight for every configuration the spec says must
> not show it, with no change to the dialog widget layout.

### 4. Configuration
New boolean setting `alternate rotation`, default `False`, added alongside
`rotate facing`/`rotate reverse` in `config.py`. The toggle is written back to
`settings` in `clicked_scan_button_cb`, matching how the rotate angles are
persisted today. Test fixtures that construct minimal settings dicts use the
config default, so no existing fixture must gain the key.

## Risks / Trade-offs

- **Stale parity after an aborted batch** — if a batch is cancelled part-way
  and pages re-scanned, the counter restarts at 0; the first re-scanned page is
  physically a front, so parity stays correct. Low risk.
- **Toggle leak into non-flatbed scans** — mitigated by recomputing
  `alternating_active` from live dialog state at each emit, not from the
  toggle alone.
- **Hidden state in the mixin** — the counter is instance state; reset on every
  `clicked-scan-button`, so drift is bounded to one batch. Acceptable for the
  surgical scope.
- **Spec precedent** — the `page-numbering` delta scopes the "parity never
  influences rotation" rule; the alternation applies only under an explicit
  opt-in toggle, preserving the duplex contract.
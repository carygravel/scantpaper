## Context

See proposal.md — Why. The crash lives in the profile-apply path of
`src/scantpaper/dialog/scan.py`. `set_profile(name)` (line 1173) connects a
one-shot handler `do_changed_current_scan_options` on the
`changed-current-scan-options` signal, pushes the profile UUID onto
`self.setting_profile`, then starts an async recursive apply
(`set_current_scan_options` → `_set_option_profile` → … → `_finalize_profile`
→ `_complete_profile_setting`). When the apply finishes,
`_complete_profile_setting` emits `changed-current-scan-options`, and the
handler reads `self.setting_profile[0]` (line 1182) to match against the
emitted UUID and commit the profile name.

The handler indexes the stack unconditionally. The log shows this firing with
an already-empty `setting_profile`, raising `IndexError: list index out of
range` (three times in one session). The code even carries a stale comment
acknowledging the race (line 1184).

## Goals / Non-Goals

**Goals:**
- Applying a profile never raises `IndexError` or any exception on completion.
- The profile name is still committed and the dialog cursor restored when the
  apply genuinely finishes.
- A regression test reproduces the re-entrant completion and asserts no
  exception.

**Non-Goals:**
- Not changing the async apply ordering or the worker-thread architecture.
- Not changing the `scan-option-convergence` reverted-option logic.
- Not fixing the unrelated flatbed/ADF source behaviour from the same log
  (that is hardware behaviour, not reproduced as a bug).

## Decisions

### 1. Make the completion handler defensive and consume the stack

`do_changed_current_scan_options` currently does `uuid = self.setting_profile[0]`.
Change it to guard against an empty stack and to consume the entry only when
it matches the emitted UUID:

```python
def do_changed_current_scan_options(_1, _2, uuid_found):
    if not self.setting_profile:
        return
    if self.setting_profile[0] == uuid_found:
        self.disconnect(signal)
        self.setting_profile.pop(0)
        self._profile = name
        self.emit("changed-profile", name)
```

- **Rationale:** A re-entrant or duplicate `changed-current-scan-options` emit
  during finalize can reach this handler when no `set_profile` is pending.
  Guarding the read removes the `IndexError`. Consuming with `pop(0)` happens
  only on a match, so an unrelated completion (e.g. an option reload emitted
  with an empty UUID while the pending profile is still on the stack) cannot
  clear the stack before the genuine completion arrives; and the handler is
  disconnected on the first match, so a duplicate emit cannot commit the same
  profile twice.
- **Alternative considered:** `uuid = self.setting_profile.pop(0)` before
  comparing. Rejected: popping unconditionally consumes the pending profile's
  UUID on the first unmatched completion (the reload path emits with an empty
  UUID), so the genuine completion then finds an empty stack and the profile
  name is never committed (`test_reloads_in_profile` regressed).
- **Alternative considered:** `if self.setting_profile: uuid = self.setting_profile[0]`
  (read-only, no pop). Rejected as the sole change: after a match the handler
  disconnects, so the stack is left non-empty and the profile name commit still
  works, but consuming the matched entry keeps the stack accurate for any
  deeper pending `set_profile` entry.

### 2. Regression test at the dialog level

Add a test that drives `set_profile` through the `sane_scan_mocks` fixture and
arranges for the completion emit to reach the handler after the stack has been
cleared. A genuine single apply must still commit the profile name and restore
the cursor (the clean path), and the re-entrant completion must not raise
`IndexError` (detected via the traceback PyGObject logs to stderr, since
handler exceptions are logged, not propagated). Follow the existing mock
patterns in `test_06198_dialog_scan_sane.py`.

## Risks / Trade-offs

- [Empty-stack emit could hide a genuinely lost commit] → Mitigation: the
  normal, single-emit path still commits the profile (the guard only returns
  early for re-entrant/duplicate emits); the regression test asserts `_profile`
  is committed on the clean path.
- [`pop(0)` on a list is O(n)] → Mitigation: the pop now runs only on a
  matched completion and removes a single entry; the stack holds at most a
  handful of profile UUIDs, so the cost is negligible. `collections.deque`
  would be over-engineering for this size.

## Open Questions

None — the fix is contained and the regression scenario is fully specified.

## Context

See proposal.md - Why. In short: `_update_options` (scan.py:714) re-applies the
whole `current_scan_options` after every reload, and the current safety net is
a single global counter (`num_reloads`) tripped at `n·(n+1)/2` reloads
(scan.py:355). It counts *total* reloads, not *reverted* options, so a single
coupled pair (e.g. `quick-format` ↔ `scan-area` on the Epson GT-20000) burns
the whole budget (~2278 reloads, ~15s spinner in the user's log) and then
aborts the entire apply with a generic dialog.

Config lives in `~/.config/scantpaperrc`; `default-scan-options` is applied to
the scan dialog on every startup via `set_current_scan_options`
(scan_menu_item_mixins.py:426-429). Two existing precedents to build on:
`SANE_INFO_INEXACT` already causes per-option retreat (scan.py:1270-1281), and
`Profile.remove_backend_option_by_name` is already used to prune buttons before
re-apply (scan.py:753-760).

## Goals / Non-Goals

**Goals:**
- Applying a scan-option profile always terminates, converged in the common
  case, with a specific option dropped when the backend won't honor it.
- The dropped option is no longer re-applied by later reloads nor re-saved
  into the rc config ("self-healing" defaults).
- Keep a total reload cap, but linear in the option count instead of
  triangular, so a hostile backend still cannot hang the dialog.
- Identify the culprit in the log instead of a blanket bug-report dialog.

**Non-Goals:**
- Detecting or special-casing *deprecated* scan options (no SANE flag exists;
  separate concern, see exploration).
- Changing how the scan dialog displays options, or the widget reset points.
- Migration of already-saved conflicting `default-scan-options`; the new
  apply semantics heal them naturally on the next startup.

## Decisions

### D1: Per-option re-apply budget instead of one global counter
Count, per option name, how many times `_set_option_profile` decides to
*set* that option during one top-level apply. Give up on the option once its
count reaches K (K=2):

```
count[name] < K  → count[name] += 1; set_option(name, val)
count[name] >= K → drop: remove from current_scan_options, log, skip
```

Rationale: each genuine set that is reverted by a reload causes the option to
appear non-within-tolerance again on the next re-apply pass (checked at
scan.py:1244). So the counter naturally increments *only* on actual reversion
churn — a healthy option is set exactly once per apply and never counted twice.
Alternatives considered: (a) time-based caps — fragile, unrelated to the
mechanism; (b) detecting oscillation patterns between pairs — over-engineered,
the per-option count already implies it.

K=2 means set → reverted → set → reverted → dropped on the third attempt. It
allows one retry for transient readback drift while treating a second revert
as definitive. K is a module constant, not a config option.

### D2: Counters owned by the top-level apply, reset at set_current_scan_options
A small per-dialog dict (`_reverted_option_counts`), cleared in
`set_current_scan_options` (scan.py:1160) which is the single entry point for
profile applies (default profile, saved profile, paper/profile changes all
route through it or its direct helper). The nested re-apply inside
`_update_options` (scan.py:763) calls `_add_current_scan_options`, not
`set_current_scan_options`, so it inherits the parent's counters instead of
resetting them — satisfying the "recursive re-entry shares the budget"
requirement.

Clearing in the `available_scan_options` setter was rejected: it fires on
every reload (`_update_options` line 748) and would zero the counters mid-apply.

User-initiated sets (widget callbacks, `uuid=None`) reset that option's count
too, mirroring the existing `num_reloads = 0` in the widget callbacks
(sane.py:246-328), so a user manually overriding an option always gets a fresh
budget and is never penalised by apply-time drops.

### D3: Linear total-reload backstop replaces the triangular limit
Keep `num_reloads` as a global backstop but change its bound to a linear
function of the option count:

```
reload_recursion_limit = 3 * num_options
```

Rationale: with the per-option rule, each option is set at most K=2 times and
each RELOAD_OPTIONS costs one reload, so the apply cannot legitimately exceed
~2n reloads; 3n adds slack for the initial option fetch and paper/geometry
side-effects. The triangular `n·(n+1)/2` over-grants an O(n²) budget that only
served to let a runaway spin for seconds before failing. The backstop now only
fires for a genuinely hostile backend; when it does, it logs an informative
message (the old user-facing dialog stays as a last resort).

### D4: Drop = remove from current_scan_options
On give-up, call `current_scan_options.remove_backend_option_by_name(name)`
on the *live* object. `_update_options` clones it (scan.py:737) at entry, so
the in-flight re-apply finishes on the stale clone, and every subsequent
re-apply and config save use the pruned profile. The widget is left showing
whatever the backend reports, so the user still sees the real state.

## Risks / Trade-offs

- [False drop of a legitimately converging option] → K=2 requires two actual
  reverts; a healthy apply sets each option once, so only genuine churn is
  counted. Scope is one apply; a user manual override resets the budget.
- [User's saved defaults change without explicit acknowledgement] → the drop
  is visible in the log (WARNING naming the option and reason) and matches
  backend reality; the widget still shows the actual value.
- [Exotic backend that needs >K sets to finally converge] → acceptable
  trade-off; the option can be re-set manually via its widget, which grants a
  fresh budget.
- [Existing tests asserting the old error-dialog behaviour] → test_0608
  `test_infinite_reloads`, test_06093 `test_infinite_reloads_due_to_inexact`,
  and test_0601 need their expectations updated to per-option-drop semantics.
- [Linear bound constant feel arbitrary] → derived from the mechanism
  (≤2 sets/option × ≤1 reload/set); pinned by a test.

## Migration Plan

No data or config migration: `default-scan-options` entries that conflict are
silently pruned by the first successful apply, which heals the rc file on the
next write. Rollback is a clean revert of the change; no deployed state is
transformed destructively.

## Open Questions

None that would change the specs or task breakdown. (The exact K value is a
constant pinned by tests; 2 is the recommended default.)
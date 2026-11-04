# Design

## Context

See `proposal.md` for motivation. The current filtering lives in
`_apply_device_blacklist()` in `scan_menu_item_mixins.py` and is called
only from `_changed_device_list_callback()`. The scan dialog owns the
`SimpleNamespace(name, vendor, model, label)` entries and emits
`changed-device-list`; the application mixin owns `self.settings` and is
therefore the only layer that can persist a blacklist edit. The cached
device list is installed directly in `scan_dialog()` and bypasses the
callback, and device entries are serialised with all four fields.

## Goals / Non-Goals

**Goals:**

- One matching rule that accepts the visible label, the backend name, or
  a sensible substring such as `CameraA`.
- Deterministic, crash-free behaviour when the filter empties the list.
- One-click blacklisting that cannot produce an invalid or
  over-escaping-prone value.
- Hints that make the preference self-explanatory.

**Non-Goals:**

- Changing the preference format from a single regular-expression
  string.
- Replacing the blacklist with a per-device persisted selection list.
- Filtering devices inside the SANE backend or changing
  `sane.get_devices()`.
- Auto-detecting cameras or other non-scanner devices.

## Decisions

### Match one composite haystack, not a single field

Build the searched text per device from its label, name, vendor, and
model, separated by newlines, then run `re.search(pattern, haystack,
re.IGNORECASE | re.MULTILINE)`. This keeps existing exact-name values
working while making the label the natural thing to type.

Alternatives considered:

- *Match the name only*: preserves the current contract but leaves the
  user guessing, which is the reported bug.
- *Match the label only*: breaks users whose saved blacklist uses a
  backend name and fails for cached entries that lack a label.
- *Try the pattern against each field separately*: equivalent result,
  more branches, and harder to anchor with `^`/`$`.

`re.MULTILINE` lets `^` and `$` anchor to individual fields; `^v4l:`
still targets the backend-name line. Drop `re.DOTALL` and `re.VERBOSE`,
because they make a literal label with spaces behave unexpectedly; a
space in the pattern now matches a space. This is the behavioural change
that makes the reporter's `Noname CameraA: CameraA` text meaningful.

### Filter into a list, then decide what emptiness means

Extract the filtering loop into a pure helper that returns a new list
instead of mutating in place. Callers then check emptiness once and
share the existing "No devices found" process-error path. The dialog
must not index `device_list[0]` after filtering; scanning stays
unavailable when the result is empty. Keeping the pure helper also makes
the matcher directly unit-testable, so tests can use a pattern that
differs from the device name and would fail under the reversed argument
order.

The existing `_apply_device_blacklist` wrapper can remain for the
`changed-device-list` path, but it should only assign `widget.device_list`
when the filtered list differs. That avoids a pointless
`changed-device-list` re-emission and keeps the cache write identical.

### Apply the filter at every entry point

There are three paths that populate the selector: a fresh SANE fetch, a
cached list, and command-line device arguments. Apply the same filter to
the cached list before it is assigned, so editing the preference affects
the next scan dialog without a rescan. Command-line device lists are
explicit user intent and should not be filtered; this preserves the
current behaviour of `--device`.

A fresh fetch already filters in its callback. The cached path becomes
symmetric by using the same helper. Whenever the filter empties a cached
list, report no devices rather than installing an empty selector.

### Emit a signal for the one-click action

Add a `blacklist-device` signal (payload: the selected device's label or
name) to the scan dialog and a small button next to the Device combo.
The button is sensitive only when a real device is selected (not the
"Rescan for devices" row and not `NO_INDEX`). The mixin handles the
signal, appends the escaped label to `settings["device blacklist"]`,
refreshes the dialog's list, and persists the setting through the
normal preference-save path.

Why not let the dialog write settings directly: the dialog has no
settings object, and every other preference change flows through the
mixin. A signal keeps that boundary intact and lets the action reuse the
existing persistence and validation code.

### Append with alternation, not a new syntax

Store the new entry as `existing|escaped_label`, or just
`escaped_label` when the blacklist is empty. `|` has the lowest regex
precedence, so appending preserves the user's existing expression. Use
`re.escape()` so labels containing `(`, `)`, `.`, `/`, or spaces match
literally. Skip the append when the escaped entry is already present to
avoid unbounded growth after repeated clicks. The preference's
validation (`re.search(pattern, "dummy_device")`) remains the guard
against a hand-edited invalid pattern.

### Put the hint where the value is entered

Update the preference tooltip and add an entry placeholder that name the
matched fields and show an example such as `Camera` or `v4l:.*`. The
label stays "Device blacklist"; no new preference row is added.

## Risks / Trade-offs

- **Broad patterns hide the scanner too** → The empty-result path reports
  "No devices found" instead of crashing; the user can clear the
  preference or use **Blacklist this device** for a precise value.
- **Case-insensitive matching may catch unintended devices** → The
  matched haystack is limited to device metadata, and the one-click
  action produces an escaped, device-specific pattern.
- **Appending to an existing advanced pattern could surprise the user**
  → Alternation preserves the existing expression, and the resulting
  value stays visible and editable in the preference.
- **Cached entries from older versions may lack a label** → Fall back to
  the backend name when building the haystack and when writing a
  one-click pattern.

## Migration Plan

No migration is required. The configuration key, its type, and the
cached device-list schema are unchanged. Previously saved values that
were exact backend names continue to match because the name remains in
the haystack. Rollback is a code revert; no stored data needs undoing.

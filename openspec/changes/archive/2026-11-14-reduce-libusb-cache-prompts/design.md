# Design

## Context

See `proposal.md` for motivation. The relevant current behaviour:

- `ScanMenuItemMixins.scan_dialog` (`scan_menu_item_mixins.py`) creates the
  scan dialog. When `cache-device-list` is enabled, the stored list is not
  empty and `scan` is false, it assigns the stored list to the dialog;
  otherwise it calls `get_devices()`.
- Assigning the `device_list` property emits `changed-device-list`
  (`dialog/scan.py`). `_changed_device_list_callback` applies the blacklist,
  asks the libusb question, stores the list when caching is enabled, and then
  selects the default device.
- The signal carries only the list, so the callback cannot tell a cache load
  from a fresh search. `_confirm_libusb_caching` therefore fires for both,
  which is the reported annoyance.
- `_confirm_libusb_caching` shows an OK-only `Gtk.MessageDialog`; anything
  other than OK turns `cache-device-list` off. Its body is built by
  concatenating two msgids, and the concatenation has no separating space
  between sentences.
- Settings live in `config.py`; unknown-to-old-config keys fall back to the
  defaults, so a new key needs no migration.
- Dialogs with a "Don't show this message again" checkbox exist in
  `session_mixins._ask_question`, but that machinery stores responses by
  message text in `settings["message"]`; the libusb question is not a
  message-dialog user and is better served by a dedicated setting.

## Goals / Non-Goals

**Goals:**

- Tell a cache load apart from a new list without comparing list contents.
- Ask at most once per caching event, and only when a new list is stored.
- Make "cache and stop asking" persistent and testable.
- Keep the failure path unchanged.

**Non-Goals:**

- A Preferences control to re-enable the warning; suppression is one-way, as
  with the existing stored message responses.
- Fixing the inert "Cache device list" checkbox in the error dialog.
- Automatic rescan or rematch after a failed open.
- Changing the `changed-device-list` signal signature or moving the cache
  decision out of the mixin.

## Decisions

### D1: Mark cache loads with a short-lived flag on the mixin

Add a class attribute `_device_list_from_cache: bool = False` to
`ScanMenuItemMixins`. In `scan_dialog`, set it to `True` only around the
assignment of the stored list, and reset it in a `finally` block. The
`device_list` setter emits `changed-device-list` synchronously, so
`_changed_device_list_callback` sees the flag for exactly that emission.
Fresh searches, command-line device lists and forced rescans never set it.

In the callback, compute `from_cache = self._device_list_from_cache` and
store the list when caching is enabled and either `from_cache` is true or
`_confirm_libusb_caching` returns true. Cache loads therefore keep the
current side effect of re-storing the filtered list (which prunes
blacklisted entries) but never ask.

- **Why a flag and not a comparison:** a re-scan can legitimately return the
  same device names, so comparing the incoming list with the stored one
  would suppress a question that should be asked. Comparing object identity
  fails too, because the cached path passes a filtered copy.
- **Why not extend the signal:** changing `__gsignals__` to carry a source
  argument would touch the dialog's public contract for one consumer and
  every emit site. A call-scoped flag is local and synchronous.
- **Why on the mixin, not the dialog:** the callback lives on the mixin and
  reads the flag in the same call. A class-level default keeps test doubles
  that subclass the mixin working without extra setup.
- **Risk of leakage:** the property setter calls `set_device_list` and then
  `emit` directly, and the `try/finally` in `scan_dialog` clears the flag
  even if the setter raises. A leak would require an asynchronous emit,
  which this signal does not have.

### D2: One boolean setting and one checkbox

Add `"warn-libusb-cache": True` to `DEFAULT_SETTINGS`.
`_confirm_libusb_caching` returns true immediately when the list has no
`libusb` name or the setting is false. Otherwise it shows the dialog; OK
stores the list and, when the new "Don't ask again" checkbox is active, sets
`warn-libusb-cache` to false. Declining keeps the current behaviour:
`cache-device-list` becomes false and the suppression flag is untouched.

Change the dialog from `ButtonsType.OK` to `ButtonsType.OK_CANCEL` so the
negative answer is visible instead of being a window close, and add
`Gtk.CheckButton.new_with_label(_("Don't ask again"))` to the message area.
The checkbox is honoured only with OK; declining with it selected does not
record suppression, which keeps "don't cache" and "never ask again" from
contradicting each other.

- **Why a positive setting:** `warn-libusb-cache=True` reads directly at the
  decision point and matches `cache-device-list`. The inverse
  (`suppress-libusb-cache-warning`) would make every default and check a
  double negative.
- **Why not reuse `settings["message"]`:** that mechanism keys stored
  responses by message text and is used by the generic message dialog. The
  libusb question needs one policy bit, not a per-text response, and it is
  shown from a different code path.
- **Alternative considered:** a Preferences checkbox that mirrors the
  suppression. Deferred as a non-goal to keep this change focused; the
  setting is readable and editable in `~/.config/scantpaperrc`.

### D3: Replace the concatenated body with one msgid

Build the body from a single string, for example: "Caching the device list
with libusb devices is not recommended, as they can change between reboots.
Cache them anyway?" This fixes the missing space between the current two
sentences and removes a translation fragment, which `dev/check_po.py` flags.
The title stays "Really cache libusb device names?".

The new body is a new msgid, so existing translations fall back to English
until reviewed; the normal workflow applies: regenerate the template, seed
`#, fuzzy` entries, run `dev/check_po.py`, and upload to Launchpad before the
release. "Don't ask again" is a second new msgid.

- **Alternative considered:** keep both existing msgids and only add the
  checkbox. Rejected because the rendered text is already missing a space
  and the concatenation is an advisory in the catalog checks; touching the
  dialog is the moment to fix it.

## Risks / Trade-offs

- **The prompt disappears on cache loads by design.** Users who treated it
  as a per-start reminder lose that reminder. Mitigation: the question is
  still asked whenever a new list is cached, which is the only point where
  the answer affects what is stored.
- **Suppression is one-way.** A user who wants the prompt back must edit the
  config file. Mitigation: document the setting; a Preferences toggle is a
  natural follow-up if requested.
- **Translation churn.** A new body msgid and a new checkbox label will be
  untranslated (fuzzy) until reviewed. Mitigation: the release gate shows
  English rather than a bad translation, and the catalog checks catch format
  errors.
- **Flag leakage into a later event.** Mitigation: synchronous emit plus
  `try/finally`; a focused test asserts that a cache load is silent and the
  next fresh list still asks.
- **Old configs lack the new key.** Mitigation: the default is applied by
  the settings loader; no migration is needed.

## Migration Plan

No data or config migration. Existing configs get `warn-libusb-cache=True`
from the defaults. Rollback is reverting the touched files; the unknown key
is ignored by older builds.

## Open Questions

None.

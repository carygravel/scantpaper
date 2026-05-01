"Provide _() function for translations"

import gettext
import logging
import os

localedir_pkg = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "locale")
locales_to_try = [localedir_pkg, "/usr/share/locale", "/usr/local/share/locale"]
logger = logging.getLogger(__name__)
_log_buffer = []

# Try to find a translation in the package locale directory first, then
# common system locale locations. Log which one we end up using so it's
# easier to debug packaging/install issues.
translate = None
for ld in locales_to_try:
    try:
        t = gettext.translation("scantpaper", localedir=ld)
        translate = t
        _log_buffer.append(
            ("warning", "Loaded translations for 'scantpaper' from %s", ld)
        )
        break
    except (FileNotFoundError, OSError):
        _log_buffer.append(("warning", "No translations for 'scantpaper' in %s", ld))

# Fallback to a null translation if none found
if translate is None:
    _log_buffer.append(
        (
            "warning",
            "No translations found for 'scantpaper'; falling back to untranslated strings",
        )
    )
    translate = gettext.NullTranslations()


def log_i18n_status():
    "Log the buffered messages"
    for level, msg, *args in _log_buffer:
        getattr(logger, level)(msg, *args)
    _log_buffer.clear()


_ = translate.gettext

# sane-backends translations are usually provided by the system; try to load
# them from the default locations and otherwise fall back silently.
try:
    d_sane = gettext.translation("sane-backends").gettext
except (FileNotFoundError, OSError):
    d_sane = gettext.gettext

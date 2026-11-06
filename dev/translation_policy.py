"""Shared translation-approval policy definitions.

The provenance classes and the high-impact classification live here so that
the gate, the ledger validation and the tests use one definition. Nothing in
this module reads a catalog or a ledger; it is pure policy.

An approval names exactly one provenance class. ``human-historical`` is the
frozen pre-2026 Launchpad core, ``human-review`` is a human who reviewed the
current text, ``in-project-rebase`` is a mechanical mnemonic or placeholder
rebase of an existing translation, ``tm-consensus`` is a dominant
cross-project match combined with the remaining evidence, and the two machine
classes record the strength of the automated evidence. Only the machine
classes are provisional and revocable.

High-impact strings are menu actions, destructive verbs and data-loss error
messages. They may ship only with human-origin evidence or a
``machine-strong`` approval. The classification is deliberately conservative:
a tooltip or descriptive label is not high-impact merely because it lives in a
``.ui`` file, while an unknown menu label is.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

PROVENANCE_CLASSES = (
    "human-historical",
    "human-review",
    "in-project-rebase",
    "tm-consensus",
    "machine-strong",
    "machine-weak",
)

HUMAN_PROVENANCE_CLASSES = frozenset(PROVENANCE_CLASSES[:4])
MACHINE_PROVENANCE_CLASSES = frozenset(PROVENANCE_CLASSES[4:])

# Base forms only; ``_is_action_word`` accepts the common inflections.
HIGH_IMPACT_ACTION_WORDS = frozenset(
    {
        "clear",
        "delete",
        "destroy",
        "discard",
        "erase",
        "overwrite",
        "purge",
        "quit",
        "remove",
        "reset",
        "unlink",
    }
)

# Words that mark a message in a dialog as an error or a data-loss warning.
HIGH_IMPACT_ERROR_WORDS = frozenset(
    {
        "cannot",
        "corrupt",
        "crash",
        "error",
        "fail",
        "failed",
        "invalid",
        "lose",
        "lost",
        "overwrite",
        "unable",
        "warning",
    }
)

# A short label is an action; a longer sentence is a description or a tooltip.
HIGH_IMPACT_MAX_LENGTH = 40

# Occurrence rules. A label in the menu definition is an action; a message in
# a dialog is high-impact only when it warns about an error or data loss.
MENU_UI_NAME = "menu.ui"
DIALOG_PREFIX = "dialog/"

# Placeholder extraction shared by the rebase and defect-fix checks.
_PRINTF_RE: re.Pattern[str] = re.compile(
    r"%(?:\((?P<name>[^)]+)\))?[-+#0 ]*\d*(?:\.\d+)?"
    r"(?P<conversion>[diouxXeEfFgGcrsa%])"
)
_FORMAT_FIELD_RE: re.Pattern[str] = re.compile(r"(?<!\{)\{(?P<field>[^{}]*)\}(?!\})")
_SPACED_PRINTF_RE: re.Pattern[str] = re.compile(r"% +[diouxXeEfFgGcrsa]")
_WORD_RE: re.Pattern[str] = re.compile(r"[^\W\d_]+", re.UNICODE)


def _printf_token(match: re.Match[str]) -> str:
    """Return a canonical token for one printf placeholder."""
    name = match.group("name")
    return f"%({name})" if name else f"%{match.group('conversion')}"


def placeholder_tokens(text: str) -> list[str]:
    """Return the printf and ``str.format`` placeholders in a message."""
    tokens = [_printf_token(match) for match in _PRINTF_RE.finditer(text)]
    tokens.extend(
        f"{{{match.group('field')}}}" for match in _FORMAT_FIELD_RE.finditer(text)
    )
    return tokens


def has_spaced_printf(text: str) -> bool:
    """Return whether a printf placeholder has a space after ``%``.

    ``msgfmt`` accepts ``"% s"`` under ``python-format`` but Python renders it
    incorrectly, so it is a deterministic defect the audit can recognise.
    """
    return _SPACED_PRINTF_RE.search(text) is not None


def fixes_placeholder_defect(source: str, old: str, new: str) -> bool:
    """Return whether ``new`` repairs a placeholder defect in ``old``."""
    expected = Counter(placeholder_tokens(source))
    if not expected:
        return False
    old_bad = has_spaced_printf(old) or Counter(placeholder_tokens(old)) != expected
    new_good = (
        not has_spaced_printf(new) and Counter(placeholder_tokens(new)) == expected
    )
    return old_bad and new_good


def _visible_words(text: str) -> list[str]:
    """Return the translatable words left after placeholders and mnemonics."""
    without_placeholders = _PRINTF_RE.sub("", text)
    without_placeholders = _FORMAT_FIELD_RE.sub("", without_placeholders)
    words = _WORD_RE.findall(_strip_mnemonics(without_placeholders).casefold())
    return cast("list[str]", words)


def is_mechanical_rebase(old: str, new: str) -> bool:
    """Return whether a change is limited to a mnemonic or a placeholder.

    The visible words must be identical and the placeholder set must be
    unchanged; punctuation and whitespace differences are allowed because
    they do not translate a different meaning.
    """
    if not old.strip() or Counter(placeholder_tokens(old)) != Counter(
        placeholder_tokens(new)
    ):
        return False
    return _visible_words(old) == _visible_words(new)


def validate_provenance_class(value: str) -> str:
    """Return ``value`` if it is one of the six provenance classes.

    Raises:
        ValueError: if ``value`` is not a known class.

    """
    if value not in PROVENANCE_CLASSES:
        msg = f"unknown provenance class: {value!r}"
        raise ValueError(msg)
    return value


def is_machine_class(value: str) -> bool:
    """Return whether ``value`` is a machine-origin provenance class."""
    return validate_provenance_class(value) in MACHINE_PROVENANCE_CLASSES


def _strip_mnemonics(text: str) -> str:
    """Remove gettext mnemonics without touching the visible words."""
    return text.replace("_", "").replace("&", "")


def _words(text: str) -> set[str]:
    """Split a msgid into case-folded alphabetic words."""
    cleaned = "".join(
        char if char.isalpha() else " " for char in _strip_mnemonics(text)
    )
    return {word for word in cleaned.casefold().split() if word}


def _is_action_word(word: str) -> bool:
    """Return whether a word is a high-impact verb, including inflections."""
    for base in HIGH_IMPACT_ACTION_WORDS:
        candidates = {base, f"{base}s", f"{base}es", f"{base}ed", f"{base}d"}
        candidates.add(f"{base}ing")
        if base.endswith("e"):
            candidates.add(f"{base[:-1]}ing")
        if word in candidates:
            return True
    return False


def _occurrence_paths(occurrences: Iterable[object]) -> list[str]:
    """Normalise polib ``(path, line)`` occurrences to POSIX-style paths."""
    paths: list[str] = []
    for occurrence in occurrences:
        path = occurrence[0] if isinstance(occurrence, tuple) else occurrence
        if isinstance(path, str):
            paths.append(PurePosixPath(path.replace("\\", "/")).as_posix())
    return paths


def is_high_impact(
    msgid: str,
    occurrences: Iterable[object] = (),
) -> bool:
    """Return whether ``msgid`` needs human-origin evidence to ship.

    A message is high-impact when any of these holds:

    * it is a short label containing a destructive verb, such as ``Delete``;
    * it is a label in the menu definition (``menu.ui``), which is a menu
      action even when its verb is not in the destructive list;
    * it occurs under ``dialog/`` and names an error or a data-loss warning.

    A tooltip or descriptive label is not high-impact solely because it lives
    in a ``.ui`` file, and a long sentence containing a destructive word is a
    description rather than an action.
    """
    text = _strip_mnemonics(msgid).strip()
    words = _words(msgid)

    if len(text) <= HIGH_IMPACT_MAX_LENGTH and any(
        _is_action_word(word) for word in words
    ):
        return True

    paths = _occurrence_paths(occurrences)
    if any(PurePosixPath(path).name == MENU_UI_NAME for path in paths):
        return True

    return any(path.startswith(DIALOG_PREFIX) for path in paths) and bool(
        words & HIGH_IMPACT_ERROR_WORDS
    )

"""Some helper functions around tesseract."""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

import iso639

from scantpaper.helpers import exec_command
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

logger = logging.getLogger(__name__)

# Taken from
# https://github.com/tesseract-ocr/tesseract/blob/master/doc/tesseract.1.asc#languages
installable_language_codes = [
    "afr",
    "amh",
    "ara",
    "asm",
    "aze",
    "aze-cyrl",
    "bel",
    "ben",
    "bod",
    "bos",
    "bre",
    "bul",
    "cat",
    "ceb",
    "ces",
    "chi-sim",
    "chi-sim-vert",
    "chi-tra",
    "chi-tra-vert",
    "chr",
    "cos",
    "cym",
    "dan",
    "dan-frak",
    "deu",
    "deu-frak",
    "div",
    "dzo",
    "ell",
    "eng",
    "enm",
    "epo",
    "equ",
    "est",
    "eus",
    "fao",
    "fas",
    "fil",
    "fin",
    "fra",
    "frk",
    "frm",
    "fry",
    "gla",
    "gle",
    "gle-uncial",
    "glg",
    "grc",
    "guj",
    "hat",
    "heb",
    "hin",
    "hrv",
    "hun",
    "hye",
    "iku",
    "ind",
    "isl",
    "ita",
    "ita-old",
    "jav",
    "jpn",
    "jpn-vert",
    "kan",
    "kat",
    "kat-old",
    "kaz",
    "khm",
    "kir",
    "kmr",
    "kor",
    "kor-vert",
    "lao",
    "lat",
    "lav",
    "lit",
    "ltz",
    "mal",
    "mar",
    "mkd",
    "mlt",
    "mon",
    "mri",
    "msa",
    "mya",
    "nep",
    "nld",
    "nor",
    "oci",
    "ori",
    "pan",
    "pol",
    "por",
    "pus",
    "que",
    "ron",
    "rus",
    "san",
    "sin",
    "slk",
    "slk-frak",
    "slv",
    "snd",
    "spa",
    "spa_old",
    "sqi",
    "srp",
    "srp_latn",
    "sun",
    "swa",
    "swe",
    "swe-frak",
    "syr",
    "tam",
    "tat",
    "tel",
    "tgk",
    "tgl",
    "tha",
    "tir",
    "ton",
    "tur",
    "uig",
    "ukr",
    "urd",
    "uzb",
    "uzb_cyrl",
    "vie",
    "yid",
    "yor",
]
non_iso639_3 = {
    "aze-cyrl": "Azerbaijani (Cyrillic)",
    "chi-sim": "Simplified Chinese",
    "chi-sim-vert": "Chinese - Simplified (vertical)",
    "chi-tra": "Traditional Chinese",
    "chi-tra-vert": "Traditional Chinese (vertical)",
    "dan-frak": "Danish (Fraktur)",
    "deu-frak": "German (Fraktur)",
    "equ": "equations",
    "gle-uncial": "Irish (Uncial)",
    "ita-old": "Italian - Old",
    "jpn-vert": "Japanese (vertical)",
    "kat-old": "Old Georgian",
    "kor-vert": "Korean (vertical)",
    "osd": "Orientation, script, direction",
    "slk-frak": "Slovak (Fraktur)",
    "spa_old": "Spanish (Castilian - Old)",
    "srp_latn": "Serbian - Latin",
    "swe-frak": "Swedish (Fraktur)",
    "uzb_cyrl": "Uzbek - Cyrilic",
}
non_iso639_1 = {"zh": "chi-sim"}

# Tesseract command-line options and the engine parameter each one sets.
command_line_flags = {
    "--user-words": "user_words_file",
    "--user-patterns": "user_patterns_file",
    "--dpi": "user_defined_dpi",
}

# Engine parameters whose value is a path to a file the engine reads.
file_valued_variables = ("user_words_file", "user_patterns_file")


def get_tesseract_codes() -> list[str]:
    """Query tesseract for installed languages."""
    proc = exec_command(["tesseract", "--list-langs"])
    if proc.stdout is None:
        logger.info(proc.stderr)
        return []
    _codes = re.split(r"\n", proc.stdout)
    if re.search(r"^List[ ]of[ ]available[ ]languages", _codes[0]):
        _codes.pop(0)
    if _codes[-1] == "":
        _codes.pop()
    return cast("list[str]", (_codes))


def split_language_spec(spec: str | None) -> list[str]:
    """Split a tesseract language specification into unique codes."""
    if spec is None or spec == "":
        return []
    codes: list[str] = []
    for part in spec.split("+"):
        stripped = part.strip()
        if stripped and stripped not in codes:
            codes.append(stripped)
    return codes


def join_language_spec(
    primary: str | None, additional: Iterable[str] | None = None
) -> str:
    """Join a primary language and additional languages into a specification."""
    codes = split_language_spec(primary)
    if additional is not None:
        for item in additional:
            for code in split_language_spec(item):
                if code not in codes:
                    codes.append(code)
    return "+".join(codes)


def _flag_error(line: str) -> str:
    """Return an error for a command-line option in the variables field."""
    flag = line.split(maxsplit=1)[0]
    variable = command_line_flags.get(flag)
    if variable is None:
        return _(
            "'%(flag)s' is a Tesseract command-line option; this field accepts "
            "engine parameters in name=value form only."
        ) % {"flag": flag}
    value = line[len(flag) :].strip()
    return _(
        "'%(flag)s' is a Tesseract command-line option; use "
        "'%(variable)s=%(value)s' instead."
    ) % {"flag": flag, "variable": variable, "value": value}


def parse_variables(text: str | None) -> dict[str, str]:
    """Parse one name=value tesseract variable per line."""
    variables: dict[str, str] = {}
    if text is None or text == "":
        return variables
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "-c" or line.startswith(("-c ", "-c\t")):
            line = line[2:].strip()
        elif line.startswith("-"):
            raise ValueError(_flag_error(line))
        if "=" not in line:
            raise ValueError(
                _("Invalid Tesseract option on line %(line)s: %(text)s")
                % {"line": line_number, "text": line}
            )
        name, value = line.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(
                _("Invalid Tesseract option on line %(line)s: %(text)s")
                % {"line": line_number, "text": line}
            )
        variables[name] = value.strip()
    return variables


def validate_file_variables(variables: Mapping[str, str]) -> str | None:
    """Return an error for a file-valued variable that cannot be read."""
    for name in file_valued_variables:
        value = variables.get(name)
        if value is None:
            continue
        path = Path(value).resolve()
        if not path.exists():
            return _("%(variable)s names a file that does not exist: %(path)s") % {
                "variable": name,
                "path": str(path),
            }
        if not path.is_file() or not os.access(path, os.R_OK):
            return _("%(variable)s names a file that cannot be read: %(path)s") % {
                "variable": name,
                "path": str(path),
            }
    return None


def resolve_file_variables(variables: Mapping[str, str]) -> dict[str, str]:
    """Return the variables with file-valued paths resolved."""
    return {
        name: str(Path(value).resolve()) if name in file_valued_variables else value
        for name, value in variables.items()
    }


@lru_cache(maxsize=1)
def get_tesseract_variables() -> set[str] | None:
    """Return the variable names supported by tesseract."""
    proc = exec_command(["tesseract", "--print-parameters"])
    if proc.stdout is None or proc.returncode != 0:
        logger.info(proc.stderr)
        return None
    lines = proc.stdout.splitlines()
    first_line = next((line.strip() for line in lines if line.strip()), "")
    if not first_line.endswith(":"):
        return None
    variables: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.endswith(":"):
            continue
        name = stripped.split(maxsplit=1)[0]
        if re.fullmatch(r"[A-Za-z0-9_]+", name):
            variables.add(name)
    return variables or None


def validate_language_spec(
    spec: str | None, installed_codes: Iterable[str]
) -> list[str]:
    """Return the languages in the specification that are not installed."""
    installed = set(installed_codes)
    return [code for code in split_language_spec(spec) if code not in installed]


def validate_variable_names(
    variables: Mapping[str, str], known: set[str] | None
) -> list[str]:
    """Return the variable names that tesseract does not recognise."""
    if known is None:
        return []
    return sorted(name for name in variables if name not in known)


def code2name(code: str) -> str:
    """Given a tesseract language code, return the appropriate name."""
    if code in non_iso639_3:
        return non_iso639_3[code]
    try:
        return iso639.Language.from_part2t(code).name
    except iso639.LanguageNotFoundError:
        return code


def languages(codes: list[str]) -> dict[str, str]:
    """Given a list of tesseract language codes, return a dictionary of their names."""
    langs = {}
    for code in codes:
        name = code2name(code)
        langs[code] = name
    return langs


def installable_languages() -> dict[str, str]:
    """Return a dictionary of the installable languages."""
    _installable_languages = non_iso639_3.copy()
    for code in installable_language_codes:
        name = code2name(code)
        _installable_languages[code] = name
    return _installable_languages


def _iso639_1to3(code1: str) -> str:
    if code1.lower() == "c":
        code1 = "en"
    if code1 in non_iso639_1:
        return non_iso639_1[code1]
    return iso639.Language.from_part1(code1).part3


def locale_installed(locale: str, installed_codes: list[str]) -> str:
    """Check that the given locale is installed or installable as a tesseract language."""
    # Handle C and C.UTF-8 locales specially
    code1 = "c" if locale.upper().startswith("C") else locale.lower()[0:2]
    try:
        code3 = _iso639_1to3(code1)
    except iso639.LanguageNotFoundError:
        return (
            (_("You are using locale '%s'.") % (locale,))
            + " "
            + _(
                "scantpaper does not currently know which tesseract language "
                "package would be necessary for that locale."
            )
            + " "
            + _("Please contact the developers to add support for that locale.")
            + "\n"
        )
    if code3 in languages(installed_codes):
        return ""
    if code3 in installable_languages():
        return (
            (_("You are using locale '%s'.") % (locale,))
            + " "
            + (
                _(
                    "Please install tesseract package 'tesseract-ocr-%(package)s' "
                    "and restart scantpaper for OCR for %(language)s with "
                    "tesseract."
                )
                % {"package": code3, "language": installable_languages()[code3]}
            )
            + "\n"
        )
    return (
        (_("You are using locale '%s'.") % (locale,))
        + " "
        + (_("There is no tesseract package for %s") % (code2name(code3),))
        + ". "
        + _("If this is in error, please contact the scantpaper developers.")
        + "\n"
    )

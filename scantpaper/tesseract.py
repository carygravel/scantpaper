"Some helper functions around tesseract"

import re
import iso639
from helpers import exec_command
from i18n import _

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


def get_tesseract_codes():
    "query tesseract for installed languages"
    proc = exec_command(["tesseract", "--list-langs"])
    _codes = re.split(r"\n", proc.stdout)
    if re.search(r"^List[ ]of[ ]available[ ]languages", _codes[0]):
        _codes.pop(0)
    if _codes[-1] == "":
        _codes.pop()
    return _codes


def code2name(code):
    "given a tesseract language code, return the appropriate name"
    if code in non_iso639_3:
        return non_iso639_3[code]
    try:
        return iso639.Language.from_part2t(code).name
    except iso639.LanguageNotFoundError:
        return code


def languages(codes):
    "given a list of tesseract language codes, return a dictionary of their names"
    langs = {}
    for code in codes:
        name = code2name(code)
        langs[code] = name
    return langs


def installable_languages():
    "return a dictionary of the installable languages"
    _installable_languages = non_iso639_3.copy()
    for code in installable_language_codes:
        name = code2name(code)
        _installable_languages[code] = name
    return _installable_languages


def _iso639_1to3(code1):
    if code1 == "C":
        code1 = "en"
    if code1 in non_iso639_1:
        return non_iso639_1[code1]
    return iso639.Language.from_part1(code1).part3


def locale_installed(locale, installed_codes):
    "check that the given locale is installed or installable as a tesseract language"
    code1 = locale.lower()[0:2]
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
                    "Please install tesseract package 'tesseract-ocr-%s' and "
                    "restart scantpaper for OCR for %s with tesseract."
                )
                % (code3, installable_languages()[code3])
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

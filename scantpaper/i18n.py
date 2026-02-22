"Provide _() function for translations"

import gettext
import os

localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "locale")

# We could replace the following with
#    gettext.install("scantpaper", localedir)
# but then would get "Undefined variable '_'"" warnings from pylint everywhere
translate = gettext.translation("scantpaper", localedir, fallback=True)
_ = translate.gettext
d_sane = gettext.translation("sane-backends", fallback=True).gettext

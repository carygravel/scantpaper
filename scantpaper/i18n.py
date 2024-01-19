"Provide _() function for translations"

import gettext
import os

localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "locale")
translate = gettext.translation("scantpaper", localedir, fallback=True)
_ = translate.gettext

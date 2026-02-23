"""
To install scantpaper, run "pip install ." (note the dot).

https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html
"""

from pathlib import Path
import sys

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.install import install as _install


REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# from dev import build_translations
from scantpaper import const  # pylint: disable=wrong-import-position


TMP_LOCALE_DIR = REPO / "build" / "locale"


# class build_py(_build_py):
#     def run(self):
#         build_translations.build_translation_files(REPO / "po", TMP_LOCALE_DIR)
#         _build_py.run(self)


"""
We use the deprecated install class since it provides the easiest way to install
data files outside of a Python package. This feature is needed for the
translation files, which must reside in <sys.prefix>/share/locale for the Glade
file to pick them up.

An alternative would be to build the translation files with a separate command,
but that would require changing all package scripts for all distributions.
"""


# class install(_install):
#     def run(self):
#         _install.run(self)
#         for lang_dir in TMP_LOCALE_DIR.iterdir():
#             lang = lang_dir.name
#             lang_file = TMP_LOCALE_DIR / lang / "LC_MESSAGES" / "scantpaper.mo"
#             dest_dir = (
#                 Path(self.install_data) / "share" / "locale" / lang / "LC_MESSAGES"
#             )
#             dest_dir.mkdir(parents=True, exist_ok=True)
#             shutil.copy2(lang_file, dest_dir / "scantpaper.mo")


parameters = {
    "name": "scantpaper",
    "version": const.VERSION,
    "description": "GUI to produce PDFs or DjVus from scanned documents",
    "long_description": """Only five clicks are required to scan several pages
and then save all or a selection as a PDF or DjVu file, including metadata if
required.

scantpaper can control flatbed or sheet-fed (ADF) scanners with SANE via
SANE, and can scan multiple,pages at once. It presents a thumbnail view of
scanned pages, and permits simple operations such as cropping, rotating and
deleting pages.

OCR can be used to recognise text in the scans, and the output embedded in the
PDF or DjVu.

PDF conversion is done by ocrmypdf.

The resulting document may be saved as a PDF, DjVu, multipage TIFF file, or
single page image file.""",
    "author": const.AUTHOR,
    "author_email": const.AUTHOR_EMAIL,
    "maintainer": const.AUTHOR,
    "maintainer_email": const.AUTHOR_EMAIL,
    "url": const.URL,
    "license": "GPL-3.0-only",
    "keywords": "scan, pdf, djvu",
    # "cmdclass": {"build_py": build_py, "install": install},
    "entry_points": {
        "gui_scripts": [
            "scantpaper = scantpaper.app:main",
        ],
    },
    "packages": [
        "scantpaper",
        "scantpaper.dialog",
        "scantpaper.frontend",
        "scantpaper.scanner",
    ],
    "package_data": {
        "scantpaper": [
            "app.ui",
        ]
    },
    "include_package_data": True,
    # "data_files": [
    #     ("share/applications", ["data/scantpaper.desktop"]),
    #     (
    #         "share/icons/hicolor/scalable/apps",
    #         ["scantpaper/images/scantpaper-icon/scantpaper.svg"],
    #     ),
    #     ("share/metainfo", ["data/scantpaper.appdata.xml"]),
    # ],
}


if __name__ == "__main__":
    # Additionally use MANIFEST.in for image files
    setup(**parameters)

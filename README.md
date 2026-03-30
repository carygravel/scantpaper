# ScantPaper

A GUI to produce PDFs or DjVus from scanned documents.

<p align="center">
    <img width="1254" height="656" alt="Image" src="https://github.com/user-attachments/assets/14078f4b-9cde-404e-aaab-958c77f90c5a" />
    <em>Screenshot: Main page v3.0.0</em>
</p>

---

## Usage

1. Start the application with `python3 scantpaper/app.py`.
   Add `--debug|info|warn|error|fatal` to enable logging at the required level.
1. Scan one or several pages with **File → Scan**.
1. Create a PDF of selected pages with **File → Save**.

---

## Command-line Options

scantpaper supports the following options:

- `--device=<device>`  
    Specifies the device to use, instead of getting the list from the SANE API. Useful for remote scanners.

- `--help`  
    Displays help and exits.

- `--log=<log-file>`  
    Specifies a file to store logging messages.

- `--debug`, `--info`, `--warn`, `--error`, `--fatal`  
    Defines the log level. Defaults to `--debug` if a log file is specified, otherwise `--error`.

- `--import=<PDF|DjVu|images>`  
    Imports the specified file(s). For multi-page documents, a window is displayed to select required pages.

- `--import-all=<PDF|DjVu|images>`  
    Imports all pages of the specified file(s).

- `--version`  
    Displays the program version and exits.

Scanning is handled with SANE. PDF conversion uses `img2pdf` and `ocrmypdf`. TIFF export uses `libtiff`.

---

## Diagnostics

To diagnose errors, start scantpaper from the command line with logging enabled:

```sh
python3 scantpaper/app.py --debug
```

---

## Configuration

scantpaper creates a config file at `~/.config/scantpaperrc`. The directory can be changed by setting `$XDG_CONFIG_HOME`. Preferences are usually set via **Edit → Preferences**.

---

## Dependencies

### Required

- gir1.2-gdkpixbuf-2.0
- gir1.2-gtk-3.0
- gir1.2-goocanvas-2.0
- imagemagick
- img2pdf
- libtiff-tools
- ocrmypdf
- poppler-utils
- python3-gi
- python3-gi-cairo
- python3-iso639
- python3-pil
- python3-sane
- python3-tesserocr

### Optional

- djvulibre-bin
- unpaper
- xdg-utils

### Development

- pytest-black
- python3-pytest-mock
- python3-pytest-cov
- python3-pytest-pylint
- python3-pytest-timeout
- python3-pytest-xvfb

---

## Download & Installation

**Github:**  
[scantpaper downloads](https://github.com/carygravel/scantpaper/releases/)

### Debian-based

- Debian `sid` will have the latest version as soon as it has cleared the new
  queue.
- Ubuntu users can use the PPA:

    ```sh
    sudo apt-add-repository ppa:jeffreyratcliffe/ppa
    sudo apt update
    sudo apt install scantpaper
    ```

### From Source

Download from [Github](https://github.com/carygravel/scantpaper/releases/).

### From the Repository

Browse the code at [Github](https://github.com/carygravel/scantpaper):

```sh
git clone https://github.com/carygravel/scantpaper.git
```

### Building from Source

Run the app straight from the source directory:
```sh
tar xvfz scantpaper-x.x.x.tar.gz
cd scantpaper-x.x.x
# optionally run the tests
pytest
# before starting the app
python3 scantpaper/app.py
```

Or build a wheel to install via `pip`:
```sh
# if necessary install build
pip install build
python3 -m build --wheel
# which you can install with pip
pip install scantpaper
# and then start the app
scantpaper
```

Or build a package for debian:
```sh
make debdist
```

---

## Support

- **Mailing lists:**
    - [gscan2pdf-announce](https://lists.sourceforge.net/lists/listinfo/gscan2pdf-announce) (announcements)
    - [gscan2pdf-help](https://lists.sourceforge.net/lists/listinfo/gscan2pdf-help) (general support)

---

## Reporting Bugs

- Please read the [FAQs](#faqs) first.
- Report bugs preferably against the [Debian package](https://packages.debian.org/sid/gscan2pdf) or [Debian Bugs](https://www.debian.org/Bugs/).
- Alternatively, use the [Github issue tracker](https://github.com/carygravel/scantpaper/issues).
- Include the log file created by `scantpaper --log=log` with your report.

---

## Translations

gscan2pdf is partly translated into several languages. Contribute via [Launchpad Rosetta](https://translations.launchpad.net/gscan2pdf).

- Scanner option translations come from sane-backends. Contribute via the [sane-devel mailing list](mailto:sane-devel@lists.alioth.debian.org) or [SANE project](http://www.sane-project.org/cvs.html).
- Ubuntu translation project: [Jaunty SANE backends](https://translations.launchpad.net/ubuntu/jaunty/+source/sane-backends/+pots/sane-backends)

To test updated `.po` files:

```sh
perl Makefile.PL LOCALEDIR=./locale
perl -I lib bin/gscan2pdf --log=log --locale=locale
```

Set locale variables as needed (e.g., for Russian):

```sh
LC_ALL=ru_RU.utf8 LC_MESSAGES=ru_RU.utf8 LC_CTYPE=ru_RU.utf8 LANG=ru_RU.utf8 LANGUAGE=ru_RU.utf8 python3 scantpaper/app.py --log=log --locale=locale
```

---

## Description

scantpaper provides a GUI for scanning, editing, and saving documents as PDF, DjVu, TIFF, PNG, JPEG, PNM, or GIF. It supports batch scanning, metadata, OCR, and various editing tools.

### Main Features

- **Scan:** Options for device, page count, source document, side to scan, and device-dependent options (page size, mode, resolution, batch-scan, etc.).
- **Save:** Save selected/all pages in multiple formats. Supports metadata.
- **Email as PDF:** Attach pages as PDF to a blank email (requires xdg-email).
- **Print:** Print selected/all pages.
- **Compress temporary files:** Compress images to save space.

### Edit Menu

- **Delete:** Remove selected page.
- **Renumber:** Renumber pages.
- **Select:** Select all, even, odd, blank, dark, or modified pages.
- **Properties:** Edit image metadata.
- **Preferences:** Configure default behaviors and frontends.

### View Menu

- Zoom, rotate, and fit options.

### Tools

- **Threshold:** Binarize images.
- **Unsharp mask:** Sharpen images.
- **Crop**
- **unpaper:** Clean up scans.
- **OCR:** Use gocr, tesseract, or cuneiform to extract text.

#### User-defined Tool Variables

- `%i` - input filename
- `%o` - output filename
- `%r` - resolution

---

## FAQs

### Why isn't option xyz available in the scan window?

It may not be supported by SANE or your scanner. If you see it in `scanimage --help` but not in scantpaper, send the output to the maintainer.

### How do I scan a multipage document with a flatbed scanner?

Enable "Allow batch scanning from flatbed" in Preferences. Some scanners require additional settings.

### Why is option xyz ghosted out?

The required package may not be installed (e.g., xdg-email, unpaper, imagemagick).

### Why can I not scan from the flatbed of my HP scanner?

Set "# Pages" to "1" and "Batch scan" to "No".

### Why is the list of changes not displayed when updating in Ubuntu?

Only changelogs from official Ubuntu builds are shown.

### Why can't scantpaper find my scanner?

If the scanner is remote and not found automatically, specify the device:

```sh
scantpaper --device <device>
```

### How can I search for text in the OCR layer?

Use `pdftotext` or `djvutxt` to extract text. Many viewers support searching the embedded text layer.

### How can I change the colour of the selection box or OCR output?

Create or edit `~/.config/gtk-3.0/gtk.css`:

```css
.rubberband,
rubberband,
flowbox rubberband,
treeview.view rubberband,
.content-view rubberband,
.content-view .rubberband {
    border: 1px solid #2a76c6;
    background-color: rgba(42, 118, 198, 0.2);
}

#scantpaper-ocr-output {
    color: black;
}
```

### What's in a name?

"scant" (https://en.wiktionary.org/wiki/scant) in this sense means "short (of)", as I am trying to digitalise my paperwork, and I liked the play on "scan".

---

## See Also

- [XSane](http://xsane.org/)
- [Scan Tailor](http://scantailor.org/)

---

## History

I started writing `gscan2pdf` as a Perl & Gtk2 project in 2006.
Version 2 switched to Gtk3, but kept the basic software architecture.
This stored the pages as temporary files with hashed names, which had a couple
of major disadvantages:

- Difficult to support PDF/A directly
- It was impossible to create documents with more than a few hundred pages, as
it ran out of open file handles.
- In the event of a crash, it was tedious to recreate the document from the image files.
- AFAIK, Perl's support for Gtk4 never extended beyond that provided by introspection.

Therefore I decided in 2022 to completely rewrite `gscan2pdf` in Python and
renamed it for v3 `scantpaper`. The rewrite:

- Supports PDF/A by using `ocrmypdf` to write PDFs
- Stores all session data in a single Sqlite database
- Should be simple to migrate to Gtk4

---

## Author

Jeffrey Ratcliffe (jffry at posteo dot net)

---

## Thanks To

- All contributors (patches, translations, bugs, feedback)
- The SANE project
- The authors of `img2pdf` and `ocrmypdf`, without which this would have been much harder.

---

## Contributing
Contributions are welcome. Please submit pull requests, ensuring that all the
tests pass, that new code is covered by new tests, and that the `pylint` does
not drop.

To run all the tests, just run `pytest`. To run all the tests in a particular
file, `pytest scantpaper/tests/test_app.py`. To run just one test in a file
`pytest scantpaper/tests/test_app.py::test_application_init`.

Note that the test suite also tests that the code is formatted with `black`.
To fix the formatting `black scantpaper`.

Similarly to check the linting for one or more files
`pylint scantpaper/app.py scantpaper/text_layer_control.py`

---

## Donate

<form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_top">
<input type="hidden" name="lc" value="US">
<input type="hidden" name="cmd" value="_s-xclick">
<input type="hidden" name="hosted_button_id" value="GYQGXYD5UZS6S">
<input type="image" src="https://www.paypalobjects.com/en_US/DE/i/btn/btn_donateCC_LG.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
<img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
</form>

---

## License

Copyright © 2006–2026 Jeffrey Ratcliffe <jffry@posteo.net>

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License v3 as published by the Free Software
Foundation.

This program is distributed in the hope that it will be useful, but **WITHOUT
ANY WARRANTY**; without even the implied warranty of **MERCHANTABILITY** or
**FITNESS FOR A PARTICULAR PURPOSE**. See the
[GNU General Public License](https://www.gnu.org/licenses/) for more details.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether
or not all the tests are passing for the project. You can use Shields to add
some to your README. Many services also have instructions for adding a badge.

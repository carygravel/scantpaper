## 3.0.2 (2026-03-15)

* Also support old method of specifying multiple CLI arguments.
  Closes #56 (--import-all only importing the first image)
  Closes #57 (Support more than one instance of a command-line option)
  Thanks to Chris Mayo for the patch.
* Fix cursor position when typing datetime data in save dialog.
  Closes #54 (Save Dialogue: Reversed order of Digits)
* Suppress warnings like:
  `Warning: ../../../gobject/gsignal.c:2685: instance '0x29948460' has no handler with id '117'`
  when processes finish
* Suppress warnings like:
  `Warning: value "100" of type 'gint' is invalid or out of range for property 'page-number-start' of type 'gint'`
  when importing more than 99 images
* Raise `RuntimeError` if `file` returns no stdout


## 3.0.1 (2026-03-15)

* Fix selection changed callback. Closes #45
  Thanks to Chris Mayo for the patch.
* Fix opening an encrypted PDF. Closes #46
  Thanks to Chris Mayo for the patch.
* Improve session logs. Closes #47
  Thanks to Chris Mayo for the patch.
* Fix image context menu mnemonics. Closes #49
  Thanks to Chris Mayo for the patch.
* Fix missing message when PDF has no images. Closes #50
  Thanks to Chris Mayo for the patch.
* Fix updating image resolution via property dialog.
  Closes #44 (AttributeError when changing resolution)
* Replace deprecated IconSet and IconFactory. Closes #3
  Thanks to Chris Mayo for the patch.
* Use qpdf to encrypt PDFs instead of pdftk. Closes #48
  Thanks to Chris Mayo for the patch.
* Fix messages dialog text width. Closes #52
  Thanks to Chris Mayo for the patch.
* Rename scanner icon to scan. Closes #53
  Thanks to Chris Mayo for the patch.


## 3.0.0 (2026-03-11)

* + minimal en_US translation to prevent warnings. Closes #41
* Be graceful if the previous current working directory no longer exists.
  Closes #42


## 3.0.0-rc5 (2026-03-08)

* Fix search path for icon files.
* Remove unnecessary dependency on xz. Closes #40
  Thanks to Chris Mayo for the patch.


## 3.0.0-rc4 (2026-03-06)

* Fix copying or deleting a word prevents saving PDF. Closes #35
  Thanks to Chris Mayo for the patch.
* Fix error clicking on an empty canvas. Closes #36
* Don't include PDF metadata in text layer.
* Fix failure to start when pdftk is not installed. Closes #37
  Thanks to Chris Mayo for the patch.
* Enforce default image type. Closes #39
  (Save Dialog: No Document type selected by default)


## 3.0.0-rc3 (2026-03-04)

* Fixed error cancelling scan. Closes #32
  Thanks to Chris Mayo for the patch.
* Fixed error saving PDF after correcting text layer. Closes #33


## 3.0.0-rc2 (2026-03-03)

* Fixed error printing. Closes #15
* Fixed error updating text layer. Closes #29
* Fixed error pressing Encrypt PDF ok/cancel buttons. Closes #30


## 3.0.0-rc1 (2026-03-01)

* Rewrite of gscan2pdf in Python
* The UI is basically identical to gscan2pdf
* scantpaper uses OCRmyPDF as the backend to create PDFs. These means we get
  PDF/A out of the box.
* scantpaper uses an SQLite database to store all session data. This eliminates
  the need for gscan2pdf's big hairy temporary directory, and does not suffer
  from gscan2pdf's requirement to hold an open file handle for each page, which meant that some users ran out of file handles when they created several hundred pages.
* Storing sessions in a database also means that the number of undo/redo steps
  is only limited by available storage. gscan2pdf can undo/redo one step.

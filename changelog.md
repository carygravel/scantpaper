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

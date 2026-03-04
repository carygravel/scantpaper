## 3.0.0-rc2 (2026-03-03)

* fixed bug #15 (printing)
* fixed bug #29 (updating text layer)
* fixed bug #30 (error pressing Encrypt PDF ok/cancel buttons)


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

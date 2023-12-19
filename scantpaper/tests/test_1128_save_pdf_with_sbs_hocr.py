"Test writing PDF with text layer right of the image, rather than behind it"

import re
import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test writing PDF with text layer right of the image, rather than behind it"

    subprocess.run(
        [
            "convert",
            "+matte",
            "-depth",
            "1",
            "-colorspace",
            "Gray",
            "-family",
            "DejaVu Sans",
            "-pointsize",
            "12",
            "-units",
            "PixelsPerInch",
            "-density",
            "300",
            "label:The quick brown fox",
            "-border",
            "20x10",
            "test.png",
        ],
        check=True,
    )
    info = subprocess.check_output(["identify", "test.png"], text=True)
    width, height = None, None
    regex = re.search(r"(\d+)+x(\d+)", info)
    if regex:
        width, height = regex.group(1), regex.group(2)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 452 57; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 9 449 55">
    <p class='ocr_par' dir='ltr' id='par_1_1' title="bbox 1 9 449 55">
     <span class='ocr_line' id='line_1_1' title="bbox 1 9 449 55; baseline 0 -10">
      <span class='ocrx_word' id='word_1_1' title='bbox 1 9 85 45; x_wconf 90' lang='eng' dir='ltr'>The</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 103 9 217 55; x_wconf 89' lang='eng' dir='ltr'>quick</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 235 9 365 45; x_wconf 94' lang='eng' dir='ltr'>brown</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 383 9 449 45; x_wconf 94' lang='eng' dir='ltr'>fox</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2]],
        options={"text_position": "right"},
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    example = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(
        r"The.*quick.*brown.*fox", example, re.DOTALL
    ), "PDF with expected text"

    import_in_mainloop(slist, ["test.pdf"])

    # Because we cannot reproduce the exact typeface used
    # in the original, we cannot expect to be able to
    # round-trip the text layer. Here, at least we can check
    # that we have scaled the page size correctly.
    example = slist.data[1][2].export_hocr()
    assert (
        re.search(rf"bbox\s0\s0\s{width}\s{height}", example) is not None
    ), "import text layer"

    #########################

    for fname in ["test.png", "test.pdf"]:
        if os.path.isfile(fname):
            os.remove(fname)

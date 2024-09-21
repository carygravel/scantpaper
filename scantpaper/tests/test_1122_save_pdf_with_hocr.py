"Test writing PDF with text layer from hocr"

import re
import subprocess
import tempfile
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test writing PDF with text layer from hocr"

    # Create test image
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

    # dir for temporary files
    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.png"])

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='tesseract 4.1.1' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 550 80; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 20 19 527 67">
    <p class='ocr_par' id='par_1_1' lang='eng' title="bbox 20 19 527 67">
     <span class='ocr_line' id='line_1_1' title="bbox 20 19 527 67; baseline 0 -10; x_size 47; x_descenders 9; x_ascenders 10">
      <span class='ocrx_word' id='word_1_1' title='bbox 20 19 112 58; x_wconf 95'>The</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 132 19 264 67; x_wconf 96'>quick</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 284 19 432 58; x_wconf 95'>brown</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 453 19 527 58; x_wconf 96'>fox</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)
    #    slist.data[0][2].import_annotations(hocr)

    mlp = GLib.MainLoop()
    slist.save_pdf(
        path="test.pdf",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    import_in_mainloop(slist, ["test.pdf"])

    # Because we cannot reproduce the exact typeface used
    # in the original, we cannot expect to be able to
    # round-trip the text layer. Here, at least we can check
    # that we have scaled the page size correctly.
    assert (
        re.search(rf"bbox\s0\s0\s{width}\s{height}", slist.data[1][2].export_hocr())
        is not None
    ), "import text layer"
    # assert re.search(r"The.+quick.+brown.+fox", slist.data[1][2].annotations) \
    #     is not None, 'import annotations'

    capture = subprocess.check_output(["pdftotext", "test.pdf", "-"], text=True)
    assert re.search(
        r"The.*quick.*brown.*fox", capture, re.DOTALL
    ), "PDF with expected text"
    # capture = subprocess.check_output(["cat","test.pdf"], text=True)
    # assert re.search(r"/Type\s/Annot\s/Subtype\s/Highlight\s/C.+/Contents.+fox",
    #                  capture) is not None, 'PDF with expected annotation'

    #########################

    clean_up_files(["test.png", "test.pdf"])

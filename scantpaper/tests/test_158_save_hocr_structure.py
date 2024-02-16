"Test writing text"

import os
import subprocess
import tempfile
from gi.repository import GLib
from document import Document
from bboxtree import VERSION


def test_1(import_in_mainloop):
    "Test writing text"

    subprocess.run(["convert", "rose:", "test.pnm"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.pnm"])

    hocr = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name='ocr-system' content='tesseract'>
</head>
<body>
<div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 708 1054'>
<div class='ocr_carea' id='block_1_1' title="bbox 87 578 328 685">
<p class='ocr_par' id='par_1_1' lang='eng' title="bbox 87 578 328 609">
<span class='ocr_line' id='line_1_1' title="bbox 87 578 328 609; baseline 0.01 -7; textangle 0; x_size 31; x_descenders 7; x_ascenders 6">
<span class='ocrx_word' id='word_1_1' title='bbox 87 578 143 602; x_wconf 96'>The1</span>
<span class='ocrx_word' id='word_1_2' title='bbox 154 578 231 609; x_wconf 96'>quick1</span>
<span class='ocrx_word' id='word_1_3' title='bbox 241 578 328 602; x_wconf 96'>brown1</span>
</span>
</p>
</div>
<div class='ocr_carea' id='block_1_2' title="bbox 639 814 708 1054">
<p class='ocr_par' id='par_1_2' lang='eng' title="bbox 639 814 708 1054">
<span class='ocr_line' id='line_1_2' title="bbox 639 814 670 1053; textangle 90; x_size 31; x_descenders 7; x_ascenders 6">
<span class='ocrx_word' id='word_1_4' title='bbox 639 998 663 1053; x_wconf 96'>The2</span>
<span class='ocrx_word' id='word_1_5' title='bbox 639 911 670 987; x_wconf 96'>quick2</span>
<span class='ocrx_word' id='word_1_6' title='bbox 639 814 664 900; x_wconf 96'>brown2</span>
</span>
</p>
</div>
<div class='ocr_carea' id='block_1_3' title='bbox 87 578 328 685'>
<p class='ocr_par' id='par_1_3' title='bbox 87 578 328 685'>
<span class='ocr_header' id='header_1_1' title='bbox 88 578 328 609; baseline 0 -7'>
<span class='ocr_word' id='word_1_7' title='bbox 88 578 143 602; x_wconf 96'>The</span>
<span class='ocr_word' id='word_1_8' title='bbox 154 578 230 609; x_wconf 96'>quick</span>
<span class='ocr_word' id='word_1_9' title='bbox 241 578 328 602; x_wconf 96'>brown</span>
</span>
<span class='ocr_caption' id='caption_1_1' title='bbox 87 616 302 647; baseline 0 -7i; textangle 0;'>
<span class='ocr_word' id='word_1_10' title='bbox 87 616 130 640; x_wconf 96'>fox</span>
<span class='ocr_word' id='word_1_11' title='bbox 139 616 228 647; x_wconf 96'>jumps</span>
<span class='ocr_word' id='word_1_12' title='bbox 239 622 302 640; x_wconf 96'>over</span>
</span>
<span class='ocr_footer' id='footer_1_1' title='bbox 87 654 272 685; baseline -0.005 -7'>
<span class='ocr_word' id='word_1_13' title='bbox 87 655 132 678; x_wconf 96'>the</span>
<span class='ocr_word' id='word_1_14' title='bbox 144 654 201 685; x_wconf 96'>lazy</span>
<span class='ocr_word' id='word_1_15' title='bbox 211 654 272 684; x_wconf 96'>dog.</span>
</span>
</p>
</div>
</div>
</body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)

    mlp = GLib.MainLoop()
    slist.save_hocr(
        path="test.txt",
        list_of_pages=[slist.data[0][2].uuid],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 708 1054'>
   <div class='ocr_carea' id='block_1_1' title='bbox 87 578 328 685'>
    <p class='ocr_par' id='par_1_1' title='bbox 87 578 328 609'>
     <span class='ocr_line' id='line_1_1' title='bbox 87 578 328 609; baseline 0.01 -7; textangle 0'>
      <span class='ocr_word' id='word_1_1' title='bbox 87 578 143 602; x_wconf 96'>The1</span>
      <span class='ocr_word' id='word_1_2' title='bbox 154 578 231 609; x_wconf 96'>quick1</span>
      <span class='ocr_word' id='word_1_3' title='bbox 241 578 328 602; x_wconf 96'>brown1</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_2' title='bbox 639 814 708 1054'>
    <p class='ocr_par' id='par_1_2' title='bbox 639 814 708 1054'>
     <span class='ocr_line' id='line_1_2' title='bbox 639 814 670 1053; textangle 90'>
      <span class='ocr_word' id='word_1_4' title='bbox 639 998 663 1053; x_wconf 96'>The2</span>
      <span class='ocr_word' id='word_1_5' title='bbox 639 911 670 987; x_wconf 96'>quick2</span>
      <span class='ocr_word' id='word_1_6' title='bbox 639 814 664 900; x_wconf 96'>brown2</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_3' title='bbox 87 578 328 685'>
    <p class='ocr_par' id='par_1_3' title='bbox 87 578 328 685'>
     <span class='ocr_header' id='header_1_1' title='bbox 88 578 328 609; baseline 0 -7'>
      <span class='ocr_word' id='word_1_7' title='bbox 88 578 143 602; x_wconf 96'>The</span>
      <span class='ocr_word' id='word_1_8' title='bbox 154 578 230 609; x_wconf 96'>quick</span>
      <span class='ocr_word' id='word_1_9' title='bbox 241 578 328 602; x_wconf 96'>brown</span>
     </span>
     <span class='ocr_caption' id='caption_1_1' title='bbox 87 616 302 647; baseline 0 -7; textangle 0'>
      <span class='ocr_word' id='word_1_10' title='bbox 87 616 130 640; x_wconf 96'>fox</span>
      <span class='ocr_word' id='word_1_11' title='bbox 139 616 228 647; x_wconf 96'>jumps</span>
      <span class='ocr_word' id='word_1_12' title='bbox 239 622 302 640; x_wconf 96'>over</span>
     </span>
     <span class='ocr_footer' id='footer_1_1' title='bbox 87 654 272 685; baseline -0.005 -7'>
      <span class='ocr_word' id='word_1_13' title='bbox 87 655 132 678; x_wconf 96'>the</span>
      <span class='ocr_word' id='word_1_14' title='bbox 144 654 201 685; x_wconf 96'>lazy</span>
      <span class='ocr_word' id='word_1_15' title='bbox 211 654 272 684; x_wconf 96'>dog.</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    assert subprocess.check_output(["cat", "test.txt"], text=True) == hocr, "saved hOCR"

    #########################

    for fname in ["test.pnm", "test.txt", "test2.txt"]:
        if os.path.isfile(fname):
            os.remove(fname)

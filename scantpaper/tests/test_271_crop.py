"Test brightness contrast"

import os
import subprocess
import tempfile
from page import VERSION
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test brightness contrast"

    subprocess.run(["convert", "rose:", "test.gif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.gif"])

    assert slist.data[0][2].width == 70, "width before crop"
    assert slist.data[0][2].height == 46, "height before crop"

    slist.data[0][2].saved = True
    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf 2.7.0' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 70 46'>
      <span class='ocr_word' title='bbox 1 1 9 9'>beyond br</span>
      <span class='ocr_word' title='bbox 5 5 15 15'>on br</span>
      <span class='ocr_word' title='bbox 11 11 19 19'>inside</span>
      <span class='ocr_word' title='bbox 15 15 25 25'>on tl</span>
      <span class='ocr_word' title='bbox 21 21 29 29'>beyond tl</span>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)

    mlp = GLib.MainLoop()
    slist.crop(
        x=10,
        y=10,
        w=10,
        h=10,
        page=slist.data[0][2].uuid,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert slist.data[0][2].width == 10, "page width after crop"
    assert slist.data[0][2].height == 10, "page height after crop"
    image = slist.data[0][2].im_object()
    assert image.width == 10, "image width after crop"
    assert image.height == 10, "image height after crop"
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
  <div class='ocr_page' title='bbox 0 0 10 10'>
   <span class='ocr_word' title='bbox 0 0 5 5'>on br</span>
   <span class='ocr_word' title='bbox 1 1 9 9'>inside</span>
   <span class='ocr_word' title='bbox 5 5 10 10'>on tl</span>
  </div>
 </body>
</html>
"""
    assert slist.data[0][2].export_hocr() == hocr, "cropped hocr"
    assert not slist.scans_saved(), "modification removed saved tag"

    #########################

    for fname in ["test.gif"]:
        if os.path.isfile(fname):
            os.remove(fname)
